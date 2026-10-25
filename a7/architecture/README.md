# Architecture lead work and remaining handoffs

Run from the repository root with `.venv/Scripts/python.exe` on Windows.

```powershell
python -m a7.architecture_run
python -m a7.review_results a7/results/architecture_benchmark.csv
python -m a7.architecture_review
python -m a7.architecture_analysis
python -m a7.architecture_verify_handoff
python -m a7.architecture_execute
python -m unittest discover -s a7/tests -v
```

`architecture_run` resumes the shared benchmark with four CPU threads and float32.
It records an environment sidecar. Keep one environment for all three models.
Downloaded weights stay in ignored `model_cache/`. Llama-3.2-3B needs an approved
account and local Hugging Face authentication; never put credentials in notebooks.
Review every successful response and score after the automated first pass. Error
rows are not completed model evaluations. Do not replace the gated model silently.
`architecture_review` records assistant-inspected corrections for the observed float32
SmolLM outputs and verifies response hashes before applying them. Student signoff
is still pending. It will reject changed responses; inspect those before reusing
the old scores. Other models initially receive the shared automated first pass.

Initial local outcome: 25/75 successful float32 evaluations; TinyLlama later completed on Colab (50/75 current). TinyLlama hit Windows
paging-file error 1455; Llama returned gated repository HTTP 401. The float16 trial
was stopped at high RAM utilization; it remains a separate partial experiment.
Use `../architecture_gpu_benchmark.ipynb` for a common GPU/float16 run after Llama access
is approved. Preserve CPU evidence before importing a completed GPU result file.

## TinyLlama Colab continuation

`../architecture_tinyllama_colab.ipynb` is self-contained and embeds the exact shared
contract, runner and reviewer with SHA256 checks. It runs only TinyLlama's 25
prompts on CUDA/float16 and exports a ZIP containing the raw CSV and environment.
No Hugging Face login is needed for TinyLlama. The current Colab notebook is:
https://colab.research.google.com/drive/1rawE_2ImgxBE7cFPceUv9ke7Dg7mughx

Import the downloaded ZIP with:

```powershell
python -m a7.architecture_import_colab "C:/path/to/architecture_tinyllama_cuda_results.zip"
```

The importer validates all 25 keys, successful CUDA status and source hashes,
archives the older CPU table, and replaces only TinyLlama rows in the canonical
Architecture lead matrix. CPU and GPU environment evidence stays separate. Automated
scores require response-level inspection before treating them as final.
TinyLlama completed 25/25 evaluations on Colab Tesla T4/float16; the canonical
Architecture lead table now has 50/75 successful rows. The original CPU attempt table,
raw GPU CSV, environment, executed Colab notebook and score-review hashes are
preserved. CUDA and CPU timings are not directly comparable. Mean inspected
TinyLlama score is 2.96/10, so successful inference does not establish usable
structured-output quality. The latest local Llama check reports the author's
access review is still pending.

A separate `architecture_float16_benchmark.csv` run tests lower memory usage after the
float32 TinyLlama load failed with Windows paging-file error 1455. Keep these
precision conditions separate; do not silently mix their timings. The default
analysis currently uses `architecture_benchmark.csv`, which combines labeled CPU
SmolLM and CUDA TinyLlama evidence. Promote a different run
only after labeling its environment, preserving the earlier evidence, and reviewing
the new responses.

Open `multi_model_system.ipynb` for combined Assignment 1 analysis and
`slm/architecture_comparison.ipynb` for Assignment 2. Notebook execution does not launch
downloads or retrain the shared SLM. The SLM comparison is also included in the
submitted `slm/slm_experiments.ipynb` as a Markdown section, to satisfy the brief.
After new teammate evidence arrives, run `python -m a7.architecture_build_notebooks`
to refresh Markdown comparison cells, then execute the notebooks again.

## Person 2 / Person 3 cost contract

Preserve original cost tables. Provide normalized `a7/results/local_costs.csv`
and `a7/results/api_costs.csv`, each with 90 rows (15 models × six traffic levels).
Required columns:

```text
model_id,traffic_category,daily_active_users,requests_per_user,input_tokens_per_request,output_tokens_per_request,total_daily_cost_usd,assumptions_id,source_or_assumption
```

Use registry model IDs and the six exact traffic labels from `architecture_analysis.TRAFFIC`.
Total cost includes the appropriate local/API infrastructure and inference cost.
Use common `assumptions_id` values to identify the same workload, inclusion rules
and currency/day basis. `source_or_assumption` records price source/date or clearly
states an assumed rate. Additional columns are welcome: paid model, machine type,
replicas, GPU count, utilization, capacity, token rates and itemized costs. The
normalization is for joining the two tables, not a replacement for the required
itemized assignment tables. No real prices or crossover results have been invented.

## Person 2 / Person 3 SLM comparison contract

Provide `a7/architecture/inputs/slm_comparison.json` with these keys:

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
The five questions and baseline/RAG evidence are now available and auto-loaded
from Person 2's reviewed export when the complete three-condition input file is
absent. The complete three-condition input is now generated from both peers by `python -m a7.architecture_integrate_peers`. Raw automatic scores are retained separately from continuation-level reviews.

## Integration checklist

- [ ] Full team: 375 successful rows; all scores reviewed, model/prompt keys unique.
- [x] Hardware and quantization labeled; no cross-condition fastest-model claim.
- [x] Person 2: local 90-row itemized costs and assumptions.
- [x] Person 3: API 90-row itemized costs and assumptions.
- [x] Person 2: five questions, facts, baseline and 20 RAG outputs.
- [x] Person 3: matching original baseline, five fine-tuned outputs and changed-weight evidence.
- [x] Refresh comparison Markdown and write empirical conclusions in system_design.md.
- [x] Execute integration notebooks and remove obsolete teammate-input placeholders. The gated-model blocker remains explicit.
- [x] Keep checkpoints and model caches out of Git and submission.

See `STATUS.md` for current completion and external blockers. Paired local/API comparisons now use both 90-row tables. Conditional API price thresholds remain a separate zero-gateway sensitivity analysis. Available benchmark analysis is
split by measured hardware/precision condition, including the T4/NF4 results.

Known rubric issue: Person 1 retained A6's five size bins (all ≤7.62B), rather than
the illustrative <1B/1–3B/3–7B/7–30B/30B+ bins. The brief calls those ranges an
example and requires the same A6 models with three/category. Preserve the shared
registry and state the actual ranges; do not relabel a 7B model as 30B+.

## Person 3 integration received October 25

Main PR #40 supplies 100 benchmark rows, 90 API estimates and five before/after
fine-tuning responses. Team completion is now 350/375. Only Llama's 25 rows remain
blocked by author approval. API is cheaper in all modeled pairs; the single paid
Llama-3.1-8B comparable has not been quality-qualified.

`architecture_integrate_peers` validates all five pre-training baseline matches,
question identity, original state and generation settings. It retains source
phrase-match scores but reviews contradictions on the same 1–10 scale as baseline/RAG.
The final comparison uses actual source continuations, not substituted retrieval answers.

`architecture_verify_finetune` independently trains the supplied tiny model in
memory without changing checkpoints or source exports. Local state differs from
the Mac export and 4/5 continuations match exactly; see the reproduction report.
Training questions overlap the evaluation questions, so this is in-sample evidence.
