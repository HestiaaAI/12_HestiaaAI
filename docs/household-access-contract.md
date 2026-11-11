# Household product access/UI contract — Phase 3

Current integrated product contract. The UI/grocery integration below supersedes historical Phase 1B handbook removal; Phase 2 adds authenticated household creation; Phase 3 adds owner invitations and verified explicit joining. Canonical task, grocery, roster, Insights and restored Ask Hestia journeys share the existing context. Removed assignment-only transports remain 404.

## Current application routes

| Path | Name | Methods / purpose | Policy / verification |
|---|---|---|---|
| `/` | `home` | GET/HEAD; landing or continuation | Public anonymous; signed-in → board or picker/onboarding. `test_home_respects_household_state` |
| `/households/` | `households:list` | GET; membership picker | Login; only active user memberships. `test_household_selection` |
| `/households/onboarding/` | `households:onboarding` | GET; explanation and Create household action | Login; existing members continue to board/picker. `test_onboarding` |
| `/households/create/` | `households:create` | GET form / CSRF POST creation | Login, including users with no membership; atomic server-owned household/owner; selects new household. `test_onboarding` |
| `/households/switch/` | `households:switch` | POST `workspace_id`, CSRF | Fresh active membership; invalid 400, GET 405, no external `next`; invalid choice preserves even stale session. `test_household_selection` |
| `/households/current/invites/` | `households:invites` | GET list/form; POST issue | Current selected OWNER, CSRF, signed one-use nonce, throttles; `test_invitation_views` |
| `/households/current/invites/<id>/revoke/` | `households:revoke-invite` | POST revoke pending | Current OWNER; foreign ID 404, roommate 403; CSRF |
| `/households/current/invites/<id>/resend/` | `households:resend-invite` | POST fresh link | Same owner/scope/CSRF/nonce/throttles as issue; prior pending links revoked |
| `/households/invites/<token>/` | `households:accept-invite` | GET preview; CSRF POST `action=accept` or `verify` | Public generic preview; matching verified allauth address for joining; `test_invitation_acceptance` |
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
- Future privileged operations on a selected household must use 403 for insufficient role. Phase 3 invitation issue/reissue/revoke requires current ownership.

Private and authenticated responses use no-store/private caching and `Vary: Cookie`. Do not introduce shared user/household content caches. The action-plan cooldown is a per-user timestamp, not a content cache. A removed/inactive/null-user membership cannot authorize a subsequent request or a fresh write check. Historical user data is not migrated/deleted.

## Request context and writes

`active_memberships(user) -> QuerySet[Membership]` selects active rows belonging to the authenticated user with workspace loaded; anonymous returns none. `resolve_active_membership(request)` populates one request-local snapshot reused by `require_household(request)` and template context. `request.household_memberships` is a tuple of already-loaded memberships; use truthiness/iteration, not QuerySet methods. The next request always re-queries. Exceptional access failures may explicitly refresh the snapshot.

Session selection remains `active_workspace_id`. One membership auto-resolves without storing a GET choice; multiple memberships require selection; stale references are discarded. Switch POST independently validates its posted ID before changing the session. GET never creates households, memberships or tasks.

Task creation resolves the selected workspace and creator server-side and rechecks the actor under `select_for_update()` inside the write transaction. Approved draft persistence also rechecks active actor/workspace inside its transaction. Request-local caching must never replace those write-time checks. AI drafts bind user, selected workspace, nonce, count, signature and session; changed selection or revoked access prevents persistence. No provider runs for unauthorized task/household requests. Generated plans/drafts remain previews until the explicit existing approval workflow saves them.

`compare_products(query, *, workspace)` and `_internal_matches(query, *, workspace)` require explicit scope. Products, shopping-list rows and shopping tasks are selected before public catalogue comparison. `task_summary(tasks)`/`grouped_summary(tasks, ...)` require scoped querysets; total derives from real priority counts. CSV uses the same server-selected workspace and explicit record allowlist.

## UI teammate contract

Context processor: `active_household`, `active_membership`, `household_memberships`, `can_manage_household` (OWNER). Primary navigation retains Tasks, Groceries, Household roster and Ask Hestia, plus shared household selection and its label. Board retains filtering, Add task, Organize with AI, Insights and catalogue lookup. Ask Hestia is accurately labeled bundled example content. No expense/invitation placeholders or coursework footer.

Stable template blocks: `base.html` retains `content`, `navigation`, `extra_css`, `extra_js`; board adds `task_board_actions`; Insights adds `insight_summary`. Styling remains the UI teammate's responsibility.

