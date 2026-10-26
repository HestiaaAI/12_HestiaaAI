# Score review and provenance

All 375 benchmark continuations have saved five-component, 1–10 rubric scores.
Baseline/RAG/fine-tuned classroom SLM continuations have separate disclosed reviews.
These are AI-assisted self-evaluations, not independent instructor grading.

| Evidence | Current review basis |
|---|---|
| Person 1: 100 benchmarks | PR #45 applied 42 authorized corrections; original CSV, hashes and every assessment are in `person1/review/`. Application authorization does not assert personal inspection of every response. |
| Person 2: 100 benchmarks and 25 baseline/RAG continuations | Owner branch `dev-ddhene2-a7-local-costs-rag`, commit `abb0a42`, reports that the scores stand and records student approval. Updated owner handoff/analysis text is incorporated. No numeric score changes are imported. |
| Person 3: 100 benchmarks | PR #43 applied four score corrections. Raw outputs remain unchanged. |
| Architecture: 75 benchmarks | Response-hash-bound assistant reviews for SmolLM, TinyLlama and Llama are preserved in `architecture/` and `results/architecture_review_audit.json`. |
| Three-condition SLM comparison | Source phrase-match scores are retained separately from continuation-level 1–10 assessments. Contradictory statements receive partial credit and unsupported-information flags. |

The owner branch's broader `review_signoff.json` predates the latest Person 1
corrections. It is not copied as blanket approval of the current team matrix.
The owner report above records supplied evidence, not new authorization by the
current user or a claim of personal review by all four students.

Scores are judgments with a shared rubric. Wrong fixed-reference labels receive
the shared minimum score; useful but malformed JSON receives content credit while
losing adherence points. Small differences between owners should not be treated
as precise scientific rankings. The report retains hardware/precision labels.

Do not run the first-pass `a7.review_results` tool over corrected canonical CSVs:
it replaces inspected ratings. The architecture reviewer checks response hashes
before rewriting, accepts CRLF/LF conversion only, and retains the response text.
The original benchmark contract, runner and first-pass reviewer remain unchanged
so historical source hashes still identify the actual experiments.
