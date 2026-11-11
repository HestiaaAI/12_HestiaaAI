# Product-First Phase 1B Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans task by task. User instruction supersedes earlier compatibility requirements. Execute directly without subagents or collaborator changes.

**Goal:** Finish turning the secured Phase 1 application into a lean household product, removing assignment-only runtime surfaces and measuring usability/performance before adding onboarding writes.

**Architecture:** Continue with Django, allauth, Workspace and Membership. Keep canonical task/household journeys and explicit domain services; remove legacy runtime adapters with no product use. Change architecture where a concrete product problem warrants it; do not replace the stack merely because replacement is permitted.

**Tech Stack:** Existing Python/Django application; runtime dependencies audited against actual product paths. No required new dependency.

**Spec:** Latest user direction: nothing is required solely for assignment purposes; application quality, user experience, performance and usability determine retention. This supersedes preservation/alias/public-sample obligations in previous plans.

## Global Constraints

- Never use codex in branch names; no added collaborators, reviewers, assignees or coauthor attribution.
- Preserve household isolation, authentication/verification, CSRF, safe redirects, explicit AI save approval and historical user-data integrity.
- No assignment compatibility requirement. Intentional endpoint removal may return 404; update callers and tests in the same change.
- Architecture changes must solve a stated problem and have verification; a broad rewrite is not a deliverable.
- No automatic deletion of databases, secrets or user data. Research/assignment artifacts may be removed from the product checkout after confirming they are not live dependencies; Git retains committed history. Do not delete unrelated untracked work.
- Coordinate template/context contracts through docs; UI teammate owns visual redesign. No external messages, push or deployment in this assignment.

## Review Focus

1. Removing a legacy route must not strand a canonical template, reverse lookup or account redirect (task 1).
2. Removing research folders must not break a retained handbook/model loader (tasks 1 and 3).
3. Request-local membership reuse must not weaken fresh authorization inside mutations (task 2).
4. Static/example data must not appear as a real household's activity (task 1).
5. Performance improvements must preserve pagination, empty/error states and private response isolation (tasks 2 and 3).

## Evidence and limits

Inspected Phase 1 code and checked-in verification report on household-isolation. Report records 235 scoped tests and 279 full-discovery tests passing, plus browser checks. These are the implementing agent's results, not independently rerun in this planning update. PostgreSQL concurrency, live providers and independent review remain unverified. A route count of 155 includes account/admin-generated routes and does not itself indicate 155 product features.

Remaining observed code: legacy_task_list and standalone search aliases; reports/statistics redirect views; public Vega/sample chart routes; /api/response-demo/; AssignmentAccessMiddleware plus household/API policies; repeated resolve_active_membership calls; Matplotlib chart rendering; sample-handbook service importing a8.corpus. Removal and optimization candidates are evidence-backed; latency improvement is not yet measured.

## Revised phases

- Phase 1A: security/context/consolidation already implemented, subject to final verification.
- Phase 1B: product cleanup and performance/usability baseline — this plan.
- Phase 2: signup-to-create/select household, atomic owner creation and purposeful onboarding.
- Phase 3: verified email-bound invitations, acceptance, expiry/revocation and delivery states.
- Phase 4: roster/settings/leave/removal/ownership transfer.
- Phase 5: integrate finished task/grocery/expense features and teammate UI; demonstrate full roommate journey and deployment readiness.

### Task 1 — Remove assignment-only runtime surfaces

**Files:** hestia_config/urls.py; workflows/urls.py, views.py, search_urls.py, search_views.py; reports/urls.py, views.py; analytics/urls.py, views.py, vega_urls.py, vega_views.py; api/urls.py, views.py, chart_views.py; households/access.py; templates/base.html and tasks/insights.html; docs/household-access-contract.md; new workflows/test_product_routes.py. Delete files only after reference audit.

**Consumes:** canonical task board/detail/AI/Insights and household routes. **Produces:** reduced runtime URL inventory; no compatibility handler retained solely for assignments.

- [ ] Write route/feature decision table: retained product routes and required account/admin/provider callbacks; legacy assignment routes to remove; product helpers to move before deleting their old modules. Resolve imports, templates, settings allowlists, commands and dynamic provider hooks. External integrations are retained only where actually used by the product, not for old coursework.
- [ ] Write failing tests asserting /tasks/manual/, /tasks/render/, /tasks/cbv-base/, /tasks/cbv-generic/, /tasks/search/, /tasks/search/post/, /api/response-demo/ and /vega-lite/ no longer resolve. Public sample JSON/spec/image routes also disappear. Canonical board, detail, Insights and account routes still resolve; existing household-isolation tests remain meaningful.
- [ ] Remove legacy URL registrations and compatibility functions; migrate internal reverse links first. Remove redirect-only report/statistics pages. Retain useful CSV export/real household summaries with canonical private routes and updated consumers; JSON/charts only if an actual retained screen/client needs them. No public fictional task chart is required anymore.
- [ ] Delete obsolete runtime templates/demo commands/helpers after caller audit. Research documents/notebooks do not belong in the production runtime/package; remove their product links/deployment inclusion. Folder deletion is permitted after proving retained runtime independence; never erase unrelated local outputs or data.
- [ ] Update obsolete route/schema tests to new product requirements; retain security, escaping, method, CSV and approval assertions on surviving equivalents. Run `python manage.py test workflows.test_product_routes households api workflows reports analytics`; commit a focused route-cleanup change.

### Task 2 — Simplify access ownership and establish performance proof

**Files:** households/access.py, context.py, context_processors.py; api/middleware.py; hestia_config/settings/base.py; workflows/forms_views.py, task_insights.py; tests in households/test_household_context.py, households/test_isolation.py and new households/test_performance.py; docs/household-performance.md.

