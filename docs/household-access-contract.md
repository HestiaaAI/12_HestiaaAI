# Household product access/UI contract — Phase 1B

This replaces Phase 1A's compatibility and public-sample contract. The product has one task board, one Insights destination, and no assignment-only HTTP transports. Removed paths return 404 rather than redirects.

## Current application routes

| Path | Name | Methods / purpose | Policy / verification |
|---|---|---|---|
| `/` | `home` | GET/HEAD; landing or continuation | Public anonymous; signed-in → board or picker/onboarding. `test_home_respects_household_state` |
| `/households/` | `households:list` | GET; membership picker | Login; only active user memberships. `test_household_selection` |
| `/households/onboarding/` | `households:onboarding` | GET; useful no-membership explanation | Login; no invented create/invite actions. `test_household_selection` |
| `/households/switch/` | `households:switch` | POST `workspace_id`, CSRF | Fresh active membership; invalid 400, GET 405, no external `next`; invalid choice preserves even stale session. `test_household_selection` |
| `/tasks/manage/` | `task_forms:board` | GET filter, POST create | Selected household; `test_forms`, `test_isolation` |
| `/tasks/<pk>/` | `workflows:task-detail` | GET; details | Selected household query before object lookup; foreign 404 even for dual member. `test_isolation`, `workflows.tests` |
| `/tasks/<pk>/action-plan/` | `workflows:task-action-plan` | GET disclosure, POST plan preview | Selected task before provider; CSRF; no writes. `test_action_plan_views`, `test_ai_action_plan` |
| `/tasks/ai/` | `ai_tasks:brain-dump` | GET, POST generate/review/breakdown/save | Selected household; signed drafts, explicit approval, fresh transactional actor on save. `test_ai`, `test_isolation`, `test_unified_flow` |
| `/tasks/insights/` | `workflows:task-insights` | GET; real numeric totals/priority/type lists | Selected scoped task queryset; no PNG/JS/chart request. `analytics.tests`, `test_isolation` |
| `/tasks/export.csv` | `workflows:task-export-csv` | GET; CSV download from Insights | Private data boundary; exact scoped rows and formula-safe cells. `reports.tests`, `api.test_access`, `test_isolation` |
| `/lookup/` | `product-lookup` | GET; secondary catalogue comparison | Selected household before internal lookup/upstream request; public results never persisted. `api.tests`, `api.test_access`, `test_isolation` |

Accounts, password reset, email verification, OAuth/provider callbacks and Django admin retain their existing routes and framework controls. Static assets remain outside household authorization. No household selection is required to log in, verify, recover an account, sign out, or use authorized admin.

## Policy ownership and status behavior

`households.access.HouseholdContextMiddleware` owns application login/household translation and private response caching. The overlapping AssignmentAccessMiddleware, ApiAccessMiddleware and public sample allowlist are removed. Allauth/admin own account/admin authorization; CSRF middleware owns CSRF rejection; scoped detail lookups own object 404. Views keep HTTP method decorators and fresh actor validation at mutations.

- Anonymous private HTML → login redirect with safe local `next`.
- Anonymous CSV → 401 `{"error":"Authentication required."}`.
- Signed-in private HTML with no active memberships → onboarding; multiple memberships without a valid selection → picker.
- Signed-in CSV without context → 409 `{"error":"Select a household to continue.","code":"household_required"}`.
- Foreign task → 404, including dual-member sessions; no staff bypass outside admin.
- Invalid switch → 400 without selection mutation; wrong methods → 405 once access requirements pass; CSRF rejection → 403.
- Future privileged operations on a selected household must use 403 for insufficient role. Phase 1B adds no owner-only writes.

Private and authenticated responses use no-store/private caching and `Vary: Cookie`. Do not introduce shared user/household content caches. The action-plan cooldown is a per-user timestamp, not a content cache. A removed/inactive/null-user membership cannot authorize a subsequent request or a fresh write check. Historical user data is not migrated/deleted.

## Request context and writes

`active_memberships(user) -> QuerySet[Membership]` selects active rows belonging to the authenticated user with workspace loaded; anonymous returns none. `resolve_active_membership(request)` populates one request-local snapshot reused by `require_household(request)` and template context. `request.household_memberships` is a tuple of already-loaded memberships; use truthiness/iteration, not QuerySet methods. The next request always re-queries. Exceptional access failures may explicitly refresh the snapshot.

Session selection remains `active_workspace_id`. One membership auto-resolves without storing a GET choice; multiple memberships require selection; stale references are discarded. Switch POST independently validates its posted ID before changing the session. GET never creates households, memberships or tasks.

Task creation resolves the selected workspace and creator server-side and rechecks the actor under `select_for_update()` inside the write transaction. Approved draft persistence also rechecks active actor/workspace inside its transaction. Request-local caching must never replace those write-time checks. AI drafts bind user, selected workspace, nonce, count, signature and session; changed selection or revoked access prevents persistence. No provider runs for unauthorized task/household requests. Generated plans/drafts remain previews until the explicit existing approval workflow saves them.

`compare_products(query, *, workspace)` and `_internal_matches(query, *, workspace)` require explicit scope. Products, shopping-list rows and shopping tasks are selected before public catalogue comparison. `task_summary(tasks)`/`grouped_summary(tasks, ...)` require scoped querysets; total derives from real priority counts. CSV uses the same server-selected workspace and explicit record allowlist.

