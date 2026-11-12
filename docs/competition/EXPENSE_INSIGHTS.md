# Expense activity and spending trends

Navigation: Expenses → Overview / Activity / Trends. Read-only features; no external AI, bank connections, or model calls. Household membership is checked before either view is read.

## Metrics
- Your recorded spending: your positive ExpenseShare amounts, not the full value of purchases you fronted. Removed expenses and future-dated entries are excluded. Settlement records are never spending.
- You paid upfront: full purchase totals where you were the payer in the selected month.
- Household spending: non-removed purchase totals for the selected month, counted once per expense.
- Monthly comparison: current month to date versus the same available days in the previous month; historical complete months compare full calendar months. The previous full recorded month total is shown separately. Zero comparison spending produces no fabricated percentage.
- Year chart: 12 clickable months, stacked personal-only/shared shares. Future months are not forecasts. Empty months mean no recorded spending, not verified zero real-world spending.
- Personal: you are the only positive-share participant. Shared: at least two people have a positive share. This includes small groups and whole-house expenses; it does not assume today's membership count was the membership count at purchase time.
- Category mix and changes use the existing expense category field. Category changes use the same comparison window as the headline.
- Additional KPIs: calendar-month average for the recorded year-to-date, largest month, purchase count and average share, largest purchase shares, highest recorded spending day, pending incoming/outgoing record count and value.

Use the year/month selectors or month bars to explore. The dashboard is not a budget, bank balance, or financial recommendation. No invented history or demo spending is added.

## Activity
Expense creation, edits, comments, removal and restoration are read from ExpenseEvent. Records without a creation event have a fallback based on their original created_at/created_by fields. Amounts and titles are the current expense values; historical versions were not stored and are not fabricated.

Payment records appear when recorded and again when confirmed/declined/cancelled. The recording actor is the sender; confirmation/decline is attributed to the receiver, cancellation to the sender. Payments remain household ledger records, not a claim that Hestia transferred money. Per-expense settlement is not invented.

Filters: acting roommate, event type, start/end dates. Dates use the household timezone and the feed is paginated at 25 events. Access by an account without active membership is denied. Values are rendered with normal template escaping.

## Verification
Tests cover share vs upfront totals; personal/shared classification; comparable and complete-month totals; January rollover; zero baselines; exclusion of settlements, removed and future entries; household isolation; empty states; activity actor identity and filters; invalid input. Verify with `python manage.py test expenses.test_insights`, followed by the full suite.
