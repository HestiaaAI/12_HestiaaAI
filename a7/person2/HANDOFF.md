# Person 2 handoff — October 24, 2026

## What is supplied

- `a7/person2_analysis.ipynb`: executed benchmark review, all 100 required benchmark rows, all 90 cost rows, token-load table, capacity assumptions, formulas, charts, findings and limitations. No new inference during analysis execution.
- `a7/person2_benchmark_colab.ipynb`: original user-executed GPU notebook.
- `a7/results/person2_nf4_colab/`: untouched raw 100-row CSV, environment and import verification.
- `a7/results/person2_benchmark.csv`: canonical 100-row assessed matrix for the architecture lead's existing importer. Mean assisted scores: OPT 1.08, Qwen 5.20, SmolLM2 4.96, Mistral 8.12. These are this owner's four-model slice, not a 15-model ranking.
- `a7/person2/review/benchmark_review_audit.json`: per-response hashes, individual component scores, policy and concrete observations. Scoring is AI-assisted; student signoff pending. This is not a human-reviewed certification.
- `a7/results/local_costs.csv`: 90 itemized inference-tier estimates, existing normalized columns plus CPU/RAM/GPU, capacity provenance, machine rounding and compute/storage components.
- `a7/results/person2_capacity_assumptions.csv`: four measured T4 anchor rates and eleven assumed size-based rate proxies. All RTX 3090 rates are unvalidated transfers, not measurements.
- `a7/results/person2_local_cost_sensitivity.csv`: 270 assumed half/base/double-throughput cases.
- `a7/results/person2_daily_token_loads.csv`, `person2_model_summary.csv`, `local_costs.provenance.json` and `person2_figures/`: supporting evidence.
- `a7/slm/person2_rag_colab.ipynb`: user-executed class SLM RAG experiment with five baseline and twenty RAG responses and the five required analysis answers.
- `a7/slm/results/person2_rag_colab/`: raw baseline/RAG CSV/JSON, reviewed JSON and validation record. No grounded household answers were produced; scores stay 1/10. Original/final reported checkpoint hashes match.
- `a7/slm/knowledge_base/`: shared five documents, questions, facts and source IDs. The original checkpoint and all model weights remain excluded from Git/package.

## For Person 3

Use the unchanged original checkpoint, same vocabulary/model, exact exported baseline prompts, five shared questions and CPU threads=2, seed=42, temperature=0.7, 100 character-token generation settings. Exported RAG environment: Python 3.13.16, torch 2.11.0+cpu, numpy 2.1.3, scikit-learn 1.6.1, pandas 2.2.3. Compare your pre-fine-tuning baselines before claiming matched conditions. Zero-score retrieval ties can reorder documents across NumPy/scikit-learn versions; retain the exported document order/full prompts for comparisons. Do not change the selected architecture to conceal poor RAG performance.

For API economics use the same inference-tier scope and `hestia-a7-256in-500out-r1-inference-only-v1`: one request/user/day, 256 input and 500 output tokens. These are explicit future workload assumptions, not observed token lengths. Local includes 24h Pods and per-replica disks plus co-hosted thin handlers. API must include its own required gateway compute/storage. Both sides exclude the common Django/frontend/database baseline, egress, tax, labor, monitoring, redundancy etc. If you choose a different workload or inclusion scope, regenerate both tables and change the shared assumptions ID; do not just rename IDs on incompatible totals.

## For Person 4

Read `a7/results/person2_benchmark.csv` via the existing `benchmark_evidence` path. The timing environment is **Tesla T4 / NF4 / FP32 compute / eager / batch 1 / greedy / cap 220**; retain that label and do not compare it as native FP32 CPU or another GPU's speed. `a7/results/local_costs.csv` is ready for the existing normalized join once Person 3 supplies compatible API rows. No supported crossover result exists without those inputs.

The local scenario uses the official advertised RTX 3090 listing ($0.50/hour, 24 GB VRAM, 16 vCPU, 125 GB RAM), 20 GB container + 80 GB running volume at $0.10/GB/month, checked October 24. See [pricing](https://www.runpod.io/pricing) and [billing](https://docs.runpod.io/pods/pricing). Costs are alternatives for one model at a time; do not add all 15 as the default app fleet. Public inventory/region is not guaranteed. The 100-million-DAU fleet counts assume ideal distribution and do not establish procurement feasibility or queue-latency SLA.

Use `person2_rag_reviewed.json` as the baseline/RAG portion of the SLM comparison, retaining the assistant-review disclosure. Person 3's five fine-tuned outputs and unchanged pre-training baseline check are still needed before constructing the final three-condition comparison. All RAG K scores tie at 1; the specified lower-K tie rule selects K=1 but does not imply quality improvement.

## Rebuild and checks

From the repository root:

```sh
python -m a7.person2.review_benchmarks
python -m a7.person2.local_costs
python -m unittest discover -s a7/tests -v
```

Execute `a7/person2_analysis.ipynb` using the project environment to regenerate its analysis outputs/figures. It performs no model inference. Do not rerun the Colab generation cells merely to refresh tables.
