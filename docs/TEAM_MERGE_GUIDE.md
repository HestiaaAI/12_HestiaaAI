# Hestia team feature integration guide

Reviewed 2026-11-11. This is a product integration contract for Darshan, Shivani, Anushka and Chaitanya and their AI agents. It preserves everyone's implemented features while making them use one application architecture. It is not permission to push, merge main, deploy, email users or change grading data.

## 1. Baseline and actual remote review

| Source | Reviewed tip | What is present / integration status |
|---|---|---|
| origin/household-member-management | 9f9405b | Published Phase 1–4 foundation (implementation tip 85f6d61) plus integration instructions: cleanup, UI/groceries, Ask Hestia, onboarding/create, verified invitations, settings, roster, remove/leave/transfer. Phase 4 report records 367 whole-project tests with 8 PostgreSQL skips; that report was inspected, not independently rerun in this review. |
| origin/household-invitations | 42a7121 | Older Phase 3 branch; use origin/household-member-management for integration. |
| origin/household-product-cleanup | 109d2d3 | Older remote snapshot; does not contain all local integration/onboarding/invitation/member-management work. Do not use as current integration base. |
| origin/main | fc037f5 | Assignment/grading baseline; keep A8/A9 functionality and grading deployment here until released by user. |
| origin/cn32-demo | c7fc59f | Chaitanya: groceries/receipt/voice/UI plus thermostat planner; earlier 95ff152 grocery work is already integrated locally. Latest new feature is weather-aware thermostat. |
| origin/codex/cn32-shared-expenses | 3890ded | Shivani: expenses, settlements, purchase lists/receipt baskets, avatars, trends and recurring reminders. Its parent is c7fc59f: it already includes Chaitanya's thermostat work. This existing remote name is reported verbatim; never create a new branch containing codex. |
| Anushka dynamic tasks | Not found | Remote author/history review found assignment work, but no identifiable newly published dynamic-task branch. Obtain exact pushed branch/commit before assessing or merging it. Do not assume an old assignment branch contains the implementation. |

The fetch and source review completed. No teammate feature was merged or run during this documentation task. Commit IDs are a snapshot: refetch and inspect changes before executing. No full independent security audit or live financial/weather-provider proof is claimed.

### Conflict simulation against local 85f6d61

`git merge-tree --write-tree --name-only HEAD <source>` was used without changing the checkout/index.

- cn32-demo: conflicts in households/models.py, inventory/views.py, static files/css/demo.css and deleted templates/inventory/household.html.
- expenses branch: conflicts in hestia_config/settings/base.py, hestia_config/urls.py, households/models.py, households/test_access.py, inventory/views.py, static files/css/demo.css, templates/base.html and deleted templates/inventory/household.html.
- These are Git conflicts only. Cleanly merging files may still restore obsolete routes or weaken permissions. Review all incoming files, not just conflict markers.

## 2. Published integration baseline and team handoff

Confirmed after fetch: `origin/household-member-management` at `9f9405b` contains Phase 4 and the original integration guide/skill. Use this published branch as the shared integration target. Refetch before starting and record its current SHA; accept subsequent documentation/integration commits deliberately. No separate demo-integration branch is required.

Each teammate creates a separate integration branch from that published target (e.g. integrate-thermostat, integrate-expenses, integrate-dynamic-tasks), then merges/ports their feature into it. Keep their original source branch intact. Integrate to the shared target one feature at a time. Later agents rebase their integration work onto the newly accepted target, or merge that updated target into their integration branch and rerun checks; never overwrite accepted work with their old main-based snapshot.

Suggested order: thermostat first (small incremental diff), expenses/receipt/avatars next, dynamic tasks once its branch is known. Expenses already contains thermostat in ancestry: after thermostat integration, merge its branch normally so Git recognizes shared commits. Do not independently cherry-pick the same thermostat changes twice. A combined thermostat+expenses integration is possible but has a larger review/rollback boundary.

## 3. Responsibilities and non-negotiable product contracts

| Area | Existing authority | Incoming additions |
|---|---|---|
| Identity/households | Darshan's Workspace, Membership, invitation and member services | Add fields/models deliberately; no replacement User/Household/shared-password mechanism |
| Tasks | Canonical board/detail/AI/Insights/export and selected context | Anushka adds assignment, occurrences/dates/status/reassignment at the existing domain boundary |
| Groceries | Existing integrated batches, expiry, receipt review and scoped writes | Chaitanya's remaining thermostat work and Shivani's shopping participation/receipt allocation |
| Expenses | Shared selected household + membership contract | Shivani's ledger, splits, settlements, trends and bill calendar |
| UI | Canonical shell/navigation/context + teammate design | Merge useful visual components and assets without restoring duplicate task/search/report pages |
| Ask Hestia | Required working feature with product-local handbook assets | Keep route/service/tests/lazy model loading; don't replace it with unrelated assistant behavior |

