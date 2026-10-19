# Person 3 NF4 benchmark review

32 original generations on Colab Tesla T4 (14.56 GiB). Both metadata files have the same notebook SHA256. Python 3.13 differs from the notebook's suggested 3.11; retain that limitation. Hardware and quantization differ from other teammates, so timing/quality comparisons are conditional.

Original files are byte-for-byte copies of the supplied downloads in `a6_results/person3_nf4_raw/`; SHA256SUMS.json records their hashes. No outputs or original validation flags were repaired.

| Model | Shared-validator passes | Mean generation seconds |
|---|---:|---:|
| microsoft/Phi-3.5-mini-instruct | 6/8 | 9.326 |
| Qwen/Qwen2.5-7B-Instruct | 0/8 | 12.615 |
| mistralai/Mistral-7B-Instruct-v0.3 | 6/8 | 10.074 |
| meta-llama/Llama-3.2-3B-Instruct | 1/8 | 6.881 |

## Draft scoring

`a6_results/person3_nf4_review_draft.csv` preserves all 32 runs and adds criterion scores (extraction 3, type 2, priority 2, clarity 2, format 1). These are assistant-generated review drafts, NOT completed independent human evaluations. Darshan/team must review and approve or amend them. Scores are subjective, and half points are used. Qwen has no score pending diagnosis. Do not merge these automatically into the final notebook.

BD1 has three explicit actionable concerns (kitchen, groceries, leaking tap). Guests tomorrow provide context, not an instruction to invent guest-room tasks. BD2 has four concerns. No current weekday is supplied: Friday alone does not establish a deadline within 24 hours. Format points require a complete JSON-only response with the required fields; the original shared validator extracts a nested/first object and sometimes accepts trailing commentary. Thus a recorded schema pass can receive zero format points in the review. No automatic brace repair was applied.

## Findings

- Phi: library returns classified SHOPPING, wrong title0 key, truncated output/commentary, and example contamination mentioning gas.
- Mistral: missing descriptions in zero-shot BD1, unsupported LAUNDRY, invented overdue book, unsupported URGENT deadline.
- Llama: seven outputs omit the final outer brace despite staying below 220 tokens. BD2 zero is valid but descriptions are weak time phrases. Some outputs invent dead batteries or an overdue book.
- Qwen: all eight outputs contain abnormal exclamation marks and hit the 220-token cap. Observed failure is valid evidence for this configuration, but its cause is unresolved; do not generalize it to all Qwen inference.

## Qwen diagnostic

Run `llm-test/person3_qwen_diagnostic.py` in the existing Colab bundle. It uses the same BD1 one-shot prompt and 220-token deterministic generation, retaining NF4/double quant/eager attention, while testing float32 compute and non-quantized modules. This tests a precision hypothesis; it is not a confirmed fix. It records raw output, prompt hash, library versions, latency, numeric NaN/infinity checks and strict full-output JSON validity. Files are created exclusively, so existing diagnostic output cannot be overwritten. Do not load unquantized 7B on the T4.

First run `--compute float16` to see whether the anomaly reproduces in isolation. Then run `--compute float32`. Each command exits before the next model load. Compare outputs and diagnostics before choosing another benchmark configuration; if precision changes help, rerun all eight fixed cases separately and label the new configuration. If both corrupt, investigate dependency/model-tokenizer compatibility next. Negative infinity scores can be deliberately masked; they do not alone establish numerical failure. Neither healthy first scores nor one successful probe proves all prompts work.

The script was syntax/CLI checked locally; CUDA inference has not been executed here. Outputs require Colab execution.

Primary references: [Qwen model card](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) and [Transformers bitsandbytes configuration](https://huggingface.co/docs/transformers/v4.48.0/en/quantization/bitsandbytes). The documentation permits compute dtype configuration; it does not establish the cause of these particular outputs.


## Qwen precision diagnosis: probes received

Both probes used the same rendered prompt SHA256, notebook, GPU, versions, eager attention, NF4 weights, and double quantization. The float16 probe reproduced the original BD1 one-shot output byte-for-byte and reported NaNs in 134 of 220 generation score steps. Float32 compute and float32 non-quantized modules produced valid JSON in 92 tokens with zero NaN/infinity score steps. Peak allocated memory was 6.586 vs 7.707 GiB, and generation time was 13.390 vs 9.747 seconds for these single probes. Files are in `a6_results/person3_nf4_diagnostics/`.

This is evidence of a precision-related numerical failure in the tested float16 configuration, not evidence that Qwen cannot perform task extraction. The probe changes both compute dtype and non-quantized module dtype, so it does not isolate the exact failing layer or arithmetic operation. A single healthy float32 response is not a full benchmark. Re-run the same eight cases with NF4 weights/float32 computation and label the new configuration separately. Do not pool timing or silently replace failures from the original configuration. Original Qwen quality scores remain deferred until that rerun and review.

## Complete Qwen float32-compute rerun received

All eight fixed input/shot-mode combinations completed and passed both the shared validator and an independent full-output JSON/schema check. The latter checked the exact root/task keys, nonempty string fields, allowed types/priorities, task counts (BD1=3, BD2=4) and title/description lengths. No response reached 220 tokens (range 85–157). Mean generation time was 12.385 seconds; this is per-response generation, excluding download/model loading. The notebook SHA256 matches the original 32 runs. Raw CSV/metadata and checksums are in `a6_results/person3_nf4_fp32/`.

The comparison is now 0/8 shared-validator passes under NF4+float16 versus 8/8 under NF4+float32. These are distinct inference configurations of the SAME model, not a fifth unique model. Together with the originals, 40 generations are retained. Original float16 failures remain evidence of numerical instability, not reliable model-quality scores. The full rerun did not collect stepwise NaN checks, so do not assert it measured zero NaNs on all eight cases; only the diagnostic probe did.

The structural issue is resolved across these eight test cases, but semantic errors remain: BD2 zero/one incorrectly assign URGENT to booking a dentist, one-shot expands batteries to all smoke detectors, and many-shot assigns LOW to the Friday library return. DEADLINE and ERRAND are both allowed and defensible classifications of a library return; do not penalize a valid alternate type automatically.

`a6_results/person3_nf4_fp32_review_draft.csv` contains eight assistant-proposed criterion scores with justifications. Human approval remains required. It does not alter the raw CSV. Qwen now has the strongest structural reliability among the P3 configurations tested on these two inputs; this small test set does not establish general model superiority. Any final notebook table must label its NF4/float32 setting separately from the other models' NF4/float16 setting, preserve failed configurations, and distinguish measured generation time from loading.

## Final assistant-assisted review and handoff

The draft CSVs are superseded by `a6_results/person3_reviewed_scores.csv` and the merge-ready `a6_results/person3_benchmark_results.csv`. Final review made urgency judgments consistent across models and retained reviewer attribution. See `handoff/README.md` and the executed `llm-test/person3_benchmark_handoff.ipynb`. This is the completed P3 benchmark handoff for integration into the team notebook.
