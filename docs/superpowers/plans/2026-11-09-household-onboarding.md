# Household Onboarding Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task by task. This is a reviewable proposal, not approval to implement product changes.

**Goal:** Let real roommates sign up, create a household, invite and join, manage membership, and share only their household's data.

**Architecture:** Retain Django sessions, allauth, Workspace and Membership. Add invitations and a request-level active household resolver; enforce membership in queries and writes rather than relying on navigation or login alone. Use Django HTML forms initially so the UI revamp can proceed without introducing a second frontend or authentication system.

**Tech stack:** Existing Django application, allauth, SQLite for local development, existing PostgreSQL shared configuration. No new runtime dependency planned.

**Spec:** User's demo requirements, captured below. Product defaults in this document are proposals to review before implementation.

## Scope and proposed decisions

Darshan owns onboarding, household creation, invitation and acceptance, active household context, member management and shared authorization. Anushka owns task lifecycle; Chaitanya owns grocery batches, expiry and suggestions; Shivani owns shared expenses. The UI teammate owns visual design and shared navigation. Native mobile, PWA installation, grocery AI and expense implementation are separate deliverables.

A first-time member signs up/signs in, chooses Create household or follows an invitation, then enters the task board. Users may belong to multiple households because the existing model supports that; only one is active per session. A removed member loses access on their next request. No account is silently added to a sample household.

Use the existing OWNER role for household administrators and ADULT for ordinary roommates internally, displaying “Owner” and “Roommate.” Do not rename legacy roles or models. All active roommates can create shared tasks and receive assignments; owners manage household settings, invites and membership. Preserve existing specialized permission fields until their consumers are audited.

Invitations are email-bound, single-use links valid for seven days, revocable by an owner. Acceptance requires a signed-in account with a verified allauth EmailAddress matching the normalized invitation email; verification must be available even where general signup verification is optional. Provide a copyable link for a live demo and optional email delivery using configured Django mail. Invite links must survive signup/login/verification. GET never joins, revokes or removes anyone.

## Backend review — at commit 421b75d

| Area | Evidence | Assessment / required work |
|---|---|---|
| Account security | households/account_views.py, account_adapter.py, auth_urls.py; settings/base.py | Signup/login/logout and allauth integration exist, including safe redirect and mail-failure handling. Keep them; add onboarding routing and invite continuation. Base settings currently set email verification to none. |
| Household data | households/models.py; migrations/0001_initial.py | Workspace and Membership already connect users and household data, with per-user/workspace uniqueness and is_active. No Invitation model exists. Membership.user is nullable, so seeded or historical members are not necessarily login accounts. |
| Household experience | households/views.py; hestia_config/urls.py | Placeholder household view and no household route group. Create/join/settings/member screens need implementation. |
| Login boundary | households/access.py; api/middleware.py | Protects routes from anonymous requests; does not enforce household ownership. Authentication is not household isolation. |
| Task writes | workflows/task_forms.py; forms_views.py | available_workspaces() returns every workspace. A signed-in nonmember can select another household and create a task; creator membership can be null. Must scope and assign workspace/creator server-side. |
| Reads and exports | workflows/views.py, search_views.py; api/views.py; reports/views.py; analytics/views.py; api/chart_views.py | Global task querysets and aggregates expose other households to signed-in users. Audit all paths, including direct detail IDs, CSV/JSON and images. |
| Product lookup | api/external.py; api/views.py | Internal product, shopping-entry and shopping-task matches query all households. Add required workspace to internal comparison; public product search itself is unrelated to membership. |
| AI paths | workflows/ai_forms.py, ai_views.py, action_plan_views.py | Brain dump and action plans already check active membership. Reuse strengths; align with selected household and recheck on save. ReviewTaskForm inherits TaskCreateForm, so form signature changes must preserve this subclass. |
| Ask Hestia | workflows/ask_hestia_views.py | Answers from bundled handbook, not workspace records. Keep that distinction clear; any future household retrieval must be scoped before sending context to a model. |
| Inventory | inventory/models.py; inventory/views.py | Existing Product, SupplyItem and ShoppingListEntry are workspace-linked. Grocery UI and expiry/batches remain Chaitanya's scope. Shared relationship validation is needed when those writes ship. |
| Existing tests | households/test_access.py; api/test_access.py | Some fixtures deliberately expect users without memberships to read global records. Update these expectations rather than retaining a global-data compatibility bypass. |
| Public chart | settings/base.py PUBLIC_API_VIEW_NAMES; api/chart_views.py | Anonymous task-priority aggregate currently reads real Task rows. Proposed demo policy: preserve its URL/schema with fixed fictional sample data; authenticated charts use scoped real data. Historical assignment tests must change explicitly. |

