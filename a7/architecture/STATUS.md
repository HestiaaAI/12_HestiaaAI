# Architecture and final comparison — October 25, 2026

Branch: `devcrn-P4`, updated through main `ba1c032` (Person 3's PR #40).

## Completed

- Integrated all Person 2 and Person 3 benchmark, cost and SLM exports.
- Team benchmark: 350/375 successful scored rows across 14/15 models. Each of
  Persons 1–3 contributes 100; the architecture allocation contributes 50/75.
- SmolLM: 25 CPU/FP32; TinyLlama: 25 Colab T4/FP16. Raw responses, environment
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
  are schema-valid with no saved errors. All 34 assignment tests pass. The 90 API
  inference and gateway totals were independently recomputed. Checkpoints and caches stay excluded.

## Remaining external blocker

The last 25 prompts for `meta-llama/Llama-3.2-3B-Instruct` cannot run with this
account: the October 25 check returned HTTP 403, explicitly awaiting model-author
review. Authentication is present. A GPU runtime is preferable after approval.

Completion requires approved access and a 25-prompt run, or an authorized teammate
running the shared contract on an approved account. Do not reuse A6's eight
different evaluations or silently replace a required roster model. The GPU
notebook is prepared. Import actual results, review scores, then refresh analysis.

The full 375-row result and final Medium-bin ranking remain incomplete until that
run. All other integration work supported by merged evidence is complete.
Student signoff on assistant-assisted rubric reviews remains a submission check.

## Rebuild

```powershell
python -m a7.architecture_integrate_peers
python -m a7.architecture_build_notebooks
python -m a7.architecture_execute
python -m unittest discover -s a7/tests -q
```

Optional independent fine-tuning check: `python -m a7.architecture_verify_finetune`.
It trains only the tiny classroom SLM in memory and never saves a checkpoint.
