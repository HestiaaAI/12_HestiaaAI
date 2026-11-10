# Hestia

Hestia helps a household find and create shared tasks, organize rough notes into
reviewable task drafts, plan a saved task, and inspect its own task summaries.
Household selection controls every product page and export.

## Run locally

Use Python 3.13 and the existing project environment, or create an environment
and install `requirements.txt`. Configure a local nonsecret `SECRET_KEY` through
the environment. For the current SQLite development configuration:

```sh
export DJANGO_SETTINGS_MODULE=hestia_config.settings.development
export SECRET_KEY=replace-with-your-local-development-secret
python manage.py migrate
python manage.py runserver
```

Account login/signup/verification uses Django/allauth. At this phase, household
records and memberships must be provisioned through authorized Django admin or
controlled fixtures. Signup does not automatically enroll users in a sample
household. Creation and invitations are later phases. Do not use the tracked
historical database as a source of real accounts or production data.

## Current product routes

- `/` — public landing; signed-in users continue to Tasks or household selection.
- `/households/` — select from current active memberships.
- `/tasks/manage/` — search/filter and create tasks in the selected household.
- `/tasks/<id>/` — task details and action-plan entry.
- `/tasks/ai/` — generate, review and explicitly approve task drafts.
- `/tasks/insights/` — real household totals and accessible priority/type summaries.
- `/tasks/export.csv` — private CSV download from Insights.
- `/lookup/` — secondary public catalogue comparison with selected-household rows.

AI task drafts use the configured local Hugging Face provider; weights are loaded
only after an authorized explicit generation request. Ordinary pages do not load
Torch/Transformers. `HESTIA_BRAIN_DUMP_BACKEND=mock` is for clearly labeled test or
preview fixtures only. Task action plans use the configured Groq provider and
never save automatically. The optional bounded task-step hook is configured by
`HESTIA_TASK_BREAKDOWN_CALLABLE`. Do not put credentials in source control.

## Verify and integrate

```sh
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python manage.py check
python manage.py makemigrations --check --dry-run
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python manage.py test households workflows api reports analytics
```

See [the access/UI contract](docs/household-access-contract.md),
[performance measurements](docs/household-performance.md), and
[verification record](docs/household-phase1-verification.md).

Product archives use `git archive` and `.gitattributes` to omit research packages,
notebooks, assignment evidence, optional experiment requirements and the tracked
historical SQLite database. No research/data files are automatically deleted.
Historical experiments remain in source control and use their own requirements;
they are outside the product's runtime and release package. The retired handbook
experiment depended on the old product adapter and must be reproduced from the
Phase 1A revision, rather than restored as a production feature.
