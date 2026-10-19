# Hestia AI — Brain Dump (A6)

Hestia turns one free-text household brain dump into structured `Task` drafts
using a local Hugging Face model. Drafts are reviewed before save (Person 4 UI).
Person 3 adds an external API action-plan feature separately.

## Data input

Signed-in users submit text via `POST /api/ai/brain-dump/` with JSON
`{"text": "..."}` (or the Person 4 form that calls this API). The endpoint does
**not** write `Task` rows; it returns `"saved": false`.

## Preprocessing

- Strip whitespace; reject empty text and dumps over 4000 characters.
- Build the **shared team prompt** from `ai_prototype.ipynb` on `main`
  (`SYSTEM_INSTRUCTION`, few-shot examples, BD-style `Household message` /
  `JSON output:` formatting) in `workflows/services/brain_dump.py`.
- Generation uses `do_sample=False` and `max_new_tokens=220`.

## Safety guardrails

| Guard | Behavior |
| --- | --- |
| Auth | API requires a Django session. |
| Length cap | 4000 characters. |
| Schema | Must be `{"tasks":[...]}` with `title`, `task_type`, `priority`, `description`. |
| Enums | Must match `Task.TaskType` / `Task.Priority` (unknown values coerced for drafts). |
| Broken JSON | HTTP 422; nothing saved. |
| Confirm before save | Extraction never creates tasks. |
| Secrets / weights | `.env` only; `*.safetensors` / HF caches gitignored. |

## Local LLM integration (Person 2)

- Default model: `TinyLlama/TinyLlama-1.1B-Chat-v1.0` (Person 2 roster).
- Override with `HF_BRAIN_DUMP_MODEL` / `HF_BRAIN_DUMP_DEVICE` / `HF_BRAIN_DUMP_SHOT_MODE`.
- Entry point: `workflows.services.hf_local.extract_tasks(text)`.
- HTTP: `POST /api/ai/brain-dump/`.
- Benchmark CSV for Person 1 merge: `a6_results/person2_benchmark_results.csv`.

## External API (Person 3)

Document the chosen provider (Gemini / Groq / OpenRouter / etc.) and action-plan
endpoint here when integrated.
