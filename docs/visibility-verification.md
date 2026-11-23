# Visibility foundation verification

Implemented on `visibility-foundation` from the demo integration baseline
`3f726f8`, which contains published `origin/household-member-management`
`68b02eb`. The commits add no runtime dependency.

## Product checks

- Four separate Chrome sessions exercised creation of a selected-roommate
  shopping list, adding a grocery item by keyboard, receipt review and posting,
  partial settlement, and receiver confirmation. The excluded household owner
  could not open the list or its ledger and saw neither the shopping item in
  Today nor the settlement in the inbox. A receipt reader could see the approved
  expense line but could not open the original review. Shopping, Today, and the
  inbox fit a 390-pixel viewport without horizontal scrolling.
- Automated coverage checks excluded-owner responses across ledger routes,
  reports and CSV. It also covers removal, dual-member household switching,
  old audience forms, restricted receipt routing, repeated confirmation,
  separate household and subgroup balances, and private-payer validation.
- Inbox coverage checks that unverified accounts cannot see incoming invitations,
  viewing never joins the household, CSRF is required, and a verified invitation
  is accepted only once. The reminder check returns no content and denies a
  different account, a switched household, and a signed-out session.
- Today coverage verifies the household-local date boundary, deduplicates tasks
  generated for due bills, and checks that opening Today posts no expense.
- Settlement query count stays constant between 10 and 1,000 ledger entries.
  Matching tests verify that mutable named-list candidates stay out of external
  matching requests.

## Migration and release

- The fresh SQLite install and the archived product both migrated successfully.
  The historical upgrade test preserves IDs, shares, settlements, receipt links,
  recurring bills, invitations, and historical membership references. It tests
  safe reversal and reapplication and rejects rollback after a restricted circle
  is created. The required-link migration runs the backfill again before adding
  non-null constraints, covering records created while the additive schema was
  in use.
- Final `python manage.py test --noinput` run passed with 491 tests discovered,
  483 passed, and 8 PostgreSQL-only skips. The focused reminders and visibility
  run passed all 20 tests.
- Django system and migration drift checks passed. Product archive coverage
  confirms the runtime starts with its bundled handbook and excludes the
  historical database and research artifacts.
- Verification used disposable SQLite databases, a local mail backend and test
  fixtures. PostgreSQL concurrency tests require a PostgreSQL environment. Live
  SMTP, live push delivery, and actual money movement were outside this run.

Recurring bills remain household-visible. The inbox is ready for authorized
chore-swap actions when that workflow exists. See the
[access contract](household-access-contract.md#sharing-circles-today-and-the-action-inbox)
for source and route boundaries and the [merge guide](TEAM_MERGE_GUIDE.md#11-visibility-foundation-integration)
for backup and rollback instructions.
