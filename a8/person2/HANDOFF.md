# Assignment 8 Person 2 handoff

Branch: `dev-ddhene2-a8-retrieval-scaling`, based on `origin/main` at `e21f792`.
Person 1's corpus foundation is merged and reused unchanged. No Person 3 A8 branch
was visible after the November 8 fetch. No collaborator or co-author was added.

## Ready

- `a8/retrieval.py`: three-model registry, revision resolution, token overflow checks,
  normalized float32 embeddings, exact cosine search, full-context hit records,
  portable index persistence and checksum validation.
- `a8/person2_experiments.py`: 15-row small-model matrix, 10-row controlled scaling
  experiment, checkpointed evidence, strict resume guards, latency measurements,
  CSV exports and a callable adapter for Person 3's generator.
- `a8/results/person2/small-cpu-2026-11-08/`: actual HF small-model CPU results.
- `a8/person2_retrieval_scaling.ipynb`: saved-evidence analysis with optional explicit
  retrieval inference mode; default execution requires no model downloads.
- `a8/person2/FINDINGS.md`: retrieval/scaling findings and limitations.
- `a8/person2/requirements.txt`: tested dependencies.

## Validation

All three real Hugging Face models encoded the 20 full/hybrid chunks and retrieved
Q1 successfully: vector shapes `(20,384)`, `(20,768)`, `(20,1024)`.
Resolved revisions and actual hits are in `a8/results/person2/model_smoke_tests.json`.
The small model uses its standard 256-token context. Nine A8 tests, 42 A7 tests and
the repository's 221-test Django run passed; dependency consistency checks passed.

## Pending before Person 2 can claim all assignment deliverables

Person 3 must select the shared A6/A7 generator, prompt, decoding and rubric.
Use the same settings for small/medium/large runs. Then run actual generation for
all 15 Person 2 matrix rows and the two scaling datasets, inspect outputs and
complete context/answer quality ratings. Existing CSV quality/answer fields are
empty, and rows are labeled `retrieval_only` deliberately.

The supplied adapter accepts `generate_answer(query, hits)`; see README for exact
return fields. Use a real jointly measured request for end-to-end latency. A sum of
separately measured retrieval/generation stages is explicitly labeled as such.
Human/student review of any assisted quality scores is still required.

## Findings so far

All 15 matrix rows retrieve all exact reference quotes within k=3. Both scaling
sizes keep supporting sources at rank one and full evidence coverage. Lower-ranked
contexts change for four of five scaling queries. Review their actual usefulness
before calling them noise; no generated-answer conclusion is supported yet.

## Integration ownership

Person 3 can import `load_encoder('medium')`, `build_index` and `search` for their
15 rows and owns the shared runner/rubric and pooled model comparison. Person 4 can
use `load_encoder('large')` for their 15 rows, then integrate the team notebook,
analysis, requirements and final ZIP. This is a Person 2 handoff, not a final team ZIP.

Model revision, source/data hashes, CPU environment and token counts are recorded
with raw results. Preserve them when combining evidence. Do not compare model-family
quality differences as effects of dimension alone. Do not overwrite raw retrieval
evidence with reviewed/generated summaries.
