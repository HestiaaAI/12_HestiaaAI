# Person 4 handoff

- UI and integration guide: [README_AI.md](../../README_AI.md)
- Executed contribution notebook: [llm-test/ai_prototype.ipynb](../../llm-test/ai_prototype.ipynb)
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
python docs/a6-person-4/execute_notebook.py
```

The executor expects the local `.venv` kernel registered by the command above.
Alternatively open the notebook normally in Jupyter with the matching environment.

For the complete Django app use Python >=3.12 and root `requirements.txt`.
The dependency set was installed and checked in an isolated Python 3.14.3
environment; the full suite passed 151 tests. The real smoke check uses an
in-memory database and never modifies the committed assignment database:

```powershell
python docs/a6-person-4/smoke_local_ui.py --model model_cache/models/Qwen--Qwen2-0.5B-Instruct
python manage.py test --settings=hestia_config.settings.development --noinput
python manage.py check --settings=hestia_config.settings.development
```

No paid API was called. Person 3's provider backend is still required for live
external steps; the P4 UI's optional callable contract is implemented/tested.
The team must also reconcile the original matrix's category counts and complete
the missing larger-model categories. These three extra small-model runs do not
stand in for a completed five-category team benchmark.
