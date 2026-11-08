# Shared evaluation rules

Use the five frozen queries and three ranked passages for each request. Review the generated answer after inference. The answer key stays out of the prompt.

- Context quality (0–100) is the percentage of the query’s reference evidence spans contained in the top three passages, using Person 2’s whitespace- and case-normalized matching. Report first supporting rank separately to distinguish equal coverage with different rankings. This measures evidence availability, not overall passage precision.
- Answer quality (0–100) gives one point for each required fact fully conveyed, including all parts of a compound fact. Accept paraphrases. Deduct one fact point for each distinct, materially incorrect or unsupported instruction, floor at zero, then divide by the number of required facts. Do not deduct twice for restatements. Record fact indices, deductions and rationale. Optional, supported details carry no bonus. Exact scores can be recomputed from the review.
- End-to-end latency is one wall-clock measurement for the complete warmed request, from query encoding to decoded text. Also record retrieval and generation milliseconds. Exclude model loading, index construction, warm-up and grading. Compare medians descriptively.
