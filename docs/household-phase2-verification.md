# Phase 2 — household onboarding and creation

Implemented 2026-11-10 in `/Users/darshan/Documents/Projects/12_HestiaaAI-household-demo`, branch `household-onboarding`, based on the clean integrated `household-product-cleanup` commit `68e3ab3`. The existing six subsequent integration commits on that base were preserved. No subagents, push, PR, main merge or deployment. Original/grading checkout and database were not copied, migrated or seeded.

## Behavior and interfaces

New users continue from existing signup/login to useful onboarding and Create household. The authenticated creation form accepts trimmed name (required, max 120) and valid ZoneInfo timezone (max 50, initial America/Chicago). Duplicate names are permitted. Failed validation retains values with associated labels/help/errors. GET creates nothing and POST requires CSRF.

`create_household(*, user, name, timezone) -> Membership` validates inputs, rechecks/locks the active account inside one transaction, and creates a HOUSEHOLD Workspace plus active OWNER Membership with assign/manage-sources/receive permissions. Display name comes from trimmed full name or username, bounded to the model field length. Browser actor/type/role/permissions are ignored. A member-write failure rolls back the workspace. Deactivation between authentication and service execution cannot create records.

After the service succeeds, the view selects the new household, refreshes request-local context, shows success and redirects to the empty canonical task board. Normal POST/Redirect/GET is implemented; duplicate POST/retry idempotency is not implemented or claimed. Existing users can create additional households without losing original memberships/data. Tasks, existing groceries/roster and Insights follow selection. Switching back restores the original records.

Onboarding with one/selected membership continues to board; multiple unselected continues to the shared picker. Zero/inactive/stale memberships reach useful creation onboarding. Picker includes Create another household. Onboarding sign-out is now CSRF POST, replacing its old GET logout link. Existing Home/allauth adapters, safe next behavior, signup-disable policy, mandatory verification and OAuth linking safeguards remain unchanged.

Ask Hestia was already restored by the integrated baseline and remains intact, with product-local bundled corpus, truthful source label and lazy shared inference. Grocery functionality, teammate palette/assets, task/AI approval workflows and query budgets were preserved. No invitations, lifecycle controls, expenses, recurrence or new grocery features.

## Commits and files

- `5cb6b80 feat(households): create households with atomic owner membership` — forms, services, view/route, semantic creation template and initial 13 creation tests.
- `5ec5f54 feat(onboarding): connect account continuation and household creation` — zero/one/multiple continuation, creation links, CSRF logout and account/navigation regression coverage (23 new tests total).
- Final verification/documentation commit — current access/UI route contract, README and this report; identify hash by branch history.

No model/schema changes, migrations or new dependencies. Existing parent repository/grading files were not modified.

## Actual test results

Interpreter: `/Users/darshan/Documents/Projects/12_HestiaaAI/.venv/bin/python` (existing environment). Application commands below use `SECRET_KEY=phase2-local-only DJANGO_SETTINGS_MODULE=hestia_config.settings.development HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`. Tests create their own SQLite test database. No real `.env`/database was copied and no grading database was migrated.

| Command / stage | Result |
|---|---|
| Pre-edit `python manage.py test --noinput` | 248 passed, 13.200s |
| Initial new creation tests | RED: forms/service/route absent |
| Task 1 full `python manage.py test --noinput` | 261 passed, 13.259s |
| Initial connected-journey tests | RED: 4 failures for missing creation links and already-onboarded continuation |
| Focused `python manage.py test households.test_onboarding --noinput` | 23 passed, 3.416s |
| Task 2 full `python manage.py test --noinput` | 271 passed, 16.534s |
| Final `python manage.py check` | Clean |
| Final `python manage.py makemigrations --check --dry-run` | No changes |
| Final `python manage.py test households workflows inventory api reports analytics --noinput` | 227 passed, 18.385s |
| Final `python manage.py test --noinput` | 271 passed, 16.694s |
| `git diff --check` | Clean |

Logs: `/tmp/hestia-phase2-baseline.log`, `hestia-phase2-task1-red.log`, `hestia-phase2-task1-full.log`, `hestia-phase2-task2-red.log`, `hestia-phase2-accounts-proof.log`, `hestia-phase2-task2-full.log`, `hestia-phase2-application-final.log`, `hestia-phase2-whole-final.log`. Temporary logs are evidence from this session, not product dependencies. No tests were skipped or security assertions weakened.