Board context: `tasks`, `filter_form`, `create_form`, `has_workspaces`, `has_filters`, paginator/page object and `filter_query`. Six tasks/page, newest created/task ID first. Invalid filters show errors with zero rows, and invalid creates preserve values. `TaskCreateForm`/`TaskFilterForm` still accept `membership=None` and default-deny scope; `workspace` is now a hidden constrained field, not a second household picker. Tampering is rejected. Selected household appears in navigation. BrainDumpForm prepopulates the same hidden selected workspace. ReviewTaskForm remains a relationship-free subclass with compatible constructor.

Creation and confirmed AI save return to the plain canonical board URL with a success message. Provider failure preserves entered draft text and the manual board path. Insights contains accessible numeric text and accurate empty states; no fictional household activity. CSV action is explicit. Catalogue and task detail have direct back links. Mock drafting is allowed only as clearly labeled test/preview configuration; no mock activity is shown in Insights until a human explicitly approves/persists drafts.

## Retired surfaces and dependency decisions

See `household-product-decisions.md` for caller audit and replacements. Four list aliases, standalone search, reports/statistics redirect pages, Vega/sample/spec/image routes, all unused internal JSON transports and response-demo no longer resolve. The old report CSV URL is removed; consumers use the new canonical CSV name. The remaining `api` module contains catalogue helpers/tests, not an exposed HTTP namespace.

The sample handbook was retired in historical Phase 1B and restored by the subsequent integrated baseline. Its current page/service/tests remain; corpus data is product-local under `workflows/services/handbook_data` and does not import `a8.corpus`. No household-aware retrieval claim is made. Research notebooks/folders/results remain historical source; `.gitattributes` excludes them, their evidence/docs and the tracked SQLite database from product archives. No user database, secret, untracked output or research result was deleted. The restored handbook uses its product-local corpus and retains lazy inference; research code remains outside product archives.

Local Hugging Face task extraction and Groq task-plan generation remain distinct, useful capabilities. The optional bounded step hook remains because the approved-draft screen/config uses it. There is no generic AI framework. JSON-only metadata wrappers and eager service reexports are removed. Plotting dependencies move to `requirements-research.txt`; NumPy, Torch, Transformers and tokenizer/model support remain because the enabled local drafting provider uses them. Startup tests actively block research/plotting/inference imports and still pass ordinary application startup. A release archive test excludes research/data and retains product providers/migrations.

## Future groceries/expenses and later phases

Reuse Workspace/Membership, the snapshot/context and explicit fresh mutation checks. Derive workspace and actor on the server, scope root queries before filters/serialization, validate every related ID in the selected workspace, return foreign-object 404 and selected-household privilege 403, require CSRF on mutations, preserve private cache isolation. Include A/B, dual-member, removed/inactive/null-user, forged related IDs, exports and write-time revocation tests. Do not show unimplemented screens/actions. Household creation is implemented in Phase 2. Invitations and verified joining are implemented in Phase 3. Member lifecycle, new grocery features, expenses, recurrence and deployment remain later phases.

## Complete resolved framework/product inventory

The generated appendix includes account/admin-generated patterns as well as the product routes; pattern count is not a feature count. `A` delegates to framework account/admin tests and controls, `H` uses the private household HTML policy above, `D` is canonical private CSV, `Selection` is authenticated selection/onboarding, `P` is the public landing with signed-in continuation. Static serving is outside this resolver inventory and does not load household records.

