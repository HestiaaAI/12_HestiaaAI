# Architecture and final comparison — October 25, 2026

Current branch: `devcrn-P4`, updated with main's merged Person 2 contribution.
All tasks supported by currently available evidence are integrated. A complete
submission still depends on the external inputs listed below.

## Completed

- Five Hestia routing scenarios with routing conditions, candidate model roles,
  latency/cost/quality reasoning, overload handling and output validation.
- `system_design.md` with architecture, cost methodology and preliminary findings.
- Thirty illustrative routing-load simulation rows: five scenarios × six traffic levels.
- SmolLM-360M: 25 successful CPU/float32 benchmark evaluations.
- TinyLlama-1.1B: 25 successful Colab Tesla T4/float16 evaluations, imported and reviewed.
- Fifty response-level rubric reviews with output-hash evidence; student signoff pending.
- Integrated 250/375 successful, scored team evaluations across 10/15 models:
  Person 1 contributes 100, Person 2 contributes 100, and your allocation contributes 50.
- Step 1.6 findings, category completeness, matched-prompt size counterexamples,
  condition-separated speed/quality figures and actual task-level routing candidates.
- All 90 local hosting estimates and 90 conditional API price thresholds are integrated.
  The thresholds are not invented paid API rates or observed DAU crossover points.
- The five shared questions, five baseline outputs and twenty RAG outputs are
  integrated into the submitted SLM notebook's Part 4 Markdown section. Both
  available conditions score 1/10; lower-K tie selection chooses K=1.
- Independently reproduced all 25 exported baseline/RAG continuations exactly
  from the selected checkpoint, with unchanged weights. Source-file hashes match
  after documented Windows Git line-ending normalization.
- All 33 assignment tests pass; analysis notebooks are executed with the available evidence.
- Shared SLM checkpoint verified against the selected tensor-state hash.
- Notebook integration and SLM comparison workflow prepared; missing inputs are explicit.
- Descriptive artifact names and `architecture` owner label replace the old member-number labels.

## Pending work assigned to the architecture lead

| Required work | What is still needed | Dependency |
|---|---|---|
| Third model benchmark | Run all 25 prompts on Llama-3.2-3B and inspect scores. Current benchmark completion is 50/75. | Last checked: model-author access approval pending. A GPU runtime is preferable because local loading hit memory limits. |
| Step 1.6: final all-model performance analysis | Available 250-row findings are complete; the final category ranking needs the missing 125 evaluations. | Person 3's 100 benchmark rows plus your last 25 Llama rows. |
| Step 2.5: actual local/API crossover analysis | Local estimates and 90 conditional price thresholds are complete; actual cheaper options and crossover intervals need paid API data. | Person 3's 90 API rows with compatible provider/model, rates, gateway costs and workload scope. Person 2's local costs are integrated. |
| Final routing recommendations | Actual qualified task candidates are documented. Finish API route selection and validate any new model candidates when their evidence arrives. | Missing model benchmarks and comparable paid API model/rates. The five strategy designs are complete for the available evidence. |
| Assignment 2 Part 4 comparison | Baseline/RAG table, context analysis and available answers are filled. Complete the fine-tuned column and three-condition accuracy answer. | Person 3's matching pre-training baseline, five fine-tuned responses and training/weight-change evidence. |
| Final submission integration | Refresh both assignment notebooks and the design document, remove pending placeholders and perform final execution/reproducibility review. | The missing evidence above. Current checks validate the available work, not a completed submission. |

## Handoffs to request

Person 2's benchmark, local-cost and RAG handoffs are received and integrated.

Person 3: reviewed four-model benchmark CSV, API cost table with rates/sources or
explicit assumptions, pre-fine-tuning baseline, five post-fine-tuning responses,
generation settings and training/weight-change evidence.

No additional SLM training, RAG implementation or fine-tuning implementation is
assigned to the architecture lead. The responsibility is to compare and integrate
those teammates' actual results.

## Naming and provenance

The rename changes labels and artifact paths only. `source_label_migration.json`
records source hashes before and after the rename; model IDs, prompts, output
instructions and rubric were verified unchanged. The executed Colab notebook
contains a migration note, and recorded original source hashes remain available
in its environment evidence. Historical outputs do not represent a new run.
