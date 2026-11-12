# Competition: shared expenses and grocery receipt splits

Feature branch: `codex/cn32-shared-expenses`, based on `cn32-demo` at `c7fc59f`.

## Included

- Household-scoped USD ledger: equal, exact, percentage, shares and manual itemized splits; integer-cent reconciliation, stale-edit protection, soft delete/restore, comments and CSV/print exports.
- Overview combines owe/owed/net balances, one manual-add + control, and paginated/filterable activity. Separate Trends dashboard covers monthly and yearly spending, categories, personal/shared purchases and comparisons.
- Full/partial settlement records require actual receiver confirmation. Original vs Simplified mode is household-wide and owner-controlled. Switching is blocked while payments await confirmation, and switching back to Original is blocked if historical simplified transfers would recreate circular debts. Expense history and net balances remain unchanged.
- Grocery checklists: whole-house, personal, subgroup, sharing a product vs getting separate units. Checking an item alone never creates a charge.
- Up to five receipts, explicit payer per receipt, local OCR/text correction and optional Groq matching. Human review required. Tax/discount reconciled before atomic save; duplicates and stale lists are blocked. Unmatched products can be assigned to one, multiple or all roommates through draggable/tappable baskets. Assigned cards leave the unmatched tray and can be reopened from their baskets.
- Local vector profile avatars with visual style tiles and color choices. Optional setup after account creation; edit from the header. No selfies or external avatar service.
- Recurring bills calendar, icons, notes, payer/participants, weekly/monthly/yearly dates, edits and pause/resume. Recording the actual bill creates one expense for its due date and advances the schedule. Calendar projections/reminders do not create charges. Monthly day anchors survive shorter months.
- In-app reminders plus optional Web Push plumbing, private lock-screen copy and per-device subscriptions. See BILL_REMINDERS.md. Phone delivery requires HTTPS, deployment configuration, scheduled sending and device permission; real-device delivery has not been verified.

## Setup after checkout / deployment

1. Install `requirements.txt` in the existing environment.
2. Run `python manage.py migrate`.
3. Run `python manage.py collectstatic --noinput` with the deployment settings and reload the app.
4. Existing household memberships are used; no demo credentials or local database changes are shipped.
5. Optional Groq receipt suggestions use the existing `GROQ_API_KEY`; local matching works without it.
6. Optional push requires private server-side Web Push keys and a scheduled command; see BILL_REMINDERS.md. Do not commit `.env` or `.local-secrets/`.

## Disposable demo data

`python manage.py seed_trends_demo --username YOUR_EXISTING_USER` adds a separate A/B/C expense history household. It does not reset other households, change your password or grant staff privileges. A uses the supplied account; B/C have unusable passwords unless explicitly configured by the developer. This command is optional and must not be run against real household data without intent to add demonstration records.

`seed_expenses_demo` is a smaller legacy demo. The fake images under `test-receipts/` are clearly labelled test receipts; expected results describe their original demo participants. They are not real purchases. Local seeded A/B/C accounts and receipt drafts are not included in this branch.

## Validation and limits

The complete Django suite, receipt-total parser self-check, JavaScript syntax and migration drift checks are run before publication. Phone notification code is tested with mocked delivery; live device permission/delivery is a separate deployment check. This app records payments and never transfers real money. Original/Simplified calculations preserve household net balances; changing mode does not undo earlier confirmed payments.
