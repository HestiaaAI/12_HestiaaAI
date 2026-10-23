"""Build a self-contained Colab notebook with the unchanged shared benchmark sources."""
import hashlib
import json
from pathlib import Path
import nbformat as nbf


def main():
    root = Path(__file__).resolve().parents[1]
    names = ['__init__.py', 'benchmark_contract.py', 'benchmark_runner.py', 'review_results.py']
    sources = {name: (root/'a7'/name).read_text(encoding='utf-8') for name in names}
    hashes = {name: hashlib.sha256(text.encode()).hexdigest() for name, text in sources.items()}
    setup = '''import sys, subprocess, os, json, hashlib
from pathlib import Path
WORK = Path('/content/hestia_a7_architecture')
WORK.mkdir(parents=True, exist_ok=True)
os.environ['HF_HOME'] = str(WORK/'model_cache/huggingface')
os.environ['HF_HUB_DISABLE_XET'] = '1'
subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q',
    'transformers==4.57.6', 'huggingface-hub==0.36.2', 'accelerate==1.15.0', 'psutil>=5.9'])
SOURCES = ''' + repr(sources) + '''
HASHES = ''' + repr(hashes) + '''
(WORK/'a7').mkdir(exist_ok=True)
for name, source in SOURCES.items():
    assert hashlib.sha256(source.encode()).hexdigest() == HASHES[name]
    (WORK/'a7'/name).write_text(source, encoding='utf-8')
if str(WORK) not in sys.path:
    sys.path.insert(0, str(WORK))
print('Shared benchmark source hashes verified. Ready for CUDA benchmark.')
'''
    benchmark = '''import torch, platform, importlib.metadata
from datetime import datetime, timezone
from a7.benchmark_runner import run_matrix, select_models
assert torch.cuda.is_available(), 'Select Runtime > Change runtime type > T4 GPU.'
OUT = WORK/'results/architecture_tinyllama_cuda.csv'
OUT.parent.mkdir(parents=True, exist_ok=True)
ENV = dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(), platform=platform.platform(),
    device='cuda', dtype='float16', gpu=torch.cuda.get_device_name(0),
    vram_bytes=torch.cuda.get_device_properties(0).total_memory,
    max_new_tokens=220, do_sample=False, contract_source_sha256=HASHES,
    packages={p:importlib.metadata.version(p) for p in ['torch','transformers','huggingface-hub']},
    timing_scope='Unchanged shared runner: prefill plus decoding, excludes model loading; no warmup')
OUT.with_suffix('.environment.json').write_text(json.dumps(ENV,indent=2),encoding='utf-8')
print('GPU:',ENV['gpu'],flush=True)
rows = run_matrix(select_models(model_ids=['TinyLlama/TinyLlama-1.1B-Chat-v1.0']),
    OUT, device_request='cuda', dtype_request='float16')
print('TinyLlama successful evaluations:',sum(r['status']=='ok' for r in rows),'/ 25')
'''
    export = '''from a7.review_results import review_csv
import csv, zipfile
review_csv(OUT)
with OUT.open(encoding='utf-8',newline='') as handle:
    results = list(csv.DictReader(handle))
print('Successful:',sum(r['status']=='ok' for r in results),'/ 25')
print('Automated rubric scores require inspection against actual responses.')
BUNDLE = WORK/'architecture_tinyllama_cuda_results.zip'
with zipfile.ZipFile(BUNDLE,'w',zipfile.ZIP_DEFLATED) as z:
    z.write(OUT,OUT.name)
    z.write(OUT.with_suffix('.environment.json'),OUT.with_suffix('.environment.json').name)
print('Results bundle:',BUNDLE)
from google.colab import files
files.download(str(BUNDLE))
'''
    nb = nbf.v4.new_notebook(cells=[
        nbf.v4.new_markdown_cell('# A7 Architecture lead — TinyLlama on Colab GPU\n\n'
            'Select a T4 GPU runtime and run the cells in order. No Hugging Face token is '
            'needed for this public model. The shared 25 prompts, greedy generation and '
            '220-token limit are unchanged. Sources are embedded with SHA256 checks. '
            'Keep these CUDA/float16 timings separate from Windows CPU/float32 timings. '
            'Llama-3.2 remains subject to the author’s gated access approval.'),
        nbf.v4.new_code_cell(setup), nbf.v4.new_code_cell(benchmark), nbf.v4.new_code_cell(export)],
        metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}})
    nbf.write(nb,root/'a7/architecture_tinyllama_colab.ipynb')
    for cell in nb.cells:
        if cell.cell_type == 'code': compile(cell.source,'colab_cell','exec')
    print('Self-contained Colab notebook built and code cells syntax-checked.')


if __name__ == '__main__':
    main()
