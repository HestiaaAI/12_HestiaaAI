"""Refresh Architecture lead notebook sections without executing expensive team experiments."""
from pathlib import Path
import nbformat as nbf
from a7.architecture_comparison import comparison_markdown

ROOT = Path(__file__).resolve().parents[1]


def md(text):
    cell = nbf.v4.new_markdown_cell(text)
    cell.metadata['architecture'] = True
    return cell


def code(text):
    cell = nbf.v4.new_code_cell(text)
    cell.metadata['architecture'] = True
    return cell


SETUP = '''from pathlib import Path
import sys
import pandas as pd
from IPython.display import display, Markdown
ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / 'a7/benchmark_contract.py').exists())
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
'''


def main():
    text = comparison_markdown(ROOT/'a7/architecture/inputs/slm_comparison.json',
                               ROOT/'a7/slm/results/selected_checkpoint.json')
    # Keep every Person 1 experiment and output; only replace our labeled sections.
    path = ROOT/'a7/multi_model_system.ipynb'
    notebook = nbf.read(path, as_version=4)
    notebook.cells = [c for c in notebook.cells if not c.metadata.get('architecture')]
    notebook.cells[0].source = ('# A7 — Multi-Model AI Systems\n\n'
        'Person 1 supplies the shared contract and SLM foundation. Architecture lead integrates '
        'the team evidence, architecture, costs and routing analysis. Original experiments '
        'are preserved below. Missing results are explicitly reported.')
    notebook.cells += [
        md('## Architecture lead — integrated evidence and coverage\n\n'
           'Successful, reviewed results are required for all 375 model/prompt pairs. '
           'A failed download is not an evaluated response. Timings from different '
           'machines are not directly comparable, even if both use the same device label.'),
        code(SETUP + '''from a7.architecture_analysis import write_analysis
data, coverage, models, categories, costs, cost_status = write_analysis(ROOT)
display(coverage)
print('Successful evaluations:', int(coverage.successful.sum()), '/ 375')
print('Scored successful evaluations:', int(coverage.scored.sum()), '/ 375')
display(models)
display(categories)
'''),
        md('### Step 1.6: performance analysis\n\n'
           'Category means are preliminary until each category has 75 successful reviewed '
           'evaluations. Determine whether larger models always win by checking matched '
           'prompts, not by assuming parameter count determines quality. The best '
           'speed/quality choice must satisfy the task quality threshold and be timed on '
           'the same hardware. The next cell shows available evidence without declaring '
           'a global speed winner.'),
        code('''if not models.empty:
    display(models.sort_values('mean_quality', ascending=False))
    display(data[data.status.eq('ok')].groupby(['model_id', 'prompt_type'])[
        'self_evaluation_score_1_to_10'].agg(['count', 'mean']))
if coverage.successful.sum() < 375 or coverage.scored.sum() < 375:
    print('PENDING: complete and manually review all team results before final conclusions.')
'''),
        code('''display(Markdown((ROOT/'a7/results/architecture/performance_findings.md').read_text(encoding='utf-8')))
from IPython.display import Image
display(Image(filename=str(ROOT/'a7/results/architecture/speed_quality_by_condition.png')))
tasks = pd.read_csv(ROOT/'a7/results/architecture/task_summary.csv')
display(tasks[tasks.meets_proposed_gate])
'''),
        md('## Architecture lead — Steps 2.5 and 3.1–3.3\n\n'
           'The full five-scenario design and cost methodology are in `system_design.md`. '
           'Both normalized 90-row team tables are integrated. The API comparison uses one '
           'comparable Llama-3.1-8B/Novita rate for all 15 local alternatives, without measured quality equivalence. '
           'Routing load simulations below use explicit planning assumptions, not measured '
           'traffic or inferred savings.'),
        code('''from a7.architecture_analysis import crossover_intervals, routing_simulation
print(cost_status)
if not costs.empty:
    display(costs)
    display(crossover_intervals(costs))
    display(costs.groupby(['model_id', 'cheaper']).daily_active_users.apply(list))
simulation = routing_simulation()
display(simulation)
'''),
        md('### Step 2.5: conditional API price thresholds\n\n'
           'Person 2 supplied 90 local-hosting estimates using one request/user/day, '
           '256 input and 500 output tokens. The paired API costs above include Person 3’s gateway estimates. '
           'As a separate sensitivity analysis, the next table computes the API price that would tie each '
           'local estimate assuming a zero-cost API gateway, an optimistic API bound. '
           'These are conditional thresholds, not paid API rates or observed DAU crossovers. '
           'For nonzero gateway cost A/day, subtract A from local daily cost before dividing '
           'by daily output tokens. The paired results show API cheaper in all 90 modeled cases; no crossover is observed.'),
        code('''frontier = pd.read_csv(ROOT/'a7/results/architecture/api_rate_frontier.csv')
display(frontier)
display(Image(filename=str(ROOT/'a7/results/architecture/api_rate_frontier.png')))
display(Markdown((ROOT/'a7/results/architecture/cost_analysis.md').read_text(encoding='utf-8')))
'''),
        code('''import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(8, 4))
for scenario, group in simulation.groupby('scenario'):
    ax.plot(group.daily_active_users, group.api_requests, marker='o', label=scenario)
ax.set(xscale='log', yscale='log', xlabel='Daily active users', ylabel='API requests/day',
       title='Illustrative routing load — assumed shares, not measured results')
ax.legend(fontsize=8)
fig.tight_layout()
plt.show()
'''),
        md('### Submission status\n\n'
           'Architecture lead benchmark: 75/75; team: 375/375. Llama-3.2 completed on an approved-account '
           'Colab T4/FP16 run; raw evidence and scoring reviews are preserved. Student signoff is recorded in `review_signoff.json`. '
           'Cost analysis and three-condition comparison are integrated. '
           'Assignment 2 Part 4 '
           'is in `slm/architecture_comparison.ipynb` and a Markdown section of the submitted '
           '`slm/slm_experiments.ipynb`. Checkpoints are excluded from submission.')]
    nbf.write(notebook, path)
    (ROOT/'a7/results/architecture/slm_comparison.md').write_text(text,encoding='utf-8')

    comparison = nbf.v4.new_notebook(cells=[
        md('# Assignment 2 — Architecture lead comparison\n\n'
           'This notebook checks the shared SLM and prepares Part 4 using Persons 2 and 3’s '
           'actual evidence. It does not invent questions, facts or model responses.'),
        code(SETUP),
        code('''import json
import torch
from a7.slm.handoff import load_selected, generate, state_hash
torch.set_num_threads(2)
manifest = json.loads((ROOT/'a7/slm/results/selected_checkpoint.json').read_text())
model, vocab = load_selected()
before = state_hash(model)
assert before == manifest['state_sha256']
sample = generate(model, vocab, 'students ', **manifest['generation'])
assert state_hash(model) == before
print('Original tensor state verified:', before)
print('Sample continuation (not an evaluation question):', repr(sample[len('students '):]))
print('Context length:', model.context_length, 'characters')
reproduction=ROOT/'a7/results/architecture/slm_reproduction_check.json'
if reproduction.exists():
    check=json.loads(reproduction.read_text(encoding='utf-8'))
    print('Independent exported-prompt matches:',check['matching_responses'],'/',check['total_responses'])
'''),
        md(text),
        md('## Comparison method and completed analysis\n\n'
           'Use the same five shared questions and generation settings: CPU, two threads, '
           'seed 42 per question, temperature 0.7, 100 new characters. Preserve exact prompts '
           'and show continuation-only responses. Score accuracy against document facts and '
           'relevance on a disclosed assistant-assessed 1–10 scale; record unsupported claims and '
           'consistency observations. Baseline/RAG weights must match the original hash; '
           'fine-tuned weights must differ. RAG context is the final 32 prompt characters.\n\n'
           'Baseline and RAG results are supplied by Person 2; fine-tuning results are supplied by Person 3. '
           'All five original baselines match exactly. Raw phrase-match scores are retained separately '
           'from continuation-level reviews because contradictory answers are not fully correct. Fine-tuning '
           'changes weights; RAG updates external knowledge. Retrieval supports changing '
           'policies without retraining, provided the model can use the retrieved context. '
           'RAG and fine-tuning can be combined, although that condition is not tested here. '
           'Single-seed runs cannot establish stability across random seeds.')],
        metadata={'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}})
    nbf.write(comparison, ROOT/'a7/slm/architecture_comparison.ipynb')
    # The brief requires Part 4 in one of the original three submitted notebooks.
    path = ROOT/'a7/slm/slm_experiments.ipynb'
    slm = nbf.read(path, as_version=4)
    slm.cells = [c for c in slm.cells if not c.metadata.get('architecture')]
    slm.cells.append(md(text))
    nbf.write(slm, path)
    gpu = nbf.v4.new_notebook(cells=[
        md('# Architecture lead — GPU benchmark continuation\n\n'
           'Use a Colab or Jupyter CUDA GPU runtime. Clone/open your team repository '
           'with your own GitHub access first and set its root as the working directory. '
           'Run all three assigned models on this common hardware/precision. '
           'The Windows float32 results remain separate exploratory evidence.'),
        code('''from pathlib import Path
import os, sys, subprocess
ROOT = Path.cwd()
assert (ROOT/'a7/benchmark_runner.py').exists(), 'Open the team repository root first.'
os.environ['HF_HOME'] = str(ROOT/'model_cache/huggingface')
subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', str(ROOT/'a7/requirements.txt')])
'''),
        md('Approve Llama access with your Hugging Face account, then use the login widget. '
           'Do not place a token in a code cell or share outputs containing credentials.'),
        code('''from huggingface_hub import notebook_login
notebook_login()
'''),
        code('''import json, platform, importlib.metadata
from datetime import datetime, timezone
import torch
assert torch.cuda.is_available(), 'Select a CUDA GPU runtime before benchmarking.'
from a7.benchmark_runner import run_matrix, select_models
out = ROOT/'a7/results/architecture_benchmark.csv'
assert not out.exists(), 'Use a clean GPU checkout, or remove this guard only to resume the SAME GPU/dtype run.'
environment = dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(),
    platform=platform.platform(), device='cuda', dtype='float16',
    gpu=torch.cuda.get_device_name(), vram_bytes=torch.cuda.get_device_properties(0).total_memory,
    max_new_tokens=220, do_sample=False,
    packages={p:importlib.metadata.version(p) for p in ['torch','transformers','huggingface-hub']})
out.parent.mkdir(parents=True,exist_ok=True)
out.with_name('architecture_benchmark_environment.json').write_text(json.dumps(environment,indent=2))
rows = run_matrix(select_models(owner='architecture'), out, device_request='cuda', dtype_request='float16')
print('Successful:',sum(r['status']=='ok' for r in rows),'/ 75')
'''),
        code('''from a7.review_results import review_csv
review_csv(out)
print('Review every raw response and score before submission.')
print('Return architecture_benchmark.csv and architecture_benchmark_environment.json to your local checkout.')
print('Preserve CPU evidence separately before replacing the canonical input file.')
''')], metadata={'kernelspec': {'display_name':'Python 3','language':'python','name':'python3'}})
    nbf.write(gpu, ROOT/'a7/architecture_gpu_benchmark.ipynb')
    print('Refreshed shared notebook, comparison notebook and submitted SLM Markdown section.')


if __name__ == '__main__':
    main()
