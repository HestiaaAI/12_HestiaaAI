# Hestia AI Household Brain Dump — A6

## Run the integrated app

Use Python 3.12 or newer for the current complete requirements (verified separately
on Python 3.14.3). The team benchmark notebook uses a separate Python 3.11 environment.

```powershell
python -m pip install -r requirements.txt
# Copy .env.example to .env and set a private SECRET_KEY.
python manage.py migrate --settings=hestia_config.settings.development
python manage.py runserver --settings=hestia_config.settings.development
```

Sign in using a verified Hestia account with an active household Membership, then
choose **AI Brain Dump** (`ai_tasks:brain-dump`, `/tasks/ai/`). Signup alone does
not create a household membership; an administrator can add it in Django admin.

## Data input

The user selects an accessible household and writes a natural-language paragraph.
For example: "Guests are coming tomorrow, the kitchen is messy, we need groceries,
and the bathroom tap is leaking." The UI captures it through a CSRF-protected POST.

Generation creates editable cards containing title, type, priority, and description.
Check **Remove this task** to exclude a card; it stays visible until submission so
removal can be reversed. Check the explicit confirmation and choose **Save approved
tasks**. Only kept cards are saved, together, using the existing Task model and
TaskCreateForm-derived validation. Success redirects to the input page with a
message and a link to the Task board. No occurrences/assignments are created.

## Preprocessing

- Trim whitespace and reject empty paragraphs or more than 4,000 characters.
- Restrict household selection to the user's active memberships.
- Call Person 2's `workflows.services.hf_local.extract_tasks(text)` lazily through
  `workflows/ai_adapter.py`. The provider uses the team's notebook system prompt,
  examples, and deterministic generation, with a configurable 220-token default.
- The service parses JSON into a dictionary. The UI accepts at most 20 task
  dictionaries and revalidates every title, type, priority, and description.
- Model choices supply allowed enums; title length is the actual model's 200
  characters. Description has no model maximum, so the UI caps it at 5,000
  characters (or the model maximum if later introduced). No eval or Python-literal
  parsing is used. Unknown/protected keys never reach the ModelForm.
- Person 2's parser may normalize unknown enums to safe defaults; the UI strictly
  validates the resulting draft values. The UI does not show provider raw text.

## Local model configuration (Person 2)

```dotenv
HESTIA_BRAIN_DUMP_BACKEND=local
HF_BRAIN_DUMP_MODEL=TinyLlama/TinyLlama-1.1B-Chat-v1.0
HF_BRAIN_DUMP_DEVICE=cpu
HF_BRAIN_DUMP_MAX_NEW_TOKENS=220
HF_BRAIN_DUMP_SHOT_MODE=few
HF_TOKEN=
HF_HOME=model_cache/huggingface
```

These are read by Django settings from the private environment. First successful
inference downloads weights through Transformers; loading is lazy on the first
extraction request, not at server startup. Subsequent requests reuse the service's
cached model. First use therefore needs network access and can be slow. Model
selection remains configurable; the integration does not silently change Person
2's chosen default. Their standalone API is `POST /api/ai/brain-dump/`, returning
unsaved drafts. The UI calls the same service directly, avoiding an internal HTTP
round trip. Person 2's provider files are preserved from their pushed branch.

Set `HESTIA_BRAIN_DUMP_BACKEND=mock` only for a deterministic UI demo. A visible
banner states that three fixed sample tasks are returned regardless of input.
Local failures never silently fall back to mock output.

## Safety guardrails

- Login, active household membership, POST-only mutations, and CSRF protection.
- No generation request writes Task rows. Saving requires valid kept forms,
  explicit confirmation, and a signed draft bound to the current user/session.
- Draft metadata expires after one hour. A new generation replaces the session's
  previous draft; successful saving clears it. Raw paragraphs/suggestions are not
  stored in the session. Ordinary refresh/replay cannot repeat a completed save.
- Workspace and creator are assigned server-side; browser/AI relationship IDs are
  ignored. Membership is checked again inside the save transaction.
- Duplicate titles within the batch or existing household cause validation errors.
  Integrity failures roll back the entire batch. No partial save is accepted.
- Autoescaping remains enabled; provider output is plain editable text.
- Malformed/unavailable local output produces a generic error without exposing
  provider exceptions or secrets. Other Hestia functionality remains usable.
- The UI logs no raw input or suggestions. Responses have no-cache headers.
- `.env`, model weights, and cache directories stay ignored. Keep credentials
  private; `.env.example` contains placeholders only.