| Resolved pattern | Name | Policy | Verification |
|---|---|---|---|
| `/households/current/invites/` | `households:invites` | Selected OWNER | test_invitation_views |
| `/households/current/invites/<int:invitation_id>/revoke/` | `households:revoke-invite` | Selected OWNER / CSRF POST | test_invitation_views |
| `/households/current/invites/<int:invitation_id>/resend/` | `households:resend-invite` | Selected OWNER / CSRF POST | test_invitation_views |
| `/households/invites/<str:token>/` | `households:accept-invite` | Public private preview / verified explicit join | test_invitation_acceptance |
| `/groceries/` | `groceries:list` | H | inventory.tests / inventory.test_integration / test_onboarding |
| `/groceries/household/` | `groceries:household` | H | inventory.tests / inventory.test_integration / test_onboarding |
| `/groceries/<int:workspace_id>/` | `groceries:workspace` | H | inventory.tests / inventory.test_integration / test_onboarding |
| `/groceries/<int:workspace_id>/scan/` | `groceries:scan` | H | inventory.tests / inventory.test_integration / test_onboarding |
| `/groceries/<int:workspace_id>/add/` | `groceries:add` | H | inventory.tests / inventory.test_integration / test_onboarding |
| `/groceries/<int:workspace_id>/<int:batch_id>/edit/` | `groceries:edit` | H | inventory.tests / inventory.test_integration / test_onboarding |
| `/groceries/<int:workspace_id>/<int:batch_id>/close/` | `groceries:close` | H | inventory.tests / inventory.test_integration / test_onboarding |
| `/groceries/<int:workspace_id>/suggest/` | `groceries:suggest` | H | inventory.tests / inventory.test_integration / test_onboarding |
| `/groceries/<int:workspace_id>/approve/` | `groceries:approve` | H | inventory.tests / inventory.test_integration / test_onboarding |
| `/tasks/ask/` | `ask-hestia` | Authenticated bundled handbook | workflows.test_ask_hestia_views |
| `/households/create/` | `households:create` | Selection / creation | test_onboarding / test_household_selection / test_household_context |
| `/households/` | `households:list` | Selection / creation | test_onboarding / test_household_selection / test_household_context |
| `/households/onboarding/` | `households:onboarding` | Selection / creation | test_onboarding / test_household_selection / test_household_context |
| `/households/switch/` | `households:switch` | Selection / creation | test_onboarding / test_household_selection / test_household_context |
| `/` | `home` | P | test_onboarding / test_unified_flow |
| `/accounts/signup/` | `accounts:signup` | A | households account/signup/OAuth suites; Django admin |
| `/accounts/logout/` | `accounts:logout` | A | households account/signup/OAuth suites; Django admin |
| `/accounts/login/` | `accounts:login` | A | households account/signup/OAuth suites; Django admin |
| `/accounts/login/` | `account_login` | A | households account/signup/OAuth suites; Django admin |
| `/accounts/signup/` | `account_signup` | A | households account/signup/OAuth suites; Django admin |
| `/accounts/logout/` | `account_logout` | A | households account/signup/OAuth suites; Django admin |
| `/accounts/confirm-email/` | `account_email_verification_sent` | A | households account/signup/OAuth suites; Django admin |
| `/accounts/confirm-email/<str:key>/` | `account_confirm_email` | A | households account/signup/OAuth suites; Django admin |
| `/accounts/inactive/` | `account_inactive` | A | households account/signup/OAuth suites; Django admin |
| `/accounts/3rdparty/login/cancelled/` | `socialaccount_login_cancelled` | A | households account/signup/OAuth suites; Django admin |
| `/accounts/3rdparty/login/error/` | `socialaccount_login_error` | A | households account/signup/OAuth suites; Django admin |
| `/accounts/3rdparty/signup/` | `socialaccount_signup` | A | households account/signup/OAuth suites; Django admin |
| `/accounts/3rdparty/` | `socialaccount_connections` | A | households account/signup/OAuth suites; Django admin |
| `/accounts/google/login/` | `google_login` | A | households account/signup/OAuth suites; Django admin |
| `/accounts/google/login/callback/` | `google_callback` | A | households account/signup/OAuth suites; Django admin |
| `/accounts/google/login/token/` | `google_login_by_token` | A | households account/signup/OAuth suites; Django admin |
| `/admin/` | `admin:index` | A | households account/signup/OAuth suites; Django admin |
| `/admin/login/` | `admin:login` | A | households account/signup/OAuth suites; Django admin |
| `/admin/logout/` | `admin:logout` | A | households account/signup/OAuth suites; Django admin |
| `/admin/password_change/` | `admin:password_change` | A | households account/signup/OAuth suites; Django admin |
| `/admin/password_change/done/` | `admin:password_change_done` | A | households account/signup/OAuth suites; Django admin |
| `/admin/autocomplete/` | `admin:autocomplete` | A | households account/signup/OAuth suites; Django admin |
| `/admin/jsi18n/` | `admin:jsi18n` | A | households account/signup/OAuth suites; Django admin |
| `/admin/r/<path:content_type_id>/<path:object_id>/` | `admin:view_on_site` | A | households account/signup/OAuth suites; Django admin |
| `/admin/auth/group/` | `admin:auth_group_changelist` | A | households account/signup/OAuth suites; Django admin |
| `/admin/auth/group/add/` | `admin:auth_group_add` | A | households account/signup/OAuth suites; Django admin |
| `/admin/auth/group/<path:object_id>/history/` | `admin:auth_group_history` | A | households account/signup/OAuth suites; Django admin |
| `/admin/auth/group/<path:object_id>/delete/` | `admin:auth_group_delete` | A | households account/signup/OAuth suites; Django admin |
| `/admin/auth/group/<path:object_id>/change/` | `admin:auth_group_change` | A | households account/signup/OAuth suites; Django admin |
| `/admin/auth/group/<path:object_id>/` | `admin:(unnamed)` | A | households account/signup/OAuth suites; Django admin |
| `/admin/auth/user/<id>/password/` | `admin:auth_user_password_change` | A | households account/signup/OAuth suites; Django admin |
| `/admin/auth/user/` | `admin:auth_user_changelist` | A | households account/signup/OAuth suites; Django admin |
| `/admin/auth/user/add/` | `admin:auth_user_add` | A | households account/signup/OAuth suites; Django admin |
| `/admin/auth/user/<path:object_id>/history/` | `admin:auth_user_history` | A | households account/signup/OAuth suites; Django admin |
| `/admin/auth/user/<path:object_id>/delete/` | `admin:auth_user_delete` | A | households account/signup/OAuth suites; Django admin |
| `/admin/auth/user/<path:object_id>/change/` | `admin:auth_user_change` | A | households account/signup/OAuth suites; Django admin |
| `/admin/auth/user/<path:object_id>/` | `admin:(unnamed)` | A | households account/signup/OAuth suites; Django admin |
| `/admin/account/emailaddress/` | `admin:account_emailaddress_changelist` | A | households account/signup/OAuth suites; Django admin |
| `/admin/account/emailaddress/add/` | `admin:account_emailaddress_add` | A | households account/signup/OAuth suites; Django admin |
| `/admin/account/emailaddress/<path:object_id>/history/` | `admin:account_emailaddress_history` | A | households account/signup/OAuth suites; Django admin |
| `/admin/account/emailaddress/<path:object_id>/delete/` | `admin:account_emailaddress_delete` | A | households account/signup/OAuth suites; Django admin |
| `/admin/account/emailaddress/<path:object_id>/change/` | `admin:account_emailaddress_change` | A | households account/signup/OAuth suites; Django admin |
| `/admin/account/emailaddress/<path:object_id>/` | `admin:(unnamed)` | A | households account/signup/OAuth suites; Django admin |
| `/admin/socialaccount/socialapp/` | `admin:socialaccount_socialapp_changelist` | A | households account/signup/OAuth suites; Django admin |
| `/admin/socialaccount/socialapp/add/` | `admin:socialaccount_socialapp_add` | A | households account/signup/OAuth suites; Django admin |
| `/admin/socialaccount/socialapp/<path:object_id>/history/` | `admin:socialaccount_socialapp_history` | A | households account/signup/OAuth suites; Django admin |
| `/admin/socialaccount/socialapp/<path:object_id>/delete/` | `admin:socialaccount_socialapp_delete` | A | households account/signup/OAuth suites; Django admin |
| `/admin/socialaccount/socialapp/<path:object_id>/change/` | `admin:socialaccount_socialapp_change` | A | households account/signup/OAuth suites; Django admin |
| `/admin/socialaccount/socialapp/<path:object_id>/` | `admin:(unnamed)` | A | households account/signup/OAuth suites; Django admin |
| `/admin/socialaccount/socialtoken/` | `admin:socialaccount_socialtoken_changelist` | A | households account/signup/OAuth suites; Django admin |
| `/admin/socialaccount/socialtoken/add/` | `admin:socialaccount_socialtoken_add` | A | households account/signup/OAuth suites; Django admin |
| `/admin/socialaccount/socialtoken/<path:object_id>/history/` | `admin:socialaccount_socialtoken_history` | A | households account/signup/OAuth suites; Django admin |
| `/admin/socialaccount/socialtoken/<path:object_id>/delete/` | `admin:socialaccount_socialtoken_delete` | A | households account/signup/OAuth suites; Django admin |
| `/admin/socialaccount/socialtoken/<path:object_id>/change/` | `admin:socialaccount_socialtoken_change` | A | households account/signup/OAuth suites; Django admin |
| `/admin/socialaccount/socialtoken/<path:object_id>/` | `admin:(unnamed)` | A | households account/signup/OAuth suites; Django admin |
| `/admin/socialaccount/socialaccount/` | `admin:socialaccount_socialaccount_changelist` | A | households account/signup/OAuth suites; Django admin |
| `/admin/socialaccount/socialaccount/add/` | `admin:socialaccount_socialaccount_add` | A | households account/signup/OAuth suites; Django admin |
| `/admin/socialaccount/socialaccount/<path:object_id>/history/` | `admin:socialaccount_socialaccount_history` | A | households account/signup/OAuth suites; Django admin |
| `/admin/socialaccount/socialaccount/<path:object_id>/delete/` | `admin:socialaccount_socialaccount_delete` | A | households account/signup/OAuth suites; Django admin |
| `/admin/socialaccount/socialaccount/<path:object_id>/change/` | `admin:socialaccount_socialaccount_change` | A | households account/signup/OAuth suites; Django admin |
| `/admin/socialaccount/socialaccount/<path:object_id>/` | `admin:(unnamed)` | A | households account/signup/OAuth suites; Django admin |
| `/admin/households/workspace/` | `admin:households_workspace_changelist` | A | households account/signup/OAuth suites; Django admin |
| `/admin/households/workspace/add/` | `admin:households_workspace_add` | A | households account/signup/OAuth suites; Django admin |
| `/admin/households/workspace/<path:object_id>/history/` | `admin:households_workspace_history` | A | households account/signup/OAuth suites; Django admin |
| `/admin/households/workspace/<path:object_id>/delete/` | `admin:households_workspace_delete` | A | households account/signup/OAuth suites; Django admin |
| `/admin/households/workspace/<path:object_id>/change/` | `admin:households_workspace_change` | A | households account/signup/OAuth suites; Django admin |
| `/admin/households/workspace/<path:object_id>/` | `admin:(unnamed)` | A | households account/signup/OAuth suites; Django admin |
| `/admin/households/membership/` | `admin:households_membership_changelist` | A | households account/signup/OAuth suites; Django admin |
| `/admin/households/membership/add/` | `admin:households_membership_add` | A | households account/signup/OAuth suites; Django admin |
| `/admin/households/membership/<path:object_id>/history/` | `admin:households_membership_history` | A | households account/signup/OAuth suites; Django admin |
| `/admin/households/membership/<path:object_id>/delete/` | `admin:households_membership_delete` | A | households account/signup/OAuth suites; Django admin |
| `/admin/households/membership/<path:object_id>/change/` | `admin:households_membership_change` | A | households account/signup/OAuth suites; Django admin |
| `/admin/households/membership/<path:object_id>/` | `admin:(unnamed)` | A | households account/signup/OAuth suites; Django admin |
| `/admin/intake/sourcedocument/` | `admin:intake_sourcedocument_changelist` | A | households account/signup/OAuth suites; Django admin |
| `/admin/intake/sourcedocument/add/` | `admin:intake_sourcedocument_add` | A | households account/signup/OAuth suites; Django admin |
| `/admin/intake/sourcedocument/<path:object_id>/history/` | `admin:intake_sourcedocument_history` | A | households account/signup/OAuth suites; Django admin |
| `/admin/intake/sourcedocument/<path:object_id>/delete/` | `admin:intake_sourcedocument_delete` | A | households account/signup/OAuth suites; Django admin |
| `/admin/intake/sourcedocument/<path:object_id>/change/` | `admin:intake_sourcedocument_change` | A | households account/signup/OAuth suites; Django admin |
| `/admin/intake/sourcedocument/<path:object_id>/` | `admin:(unnamed)` | A | households account/signup/OAuth suites; Django admin |
| `/admin/intake/extractedfield/` | `admin:intake_extractedfield_changelist` | A | households account/signup/OAuth suites; Django admin |
| `/admin/intake/extractedfield/add/` | `admin:intake_extractedfield_add` | A | households account/signup/OAuth suites; Django admin |
| `/admin/intake/extractedfield/<path:object_id>/history/` | `admin:intake_extractedfield_history` | A | households account/signup/OAuth suites; Django admin |
| `/admin/intake/extractedfield/<path:object_id>/delete/` | `admin:intake_extractedfield_delete` | A | households account/signup/OAuth suites; Django admin |
| `/admin/intake/extractedfield/<path:object_id>/change/` | `admin:intake_extractedfield_change` | A | households account/signup/OAuth suites; Django admin |
| `/admin/intake/extractedfield/<path:object_id>/` | `admin:(unnamed)` | A | households account/signup/OAuth suites; Django admin |
| `/admin/inventory/product/` | `admin:inventory_product_changelist` | A | households account/signup/OAuth suites; Django admin |
| `/admin/inventory/product/add/` | `admin:inventory_product_add` | A | households account/signup/OAuth suites; Django admin |
| `/admin/inventory/product/<path:object_id>/history/` | `admin:inventory_product_history` | A | households account/signup/OAuth suites; Django admin |
| `/admin/inventory/product/<path:object_id>/delete/` | `admin:inventory_product_delete` | A | households account/signup/OAuth suites; Django admin |
| `/admin/inventory/product/<path:object_id>/change/` | `admin:inventory_product_change` | A | households account/signup/OAuth suites; Django admin |
| `/admin/inventory/product/<path:object_id>/` | `admin:(unnamed)` | A | households account/signup/OAuth suites; Django admin |
| `/admin/inventory/supplyitem/` | `admin:inventory_supplyitem_changelist` | A | households account/signup/OAuth suites; Django admin |
| `/admin/inventory/supplyitem/add/` | `admin:inventory_supplyitem_add` | A | households account/signup/OAuth suites; Django admin |
| `/admin/inventory/supplyitem/<path:object_id>/history/` | `admin:inventory_supplyitem_history` | A | households account/signup/OAuth suites; Django admin |
| `/admin/inventory/supplyitem/<path:object_id>/delete/` | `admin:inventory_supplyitem_delete` | A | households account/signup/OAuth suites; Django admin |
| `/admin/inventory/supplyitem/<path:object_id>/change/` | `admin:inventory_supplyitem_change` | A | households account/signup/OAuth suites; Django admin |
| `/admin/inventory/supplyitem/<path:object_id>/` | `admin:(unnamed)` | A | households account/signup/OAuth suites; Django admin |
| `/admin/inventory/shoppinglistentry/` | `admin:inventory_shoppinglistentry_changelist` | A | households account/signup/OAuth suites; Django admin |
| `/admin/inventory/shoppinglistentry/add/` | `admin:inventory_shoppinglistentry_add` | A | households account/signup/OAuth suites; Django admin |
| `/admin/inventory/shoppinglistentry/<path:object_id>/history/` | `admin:inventory_shoppinglistentry_history` | A | households account/signup/OAuth suites; Django admin |
| `/admin/inventory/shoppinglistentry/<path:object_id>/delete/` | `admin:inventory_shoppinglistentry_delete` | A | households account/signup/OAuth suites; Django admin |
| `/admin/inventory/shoppinglistentry/<path:object_id>/change/` | `admin:inventory_shoppinglistentry_change` | A | households account/signup/OAuth suites; Django admin |
| `/admin/inventory/shoppinglistentry/<path:object_id>/` | `admin:(unnamed)` | A | households account/signup/OAuth suites; Django admin |
| `/admin/workflows/task/` | `admin:workflows_task_changelist` | A | households account/signup/OAuth suites; Django admin |
| `/admin/workflows/task/add/` | `admin:workflows_task_add` | A | households account/signup/OAuth suites; Django admin |
| `/admin/workflows/task/<path:object_id>/history/` | `admin:workflows_task_history` | A | households account/signup/OAuth suites; Django admin |
| `/admin/workflows/task/<path:object_id>/delete/` | `admin:workflows_task_delete` | A | households account/signup/OAuth suites; Django admin |
| `/admin/workflows/task/<path:object_id>/change/` | `admin:workflows_task_change` | A | households account/signup/OAuth suites; Django admin |
| `/admin/workflows/task/<path:object_id>/` | `admin:(unnamed)` | A | households account/signup/OAuth suites; Django admin |
| `/admin/workflows/taskoccurrence/` | `admin:workflows_taskoccurrence_changelist` | A | households account/signup/OAuth suites; Django admin |
| `/admin/workflows/taskoccurrence/add/` | `admin:workflows_taskoccurrence_add` | A | households account/signup/OAuth suites; Django admin |
| `/admin/workflows/taskoccurrence/<path:object_id>/history/` | `admin:workflows_taskoccurrence_history` | A | households account/signup/OAuth suites; Django admin |
| `/admin/workflows/taskoccurrence/<path:object_id>/delete/` | `admin:workflows_taskoccurrence_delete` | A | households account/signup/OAuth suites; Django admin |
| `/admin/workflows/taskoccurrence/<path:object_id>/change/` | `admin:workflows_taskoccurrence_change` | A | households account/signup/OAuth suites; Django admin |
| `/admin/workflows/taskoccurrence/<path:object_id>/` | `admin:(unnamed)` | A | households account/signup/OAuth suites; Django admin |
| `/admin/workflows/assignment/` | `admin:workflows_assignment_changelist` | A | households account/signup/OAuth suites; Django admin |
| `/admin/workflows/assignment/add/` | `admin:workflows_assignment_add` | A | households account/signup/OAuth suites; Django admin |
| `/admin/workflows/assignment/<path:object_id>/history/` | `admin:workflows_assignment_history` | A | households account/signup/OAuth suites; Django admin |
| `/admin/workflows/assignment/<path:object_id>/delete/` | `admin:workflows_assignment_delete` | A | households account/signup/OAuth suites; Django admin |
| `/admin/workflows/assignment/<path:object_id>/change/` | `admin:workflows_assignment_change` | A | households account/signup/OAuth suites; Django admin |
| `/admin/workflows/assignment/<path:object_id>/` | `admin:(unnamed)` | A | households account/signup/OAuth suites; Django admin |
| `/admin/^(?P<app_label>auth|account|socialaccount|households|intake|inventory|workflows)/$` | `admin:app_list` | A | households account/signup/OAuth suites; Django admin |
| `/admin/(?P<url>.*)$` | `admin:(unnamed)` | A | households account/signup/OAuth suites; Django admin |
| `/lookup/` | `product-lookup` | H | workflows / test_isolation / api.tests / analytics.tests |
| `/tasks/manage/` | `task_forms:board` | H | workflows / test_isolation / api.tests / analytics.tests |
| `/tasks/ai/` | `ai_tasks:brain-dump` | H | workflows / test_isolation / api.tests / analytics.tests |
| `/tasks/export.csv` | `workflows:task-export-csv` | D | reports.tests / test_isolation |
| `/tasks/insights/` | `workflows:task-insights` | H | workflows / test_isolation / api.tests / analytics.tests |
| `/tasks/<int:pk>/action-plan/` | `workflows:task-action-plan` | H | workflows / test_isolation / api.tests / analytics.tests |
| `/tasks/<int:pk>/` | `workflows:task-detail` | H | workflows / test_isolation / api.tests / analytics.tests |

