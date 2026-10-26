# Person 1: review of all 100 benchmark scores

Reviewed GitHub main at `ab0235169d67f7a92923fdba2b474c28a45f9ec0`. This is an AI-assisted second review. The student authorized application of these recommendations; that authorization does not claim personal inspection of every response. The canonical score components/notes and dependent summaries are updated; raw outputs and timings are unchanged. The original CSV is preserved in `person1_benchmark_before_review.csv`.

## Decision

Applied 42 revised totals and retained 58 totals. All 100 outputs were inspected against their full shared prompts and five-part rubric. Component recommendations are recorded in the companion CSV; totals have a floor of 1.

## Scoring interpretation

- Score the whole generated continuation. Do not silently strip markdown fences, duplicate objects, unrelated persona text or truncated suffixes to call an output JSON-only.
- Fenced otherwise valid JSON gets partial instruction credit (1/2); unusable structured responses get 0/2. Content and clarity can still earn points.
- Mere prompt/schema echoes do not count as a successful extraction, summary or plan. Recognizable keywords alone earn no completion credit.
- Accept faithful synonyms. Proposed planning actions are allowed; invented completed actions and specific factual claims are not.
- Preserve the original fixed-reference label scoring convention for consistency. A wrong reference label remains 1 even if readable; this convention is stricter than independently scoring its formatting. Priority reference labels are agreed benchmark judgments, not universal ground truth. Any change to this policy must be applied across all 15 models.
- These numbers involve judgment. Application was authorized by the student; personal inspection remains a separate step. Format conventions must be consistent across the team.

## Applied mean scores

| Model | Original mean | Applied mean | Totals changed |
|---|---:|---:|---:|
| distilbert/distilgpt2 | 2.28 | 1.00 | 9 |
| HuggingFaceTB/SmolLM2-360M-Instruct | 3.84 | 3.32 | 10 |
| Qwen/Qwen2.5-1.5B-Instruct | 7.56 | 6.60 | 13 |
| microsoft/Phi-3.5-mini-instruct | 7.32 | 7.00 | 10 |

## Important examples

- distilgpt2 extraction-03: 7 → 1. Repeats the request/schema and invents door advice, rather than extracting tasks.
- Qwen2.5-1.5B summary-02: 6 → 3. Invents an already-confirmed appointment next Wednesday at 4 PM.
- Phi-3.5 summary-01: 8 → 10; summary-02: 8 → 10. Faithful paraphrases were undercounted by keyword checks.
- SmolLM2 priority-04: 1 → 8. The correct URGENT answer is present after a request echo; it is not exact-label compliant, but has correct content.

## Other work in the supplied checklist

Person 3 notebook presentation was already fixed on main by PR #43; the API-cost notebook execution was merged in PR #44. No duplicate fine-tuning work is needed.

Person 2 owns their 100 scores, RAG score review and stale handoff text. The architecture lead owns their 75 scores and refreshing final summaries/notebooks/package. Refresh those derived files only after accepting all owners' score changes; they must incorporate the revised Person 3 means and any accepted Person 1 corrections.

## Remaining review and reproduction

The raw responses and old scores are retained beside the response-hash-bound review CSV. The general `a7.review_results` command is only a first-pass heuristic: do not run it over this corrected canonical CSV or it will replace these assessments. Rebuild derived analyses with `python -m a7.architecture_analysis`, and refresh the multi-model notebook with generation disabled.

Personal score inspection and the other owners' signoffs remain separate. Format conventions must be reconciled across owners before interpreting small differences in cross-owner means.
