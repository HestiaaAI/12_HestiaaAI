# A6 Person 3 - Groq action plans and benchmark handoff

Branch: `dev-ddhene2-a6-external-ai`. Provider: Groq; default model:
`openai/gpt-oss-20b`. This is a separate AI feature from P2's local task extraction.

## Run locally

The Django feature uses the existing `requests` and `django-environ` requirements;
it does not need a Groq SDK or download local model weights.

1. Install the project requirements into the existing virtual environment.
2. Create a key at <https://console.groq.com/keys> and keep it in the untracked
   project `.env`:

   ```dotenv
   GROQ_API_KEY=your-real-key
   GROQ_MODEL=openai/gpt-oss-20b
   ```

3. Run migrations and the development server as usual. Sign in as a user with an
   **active Membership** in the task's Workspace. Merely being logged in or staff
   does not authorize disclosing another household's task to Groq.
4. Open a task's detail page and choose **Create an AI action plan**. The link
   appears only to active members. Review the disclosure, then submit the form.
   GET never calls Groq. The generated plan remains a preview; no Tasks/subtasks
   are created, edited or executed automatically.

The current shared task board allows creation without joining a Workspace. If a
test account lacks membership, assign it to the fictional demo household using
the existing admin interface before testing this external disclosure feature.
Do not remove membership checks to work around that setup requirement.

For later PythonAnywhere rollout: set the same Groq environment variables on the
server, pull merged code, collect static if needed, and reload. Check whether the
hosting plan permits outbound `api.groq.com` HTTPS requests; network failures are
reported as 502. A successful local call is not production deployment evidence.

## Contract for P4's UI

HTML: `GET/POST /tasks/<pk>/action-plan/`, named `workflows:task-action-plan`.
API: `POST /api/tasks/<pk>/action-plan/`, named `api:task-action-plan`.

The API uses the **saved** Task ID. It ignores request-supplied task descriptions,
workspace IDs or provider URLs. P4 can offer a link after a reviewed Brain Dump
task is saved. Use the user's Django session and standard CSRF header:

```javascript
// taskId is an existing saved Task. csrfToken comes from Django's rendered form.
const response = await fetch(`/api/tasks/${taskId}/action-plan/`, {
  method: 'POST',
  headers: {'X-CSRFToken': csrfToken},
  credentials: 'same-origin'
});
const result = await response.json();
// Handle response.ok before displaying result.plan; use textContent, not innerHTML.
```

Successful response shape:

```json
{
  "task_id": 1,
  "provider": "Groq",
  "model": "openai/gpt-oss-20b",
  "plan": {
    "summary": "Short overview",
    "steps": [{"title": "First step", "description": "What to do"}],
    "supplies": [],
    "cautions": []
  }
}
```

| Result | HTTP status | Behavior |
| --- | --- | --- |
| Anonymous API request | 401 | No provider call |
| Non-member, inactive member or unknown task | 404 | Generic JSON; no task disclosure |
| Invalid Task fields / description over 4,000 chars | 400 | No provider call |
| Missing/invalid CSRF token | 403 | Django's standard CSRF rejection |
| Repeated request within 15 seconds | 429 | No second provider call |
| Groq quota/rate limit | 429 | Safe message; no automatic paid retry |
| Missing key / rejected provider credentials | 503 | Site-owner configuration message |
| Connection error, provider error, malformed/refused/truncated plan | 502 | No partial plan |
| Connect/read timeout | 504 | Safe retry-later message |

All page and API plan responses use `no-store`. Cooldown uses Django cache and is
per process with the default LocMemCache; use a shared cache and provider spend
limits for deployment at scale. Plans are not cached. Title (200), description
(4,000), choice fields, exact output keys, step count (1-10), string lengths and
list lengths are validated. Duplicate JSON keys, extra prose, null fields and
invalid types are rejected. Only title, type, priority and description are sent;
workspace/membership information and source documents are excluded.