## UI/grocery integration — 2026-11-10

Supersedes Phase 1B removal of Ask Hestia. `/tasks/ask/` (`ask-hestia`) is authenticated, read-only handbook help; it does not require household selection or use private household records. Its corpus ships under workflows/services/handbook_data and does not import research packages.

The `groceries` namespace is selected-household protected. `/groceries/` redirects to the selected household; `/groceries/household/` shows its roster. Explicit workspace paths must equal the selected household, even for dual members. Switch with the existing CSRF POST household picker; query parameters and grocery links do not change selection. Every batch create/edit/close, receipt save and meal-task approval revalidates active membership inside its transaction. Existing task creator/AI approval protection and private no-store responses remain.

UI: Tasks, Groceries, Household and Ask Hestia share the teammate’s palette/assets and selected-household label. Insights, CSV, task drafting and catalogue lookup remain contextual task-board actions. Assignment list/search/chart routes stay removed. GroceryBatch migration 0002 is required; the incoming public-task visibility flag/migration was omitted because all task data is already household-scoped. Existing research files and main are untouched.


## Phase 2 onboarding and creation — 2026-11-10

`HouseholdCreateForm`: required trimmed `name` (1–120 characters), required valid ZoneInfo `timezone` (max 50, initial `America/Chicago`). No global name uniqueness. Inputs render with Django-associated labels/help/errors and the existing teammate `demo-panel`/`demo-form` visual system. Invalid POST preserves input and renders status 200 without records or selection changes from creation.

