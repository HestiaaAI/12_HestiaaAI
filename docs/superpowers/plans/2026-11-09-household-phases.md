# Connected Household Experience Implementation Plan

> **Superseded compatibility policy (2026-11-09):** The user has removed all assignment-preservation requirements. Read `2026-11-09-product-first-cleanup.md` before executing remaining work. Legacy aliases, public fictional charts, research integrations and historical templates are not required product features. Existing security protections and useful user behavior remain required.

> **For agentic workers:** Use superpowers:executing-plans to implement one approved phase at a time. Steps use checkbox syntax. Do not spawn agents or add repository collaborators. This document is planning, not a claim of implementation.

**Goal:** Establish one household context connecting onboarding, roommate membership, tasks, groceries and future expenses, with consistent permissions and useful next actions.

**Architecture:** Reuse Workspace, Membership, Django sessions and allauth. Resolve one active membership per request; scope every household query and relationship to it. Keep backend contracts independent of visual design so the UI teammate can work in parallel.

**Tech Stack:** Existing Django/allauth application, SQLite locally and existing PostgreSQL shared settings; no new dependency required for this scope.

**Spec:** `2026-11-09-household-onboarding.md` contains the backend review and proposed feature contract. This document supersedes its task order. User's latest requirement prioritizes isolation and a unified experience.

## Global Constraints

- Never use `codex` in a branch name, regardless of case.
- Do not add collaborators, reviewers, assignees or coauthor attribution. Preserve configured Git author identity.
- Work only on the current approved phase. Preserve unrelated files, research artifacts and local databases.
- Keep Workspace and Membership; display Household and Roommate in the UI.
- Authentication alone never grants household data access. Staff has no application bypass outside Django admin.
- Use server-resolved active household and actor; scope related objects before reading or writing.
- Preserve allauth account protections, CSRF, safe redirect validation and no-store private response behavior.
- UI teammate owns visual redesign; backend work supplies named routes, forms, stable context and states.
- Future Tasks, Groceries and Expenses share the context; do not build unimplemented modules merely to fill navigation.

## Review Focus

1. Stale session after membership deactivation must lose access on the next request (Phase 1, task 1).
2. Membership in A and B must not allow B records while A is selected (Phase 1, tasks 2–4).
3. CSV/JSON, chart aliases, product comparisons and AI provider input must not leak data (Phase 1, tasks 3–4).
4. Wrong-email, expired or revoked invite cannot create membership (Phase 3).
5. Concurrent owner removal/transfer must not leave an active household without an owner (Phase 4).

## Phases, deliverables and acceptance gates

| Phase | Description and deliverable | Success / acceptance criteria |
|---|---|---|
| 1. Household isolation and shared context | Repair existing data access; consolidate assignment routes/services into one task experience; add active-household context. | Two households cannot read/write one another's data through any existing route; dual-member sessions see only selected household; stale membership denied; no-membership state is useful; duplicate production handlers removed; canonical journey and regression matrix pass. No creation/invitation feature required yet. |
| 2. Onboarding and household creation | Connect signup/login to create-or-select household, creating Workspace and OWNER membership atomically. | Fresh user creates a household without admin; validation and CSRF enforced; correct post-login destination; no sample-household auto-enrollment; creation rollback leaves no orphan; existing safe invitation continuation preserved for Phase 3. |
| 3. Invitations and joining | Email-bound seven-day links, copy/share, optional delivery, preview, verification, acceptance and owner revocation. | Existing and new verified users join intended household; GET never joins; wrong/unverified email, expiry, revoked link and replay rejected; concurrent acceptance creates one membership; SMTP failure leaves a usable link and honest delivery state. |
| 4. Household and roommate lifecycle | Settings, roster, leave, remove and ownership transfer with soft deactivation. | Owners alone manage settings/members; foreign IDs denied; roommate can leave; last owner cannot leave/remove self without transfer; removed users immediately lose access; historical task references survive; PostgreSQL concurrency gate passes. |
| 5. Unified experience and demo proof | Integrate teammate UI with shared household navigation and states; connect existing useful actions and validate full journey. | Signup → create → invite → verify/join → shared tasks/groceries → remove works across separate browser sessions. Household switching updates every module consistently. Mobile layouts and empty/error states work. No dead expense/grocery links; unbuilt module integrations explicitly recorded. Two-household isolation regression remains green; deployment checklist and demo script recorded. |

Each later phase must get detailed failing-test/implementation/check/commit steps before execution. Do not assume feature completion for Anushka's task lifecycle, Chaitanya's groceries or Shivani's expenses. Their screens become part of Phase 5 only when their backend functionality exists and passes the shared access contract.

