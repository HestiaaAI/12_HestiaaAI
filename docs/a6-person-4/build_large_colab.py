"""Create the self-contained P4 category-correction GPU notebook."""
from pathlib import Path
import nbformat as nb

ROOT=Path(__file__).resolve().parents[2]
source=(ROOT/'llm-test/person4_large_benchmark.py').read_text(encoding='utf-8')
models=['tiiuae/Falcon3-7B-Instruct','Qwen/Qwen2.5-14B-Instruct',
        'microsoft/Phi-3-medium-4k-instruct','Qwen/Qwen3-14B']
cells=[nb.v4.new_markdown_cell("""# Hestia P4 — larger-category correction

**Actual CUDA inference, not a hosted text API.** Run on a fresh Colab GPU
(T4 with sufficient free VRAM or a larger GPU). This tests Falcon3-7B plus
Qwen2.5-14B, Phi-3-medium-4k, and Qwen3-14B: four models × two fixed inputs ×
zero/one/few/many-shot = **32 generations**.

Weights are NF4 4-bit; compute and non-quantized modules are FP32 to avoid the
FP16 numerical issue observed in P3's Qwen work. Attention is eager, generation
is deterministic with 220 new tokens, Qwen3 thinking is disabled. These results
are labeled quantized and must not be passed off as native FP16 measurements.
The runner checks finite logits, records revisions/configuration and timings,
and checkpoints every response. Quality scores stay blank until outputs are read.

No Hugging Face token, paid API key, Drive mounting, or paid Colab purchase is
required for these public models. Use only an available GPU session; do not buy
compute units as part of running this notebook. Downloads can be large. Model
weights are deleted from this notebook's dedicated cache after each successful
model; results are retained. Original small-model results remain separate.

P1 owns the final matrix. These runs supply one-large / three-above-10B candidates
under the original ranges. Main PR #31 now uses different balanced ranges;
these tests are separate evidence until P1/the team chooses the final selection.
Do not blindly add them to the existing 15-model notebook.
"""),nb.v4.new_code_cell("""# Environment setup; first generation below downloads the actual model weights.
%pip -q install transformers==4.57.6 huggingface-hub==0.36.2 accelerate==1.15.0 bitsandbytes==0.50.2 'sentencepiece>=0.2,<0.3' 'protobuf>=6,<7' 'psutil>=7,<8'
""")]
cells.append(nb.v4.new_code_cell("""import os, sys, json, shutil, subprocess, zipfile
from pathlib import Path
os.environ['HF_HOME']='/content/hestia_p4_cache'
os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
os.environ['HF_HUB_DISABLE_XET']='1'
import torch
assert torch.cuda.is_available(), 'Choose Runtime > Change runtime type > GPU first. CPU is not sufficient.'
print('GPU:', torch.cuda.get_device_name(0))
print('Free/total VRAM GiB:', tuple(round(x/2**30,2) for x in torch.cuda.mem_get_info()))
WORK=Path('/content/hestia_p4_large')
WORK.mkdir(exist_ok=True)
OUTPUT=WORK/'a6_results/person4_large'
OUTPUT.mkdir(parents=True,exist_ok=True)
RUNNER=WORK/'person4_large_benchmark.py'
RUNNER.write_text("""+repr(source)+""",encoding='utf-8')

def package_results():
    bundle=Path('/content/hestia_p4_large_results.zip')
    with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
        for p in OUTPUT.rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:
                z.write(p,p.relative_to(WORK))
        z.write(RUNNER,'person4_large_benchmark.py')
    return str(bundle)

def run_one(model):
    # Separate process releases all model/allocator memory between models.
    with subprocess.Popen([sys.executable,'-u',str(RUNNER),'--model',model,'--output',str(OUTPUT)],
                          stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1) as process:
        for line in process.stdout:
            print(line,end='',flush=True)
        code=process.wait()
    print('Checkpoint bundle:',package_results(),flush=True)
    if code:
        raise RuntimeError(f'{model} stopped (exit {code}); retain partial results and inspect the error. Do not count it as completed.')
    # Only our newly downloaded, reproducible weight cache is removed.
    cache=Path('/content/hestia_p4_cache').resolve()
    folder=cache/'hub'/('models--'+model.replace('/','--'))
    if folder.resolve().is_relative_to(cache) and folder.exists():
        shutil.rmtree(folder)
    print('Completed model; result evidence preserved.',flush=True)
"""))
for model in models:
    cells.append(nb.v4.new_markdown_cell(f"## {model}\n\nFirst use downloads weights automatically through Transformers. Eight actual generations are checkpointed."))
    cells.append(nb.v4.new_code_cell(f"run_one({model!r})"))
cells += [nb.v4.new_markdown_cell("""## Export the actual evidence

Run this cell even after a model failure to preserve partial results. A partial
CSV is not a completed four-model benchmark. Do not invent quality scores.
Return the ZIP to the P4 checkout for raw-output review, metadata validation,
and P1's final model-matrix handoff. The checksum/base64 block is a backup transfer
of the same small evidence ZIP; it contains no weights."""),nb.v4.new_code_cell("""import csv, base64, hashlib
path=OUTPUT/'person4_large_results.csv'
if path.exists():
    with path.open(encoding='utf-8',newline='') as f:
        rows=list(csv.DictReader(f))
    counts={model:sum(r['model_id']==model for r in rows) for model in [
        'tiiuae/Falcon3-7B-Instruct','Qwen/Qwen2.5-14B-Instruct',
        'microsoft/Phi-3-medium-4k-instruct','Qwen/Qwen3-14B']}
    print('Actual completed generations:',len(rows),counts)
    print('All four complete:',len(rows)==32 and all(n==8 for n in counts.values()))
else:
    print('No actual generations completed yet.')
bundle=Path(package_results())
print('P4_ZIP_SHA256',hashlib.sha256(bundle.read_bytes()).hexdigest())
print('P4_ZIP_BASE64_BEGIN')
print(base64.b64encode(bundle.read_bytes()).decode('ascii'))
print('P4_ZIP_BASE64_END')
from google.colab import files
files.download(str(bundle))
""")]
n=nb.v4.new_notebook(cells=cells,metadata={'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'},
    'colab':{'provenance':[]},'accelerator':'GPU','language_info':{'name':'python'}})
dest=ROOT/'llm-test/person4_large_models_colab.ipynb'
nb.write(n,dest)
print(dest)