**Consumes:** retained route inventory and active membership contract. **Produces:** clearly owned access policy, request-local context reuse and recorded query/latency evidence.

- [ ] Measure board, picker and Insights database queries with 10 and 1,000 tasks and 1 versus 20 memberships. Record fixture sizes, environment, cold/warm timing and query counts; separate server response from AI/provider time. Do not turn test-suite runtime into a page performance claim.
- [ ] Write failing tests for redundant resolver work within the same request, stale membership on the next request, fresh write-time actor validation and query growth as rendered page size remains fixed. Budget: query count must not grow with total tasks or number of displayed memberships beyond intentional fixed queries; pin measured improved fixed counts after profiling, documenting why.
- [ ] Resolve memberships once per normal request using a request-local snapshot reused by views/context processor. Keep explicit fresh membership checks inside write transactions. Remove overlapping assignment middleware/policy exemptions now obsolete; one clearly documented component owns each login/household error translation. Preserve 401/409/403/404 and no-store semantics on surviving routes.
- [ ] Profile chart cost and dependency startup before deciding whether to retain PNG rendering. Proposed simple product choice: one accessible HTML/CSS summary with numeric values on Insights, eliminating server PNG generation if no product consumer requires it. Preserve an equivalent text summary and accurate empty state. Avoid adding a charting dependency solely for replacement.
- [ ] Run security and query regression tests, repeat same performance measurements and record before/after. No unsupported percentage-speedup claims. Commit measurable simplification independently of route removal.

### Task 3 — Useful connected flows and runtime dependency cleanup

**Files:** templates/base.html, home.html, tasks/forms/task_board.html, tasks/insights.html, tasks/task_detail.html, tasks/ai_brain_dump.html; workflows/ai_adapter.py, ai_breakdown.py, action_plans.py, services/ask_hestia.py, services/__init__.py; hestia_config/urls.py, requirements.txt; docs/household-access-contract.md, docs/household-phase1-verification.md; workflows/test_unified_flow.py.

**Consumes:** cleaned routes and access layer. **Produces:** canonical task journey with no assignment dead ends and lean product imports/dependencies.

- [ ] Audit each AI capability's actual user outcome. Keep draft generation and task-plan help when they are useful. Retain Ask Hestia UI, route and useful service behavior. Clearly label current answers as based on the bundled handbook, not live household records. Remove assignment-specific framing and connect its navigation/back links to the active household experience. Household-aware retrieval is a separate incremental enhancement, not a prerequisite for retaining the feature; no private-household claims based on bundled examples. Remove optional step hooks only if no retained caller/configured product use. Shared services should follow responsibilities, not assignment ownership or a universal AI abstraction.
- [ ] Add failing tests for canonical navigation/back links, context-preserving AI save, provider failure preserving manual creation, no sample-household metrics presented as real data, truthful handbook source labels, retained Ask Hestia route, no dead links and import/startup without removed research packages. Keep AI/provider calls mocked in access tests.
- [ ] Implement minimal semantic UX adjustments with stable template blocks for UI teammate. Household selected once controls all current screens. Do not show unimplemented grocery/expense buttons or nonexistent create/invite actions before later phases. Remove coursework footers/copy and backend terminology from product screens.
- [ ] Remove dependencies only after checking retained runtime, migration and tooling imports; move experiment-only requirements out of production installs if experiments remain in repo. Do not remove local inference packages while an enabled product provider still uses them. Test ordinary pages start without loading heavyweight inference models.
- [ ] Run `python manage.py check`, `python manage.py makemigrations --check --dry-run`, full application tests and whole-project discovery for remaining supported files, `git diff --check`; record intentional test deletions with replaced requirements. Browser-check signed-in task/AI/Insights flow, keyboard interaction and 390px viewport. Measure responsiveness with method/device stated; report live provider and PostgreSQL limits explicitly.
- [ ] Update contract and verification report with the final route map, deletions/replacements, actual performance evidence, browser results and unresolved blockers. Commit. Stop before Phase 2, push and deployment.

## Acceptance gate

No runtime route/helper/template is kept solely for assignment compatibility. Every remaining screen serves the household journey and displays only selected-household records. Core pages avoid unnecessary per-request membership work and model loading; measurements and tests substantiate performance behavior. Account/isolation/AI approval regressions pass. No fake household metrics, duplicate task/search destinations or misleading claims of live household awareness remain. Ask Hestia remains available with accurate source labeling. UI teammate has current routes/context/states; later phases retain clear boundaries.

Self-review: all five review conditions map to tests/tasks. This plan removes preservation constraints without implying permission to delete user data or requiring a speculative rewrite. Exact performance thresholds follow measured fixtures rather than invented device-independent timings.


## Confirmed product decision — retain Ask Hestia

The user explicitly confirmed that Ask Hestia remains a product feature. This decision supersedes any deletion recommendation in earlier plans or prompts.

Phase 1B acceptance: Ask Hestia remains reachable from the connected experience; current handbook answers are accurately attributed; account access and provider error behavior remain tested. Do not delete its route, templates, retrieval runtime or dependencies merely because they originated in an assignment. Audit dependencies against this retained feature.

Future enhancement: incrementally answer from selected-household tasks, then groceries and expenses when their records/features exist. Enforce active membership before retrieval/provider calls; scope retrieved records, citations and caches to the household; do not mix sample handbook rules with real household facts. Explain answer sources, handle missing evidence honestly, and require explicit confirmation with fresh authorization before any proposed write. No automatic action execution or promise of currently unsupported household awareness.

Add regression tests for retained navigation/route, truthful source labeling and provider failure. Add cross-household retrieval and source-evidence tests when household-aware retrieval is implemented; do not represent them as already completed.
