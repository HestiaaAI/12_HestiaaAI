# Available benchmark findings

375/375 successful, scored evaluations are available across 15/15 models. Scores are assistant-assessed; student signoff remains pending. Hardware/precision conditions are separate; this is not a controlled size-only experiment.

| Model | Condition | Mean quality /10 | Median latency (s) |
|---|---|---|---|
| mistralai/Mistral-7B-Instruct-v0.3 | Tesla T4 / NF4 weights / float32 compute / eager | 8.12 | 4.1807 |
| Qwen/Qwen2.5-3B-Instruct | Person 3 macOS arm64 / mps / float16 / 16 GB unified memory | 7.72 | 5.7808 |
| Qwen/Qwen2.5-7B-Instruct | Person 3 macOS arm64 / mlx-4bit / 4-bit / 16 GB unified memory | 7.32 | 1.6516 |
| microsoft/Phi-3.5-mini-instruct | Apple MPS / native model / exact GPU unrecorded | 7.00 | 5.3627 |
| meta-llama/Llama-3.2-3B-Instruct | Tesla T4 / native FP16 | 6.88 | 1.0295 |
| Qwen/Qwen2.5-1.5B-Instruct | Apple MPS / native model / exact GPU unrecorded | 6.60 | 1.5895 |
| Qwen/Qwen3-0.6B | Person 3 macOS arm64 / mps / float16 / 16 GB unified memory | 6.36 | 1.2654 |
| Qwen/Qwen2-0.5B-Instruct | Tesla T4 / NF4 weights / float32 compute / eager | 5.20 | 1.4941 |
| HuggingFaceTB/SmolLM2-1.7B-Instruct | Tesla T4 / NF4 weights / float32 compute / eager | 4.96 | 0.8802 |
| HuggingFaceTB/SmolLM2-360M-Instruct | Apple MPS / native model / exact GPU unrecorded | 3.32 | 0.5633 |
| TinyLlama/TinyLlama-1.1B-Chat-v1.0 | Tesla T4 / native FP16 | 2.96 | 5.2453 |
| HuggingFaceTB/SmolLM2-135M-Instruct | Person 3 macOS arm64 / mps / float16 / 16 GB unified memory | 2.56 | 1.6161 |
| HuggingFaceTB/SmolLM-360M-Instruct | Windows CPU / native FP32 / 4 threads | 2.48 | 19.0588 |
| facebook/opt-125m | Tesla T4 / NF4 weights / float32 compute / eager | 1.08 | 3.1447 |
| distilbert/distilgpt2 | Apple MPS / native model / exact GPU unrecorded | 1.00 | 0.7815 |

## Step 1.6 answers

1. Best output category: Large (≥3.5B) has the highest observed mean (7.48/10) across the completed 75-row/category matrix. Quantization, instruction tuning and hardware differ, so this is descriptive rather than a size-only causal result.

| Category | Models available /3 | Rows available /75 | Mean quality /10 |
|---|---|---|---|
| Compact (0.2B–<0.6B) | 3 | 75 | 3.67 |
| Large (≥3.5B) | 3 | 75 | 7.48 |
| Medium (1.6B–<3.5B) | 3 | 75 | 6.52 |
| Small (0.6B–<1.6B) | 3 | 75 | 5.31 |
| Ultra-light (<0.2B) | 3 | 75 | 1.55 |

2. On extraction-02, Qwen2.5-1.5B scored 8; Phi-3.5-mini scored 5. The smaller Qwen model scores higher on 6 matched prompts in this pair. These are counterexamples to larger models always scoring higher.

3. Speed/quality balance: within Person 1’s MPS subset, Qwen2.5-1.5B averages 6.60/10 with median latency 1.5895 s; Phi-3.5-mini averages 7.00/10 with median latency 5.3627 s. Choose by task-specific quality and format requirements rather than declaring an overall winner from speed alone. Cross-condition times do not identify a global fastest model.

Routing candidates are in task_summary.csv. A proposed qualification requires five observations, mean score at least 8/10 and all five instruction-format scores equal to 2. Passing this small offline gate is a candidate-selection result, not production validation. Person 1 corrections were authorized for application; this is not personal student signoff. Cross-owner format/scoring conventions still need reconciliation.
