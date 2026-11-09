# Household access and integration contract — Phase 1

Canonical journey: sign in → household picker/onboarding → `/tasks/manage/` (`task_forms:board`) → task detail/action plan or reviewed AI drafting → same board → `/tasks/insights/` (`workflows:task-insights`). Signed-in Home redirects to the board or missing-context state. Anonymous Home remains public.

## Context and error behavior

`households.context.active_memberships(user)` returns active, non-null-user memberships with workspace loaded. `resolve_active_membership(request)` revalidates current database membership each call and publishes `request.active_membership`, `request.active_household`, and `request.household_memberships`. No memberships: onboarding; one: automatic request context; multiple: explicit picker unless the session contains a valid `active_workspace_id`. Staff has no application bypass. Historical null-user memberships never grant access.

`require_household(request)` returns the current membership or raises `HouseholdRequired`. Middleware classifies resolved routes, never Accept headers or URL substrings, and translates missing context. Anonymous private HTML redirects to login; anonymous private JSON/export/image data returns 401 `{"error":"Authentication required."}`. Signed-in missing-context HTML redirects to onboarding/picker. Private data returns 409 `{"error":"Select a household to continue.","code":"household_required"}`. Foreign task IDs return 404 even for dual members. Future privileged actions within a selected household must return 403. There are no new owner-only write operations in Phase 1.

`POST households:switch` accepts `workspace_id`, requires CSRF and active membership, ignores `next`, redirects to the board. Invalid choice returns 400 without changing the selected session value. GET returns 405. Resolution never stores an automatic selection on GET and never changes household records; invalid stale session references are discarded rather than trusted. This reconciles automatic single membership context with read-only GET: only explicit switch POST stores a household choice.

All authenticated responses and all household-dependent responses have private/no-store caching and `Vary: Cookie`. Do not introduce shared household response caches. Public priority samples are fixed `(Low=2, Medium=4, High=3, Urgent=1)` for anonymous and signed-in callers; no task aggregate queries occur through public JSON, specification, image or embedded sample paths. Chart2 image renders selected-household daily data instead of serving an archived database snapshot. Chart specs preserve the existing URL/schema contract; their private data API enforces the current session independently.

## UI teammate interface

Context processor publishes `active_household`, `active_membership`, `household_memberships`, `can_manage_household` (OWNER only). Primary navigation contains Tasks and Household plus Home. Board contains title search, priority/type filters, Add task, Organize with AI, Insights, secondary product catalogue lookup, and accurately labeled bundled sample handbook help. Do not add grocery/expense links until those screens exist.

`TaskCreateForm(*args, membership=None, **kwargs)` and `TaskFilterForm(*args, membership=None, **kwargs)` default-deny workspace choices. Legacy `workspace` form field accepts only the selected household; creator and workspace are assigned server-side. `ReviewTaskForm` intentionally retains inheritance and its relationship-free constructor. Board context includes `tasks`, `filter_form`, `create_form`, `has_workspaces`, pagination (6 per page, newest created/task ID first), `filter_query`, and `has_filters`. Invalid filters return no rows with field errors; invalid creates preserve input. AI errors preserve submitted input/manual board access. Signed drafts require explicit human confirmation, current selected workspace and membership, and membership revalidation inside the transaction. Successful save returns to board with a message.

## Consolidation decisions and caller audit

Audit: project URLconfs, production Python imports, template references, tests, management commands, `.env.example`, `import_string`, and configured hook names were searched. Research/assignment folders remain historical evidence.

