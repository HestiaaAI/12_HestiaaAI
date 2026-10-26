"""Build a checked A7 upload bundle from an explicit file-type and directory allowlist."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT=Path(__file__).resolve().parents[1]
PRIMARY=['a7/multi_model_system.ipynb','a7/system_design.md',
         'a7/slm/slm_experiments.ipynb','a7/slm/person2_rag_colab.ipynb',
         'a7/person3/finetune_slm.ipynb']
ALLOWED={'.py','.csv','.json','.md','.txt','.png','.jpg','.ipynb'}
EXCLUDED_PARTS={'__pycache__','.ipynb_checkpoints','checkpoints','model_cache',
                'models','offload','.cache','.local-backups'}
EXCLUDED_NAMES={'architecture_gpu_benchmark.ipynb','architecture_tinyllama_colab.ipynb',
    'architecture_cpu_float32_before_colab.csv',
    'architecture_float16_benchmark.csv','architecture_float16_benchmark_environment.json',
    'architecture_environment.json'}
CREDENTIAL=re.compile(r'hf_[A-Za-z0-9]{25,}|ghp_[A-Za-z0-9]{25,}|gsk_[A-Za-z0-9]{25,}|sk-[A-Za-z0-9]{30,}')


def candidate_files(root):
    return sorted(p for p in (root/'a7').rglob('*') if p.is_file() and not p.is_symlink()
                  and p.suffix.lower() in ALLOWED and p.name not in EXCLUDED_NAMES
                  and not any(part in EXCLUDED_PARTS or part.startswith('.')
                              for part in p.relative_to(root).parts))


def validate(root):
    for name in PRIMARY:
        path=root/name
        if not path.exists():raise ValueError(f'Missing required deliverable: {name}')
        if path.suffix=='.ipynb':
            notebook=json.loads(path.read_text(encoding='utf-8'))
            code=[c for c in notebook['cells'] if c['cell_type']=='code']
            if not code or any(c.get('execution_count') is None for c in code):
                raise ValueError(f'Required notebook lacks saved execution: {name}')
            if any(o.get('output_type')=='error' for c in code for o in c.get('outputs',[])):
                raise ValueError(f'Required notebook has saved errors: {name}')
    from a7.architecture_analysis import benchmark_evidence,compare_costs
    _,coverage=benchmark_evidence(root/'a7/results')
    if int(coverage.successful.sum())!=375 or int(coverage.scored.sum())!=375:
        raise ValueError('Submission requires all 375 successful scored evaluations')
    costs,_=compare_costs(root/'a7/results/local_costs.csv',root/'a7/results/api_costs.csv')
    if len(costs)!=90:raise ValueError('Submission requires both 90-row cost tables')


def build(root=ROOT,output=None):
    root=Path(root).resolve()
    output=Path(output) if output else root/'dist/hestia-a7-submission.zip'
    validate(root)
    files=candidate_files(root)
    payloads={p.relative_to(root).as_posix():p.read_bytes() for p in files}
    for name,content in payloads.items():
        if Path(name).suffix not in {'.png','.jpg'} and CREDENTIAL.search(content.decode('utf-8')):
            raise ValueError(f'Possible credential in {name}; inspect before packaging')
    payloads['README.md']=('''# Hestia AI — Team 12: Assignment 7 submissions

Start with [the submission guide](a7/SUBMISSION.md) for the requirement map,
findings, limitations and reproduction instructions.

## Multi-model benchmarking, costs and routing

- [Benchmark notebook](a7/multi_model_system.ipynb)
- [Architecture and cost analysis](a7/system_design.md)

## Class SLM, RAG and fine-tuning

- [SLM experiments and Part 4 comparison](a7/slm/slm_experiments.ipynb)
- [RAG experiment](a7/slm/person2_rag_colab.ipynb)
- [Fine-tuning experiment](a7/person3/finetune_slm.ipynb)

Keep the folder structure intact. Saved outputs can be reviewed without tokens,
weights or Django. Supporting source and evidence remain under `a7/`.
`MANIFEST.json` lists exact file checksums; model weights are excluded.
''').encode('utf-8')
    # All paths under a7 remain identical, including raw CSV/notebook bytes.
    manifest=dict(format_version=1,primary_deliverables=PRIMARY,
        scope='Both A7 assignments; saved evidence plus source; no model weights.',
        benchmark_evaluations=375,local_cost_rows=90,api_cost_rows=90,
        files={name:dict(bytes=len(content),sha256=hashlib.sha256(content).hexdigest())
               for name,content in sorted(payloads.items())})
    payloads['MANIFEST.json']=(json.dumps(manifest,indent=2)+'\n').encode('utf-8')
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,content in sorted(payloads.items()):archive.writestr(name,content)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:raise ValueError('Archive integrity check failed')
        for name,record in manifest['files'].items():
            if hashlib.sha256(archive.read(name)).hexdigest()!=record['sha256']:
                raise ValueError(f'Packaged checksum mismatch: {name}')
    digest=hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.zip.sha256').write_text(f'{digest}  {output.name}\n',encoding='utf-8')
    print(f'Built {output}: {len(payloads)} files; SHA256 {digest}')
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    build(output=args.output)
