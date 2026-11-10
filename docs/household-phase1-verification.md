# Household product verification — Phase 1B

Phase 1B supersedes Phase 1A's assignment compatibility/sample obligations. Source baseline: `404ea31` on `household-isolation`; execution branch: `household-product-cleanup`. The original checkout, configured Git identity, databases, secrets and unrelated outputs were preserved. No subagents, collaborators, external messages, push, PR or deployment.

## Delivered and commits

- Task 1, `4d125a5 refactor(routes): remove assignment-only runtime surfaces`: removed compatibility lists/search, redirects, Vega/public samples, unused internal JSON transports and demo scripts; moved useful CSV to `/tasks/export.csv`; kept actual browser task/draft/plan/catalogue workflows.
- Task 2, `29ecba0 perf(households): reuse request context and remove PNG rendering`: one policy owner; request-local snapshot; fresh mutation checks; measured/pinned query counts; accessible text replaces PNGs.
- Task 3, `refactor(product): remove handbook and isolate research dependencies` (identify final hash in branch history): removed sample-handbook runtime and coursework copy, simplified selected-household forms and dead transport metadata, retained useful providers/hooks, separated plotting requirements and excluded research/data from product archives. Updated route/context/UI contract and evidence.

The complete current matrix has **134 resolved patterns**, including account/admin-generated patterns; only 11 are product/selection/landing patterns. This is not a claim of 134 features. `household-access-contract.md` records methods, status policy, surviving helpers, UI blocks/context and future feature requirements. `household-product-decisions.md` records callers and remove/retain decisions. There are no compatibility-only handlers or public fake metrics left.

## Commands and actual results

Interpreter: `/Users/darshan/Documents/Projects/12_HestiaaAI/.venv/bin/python` (existing environment, Python 3.13.7). All application runs use `SECRET_KEY=phase1b-local-only DJANGO_SETTINGS_MODULE=hestia_config.settings.development HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`. Tests create an isolated SQLite test database; no real environment/database copied.

| Check | Result |
|---|---|
| Pre-edit application baseline: `python manage.py test households workflows api reports analytics --noinput` | 236 passed, 17.361s (235 Phase 1A tests plus new measurement test) |
| Task 1: `python manage.py test workflows.test_product_routes households api workflows reports analytics --noinput` | 184 passed, 15.058s |
| Task 2: `python manage.py test households workflows api reports analytics --noinput` | 185 passed, 14.753s |
| Task 3 focused: `python manage.py test workflows.test_product_runtime workflows.test_unified_flow --noinput` | 12 passed, 0.459s |
| Final application: `python manage.py test households workflows api reports analytics --noinput` | 179 passed, 11.054s |
| Whole repository discovery: `python manage.py test --noinput` | 223 passed, 11.718s; includes retained supported historical tooling tests |
| `python manage.py check` | Clean |
| `python manage.py makemigrations --check --dry-run` | No changes |
| `git diff --check` | Clean final diff |

Logs: `/tmp/hestia-phase1b-baseline.log`, `/tmp/hestia-phase1b-task1-green.log`, `/tmp/hestia-phase1b-task2-green.log`, `/tmp/hestia-phase1b-task3-green.log`, `/tmp/hestia-phase1b-app-final.log`, `/tmp/hestia-phase1b-whole-final.log`. Raw reproducible measurements are checked into `docs/performance/`; temporary logs are not runtime dependencies.

No test skips or weakened isolation bypasses were introduced. The lower test count intentionally reflects removed product requirements and removal of duplicate inherited security test discovery; it is not itself a performance claim. The task 1 command explicitly names the product-route module as well as `workflows`, so it collects those route tests twice.

## Red/green and retained regression coverage

Task 1 product-route tests first failed for 22 routes that still resolved and the missing new CSV name. They passed after removal/migration. Task 2 tests first failed on repeated membership reads/snapshot identity and the still-resolving PNG/presence of the chart. They passed with one snapshot and text summaries. Query budgets were pinned after actual profiling. Task 3 first failed for coursework/dead handbook links, repeated household picker, research import and archive inclusion; then passed after cleanup. Final self-review added a failing landing-copy regression for references to removed reports/charts; the corrected product copy passed both full suites.

Existing A/B, dual-member, inactive/null-user/staff, stale-selection and staged-draft rejection tests remain. `test_performance.test_write_revalidates_actor_after_snapshot` revokes membership during real form validation and proves no task is saved, then observes 409 next request. Transaction lock/get failure also cannot save. CSV retains exact row scope/field allowlist, Unicode/quotes/newlines, formula neutralization, methods and empty-state proof. HTML plan/draft tests retain CSRF enforcement, safe provider errors, cooldown, schema validation, escaping, bounded output, signed drafts and human confirmation. Independent clients retain data isolation proof. A link audit resolves every local navigation/form target on current product pages.

## Intentional test deletions/replacements