| Candidate | Callers/configuration | Decision and replacement |
|---|---|---|
| `task_manual_view`, `task_render_view`, `TaskBaseView`, `TaskListView`, `filter_tasks` | Four named task URL routes; historical tests/docs | Merge/remove implementations; one `legacy_task_list` GET adapter redirects to board. Old names/URLs preserved. |
| Standalone GET/POST search `_render_search` | `task_search:get`, `task_search:post` | Remove duplicate rendering/query workflow. GET redirects to board. POST explicitly calls board GET handler with body filters in memory; never invokes creation. |
| `tasks/task_list.html`, `tasks/search.html` | No remaining runtime callers after merge | Retire production templates to `docs/history/retired-templates/`; historical content preserved. |
| `reports.task_report`, `analytics.task_stats`, authenticated `vega.charts` | Named HTML URLs | Thin 302 adapters to Insights. Anonymous Vega landing remains a public sample embed. |
| Report `grouped_summary`, analytics grouping | Reports/priority chart | One scoped `workflows.task_insights.grouped_summary`; `task_summary(tasks)` supplies total/priority/type report format. `priority_counts(tasks)` only fills zero categories. `daily_task_counts(tasks)` stays a separate date-grouping operation shared by JSON and image adapters with explicit scoped input. |
| `reports.task_records(tasks)` | CSV and JSON downloads | Keep shared serialization allowlist and formula-safe CSV escaping; queryset is required and scoped by callers. |
| `reports/tasks.html`, `analytics/task_stats.html` | No runtime callers | Retire to historical templates; Insights supplies useful summaries/chart/downloads. |
| `api.brain_dump_extract` direct local extractor | JSON endpoint | Keep transport adapter; call `ai_adapter.get_suggestions(text)` shared with HTML. Preserve tasks/warnings/model_id/saved/message envelope; list subclass carries validated provider metadata. Expected validation/model errors remain 422; unexpected provider exceptions return safe 500 without raw details. |
| `ai_adapter.validate_suggestions` | Shared draft generator and existing tests | Keep schema validation through actual review form. Configured local/mock backend stays here. |
| `hf_local`, `services.brain_dump` parsing | Shared extraction, tests/research; handbook reuses model loading | Keep real runtime/parsing responsibilities; no generic AI framework. |
| `action_plans`, `action_plan_views` | Task detail, private API; GROQ configuration | Keep separate task-plan semantics and cooldown; selected household checked before provider call. |
| `ai_breakdown.suggest_steps` | HTML review; `HESTIA_TASK_BREAKDOWN_CALLABLE`, `.env.example`, tests | Keep referenced optional configured hook, bounded validation and approval. No provider introduced. |
| `services.ask_hestia` | Authenticated handbook page, tests; `a8.corpus.load_chunks` | Keep distinct retrieval. Bundled `a8/data` corpus, MiniLM embeddings and Qwen generator; no household database retrieval. |
| Product lookup | HTML and JSON adapters | Keep secondary catalogue comparison; `compare_products(query, *, workspace)` and `_internal_matches(query, *, workspace)` require scope for Products, ShoppingListEntry and shopping Tasks before external request. |
| Inventory placeholder | Not mounted by project URLconf | Future grocery implementation, not a production CRUD feature. No invented screens. |

Legacy GET aliases forward only supported `q`, `priority`, `task_type`, `page` filters. A posted/queried legacy workspace is validated against selection; an invalid workspace filter remains an error on the board rather than widening results. Arbitrary redirect targets are discarded. Legacy workspace-name HTML search is retired in favor of the current household context; API title/workspace-name filtering remains scoped. Canonical board ordering/pagination is retained rather than old primary-key search ordering. Historical tests expecting global data, four independent view styles, database-backed public samples, archived private images or fragmented navigation were intentionally updated to assert the new scoped behavior, schemas, escaping, CSRF and aliases.

## Stateless versus data-bearing AI

`api:brain-dump` is authenticated stateless extraction: bounded user text only, no household read/write, no selected membership required. It never saves tasks. `ask-hestia` is authenticated bundled sample retrieval: source is `a8.corpus` loading `a8/data`, not selected household documents. HTML brain-dump generation/review/save and all task-plan routes are household-dependent. Never send household data to a provider until selection and object access have passed; never persist AI output without approval.

## Future groceries and expenses

Reuse Workspace/Membership, this resolver, Django sessions and the same context. Resolve workspace and actor server-side on every request; revalidate on writes, scope root querysets before filters/aggregation/serialization, verify every related product/member/task/entry belongs to that workspace, return foreign-object 404 and selected-household privilege 403. No nullable creator fallback or staff bypass. Cache keys must include household and relevant user permissions, with invalidation on removal; default to no-store. Include A/B, dual-member, inactive/null-user, no-membership, forged related IDs, CSRF, exports and stale draft tests. Household creation, invitations, lifecycle, expiry, expenses, recurrence and deployment remain later phases.

## Verification record

Baseline: system check clean, no migration changes, 189 tests passed. Existing virtual environment used with explicit development settings, nonsecret local SECRET_KEY and offline Hugging Face flags. Tests create an isolated test database; no real environment/database copied. Final commands/counts are recorded in `household-phase1-verification.md`.

