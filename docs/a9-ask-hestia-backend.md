# Ask Hestia backend handoff

Ask Hestia answers questions about household routines using the fictional A8
handbook. Its sources describe chores, shopping, inventory, maintenance reporting,
and guest preparation. The Django service accepts a question and returns the
generated answer with the passages provided to the model.

## Run locally

From the repository root, activate the project environment, install
`requirements.txt`, and configure `.env` as described in the root README.
The dependency list already includes Torch, Transformers and Safetensors. Use
`HF_HOME=model_cache/huggingface` for the ignored cache. CPU is the default.
`HF_ASK_HESTIA_DEVICE` can request `cuda` or `mps` for generation. The embedding
encoder runs on CPU. The first request downloads public weights and builds the
in-memory index. Later requests in the same worker reuse the loaded models and
index. With both models cached, set `HF_HUB_OFFLINE=1` to run offline.

```sh
python manage.py ask_hestia "Where do I find the shared cordless drill?" "What is the orbital period of Neptune?"
python manage.py test workflows.test_ask_hestia workflows.test_hf_output_retry workflows.test_brain_dump
```

The command calls the same service that the Django view should use. Each input
produces one JSON line. The first request can include model startup and index
creation in its reported latency. Send multiple questions in one command to
observe warm requests separately.

## Model selection and prior assignments

- **A6.** `Qwen/Qwen2-0.5B-Instruct` generated actual household-task outputs in
  `a6_results/person4_benchmark_results.csv`. Several outputs had invalid
  categories or invented actions, which supports using source passages and
  evaluating generated text before using it for decisions.
- **A7.** Qwen scored 5.20/10 with a 1.4941-second median in its T4/NF4 benchmark.
  SmolLM2-360M scored 3.32/10 in an Apple MPS run. Mistral-7B scored 8.12/10
  and had a 4.1807-second median in the same T4/NF4 condition as Qwen. The
  smaller Qwen is the initial local choice for its memory budget and lower
  measured latency than Mistral in that GPU condition. It scored higher than
  SmolLM2 in the recorded tests. These benchmarks used different tasks from Ask
  Hestia, and the SmolLM2 run used different hardware. See
  `a7/results/architecture/model_summary.csv`.
- **A8.** The backend imports `a8.corpus` and uses its full handbook with the
  fixed, sentence-preserving chunks. It uses
  [MiniLM](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2), a public
  384-dimensional sentence encoder, through Transformers with attention-mask
  mean pooling and L2 normalization. The 256-token limit is enforced before
  encoding. This is an initial design choice while the full A8 comparison is
  pending. The [Qwen model card](https://huggingface.co/Qwen/Qwen2-0.5B-Instruct)
  documents the generator used locally.

## Django integration contract

Call `workflows.services.ask_hestia.answer_question(question)` from the signed-in
view. Validate access before calling the service and render the answer and source
text with Django autoescaping.

| Return field | Meaning |
|---|---|
| `status` | `ok` means generated text was returned. `no_context` means no passage reached the similarity threshold. `insufficient_context` means the generator returned the requested abstention. |
| `answer` | Continuation from Qwen or the handbook abstention message |
| `sources` | Ranked records with chunk ID, document, section, paragraph IDs, text and cosine score |
| `latency_seconds` | Wall-clock seconds for retrieval and generation, including time waiting for the model lock and any first-load work |
| `model_id`, `embedding_model_id` | Model identifiers for the evaluation record |

The index searches 30 normalized chunk vectors using cosine similarity. It takes
up to two passages with scores of at least 0.30. With no eligible passage, the
service returns `no_context` without calling Qwen. The threshold is provisional
and should be evaluated on additional unrelated and ambiguous questions. The
model receives a grounding instruction, retrieved text and the question. It
generates greedily, with a 128-token cap and a 45-second cooperative generation
budget. Downloads, loading, and prefill can take additional time. Retrieved
passages provide evidence for review. Generated answers still require evaluation.

Catch `AskHestiaError` for `invalid_question`, `model_unavailable`,
`empty_answer` or `incomplete_answer`. The service rejects output that reaches
the generation budget without an end token. `str(error)` is suitable for the
page. Log diagnostics on the server. Input is limited to 500 characters and the
encoder token budget. The inference lock serializes model work within each process.

## Local smoke observations

On November 8, 2026, actual CPU retrieval returned all annotated evidence spans
in the top two passages for each of the five A8 queries. The unrelated Neptune
question returned `no_context` with no generator call. This checks one clear
out-of-scope example at the provisional threshold.

The first Qwen prompt yielded two useful failure cases for the app evaluation:

| Case | Retrieved chunks | Observation |
|---|---|---|
| Grocery item unavailable, no substitute | `fixed-shopping-02`, `fixed-shopping-01` | Qwen said to record the item purchased, contradicting the correct policy in the retrieved text. The cold request took 40.620 seconds. |
| Borrowing and returning the cordless drill | `fixed-inventory-01`, `fixed-inventory-02` | Qwen found the correct bin, invented a login step and cut off before the return instructions. The request took 45.128 seconds. |

The updated prompt puts passages before the question, restores handbook order
when both passages are from the same topic, and asks for a short answer. A rerun
of the grocery case reached the generation limit and returned `incomplete_answer`.
This change prevents displaying a cut-off completion. The revised prompt also
answered a question about towel quantity with “One clean sheet set” in 33.419
seconds, although `fixed-guests-01` contains the correct quantity of two towels.
For “Where does the shared cordless drill normally live?”, the revised service
returned “blue tool bin in the hallway cupboard.” with `fixed-inventory-01` as
the top passage. That cold CPU request took 44.232 seconds.
Answer quality and CPU latency remain limitations to evaluate in the app.