`create_household(*, user, name, timezone) -> Membership`: rejects anonymous/inactive actors, validates the same fields, locks/rechecks the active account inside an atomic transaction, creates `Workspace(workspace_type=HOUSEHOLD)` plus active OWNER Membership. Owner can assign tasks, manage sources and receive assignments. Display name is trimmed full name or username, truncated to the model limit (100). Actor, role, permissions and workspace type cannot be supplied by the browser. Failed member creation rolls back the workspace.

`GET/POST households:create` is authenticated but intentionally does not require an existing household membership. GET is read-only. After the atomic service succeeds, POST sets `active_workspace_id`, refreshes request-local context, queues a success message and redirects to `task_forms:board`. The new household has no copied tasks/grocery batches. Existing members can create another household, retaining original memberships/data. Standard POST/Redirect/GET prevents refresh resubmission; repeated POST/retry idempotency is not implemented or claimed.

Zero memberships → useful onboarding with a working Create household action and CSRF POST sign-out. One → existing auto-resolved context/board. Multiple unselected → shared picker with Create another household. Visiting onboarding with a selected/sole household continues to board; unselected multiple continues to picker without loops. Inactive/stale memberships follow the same existing resolver rules. Creation always selects its new household for Tasks, Groceries, roster and Insights. Restored Ask Hestia remains accessible with the same navigation label and bundled-source limitation.