Task text is an untrusted JSON user message, separated from system instructions.
There are no model tools, code execution, URLs to fetch, or automatic writes.
Django autoescapes the displayed plan. Prompts discourage hazardous DIY and
instruct professional help, but validation cannot establish factual correctness
or guarantee safety; the user must review every suggestion.

## Four-model benchmark handoff for P1

Only P1 edits the final notebook. `llm-test/person3_benchmark.py` reads its literal
constants without executing notebook cells. It preserves the same two inputs,
system instruction, 0/1/2/3 examples, prompt formatting, 220-token limit,
deterministic generation and CSV columns. It records environment information and
the notebook SHA-256. Human quality scores start blank and require review.

| Assigned HF model | Parameters (P1 roster) | FP16 weights alone, approximately | Conservative device-capacity estimate |
| --- | ---: | ---: | ---: |
| microsoft/Phi-3.5-mini-instruct | 3.82B | 7.12 GiB | 12.0 GiB |
| meta-llama/Llama-3.2-3B-Instruct | 3.21B | 5.98 GiB | 10.4 GiB |
| Qwen/Qwen2.5-7B-Instruct | 7.62B | 14.19 GiB | 21.9 GiB |
| mistralai/Mistral-7B-Instruct-v0.3 | 7.25B | 13.50 GiB | 20.9 GiB |

Weights alone = parameters x 2 bytes / 2^30. The preflight estimate adds 40%
loading/activation allowance and 2 GiB for runtime/KV overhead; it is an estimate,
not measured peak usage. CPU FP32 needs more memory. A 24+ GiB GPU environment is
the recommended starting point for these unquantized runs. Actual requirements
vary by software, context and runtime. Quantized measurements use the separately
labeled NF4 mode below; do not silently mix them with P1's native-precision baseline.

This Apple M3 has **8.0 GiB unified memory**. No local inference of these four
models was attempted. The four rows in `a6_results/person3_preflight.csv` record
resource checks, not measured output quality or latency. They deliberately do
not match P1's `person*_benchmark_results.csv` merge glob. Llama additionally
requires its Hugging Face access/license approval. Do not claim this part is
complete until actual generation results and reviews have been submitted.
The user initially deferred local runs, then obtained a Colab Tesla T4 with
15,360 MiB VRAM. The NF4 runner is prepared for that environment; successful GPU
generations have not yet been verified. No fabricated benchmark CSV is supplied.

### Colab T4: optional NF4 inference

For the assigned T4, install `llm-test/requirements-person3-colab.txt` and use:

```bash
python llm-test/person3_benchmark.py --run --device cuda --precision nf4
```

This uses bitsandbytes 4-bit NF4 weights, double quantization, FP16 computation,
eager attention and one model at a time. It is inference, not fine-tuning. Same
inputs, prompts, output format and deterministic 220-token generation are retained.
The memory estimate is a heuristic, not a guarantee that every GPU run succeeds.
CUDA timing is synchronized before/after generation.

Output: `a6_results/person3_nf4_results.csv` and matching `.metadata.json`.
These do not match P1's automatic native-results glob. Precision is also recorded
in each row's review notes and in metadata alongside dependency versions. P1
should explicitly import and label these results in the final comparison. Different
hardware/precision/attention can affect speed and quality; NF4 measurements are
not evidence of native FP16 behavior. All four P3 models should use the same mode.

Colab's preinstalled Gradio/Diffusers may warn about Hub versions after installing
the Transformers 4.x benchmark requirements. Those packages are not used here.
Restart the session after dependency changes, then verify CUDA and imports. Do not
change unrelated packages or put a Hugging Face token in notebook source/output.
Llama still requires approved access regardless of quantization.

On an adequate GPU machine, clone this branch/repository and run:

```bash
python -m pip install -r llm-test/requirements-person3.txt
# For the gated Llama model, obtain access on its HF model page first.
# Authenticate using the Hugging Face CLI; never put the token in this repository.
hf auth login
python llm-test/person3_benchmark.py --run --device cuda
```

