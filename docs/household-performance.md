# Household page performance — Phase 1B

Measured on Apple M3, macOS 27.0.1 arm64, Python 3.13.7, existing project virtual environment, SQLite in-memory Django test database. Synthetic fixtures: 10/1,000 selected-household tasks × 1/20 active user memberships. Session has an explicit selected household. No AI or external service runs during measurement.

Method: `households.test_performance.PageMeasurementTests` renders full responses through Django's test client, with SQL captured by `CaptureQueriesContext`. Each case has one first request and seven subsequent samples; warm value is their median. First means first request for that fixture/page, **not** a reboot or guaranteed cold filesystem/template cache; only the initial process/page incurs first template import costs. Latency is server/client-in-process response time, not browser paint or network latency, and test-suite duration is not a page benchmark. Sessions/authentication queries are included. Board renders six records on page one for every size. The picker renders all available memberships, so its HTML size/time may grow with membership count even though query count is fixed.

Before measurements preceded route cleanup. After measurements were repeated after all three tasks, including request-local snapshot, form/summary simplification and product template cleanup. Raw recordings are in `docs/performance/phase1b-before.json` and `phase1b-after.json`. These are local observations, not deployment SLAs or universal speedup claims.

| Tasks / memberships | Page | Queries before → after | First ms before → after | Warm median ms before → after |
|---|---|---|---|---|
| 10 / 1 | `task_forms:board` | 10 → 5 | 20.229 → 4.255 | 5.063 → 4.262 |
| 10 / 1 | `households:list` | 4 → 3 | 1.792 → 1.035 | 1.306 → 0.894 |
| 10 / 1 | `workflows:task-insights` | 7 → 5 | 2.443 → 1.333 | 1.599 → 1.313 |
| 10 / 20 | `task_forms:board` | 10 → 5 | 5.314 → 6.014 | 5.316 → 4.460 |
| 10 / 20 | `households:list` | 4 → 3 | 2.549 → 1.687 | 1.880 → 1.463 |
| 10 / 20 | `workflows:task-insights` | 7 → 5 | 2.240 → 1.637 | 1.943 → 1.402 |
| 1000 / 1 | `task_forms:board` | 10 → 5 | 5.693 → 4.878 | 5.891 → 4.408 |
| 1000 / 1 | `households:list` | 4 → 3 | 1.404 → 1.155 | 1.351 → 0.904 |
| 1000 / 1 | `workflows:task-insights` | 7 → 5 | 2.011 → 1.513 | 2.053 → 1.545 |
| 1000 / 20 | `task_forms:board` | 10 → 5 | 6.100 → 4.895 | 5.592 → 4.910 |
| 1000 / 20 | `households:list` | 4 → 3 | 2.033 → 1.822 | 1.902 → 1.462 |
| 1000 / 20 | `workflows:task-insights` | 7 → 5 | 2.234 → 1.903 | 2.321 → 1.795 |

## Query budgets and authorization

Measured fixed default-page budgets, enforced on all four fixture sizes: board **5**, picker **3**, Insights **5**. Board: session + user + membership snapshot + pagination count + six task rows. Picker: session + user + membership/workspace snapshot, without N+1 lookups. Insights: session + user + membership snapshot + priority grouping + type grouping; total derives from priority counts instead of a redundant count query. Explicit submitted workspace filters legitimately require a validation query; these default-page budgets do not cover extra user filters, CSRF/session writes or exports.

**Dynamic tasks integration update:** the canonical board budget is now **8** queries (adds occurrence annotation, assignment prefetch, and roommate assignee choices for create/assign). Membership table reads on the board are **2** (selected-context snapshot + assignee queryset). Picker and Insights budgets are unchanged.

`resolve_active_membership`/`require_household` and context processor reuse one request-local snapshot. The next HTTP request starts a new snapshot; revoked membership is re-read then. Task creation and approved AI persistence still fetch/lock the active actor inside their existing transaction. A regression revokes membership after form validation to prove the read snapshot cannot authorize a write. An error after revocation refreshes context before translating to onboarding/picker. Switching validates directly; invalid switch leaves even a stale session untouched.

## PNG and startup decision

Before removal, eight priority-PNG requests for 1,000 tasks: first 68.999 ms, seven-sample warm median 43.119 ms (individual measured values 42.164–44.201 ms). This was a separate chart response after Insights HTML, excluding browser image fetch/network/paint and AI time. Its only product caller was the Insights image. Insights now displays accurate selected-household totals and priority/type lists as accessible HTML; the PNG route, renderer and startup Matplotlib imports are removed. No new chart dependency was introduced.

Startup measurement uses five fresh Python processes, timing `django.setup()` plus `django.core.checks.run_checks()` (includes URL import), with Hugging Face offline flags. Baseline recordings in `startup-before.json`: 629.311, 347.423, 346.923, 342.600, 337.139 ms; median 346.923 ms. Matplotlib and the research `a8` package were loaded, Torch was not. Final post-handbook cleanup recordings in `startup-after.json`: 310.398, 179.446, 178.563, 183.14, 173.457 ms; median 179.446 ms. None of those processes loaded Matplotlib, Torch or research packages. No percentage-speedup claim is made from this small local sample. This measures process setup, not request latency; first-process filesystem/cache effects vary.

## Reproduce

From the product checkout, with the existing interpreter and no real `.env`/database copying:

```sh
SECRET_KEY=phase1b-local-only DJANGO_SETTINGS_MODULE=hestia_config.settings.development HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HESTIA_PERFORMANCE_OUTPUT=/tmp/hestia-measurements.json /Users/darshan/Documents/Projects/12_HestiaaAI/.venv/bin/python manage.py test households.test_performance --noinput
```

No live-provider, production-network, PostgreSQL concurrency, sustained-load or device-independent responsiveness claim is made. Browser interaction/390px proof is recorded separately in the verification report.

## Browser responsiveness/usability scope

Signed-in checks used the Codex in-app browser against Django's local development server on the same Apple M3 host, with an independent disposable SQLite database and explicit mock drafting/no Groq key. Search submitted with Enter; approval used Space, Tab, Enter; create/save/Insights/back links and household switching visibly completed. Board and Insights at a 390×844 viewport each reported document width 390. Screenshots are recorded in the verification report. This is functional/keyboard/layout proof, not an accessibility audit or browser-paint latency benchmark. Navigation timing globals were unavailable through the browser tool's read-only DOM interface; no browser/network timing claim is substituted. Server request and process-startup measurements above are the numeric responsiveness evidence.

Fresh-process setup/check measurement can be reproduced in the same configured
Python environment (repeat in five fresh processes; do not time the full test suite):

```python
import json, sys, time
start = time.perf_counter()
import django
django.setup()
from django.core.checks import run_checks
errors = run_checks()
print(json.dumps({"startup_ms": (time.perf_counter() - start) * 1000,
                  "matplotlib_loaded": "matplotlib" in sys.modules,
                  "torch_loaded": "torch" in sys.modules,
                  "research_loaded": "a8" in sys.modules,
                  "errors": len(errors)}))
```
