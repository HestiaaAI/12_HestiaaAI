# Architecture and final comparison — submission status

## Completed

- Five Hestia routing scenarios with routing conditions, candidate model roles,
  latency/cost/quality reasoning, overload handling and output validation.
- `system_design.md` with architecture, cost methodology and preliminary findings.
- Thirty illustrative routing-load simulation rows: five scenarios × six traffic levels.
- SmolLM-360M: 25 successful CPU/float32 benchmark evaluations.
- TinyLlama-1.1B: 25 successful Colab Tesla T4/float16 evaluations, imported and reviewed.
- Fifty response-level rubric reviews with output-hash evidence; student signoff pending.
- Shared SLM checkpoint verified against the selected tensor-state hash.
- Notebook integration and SLM comparison workflow prepared; missing inputs are explicit.
- Descriptive artifact names and `architecture` owner label replace the old member-number labels.

## Pending work assigned to the architecture lead

| Required work | What is still needed | Dependency |
|---|---|---|
| Third model benchmark | Run all 25 prompts on Llama-3.2-3B and inspect scores. Current benchmark completion is 50/75. | Last checked: model-author access approval pending. A GPU runtime is preferable because local loading hit memory limits. |
| Step 1.6: complete performance analysis | Final best category, larger-versus-smaller comparison and speed/quality recommendation using all 15 models. Existing findings cover only available results. | All four reviewed benchmark CSVs: 375 successful evaluations total. Currently 150 are available: 100 from Person 1 and 50 from the architecture allocation. |
| Step 2.5: local/API crossover analysis | Calculate cheaper options at six traffic levels, bracket all observed crossovers and explain when to switch architecture. | Person 2's 90 local-cost rows and Person 3's 90 API-cost rows with reconciled workload and pricing assumptions. |
| Final routing recommendations | Replace provisional model/provider roles and assumed thresholds with conclusions supported by the completed benchmark/cost evidence. | Full benchmark results and the comparable paid API model/rates. The five strategy designs themselves are drafted. |
| Assignment 2 Part 4 comparison | Fill the five-question baseline/RAG/fine-tuned table, compare factual accuracy, relevance, consistency and unsupported claims, and answer the five final-analysis questions. | Person 2's five shared questions, expected facts, baseline and 20 RAG outputs; Person 3's matching baseline, five fine-tuned outputs and weight-change evidence. |
| Final submission integration | Refresh both assignment notebooks and the design document, remove pending placeholders and perform final execution/reproducibility review. | The missing evidence above. Current checks validate the available work, not a completed submission. |

## Handoffs to request

Person 2: reviewed four-model benchmark CSV, local hosting cost table, knowledge
documents, five shared questions with expected facts, baseline responses and all
Top-K 1/2/3/5 RAG responses, including visible context and unchanged-weight proof.

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
