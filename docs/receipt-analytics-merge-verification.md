# Receipt and AI analytics merge verification — 2026-11-23

Target: household-member-management, initially 68b02eb. Backup reference: backup-household-before-receipt-analytics. Sources: origin/demo-receipts-recurring-tasks at 19b3953 and origin/ai-analytics-dashboard at 476d101. User authorized both local merges; no push, main merge or deployment authorized/performed.

The receipt branch merged without conflicts as 1fab43b. It adds reviewed quantity handling, browser receipt interactions, editable stock-date/storage suggestions, and a recurring-bill task relationship. Expense posting remains an explicit action; a task reminder alone does not record a charge. Stock-only and Scan & Split remain distinct workflows; this merge does not implement unified stock+expense confirmation or subgroup privacy.

The analytics branch already contains the receipt commit and dashboard implementation in its ancestry. Merging it after the receipt branch adds only docs/analytics-submission report/screenshots and PDF attributes. Dashboard source remains the accepted implementation with explicitly simulated requests/hypothetical costs. No duplicate receipt code or extra copy of dashboard routes introduced. Both original source branches retained.

Evidence:
- Prior current-target baseline: 467 tests run, 8 PostgreSQL-only skips; system and migration checks clean.
- Combined runtime after receipt merge: full discovery ran 478 tests in 36.927s, OK with 8 skips. Offline AI flags and mocked/captured providers/email; no live external calls used for proof.
- System check clean; makemigrations --check --dry-run reports no changes; staged whitespace checks clean.
- Disposable SQLite database migrated to current state, reverted expenses to 0006, created historical bill data, applied 0007, rolled back and reapplied. Existing bill value and household/membership references survived; task FK starts null. An initial historical-model fixture omitted a newer required household field; corrected the fixture and reran successfully. No application migration defect was found from that fixture error.
- Browser on isolated temporary database/server: signed-in canonical task navigation, grocery entry, stock-only receipt text review with MILK/RICE, editable storage/date estimates, and AI Analytics with simulated labels. Receipt-review and analytics document width both equaled 390 at viewport 390x844; viewport reset afterward. No reviewed stock or expenses saved through this browser check. Screenshot: /tmp/hestia-nov23-merged-analytics.png.
- Existing automated receipt, recurring bill/task, visibility and access suites ran in full discovery. New live PostgreSQL concurrency, real model/email/weather, camera OCR and notification delivery were not tested in this merge.

New required schema: expenses migration 0007_recurring_bill_task. Apply it to the product database only during a separate authorized deployment after backup. This task only applied migrations to disposable test/preview databases; original/grading/product user databases were not changed. Main remains fc037f5.

Post-commit archive/startup check results are reported in the final response. No tests were weakened or feature code changed to make this merge pass.