## UI teammate contract

Context processor: `active_household`, `active_membership`, `household_memberships`, `can_manage_household` (OWNER). Navigation offers Tasks and Household, with Home continuing to the same context. Board offers filtering, Add task, Organize with AI, Insights and secondary Product catalogue lookup. No handbook, public examples, grocery/expense placeholders or coursework footer.

Stable template blocks: `base.html` retains `content`, `navigation`, `extra_css`, `extra_js`; board adds `task_board_actions`; Insights adds `insight_summary`. Styling remains the UI teammate's responsibility.

Board context: `tasks`, `filter_form`, `create_form`, `has_workspaces`, `has_filters`, paginator/page object and `filter_query`. Six tasks/page, newest created/task ID first. Invalid filters show errors with zero rows, and invalid creates preserve values. `TaskCreateForm`/`TaskFilterForm` still accept `membership=None` and default-deny scope; `workspace` is now a hidden constrained field, not a second household picker. Tampering is rejected. Selected household appears in navigation. BrainDumpForm prepopulates the same hidden selected workspace. ReviewTaskForm remains a relationship-free subclass with compatible constructor.

Creation and confirmed AI save return to the plain canonical board URL with a success message. Provider failure preserves entered draft text and the manual board path. Insights contains accessible numeric text and accurate empty states; no fictional household activity. CSV action is explicit. Catalogue and task detail have direct back links. Mock drafting is allowed only as clearly labeled test/preview configuration; no mock activity is shown in Insights until a human explicitly approves/persists drafts.

## Retired surfaces and dependency decisions

See `household-product-decisions.md` for caller audit and replacements. Four list aliases, standalone search, reports/statistics redirect pages, Vega/sample/spec/image routes, all unused internal JSON transports and response-demo no longer resolve. The old report CSV URL is removed; consumers use the new canonical CSV name. The remaining `api` module contains catalogue helpers/tests, not an exposed HTTP namespace.

The sample handbook page/form/service/command and its tests are removed; there is no household-aware retrieval claim. Its only `a8.corpus` runtime import is gone. Research notebooks/folders/results remain historical source; `.gitattributes` excludes them, their evidence/docs and the tracked SQLite database from product archives. No user database, secret, untracked output or research result was deleted. Historical handbook evaluation depending on old adapters requires the Phase 1A revision.

Local Hugging Face task extraction and Groq task-plan generation remain distinct, useful capabilities. The optional bounded step hook remains because the approved-draft screen/config uses it. There is no generic AI framework. JSON-only metadata wrappers and eager service reexports are removed. Plotting dependencies move to `requirements-research.txt`; NumPy, Torch, Transformers and tokenizer/model support remain because the enabled local drafting provider uses them. Startup tests actively block research/plotting/inference imports and still pass ordinary application startup. A release archive test excludes research/data and retains product providers/migrations.

## Future groceries/expenses and later phases

Reuse Workspace/Membership, the snapshot/context and explicit fresh mutation checks. Derive workspace and actor on the server, scope root queries before filters/serialization, validate every related ID in the selected workspace, return foreign-object 404 and selected-household privilege 403, require CSRF on mutations, preserve private cache isolation. Include A/B, dual-member, removed/inactive/null-user, forged related IDs, exports and write-time revocation tests. Do not show unimplemented screens/actions. Household creation, invitations, member lifecycle, expiry, expenses, recurrence and deployment remain later phases.

## Complete resolved framework/product inventory

The generated appendix includes account/admin-generated patterns as well as the product routes; pattern count is not a feature count. `A` delegates to framework account/admin tests and controls, `H` uses the private household HTML policy above, `D` is canonical private CSV, `Selection` is authenticated selection/onboarding, `P` is the public landing with signed-in continuation. Static serving is outside this resolver inventory and does not load household records.

| Resolved pattern | Name | Policy | Verification |
|---|---|---|---|
| `/households/` | `households:list` | Selection | test_household_selection / test_household_context |
| `/households/onboarding/` | `households:onboarding` | Selection | test_household_selection / test_household_context |
| `/households/switch/` | `households:switch` | Selection | test_household_selection / test_household_context |
| `/` | `home` | P | test_unified_flow; household auth tests |
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
| `/lookup/` | `product-lookup` | H | test_forms / test_ai / test_action_plan_views / test_isolation / test_unified_flow / api.tests / analytics.tests |
| `/tasks/manage/` | `task_forms:board` | H | test_forms / test_ai / test_action_plan_views / test_isolation / test_unified_flow / api.tests / analytics.tests |
| `/tasks/ai/` | `ai_tasks:brain-dump` | H | test_forms / test_ai / test_action_plan_views / test_isolation / test_unified_flow / api.tests / analytics.tests |
| `/tasks/export.csv` | `workflows:task-export-csv` | D | reports.tests; api.test_access; test_isolation |
| `/tasks/insights/` | `workflows:task-insights` | H | test_forms / test_ai / test_action_plan_views / test_isolation / test_unified_flow / api.tests / analytics.tests |
| `/tasks/<int:pk>/action-plan/` | `workflows:task-action-plan` | H | test_forms / test_ai / test_action_plan_views / test_isolation / test_unified_flow / api.tests / analytics.tests |
| `/tasks/<int:pk>/` | `workflows:task-detail` | H | test_forms / test_ai / test_action_plan_views / test_isolation / test_unified_flow / api.tests / analytics.tests |
