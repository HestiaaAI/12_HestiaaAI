"""Evidence aggregation and explicit-assumption routing simulations for Architecture lead."""
from __future__ import annotations

import math
from pathlib import Path
import pandas as pd

from a7.benchmark_contract import MODEL_REGISTRY, PROMPTS
from a7.benchmark_runner import RESULT_COLUMNS

TRAFFIC = {"Prototype": 1_000, "Early Startup": 10_000,
           "Growing Product": 100_000, "Large Platform": 1_000_000,
           "Mass Consumer App": 10_000_000, "Global Platform": 100_000_000}


def benchmark_evidence(results_dir: Path):
    """Read only explicit owner files, reject drift, and report missing evidence."""
    frames, coverage = [], []
    registry = {m['model_id']: m for m in MODEL_REGISTRY}
    prompts = {p['prompt_id']: p for p in PROMPTS}
    for owner in ('P1', 'P2', 'P3', 'architecture'):
        filename = 'architecture_benchmark.csv' if owner == 'architecture' else f'person{owner[1]}_benchmark.csv'
        path = results_dir / filename
        expected = {(m['model_id'], p['prompt_id']) for m in MODEL_REGISTRY
                    if m['owner'] == owner for p in PROMPTS}
        ok = scored = rows_count = 0
        if path.exists():
            df = pd.read_csv(path, keep_default_na=False)
            if set(RESULT_COLUMNS) - set(df.columns):
                raise ValueError(f'{path}: result columns missing')
            if df.duplicated(['model_id', 'prompt_id']).any():
                raise ValueError(f'{path}: duplicate model/prompt rows')
            for row in df.to_dict('records'):
                key = (row['model_id'], row['prompt_id'])
                if key not in expected or row['owner'] != owner:
                    raise ValueError(f'{path}: unexpected owner/model/prompt {key}')
                if row['model_category'] != registry[row['model_id']]['category']:
                    raise ValueError(f'{path}: category drift')
                if (row['prompt_type'] != prompts[row['prompt_id']]['prompt_type']
                        or row['prompt'] != prompts[row['prompt_id']]['input']):
                    raise ValueError(f'{path}: prompt drift')
                if row['status'] not in ('ok', 'error'):
                    raise ValueError(f'{path}: unknown status')
                if int(row['max_new_tokens']) != 220:
                    raise ValueError(f'{path}: generation limit differs from shared 220-token contract')
            rows_count = len(df)
            valid = df['status'].eq('ok')
            ok = int(valid.sum())
            scores = pd.to_numeric(df['self_evaluation_score_1_to_10'], errors='coerce')
            if (valid & df['self_evaluation_score_1_to_10'].ne('') & ~scores.between(1, 10)).any():
                raise ValueError(f'{path}: successful score outside the shared 1–10 rubric')
            scored = int((valid & scores.between(1, 10)).sum())
            df['self_evaluation_score_1_to_10'] = scores
            for col in ('latency_seconds', 'tokens_per_second', 'output_tokens'):
                df[col] = pd.to_numeric(df[col], errors='coerce')
            if (df.loc[valid, 'latency_seconds'].isna().any()
                    or (df.loc[valid, 'latency_seconds'] <= 0).any()):
                raise ValueError(f'{path}: invalid successful latency')
            frames.append(df)
        coverage.append(dict(owner=owner, expected=len(expected), recorded=rows_count,
                             successful=ok, scored=scored, missing=len(expected)-rows_count,
                             remaining_successful=len(expected)-ok))
    data = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=RESULT_COLUMNS)
    return data, pd.DataFrame(coverage)


def benchmark_summaries(data):
    """Use successful rows; split speed by device/token limit. Hardware labels still required."""
    valid = data[data.status.eq('ok')].copy()
    if valid.empty:
        return pd.DataFrame(), pd.DataFrame()
    model = valid.groupby(['model_id', 'model_category', 'device', 'max_new_tokens']).agg(
        evaluations=('prompt_id', 'size'), scored=('self_evaluation_score_1_to_10', 'count'),
        mean_quality=('self_evaluation_score_1_to_10', 'mean'),
        median_latency_s=('latency_seconds', 'median'),
        p95_latency_s=('latency_seconds', lambda x: x.quantile(.95)),
        median_tokens_s=('tokens_per_second', 'median')).reset_index()
    # Incomplete categories are labeled with counts; no automatic winner is declared.
    category = valid.groupby('model_category').agg(
        models=('model_id', 'nunique'), evaluations=('prompt_id', 'size'),
        scored=('self_evaluation_score_1_to_10', 'count'),
        mean_quality=('self_evaluation_score_1_to_10', 'mean')).reset_index()
    category['expected_evaluations'] = 75
    return model, category