Baseline on original checkout: `python manage.py check` passed; `python manage.py test households api.test_access --verbosity 0` passed 48 tests. This establishes existing behavior, not security readiness. No full-suite or deployed-environment verification was performed. No live external AI calls were needed.

## Branch and collaboration

Plan branch: `codex/household-onboarding-demo-plan`, based on local HEAD `421b75d`. This is the current development branch's committed snapshot, not a verified release/default-branch baseline. Confirm the team's integration base before implementation. Existing .gitignore, database and output changes in the original checkout are unrelated and remain there.

Workspace: `/Users/darshan/Documents/Projects/12_HestiaaAI-household-demo`.

Darshan owns households Python files, migrations, household tests and integration of scoped query helpers. UI teammate owns templates/households, shared styles and base navigation. Agree field names and routes below first. Darshan may supply minimal semantic templates in a separate commit if UI work is not yet ready. Coordinate before editing existing task templates/forms with Anushka; maintain backward-compatible constructors where inherited by AI forms. Do not redesign task workflow in the isolation change.

## Global constraints

- User-facing term: Household; internal model: Workspace. No duplicate Household model.
- Default deny: missing/inactive membership never returns global data, including for staff outside Django admin.
- Derive workspace and acting membership on the server; validate all related IDs within the same workspace.
- CSRF-protected POST for mutations; login-required HTML redirects; JSON retains 401 for anonymous access.
- JSON household-dependent endpoints return 409 with `code: household_required` if no active household can be resolved; foreign objects return 404; insufficient role returns 403.
- Preserve existing account security and verification controls. No new auth tokens, framework or frontend stack.
- No destructive migration, automatic adoption of orphaned demo rows or deletion of historical assignment evidence.
- Public demo aggregates must contain only fixed fictional data, never production household aggregates.

## Review focus

1. Stale active-household session after removal: revalidate every request and deny stale writes (tasks 1, 4).
2. Invitation stolen/replayed, expired, revoked or used by wrong email: no membership created (task 3).
3. Parallel invitation acceptance and last-owner changes: atomic outcome, no duplicate membership or ownerless active household (tasks 3, 5).
4. Forged nested IDs, report URLs and AI draft workspace: no read, write or external AI payload across households (task 4).
5. Existing inactive and null-user memberships: no implicit login access or duplicate/reactivated account except an explicit valid reinvitation (tasks 1, 3).

## Stable UI and teammate contract (proposed)

All paths below are new except existing accounts and task board. Use named routes in templates. Form errors render status 200, successful mutations redirect (POST/Redirect/GET). Authenticated responses containing household data use private/no-store caching; never share cached responses between sessions.

