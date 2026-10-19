"""Build the P4 notebook without editing Person 1's shared notebook."""
from pathlib import Path
import nbformat as nb

ROOT = Path(__file__).resolve().parents[2]
cells = [
    nb.v4.new_markdown_cell("""# Hestia A6 — Person 4 model tests and UI integration

This contribution tests **three additional public models** not present in P1/P2's
completed CSVs: Qwen2-0.5B-Instruct, SmolLM-360M-Instruct, and Qwen3-0.6B.
They are different from teammates' Qwen2.5 and SmolLM2 IDs. Selection follows the
user's authorization to choose any three uncompleted models, bounded by this
machine's approximately 15.5 GiB RAM and lack of a CUDA GPU.

These small models **do not complete the missing large-model categories** in the
team's original roster. Person 1 owns the final 15-model matrix; keep the root
notebook intact and merge this CSV through its existing merge cell.

Set up a separate Python 3.11 environment using
`docs/a6-person-4/requirements-benchmark.txt`. Weights stay in ignored
`model_cache/`. No API keys or paid calls are needed."""),
    nb.v4.new_markdown_cell("""## Download weights first

The first code cell downloads the actual public Transformers safetensors and
tokenizers into an ordinary local directory (avoids Windows symlink privileges).
It records publisher revision IDs and reuses existing local files on subsequent
runs. First execution requires network access and a few GB of disk space."""),
    nb.v4.new_code_cell("""from pathlib import Path
import importlib.util
import sys

ROOT = Path.cwd()
if not (ROOT / 'manage.py').exists():
    ROOT = ROOT.parent
assert (ROOT / 'manage.py').exists(), 'Run from repository root or llm-test/'
spec = importlib.util.spec_from_file_location('p4_benchmark', ROOT / 'docs/a6-person-4/benchmark.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
snapshots = runner.download_models()
{model: details['revision'] for model, details in snapshots.items()}"""),
    nb.v4.new_markdown_cell("""## Shared experiment contract

Two fixed household paragraphs × four prompting modes × three models = **24
generations**. The runner imports the exact system instruction, examples, parser,
and schema functions from the checked-in P2 helper, aligned to P1's notebook.
`zero/one/few/many` use 0/1/2/3 examples. Generation is greedy, capped at 220 new
tokens, CPU FP32 with four PyTorch threads and seed 0. Qwen3 thinking is explicitly
disabled to keep direct JSON output within the same token budget; this mode and
greedy decoding are disclosed deviations from vendor-recommended sampling.

Model-card sources:
- https://huggingface.co/Qwen/Qwen2-0.5B-Instruct
- https://huggingface.co/HuggingFaceTB/SmolLM-360M-Instruct
- https://huggingface.co/Qwen/Qwen3-0.6B

The runner checkpoints real outputs after each response. If the CSV already
contains all 24 runs, this cell resumes without re-generating; the following
cells display the stored evidence. To rerun from scratch, move the P4 CSV aside
first. Download time is separate from recorded model-load and generation time.
CPU timings are not comparable to teammates' hardware without controls."""),
    nb.v4.new_code_cell("""team = runner.contract()
print(team.SYSTEM_INSTRUCTION)
print(team.TEST_INPUTS)
print('Shot modes:', team.SHOT_MODES)
runner.run(snapshots)"""),
    nb.v4.new_markdown_cell("""## Environment and automatic schema results

Raw text is kept even when JSON fails or the token cap truncates a response.
Schema success is measured separately from semantic quality. A model can produce
valid JSON that copies an example or misses the household's actual concerns."""),
    nb.v4.new_code_cell("""import json
import pandas as pd
print((ROOT / 'a6_results/person4_environment.json').read_text(encoding='utf-8'))
results = pd.read_csv(ROOT / 'a6_results/person4_benchmark_results.csv')
assert len(results) == 24
assert results.groupby('model_id').size().eq(8).all()
assert set(results['model_id']) == set(runner.MODELS)
summary = results.groupby('model_id').agg(
    runs=('input_id', 'size'),
    schema_success_rate=('schema_valid', 'mean'),
    mean_generation_seconds=('generation_seconds', 'mean'),
    mean_quality=('quality_score_0_to_10', 'mean'),
)
display(summary.round(3))
display(results.groupby(['model_id', 'shot_mode']).agg(
    schema_success_rate=('schema_valid', 'mean'),
    mean_generation_seconds=('generation_seconds', 'mean'),
    mean_quality=('quality_score_0_to_10', 'mean'),
).round(3))"""),
    nb.v4.new_markdown_cell("""## Review every raw response

Shared rubric: extraction 0–3, task types 0–2, priority 0–2, clarity 0–2,
JSON format 0–1. Scores and written notes are assistant-assisted content reviews,
not a separate blinded human study. The submitter should inspect the raw outputs
and approve/correct them. Invalid JSON does not erase partially correct semantic
content, but such output is rejected by Django rather than saved.
"""),
    nb.v4.new_code_cell("""for row in results.to_dict('records'):
    print('\\n' + '=' * 75)
    print(row['model_id'], row['input_id'], row['shot_mode'])
    print('Generation seconds:', row['generation_seconds'], 'Schema:', row['schema_valid'])
    print(row['raw_output'])
    print('Score:', row['quality_score_0_to_10'], 'Review:', row['review_notes'])"""),
    nb.v4.new_markdown_cell("""## Findings, limitations, and handoff

See the generated measured summary below, the full CSV, and revision metadata.
No results from unrun models are invented. The test has only two inputs and
greedy decoding; it cannot establish broad quality, production concurrency, or
the final team-wide size sweet spot. All generated tasks still require UI review.
"""),
    nb.v4.new_code_cell("""from IPython.display import Markdown, display
display(Markdown((ROOT / 'docs/a6-person-4/benchmark_summary.md').read_text(encoding='utf-8')))
print('P1 handoff:', 'a6_results/person4_benchmark_results.csv')"""),
    nb.v4.new_markdown_cell("""## Part 3 — local model vs paid API

The detailed estimate is linked below and also referenced in `docs/notes/notes.txt`.
Pricing is sourced and dated; token counts are workload assumptions, not paid API
measurements. The external provider remains Person 3's responsibility."""),
    nb.v4.new_code_cell("""display(Markdown((ROOT / 'docs/a6-person-4/local-vs-api.md').read_text(encoding='utf-8')))"""),
]
notebook = nb.v4.new_notebook(cells=cells, metadata={
    "kernelspec": {"display_name": "Python 3.11 (P4 benchmark)", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.11.15"},
})
destination = ROOT / "llm-test/ai_prototype.ipynb"
destination.parent.mkdir(exist_ok=True)
nb.write(notebook, destination)
print(destination)
