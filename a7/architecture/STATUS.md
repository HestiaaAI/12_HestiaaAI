# Architecture and final comparison — October 25, 2026

Merged integration through main PR #41, followed by the approved-account Llama evidence import.

## Completed

- Integrated all Person 2 and Person 3 benchmark, cost and SLM exports.
- Team benchmark: 375/375 successful scored rows across 15/15 models. Each of
  Persons 1–3 contributes 100; the architecture allocation contributes 75/75.
- SmolLM: 25 CPU/FP32; TinyLlama and Llama: 25 each on Colab T4/FP16. Raw responses, environment
  records and assistant score reviews are preserved.
- Step 1.6 findings, category completeness, condition-separated plots and task
  gates refreshed, including Person 3's MPS/FP16 and MLX/4bit conditions.
- Step 2.5: 90 workload-aligned local/API comparisons. API is cheaper in all 90
  modeled cases; no crossover at the six tested traffic levels. API uses one
  Llama-3.1-8B/Novita comparable, without proven quality equivalence.
- Five routing strategies updated with Qwen3 summaries, Qwen2.5-3B classification
  and summaries, and Qwen2.5-7B/MLX action planning. Priority prediction and the
  paid API candidate still need independent qualification.
- Assignment 2 Part 4: all five baseline/RAG/fine-tuned responses, scores, review
  notes and five analysis answers included in the submitted SLM notebook.
- All five pre-training baselines match Person 2. Checkpoint lineage/settings agree.
  Source exports and automatic phrase-match scores are preserved separately.
- Reviewed fine-tuning accuracy is 2.4/10 versus baseline/RAG 1.0, but no wholly
  correct, contradiction-free answer; all five tuned outputs contain unsupported
  information. Evaluation questions overlap fine-tuning examples.
- Original baseline/RAG inference independently reproduced 25/25 exactly.
- Independent fine-tuning rerun: weights change, loss 4.6915 to 0.2220, 4/5
  continuations match. Final state and Q4 differ across Windows/Mac; exact
  fine-tuned checkpoint reproduction is not claimed. No source exports overwritten.
- Shared analysis notebooks regenerated and executed; all three integration notebooks
  are schema-valid with no saved errors. The current test result is recorded in `../SUBMISSION.md`; see `LLAMA_COMPLETION.md` for import checks and remaining submission checks. The 90 API
  inference and gateway totals were independently recomputed. Checkpoints and caches stay excluded.

## Final Llama import and remaining submission checks

The approved-account teammate run supplied all 25 new A7 prompts successfully.
The previous 75-row matrix, including access errors, is preserved separately;
non-Llama responses/scores were retained. No A6 result substituted for an A7 run.
All five categories now have three successful models and 75 evaluated prompts.
Llama mean assisted quality is 6.88/10; malformed JSON and wrong priority labels
are retained honestly. The Large bin has the highest observed mean (7.48/10).

There is no remaining gated-model experiment blocker in the merged evidence.
Student signoff on assisted ratings, the disclosed scoring limitations
and final submission packaging are separate checks; do not
interpret 375/375 as a guarantee of full marks or production readiness.

## Rebuild

```powershell
python -m a7.architecture_integrate_peers
python -m a7.architecture_build_notebooks
python -m a7.architecture_execute
python -m unittest discover -s a7/tests -q
```

Optional independent fine-tuning check: `python -m a7.architecture_verify_finetune`.
It trains only the tiny classroom SLM in memory and never saves a checkpoint.

## Person 1 semantic score correction

Applied 42 authorized AI-assisted score corrections with all raw outputs/timings
unchanged and the original CSV preserved in `person1/review/`. Means are distilgpt2
1.00, SmolLM2-360M 3.32, Qwen2.5-1.5B 6.60, Phi-3.5-mini 7.00. Derived model/category
and task summaries include Person 3's corrected means (Qwen3 6.36, Qwen2.5-3B 7.72).
No model currently passes the five-prompt extraction or priority format/quality gate.
Personal student signoff remains separate from authorization to apply corrections.