Always preserve signup/login, safe redirects, current SMTP link verification, verified invitation identity, invitation continuation/reissue/revoke, household creation, owner transfer/last-owner safeguards, soft deactivation, historical records, selected context, no-store private responses, AI approval and baseline tests. Signup OTP is a later planned phase, not part of these integrations. Do not revert settings/adapters because the incoming branch predates them.

All active members see shared household content. Household administration remains owner-only. Feature-specific mutations (e.g. receiver-only settlement confirmation) retain their actual domain rules. Personal shopping allocation visible to household members is NOT private content. Label it “For Alex”/“Alex's purchases” or explain visibility. Explicitly private notes/lists are creator-only, including against owners; do not expose them through search, exports, receipts or AI. Do not invent a private-notes subsystem just to merge this feature.

## 4. Concrete code adaptations required

### Shared household and write authorization

- Use households.context.require_household(request); explicit workspace IDs must equal selected membership.workspace_id, even for users in both households. Switch only via existing CSRF POST households:switch.
- Incoming expenses/views.py membership() checks eligible membership by URL but not selected household; expenses/households implements a second picker. Replace these semantics with shared context; preserve route names where they serve the new feature, not a duplicate picker.
- Extend households/access.py classification for the new expenses namespace and any JSON/export/provider/notification endpoints. Preserve HTML login/onboarding redirects, private-data 401/409, foreign object 404 and insufficient-role 403. Account/avatar routes need authentication but not household selection; invitation acceptance must remain publicly reachable through its controlled flow.
- Writes re-fetch active membership and active User, current role and same-household relationships inside a transaction. Use workspace-first locking with membership rows in stable PK order, consistent with households.services.locked_household. Reuse existing functions where their exceptions/contracts fit; adapt service errors at view boundaries.
- expenses.services.lock_household currently uses a Workspace no-op UPDATE and a fresh active Membership query. It lacks the foundation's explicit active-user check and membership lock convention; align deliberately instead of running two incompatible policies. Preserve payment idempotency/version checks.
- Thermostat preference/location writes in inventory/views.py currently authorize before mutation, without fresh transactional role/membership validation. Add revocation/transfer-race checks and use fresh_household immediately before external weather/provider calls. Nonowners cannot change the shared weather location; each member edits only their own temperature preference.
- Scope all new foreign keys, form querysets, receipt recipients, cached private data, reminders, bill participants and exports. Soft-deactivated members' historical debts are retained; keep them available where accounting history requires them, never as new active participants or authorized sessions.

### Models and migrations: preserve both histories

Current foundation households chain: 0001_initial → 0002_household_invitation → 0003_invitation_request_nonce. Incoming chain: 0001_initial → 0002_workspace_weather_location_thermostatpreference → 0003_useravatar. Both must survive.

- Merge Workspace.weather_location and ThermostatPreference/UserAvatar additively alongside HouseholdInvitation and all existing fields/methods. Do not replace households/models.py with either full branch copy.
- If migrations have been used on teammate databases, preserve their names/dependencies and add an explicit merge migration joining both leaf migrations. If demonstrably never applied anywhere, coordinate before any renumbering. Never delete/rewrite applied migration history or use --fake merely to get green.
- Inspect expenses migrations' households dependencies after building the combined graph. Run migration plan, drift check, fresh install AND upgrade from an existing Phase 4 database copy. Verify invitation nonces, owners, memberships and historical rows survive. Use disposable copies only.
- Incoming workflows/0002_task_household_only and TaskQuerySet.visible_to introduce a “public unless flagged” policy. Do not reintroduce it: every task is already scoped by selected household. If that migration has been applied in teammate environments, retain a safe history then add a corrective migration/remove redundant field deliberately; never silently remove applied state. This feature must not restore public task visibility.

### Receipts, purchases and accounting

There are TWO receipt outcomes: inventory quantities/expiry batches and reviewed expense allocations. Integrate their navigation and clearly explain which action creates stock, charges, or both; do not silently execute both flows on the same click or duplicate charges/batches on retry.