## Phase 1 boundaries and decisions

Use existing accounts and memberships for this phase; test fixtures create data. No invitation model/migration, no household creation, no task recurrence, grocery expiry, expense schema, new authentication stack, AI model download or broad visual redesign.

Missing context has explicit behavior: anonymous private HTML → login; anonymous private JSON/export/image-data endpoints retain their existing 401 JSON policy; signed-in household HTML without selection → onboarding or picker; signed-in household JSON/export/chart-data without selection → 409 `{"error": "Select a household to continue.", "code": "household_required"}`. Foreign object → 404. Valid selected household plus forbidden operation → 403. Invalid posted household choice → 400 with no session change.

No memberships: `/households/onboarding/` renders a useful explanation and sign-out action (creation/join actions arrive in later phases; no dead links). One active membership auto-selects. Multiple memberships without a valid selection show `/households/` picker; never choose arbitrarily. A stale or foreign session selection is cleared, then the same zero/one/multiple rule applies using current memberships. POST `/households/switch/` validates membership and redirects to `task_forms:board`; reject GET with 405. Do not accept external next URLs.

Public historical priority chart stays public at the same URL/schema but uses fixed fictional sample data for everyone. Household charts use explicit private routes with session context. Audit all chart1/priority JSON, PNG and embedded page paths: none may indirectly query real rows for anonymous users. This is an intentional update to historical assignment behavior and tests.

Ask Hestia currently uses a bundled handbook: label that source accurately, do not claim household-aware recommendations. Stateless extraction without household reads/writes may remain authenticated-only, but document it in the route matrix. Any path loading household records must require selected context before external work begins.

## Phase 1 file map and interfaces

| File | Responsibility |
|---|---|
| households/context.py (new) | Query active memberships, resolve/revalidate selection, common requirement errors |
| households/context_processors.py (new) | Publish selected household, membership, available memberships and owner capability |
| households/access.py (extend) | Keep anonymous policy; middleware populates request context without blocking account/static/admin/public paths |
| households/views.py, urls.py (new URL module) | Minimal onboarding/picker and CSRF-protected switch |
| hestia_config/settings/base.py, hestia_config/urls.py | Middleware/context processor/household route registration |
| templates/households/onboarding.html, list.html (new), templates/base.html | Minimal semantic states and selected household label; coordinate shared template edits |
| workflows/task_forms.py, forms_views.py, views.py, search_views.py, task_queries.py | Scoped list/detail/filter/create behavior |
| workflows/ai_forms.py, ai_views.py, action_plan_views.py | Active-context generation and confirmation; preserve form inheritance |
| api/views.py, external.py, chart_views.py; reports/views.py; analytics/views.py, vega_views.py | Scoped lookup, export, summary and image helper inputs; fictional public chart |
| households/test_household_context.py, test_household_selection.py, test_isolation.py (new) | Resolver, selection and cross-route regression tests |
| Existing tests in households/workflows/api/reports/analytics | Replace unsafe global-data expectations with realistic membership fixtures |
| docs/household-access-contract.md (new) | Route matrix, permissions, context and teammate integration contract |

Exact proposed interfaces:

- `active_memberships(user) -> QuerySet[Membership]`: active rows belonging to authenticated user, select_related workspace, none for anonymous.
- `resolve_active_membership(request) -> Membership | None`: validate session `active_workspace_id`; populate `request.active_membership` and `request.active_household`; never return stale objects across requests.
- `require_household(request) -> Membership`: return resolved membership or raise `HouseholdRequired` (defined in households/context.py). Shared Django error handling translates this to the HTML redirect/JSON policy above; classify resolved routes, not Accept headers or URL substrings.
- Template context: `active_household`, `active_membership`, `household_memberships`, `can_manage_household`.
- `TaskCreateForm(*args, membership=None, **kwargs)` and `TaskFilterForm(*args, membership=None, **kwargs)`: default-deny without explicit scope; limit workspace field choices to supplied membership's workspace. Preserve `ReviewTaskForm` operation via explicit constructor adaptation rather than silently granting global access.
- `compare_products(query, *, workspace)` and internal lookup require workspace; report/chart helpers accept a scoped queryset. Existing caller return schemas stay stable except intentional error policy/public sample change.

### Task 1: Context resolution and selection

**Consumes:** existing Workspace/Membership and sessions. **Produces:** context interfaces, routes `households:onboarding`, `households:list`, `households:switch`.

