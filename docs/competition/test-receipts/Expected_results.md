# Hestia fake receipt test

This is a fictional receipt. Choose **Alex** as payer, receipt date **2026-11-11**, total **$36.30**, tax **$3.30**, discount **$0.00**.

Read the PNG or paste the accompanying TXT. The four TEST requests were added to Maple House · expenses demo. No expenses were created.

The demo has four active accounts: Alex, Jamie, shiv and Shivani. The two Shivani display names are separate accounts; the household item therefore splits four ways.

## Expected reviewed line totals (including tax)

| Item | Units | Total | Shares |
|---|---:|---:|---|
| TEST Rice | 1 | $9.90 | Alex (@hestia-demo-alex): $2.48; Jamie (@hestia-demo-jamie): $2.47; Shivani (@shiv): $2.48; Shivani (@Shivani): $2.47 |
| TEST Shampoo | 1 | $6.60 | Shivani (@Shivani): $6.60 |
| TEST Vaseline | 1 | $8.80 | Shivani (@Shivani): $4.40; Alex (@hestia-demo-alex): $4.40 |
| TEST Oat milk | 2 | $11.00 | Shivani (@Shivani): $5.50; Jamie (@hestia-demo-jamie): $5.50 |

All line shares should sum to **$36.30**. Existing household balances include earlier expenses; compare the four new expense details rather than expecting the whole ledger to equal this receipt.

No changes occur until you press **Confirm and add expenses**. After confirmation, the four TEST requests become purchased and exactly four new receipt-linked expense records should appear. Reuploading the same receipt after confirmation should be rejected as a duplicate.
