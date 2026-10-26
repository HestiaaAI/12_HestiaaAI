"""Apply inspected, hash-bound assessments without changing raw benchmark evidence."""
import csv
import hashlib
import json
from pathlib import Path

from a7.benchmark_contract import PROMPTS
from a7.benchmark_runner import RESULT_COLUMNS, select_models, validate_result_rows

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT/'a7/results/person2_nf4_colab/person2_benchmark.csv'
AUDIT = ROOT/'a7/person2/review/benchmark_review_audit.json'


def reviewed_rows(raw=RAW, audit_path=AUDIT):
    audit = json.loads(Path(audit_path).read_text())
    if hashlib.sha256(Path(raw).read_bytes()).hexdigest() != audit['raw_csv_sha256']:
        raise ValueError('Raw evidence changed; inspect new outputs before reusing scores')
    with Path(raw).open(newline='') as handle:
        rows = list(csv.DictReader(handle))
    validate_result_rows(rows, select_models(owner='P2'), PROMPTS)
    entries = {(e['model_id'], e['prompt_id']): e for e in audit['entries']}
    if len(entries) != len(audit['entries']) or len(entries) != len(rows):
        raise ValueError('Review coverage must contain exactly one assessment per response')
    for row in rows:
        entry = entries[(row['model_id'], row['prompt_id'])]
        if hashlib.sha256(row['generated_output'].encode()).hexdigest() != entry['response_sha256']:
            raise ValueError('Response changed; previous assessment cannot be reused')
        components = entry['components']
        if len(components) != 5 or any(type(v) is not int or not 0 <= v <= cap
                                     for v, cap in zip(components, [3, 2, 2, 2, 1])):
            raise ValueError('Rubric component outside its allowed range')
        row.update(dict(zip(audit['component_order'], components)))
        row['self_evaluation_score_1_to_10'] = max(1, sum(components))
        row['review_notes'] = entry['notes']
    return rows


def main():
    rows = reviewed_rows()
    dest = ROOT/'a7/results/person2_benchmark.csv'
    with dest.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_COLUMNS)
        writer.writeheader(); writer.writerows(rows)
    print(f'Wrote {len(rows)} assessed rows to {dest.relative_to(ROOT)}; raw CSV unchanged.')


if __name__ == '__main__':
    main()
