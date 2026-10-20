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

On a Mac with limited memory, a smaller benchmarked option is
`HF_BRAIN_DUMP_MODEL=HuggingFaceTB/SmolLM2-360M-Instruct`, with
`HF_BRAIN_DUMP_DEVICE=mps` when Apple GPU acceleration is available. Model
weights still download automatically through Transformers. Keep these choices
in the private `.env`; generation quality varies, so review the drafts.

If the local model returns JSON that cannot be parsed, Hestia regenerates once
with an explicit single-object/single-`tasks`-array formatting reminder. Duplicate
keys remain rejected; output is not silently repaired. A second invalid response
returns an error. Runtime/loading failures are not retried, and this retry never
calls Groq or writes tasks. The notebook benchmark outputs remain unchanged.

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

## External Groq action plans (Person 3)

Person 3 implemented a separate external-AI feature for saved tasks. Add the
provider credentials only to the ignored `.env` file:

```dotenv
GROQ_API_KEY=your-real-key
GROQ_MODEL=openai/gpt-oss-20b
```

Open a saved task as an active household member and choose **Create an AI action
plan**. The review page explains that the task title, type, priority and description
will be sent to Groq. The provider is called only after the user submits that page.
The validated plan is displayed for review and is not saved as tasks or subtasks.

The HTML route is `GET/POST /tasks/<pk>/action-plan/`; the protected JSON route is
`POST /api/tasks/<pk>/action-plan/`. Both enforce login, active membership, CSRF,
input limits and a short repeat-request cooldown. Provider credentials, raw error
bodies and household membership data are never returned or sent. Network, quota,
credential and malformed-output failures produce bounded status codes and safe
messages. See `docs/a6-person-3/README.md` for the complete contract and evidence.

## Final team benchmark and Person 4 handoff

Person 1 combined the four canonical benchmark CSV files into the final
`llm-test/ai_prototype.ipynb`; the repository-root `ai_prototype.ipynb` is an
identical convenience copy. The notebook has the required model-download cell,
shared inputs and prompt modes, schema checks, all 120 reviewed runs, comparison
tables, charts and the final Size vs Quality analysis. Each of the 15 models has
eight runs: two fixed inputs across zero-, one-, few- and many-shot prompting.

Three additional public models were selected under the user's instruction to use
any models not already completed by teammates:

| Model | Approximate parameters | Publisher source |
| --- | ---: | --- |
| Qwen/Qwen2-0.5B-Instruct | 0.5B | https://huggingface.co/Qwen/Qwen2-0.5B-Instruct |
| HuggingFaceTB/SmolLM-360M-Instruct | 0.36B | https://huggingface.co/HuggingFaceTB/SmolLM-360M-Instruct |
| Qwen/Qwen3-0.6B | 0.6B | https://huggingface.co/Qwen/Qwen3-0.6B |

These are distinct model IDs from teammates' completed Qwen2.5 and SmolLM2 runs.
The final roster uses five fixed, non-overlapping parameter ranges with exactly
three tested models in each range: under 0.2B, 0.2B to under 0.6B, 0.6B to under
1.6B, 1.6B to under 3.5B, and 3.5B or larger. Person 1 benchmarked OPT-125M to
complete the smallest range with real evidence. The notebook cites the Hugging
Face Open LLM Leaderboard as the research starting point, links every model card,
and does not make claims about models larger than the tested 7.62B limit.

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

## P4 larger-model extension

P4 also completed actual Colab Tesla T4 inference for Falcon3-7B-Instruct,
Qwen2.5-14B-Instruct, Phi-3-medium-4k-instruct and Qwen3-14B: **32 unique
generations**, each with the same two inputs and four prompt modes. Weights
use NF4 double quantization, FP32 computation/non-quantized modules and eager
attention; generation is greedy with 220 new tokens and Qwen3 thinking disabled.

| Model | Schema valid | Mean generation | Reviewed quality /10 |
| --- | ---: | ---: | ---: |
| Falcon3-7B | 7/8 | 17.453 s | 8.500 |
| Qwen2.5-14B | 8/8 | 20.778 s | 9.500 |
| Phi-3-medium-4k | 3/8 | 33.919 s | 6.875 |
| Qwen3-14B | 8/8 | 21.801 s | 9.250 |

The [executed review notebook](llm-test/person4_large_results_review.ipynb)
contains every raw response and explicit criterion review. Original unscored
CSV/metadata are preserved, with hashes in the review audit. Scores are
assistant-assisted judgments, not independent human signoff. GPU/quantized
timings cannot be treated as a controlled CPU/native or paid-API comparison.
See the [reproduction notebook](llm-test/person4_large_models_colab.ipynb),
[32-run CSV](a6_results/person4_large/person4_large_results.csv), and
[handoff](docs/a6-person-4/large-models.md).

Main PR #31 adopted the different balanced bands described above while these
tests were running. That final notebook selection is preserved; the new runs
remain separate evidence until P1/the team chooses whether to incorporate
them under the original large/above-10B ranges. Do not concatenate both P4
result sets without a deliberate 15-model selection. The earlier P4 notebook
is preserved at `llm-test/person4_small_reference.ipynb`; P4's builder/executor
now use that path to avoid overwriting P1's final notebook.

The integrated Groq flow is reached after task confirmation from a saved
task's detail page. P4's older optional pre-save callable remains disabled and
is not needed for P3's `generate_action_plan(Task)` interface. P4's combined-flow
test uses real view/service code with mocked Groq HTTP; it does not claim a paid
call. See `docs/a6-person-4/closeout.md` for that test and remaining visual QA scope.

## Final verification

```powershell
python manage.py test --settings=hestia_config.settings.development --noinput
python manage.py check --settings=hestia_config.settings.development
```

Tests cover the original Task flow, local Brain Dump API, signed review drafts,
editing/removal, explicit confirmation, atomic saves, membership boundaries,
malformed model output, CSRF and the external Groq action-plan feature. Real model
benchmark evidence and environment details are stored under `a6_results/`.

Final integrated verification on October 18, 2026:

- **175 Django tests passed** after P4's combined-flow test; system checks reported no issues.
- Both `ai_prototype.ipynb` copies executed all 12 code cells with no errors.
- The notebook validated 120 unique runs, 15 distinct models, eight runs per model,
  and exactly three models in each of five balanced parameter-size categories.
- A real local-model flow generated editable drafts and saved only explicitly
  confirmed tasks; see `a6_results/person4_django_integration.json`.
- A real Groq request and browser flow produced a validated action-plan preview;
  see `docs/a6-person-3/evidence/`.
- `.env`, model weights and model caches remain ignored. No credentials or model
  weight files belong in the repository.
- P4's larger-model harness passed five tests; its separate review notebook
  executed all four code cells without errors and verified all 32 export rows.

The remaining work is the team's final clean-clone/manual submission check and
submission of the GitHub repository link. Production environments must provide
their own secrets and confirm that outbound Groq requests are permitted.