The 23 new tests cover name/timezone validation/default, actor identity and permissions, inactive account, display-name fallback/truncation, duplicate names, transaction rollback, read-only GET, anonymous access, error/input retention, forged protected fields, selected session/context, CSRF rejection and valid token, failure preserving previous selection, second-household task/grocery isolation, zero/one/multiple/inactive/stale continuation, safe/external next, signup-disable, POST logout, current navigation, mandatory verification and mocked Google callback/linking.

Mandatory verification test signs up an unverified account, proves it has no authenticated session/cannot create, confirms GET does not verify, confirms via POST, signs in and creates its household. Google token/profile transport is mocked while real allauth state/callback/signup/link policy runs; a new verified Google identity reaches onboarding without auto-enrollment and a matching email cannot silently link an existing password account. The first version of that mock lacked a provider instance; the test fixture was corrected to match allauth's real provider shape, without changing production auth policy.

Existing startup/archive, shared inference-lock, grocery/task isolation, private cache/CSV, signed draft approval and write-time membership regressions all pass. Measured default query budgets remain board **5**, picker **3**, Insights **5** across 10/1,000 tasks and 1/20 memberships; no thresholds were lowered. These are query-count checks, not new page-latency or live-provider claims.

## Browser proof actually performed

A new disposable database was created under the directory recorded in `/tmp/hestia-phase2-preview-dir.txt`, with settings `/tmp/hestia_phase2_preview_settings.py`; migrations (including the existing GroceryBatch migration) were applied only there. Local server: `127.0.0.1:8026`. The browser account and both households were created through the real UI, without admin, fixture users or direct database provisioning. Development's existing verification-none signup policy was used for this browser run; mandatory verification is separately proved by automated tests, not claimed as live email/browser delivery.

Observed sequence:

1. Fresh signup → useful onboarding → Create household.
2. Submit `Cedar browser home` with `Fake/Zone`: errors shown, both values retained, associated field error visible.
3. At 390×844, replace timezone with America/Chicago and use Tab/Enter to submit; success redirects to Cedar's empty task board (0 tasks), matching household label.
4. Create `Cedar kitchen task` via board; open Groceries (initially empty), create `Cedar milk`, quantity 2 L, via existing batch form.
5. Shared picker → Create another household → `Oak browser home`; its task board and groceries are both empty, matching Oak label.
6. Switch back to Cedar; original task remains. Insights shows exactly one task. Roster shows the new account as its sole member. Ask Hestia opens with bundled example-handbook attribution; no question/inference submitted.
7. Cedar grocery list still contains 2 L milk after switching. Picker contains both households and the create-another action.

Creation error form, groceries and picker each measured document width **390** at viewport **390×844**, without horizontal overflow. Existing teammate responsive styles were reused. Viewport override was reset. Screenshots: `/tmp/hestia-phase2-create-errors-390.png`, `/tmp/hestia-phase2-groceries-390.png`, `/tmp/hestia-phase2-households-390.png`. Browser evidence is functional/keyboard/layout proof, not a full accessibility audit or latency measurement. The preview server was stopped after verification.

No live AI, model downloads, Google provider calls, SMTP delivery, receipt OCR, microphone or camera permissions were used. Preview model configuration was mock/offline; automated providers are mocked. SQLite does not prove PostgreSQL row-lock/concurrency behavior.

## Review decisions, limits and next work

Author self-review only, as the user explicitly prohibited subagents. Reviewed create service atomicity/actor freshness, browser field allowlist, rollback and session ordering, request snapshot refresh, continuation loops, account policies, template/error semantics, module isolation and preserved performance tests. No unresolved local acceptance failure remains.

Ruling: reuse Home/allauth continuation instead of introducing redirect overrides; the existing policy already correctly resolves zero/one/multiple memberships after login. Creation revalidates the active account transactionally; existing household mutations retain their membership checks. Reuse the current palette/components without redesign. Keep Ask Hestia untouched, as explicitly required. No retry-idempotency claim. Cost/limit: existing account/default verification behavior is retained; no independent review or PostgreSQL concurrency proof.

Unverified: PostgreSQL concurrency, live provider inference, real Google handshake, production email delivery, clean dependency installation and deployment. No push/main merge/deployment performed. Next phase is invitations; member lifecycle/ownership transfer, expenses, recurrence and new grocery work remain separate later phases.