- [ ] Write resolver tests: anonymous and no membership → None; one auto-selects; two with no selection → None; selected A → A; foreign/inactive selection cleared; null-user rows excluded; next request after removal cannot use old context; staff gets no bypass.
- [ ] Run `python manage.py test households.test_household_context` and capture expected behavior failures.
- [ ] Implement context.py and middleware registration; do not add model migrations or blanket redirects on account routes.
- [ ] Write selection tests: login boundary, useful zero-member page, picker exposes only user's households, valid POST switch, GET 405, invalid/foreign/inactive choice 400 without session change, real CSRF rejection, no external redirect.
- [ ] Run `python manage.py test households.test_household_selection` to confirm red.
- [ ] Implement routes, minimal templates, context processor and a selected-household label without visual redesign. Middleware order must allow authentication before resolution and must not interfere with allauth callback/verification.
- [ ] Run both modules to green; commit `feat(households): establish active household context`.

### Task 2: Task query and write isolation

**Consumes:** require_household and active membership. **Produces:** scoped task reads and forms; server-owned workspace/creator.

- [ ] Add named regression tests `test_task_routes_exclude_foreign_household`, `test_foreign_detail_returns_404`, `test_dual_member_sees_only_selected_household`, `test_forged_workspace_cannot_create_task`, `test_valid_create_uses_active_membership`, `test_no_membership_cannot_read_or_create`.
- [ ] Test each list variant and GET/POST search; assert foreign names/titles/IDs absent, not only a successful status. Assert tampered POST leaves task counts unchanged. Use nullable/inactive membership fixtures too.
- [ ] Run failing task-isolation tests; implement scoped query roots before user filters. Accept only selected-workspace field value when legacy form posts it; set creator and workspace server-side; enforce context for CBV post as well as get. No null-creator fallback.
- [ ] Update realistic fixtures/redirect assertions in existing form and access tests; never weaken assertions or skip them to pass.
- [ ] Run `python manage.py test households.test_isolation workflows.test_forms workflows.test_search`; commit `fix(tasks): enforce selected household on reads and writes`.

### Task 3: APIs, exports, lookup, aggregates and public samples

**Consumes:** scoped context and queryset helper inputs. **Produces:** no cross-household information through secondary data surfaces.

- [ ] Add tests `test_private_api_and_exports_are_household_scoped`, `test_lookup_scopes_products_entries_and_tasks`, `test_private_charts_exclude_foreign_counts`, `test_public_chart_variants_use_fictional_samples`, `test_missing_household_returns_409_for_private_data`, `test_private_responses_are_not_shared_cacheable`.
- [ ] Fixtures use distinct priorities, dates and product names for A/B, so count/date leaks are detectable. Check response data and generated chart source/query inputs; PNG HTTP 200 alone is insufficient. Verify anonymous requests do not execute real household aggregate queries.
- [ ] Run targeted red tests; scope private routes and all helper call sites before aggregation/serialization or external requests. Set private no-store and Vary: Cookie. Switch anonymous chart aliases/embeds to one fixed sample source independent of real rows.
- [ ] Update tests intentionally expecting global/public database-backed aggregates and document why. Keep public endpoint field schema, CORS shape and method restrictions stable.
- [ ] Run `python manage.py test api reports analytics households.test_isolation`; commit `fix(access): scope exports lookup and analytics to household`.

### Task 4: AI boundary, teammate contract and final gate

**Consumes:** shared context and scoped forms. **Produces:** consistent AI access plus documented integration surface.

- [ ] Add tests `test_foreign_action_plan_never_calls_provider`, `test_brain_dump_confirmation_rejects_other_selected_household`, `test_membership_revoked_between_preview_and_save`, `test_review_form_subclass_preserves_scoped_validation`. Mock providers and assert no calls/writes when unauthorized.
- [ ] Run red tests; enforce active workspace at generation and save; recheck membership inside existing write transaction. Preserve draft signing/validation and explicit human confirmation.
- [ ] Record every URL in root/included URLconfs in docs/household-access-contract.md: public sample, account/admin/static, authenticated stateless, or selected-household. Include direct aliases and data/image routes, expected error behavior and tests. Inspect home/dashboard helpers too; an unlisted data route is an unfinished audit.
- [ ] Document future groceries/expenses contract: active workspace is server-owned, all FK targets are same-household, actor active, access validated on each request, household-scoped cache keys, cross-household tests required. Show UI fields/states and current public-handbook limitation.
- [ ] Run `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py test households workflows api reports analytics`, and `git diff --check`. Capture counts and failures. Do not download models or call external providers to make tests run.
- [ ] Verify with separate sessions using controlled existing/fixture memberships: A and B have disjoint data; a dual member switches context consistently; removal invalidates access; public charts remain sample-only. If browser tools/environment unavailable, report that limitation rather than claiming manual validation.
- [ ] Commit `test(households): verify isolation and document shared contract`; report files, behavior, test evidence, unresolved baseline issues and remaining phases. Stop before Phase 2.