Home/allauth account/social adapters, safe local `next`, email-verification settings, signup-disable policy and OAuth linking protections are unchanged. Mandatory verification is exercised end-to-end by tests before creation; token/profile calls are mocked for Google callback tests. Signup does not auto-enroll into any household. Creation accepts no external redirect target. Context, private no-store responses, fresh task/grocery mutation checks, signed AI drafts, startup/archive tests and fixed query budgets remain intact.

UI teammate: new `templates/households/create.html` receives `form` with stable fields/IDs `name`/`id_name` and `timezone`/`id_timezone`; existing shared template context is unchanged. The picker receives the existing `memberships` snapshot and uses POST switch forms plus the new create link. No new grocery features, invite/join links or lifecycle controls are introduced. Verification evidence/limits are in `household-phase2-verification.md`.

## Phase 3 invitation and verification contract

Owners reach invitations from the Household roster. Issue accepts `email` and a signed `nonce`; workspace, inviter and role are server-owned. Reissue accepts a nonce and derives the email from its scoped invitation. Revoke accepts only CSRF. Recipient emails are trimmed/lowercased/validated. Status is derived from revoked/accepted timestamps and seven-day expiry (equal to now is expired). Foreign IDs are 404; selected-household roommates are 403. Every write rechecks ownership in its transaction.