| Route / name under households | Method | Fields / behavior |
|---|---|---|
| /households/onboarding/ — onboarding | GET | Create or join explanation; show current memberships without exposing other households |
| /households/create/ — create | GET/POST | name (trimmed, 1–120), timezone (valid IANA zone; America/Chicago default); atomically create Workspace + OWNER membership |
| /households/ — list | GET | Active memberships only; each row links to POST switch form |
| /households/switch/ — switch | POST | workspace_id; validate active membership; update session then redirect task_forms:board |
| /households/current/ — detail | GET/POST | Household name/timezone; POST owner-only |
| /households/current/members/ — members | GET | Active roster with display names and UI permissions; email visible to owner only |
| /households/current/invites/ — invite | GET/POST | Owner only; email. Response includes pending invites; new raw link only on creation |
| /households/current/invites/<id>/revoke/ — revoke-invite | POST | Owner only; household-scoped invitation ID |
| /households/invites/<token>/ — accept-invite | GET/POST | GET preview/confirmation, POST accept; unauthenticated request preserves safe local continuation |
| /households/current/members/<id>/remove/ — remove-member | POST | Owner only; deactivate target; no last-owner removal |
| /households/current/leave/ — leave | POST | Deactivate self; last owner must first transfer ownership |
| /households/current/members/<id>/transfer/ — transfer-owner | POST | Current owner only; target active member; atomically promote target and demote actor |

Shared template context: `active_household`, `active_membership`, `household_memberships`, `can_manage_household`. Invite screens additionally receive `invitation`, `invite_url` only on creation, and stable errors `invalid`, `expired`, `revoked`, `used`, `email_mismatch`, `email_unverified`. Do not put tokens in analytics, error logs or referrer headers; acceptance page sets Referrer-Policy: no-referrer and loads no third-party assets.

## Task 1 — Shared household context and authorization

**Files:** extend households/access.py; create households/context.py, households/context_processors.py and households/test_household_context.py; update settings/base.py middleware/context processors.

**Interfaces:** `active_memberships(user) -> QuerySet[Membership]`; `resolve_active_membership(request) -> Membership | None`; `require_household(request) -> Membership` (HTML onboarding redirect or JSON policy above); `require_owner(membership) -> None` raises PermissionDenied. Request carries `active_membership` and `active_household`. Session stores only `active_workspace_id`.

- [ ] Write tests: zero memberships resolves None; one auto-selects; multiple require explicit selection if session missing; inactive/null-user memberships excluded; tampered session cannot select another household; removed membership denied next request; staff gets no bypass.
- [ ] Run `python manage.py test households.test_household_context` and confirm failure from missing behavior.
- [ ] Implement resolver: requery active membership on every request; clear invalid session; no `.first()` fallback for multiple households. Middleware populates context but does not globally block account/invite/static/admin routes. Views enforce requirements explicitly.
- [ ] Run targeted tests to green; commit `feat(households): resolve active household and permissions`.

## Task 2 — Create household and route onboarding

**Files:** create households/forms.py, households/urls.py, households/services.py, households/test_onboarding.py; implement households/views.py; update households/account_adapter.py, hestia_config/urls.py; coordinate templates/households/onboarding.html, create.html, list.html.

**Interfaces:** `create_household(*, user, name: str, timezone: str) -> Membership`; new routes as contract above. Owner can assign/manage sources and receive assignments. Ordinary members can assign/receive tasks; source-management remains owner-only.

- [ ] Write tests for create-plus-owner transaction, blank/long name and invalid timezone, anonymous redirect, CSRF failure, duplicate display names allowed, no sample data adoption, safe next URL and invitation continuation after login/verification, switching and no-membership onboarding.
- [ ] Run `python manage.py test households.test_onboarding` to confirm red.
- [ ] Implement atomic creation and scoped selection. Override allauth login/signup redirect hooks to resume safe invite first, otherwise onboarding for zero memberships, picker for multiple, board for one. Existing safe next destinations remain subject to view-level household checks. Set active session only after transaction succeeds.
- [ ] Run onboarding and existing signup/OAuth tests; update only intentional destination assertions. Commit `feat(households): add household creation and onboarding`.

## Task 3 — Invitations and joining

**Files:** extend households/models.py, services.py, forms.py, views.py, urls.py and admin.py; create migration 0002_household_invitation.py, households/test_invitations.py and household invitation email templates; coordinate invite/accept templates.

