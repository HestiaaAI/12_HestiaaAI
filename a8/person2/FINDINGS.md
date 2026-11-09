# Person 2 — Assignment 8 results

Completed November 9, 2026 using the returned Google Colab CPU run. All 15 small-model matrix requests and 10 scaling requests contain actual answers, full retrieved chunks, exact prompts and measured end-to-end latency. Quality and relevance judgments are AI-assisted; student signoff is not recorded.

## Configuration and evidence

- Encoder: `sentence-transformers/all-MiniLM-L6-v2`, revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, 384 dimensions, normalized float32 cosine search, k=3.
- Generator: `Qwen/Qwen2-0.5B-Instruct`, revision `c540970f9e29518b1d8f06ab8b24cba66ad77b6d`, previously evaluated in A6/A7. The unchanged Person 3 system prompt, cited-context format, greedy decoding, 128-token cap and CPU float32 calculation are used throughout.
- Runtime: hosted Linux x86-64, Python 3.13.18, torch 2.14.1+cpu, NumPy 2.4.6, sentence-transformers 5.1.2, transformers 4.57.6, four PyTorch threads. Matrix/scaling manifests match on controls and environment.
- Full corpus: 30 paragraphs, 2,901 words. Small subset: 15 paragraphs, 1,461 words. The shared source/chunkers are unchanged. Both datasets retain all five reference answers.
- Raw evidence: `../results/person2/completed-2026-11-09/`; every review is SHA-256-bound to its entire raw row, including prompt, answer, hits and timing. All three downloaded ZIP snapshots agree on shared raw files; the executed Colab notebook contains no error outputs.

## Evaluation method

Context quality is the shared rubric’s percentage of reference quotes present in the top three retrieved texts. Source recall and reciprocal rank are separate diagnostics, not semantic precision. Answer quality awards each fully conveyed required fact, subtracts one fact point per distinct materially incorrect or unsupported instruction, floors at zero, then divides by the number of required facts. Compound facts require all parts. Exact fact indices, deductions and rationale are in `reviews.csv`.

Noise is separately reviewed: a chunk is relevant if it answers a requested part or supplies directly applicable conditions, handoff or approval context. A broad household vocabulary match is insufficient. Redundant but relevant passages are not automatically noise; a different source ID is not automatically noise. Noise fraction is `(3 - relevant_hits) / 3`.

## Fifteen-row evaluation table

All rows below use the MiniLM encoder and fixed Qwen generator. Full questions, answers, complete retrieved chunks and longer review notes are in `matrix_evaluation.csv`; raw JSONL also retains exact prompts. Latency is observed warmed request time from query encoding through decoded text, excluding downloads, index construction, warm-up and review.

| Strategy | Query | Context /100 | Answer /100 | Request seconds | Notes |
|---|---|---:|---:|---:|---|
| fixed | Q1 | 100 | 66.67 | 29.95 | Tag attachment omitted |
| fixed | Q2 | 100 | 0.00 | 11.52 | Incorrectly closes unpurchased entry |
| fixed | Q3 | 100 | 0.00 | 36.34 | Missing facts; invented log fields |
| fixed | Q4 | 100 | 0.00 | 40.02 | Conditional notification wrong; capped |
| fixed | Q5 | 100 | 20.00 | 25.93 | Missing placements/lamp/completion rule |
| overlap | Q1 | 100 | 100.00 | 41.11 | All handoff facts |
| overlap | Q2 | 100 | 0.00 | 14.65 | Quantity alone does not answer question |
| overlap | Q3 | 100 | 0.00 | 33.55 | Misuses appliance upkeep as drill context |
| overlap | Q4 | 100 | 75.00 | 37.00 | Omits Plumbing/Maintenance names |
| overlap | Q5 | 100 | 100.00 | 45.55 | All required facts before cap |
| hybrid | Q1 | 100 | 0.00 | 21.84 | Invents status card and service call |
| hybrid | Q2 | 100 | 0.00 | 13.89 | Describes a purchase despite no substitute |
| hybrid | Q3 | 100 | 25.00 | 31.52 | Correct kit bin; missing name/closure |
| hybrid | Q4 | 100 | 75.00 | 40.41 | Omits Plumbing/Maintenance names |
| hybrid | Q5 | 100 | 100.00 | 41.37 | All required facts before cap |

Query mapping: Q1 kitchen close/running dishwasher; Q2 unavailable grocery/no approved replacement; Q3 drill location/checkout/return; Q4 slow-drip reporting; Q5 guest-room readiness. The five verbatim queries and required facts remain in `../data/queries.json`.

