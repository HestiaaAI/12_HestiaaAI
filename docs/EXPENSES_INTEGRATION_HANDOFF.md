# Expenses integration — local verification

Target: origin/household-member-management, 9f9405be98044e50376369c698ced0a502a7c7c2.
Incoming: 3890ded225b1da84626dee6d3a1ec69b4b4c550b (includes thermostat ancestry).
Branch: integrate-expenses. Main, source branch, local source database and secrets remain untouched.

Baseline verification: 367 tests pass; 8 PostgreSQL-only skips.

Integration decisions:
- Preserve foundation verification, invitation continuation, role/lifecycle and selected-household policy.
- Expenses redirects through canonical selected household; explicit IDs cannot bypass selection.
- Ledger writes reuse workspace-first foundation locks and active-account authorization.
- Preserve both households migration histories, join them in 0005; preserve incoming workflow migration and remove its redundant visibility field in 0003. Task visibility remains selected-household-only.
- Canonical Household page links thermostat; no duplicate grocery roster.
- Avatar setup remains optional, preserving invitation/signup redirects. Existing avatar test redirects intentionally updated; deactivated users without another home receive canonical onboarding redirect rather than old 404, with balance-history assertion retained.
- Avatar retrieval joins existing membership query, preserving foundation page query budgets.
- Inventory receipt capture and expense receipt allocation remain distinct reviewed operations.
- No database, credentials, automatic seed data or provider configuration included.

Verification so far:
- `manage.py check`: no issues.
- `manage.py makemigrations --check --dry-run`: no changes.
- `manage.py showmigrations --plan`: combined graph resolves.
- `manage.py test --noinput`: 461 tests passed, 8 PostgreSQL-only skips, 27.788 seconds (before final onboarding regression); all ten integration regressions pass separately.
- Focused suite (expenses + avatar + thermostat + original page budgets): 95 tests passed before the final two race regressions; all ten integration-specific regressions pass.
- Fresh test database installation succeeds. Disposable Phase 4 schema upgrade preserves existing household, owner and invitation request nonce. Both applied histories retained without fake migrations.
- Browser: login → canonical Tasks → Expenses, recurring calendar, Groceries → shopping notes, and canonical Household with invite/settings/thermostat links. At 390px, calendar and shopping notes document widths equal viewport (390px), no horizontal overflow. Browser uses only disposable local DB; no existing test household/config copied.
- Original query-budget assertions remain unchanged and pass (Tasks5, household selector3, Insights5 queries at 1/20 memberships and 10/1000 tasks). Avatar joined to existing selection query rather than adding header lookup.
- `git diff --check`: clean.

Remaining acceptance evidence (not claimed complete): full manual verification/invite/join/transfer/remove journey with authorized SMTP resources, real PostgreSQL concurrency, live weather/AI/Web Push delivery, clean dependency install, exhaustive keyboard/mobile interaction and migration rollback. Providers are mocked in automated tests. Integration has not been deployed or merged to shared target.

Conflicts: settings preserved invitation privacy/rate limits plus expenses/Web Push config; URLs union canonical product routes plus expenses (no retired reports/charts restored); models union invitation/thermostat/avatar/payment-mode; baseline auth tests retained; inventory context kept; CSS components combined; shell kept canonical nav plus Expenses/profile; competing household template deleted with thermostat link ported.

Migrations: households0002/0003 invitation history and weather/avatar/payment-mode history joined in0005_merge_integration. workflows0002_task_household_only retained for applied history and corrected by0003_remove_task_household_only. No visibility bypass added. Existing installations that already contain either history must use normal migrate after backup.

Private setup/scheduling steps are in ignored user_input.md. No source database, .env, private key, real account or automatic demo enrollment included. Local logo changes have been copied as assets and narrowly applied in shell, preserving source edits.


Independent review found two stale-access gaps (comment insertion and provider-bound receipt matching). Both were reproduced, fixed, and covered by regression tests. Fresh signup/onboarding creation test confirms all six feature routes work with a newly created household and no seeds. Target refetched before commit and remains 9f9405b.
