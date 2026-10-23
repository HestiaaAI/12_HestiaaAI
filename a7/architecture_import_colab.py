"""Import verified TinyLlama Colab results while preserving CPU evidence."""
import argparse
import csv
import json
from pathlib import Path
import zipfile

from a7.benchmark_contract import PROMPTS
from a7.benchmark_runner import select_models, validate_result_rows, RESULT_COLUMNS

MODEL = 'TinyLlama/TinyLlama-1.1B-Chat-v1.0'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    folder = root/'a7/results'
    with zipfile.ZipFile(args.bundle) as archive:
        csv_names = [n for n in archive.namelist() if n.endswith('_tinyllama_cuda.csv')]
        env_names = [n for n in archive.namelist() if n.endswith('_tinyllama_cuda.environment.json')]
        if len(csv_names) != 1 or len(env_names) != 1:
            raise ValueError('Expected one TinyLlama CSV and one environment file')
        csv_bytes = archive.read(csv_names[0])
        env_bytes = archive.read(env_names[0])
    import io
    rows = list(csv.DictReader(io.StringIO(csv_bytes.decode('utf-8'))))
    for row in rows:
        row['owner'] = 'architecture'
    environment = json.loads(env_bytes)
    validate_result_rows(rows, select_models(model_ids=[MODEL]), PROMPTS)
    if any(r['status'] != 'ok' or r['device'] != 'cuda' or int(r['max_new_tokens']) != 220 for r in rows):
        raise ValueError('Import requires 25 successful CUDA evaluations with the common token limit')
    if environment['dtype'] != 'float16' or environment['device'] != 'cuda':
        raise ValueError('Unexpected Colab precision/device metadata')
    import hashlib
    migration_path = root/'a7/architecture/source_label_migration.json'
    migration = json.loads(migration_path.read_text(encoding='utf-8')) if migration_path.exists() else {}
    if set(environment['contract_source_sha256']) != {'__init__.py','benchmark_contract.py','benchmark_runner.py','review_results.py'}:
        raise ValueError('Unexpected source-file names in Colab metadata')
    for name, digest in environment['contract_source_sha256'].items():
        source = (root/'a7'/name).read_text(encoding='utf-8')
        actual = hashlib.sha256(source.encode()).hexdigest()
        permitted_rename = (migration.get('before_source_sha256',{}).get(name) == digest
                            and migration.get('after_source_sha256',{}).get(name) == actual)
        if actual != digest and not permitted_rename:
            raise ValueError(f'Colab shared source differs: {name}')
    canonical = folder/'architecture_benchmark.csv'
    old_bytes = canonical.read_bytes()
    original = list(csv.DictReader(io.StringIO(old_bytes.decode('utf-8'))))
    merged = [r for r in original if r['model_id'] != MODEL] + rows
    validate_result_rows(merged, select_models(owner='architecture'), PROMPTS)
    archive_path = folder/'architecture_cpu_float32_before_colab.csv'
    if not archive_path.exists():
        archive_path.write_bytes(old_bytes)
    with (folder/'architecture_tinyllama_cuda.csv').open('w',encoding='utf-8',newline='') as handle:
        writer = csv.DictWriter(handle,fieldnames=RESULT_COLUMNS)
        writer.writeheader(); writer.writerows(rows)
    (folder/'architecture_tinyllama_cuda.environment.json').write_bytes(env_bytes)
    temporary = canonical.with_suffix('.csv.tmp')
    with temporary.open('w',encoding='utf-8',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=RESULT_COLUMNS)
        writer.writeheader(); writer.writerows(merged)
    temporary.replace(canonical)
    metadata = dict(
        timing_comparability='Mixed devices/precision: compare within hardware groups only.',
        models={
            'HuggingFaceTB/SmolLM-360M-Instruct':dict(device='cpu',dtype='float32',
                environment_file='architecture_environment.json'),
            MODEL:dict(device='cuda',dtype='float16',
                environment_file='architecture_tinyllama_cuda.environment.json'),
            'meta-llama/Llama-3.2-3B-Instruct':dict(device='cpu',dtype='float32',
                status='not successfully evaluated; gated access pending')})
    (folder/'architecture_benchmark_environment.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    print('Imported 25 verified TinyLlama CUDA rows; original CPU evidence archived.')


if __name__ == '__main__':
    main()
