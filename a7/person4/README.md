# Person 4 work and remaining handoffs

Run from the repository root with `.venv/Scripts/python.exe` on Windows.

```powershell
python -m a7.person4_run
python -m a7.review_results a7/results/person4_benchmark.csv
python -m a7.person4_review
python -m a7.person4_analysis
python -m a7.person4_execute
python -m unittest discover -s a7/tests -v
```

`person4_run` resumes the shared benchmark with four CPU threads and float32.
It records an environment sidecar. Keep one environment for all three models.
Downloaded weights stay in ignored `model_cache/`. Llama-3.2-3B needs an approved
account and local Hugging Face authentication; never put credentials in notebooks.
Review every successful response and score after the automated first pass. Error
rows are not completed model evaluations. Do not replace the gated model silently.
`person4_review` records assistant-inspected corrections for the observed float32
SmolLM outputs and verifies response hashes before applying them. Student signoff
is still pending. It will reject changed responses; inspect those before reusing
the old scores. Other models initially receive the shared automated first pass.

Local outcome: 25/75 successful float32 evaluations. TinyLlama hit Windows
paging-file error 1455; Llama returned gated repository HTTP 401. The float16 trial
was stopped at high RAM utilization; it remains a separate partial experiment.
Use `../person4_gpu_benchmark.ipynb` for a common GPU/float16 run after Llama access
is approved. Preserve CPU evidence before importing a completed GPU result file.

A separate `person4_float16_benchmark.csv` run tests lower memory usage after the
float32 TinyLlama load failed with Windows paging-file error 1455. Keep these
precision conditions separate; do not silently mix their timings. The default
analysis currently uses `person4_benchmark.csv` (float32). Promote a different run
only after labeling its environment, preserving the earlier evidence, and reviewing
the new responses.

Open `multi_model_system.ipynb` for combined Assignment 1 analysis and
`slm/person4_comparison.ipynb` for Assignment 2. Notebook execution does not launch
downloads or retrain the shared SLM. The SLM comparison is also included in the
submitted `slm/slm_experiments.ipynb` as a Markdown section, to satisfy the brief.
After new teammate evidence arrives, run `python -m a7.person4_build_notebooks`
to refresh Markdown comparison cells, then execute the notebooks again.

## Person 2 / Person 3 cost contract

Preserve original cost tables. Provide normalized `a7/results/local_costs.csv`
and `a7/results/api_costs.csv`, each with 90 rows (15 models × six traffic levels).
Required columns:

```text
model_id,traffic_category,daily_active_users,requests_per_user,input_tokens_per_request,output_tokens_per_request,total_daily_cost_usd,assumptions_id,source_or_assumption
```

Use registry model IDs and the six exact traffic labels from `person4_analysis.TRAFFIC`.
Total cost includes the appropriate local/API infrastructure and inference cost.
Use common `assumptions_id` values to identify the same workload, inclusion rules
and currency/day basis. `source_or_assumption` records price source/date or clearly
states an assumed rate. Additional columns are welcome: paid model, machine type,
replicas, GPU count, utilization, capacity, token rates and itemized costs. The
normalization is for joining the two tables, not a replacement for the required
itemized assignment tables. No real prices or crossover results have been invented.

## Person 2 / Person 3 SLM comparison contract

Provide `a7/person4/inputs/slm_comparison.json` with these keys:

- `original_state_sha256`: selected manifest tensor hash.
- `generation`: exactly `{"seed":42,"temperature":0.7,"max_new_tokens":100,"device":"cpu","threads":2}`.
- `questions`: exactly five entries, each with `question_id`, `question`,
  `expected_facts` (list), `source_document_ids` (list), `baseline`, `rag`, `fine_tuned`.
- `baseline` and `fine_tuned` are response objects. `rag` is a list of four response
  objects with `top_k` equal to 1, 2, 3 and 5.
- Every response object contains `prompt` (exact string passed to generate),
  `response` (continuation only, including empty text if actually generated),
  `state_sha256`, `factual_accuracy` and `relevance` (human-reviewed 1–10 scores),
  `unsupported_information` (boolean), and `review_notes` (evidence-backed text).
- Each RAG object additionally contains `retrieved_document_ids` (length Top-K),
  `visible_context` (exact final 32 prompt characters). Preserve all underlying
  knowledge documents and retrieval results in Person 2's notebook.

Normalize questions/prompts only with an explicit shared rule and record it in
the submitted notebooks. Original vocabulary excludes q, z, uppercase, digits,
question marks and colons. Do not silently change questions or expand embeddings.
Provide Person 3's pre-fine-tuning baseline for a separate equality check against
Person 2's baseline before filling this combined file. Also retain training loss,
time/configuration and changed-weight evidence in Person 3's notebook.

Part 4 uses highest mean factual accuracy to select K; lower K breaks ties. This
uses the evaluation set for selection and must be disclosed. It preserves all
four K results in the source data and does not imply unseen-question accuracy.
No completed comparison can be produced before the five shared questions arrive.

## Integration checklist

- [ ] P1–P4: 375 successful rows; all scores reviewed, model/prompt keys unique.
- [ ] Hardware labeled; no fastest-model conclusion across different machines.
- [ ] Person 2: local 90-row itemized costs and assumptions.
- [ ] Person 3: API 90-row itemized costs and assumptions.
- [ ] Person 2: five questions, facts, baseline and 20 RAG outputs.
- [ ] Person 3: matching original baseline, five fine-tuned outputs and changed weights.
- [ ] Refresh comparison Markdown and write empirical conclusions in system_design.md.
- [ ] Execute final notebooks, check outputs and remove pending placeholders.
- [ ] Keep checkpoints and model caches out of Git and submission.

Known rubric issue: Person 1 retained A6's five size bins (all ≤7.62B), rather than
the illustrative <1B/1–3B/3–7B/7–30B/30B+ bins. The brief calls those ranges an
example and requires the same A6 models with three/category. Preserve the shared
registry and state the actual ranges; do not relabel a 7B model as 30B+.