def compare_costs(local_path: Path, api_path: Path):
    """Join normalized daily USD totals. Missing inputs stay missing, never become zero."""
    if not local_path.exists() or not api_path.exists():
        return pd.DataFrame(), 'Pending Person 2 local_costs.csv and Person 3 api_costs.csv.'
    tables = []
    required = {'model_id', 'traffic_category', 'daily_active_users', 'requests_per_user',
                'input_tokens_per_request', 'output_tokens_per_request', 'total_daily_cost_usd',
                'assumptions_id', 'source_or_assumption'}
    expected = {(m['model_id'], t) for m in MODEL_REGISTRY for t in TRAFFIC}
    for path in (local_path, api_path):
        df = pd.read_csv(path, keep_default_na=False)
        if required - set(df.columns):
            raise ValueError(f'{path}: missing columns {required-set(df.columns)}')
        if df.duplicated(['model_id', 'traffic_category']).any():
            raise ValueError(f'{path}: duplicate cost rows')
        if set(zip(df.model_id, df.traffic_category)) != expected:
            raise ValueError(f'{path}: must contain all 90 model/traffic combinations')
        for col in ('daily_active_users', 'requests_per_user', 'input_tokens_per_request',
                    'output_tokens_per_request', 'total_daily_cost_usd'):
            df[col] = pd.to_numeric(df[col], errors='raise')
            if not df[col].map(math.isfinite).all() or (df[col] < 0).any():
                raise ValueError(f'{path}: invalid {col}')
        if not (df.daily_active_users == df.traffic_category.map(TRAFFIC)).all():
            raise ValueError(f'{path}: traffic counts do not match assignment')
        if (df.requests_per_user <= 0).any():
            raise ValueError(f'{path}: requests per user must be positive')
        if df[['assumptions_id', 'source_or_assumption']].eq('').any().any():
            raise ValueError(f'{path}: document cost assumptions and source')
        tables.append(df)
    common = ['model_id', 'traffic_category', 'daily_active_users', 'requests_per_user',
              'input_tokens_per_request', 'output_tokens_per_request', 'assumptions_id']
    joined = tables[0].merge(tables[1], on=common, suffixes=('_local', '_api'), validate='one_to_one')
    if len(joined) != 90:
        raise ValueError('Local/API workload or assumptions differ; reconcile before comparing')
    joined['local_minus_api_usd'] = joined.total_daily_cost_usd_local - joined.total_daily_cost_usd_api
    joined['cheaper'] = joined.local_minus_api_usd.map(
        lambda d: 'local' if d < 0 else 'api' if d > 0 else 'tie')
    return joined.sort_values(['model_id', 'daily_active_users']), 'Validated 90 like-for-like daily cost comparisons.'


def crossover_intervals(costs):
    """Return every observed change, not an unjustified single continuous break-even."""
    rows = []
    for model, group in costs.groupby('model_id'):
        previous = None
        for row in group.sort_values('daily_active_users').to_dict('records'):
            if previous and row['cheaper'] != previous['cheaper']:
                rows.append(dict(model_id=model, lower_dau=previous['daily_active_users'],
                                 upper_dau=row['daily_active_users'],
                                 lower_cheaper=previous['cheaper'], upper_cheaper=row['cheaper']))
            previous = row
    return pd.DataFrame(rows, columns=['model_id', 'lower_dau', 'upper_dau', 'lower_cheaper', 'upper_cheaper'])


def routing_simulation():
    """Planning assumptions only: no modeled latency/quality is reported as measurement."""
    # Fractions are mutually exclusive final destinations. Cache hits make no generation call.
    scenarios = [('Normal operation', .10, .65, .25, 1),
                 ('Evening peak', .10, .50, .40, 4),
                 ('Complex household plan', .05, .15, .80, 1),
                 ('Budget pressure', .20, .70, .10, 1),
                 ('Local overload', .10, .10, .80, 4)]
    rows = []
    for traffic, dau in TRAFFIC.items():
        for name, cache, local, api, peak_factor in scenarios:
            requests = dau  # assignment convention: one request per daily active user
            rows.append(dict(traffic_category=traffic, daily_active_users=dau, scenario=name,
                             assumed_requests_per_user=1, assumed_output_tokens=500,
                             assumed_cache_fraction=cache, assumed_local_fraction=local,
                             assumed_api_fraction=api, assumed_peak_factor=peak_factor,
                             cached_requests=requests*cache, local_requests=requests*local,
                             api_requests=requests*api, local_output_tokens=requests*local*500,
                             api_output_tokens=requests*api*500,
                             peak_generation_requests_s=requests*(local+api)/86400*peak_factor,
                             evidence_type='illustrative planning assumptions'))
    return pd.DataFrame(rows)


def write_analysis(repo_root: Path):
    out = repo_root / 'a7/results/architecture'
    out.mkdir(parents=True, exist_ok=True)
    data, coverage = benchmark_evidence(repo_root / 'a7/results')
    model, category = benchmark_summaries(data)
    for name, frame in [('coverage', coverage), ('model_summary', model), ('category_summary', category),
                        ('routing_simulation', routing_simulation())]:
        frame.to_csv(out / f'{name}.csv', index=False)
    costs, status = compare_costs(repo_root/'a7/results/local_costs.csv', repo_root/'a7/results/api_costs.csv')
    if not costs.empty:
        costs.to_csv(out/'cost_comparison.csv', index=False)
        crossover_intervals(costs).to_csv(out/'crossover_intervals.csv', index=False)
    return data, coverage, model, category, costs, status


if __name__ == '__main__':
    result = write_analysis(Path(__file__).resolve().parents[1])
    print(result[1].to_string(index=False))
    print(result[-1])