- Retain reviewed receipt matching and drag/drop with an equivalent keyboard/form control. AI suggestions never authorize charges. Confirmed save validates all recipients/items/draft ownership, stock/claim versions and exact totals server-side.
- Preserve integer cents, split rounding invariants, receipt subtotal + tax − discount = total, unique request tokens, no duplicated confirmed receipts and immutable/useful audit events. Preserve sender/receiver capacity checks and receiver-only payment confirmation; pending full/partial settlements do not change the confirmed balance.
- Only a fresh active owner can change original/simplified household payment mode; transfer immediately changes this capability. Calendar occurrences/reminders alone never post expenses. Repeated explicit bill recording is idempotent.
- Review membership departure against financial history: no cascaded loss of ledger, settlements or bill history. No automatic debt forgiveness or forced payment introduced by remove/leave.
- Some incoming recurring-calendar GET code calls collect_reminders. It must not create expenses/payments; assess whether reminder generation belongs in the existing scheduled command and test duplicate-delivery prevention.

### Thermostat, avatars, browser and deployment boundaries

- Place thermostat under the canonical Household page/settings with useful links. Do not restore deleted inventory/household.html as an independent household implementation. Keep each person's day/night ranges, active member aggregation, owner-set location, actual weather failures and manual application disclaimer.
- Preserve recommendation behavior for overlapping/nonoverlapping ranges; show affected members without claiming savings measurements or controlling real devices. Requests to Open-Meteo remain fixed-host, bounded/timeout-controlled and mocked in tests; assess timezone/day/night behavior with household location.
- Avatar options remain bound to request.user, validated against supported options and safely rendered. Do not allow posted user IDs to edit another avatar. Merge signup/avatar UI without rewriting the working allauth/verification adapters.
- Expenses adds notifications/service-worker/reminder paths: review authentication, selected household, storage/caching and permission lifecycles. Never cache private HTML/financial data for another session; switch/logout/removal must not retain accessible private UI data. No actual web push or real SMTP in automated tests.
- Keep core model/provider loading lazy. Preserve local handbook shipping, inference lock, research exclusion from product archives, and original A8/A9 grading artifacts. Add real runtime dependencies only with a feature justification and clean install evidence. Timer/reminder scheduling and new provider keys go into ignored user_input.md as manual steps without secrets.

## 5. Shared-file conflict rulings

| File | Required resolution |
|---|---|
| hestia_config/urls.py | Foundation account/household/task/Ask routes + new feature routes; no restored assignment API/search/chart URL groups |
| hestia_config/settings/base.py | Preserve allauth, middleware, trusted-origin/email settings; register expenses and strictly required config additively |
| households/models.py | Union of domain fields/models; preserve invitation/nonces and constraints |
| households/services.py/access.py | One role/selection/lock policy; extend capabilities without dropping lifecycle guards |
| templates/base.html | Keep visual design, add Expenses and profile controls; retain canonical Household, Ask Hestia and selected label; no old list/report navigation |
| inventory/views.py | Preserve Phase 4 shared scope, fresh/provider authorization, redirects and stock semantics; add thermostat/purchase hooks narrowly |
| templates/inventory/household.html | Keep canonical households/detail.html; port useful thermostat/avatar controls there, no competing roster |
| static files/css/demo.css | Merge components; test Tasks, Groceries, Expenses, Household and auth at desktop/390px; don't replace shared CSS wholesale |
| households/test_access.py and existing tests | Retain current security/continuation assertions; adapt fixture/routes only for intentional feature changes |
| README / docs / requirements / .gitattributes | Retain product instructions, grading separation, actual optional runtime needs and required handbook archive assets |

## 6. Execution checklist for each AI agent

- [ ] Read AGENTS.md, this guide and current access/verification contract. Record exact target + source SHAs and feature boundary.
- [ ] Fetch. Check git status and migration state. Stop destructive cleanup; preserve unrelated edits and backups.
- [ ] Make an integration branch from accepted shared target. Create a local backup reference. Inspect merge-base/diff and simulate conflicts with git merge-tree; do not assume main is current product.
- [ ] Run baseline checks/tests from the target using a separate test configuration; record existing failures/skips honestly.
- [ ] Merge source with --no-commit (or port deliberately where a documented smaller boundary makes sense). Resolve every shared-file responsibility; no blanket -X ours/theirs or whole-file replacement for core conflicts.
- [ ] Add failing integration regressions before adapting behavior: dual household selection, removed/deactivated user, role transfer between load/save, wrong FK/draft, exact totals, duplicate confirm/retry, private visibility and no unauthorized provider calls.
- [ ] Reconcile migrations/settings/templates and all call sites; inspect semantic differences in cleanly merged files. Preserve upstream domain features/tests; do not remove features to resolve conflicts quickly.
- [ ] Run checks below. Fix regressions without bypasses, skipped assertions, disabled CSRF or lower quality thresholds. Narrow PostgreSQL skips must remain visible.
- [ ] Commit only coherent verified integration. Supply handoff record. Coordinator accepts it into shared target only after review; next integrator starts from that newly accepted commit.

