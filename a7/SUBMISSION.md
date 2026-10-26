# Assignment 7 submission guide

Team 12 — Hestia AI. Updated October 26, 2026.

## What to submit and read first

| Assignment | Required deliverable | What it contains |
|---|---|---|
| Multi-model systems | [multi_model_system.ipynb](multi_model_system.ipynb) | Registry, 25 prompts, rubric, 375 benchmark results, cost comparisons and scaling simulations |
| Multi-model systems | [system_design.md](system_design.md) | Performance findings, local/API analysis and five routing strategies with latency/cost/quality reasoning |
| SLM/RAG/fine-tuning | [slm/slm_experiments.ipynb](slm/slm_experiments.ipynb) | Original class SLM, five independent architecture runs, four temperatures, Part 1 analysis and Part 4 three-condition comparison |
| SLM/RAG/fine-tuning | [slm/person2_rag_colab.ipynb](slm/person2_rag_colab.ipynb) | Five documents/questions, baseline, K=1/2/3/5 retrieval, 20 responses, scored tables and five analysis answers |
| SLM/RAG/fine-tuning | [person3/finetune_slm.ipynb](person3/finetune_slm.ipynb) | Ten examples, five matching pre-training responses, configuration/loss/time, changed-weight evidence, after responses and analysis |

The optional [API cost notebook](person3/api_costs.ipynb) and
[comparison notebook](slm/architecture_comparison.ipynb) explain supporting results.
The Part 4 comparison is already inside the required SLM notebook; it is not
dependent on submitting the optional notebook.

Keep the `a7/` folder structure intact: notebooks import Python modules and read
CSV/JSON files by relative path. Upload the required files and supporting folder
as permitted by the course portal. Do not upload the entire Django repository or
an isolated notebook without its dependencies.

## Requirement map and evidence

| Requirement | Evidence |
|---|---|
| Same 15 A6 models, three per size bin | `model_registry.csv`, `benchmark_contract.py` |
| Five prompt types, five prompts each | `prompts.csv`, `evaluation_rubric.csv` |
| Every model on every prompt | `results/person1_benchmark.csv`, `person2_benchmark.csv`, `person3_benchmark.csv`, `architecture_benchmark.csv`; 375 unique successful scored pairs |
| Six traffic levels and token assumptions | `person2/cost_assumptions.json`, `results/person2_daily_token_loads.csv` |
| Local and API costs: 90 rows each | `results/local_costs.csv`, `results/api_costs.csv` |
| Cost crossover and routing analysis | `results/architecture/cost_analysis.md`, `cost_comparison.csv`, `routing_simulation.csv`, `system_design.md` |
| Class architecture and independent training | `slm/class_source.ipynb`, `slm/class_model.py`, `slm/results/baseline.csv`, `architecture.csv`, `temperatures.csv` |
| RAG pipeline and actual continuations | `slm/class_rag_source.ipynb`, `slm/rag_experiment.py`, `slm/knowledge_base/`, `slm/results/person2_rag_colab/` |
| Fine-tuning procedure and saved experiment | `person3/finetune_slm.py`, `person3/results/finetune_results.json` |
| Shared original checkpoint lineage | `slm/results/selected_checkpoint.json`, `slm/HANDOFF.md`, `architecture/inputs/slm_comparison.json` |
| Review methods and original ratings | `REVIEW_STATUS.md`, `person1/review/`, `person2/review/`, `architecture/*review*.json` |

## Findings and limits to retain

- The completed benchmark has 375 responses, 15 models and five 75-row categories.
  The highest observed category mean is Large, **7.48/10** after score corrections.
  A6's actual size bins are retained; the assignment's example ranges are not
  mandatory labels. No 7B model is described as a 30B model.
- Hardware and precision differ: CPU/FP32, Apple MPS, T4/FP16, T4/NF4 and MLX/4bit.
  Report condition-specific speed/quality choices rather than a global speed winner.