**Data:** HouseholdInvitation has workspace, normalized email, unique token_digest, invited_by (nullable Membership with SET_NULL), created_at, expires_at, accepted_at, accepted_by (nullable user), revoked_at. Generate a 32-byte URL-safe secret with Python secrets; persist only SHA-256 digest. Expiry = creation + seven days. No uniqueness constraint on pending email is required: each link independently expires/revokes and membership uniqueness prevents duplication. Owner UI explains that reissuing revokes previous pending links for that household/email.

**Interfaces:** `issue_invitation(*, actor: Membership, email: str) -> tuple[HouseholdInvitation, str]`; `accept_invitation(*, user, raw_token: str) -> Membership`; `revoke_invitation(*, actor, invitation_id: int) -> None`.

- [ ] Write tests: owner-only issuance/revoke; wrong household ID; token absent from database; boundary expiry; bad token; wrong/unverified email; GET does not mutate; POST CSRF; correct join creates ADULT once; duplicate acceptance by same member is harmless; replay by another account denied; inactive membership reactivated only by valid new invite; revoked/used link never reactivates removed member.
- [ ] Run `python manage.py test households.test_invitations` to confirm red.
- [ ] Implement membership and invite updates in one transaction. Lock workspace/invitation consistently, recheck owner/membership and invite state inside transaction. Keep uniqueness constraint as final safeguard. Test concurrency with separate connections on PostgreSQL; SQLite locking is not equivalent.
- [ ] Generate absolute links using ACCOUNT_PUBLIC_ORIGIN, not untrusted Host. Store raw URL only long enough for creation response; regeneration issues a new token and revokes previous pending invites. Return generic invalid-link error to unauthenticated users. Preserve token locally through allauth without allowing external redirect.
- [ ] Deliver optional email after commit, handling mail errors without losing invite or showing false delivery success; copy-link flow must work without SMTP. Test locmem mail and mocked SMTP failure. Apply existing allauth rate-limit patterns to issuance/acceptance attempts; test configured limits without inventing a second limiter.
- [ ] Run invitation/account tests and migration checks; commit `feat(households): add secure roommate invitations`.

## Task 4 — Close cross-household reads and writes

**Files:** workflows/task_forms.py, forms_views.py, views.py, search_views.py, task_queries.py, ai_forms.py, ai_views.py, action_plan_views.py; api/views.py, external.py, chart_views.py; reports/views.py; analytics/views.py, vega_views.py; settings/base.py; related access/form/report/analytics tests. Inspect their helpers and URL aliases before editing.

**Interfaces:** scoped code consumes `require_household(request)` and its workspace. `TaskCreateForm(..., membership=...)` and `TaskFilterForm(..., membership=...)` restrict querysets; maintain AI subclass compatibility explicitly. `compare_products(query, *, workspace)` and its internal lookup require workspace; update every caller. Report/chart helpers accept a scoped queryset rather than opening a global queryset themselves.

- [ ] Add two-household fixtures (owner A, roommate A, owner B, unaffiliated user, inactive member). Assert foreign content absent from all task list/detail/search variants, /api/tasks/, lookup results, exports, reports, charts/images and AI draft/save paths. Foreign detail ID returns 404; forged workspace/creator/member/product/task IDs never write. No-membership response cannot expose seeded rows.
- [ ] Run targeted tests and confirm failures before changes. Include a spy proving unauthorized AI requests never reach provider calls.
- [ ] Replace global query roots with active-workspace filtering before user filters and aggregations. Remove household choice from create UI where possible; reject tampered legacy workspace inputs. Set workspace and creator membership server-side; never save with null creator for a real user submission. Keep GET read-only.
- [ ] Align AI active-workspace validation at both generation and confirmation. Existing membership checks stay in place. Pass scoped querysets into shared report/chart/image helpers, and ensure caching cannot mix households.
- [ ] Keep anonymous priority-chart URL/schema working using fixed fictional samples; update historical assignment tests to describe the intentional policy change. Do not exempt a route merely because an old assignment called it public.
- [ ] Document required inventory/expense write contract for teammates: parent workspace from active membership, related FK ownership checked, list/detail queries scoped, no nullable actor fallback. Existing inventory lookup is fixed here; future grocery/expense CRUD must ship its own isolation tests.
- [ ] Run `python manage.py test households workflows api reports analytics` with AI/network calls mocked by tests. Commit `fix(access): isolate household data across application routes`.