Issuance returns a direct POST response to display the newly generated copyable link once. A signed user/workspace nonce expires after one hour; an atomic cache consume plus unique persisted SHA-256 `request_digest` prevents repeat issuance even after cache loss. No raw copy link is stored in the database or session. Reloading the GET does not recover it; reissue creates another token and revokes preceding pending links for that recipient in that household. Tokens have 32 random bytes and only unique SHA-256 digests persist. Emails and all links use `ACCOUNT_PUBLIC_ORIGIN`, never incoming Host.

Allauth rate limits are 10 issues per minute per user/household and 1 per minute per household/normalized recipient, covering reissue too. Configure a shared atomic cache for all workers; the development local-memory cache provides process-local throttling only. Database nonce uniqueness protects successful issuance replay independently of that cache. Nonces consumed by invalid/rate-limited attempts require a fresh page.

Acceptance GET is read-only and initially generic. Only the matching verified allauth EmailAddress authorizes revealing the invited household name and accepting; User.email alone cannot authorize membership. Signup, sign-in and verification retain a strictly validated local invitation continuation, including a temporary session path. This path is navigation state, never a grant. Mandatory verification/OAuth protections remain. Optional general verification still requires matching verified invitation identity; the `verify` POST uses allauth delivery and throttles and never joins, even when the address is already verified. Wrong-account GET never signs out; switching accounts is a CSRF POST.