- API costs are lower in all 90 supplied scenarios; no crossover is observed at
  the six sampled loads. All local choices are compared with the same external
  Llama-3.1-8B/Novita service to hold that alternative's rate constant. It performs
  the same intended instruction tasks, but equal quality is not measured. This is
  a common-service cost scenario, not 15 exact-model offers or a size-matched API
  benchmark. Rates are the supplied dated assumptions, not a fresh deployment quote.
- Local fleet capacity uses four T4 anchors and eleven size proxies, transferred
  to RTX3090 without validation. Gateway capacity is assumed. Both sides exclude
  the common application baseline and documented operational costs.
- Baseline and RAG fail to answer the five household facts (accuracy 1/10).
  Fine-tuning has mean reviewed accuracy 2.4/10 but no fully correct,
  contradiction-free answer. Negative results are preserved honestly.
- The selected SLM sees only the last 32 characters. RAG uses unchanged weights;
  fine-tuning starts from the same original state and changes it. All five
  pre-training continuations match the baseline exactly.
- Fine-tuning examples include the evaluation questions. This is in-sample evidence,
  not held-out generalization. Local retraining matches 4/5 continuations; the
  changed final hash and Q4 platform difference are disclosed in the reproduction report.

## Read saved outputs or reproduce analysis

No keys, Hugging Face approval, weights or Django server are needed to read the
saved notebooks and data. The saved API/fine-tuning notebooks display exported
experiments; viewing them does not initiate paid requests or new training.

From the repository root, install the A7 environment:

```sh
python -m pip install -r a7/requirements.txt -r a7/requirements-person2-rag.txt
python -m unittest discover -s a7/tests -q
python -m a7.architecture_analysis
```

On low-memory Windows machines, set `OPENBLAS_NUM_THREADS`, `OMP_NUM_THREADS` and
`MKL_NUM_THREADS` to `1` before launching Python (see the root README). Import
checks now explicitly read UTF-8 and accept documented Git CRLF/LF conversion
without accepting substantive response changes.

To refresh the two integration notebooks, place the exact original checkpoint
privately as described in `slm/HANDOFF.md`, then run:

```sh
python -m a7.architecture_integrate_peers
python -m a7.architecture_build_notebooks
python -m a7.architecture_execute
```

This executes analysis plus tiny checkpoint verification, not the 15-model matrix
or SLM architecture training. For full training reproduction, use the class SLM
notebook from working directory `a7/slm`; run the fine-tuning display notebook
from the repository root. The RAG notebook is a Colab upload workflow; its saved
outputs and final tables are included. Its code bundle must retain the same `a7/`
source paths. Alternatively, reproduce RAG locally into a new evidence directory:

```sh
python -m a7.slm.rag_experiment --output-dir a7/slm/results/rag_reproduction
```

That command requires the private original checkpoint, performs generation and
leaves the submitted original run intact. Review any new outputs before scoring;
do not blindly apply the frozen ratings to changed continuations. Detailed
generation environments remain beside the original exports.

## Build a clean upload bundle

```sh
python -m a7.package_submission
```

This writes `dist/hestia-a7-submission.zip` and a SHA256 checksum file. The ZIP
opens with `README.md` (this guide), `MANIFEST.json` and the supporting `a7/`
tree. The manifest lists the primary deliverables and exact file checksums.
Checkpoints, weight files, virtual environments, caches, local backup attempts,
credentials, unexecuted continuation scaffolds and unrelated assignments are
excluded. The packaging command refuses missing/errored required notebooks,
incomplete benchmark/cost tables and common credential patterns.

The generated ZIP is ignored by Git. Rebuild it after final source changes.
All saved ratings remain disclosed AI-assisted self-evaluations; see
`REVIEW_STATUS.md` for owner-specific review evidence.

## Verification on October 26, 2026

- All **42 A7 tests pass** on Windows with the normal default text encoding, including from the extracted submission ZIP without a private checkpoint.
- All 375 benchmark pairs and both 90-row cost tables validate; saved summaries agree with source data.
- Required notebooks have saved execution counts and no saved errors.
- The two integration notebooks were re-executed successfully; no large-model inference or original training results were replaced.
- Submission ZIP integrity and per-file checksums are checked by the packaging command.
