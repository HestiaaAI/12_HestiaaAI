# Person 4 handoff

- Completed larger-category correction: [handoff](large-models.md), [32-run CSV](../../a6_results/person4_large/person4_large_results.csv), [review notebook](../../llm-test/person4_large_results_review.ipynb), and [GPU reproduction notebook](../../llm-test/person4_large_models_colab.ipynb).
- UI and integration guide: [README_AI.md](../../README_AI.md)
- Preserved executed small-model reference: [person4_small_reference.ipynb](../../llm-test/person4_small_reference.ipynb). `llm-test/ai_prototype.ipynb` is now P1's final team notebook.
- Measured 24-run CSV: [person4_benchmark_results.csv](../../a6_results/person4_benchmark_results.csv)
- Reviewed findings: [benchmark_summary.md](benchmark_summary.md)
- Environment/model revisions: [person4_environment.json](../../a6_results/person4_environment.json)
- Real inference → confirmed save evidence: [person4_django_integration.json](../../a6_results/person4_django_integration.json)
- Part 3 with sources and calculations: [local-vs-api.md](local-vs-api.md)
- Required notes entry: [docs/notes/notes.txt](../notes/notes.txt)

## Reproduce

Use a separate Python 3.11 environment for the benchmark and install
`requirements-benchmark.txt`. From the repository root:

```powershell
python docs/a6-person-4/benchmark.py
```

This downloads public weights to ignored `model_cache/`, then checkpoints the
two shared inputs × four shot modes for each of the three models. Existing
completed rows are resumed. Model revisions are pinned from the saved metadata;
move the CSV and environment JSON aside to start an entirely new experiment.

After reading the raw responses, `review_results.py` applies the explicit review
point breakdowns recorded for this run; `write_summary.py` summarizes measured
results. Review judgments are assistant-assisted and should be approved/corrected
by the submitter. Do not reuse those judgments after changing model/prompt/output.

```powershell
python docs/a6-person-4/review_results.py
python docs/a6-person-4/write_summary.py
# Optional: regenerate the notebook source (clears executed cell outputs)
python docs/a6-person-4/build_notebook.py
python -m ipykernel install --prefix .venv --name hestia-p4
python docs/a6-person-4/execute_notebook.py --notebook llm-test/person4_small_reference.ipynb
```

The executor expects the local `.venv` kernel registered by the command above.
Alternatively open the notebook normally in Jupyter with the matching environment.

For the complete Django app use Python >=3.12 and root `requirements.txt`.
The dependency set was installed and checked in an isolated Python 3.14.3
environment; the full suite passed 175 tests after the P3 merge and P4 combined-flow
test. The real smoke check uses an
in-memory database and never modifies the committed assignment database:

```powershell
python docs/a6-person-4/smoke_local_ui.py --model model_cache/models/Qwen--Qwen2-0.5B-Instruct
python manage.py test --settings=hestia_config.settings.development --noinput
python manage.py check --settings=hestia_config.settings.development
```

No paid API was called by P4. Person 3's Groq provider is merged and is reached
from a saved Task's detail page. Configure `GROQ_API_KEY` privately for live use;
the earlier optional pre-save callable is unnecessary and remains disabled.
P4's smoke check verifies the combined path with real local inference and mocked
Groq HTTP, including disclosure-before-call and no plan writes.
See [closeout.md](closeout.md) for the final verification scope and review audit.
P4 completed the larger-model tests separately. Main PR #31 now uses different
balanced size bands and retains the small-model selection. P1/the team decides
whether to keep that plan or consolidate the new results under the original
ranges. See [large-models.md](large-models.md); do not blindly aggregate both P4 CSVs.