Signed-in browser proof used a separate disposable SQLite database in `/tmp`: login → dual-member picker → Alpha board → create → mock AI generation → review/confirm → board success message → scoped Insights → switch Beta (only Beta task visible) → Alpha detail 404 → deactivate Beta membership in fixture database → Beta detail 404 next request. At 390×844, board document width was 390 with no horizontal overflow. Action-plan provider calls, live model inference and external catalogue network requests were not performed; provider boundaries are tested with mocks. Separate-user session isolation is covered by regression tests, not claimed as a multi-browser walkthrough. PostgreSQL/concurrency proof was not performed. No push, PR or deployment.

## Complete resolved-route inventory

Generated from the root resolver below; framework account/admin routes delegate to their existing authorization, verification and CSRF controls and are not blocked by household selection. `H` = household HTML, `D` = household data, `S` = authenticated stateless, `P` = public sample/landing, `A` = existing accounts/admin. H/D rows use the common behavior above. Verification references cover concrete aliases and underlying destinations, not links alone. Static assets remain served by Django's development static handler or deployment static server; middleware imposes no household requirement.

| Resolved pattern | Route name | Policy | Verification |
|---|---|---|---|
| `/households/` | `households:list` | Selection HTML; switch POST | test_household_selection |
| `/households/onboarding/` | `households:onboarding` | Selection HTML; switch POST | test_household_selection |
| `/households/switch/` | `households:switch` | Selection HTML; switch POST | test_household_selection |
| `/vega-lite/` | `vega:charts` | P anonymous; H signed-in → Insights | test_vega; test_public_chart_variants_use_fictional_samples; test_missing_household_returns_409_for_private_data |
| `/vega-lite/<str:chart>.json` | `vega:spec` | P for chart1; D for chart2 | test_vega; test_public_chart_variants_use_fictional_samples; test_missing_household_returns_409_for_private_data |
| `/vega-lite/<str:chart>.png` | `vega:image` | P for chart1; D for chart2 | test_vega; test_public_chart_variants_use_fictional_samples; test_missing_household_returns_409_for_private_data |
| `/reports/tasks/` | `reports:task-report` | H | test_isolation; test_unified_flow; task form/search/AI suites |
| `/reports/tasks/export.csv` | `reports:tasks-csv` | D | test_isolation; api/report/analytics suites |
| `/reports/tasks/export.json` | `reports:tasks-json` | D | test_isolation; api/report/analytics suites |
| `/analytics/tasks/` | `analytics:task-stats` | H | test_isolation; test_unified_flow; task form/search/AI suites |
| `/analytics/tasks/priority.png` | `analytics:task-priority-chart` | D | test_isolation; api/report/analytics suites |
| `/` | `home` | P / signed-in context redirect | test_home_respects_household_state |
| `/accounts/signup/` | `accounts:signup` | A | households account/auth suites; Django admin |
| `/accounts/logout/` | `accounts:logout` | A | households account/auth suites; Django admin |
| `/accounts/login/` | `accounts:login` | A | households account/auth suites; Django admin |
| `/accounts/login/` | `account_login` | A | households account/auth suites; Django admin |
| `/accounts/signup/` | `account_signup` | A | households account/auth suites; Django admin |
| `/accounts/logout/` | `account_logout` | A | households account/auth suites; Django admin |
| `/accounts/confirm-email/` | `account_email_verification_sent` | A | households account/auth suites; Django admin |
| `/accounts/confirm-email/<str:key>/` | `account_confirm_email` | A | households account/auth suites; Django admin |
| `/accounts/inactive/` | `account_inactive` | A | households account/auth suites; Django admin |
| `/accounts/3rdparty/login/cancelled/` | `socialaccount_login_cancelled` | A | households account/auth suites; Django admin |
| `/accounts/3rdparty/login/error/` | `socialaccount_login_error` | A | households account/auth suites; Django admin |
| `/accounts/3rdparty/signup/` | `socialaccount_signup` | A | households account/auth suites; Django admin |
| `/accounts/3rdparty/` | `socialaccount_connections` | A | households account/auth suites; Django admin |
| `/accounts/google/login/` | `google_login` | A | households account/auth suites; Django admin |
| `/accounts/google/login/callback/` | `google_callback` | A | households account/auth suites; Django admin |
| `/accounts/google/login/token/` | `google_login_by_token` | A | households account/auth suites; Django admin |
| `/admin/` | `admin:index` | A | households account/auth suites; Django admin |
| `/admin/login/` | `admin:login` | A | households account/auth suites; Django admin |
| `/admin/logout/` | `admin:logout` | A | households account/auth suites; Django admin |
| `/admin/password_change/` | `admin:password_change` | A | households account/auth suites; Django admin |
| `/admin/password_change/done/` | `admin:password_change_done` | A | households account/auth suites; Django admin |
| `/admin/autocomplete/` | `admin:autocomplete` | A | households account/auth suites; Django admin |
| `/admin/jsi18n/` | `admin:jsi18n` | A | households account/auth suites; Django admin |
| `/admin/r/<path:content_type_id>/<path:object_id>/` | `admin:view_on_site` | A | households account/auth suites; Django admin |
| `/admin/auth/group/` | `admin:auth_group_changelist` | A | households account/auth suites; Django admin |
| `/admin/auth/group/add/` | `admin:auth_group_add` | A | households account/auth suites; Django admin |
| `/admin/auth/group/<path:object_id>/history/` | `admin:auth_group_history` | A | households account/auth suites; Django admin |
| `/admin/auth/group/<path:object_id>/delete/` | `admin:auth_group_delete` | A | households account/auth suites; Django admin |
| `/admin/auth/group/<path:object_id>/change/` | `admin:auth_group_change` | A | households account/auth suites; Django admin |
| `/admin/auth/group/<path:object_id>/` | `admin:(unnamed)` | A | households account/auth suites; Django admin |
| `/admin/auth/user/<id>/password/` | `admin:auth_user_password_change` | A | households account/auth suites; Django admin |
| `/admin/auth/user/` | `admin:auth_user_changelist` | A | households account/auth suites; Django admin |
| `/admin/auth/user/add/` | `admin:auth_user_add` | A | households account/auth suites; Django admin |
| `/admin/auth/user/<path:object_id>/history/` | `admin:auth_user_history` | A | households account/auth suites; Django admin |
| `/admin/auth/user/<path:object_id>/delete/` | `admin:auth_user_delete` | A | households account/auth suites; Django admin |
| `/admin/auth/user/<path:object_id>/change/` | `admin:auth_user_change` | A | households account/auth suites; Django admin |
| `/admin/auth/user/<path:object_id>/` | `admin:(unnamed)` | A | households account/auth suites; Django admin |
| `/admin/account/emailaddress/` | `admin:account_emailaddress_changelist` | A | households account/auth suites; Django admin |
| `/admin/account/emailaddress/add/` | `admin:account_emailaddress_add` | A | households account/auth suites; Django admin |
| `/admin/account/emailaddress/<path:object_id>/history/` | `admin:account_emailaddress_history` | A | households account/auth suites; Django admin |
| `/admin/account/emailaddress/<path:object_id>/delete/` | `admin:account_emailaddress_delete` | A | households account/auth suites; Django admin |
| `/admin/account/emailaddress/<path:object_id>/change/` | `admin:account_emailaddress_change` | A | households account/auth suites; Django admin |
| `/admin/account/emailaddress/<path:object_id>/` | `admin:(unnamed)` | A | households account/auth suites; Django admin |
| `/admin/socialaccount/socialapp/` | `admin:socialaccount_socialapp_changelist` | A | households account/auth suites; Django admin |
| `/admin/socialaccount/socialapp/add/` | `admin:socialaccount_socialapp_add` | A | households account/auth suites; Django admin |
| `/admin/socialaccount/socialapp/<path:object_id>/history/` | `admin:socialaccount_socialapp_history` | A | households account/auth suites; Django admin |
| `/admin/socialaccount/socialapp/<path:object_id>/delete/` | `admin:socialaccount_socialapp_delete` | A | households account/auth suites; Django admin |
| `/admin/socialaccount/socialapp/<path:object_id>/change/` | `admin:socialaccount_socialapp_change` | A | households account/auth suites; Django admin |
| `/admin/socialaccount/socialapp/<path:object_id>/` | `admin:(unnamed)` | A | households account/auth suites; Django admin |
| `/admin/socialaccount/socialtoken/` | `admin:socialaccount_socialtoken_changelist` | A | households account/auth suites; Django admin |
| `/admin/socialaccount/socialtoken/add/` | `admin:socialaccount_socialtoken_add` | A | households account/auth suites; Django admin |
| `/admin/socialaccount/socialtoken/<path:object_id>/history/` | `admin:socialaccount_socialtoken_history` | A | households account/auth suites; Django admin |
| `/admin/socialaccount/socialtoken/<path:object_id>/delete/` | `admin:socialaccount_socialtoken_delete` | A | households account/auth suites; Django admin |
| `/admin/socialaccount/socialtoken/<path:object_id>/change/` | `admin:socialaccount_socialtoken_change` | A | households account/auth suites; Django admin |
| `/admin/socialaccount/socialtoken/<path:object_id>/` | `admin:(unnamed)` | A | households account/auth suites; Django admin |
| `/admin/socialaccount/socialaccount/` | `admin:socialaccount_socialaccount_changelist` | A | households account/auth suites; Django admin |
| `/admin/socialaccount/socialaccount/add/` | `admin:socialaccount_socialaccount_add` | A | households account/auth suites; Django admin |
| `/admin/socialaccount/socialaccount/<path:object_id>/history/` | `admin:socialaccount_socialaccount_history` | A | households account/auth suites; Django admin |
| `/admin/socialaccount/socialaccount/<path:object_id>/delete/` | `admin:socialaccount_socialaccount_delete` | A | households account/auth suites; Django admin |
| `/admin/socialaccount/socialaccount/<path:object_id>/change/` | `admin:socialaccount_socialaccount_change` | A | households account/auth suites; Django admin |
| `/admin/socialaccount/socialaccount/<path:object_id>/` | `admin:(unnamed)` | A | households account/auth suites; Django admin |
| `/admin/households/workspace/` | `admin:households_workspace_changelist` | A | households account/auth suites; Django admin |
| `/admin/households/workspace/add/` | `admin:households_workspace_add` | A | households account/auth suites; Django admin |
| `/admin/households/workspace/<path:object_id>/history/` | `admin:households_workspace_history` | A | households account/auth suites; Django admin |
| `/admin/households/workspace/<path:object_id>/delete/` | `admin:households_workspace_delete` | A | households account/auth suites; Django admin |
| `/admin/households/workspace/<path:object_id>/change/` | `admin:households_workspace_change` | A | households account/auth suites; Django admin |
| `/admin/households/workspace/<path:object_id>/` | `admin:(unnamed)` | A | households account/auth suites; Django admin |
| `/admin/households/membership/` | `admin:households_membership_changelist` | A | households account/auth suites; Django admin |
| `/admin/households/membership/add/` | `admin:households_membership_add` | A | households account/auth suites; Django admin |
| `/admin/households/membership/<path:object_id>/history/` | `admin:households_membership_history` | A | households account/auth suites; Django admin |
| `/admin/households/membership/<path:object_id>/delete/` | `admin:households_membership_delete` | A | households account/auth suites; Django admin |
| `/admin/households/membership/<path:object_id>/change/` | `admin:households_membership_change` | A | households account/auth suites; Django admin |
| `/admin/households/membership/<path:object_id>/` | `admin:(unnamed)` | A | households account/auth suites; Django admin |
| `/admin/intake/sourcedocument/` | `admin:intake_sourcedocument_changelist` | A | households account/auth suites; Django admin |
| `/admin/intake/sourcedocument/add/` | `admin:intake_sourcedocument_add` | A | households account/auth suites; Django admin |
| `/admin/intake/sourcedocument/<path:object_id>/history/` | `admin:intake_sourcedocument_history` | A | households account/auth suites; Django admin |
| `/admin/intake/sourcedocument/<path:object_id>/delete/` | `admin:intake_sourcedocument_delete` | A | households account/auth suites; Django admin |
| `/admin/intake/sourcedocument/<path:object_id>/change/` | `admin:intake_sourcedocument_change` | A | households account/auth suites; Django admin |
| `/admin/intake/sourcedocument/<path:object_id>/` | `admin:(unnamed)` | A | households account/auth suites; Django admin |
| `/admin/intake/extractedfield/` | `admin:intake_extractedfield_changelist` | A | households account/auth suites; Django admin |
| `/admin/intake/extractedfield/add/` | `admin:intake_extractedfield_add` | A | households account/auth suites; Django admin |
| `/admin/intake/extractedfield/<path:object_id>/history/` | `admin:intake_extractedfield_history` | A | households account/auth suites; Django admin |
| `/admin/intake/extractedfield/<path:object_id>/delete/` | `admin:intake_extractedfield_delete` | A | households account/auth suites; Django admin |
| `/admin/intake/extractedfield/<path:object_id>/change/` | `admin:intake_extractedfield_change` | A | households account/auth suites; Django admin |
| `/admin/intake/extractedfield/<path:object_id>/` | `admin:(unnamed)` | A | households account/auth suites; Django admin |
| `/admin/inventory/product/` | `admin:inventory_product_changelist` | A | households account/auth suites; Django admin |
| `/admin/inventory/product/add/` | `admin:inventory_product_add` | A | households account/auth suites; Django admin |
| `/admin/inventory/product/<path:object_id>/history/` | `admin:inventory_product_history` | A | households account/auth suites; Django admin |
| `/admin/inventory/product/<path:object_id>/delete/` | `admin:inventory_product_delete` | A | households account/auth suites; Django admin |
| `/admin/inventory/product/<path:object_id>/change/` | `admin:inventory_product_change` | A | households account/auth suites; Django admin |
| `/admin/inventory/product/<path:object_id>/` | `admin:(unnamed)` | A | households account/auth suites; Django admin |
| `/admin/inventory/supplyitem/` | `admin:inventory_supplyitem_changelist` | A | households account/auth suites; Django admin |
| `/admin/inventory/supplyitem/add/` | `admin:inventory_supplyitem_add` | A | households account/auth suites; Django admin |
| `/admin/inventory/supplyitem/<path:object_id>/history/` | `admin:inventory_supplyitem_history` | A | households account/auth suites; Django admin |
| `/admin/inventory/supplyitem/<path:object_id>/delete/` | `admin:inventory_supplyitem_delete` | A | households account/auth suites; Django admin |
| `/admin/inventory/supplyitem/<path:object_id>/change/` | `admin:inventory_supplyitem_change` | A | households account/auth suites; Django admin |
| `/admin/inventory/supplyitem/<path:object_id>/` | `admin:(unnamed)` | A | households account/auth suites; Django admin |
| `/admin/inventory/shoppinglistentry/` | `admin:inventory_shoppinglistentry_changelist` | A | households account/auth suites; Django admin |
| `/admin/inventory/shoppinglistentry/add/` | `admin:inventory_shoppinglistentry_add` | A | households account/auth suites; Django admin |
| `/admin/inventory/shoppinglistentry/<path:object_id>/history/` | `admin:inventory_shoppinglistentry_history` | A | households account/auth suites; Django admin |
| `/admin/inventory/shoppinglistentry/<path:object_id>/delete/` | `admin:inventory_shoppinglistentry_delete` | A | households account/auth suites; Django admin |
| `/admin/inventory/shoppinglistentry/<path:object_id>/change/` | `admin:inventory_shoppinglistentry_change` | A | households account/auth suites; Django admin |
| `/admin/inventory/shoppinglistentry/<path:object_id>/` | `admin:(unnamed)` | A | households account/auth suites; Django admin |
| `/admin/workflows/task/` | `admin:workflows_task_changelist` | A | households account/auth suites; Django admin |
| `/admin/workflows/task/add/` | `admin:workflows_task_add` | A | households account/auth suites; Django admin |
| `/admin/workflows/task/<path:object_id>/history/` | `admin:workflows_task_history` | A | households account/auth suites; Django admin |
| `/admin/workflows/task/<path:object_id>/delete/` | `admin:workflows_task_delete` | A | households account/auth suites; Django admin |
| `/admin/workflows/task/<path:object_id>/change/` | `admin:workflows_task_change` | A | households account/auth suites; Django admin |
| `/admin/workflows/task/<path:object_id>/` | `admin:(unnamed)` | A | households account/auth suites; Django admin |
| `/admin/workflows/taskoccurrence/` | `admin:workflows_taskoccurrence_changelist` | A | households account/auth suites; Django admin |
| `/admin/workflows/taskoccurrence/add/` | `admin:workflows_taskoccurrence_add` | A | households account/auth suites; Django admin |
| `/admin/workflows/taskoccurrence/<path:object_id>/history/` | `admin:workflows_taskoccurrence_history` | A | households account/auth suites; Django admin |
| `/admin/workflows/taskoccurrence/<path:object_id>/delete/` | `admin:workflows_taskoccurrence_delete` | A | households account/auth suites; Django admin |
| `/admin/workflows/taskoccurrence/<path:object_id>/change/` | `admin:workflows_taskoccurrence_change` | A | households account/auth suites; Django admin |
| `/admin/workflows/taskoccurrence/<path:object_id>/` | `admin:(unnamed)` | A | households account/auth suites; Django admin |
| `/admin/workflows/assignment/` | `admin:workflows_assignment_changelist` | A | households account/auth suites; Django admin |
| `/admin/workflows/assignment/add/` | `admin:workflows_assignment_add` | A | households account/auth suites; Django admin |
| `/admin/workflows/assignment/<path:object_id>/history/` | `admin:workflows_assignment_history` | A | households account/auth suites; Django admin |
| `/admin/workflows/assignment/<path:object_id>/delete/` | `admin:workflows_assignment_delete` | A | households account/auth suites; Django admin |
| `/admin/workflows/assignment/<path:object_id>/change/` | `admin:workflows_assignment_change` | A | households account/auth suites; Django admin |
| `/admin/workflows/assignment/<path:object_id>/` | `admin:(unnamed)` | A | households account/auth suites; Django admin |
| `/admin/^(?P<app_label>auth|account|socialaccount|households|intake|inventory|workflows)/$` | `admin:app_list` | A | households account/auth suites; Django admin |
| `/admin/(?P<url>.*)$` | `admin:(unnamed)` | A | households account/auth suites; Django admin |
| `/lookup/` | `product-lookup` | H | test_isolation; test_unified_flow; task form/search/AI suites |
| `/api/tasks/<int:pk>/action-plan/` | `api:task-action-plan` | D | test_isolation; api/report/analytics suites |
| `/api/charts/task-priorities/` | `api:chart-priorities` | P | test_public_chart_variants_use_fictional_samples |
| `/api/charts/task-creations/` | `api:chart-creations` | D | test_isolation; api/report/analytics suites |
| `/api/external/products/` | `api:product-compare` | D | test_isolation; api/report/analytics suites |
| `/api/tasks/` | `api:task-list` | D | test_isolation; api/report/analytics suites |
| `/api/ai/brain-dump/` | `api:brain-dump` | S | test_ask_hestia_views / api.test_brain_dump / test_api |
| `/api/response-demo/` | `api:response-demo` | S | test_ask_hestia_views / api.test_brain_dump / test_api |
| `/tasks/search/` | `task_search:get` | H | test_isolation; test_unified_flow; task form/search/AI suites |
| `/tasks/search/post/` | `task_search:post` | H | test_isolation; test_unified_flow; task form/search/AI suites |
| `/tasks/manage/` | `task_forms:board` | H | test_isolation; test_unified_flow; task form/search/AI suites |
| `/tasks/ask/` | `ask-hestia` | S | test_ask_hestia_views / api.test_brain_dump / test_api |
| `/tasks/ai/` | `ai_tasks:brain-dump` | H | test_isolation; test_unified_flow; task form/search/AI suites |
| `/tasks/insights/` | `workflows:task-insights` | H | test_isolation; test_unified_flow; task form/search/AI suites |
| `/tasks/<int:pk>/action-plan/` | `workflows:task-action-plan` | H | test_isolation; test_unified_flow; task form/search/AI suites |
| `/tasks/manual/` | `workflows:task-manual` | H | test_isolation; test_unified_flow; task form/search/AI suites |
| `/tasks/render/` | `workflows:task-render` | H | test_isolation; test_unified_flow; task form/search/AI suites |
| `/tasks/cbv-base/` | `workflows:task-cbv-base` | H | test_isolation; test_unified_flow; task form/search/AI suites |
| `/tasks/cbv-generic/` | `workflows:task-cbv-generic` | H | test_isolation; test_unified_flow; task form/search/AI suites |
| `/tasks/<int:pk>/` | `workflows:task-detail` | H | test_isolation; test_unified_flow; task form/search/AI suites |