Inference is synchronous. Person 2 owns resource limits/timeouts; production
requires an inference queue or isolated worker and load testing. This UI does not
claim prompt-injection resistance inside a model; validation and human review
bound what can reach Task storage. The standalone Person 2 API's error responses
are their existing implementation, separate from the UI's generic errors.

## Person 3: optional external task breakdown

No provider backend or API key is invented. Person 3 can expose:

```python
def break_down_task(title, description):
    return {"steps": ["First action", "Second action"], "error": None}
```

Configure the server-owned dotted callable when that provider is ready:

```dotenv
HESTIA_TASK_BREAKDOWN_CALLABLE=workflows.services.task_breakdown.break_down_task
```

The review cards then display **Suggest steps**, with a disclosure that the title
and description will be sent to the configured external provider. Only that
explicit POST calls it. The adapter accepts 1–10 nonempty string steps, at most
500 characters each, and enforces the final description cap. Steps are appended
to the editable description; confirmation is cleared and nothing is saved.
Errors preserve edits. The callable is disabled by default; the actual external
provider remains Person 3's dependency and has not been live-tested by P4.

## P4 model testing and team handoff

`llm-test/ai_prototype.ipynb` is P4's reproducible contribution. It has an early
model-download cell, the shared two inputs/four prompting modes, actual raw
outputs and timings, and a results summary. The root `ai_prototype.ipynb` remains
Person 1's existing notebook. P1's merge cell reads
`a6_results/person4_benchmark_results.csv` without requiring concurrent edits.

Three additional public models were selected under the user's instruction to use
any models not already completed by teammates:

| Model | Approximate parameters | Publisher source |
| --- | ---: | --- |
| Qwen/Qwen2-0.5B-Instruct | 0.5B | https://huggingface.co/Qwen/Qwen2-0.5B-Instruct |
| HuggingFaceTB/SmolLM-360M-Instruct | 0.36B | https://huggingface.co/HuggingFaceTB/SmolLM-360M-Instruct |
| Qwen/Qwen3-0.6B | 0.6B | https://huggingface.co/Qwen/Qwen3-0.6B |

These are distinct model IDs from teammates' completed Qwen2.5 and SmolLM2 runs.
They replace the original P4 large-model roster locally because this computer has
15.5 GiB RAM and no CUDA GPU. They do NOT satisfy the original missing large-model
categories; the team must reconcile the final 15-model/five-category matrix.
The existing roster already has category counts 4/3/3/3/2, rather than exactly
3 per category. Additional small runs do not fix that team-level requirement.

```powershell
# Separate Python 3.11 benchmark environment
python -m pip install -r docs/a6-person-4/requirements-benchmark.txt
python docs/a6-person-4/benchmark.py
```

The runner uses the exact P2/P1 prompt/schema functions and outputs the same CSV
columns. Every result is a real generation, checkpointed after each response.
The environment JSON records versions, model revisions, CPU/precision/threads,
and generation options. Qwen3 thinking is explicitly disabled for direct JSON;
greedy decoding follows the team contract, which differs from vendor sampling
recommendations. Do not compare timing across teammates' different hardware as
if it were a controlled speed experiment. Quality scores must come from output
review, not lexical-overlap heuristics.

P4's Part 3 analysis is in `docs/a6-person-4/local-vs-api.md`, with an entry in
`docs/notes/notes.txt`. API costs are sourced estimates, not measured paid calls.

## Verification and remaining team dependencies

```powershell
python manage.py test --settings=hestia_config.settings.development --noinput
python manage.py check --settings=hestia_config.settings.development
```

Tests cover the original Task flow, signed review drafts, editing/removal,
confirmation, atomic rollback, membership boundaries, malformed output, CSRF,
and the optional external-breakdown contract without paid calls. Real model
benchmark evidence and environment details live in `a6_results/`.

Remaining team dependencies are Person 3's actual external provider, P1's final
matrix consolidation/category reconciliation, and final team submission review.
No model weights, private environment files, demo database, or credentials belong
in the commit.

Verified on October 18: **151 Django tests passed** in the full Python 3.14.3
requirements environment; system checks found no issues, and all 51 installed
packages passed dependency compatibility checks. A separate real-model smoke test
using downloaded Qwen2 weights and CSRF-enforced requests produced three drafts,
saved zero before confirmation, excluded one, and saved two approved tasks with
correct attribution and edits. See `a6_results/person4_django_integration.json`.
This is programmatic verification; browser visual QA remains unverified because
the available browser could not reach the host's local demo server.
