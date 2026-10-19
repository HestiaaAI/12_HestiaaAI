# P4 larger-category correction

These tests complete P4's requested extension to the original large/above-10B
roster. During the run, main advanced to `5afd378` (PR #31): P1 adopted different
balanced size bands and kept the earlier P4 small-model tests in its selected
15-model notebook. That merged selection is preserved. The new results are
separate evidence; they are not silently added to P1's 15 selected models.

The correction tests these four public models:

| Model | Intended category | Cases |
| --- | --- | --- |
| `tiiuae/Falcon3-7B-Instruct` | Large | BD1/BD2 × zero/one/few/many |
| `Qwen/Qwen2.5-14B-Instruct` | Above 10B | BD1/BD2 × zero/one/few/many |
| `microsoft/Phi-3-medium-4k-instruct` | Above 10B | BD1/BD2 × zero/one/few/many |
| `Qwen/Qwen3-14B` | Above 10B | BD1/BD2 × zero/one/few/many |

Qwen3-14B was selected by the user as the additional above-10B model. P1 owns
the final category plan and final notebook. These results supply one-large and
three-above-10B candidates under the original ranges (≤0.5B, >0.5–2B, >2–4B,
>4–10B, >10B). PR #31 instead uses <0.2B, 0.2–<0.6B, 0.6–<1.6B, 1.6–<3.5B,
and ≥3.5B. Deciding which category plan to submit remains P1/the team's work;
P4 does not claim these different plans are interchangeable.

## Reproduction and evidence

Open [person4_large_models_colab.ipynb](../../llm-test/person4_large_models_colab.ipynb)
in Colab, select an available GPU, and run all cells. No paid compute purchase,
API key, Hugging Face token, or Drive mount is needed. The notebook embeds
[person4_large_benchmark.py](../../llm-test/person4_large_benchmark.py).
Its separate dependency list is
[requirements-person4-large.txt](../../llm-test/requirements-person4-large.txt);
the Django dependency file is unchanged.

The runner verifies a SHA-256-pinned copy of the team's existing prompt and
validation helpers from main commit `14a02aeb4eb71d1ddf7dfb66d1e868b77213eb28`.
It runs actual Transformers inference, pins each model revision, uses greedy
generation with 220 new tokens, and disables Qwen3 thinking. Weights use NF4
double quantization with FP32 computation and FP32 non-quantized modules;
attention is eager. These are quantized measurements, not native FP16 results.

Each response checkpoints an eleven-column CSV under
`a6_results/person4_large/person4_large_results.csv`. Metadata records the GPU,
versions, revisions, configuration, load time, and the last completed case's
peak allocated GPU memory (not the maximum across all cases).
Load time includes first downloads when uncached. Generation timing synchronizes
CUDA. Cross-hardware and cross-precision speed comparisons are not controlled.

The notebook uses a separate process per model and removes only that model's
dedicated downloaded weight cache after success. It exports a ZIP of the
runner, contract, CSV, and metadata, excluding weights. If a model fails, export
the partial evidence and inspect the error; partial rows are not a completed
benchmark. Re-running resumes completed input/shot cases.

Quality scores remain blank until the raw outputs have been read. Apply the
same extraction/types/priority/clarity/format rubric (3/2/2/2/1), with explicit
per-response reasons and review attribution. Schema validity alone does not
establish task quality. Do not invent scores or imply independent human review.

## Completed execution and handoff

All four models completed on October 18, 2026 (CDT; October 19 UTC), on a Tesla
T4 reporting 14.56 GiB VRAM. All **32 unique generations** were exported and
validated locally against the exact shared parser/schema. The exported runner
matched the repository source. ZIP SHA-256:
`f471c3e53964b86bf6b320b0744a4eb83ac75ac9f97a45287954a30dd6419cf5`.
These are cloud GPU model runs in the user's Colab, not measurements on the
Windows laptop or an on-premise privacy test. Inputs were the two fixed examples.

- New P4 input for any larger-model consolidation: [person4_large_results.csv](../../a6_results/person4_large/person4_large_results.csv).
- Full raw outputs and explicit review notes: [results notebook](../../llm-test/person4_large_results_review.ipynb).
- Findings: [large-model-findings.md](large-model-findings.md).
- Generation CSV/metadata are preserved separately as `person4_large_raw_results.csv`
  and `person4_large_run_metadata.json`; the review audit records their hashes.
  A directory-local `.gitattributes` keeps these files and the pinned contract
  in LF form so Windows checkout conversion cannot invalidate the hashes.
- [Colab completion screenshot](large-model-colab-complete.png) records the
  final 32-generation/eight-per-model count.

**If the team returns to the original ranges**, P1 should use the new 32-row CSV
instead of `a6_results/person4_benchmark_results.csv`, retain P2/P3, and select
three of P1's four ≤0.5B models. That yields 15 models/120 generations and
3/3/3/3/3 under the original ranges. Keeping PR #31's newer bands instead means
these four runs remain supplemental. Do not blindly concatenate both P4 sets.
P1's final notebook was not edited by P4.

The 32 quality reviews are assistant-assisted judgments with explicit criterion
points, not independent human signoff. Priorities remain context-sensitive;
read the audit's calibration notes. Schema validity is not semantic correctness.

```powershell
python docs/a6-person-4/verify_large_results.py
# Reapply only the frozen reviews for these unchanged raw outputs:
python docs/a6-person-4/review_large_results.py
python docs/a6-person-4/build_large_report.py
python docs/a6-person-4/execute_notebook.py --notebook llm-test/person4_large_results_review.ipynb
```

The benchmark harness passed five unit tests. The full Django suite passed 175
tests and its system check reported no issues. The results notebook is executed
against the exported CSV; it does not pretend to rerun GPU inference locally.