| Retired requirement/tests | Replacement |
|---|---|
| `workflows/test_api.py`: unused task-list JSON schema/filter/response-demo | Canonical board filtering/escaping/read-only GET in `test_forms`/`workflows.tests`; route absence in `test_product_routes`; CSV private data boundary in `api.test_access` |
| `workflows/test_search.py`: GET/POST search aliases | Actual board filtering and CSRF/write tests; old paths must not resolve and cannot create records |
| `api/test_brain_dump.py`, JSON-only unified schema tests | Actual HTML draft generation/review/confirmation/provider-failure tests in `test_ai`, `test_unified_flow`, `test_ai_action_plan`; JSON adapter is removed, not a supported contract |
| JSON action-plan assertions in `test_action_plan_views` | HTML disclosure, preview/no writes, foreign/no-context denial, CSRF, safe provider failure, cooldown and missing-key tests on retained plan page |
| `analytics/test_vega.py`, PNG/sample tests | No old route resolves; selected real counts/empty state/occurrence independence/escaping in `analytics.tests`; text-only Insights and no eager plotting import tests |
| JSON report export metadata/schema tests | Supported CSV headers/exact rows/formula safety/empty export/method tests in `reports.tests`; obsolete JSON URL must not resolve |
| Legacy list/redirect implementation assertions | One board/detail/Insights journey and explicit retired-route absence |
| `workflows/test_ask_hestia.py`, `test_ask_hestia_views.py` | The sample feature is removed. `test_product_runtime` blocks research imports at startup; `test_no_sample_handbook_route` and product-page copy/link tests prove no product claim remains. Historic evaluation is reproducible from Phase 1A, not a retained product requirement |
| JSON-only metadata list subclass | Ordinary validated list for the retained HTML draft adapter; existing form/schema/provider tests still run |
| Duplicate inherited isolation cases in unified-flow class | Shared fixture setup only; the independent isolation class runs once and journey class tests its own behavior |

## Performance evidence

Apple M3/macOS, Python 3.13.7, SQLite in-memory client rendering; 10/1,000 tasks and 1/20 memberships; first request plus seven warm samples per page/fixture. Full method, all rows and caveats: `household-performance.md`.

- Board default queries: **10 → 5**, six rendered tasks per page at both sizes.
- Picker: **4 → 3**, all memberships loaded with workspaces in one snapshot, no N+1 queries.
- Insights: **7 → 5**, real priority/type summaries; total derives from grouped counts.
- Separate removed PNG response: 68.999 ms first, 43.119 ms warm median in the baseline sample. Text summaries now require no PNG fetch.
- Five-process startup median (`django.setup` + checks/URL import): **346.923 → 179.446 ms** locally. Baseline loaded Matplotlib and `a8`; final loaded neither, and neither measurement loaded Torch.

These observations are not universal speedup percentages, production SLAs, provider latency, network/paint measurements or load-test results. Numeric request budgets are enforced; timing values are observations, not brittle test thresholds.

## Browser verification actually performed

Codex in-app browser against `127.0.0.1:8025`, same Apple M3 host, new disposable `/tmp/hestia-phase1b-browser.sqlite3`, explicit mock drafting and empty Groq key. No real user records or external providers used.

Observed login → dual-member picker → Alpha board; Enter submits title search; create returns to plain board with success; AI form uses selected Alpha without a second picker; mock drafts remain review-only; Space/Tab/Enter checks approval and saves; board displays saved count and still Alpha; Insights shows actual five Alpha tasks/priority/type values and CSV action; back link returns to same board. Detail/action-plan disclosure opens; unconfigured-key POST yields useful 503 recovery text with navigation intact and no network request. Switching Beta shows only its one task, with matching navigation label.

At 390×844, both Board and Insights document widths were 390, no horizontal overflow. Screenshots: `/tmp/hestia-phase1b-board-mobile.png`, `/tmp/hestia-phase1b-insights-mobile.png`. Keyboard checks are functional proof, not a full accessibility audit. Navigation timing globals were not available through the browser tool's DOM interface, so no browser paint/network latency is claimed. Server timing method/device are stated separately. The disposable server was stopped after proof.

## Dependency/release proof and rulings

No stack replacement, new dependency or visual redesign. Retained Django/allauth/PostgreSQL support, requests catalogue/Groq clients and enabled local inference/tokenizer/model packages (including NumPy/Torch/Transformers). Migrations import only Django components. Plotting-only Matplotlib, contourpy, cycler, fonttools, kiwisolver, Pillow, pyparsing, python-dateutil and six move to `requirements-research.txt`; existing experiment packages keep their own requirements. No shared-environment packages were uninstalled and no fresh clean dependency installation was claimed.

One subprocess test blocks research, plotting and inference imports before Django starts and checks the full URLconf. A product `git archive --worktree-attributes` test verifies research/notebooks, evidence bundles and historical SQLite database are excluded while product providers remain. Product release excludes research rather than deleting research/output/data files. README now describes the real household product, not submissions. Historical `a9/evaluate.py` used the retired handbook adapter and requires the Phase 1A revision; it is excluded from the product archive.

Rulings: remove unused JSON transports because no actual retained client exists; retain useful HTML domain behavior and private CSV. Keep historical research in source but exclude it from releases. Keep local inference dependencies and the bounded configured step hook because actual retained workflows use them. Retire all compatibility aliases/public examples, as authorized. Perform self-review without subagents per user instruction. No later-phase features invented.

Self-review covered removed-route callers/reverse links, source imports/configured hooks, request-local reuse versus fresh transaction checks, no-store/error policy, canonical approval and navigation, default query budgets, product archive exclusions and UI teammate contracts. Minor deferred: broader visual styling remains the UI teammate's scope.

## Limits and remaining phases

No current SQLite/application/whole-discovery failure blocks this local acceptance gate. PostgreSQL concurrency, live model/Groq/catalogue behavior, a clean-environment dependency install, production load, independent review, full accessibility audit and browser paint timing remain unverified. No provider calls/downloads were used in Phase 1B proof.

Stop before Phase 2. Household creation, invitations/email-bound acceptance, member/ownership lifecycle, grocery expiry, expenses, recurrence, PWA/native work and deployment remain later phases. Their shared access/context rules are in the contract; no unimplemented buttons are shown.