| Strategy | Mean context | Mean answer | Median request seconds |
|---|---:|---:|---:|
| fixed | 100.00 | 17.33 | 29.95 |
| overlap | 100.00 | 55.00 | 37.00 |
| hybrid | 100.00 | 40.00 | 31.52 |

All 15 contexts contain every reference quote, yet the mean answer score is only 37.44. Retrieval availability does not guarantee the generator uses the evidence. Overlap performs best on this small-model slice; this is not the team-wide chunking comparison. Three matrix requests reach the output cap; the guest answers contain all required facts before the cut, whereas the fixed tap answer is incomplete. Score the text actually returned, not a presumed continuation.

## Controlled dataset scaling

Only dataset content changes within this experiment. Small model, hybrid chunking, k=3, queries, generator, prompt, decoding, cap, thread setting and software environment stay fixed. Small/full hybrid indexes have 10/20 chunks. Their raw float32 vector payloads are 15,360/30,720 bytes, calculated as chunks × 384 × 4; these exclude metadata, text, compression and model weights.

| Dataset | Evidence quality | Mean answer | Reviewed noise | Median retrieval ms | Median generation s | Median full request s |
|---|---:|---:|---:|---:|---:|---:|
| small | 100 | 35.00 | 40% | 39.25 | 35.93 | 35.97 |
| full | 100 | 40.00 | 40% | 35.85 | 31.78 | 31.82 |

| Query | Small answer /100 | Full answer /100 | Difference | Small/full noise |
|---|---:|---:|---:|---|
| Q1 | 0.00 | 0.00 | +0.00 | 33% / 33% |
| Q2 | 0.00 | 0.00 | +0.00 | 33% / 33% |
| Q3 | 0.00 | 25.00 | +25.00 | 67% / 67% |
| Q4 | 75.00 | 75.00 | +0.00 | 33% / 33% |
| Q5 | 100.00 | 100.00 | +0.00 | 33% / 33% |

**Retrieval quality:** both sizes keep the supporting source at rank one and all reference evidence within the top three. Added paragraphs change lower-ranked hits for Q1, Q2, Q3 and Q5; Q4 keeps the same hits. There is no evidence-coverage loss from this controlled distractor addition.

**Noise:** the reviewed irrelevant fraction stays 40% overall. Extra topics sometimes replace existing irrelevant context rather than adding more irrelevant hits at fixed k. The inventory substitution-approval clause is relevant to Q2 even though it supplies no answer quote; the refund passage is not. Q5’s guest-supply guidance is relevant, whereas arrival/departure coordination does not establish readiness. These judgments are disclosed and may be revised after student review.

**Answer quality:** the five-point mean increase comes entirely from Q3 (0→25): the small-set answer invents a green kitchen bin for the kit; the full-set answer returns the kit to the correct blue hallway bin but still omits the borrower name and entry closure. Both Q1 answers invent repair instructions despite complete handoff evidence. Larger data did not eliminate generation errors.

**Scoring sensitivity:** the small-set Q2 says “checked out” rather than “unchecked.” The base review credits Out of stock, withholds the correct-status fact and deducts one point for the contradictory status instruction, yielding zero. If a reviewer treats that phrase only as an omission and removes the deduction, this row becomes 50 and the small-set mean becomes 45 rather than 35. That reverses the aggregate ordering; the observed five-point advantage is not a robust general scaling benefit.

**Latency:** the full set is not consistently faster per query. These are five warmed requests per dataset, run in dataset order rather than a randomized repeated load test. Variable output length and hosted CPU conditions affect generation; generation dominates this tiny exact-search index. Small changes in median retrieval latency do not establish a scaling speed advantage. No 10K-user/day throughput claim follows.

## Integration and limitations

- These 25 rows complete the Person 2 experiment slice. Person 3’s separate 45-row comparison remains the matched cross-encoder evidence; do not pool Colab and Mac timing medians.
- Person 4 owns the combined chunking comparison, failure/improvement section, cost/design reflection and final team ZIP. The observed unsupported service call, out-of-stock failures and invented kit location are available for that analysis.
- The original 2026-11-08 Mac retrieval-only measurements and indexes remain untouched. See `RETRIEVAL_FINDINGS_2026-11-08.md`; their timings are not relabeled as Colab measurements.
- Exact prompts confirm no answer key entered generation. There is no context truncation. Five Colab requests in total reach the 128-token cap (three matrix, two scaling).
- Quality/relevance reviews are AI-assisted, not independent human adjudication. Student signoff is not recorded.
