# Assignment 7 — experiments and submissions

Start with [SUBMISSION.md](SUBMISSION.md) for the five required deliverables,
requirement map, findings, limitations and upload instructions. The complete
matrix contains 375 successful scored results. Both 90-row cost tables and the
class SLM/RAG/fine-tuning comparison are included. [REVIEW_STATUS.md](REVIEW_STATUS.md)
records the owner-specific assessment evidence. Build the upload ZIP with
`python -m a7.package_submission` from the repository root.

This folder is independent of the Django application. It contains the locked
experiment contract for both Assignment 7 submissions.

## Person 1 completed foundation

- `benchmark_contract.py`: the exact 15 A6 models, five fixed size categories,
  a balanced 4/4/4/3 member allocation, 25 Hestia prompts, and the 10-point
  manual evaluation rubric.
- `benchmark_runner.py`: deterministic local/Colab runner that records latency,
  output tokens, tokens per second, raw output, environment, and review fields.
- `review_results.py`: reproducible first-pass self-evaluation using the shared
  ten-point rubric. The review notes make each score auditable.
- `multi_model_system.ipynb`: shared notebook scaffold and Person 1 execution
  section. Other members should return CSV files rather than edit this notebook.
- `model_registry.csv`, `prompts.csv`, and `evaluation_rubric.csv`: reviewable
  copies of the shared contract.
- `tests/`: guards against roster, prompt, allocation, and result-schema drift.

Person 1 models are distributed across four size categories:

1. `distilbert/distilgpt2`
2. `HuggingFaceTB/SmolLM2-360M-Instruct`
3. `Qwen/Qwen2.5-1.5B-Instruct`
4. `microsoft/Phi-3.5-mini-instruct`

## Run Person 1's 100 evaluations

Use one machine for all four models so latency and throughput remain comparable.
A CUDA Colab runtime is recommended for Phi-3.5. Do not combine timings collected
on different hardware without labeling them separately.

```powershell
python -m pip install -r a7/requirements.txt
python -m a7.benchmark_runner --owner P1 --dry-run
python -m a7.benchmark_runner --owner P1 --device cuda \
  --output a7/results/person1_benchmark.csv
```

The runner checkpoints after every generation and resumes by default. After all
generations finish, populate the rubric fields and then inspect the raw output
beside every score:

```powershell
python -m a7.review_results a7/results/person1_benchmark.csv
```

**Person 1 correction notice:** `results/person1_benchmark.csv` now contains authorized
AI-assisted semantic corrections. Original scores and all 100 assessments are
preserved in `person1/review/`. Do not run the first-pass reviewer above over this
corrected CSV: it would overwrite the inspected scores. Personal student signoff
and consistent scoring conventions across owners remain separate checks.

The reviewer checks exact labels, required JSON shape, task-specific concept
coverage, clarity, and unsupported details. Its notes explain each score; Person
1 must still review those notes before treating the CSV as final. Keep failed
generations visible and rerun them under the same configuration.

## Assignment 2: Person 1 SLM completed

The supplied class notebook is preserved at `slm/class_source.ipynb`.
`slm/slm_experiments.ipynb` contains executed baseline results, five architecture
experiments, four temperatures, comparison tables and all six analysis answers.
Every architecture runs the class's extended 1,000-step preset with the same
corpus, batch size, learning rate, CPU device and seeds. The class Transformer
architecture is unchanged.

`slm/results/` contains the measured tables and selected checkpoint manifest.
The original baseline is selected for Parts 2–4. Follow `slm/HANDOFF.md` to share
and verify the exact checkpoint with Persons 2 and 3. Weights are local only and
excluded by Git; the PR contains no training checkpoints.

## Team handoff rules

- Everyone uses these exact model IDs, prompts, output instructions, and rubric.
- Each member runs only the models assigned to their `owner` value.
- Do not edit another member's raw evidence.
- Return one CSV with all 25 rows per model and no duplicate model/prompt keys.
- Person 2 and Person 3 supply their respective 90-row cost tables
  across all 15 models, regardless of their four-model benchmark allocations.
- Architecture lead integrates the four reviewed CSV files into the final notebook.
- Architecture lead owns the five routing strategies and `system_design.md`.

## Architecture lead integration

See `architecture/README.md` for run commands and the fulfilled teammate input contracts.
`architecture_analysis.py` validates and summarizes available evidence without filling
missing costs or responses. `system_design.md` contains five Hestia routing
scenarios and the local/API comparison methodology. `slm/architecture_comparison.ipynb`
verifies the original checkpoint and prepares the three-condition comparison;
the comparison Markdown is also included in the submitted SLM notebook.

The completed integration includes 375 successful, scored evaluations across all
15 original A6 models. The last 25 Llama-3.2 prompts completed on an approved-account
Colab T4/FP16 run; its raw evidence, executed notebook and import checks are retained.
Both 90-row cost tables and all five baseline/RAG/fine-tuned comparisons are
integrated. See `architecture/STATUS.md` for remaining student assessment checks,
`results/architecture/performance_findings.md` for condition-separated findings,
and `results/architecture/cost_analysis.md` for paired API/local scenarios.
The original 25 SLM baseline/RAG continuations were independently reproduced
exactly without changing weights. Fine-tuning reproduction and its platform
limitations are documented separately; model weights remain excluded.