## Task 5 — Member lifecycle and settings

**Files:** households/services.py, forms.py, views.py, urls.py; create households/test_members.py; coordinate detail/members templates.

**Interfaces:** `update_household(*, actor, name, timezone) -> Workspace`; `remove_member(*, actor, membership_id) -> None`; `leave_household(*, actor) -> None`; `transfer_ownership(*, actor, membership_id) -> None`.

- [ ] Write failing tests for owner-only settings/removal/transfer, roommate leave, foreign target IDs, active target required, last-owner removal/leave denied, transfer promotes target and demotes actor, historical task references preserved, next-request access revoked.
- [ ] Implement soft deactivation. Lock workspace then affected memberships inside atomic transactions; repeat permission/last-owner checks after lock. Do not delete users or historical memberships. Shared service callers must use this lock order, including invitation issuance and acceptance.
- [ ] Run member tests to green, plus PostgreSQL TransactionTestCase coverage for simultaneous last-owner changes and invitation acceptance. SQLite-only runs must report concurrency gate unverified. Commit `feat(households): manage roommates and household ownership`.

## Task 6 — Integrate UI and prove demo readiness

**Files:** templates/households/*.html, shared base navigation (identify actual base before edits); create households/management/commands/seed_household_demo.py, households/test_demo_seed.py and docs/demo-households.md; update .env.example only for any actually added setting.

- [ ] Agree contract with UI teammate before template changes. Render mobile-friendly onboarding, create, invitation confirmation, household picker and member states; forms retain CSRF and accessible error associations. Show selected household in navigation.
- [ ] Add idempotent demo seed with two clearly fictional households and at least three accounts; never set a universal production password. Accept passwords from an explicit local setup input; guard against production invocation and avoid modifying existing real accounts/data. Test rerun behavior and production guard before implementation.
- [ ] Run `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py test households workflows api reports analytics` and clean-database migrate/reverse/reapply of the new invitation migration. Reuse installed environment; do not download local language models to run access tests.
- [ ] Verify migrations on the deployment database engine with a backup/rollback plan. Review production public origin, allowed hosts, HTTPS/session/CSRF settings, signup policy and email verification/delivery. Do not switch verification off merely to pass the demo.
- [ ] In separate browser sessions: create A, send/copy invite, sign up B, verify email, accept and confirm same roster/task data; create C in household B and prove all A data absent; revoke invite, expire invite and remove B to prove access loss. Verify mobile viewport and actual error/empty states. Record outcomes, not just screenshots.
- [ ] Commit UI integration and demo instructions separately from backend changes. Prepare a reviewable PR; deployment is a separate final action after required review and checks.

## Implementation order and stop condition

Complete tasks 1–3 first to unblock UI integration. Task 4 is mandatory before claiming real-household readiness; household screens alone do not meet the isolation requirement. Task 5 completes member lifecycle; task 6 verifies the integrated demo. Estimate after confirming the integration base and running the broader test suite; no schedule promise from this review.

Done means two real roommate accounts can join one household, collaborate on its records, switch safely, and lose access when removed, while another household cannot discover those records through any remaining application route. Anushka, Chaitanya and Shivani can use one documented household contract. Full grocery AI, task recurrence, expense settlement and native/PWA packaging remain separately owned work.

## Plan self-review

Scope covered: account continuation, create/join/invite/revoke, verified identity, active shared workspace, settings/roster/leave/transfer/remove, existing read/write isolation, teammate contract, migration and demo gates. Five review-focus cases map to named tests above. No application code or schema has been changed by preparing this plan. Product defaults and public-chart policy need team review before execution.
