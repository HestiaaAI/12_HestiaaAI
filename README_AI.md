# Hestia AI Household Brain Dump — Person 4 (A6)

This feature adds input → editable review → explicit confirmation → existing Task
records. It does not implement inference, benchmarks, or an external AI provider.

## Demonstration

Use the project's existing development environment and `.env` (copy the safe
placeholders in `.env.example` if needed). No additional packages are needed for
the mock UI. Run migrations and start Django as usual:

```powershell
python manage.py migrate --settings=hestia_config.settings.development
python manage.py runserver --settings=hestia_config.settings.development
```

Sign in with an existing verified Hestia account. The account needs an active
`Membership` in a `Workspace`; an administrator can manage these through Django
admin. Signup alone does not create a household membership.

1. Choose **AI Brain Dump** in navigation (`ai_tasks:brain-dump`, `/tasks/ai/`).
2. Select your household and enter: “Guests are coming tomorrow, the kitchen is
   messy, we need groceries, and the bathroom tap is leaking.”
3. Click **Organize My Tasks**. Default mock mode always returns three example
   tasks and labels this clearly; it does not interpret the paragraph.
4. Edit titles, types, priorities, and descriptions. Check **Remove this task**
   to exclude a card. Removal works without JavaScript and is applied on submission;
   the card stays visible so the decision can be reversed before saving.
5. Check the confirmation box and click **Save approved tasks**. Kept tasks are
   saved together, then Django redirects with a success message. Open **Task board**
   to see them. Duplicate titles must be renamed or removed.

## Data input and preprocessing

`BrainDumpForm` trims whitespace, rejects empty input, and limits paragraphs to
4,000 characters. Only workspaces with an active membership for the signed-in
user are selectable. The trimmed paragraph is passed to `get_suggestions(text)`.

The adapter expects a Python dictionary with `tasks` (a list of dictionaries)
and `error` (`None` for success). Each suggestion requires string fields `title`,
`task_type`, `priority`, and `description`. It accepts at most 20 tasks and treats
an empty list as an empty state. Malformed batches are rejected as a whole with a
generic error; raw provider output is never shown. Extra keys are discarded.

`ReviewTaskForm` subclasses the existing `TaskCreateForm`, reusing its title
cleaning and model-backed field validation. Types and priorities come from
`Task` choices. Title length is the model's 200-character limit. The model's
description currently has no maximum; this UI imposes a 5,000-character cap
(or the model limit if one is introduced). Every task is presented for review.

## Safety guardrails

- Generation and GET requests never create Task records. Saving requires a POST,
  the explicit confirmation checkbox, valid kept forms, and a valid review draft.
- CSRF protection follows Django middleware and token conventions. Only GET and
  POST are accepted; login is required and feature responses are not cached.
- Draft metadata is signed, expires after one hour, and is bound to the current
  user and session. Only the latest successful generation in a session is saved;
  generating another review replaces the previous one. Successful saving clears
  the draft, preventing ordinary refresh/replay submissions. Simultaneous requests
  are still subject to the existing database title constraint.
- Raw paragraphs and suggestion content are not persisted in the session. Only
  user/workspace IDs, task count, and a random nonce are stored for the draft.
- Membership is rechecked before saving. Workspace and creator come from the
  verified draft and current membership. Browser/AI relationship IDs are ignored.
  Other task relationships remain unset. This feature restricts workspaces even
  though the existing assignment Task board exposes demo households more broadly.
- Kept titles must be unique both within the batch and within the household.
  A transaction rolls back the entire batch on an integrity error; no partial
  batch is saved. No TaskOccurrence or assignment is automatically created.
- Template autoescaping remains enabled. No `eval`, arbitrary code, or unsafe
  HTML rendering is used. The UI does not parse JSON strings; Person 2's service
  must safely parse model output into the agreed dictionary before returning it.
- Missing services, invalid output, and model exceptions show a generic error;
  other Hestia pages remain available. Provider errors, secrets, and household
  input are not logged by this feature.

## Person 2 integration: local service

Person 2 retains ownership of `workflows/ai_service.py` and `ai_prompts.py`.
Provide this synchronous interface:

```python
def analyze_brain_dump(text):
    return {
        "tasks": [{"title": "Clean the kitchen", "task_type": "CHORE",
                   "priority": "HIGH", "description": "Clean the kitchen."}],
        "error": None,
    }
```

Once available, add this Django setting in the appropriate deployment settings:

```python
HESTIA_BRAIN_DUMP_BACKEND = "local"
```

It defaults to `"mock"`. This is a Django setting, not an environment variable
automatically read by the current configuration. Local mode lazily imports
`analyze_brain_dump` and applies the same validation and mandatory review.
It never silently substitutes mock suggestions after a local-service failure.

The provider owns inference timeouts/resource limits and safe structured-output
parsing. Inference currently runs synchronously in the request; production use
needs an appropriately bounded model runtime. Person 2 should coordinate the
compatible `torch`/`transformers` versions and installation for the target
platform. This UI adds no inference dependencies and downloads no model weights.

## Person 3 integration: external task breakdown

No external requests or provider stubs are included. The intended insertion point
is the review stage in `ai_views.py`, after `get_suggestions()` and before explicit
confirmation. Person 3's eventual `break_down_task(title, description)` contract
needs an agreed return schema, error handling, and timeout policy before wiring.
Suggested steps can then be reviewed as description text using the same form cap
and save rules; the existing Task model has no separate steps field. If steps
require sending household text to an external provider, the UI should disclose
that and require a deliberate user action. Nothing should bypass review or
auto-save. No Person 3 provider files have been changed.

## Git hygiene and shared changes

`.env` remains ignored. Store actual secrets only in private environment
configuration; never paste them into source, logs, or this README. `.env.example`
already has safe placeholders and remains unchanged. `.gitignore` retains its
existing rules and adds `*.bin`, `*.safetensors`, `*.pt`, `*.pth`, `model_cache/`,
and `llm-test/models/`. Ignore rules do not untrack any previously tracked files.

Shared changes are one URL include in `hestia_config/urls.py`, one navigation link
in `templates/base.html`, and the appended ignore patterns. Task models, existing
forms/views, authentication configuration, requirements, and teammates' AI files
are untouched. Feature code, styles, templates, and tests live in separate files.

## Verification

```powershell
python manage.py test workflows --settings=hestia_config.settings.development --noinput
python manage.py check --settings=hestia_config.settings.development
```

`workflows/test_ai.py` exercises input limits, authentication, methods, mock review,
enums/lengths, malformed/unavailable/empty output, no pre-confirmation writes,
edits, removal, duplicate batch validation, atomic rollback, protected attribution,
membership changes, expired/tampered/replayed drafts, escaping, and CSRF checks.
Existing workflow tests cover the original Task functionality.

Verified on this branch: the complete Django suite passed (136 tests), Django
system checks reported no issues, and `git diff --check` passed. Input and review
templates also rendered against a temporary in-memory database. Browser visual
inspection was attempted but the browser could not connect to the local preview
server; desktop/mobile appearance has not been visually verified.
