# Person 3 final notebook handoff

Ready for Person 1 to integrate; this is not the complete team assignment.

## Files

- `llm-test/person3_colab_run.ipynb`: the actual downloaded Colab execution notebook, including model downloads, original generation logs, diagnostics and the successful Qwen rerun. Interactive widget state/views are removed for privacy; original download is unchanged. It needs Colab and the upload bundles and is historical execution evidence, not a portable run-all notebook.

- `llm-test/person3_benchmark_handoff.ipynb`: executed report with real outputs, per-model/per-prompt summaries, all 32 selected raw responses and explanations, original Qwen corruption and numerical probes. Download cell is opt-in; report execution does not repeat model inference.
- `a6_results/person3_benchmark_results.csv`: exactly the shared 11 columns, 32 unique model/input/mode combinations; merge using P1's existing CSV collection cell.
- `a6_results/person3_reviewed_scores.csv`: same selected runs plus E/T/P/C/F criterion breakdowns, configuration and reviewer attribution.
- `a6_results/person3_nf4_raw/`: 32 original runs and metadata/checksums, unchanged.
- `a6_results/person3_nf4_fp32/`: eight Qwen reruns and metadata/checksums, unchanged.
- `a6_results/person3_nf4_diagnostics/`: two precision probes.
- `docs/a6-person-3/handoff/manifest.json`: source hashes, configuration selection, summary and team coverage audit.

## Scoring review completed

Every selected raw response was reviewed again under one policy. Scores are assistant-assisted judgments requested by the user, not independent human ratings. The older `*_review_draft.csv` files are superseded by `person3_reviewed_scores.csv`; do not merge draft files. Review notes in the canonical merge CSV include attribution, criterion scores and configuration.

The original draft sometimes assumed Friday meant an immediate deadline and treated routine smoke-detector maintenance as a confirmed emergency. Final scores do not make those assumptions. Both DEADLINE and ERRAND can reasonably classify a library return. Format failure does not erase recognizable content credit, but invalid output must be rejected by the app. A score of 10 means no problem found under this two-input rubric, not guaranteed correctness or production readiness.

| Model/configuration | Shared schema | Mean score /10 | Mean generation seconds |
|---|---:|---:|---:|
| Phi-3.5 Mini NF4/float16 | 6/8 | 8.000 | 9.326 |
| Mistral 7B NF4/float16 | 6/8 | 8.562 | 10.074 |
| Llama 3.2 3B NF4/float16 | 1/8 | 7.750 | 6.881 |
| Qwen2.5 7B NF4/float32 | 8/8 | 9.375 | 12.385 |

Qwen is the strongest structural candidate within this P3 test, not an established team-wide winner. Original Qwen NF4/float16 produced NaNs and 0/8 valid results; it remains archived rather than receiving misleading semantic quality scores. Both compute and non-quantized module precision changed in the successful rerun. Do not claim that every model used identical precision or that a single timing measurement proves an architecture is faster. No output was repaired.

## Integration for Person 1

1. Extract the package over the same relative paths in your checkout, reviewing any existing files before replacement. Keep the canonical P3 CSV at `a6_results/person3_benchmark_results.csv`.
2. Merge P1/P2/P3/P4 CSVs once each. Currently this gives 120 selected generations over 15 distinct models; Qwen's failed original configuration is not a 16th model.
3. Retain configuration and reviewer attribution. Refer to the preserved probes to explain Qwen selection and do not silently drop failed evidence.
4. Integrate report content into the actual final `llm-test/ai_prototype.ipynb`. The current root notebook is P1-only; the current notebook at the assignment path is P4-only. This handoff does not overwrite either owner's notebook.
5. Execute the final merged notebook and verify required sections, outputs and reflections. This report passed nbformat validation and all six analysis cells executed successfully; weights were intentionally not re-downloaded and inference was not rerun during report assembly.

## Running this handoff report

From the repository or extracted package root, open `llm-test/person3_benchmark_handoff.ipynb`. Ordinary report cells use Python standard-library modules. Jupyter is needed to display/execute the notebook. Optional model downloading requires Hugging Face Hub and gated access for Llama; actual GPU inference requires the included benchmark requirements. Keep all model weights and keys out of Git.

This package is local only. No commit, push, PR, or message to another teammate was made.