`--run` downloads weights automatically via Transformers to the HF cache, runs
one model at a time and flushes each row to
`a6_results/person3_benchmark_results.csv`. Copy a reviewed CSV before rerunning,
because a new run overwrites it. Use `--model MODEL_ID` to rerun selected assigned
models. Read every raw response and fill in `quality_score_0_to_10` and
`review_notes` using P1's rubric; failed loads do not receive quality scores.
Send the reviewed CSV and metadata to P1 to rerun the notebook merge cells.

**P1 coordination issues found:** the merged notebook is at repository root,
whereas the detailed assignment asks for `llm-test/ai_prototype.ipynb` (the summary
also mentions `test/`; confirm the instructor's required location). Its category
counts are 4/3/3/3/2; the assignment requires 3 models per category. P1 should own
those corrections and update this runner's notebook path if the notebook moves.

## Part 3: Hybrid Potential

The full discussion, formulas and example table are appended under
`A6 - Person 3: Hybrid Potential` in `docs/notes/notes.txt`.

## Verification evidence

- A real Groq request using fictional guest-room input succeeded locally on
  October 18, 2026. `evidence/groq-smoke.json` contains the validated plan without
  credentials. The first response added optional embellishments; the prompt was
  subsequently tightened to request minimal task-specific steps.
- A real browser flow signed in as a fictional member, opened a task, explicitly
  submitted it to Groq and rendered the plan (HTTP 200). Desktop/mobile screenshots
  and `evidence/browser-smoke.json` record the local check. There were no browser
  console errors or mobile horizontal overflow. The test used a temporary SQLite
  database; the tracked assignment database was not modified.
- Regression tests mock failures deterministically; they are separate from this
  real provider evidence. Run:

  ```bash
  python manage.py test --settings=hestia_config.settings.production
  python -m unittest discover -s llm-test -p 'test_person3*.py'
  python llm-test/person3_benchmark.py --preflight
  ```

- Final local checks: **141 Django tests passed** with production settings;
  **7 benchmark-runner tests passed**; Django system checks and dependency checks
  were clean; no migrations or model changes were detected.

- Weight patterns (`*.bin`, `*.safetensors`, `*.pt`, `*.pth`, `*.gguf`, `*.onnx`),
  caches, `.env` and `.env.*` are ignored; `.env.example` remains trackable.
- Remaining external prerequisites: completed GPU benchmark generations/reviews;
  merged P2/P4 work; production rollout and production provider verification.

## Sources (checked October 18, 2026)

- Groq models/pricing: <https://console.groq.com/docs/models>
- Groq JSON object mode vs strict schema support: <https://console.groq.com/docs/structured-outputs>
- HF bitsandbytes/NF4 loading: <https://huggingface.co/docs/transformers/quantization/bitsandbytes>
- Phi: <https://huggingface.co/microsoft/Phi-3.5-mini-instruct>
- Llama access/model card: <https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct>
- Qwen: <https://huggingface.co/Qwen/Qwen2.5-7B-Instruct>
- Mistral: <https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3>

## Colab NF4 results received

All 32 P3 generations are now preserved in `a6_results/person3_nf4_raw/`. See [the review](nf4-benchmark-review.md) for provenance, draft scoring, and the unresolved Qwen anomaly. These results supersede earlier statements that GPU generations were pending. Qwen diagnostic execution and team approval of scores remain outstanding.

Qwen follow-up: all eight NF4/float32-compute reruns now pass strict schema checks. Raw results are in `a6_results/person3_nf4_fp32/`; original float16 runs and numerical probes remain separate. See `nf4-benchmark-review.md` for limitations and draft scoring. No benchmark scores have yet been approved by a human.

## Final P3 handoff prepared

The final assistant-assisted score review is complete. See [handoff/README.md](handoff/README.md) and `llm-test/person3_benchmark_handoff.ipynb`. The canonical 32-row `a6_results/person3_benchmark_results.csv` is ready for P1’s merge. Earlier draft CSVs and pending-review statements are superseded by this handoff. This does not claim independent human validation or complete team submission readiness.