## Baseline and execution handoff

Previous review at committed base 421b75d: system check clean, 48 tests in households and api.test_access passed. These checks were run from the original checkout; rerun on the execution branch. Full application suite has not yet been verified. The original checkout has unrelated local changes; do not copy or modify its .env/database/output files. Use an external existing virtual environment if appropriate, with explicit test settings and a nonsecret local SECRET_KEY; tests must create their own database.

Phase 1 is complete only when the full route matrix is accounted for, named regressions and relevant existing tests pass, and the deliverable enforces selection across existing features. A resolver alone does not satisfy the phase. Do not implement later phases or deploy automatically. Phase 1 also requires the consolidation task below; it is not complete with access fixes alone.

Self-review: each review-focus item maps to a phase/task; Phase 1 has explicit inputs, outputs, file ownership, red/green cycles, commands and stop condition. Later phases retain high-level acceptance gates and require their own detailed execution plans when selected.


## Phase 1 scope expansion — retire assignment fragmentation

User explicitly included consolidation/removal of isolated services and functions in Phase 1. This is a targeted architecture and product-flow cleanup, coordinated with the UI teammate. Preserve useful capabilities and historical research evidence; remove duplicate production implementations, not features merely because they live in separate files.

### Current website review (2026-11-09)

Browser review: local home, login and signup pages at http://127.0.0.1:8012. No account creation or authenticated walkthrough was performed. Protected-page findings below are verified in source, not claimed as browser-tested. The local original checkout is used for preview; implementation stays in the separate execution branch.

- templates/base.html exposes Household tasks, Task board, AI Brain Dump, Ask Hestia, Search tasks, Product lookup, Task statistics, Reports and Charts alongside Home. Multiple top-level links serve the same task journey.
- templates/home.html routes users among assignment capabilities, with copy about primary keys, GET/POST and ORM/Matplotlib rather than useful household actions.
- workflows/views.py implements four list variants; templates/tasks/task_list.html renders explicit assignment-method navigation. workflows/search_views.py adds GET/POST search separate from the board's existing filtering.
- templates/tasks/forms/task_board.html already combines filtering and creation, making it the strongest existing canonical task surface. Its empty states refer to loading assignment demo data and its household fields permit global selection today.
- reports/views.py, analytics/views.py, api/chart_views.py and analytics/vega_views.py independently assemble overlapping task totals and chart views; helper inputs must converge on one scoped source.
- api/brain_dump.py calls local extraction directly; workflows/ai_views.py calls ai_adapter.get_suggestions, which calls the same extractor and performs additional UI-schema validation. These are related entry points with divergent orchestration, not two unrelated features.
- workflows/action_plans.py generates validated task plans; workflows/ai_breakdown.py has a configurable step hook; services/ask_hestia.py answers from a bundled research handbook. They have distinct semantics: a universal AI service or indiscriminate deletion would lose behavior. Audit actual callers and runtime config before removing any of them.
- inventory/views.py is a placeholder. Product lookup compares public catalogue results against internal rows; it is not the missing grocery inventory experience.

### Target product flow

Public landing → sign in/signup → household context → Tasks. For a selected household, root Home redirects to task_forms:board until a useful dashboard is designed; no new dashboard project in Phase 1. Without context root routes to onboarding/picker. Keep the anonymous landing and auth lifecycle.

Primary authenticated navigation: Tasks and Household (selection/context). Integrate Groceries and Expenses only when their actual screens are implemented. Task board contains search/filter, Add task, Organize with AI, and Insights entry. Task detail offers its existing action-plan feature and a consistent back link. AI draft confirmation returns to the same scoped board with a success message. Preserve form errors and drafts on provider failure.

Use /tasks/insights/ as the single private insights page, with priority/type summaries, one useful chart and CSV/JSON actions. Reuse existing reporting/chart code after consolidation. Do not place separate Reports, Statistics and Charts destinations in primary navigation. Product lookup stays an honestly labeled secondary tool; no claim of expiry tracking. Ask Hestia becomes secondary Household handbook help labeled as bundled sample content, not a household-aware assistant.

### Task 5: Consolidate routes, services and product navigation

**Files:** workflows/views.py, search_views.py, urls.py, search_urls.py, forms_views.py, ai_views.py, ai_adapter.py; api/brain_dump.py; reports/views.py; analytics/views.py, vega_views.py; api/chart_views.py; hestia_config/views.py, urls.py; templates/base.html, home.html, tasks/forms/task_board.html, tasks/task_detail.html, tasks/ai_brain_dump.html, tasks/action_plan.html; new workflows/task_insights.py, workflows/test_unified_flow.py; docs/household-access-contract.md. Remove legacy template/handler files only when no runtime callers remain. Identify additional template callers before moving blocks.

