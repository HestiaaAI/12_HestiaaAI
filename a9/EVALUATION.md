# Assignment 9 · Evaluation of the integrated Ask Hestia feature

## Steps 3.1 and 3.2 — Inputs, outputs and quality

Eight inputs were submitted to the authenticated Django page in each phase. Q1–Q5 are realistic multi-part household questions from the A8 handbook. Expected behavior and required facts are frozen in inputs.json. G1–G3 exercise empty input, the size limit and an unrelated question. The evaluation covers the actual URL, form, view, model service and rendered answer/source sections through Django's test client. It is an automated integrated HTTP evaluation.

The CSV includes complete input, expected behavior, visible output, correctness, usefulness, structure, request time and notes for every case. Raw requests and rendered HTML preserve the underlying evidence. Correctness percentages below measure full required facts conveyed. Misleading additions are flagged separately and prevent the overall case from passing. Scores are AI-assisted review.

| Input | Expected behavior in brief | Baseline visible output in brief | Baseline completeness | After visible output in brief | After completeness | Before / after request seconds |
|---|---|---|---:|---|---:|---:|
| Q1 Kitchen is closed but dishwasher still running | Complete existing card, clip Running tag, leave unloading for morning | Mark Running tag and store separately | 0% | Complete card, then “Leave the Running tag unloading” | 33.33% | 6.542 / 9.774 |
| Q2 Grocery unavailable with no approved substitute | Leave unchecked and write Out of stock | Record the substitute's name and close the entry | 0% | “Out of stock” | 50% | 6.536 / 8.141 |
| Q3 Borrow and return the cordless drill | Blue hallway bin, full checkout record, return kit and close entry | Correct bin, incomplete/repeated logging | 25% | Correct starting bin, invented green kitchen return bin | 25% | 7.396 / 9.715 |
| Q4 Report a dripping bathroom tap | Plumbing card, reuse existing entry, record details, notify through card | Photo and existing-card check only | 25% | All four required reporting instructions | 100% | 7.055 / 12.010 |
| Q5 Prepare an overnight guest room | Exact supplies/locations, lamp check, readiness-card rule | Three supplies only | 20% | Three supplies only | 20% | 6.477 / 8.903 |
| G1 Whitespace only | Required-field error before model call | Required-field error | Pass | Required-field error | Pass | See CSV |
| G2 501 characters | Length error before model call | 500-character error | Pass | 500-character error | Pass | See CSV |
| G3 Capital of Australia | Abstain because handbook has no answer | Handbook abstention, zero hits | Pass | Handbook abstention, zero hits | Pass | See CSV |

See evaluation.csv for exact timing values and full text. Short answers are visually readable in both phases. The after-phase plumbing answer is a long but complete prose paragraph. Several concise answers omit crucial instructions. HTTP 200 and service status ok only indicate that the page/service returned normally; they do not establish factual correctness.

## Step 3.3 — Two observed failures and causes

### Failure 1 — The out-of-stock response describes a purchase

Q2's baseline answer says, “Record the actual name of the substitute in the list entry before closing it.” No replacement was approved. Following it would close an unpurchased entry.

Both retrieved fixed chunks together contain the correct rule: leave the original item unchecked and add Out of stock. The exact prompt and hit texts are retained. The failure occurs in selecting the appropriate instruction from context. The same passage also explains what to do if an approved substitute is purchased, and the generator applies that neighboring condition to the wrong situation. The evidence shows a generation error with the required evidence present.

The overlap run says “Out of stock.” This fixes the false purchase instruction but still omits leaving the item unchecked.

### Failure 2 — The guest-room response omits readiness checks

Q5's baseline answer lists a sheet set, two towels and a water carafe. It does not specify where the towels/carafe go, check the lamp, or explain when to complete the Guest Room Ready card.

The two retrieved passages contain all required reference quotes. The prompt requests one or two short sentences, while the question requires multiple conditions. The small generator returns only the supply list. The output ends normally after a short response, so the output cap or a timeout did not cause this omission. Compression and instruction-following are plausible causes; this experiment does not isolate them individually.

The overlap intervention still returns only the supply list. Changing chunk boundaries alone does not resolve this failure.

## Step 3.4 — One targeted improvement

The baseline uses sentence-packed fixed chunks. The intervention uses overlapping windows of two adjacent paragraphs with a one-paragraph stride, bounded by topic. This keeps a specific household rule with its surrounding introduction. The index changes from 30 fixed chunks to 20 overlapping chunks.

Only the chunking strategy changes. Generator, embedder, question text, prompt, native precision, CPU threads, top-k=2, minimum cosine similarity=0.30 and decoding/output budget stay fixed. The same eight input strings were used in both phases. Exact backend snapshots and input hashes are saved.

For Q4, the baseline conveys one of four required facts, while the overlap answer conveys all four and is useful as a complete reporting procedure. Q2 improves from zero to one of two required facts. Overall mean completeness across the five content questions rises from 14.00% to 45.67%. Fully correct content answers rise from 0/5 to 1/5. The three guardrails pass in both phases.

The change has costs. Median content-request time rises from 6.542 to 9.715 seconds on this run. Q3's after answer invents a green kitchen bin for returning the drill, contradicting the blue hallway bin in the evidence. Its matching-fact percentage stays 25%, but its usefulness is worse. All required reference quotes are available within the top two passages in both phases. The improvement changes how the generator handles context.

These are five content questions, one measured request each, with sequential before/after runs. They demonstrate a mixed improvement attempt and retain the regressions. The application still needs quality work before broad use. Future experiments can test a checklist prompt or a stronger previously evaluated generator, using the same inputs.

## Reproduction and demo handoff

Use a9.evaluate to replay the current or archived baseline backend through the actual Django page with a disposable database. a9.analyze validates the saved reviews and regenerates the table. Review fingerprints bind ratings to actual prompts, sources, outputs and displayed errors.

Person 4 can demonstrate Q4 as a complete content answer, Q3 as a hallucination limitation, and G1/G2/G3 as graceful guardrails. A second successful content example still needs to be selected and verified for the team's demo rehearsal.
