# P4 larger-model findings

Actual CUDA inference on Tesla T4. NF4 weights, FP32 computation/non-quantized modules, eager attention, 220 new tokens maximum, greedy generation; Qwen3 thinking disabled.

| Model | Runs | Schema valid | Mean generation | Mean reviewed quality |
| --- | ---: | ---: | ---: | ---: |
| tiiuae/Falcon3-7B-Instruct | 8 | 7/8 | 17.453 s | 8.500/10 |
| Qwen/Qwen2.5-14B-Instruct | 8 | 8/8 | 20.778 s | 9.500/10 |
| microsoft/Phi-3-medium-4k-instruct | 8 | 3/8 | 33.919 s | 6.875/10 |
| Qwen/Qwen3-14B | 8 | 8/8 | 21.801 s | 9.250/10 |

| Model | Zero-shot quality | One-shot | Few-shot | Many-shot |
| --- | ---: | ---: | ---: | ---: |
| tiiuae/Falcon3-7B-Instruct | 7.50 | 8.50 | 9.00 | 9.00 |
| Qwen/Qwen2.5-14B-Instruct | 9.50 | 9.50 | 9.50 | 9.50 |
| microsoft/Phi-3-medium-4k-instruct | 4.50 | 7.50 | 7.50 | 8.00 |
| Qwen/Qwen3-14B | 9.50 | 9.50 | 9.00 | 9.00 |

Observed content limitations:

- Falcon extracted the concerns consistently but often overstated tap/Friday urgency; its BD2 zero-shot JSON was truncated at 220 tokens.
- Qwen2.5 produced concise, schema-valid outputs in every case. Guest preparation was often only MEDIUM; valid JSON still needs priority review.
- Phi changed the required schema in both zero-shot cases, misclassified library returns, invented overdue status, and truncated all three example-based BD2 outputs. Its 3/8 schema rate is conditional on the same 220-token cap used for every model.
- Qwen3 was schema-valid in every case but overstated leak urgency in early modes and under-ranked detector batteries in few/many-shot. More examples did not monotonically improve quality.

Scores are assistant-assisted content judgments using extraction/types/priority/clarity/format (3/2/2/2/1). Inspect each raw response and its explicit criterion notes in the notebook. Independent human approval is not asserted.

Load timing includes uncached downloads. Generation timing is CUDA-synchronized. GPU/quantized timing cannot be treated as a controlled speed comparison against the earlier CPU/native measurements or a remote paid API.

These candidates cover one large and three above-10B positions under the original ranges. Main PR #31 now uses different balanced bands and retains the earlier small-model selection. P1/the team owns whether to retain that plan or consolidate this larger-model evidence; do not blindly concatenate both P4 sets. See large-models.md for the exact handoff.
