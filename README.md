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

Account login/signup/verification uses Django/allauth. After signup/sign-in, new users can create a household at `/households/create/`
and become its owner without admin provisioning. Existing users can create
another household from the shared picker. Signup never auto-enrolls users in a
sample household. Invitations and member management remain later phases. Do not use the tracked
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
they are outside the product's runtime and release package. The retained Ask Hestia feature uses its bundled product-local handbook,
with the source labeling and inference behavior described below.


## Integrated demo

The demo combines the cleaned task board and Insights with shared grocery batches, expiry reminders, receipt review and browser voice entry. All use the same selected household. Switch households using the shared picker; direct foreign-household URLs are denied even for users belonging to both households.

Ask Hestia is retained at `/tasks/ask/` and answers from the bundled example handbook, not live household data. Its required corpus ships under `workflows/services/handbook_data`; inference remains lazy. Grocery meal suggestions use the same local generator and inference lock. Provider behavior is tested with mocks; local model availability is an environment requirement.

The integrated branch requires the new grocery migration; run `python manage.py migrate` against a separate demo database. Do not migrate or seed the grading environment. Assignment 8/9 originals remain in the repository, while product archives exclude research folders.
