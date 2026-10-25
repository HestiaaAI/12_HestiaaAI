"""Evidence aggregation and explicit-assumption routing simulations for Architecture lead."""
from __future__ import annotations

import math
import json
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
            if owner == 'P2':
                environment_path=results_dir/'person2_nf4_colab/person2_benchmark.environment.json'
                if environment_path.exists():
                    condition=json.loads(environment_path.read_text(encoding='utf-8'))['condition']
                    df['benchmark_condition']=(f"{condition['gpu']} / {condition['quantization'].upper()} weights / "
                                               f"{condition['compute_dtype']} compute / {condition['attention']}")
                else:
                    df['benchmark_condition']='CUDA / precision unrecorded; environment sidecar absent'
            elif owner == 'P1':
                df['benchmark_condition'] = 'Apple MPS / native model / exact GPU unrecorded'
            elif owner == 'architecture':
                df['benchmark_condition'] = df['device'].map({
                    'cpu':'Windows CPU / native FP32 / 4 threads',
                    'cuda':'Tesla T4 / native FP16'})
            else:
                df['benchmark_condition']=df['device']+' / owner environment metadata not yet supplied'
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
    if 'benchmark_condition' not in valid:
        valid['benchmark_condition'] = valid['device'] + ' / condition unrecorded'
    model = valid.groupby(['model_id', 'model_category', 'device', 'benchmark_condition', 'max_new_tokens']).agg(
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


def task_summary(data):
    valid = data[data.status.eq('ok')].copy()
    valid['format_ok'] = pd.to_numeric(valid.instruction_adherence_0_to_2,errors='coerce').eq(2)
    frame = valid.groupby(['model_id','prompt_type','benchmark_condition']).agg(
        evaluations=('prompt_id','size'), mean_quality=('self_evaluation_score_1_to_10','mean'),
        format_pass_rate=('format_ok','mean'), median_latency_s=('latency_seconds','median')).reset_index()
    frame['meets_proposed_gate'] = (frame.evaluations.eq(5) & frame.mean_quality.ge(8)
                                    & frame.format_pass_rate.eq(1))
    return frame


def compare_costs(local_path: Path, api_path: Path):
    """Join normalized daily USD totals. Missing inputs stay missing, never become zero."""
    missing = [p.name for p in (local_path,api_path) if not p.exists()]
    if missing:
        return pd.DataFrame(), 'Pending '+', '.join(missing)+'. No observed local/API crossover can be claimed.'
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


def api_rate_frontier(local_path: Path, gateway_daily_cost_usd=0):
    """Conditional price thresholds, not invented API prices or observed DAU crossings."""
    if not local_path.exists():
        return pd.DataFrame()
    if not math.isfinite(gateway_daily_cost_usd) or gateway_daily_cost_usd < 0:
        raise ValueError('Gateway cost assumption must be finite and nonnegative')
    local = pd.read_csv(local_path,keep_default_na=False)
    expected = {(m['model_id'],t) for m in MODEL_REGISTRY for t in TRAFFIC}
    if (local.duplicated(['model_id','traffic_category']).any()
            or set(zip(local.model_id,local.traffic_category)) != expected):
        raise ValueError('Frontier requires all 90 unique local cost rows')
    numeric = ['daily_active_users','requests_per_user','input_tokens_per_request',
               'output_tokens_per_request','total_daily_cost_usd']
    for col in numeric:
        local[col] = pd.to_numeric(local[col],errors='raise')
        if not local[col].map(math.isfinite).all() or (local[col] < 0).any():
            raise ValueError(f'Invalid local frontier input: {col}')
    if (local.requests_per_user.le(0).any() or local.output_tokens_per_request.le(0).any()
            or not local.daily_active_users.eq(local.traffic_category.map(TRAFFIC)).all()):
        raise ValueError('Invalid local frontier workload')
    cols=['model_id','traffic_category',*numeric,'assumptions_id']
    result=local[cols].copy()
    result['assumed_api_gateway_daily_cost_usd']=gateway_daily_cost_usd
    requests=result.daily_active_users*result.requests_per_user
    result['api_blended_rate_break_even_usd_per_million_output_tokens']=(
        (result.total_daily_cost_usd-gateway_daily_cost_usd)*1_000_000/
        (requests*result.output_tokens_per_request))
    result['rate_definition']='output_price_per_million + input/output token ratio * input_price_per_million'
    result['evidence_type']='conditional threshold; API prices/gateway capacity not yet supplied'
    return result


def performance_findings(data, coverage, models, categories):
    successful=int(coverage.successful.sum())
    text=['# Available benchmark findings', '',
          f'{successful}/375 successful, scored evaluations are available across {len(models)}/15 models. '
          'Scores are assistant-assessed; student signoff remains pending. '
          'Hardware/precision conditions are separate; this is not a controlled size-only experiment.', '',
          '| Model | Condition | Mean quality /10 | Median latency (s) |', '|---|---|---|---|']
    for row in models.sort_values('mean_quality',ascending=False).to_dict('records'):
        text.append(f"| {row['model_id']} | {row['benchmark_condition']} | {row['mean_quality']:.2f} | {row['median_latency_s']:.4f} |")
    text += ['', '## Step 1.6 answers', '',
             '1. Best output category: the observed category means below describe the available rows. '
             'A final five-category winner requires all three models per category; quantization/hardware '
             'differences also prevent attributing quality changes solely to parameter count.', '',
             '| Category | Models available /3 | Rows available /75 | Mean quality /10 |', '|---|---|---|---|']
    for row in categories.to_dict('records'):
        text.append(f"| {row['model_category']} | {row['models']} | {row['evaluations']} | {row['mean_quality']:.2f} |")
    text += ['', '2. Larger models did not always score higher. On Person 1’s shared MPS run, '
             'Qwen2.5-1.5B scored 10 on extraction-02 versus 7 for Phi-3.5-mini; this is a '
             'matched-prompt counterexample in the supplied rubric evidence, not a claim that smaller models always win.', '',
             '3. Speed/quality balance: Qwen2.5-1.5B is a strong available candidate within Person 1’s '
             'MPS subset (7.56/10; median 1.5895 s), versus Phi’s 7.32/10 and 5.3627 s. '
             'Within Person 2’s common T4/NF4 condition, inspect the per-task gates before choosing '
             'a model; cross-condition median times do not identify a global fastest model.', '',
             'Routing candidates are in task_summary.csv. A proposed qualification requires five '
             'observations, mean score at least 8/10 and all five instruction-format scores equal to 2. '
             'Passing this small offline gate is a candidate-selection result, not production validation.']
    return '\n'.join(text)+'\n'


def save_analysis_plots(out, models, frontier):
    import matplotlib.pyplot as plt
    if not models.empty:
        groups=list(models.groupby('benchmark_condition'))
        row_count=math.ceil(len(groups)/2)
        fig,axes=plt.subplots(row_count,2,figsize=(13,4*row_count),squeeze=False)
        for ax,(condition,group) in zip(axes.flat,groups):
            ax.scatter(group.median_latency_s,group.mean_quality)
            for row in group.to_dict('records'):
                label=row['model_id'].split('/')[-1].replace('-Instruct','').replace('-instruct','')
                right=row['median_latency_s'] >= group.median_latency_s.max()*.9
                offset_y=-14 if 'SmolLM2-1.7B' in label else 6
                ax.annotate(label,(row['median_latency_s'],row['mean_quality']),
                            xytext=(-5 if right else 5,offset_y),ha='right' if right else 'left',
                            textcoords='offset points',fontsize=7)
            ax.axhline(8,color='grey',linestyle=':',linewidth=1)
            ax.set(title=condition,ylim=(0,11),xlabel='Median generation latency (s)',ylabel='Mean rubric score /10')
            ax.margins(x=.3)
            ax.set_xlim(left=0)
        for ax in list(axes.flat)[len(groups):]: ax.set_visible(False)
        fig.suptitle('Observed speed / quality — compare within each measured condition')
        fig.tight_layout(); fig.savefig(out/'speed_quality_by_condition.png',dpi=150); plt.close(fig)
    if not frontier.empty:
        chosen=['HuggingFaceTB/SmolLM-360M-Instruct','TinyLlama/TinyLlama-1.1B-Chat-v1.0',
                'Qwen/Qwen2.5-1.5B-Instruct','mistralai/Mistral-7B-Instruct-v0.3']
        fig,ax=plt.subplots(figsize=(10,5))
        for model in chosen:
            group=frontier[frontier.model_id.eq(model)].sort_values('daily_active_users')
            ax.plot(group.daily_active_users,group.api_blended_rate_break_even_usd_per_million_output_tokens,
                    marker='o',label=model.split('/')[-1])
        ax.set(xscale='log',yscale='log',xlabel='Daily active users',
               ylabel='Break-even blended API price ($/million output tokens)',
               title='Conditional price thresholds — assumed API gateway $0/day; not API quotes')
        ax.legend(fontsize=8); fig.tight_layout()
        fig.savefig(out/'api_rate_frontier.png',dpi=150); plt.close(fig)


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
    task_summary(data).to_csv(out/'task_summary.csv',index=False)
    (out/'performance_findings.md').write_text(performance_findings(data,coverage,model,category),encoding='utf-8')
    frontier=api_rate_frontier(repo_root/'a7/results/local_costs.csv')
    if not frontier.empty:
        frontier.to_csv(out/'api_rate_frontier.csv',index=False)
    save_analysis_plots(out,model,frontier)
    costs, status = compare_costs(repo_root/'a7/results/local_costs.csv', repo_root/'a7/results/api_costs.csv')
    if not costs.empty:
        costs.to_csv(out/'cost_comparison.csv', index=False)
        crossover_intervals(costs).to_csv(out/'crossover_intervals.csv', index=False)
    return data, coverage, model, category, costs, status


if __name__ == '__main__':
    result = write_analysis(Path(__file__).resolve().parents[1])
    print(result[1].to_string(index=False))
    print(result[-1])