**Interfaces:** canonical board remains task_forms:board at /tasks/manage/. Add workflows:task-insights at /tasks/insights/ (defined before numeric detail route). `task_summary(tasks: QuerySet[Task]) -> dict` in workflows/task_insights.py returns total_tasks, priority_summary and type_summary in existing report context format; no default/global queryset. Views and chart builders receive scoped inputs. Existing ai_adapter.get_suggestions(text) becomes the common extraction/validation entry used by HTML and JSON task-draft adapters; retain its current validated list schema and adapt JSON to preserve the existing success/error envelope. Provider choice stays inside the adapter; do not make every AI feature share an incompatible schema.

- [ ] Establish the consolidation boundary in docs/household-access-contract.md: table of every candidate handler/service, callers, current behavior, keep/merge/remove/legacy-alias decision and replacement. Inspect import_string/config hooks and test/management-command references; no inference of dead code from a filename. Treat research folders/assignment documents as historical evidence outside deletion scope.
- [ ] Write test_canonical_task_journey, test_navigation_has_one_task_destination, test_no_assignment_implementation_copy_in_product_pages, test_home_respects_household_state, test_legacy_list_and_search_use_canonical_flow, test_insights_share_scoped_summary, test_html_and_json_drafts_use_shared_extractor, test_ai_confirmation_returns_to_selected_board, test_provider_failure_preserves_manual_task_path.
- [ ] Run `python manage.py test workflows.test_unified_flow` and capture failures before cleanup. Record existing task form/search ordering and pagination behavior to preserve where useful; document intentional route behavior changes.
- [ ] Route old GET task list variants and GET search to canonical board using temporary 302 redirects preserving only supported q/priority/task_type/page query values; validate workspace filters against selected household and never forward arbitrary next URLs. Keep old route names as thin compatibility aliases where model URLs/tests/integrations use them. Legacy POST search remains read-only and calls the canonical board GET/filter handler with validated form terms in memory; do not redirect POST to task creation or lose search terms. Remove the four independent list/query implementations and demo view-style template navigation once callers have moved. Test aliases under anonymous, missing-context and selected-household states.
- [ ] Consolidate report totals/priority/type grouping into task_summary with explicit scoped input; retain date-grouping as a separate necessary operation. Render one insights page. Old report/statistics HTML destinations 302 to insights; exports/data/image URLs stay thin adapters to shared scoped helpers, preserving machine response schemas. Public sample variants stay separate from private data and never call real-row summary code.
- [ ] Route HTML/JSON draft generation through get_suggestions while preserving endpoint-specific validation, current response envelopes, configured provider behavior, error codes and confirmation-only persistence. Test fixture/schema compatibility before deleting redundant normalization. Keep genuine transport/model-specific adapters. The optional breakdown hook and action-plan provider remain if referenced; remove only proven unused wrappers after reference/config audit and tests. Do not build a generic provider framework or relocate files merely for symmetry.
- [ ] Implement the target navigation/root flow and contextual back/success links with minimal semantic template changes. Remove user-facing references to primary keys, GET/POST, ORM, CBV, assignment demonstration and seed commands; retain technical guidance in developer docs. Keep bundled-handbook attribution truthful. Coordinate changed template/context contract with UI teammate in documentation; do not contact them without authorization.
- [ ] Validate no production imports/URL handlers point to removed symbols/templates; compare before/after route inventory and document intentional aliases. Test underlying canonical destination permissions as well as redirect status. No hidden live global-data route may survive just because it disappeared from navigation.
- [ ] Run `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py test households workflows api reports analytics`, and `git diff --check`. Perform signed-in browser journey and narrow-screen verification when environment is available; report actual scope and blockers. Commit logical access/consolidation changes separately; no push/deploy.

**Additional Phase 1 acceptance gate:** a user can choose a household, find/create a task, generate/review/save AI drafts, open task details/action plans, inspect household insights and return to the same board through one connected journey. Duplicate assignment list/search/aggregate business logic has been merged or removed with documented replacements. Old links either reach the canonical experience safely or remain documented data adapters; no technical demo navigation or seed instructions appear in normal screens. Existing useful services remain modular where responsibilities differ. A UI-only hiding of duplicate navigation is insufficient.

Phase 5 now focuses on final visual integration, completed grocery/expense modules and end-to-end demo polish; canonical navigation and backend consolidation are Phase 1 work.
