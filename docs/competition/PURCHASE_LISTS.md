# Purchase lists and reviewed receipt splitting

## What is implemented
Expenses → Purchase lists contains household requests, personal opt-in requests, and shared groups. Every active household member can see the lists. Household requests snapshot all current active members. Personal requests initially include only their requester. New members are not silently added to existing requests.

Join choices:
- Share the same product: join the original shared-unit pool; requested quantity stays the same.
- Get my own: add 1–1000 own units, paid entirely by that member.
A member can join an item once; existing participation cannot be silently changed or duplicated. Membership identities always come from the signed-in account.

A + B group links show matching purchase requests and their confirmed receipt expenses without creating a separate household. All household data remains isolated from other households.

## Receipt workflow
1. Create requests for every product on the receipts.
2. Open Review receipts, select the payer/date, enter total, tax and discount for each of up to five receipts.
3. Read a JPEG/PNG/WebP under 10 MB using in-browser Tesseract OCR, or paste receipt text. Check OCR text before submitting. Photos are not uploaded or saved by this feature.
4. Users may explicitly choose local-only matching. AI matching is the default choice; its disclosure explains that continuing sends only extracted product names and candidate request names to Groq, using existing GROQ_API_KEY/GROQ_MODEL settings. It does not send photos, raw receipts, prices, roommate names or IDs. Sensitive information should never be placed in item names. AI suggestions are untrusted, constrained to existing candidate IDs and require review. Missing keys, rate limiting or provider errors fall back to local/manual matching.
5. Review matches, quantities and line prices. Final cost previews include proportionally allocated receipt tax/discount. Ambiguous/unmatched lines must be manually assigned to a request. Adding an unmatched request requires a fresh review.
6. Confirm explicitly. The server rechecks membership, request versions, prices, quantities, duplicate receipts and totals in one transaction. Expenses are then created and matched requests marked purchased. Refresh/retry does not duplicate expenses.

## Cost rules
All amounts are USD integer cents. Prices from each receipt's item rows plus entered tax minus entered discount must equal its final total. Enter only tax/discount not already embedded in item prices. Largest-remainder allocation preserves every cent. Taxes and discounts are allocated proportionally across lines; tax-exempt item-level accounting is not implemented.

A shared pool's units are split equally among shared claimants; own-unit claimants pay for their units. For example: one $6 unit shared by A/B → $3 each; two $6 units, one owned by A and one by B → $6 each. Across multiple receipts with different prices, all claimants use the purchase group's average unit cost, applied consistently across the ledger lines. Penny tie-breaking is stable.

The review must contain all requested units for each matched request. Partial fulfillment across separate confirmation batches, weighted loose produce, returns and substitutions are not supported; package loose produce as a requested bag/package or enter a manual expense. Create separate requests for different products/variants. Membership or request changes invalidate an old review. Reviews expire after 24 hours.

Receipt duplicate detection hashes normalized OCR/pasted text, scoped to household. It catches exact normalized repeats, not all possible photographs of the same receipt with different OCR output. Purchased-state/version checks also block stale recharging of the same request. No claim that AI detects every duplicate.

## Integration boundaries
This feature does not modify inventory batches, expiry dates, roommate onboarding, the existing grocery scanner or task management. It adds an expense-side bridge from requested items to reviewed receipt costs. Receipt-linked expenses remain editable/deletable/restorable under existing ledger permissions. Their purchased shopping state reflects physical fulfillment, not whether a later expense was voided.

## Verification
Run `python manage.py test expenses` and the full `python manage.py test` suite. Tests cover shared-vs-own units, household snapshots, parser prices, exact reconciliation, explicit confirmation/idempotency, multiple receipts, tax/discount/penny allocation, invalid/forged matches, duplicate receipts, stale participants, authorization and AI fallback/privacy. The live Groq call and photo OCR require a configured key / clear receipt and network; automated tests use mocked provider responses. Browser-tested with pasted sample receipt and confirmation in a separate staging database.

No publication or deployment is performed by installing this local feature. Never commit local database/session data or .env.

## Current location and checklist layout
The canonical UI is now Groceries → Shopping lists at `/groceries/<workspace_id>/shopping/`. The board uses three note columns: Shared list, per-roommate Personal lists, and exact-participant Shared between groups. Mobile stacks the notes. Joining moves an opt-in personal request into its participant-group note.

Groceries → Scan & split receipt uses `/groceries/<workspace_id>/receipts/`; after explicit confirmation, costs are stored in the expense ledger. The original inventory-only scanner is retained at `/groceries/<workspace_id>/scan/` and labeled Stock-only scan. These modes have different outcomes; split receipts do not silently create stock/expiry records. Existing expense-side URLs remain backward-compatible aliases, but no longer appear as expense dashboard entry points.

Checklist ticks persist an independent in-cart flag; they never create or settle expenses. Receipt-confirmed requests are checked and cannot be unchecked through the checklist. Final regression suite after relocation: 282 tests pass.

When an opt-in item includes every active household member, it is automatically displayed under Shared list instead of the smaller-group column. Existing participants and shared/own-unit quantities are preserved; this display move never changes costs or adds people silently. A smaller subset stays in Shared between. Tests cover A+B becoming A+B+C and preservation of own-unit quantities.

The payer-first receipt screen requires an explicit payer selection for each receipt, offers in-browser photo reading, and suggests detected total/tax/discount without overwriting manual edits. AI is selected by default; local-only selection is retained after validation errors. Costs are still created only by final review confirmation. Regression suite: 288 tests pass. Run `node expenses/check_receipt_totals.cjs` for summary extraction checks.
