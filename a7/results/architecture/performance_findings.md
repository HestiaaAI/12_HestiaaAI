# Available benchmark findings

250/375 successful, scored evaluations are available across 10/15 models. Scores are assistant-assessed; student signoff remains pending. Hardware/precision conditions are separate; this is not a controlled size-only experiment.

| Model | Condition | Mean quality /10 | Median latency (s) |
|---|---|---|---|
| mistralai/Mistral-7B-Instruct-v0.3 | Tesla T4 / NF4 weights / float32 compute / eager | 8.12 | 4.1807 |
| Qwen/Qwen2.5-1.5B-Instruct | Apple MPS / native model / exact GPU unrecorded | 7.56 | 1.5895 |
| microsoft/Phi-3.5-mini-instruct | Apple MPS / native model / exact GPU unrecorded | 7.32 | 5.3627 |
| Qwen/Qwen2-0.5B-Instruct | Tesla T4 / NF4 weights / float32 compute / eager | 5.20 | 1.4941 |
| HuggingFaceTB/SmolLM2-1.7B-Instruct | Tesla T4 / NF4 weights / float32 compute / eager | 4.96 | 0.8802 |
| HuggingFaceTB/SmolLM2-360M-Instruct | Apple MPS / native model / exact GPU unrecorded | 3.84 | 0.5633 |
| TinyLlama/TinyLlama-1.1B-Chat-v1.0 | Tesla T4 / native FP16 | 2.96 | 5.2453 |
| HuggingFaceTB/SmolLM-360M-Instruct | Windows CPU / native FP32 / 4 threads | 2.48 | 19.0588 |
| distilbert/distilgpt2 | Apple MPS / native model / exact GPU unrecorded | 2.28 | 0.7815 |
| facebook/opt-125m | Tesla T4 / NF4 weights / float32 compute / eager | 1.08 | 3.1447 |

## Step 1.6 answers

1. Best output category: the observed category means below describe the available rows. A final five-category winner requires all three models per category; quantization/hardware differences also prevent attributing quality changes solely to parameter count.

| Category | Models available /3 | Rows available /75 | Mean quality /10 |
|---|---|---|---|
| Compact (0.2B–<0.6B) | 3 | 75 | 3.84 |
| Large (≥3.5B) | 2 | 50 | 7.72 |
| Medium (1.6B–<3.5B) | 1 | 25 | 4.96 |
| Small (0.6B–<1.6B) | 2 | 50 | 5.26 |
| Ultra-light (<0.2B) | 2 | 50 | 1.68 |

2. Larger models did not always score higher. On Person 1’s shared MPS run, Qwen2.5-1.5B scored 10 on extraction-02 versus 7 for Phi-3.5-mini; this is a matched-prompt counterexample in the supplied rubric evidence, not a claim that smaller models always win.

3. Speed/quality balance: Qwen2.5-1.5B is a strong available candidate within Person 1’s MPS subset (7.56/10; median 1.5895 s), versus Phi’s 7.32/10 and 5.3627 s. Within Person 2’s common T4/NF4 condition, inspect the per-task gates before choosing a model; cross-condition median times do not identify a global fastest model.

Routing candidates are in task_summary.csv. A proposed qualification requires five observations, mean score at least 8/10 and all five instruction-format scores equal to 2. Passing this small offline gate is a candidate-selection result, not production validation.
