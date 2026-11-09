# Person 2 final handoff — November 9, 2026

Person 1's merged corpus/chunkers and Person 3's merged frozen generator/runner
are reused unchanged. The completed inference was executed by the user in Colab;
the returned raw evidence has been validated and assessed with the shared rubric.

## Deliverables

- `a8/retrieval.py`: 384/768/1024-d model registry, immutable revision resolution,
  token-limit checks, normalized embeddings, cosine top-k search, full hit metadata
  and persisted indexes/checksums. All three actual models passed compatibility checks.
- `a8/results/person2/completed-2026-11-09/matrix_evaluation.csv`: **15 assessed
  small-model RAG rows**, with actual answers, complete retrieved chunks, quality,
  retrieval/generation/end-to-end latency and notes.
- `scaling_evaluation.csv`, `scaling_summary.csv`, `scaling_pairs.csv` in that folder:
  **10 assessed small/full hybrid requests**, fixed controls and paired findings.
- `a8/person2_retrieval_scaling.ipynb`: executed offline analysis with full passages
  and answers. `a8/person2_colab_executed.ipynb`: unchanged returned inference notebook.
- `a8/person2/FINDINGS.md`: measured results, interpretation and scoring sensitivity.
- `a8/person2_analysis.py`: frozen-control, full-row review hash, prompt and corpus
  validation plus table export. No generation is rerun during analysis.
- `a8/person2/README.md`, requirements and Colab instructions: setup and reproduction.

## Findings for the report

All 15 matrix rows retrieve 100% of reference evidence. Mean answer quality is
17.33 fixed, 55.00 overlap and 40.00 hybrid. This is the small-encoder slice only.

Small/full scaling keeps 100% evidence availability and rank-one supporting
sources. Lower-ranked hit identities change for four queries, but reviewed noise
remains 40% on both sizes. Mean answer quality is 35 versus 40; the difference
comes entirely from the drill question. It is not robust evidence of a general
benefit: an alternative treatment of the small grocery answer's “checked out”
wording changes the small mean to 45. See the complete review and sensitivity note.

Colab median full-request latency is 35.97 seconds small versus 31.82 seconds full.
Do not interpret this as a scaling speed advantage: five requests per dataset,
variable output length, dataset-order execution and hosted CPU conditions limit it.
Do not pool these measurements with Person 3's different machine timings.

## Evidence and integration

Raw matrix/scaling JSONL and manifests are unchanged. Reviews are AI-assisted,
with fact indices, unsupported deductions, relevant ranks and rationale; hashes
bind every field of each raw response. Student signoff is not recorded. All three
returned ZIP snapshots agree; the returned notebook has no saved error outputs.
No model weights are committed. The exact small input bundle is retained for replay.

Person 4 can reference these completed scaling rows in Step 2.5 and integrate this
analysis notebook into the final team notebook. Person 3's 45-row matrix remains the
matched evidence for the cross-encoder comparison; it is not overwritten by these
separate Colab timings. The prior Mac retrieval-only run remains historical evidence.

Rebuild tables with `python -m a8.person2_analysis` and run
`python -m unittest discover -s a8/tests -v` from the repo/extracted handoff root.
