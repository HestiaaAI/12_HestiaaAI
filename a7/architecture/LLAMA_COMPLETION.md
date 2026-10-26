# Approved-account Llama completion

The approved teammate account completed the missing **25 Assignment 7 prompts**
for `meta-llama/Llama-3.2-3B-Instruct` on Colab Tesla T4, native FP16, batch 1,
greedy decoding and a 220-token limit. A6's eight different evaluations were not reused.
The run timestamps are October 26 UTC / October 25 America/Chicago.

## Evidence and import

- `a7/architecture_llama_colab.ipynb`: original executed user-supplied notebook, preserved byte-for-byte.
- `a7/results/architecture_llama_cuda.csv`: exact raw 25-row export, with no output repairs or invented responses.
- `a7/results/architecture_llama_cuda.environment.json`: GPU, versions, shared-source hashes, observed Hub revision and raw CSV checksum.
- `a7/architecture/llama_review_audit.json`: 25 response-hash-bound assisted rubric assessments. Student signoff pending.
- `a7/results/architecture_llama_import_verification.json`: checks and preview limitations.
- `a7/results/architecture_before_llama_colab.csv`: preserved previous matrix, including the original access-error rows.

The import validated exact model/prompt keys, shared source hashes, raw CSV checksum,
CUDA/FP16 settings, notebook timing/status tables and response previews. Long notebook
previews are truncated; full continuations were inspected in the raw CSV. The recorded
Hub revision was observed before loading, not explicitly pinned by the shared runner.
No model weights or account token/cache are included. The 50 existing non-Llama rows
were preserved field-for-field, including their scores and review notes.

## Outcome

- Architecture allocation: **75/75 successful, scored**.
- Whole team: **375/375 successful, scored**, 15 models and five complete categories.
- Llama mean assisted rubric score: **6.88/10**.
- Median full-generation latency: **1.0295 seconds**; median generation rate: **26.2267 tokens/sec**.
- Four of five classification references correct; two of five priority references correct.
- Summary mean: **9.2/10**, with valid JSON across those five responses.
- Duplicate keys, illegal enum combinations and missing closing JSON objects remain
  failures in the recorded extraction/planning outputs; they were not repaired before scoring.
- The Large category has the highest observed mean across the completed matrix,
  **7.5867/10**. Hardware/precision/training conditions differ, so this is not a
  controlled causal effect of parameter count.

## Verification

All **37 A7 tests passed**. New checks cover valid import with preservation of the
existing 50 responses, rejection of altered prompts before mutation, and persistence
of inspected Llama scores through the standard review rebuild. The final
`a7/multi_model_system.ipynb` is executed with 375/375 saved success/score counts
and no saved errors. No model generation occurred in the refreshed analysis run.
Existing SLM/fine-tuning notebook outputs were preserved without rerunning inference.

This resolves the gated-model experiment blocker. It does not replace student
inspection of assisted scores or the notebook presentation items identified by the
submission audit (visible KB/scored RAG table and executed Person 3 notebooks).
No new commit, push or PR is performed by the evidence-import step.
