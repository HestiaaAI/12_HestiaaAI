# A6 Person 3: External task action plans

Goal: An authenticated household member selects an existing Task, explicitly
sends its title/type/priority/description to Groq, and reviews a structured
action plan. No generated text is saved or executed automatically.

## Design and interfaces

- `workflows/action_plans.py`: `generate_action_plan(task)` calls the fixed
  Groq HTTPS endpoint using requests. It validates input, provider envelopes,
  and the resulting JSON. `ActionPlanError` supplies a safe message/status/code.
- `workflows/action_plan_views.py`: HTML GET/POST at
  `/tasks/<pk>/action-plan/` and POST API at
  `/api/tasks/<pk>/action-plan/`. Both require active workspace membership;
  the API retains the existing API authentication middleware. CSRF remains on.
- `templates/tasks/action_plan.html`: task disclosure, explicit generate button,
  actionable errors, numbered steps, supplies and cautions. Autoescape all output.
- A task-detail link appears only for active household members. No base-template,
  brain-dump UI, local extraction model, final notebook, or database migration.
- Groq key/model are environment settings; use existing requests/django-environ.
  No additional application dependency is required. A 15-second per-user cache
  cooldown limits accidental duplicate calls (per-process with LocMemCache).

## Acceptance and implementation steps

1. Tests first: missing key, input limits, timeout, invalid key, rate limit,
   provider errors, malformed/truncated/refused output, exact JSON keys/types,
   escaping, authentication, membership/CSRF, GET never calls Groq, no DB writes.
2. Implement service, views, routes, template and task-detail entry point.
3. Reuse Person 1's notebook constants/prompts and exact CSV column contract in
   a separate Person 3 benchmark runner. Never edit the owner-controlled notebook.
   Benchmark 4 assigned models on adequate hardware; preserve honest errors.
4. Add model-weight ignore patterns before downloading anything. Keep credentials
   and model caches out of Git. Add Groq placeholders to `.env.example`.
5. Document setup, integration contract for P4, hybrid strategy/cost example and
   evidence gaps. Append only Person 3's Hybrid Potential section to notes.txt.
6. Run focused and full Django tests, system checks, benchmark-runner self-checks,
   Git hygiene checks and a browser smoke test. A real Groq call waits for the key.

## Known prerequisites and team issues

- Local computer: Apple M3, 8 GB RAM. Assigned 7B models exceed memory for the
  unquantized shared runner. Use a sufficiently large GPU environment for real
  generation; a preflight/error record is not a completed model benchmark.
  User explicitly deferred GPU model runs on October 18; keep the runner and
  preflight evidence, but do not download or attempt the four large models now.
- `meta-llama/Llama-3.2-3B-Instruct` requires Hugging Face license/access approval.
- P1's current 15-model roster has category counts 4/3/3/3/2, whereas the assignment
  requires 3 in each category. P1 owns any roster correction and final notebook
  placement (`llm-test/ai_prototype.ipynb` in the detailed assignment text).
- User selected Groq and added `GROQ_API_KEY` locally. A real fictional-task call
  succeeded; evidence is stored without credentials. No deployment requested for
  this A6 work yet.