The transactional order is workspace, invitation, account (acceptance), then membership. New or reactivated membership is ordinary ADULT, displayed Roommate, with assignment/receipt enabled and source management disabled. Active membership remains unchanged. Used links can only return their original accepting account's still-active membership; they cannot reactivate a removed member. Historical null-user rows are never guessed/attached. Selection changes and context refresh happen only after success, followed by the task board welcome. No member removal/transfer/role editing is shipped.

Mail is scheduled with `transaction.on_commit`; rollback sends nothing. Delivery failure does not invalidate the invitation and the owner sees an honest copy/reissue recovery message. “Sent” means accepted by the configured backend, not verified inbox delivery. Console preview is intentionally suppressed for invitations and invitation-related verification to avoid logging bearer links/private email. Configure SMTP or another private Django backend; no verification bypass is provided. File/locmem backends are test fixtures, not inbox proof.

Invitation responses are private/no-store, vary on Cookie, use no-referrer and noindex, and load local assets only. Acceptance CSP restricts scripts/styles/forms to the same origin (inline existing styles allowed; no inline scripts). A small local form handler uses same-origin, CORS-mode fetch with ordinary CSRF FormData: native no-referrer POSTs can send Origin:null and fail Django's origin check. It neither trusts null origins nor disables CSRF. Returned HTML replaces the page; redirects update its local URL, preserving one-time links, welcome/error messages and keyboard submission. JavaScript is required for these private forms, with an explicit noscript explanation.

Django's default console/admin-email handlers prepend a redaction filter for raw/encoded invitation paths, private recipient/request data and exception locals. The live request is never mutated. Deployment must additionally redact token-bearing paths and encoded invitation continuations in reverse-proxy/CDN/load-balancer access logs, tracing/APM, analytics, request-body capture and error reporters; Python logging filters cannot protect those external systems. Do not log request bodies/cookies or full query strings. For example map any request URI containing `/households/invites/` or `%2Fhouseholds%2Finvites%2F` to a fixed `[private invitation]` log value before writing access logs. Keep account confirmation credentials private too. Use HTTPS and secure session/CSRF cookies in deployment.