## 7. Required proof before acceptance

Use the existing supported Python environment and explicit disposable demo/test settings. No real .env copies or user-data migrations.

```sh
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py showmigrations --plan
python manage.py test households workflows inventory api reports analytics expenses --noinput
python manage.py test --noinput
git diff --check
```

Omit expenses from the first targeted command only before it exists; include every actual new app/test suite. Apply migrations on a fresh database and a disposable upgraded Phase 4 copy. Verify reversibility/data preservation where safe. Test product archive after committing because archive checks use HEAD, not uncommitted files. Retain query/performance budgets; measure new feature pages and avoid N+1 queries as member/ledger/list sizes grow.

Browser gate: signup → SMTP verification → household creation/invite/join → shared tasks/groceries/expenses → ownership transfer/remove/leave; selected household agrees everywhere. Confirm expense partial payment is pending until receiver accepts; receipt review produces one intended set of charges; bills calendar alone does not charge; thermostat preferences/manual recommendation work with mocked weather; avatars update only self. Keyboard and 390px layout on all changed screens; no dead links/retired routes. Real SMTP/weather/model/web-push verification only with explicit permitted test resources; report untested live dependencies.

Negative gate: another household, dual member with different selected household, inactive/null-user membership, removed user, stale tab/draft, changed owner and direct URL/POST cannot bypass policy. Owner status never grants private-note access. Existing A8/A9 branch/deployment remains unaffected.

## 8. Handoff format and coordinator gate

Supply: source SHA; target SHA; integration branch/commit; feature list; conflicts and decisions; added/merged migrations and prior-applied assumptions; exact test commands/counts/skips; browser evidence; performance data; private/config/scheduling steps; retained manual/live checks; unresolved feature/semantic decisions. Include mapping of removed/replaced tests and retained security assertions where relevant.

A clean Git merge is not acceptance. Coordinator reviews product behavior, permissions, migration upgrade, financial invariants and tests. Do not claim no conflicts means no regressions. Do not push teammates' branches or alter grading/main without user authorization.

## 9. Remaining information and decisions

- Published target confirmed: origin/household-member-management at 9f9405b in this review. Updated instructions may need a subsequent authorized push; always use the latest accepted target.
- Anushka: provide exact dynamic-task branch/commit; apply the same model/context/occurrence constraints and keep grocery-generated tasks visible on canonical board. No current branch-specific assessment is possible.
- Team: personal purchase lists are household-visible allocation lists; explicitly private lists/notes remain a separate creator-only concept. Resolve misleading copy before acceptance.
- PostgreSQL races, real provider/email/notification delivery and clean dependency install are acceptance evidence items, not assumed from source review.


## 10. No pre-created test household dependency

Teammates created households for their isolated feature checks. These are disposable development data, not required product records. The integrated app must start correctly with an empty database and let users create/join households through the implemented onboarding and verified invitations.

- Do not merge local database files, seed records, fixed household/member/user IDs, test credentials or automatic demo membership. Do not run seed_expenses_demo/seed_trends_demo as part of startup, migrations or normal onboarding. Keep any useful seed command explicitly opt-in for disposable development only.
- Replace assumptions about a particular test household with the current selected membership/context. Feature code must work for any newly created household and its invited roommates.
- Preserve automated test fixtures and factories in separate test databases. End-to-end verification may create disposable households through real product flows; no permanent seeded household is required.
- Do not indiscriminately delete existing database rows. If cleaning an existing shared/demo database, identify the exact disposable household, dependent expenses/settlements/receipts and affected accounts, back up the data and obtain authorization for the concrete destructive action. Never touch grading or real household data.

Acceptance includes: fresh disposable database → signup → verified invite/create/join → tasks/groceries/expenses/thermostat work without manually inserted household records.
