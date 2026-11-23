# Hestia AI Analytics submission

Dashboard source: `ai-analytics-dashboard`. The selected 7- or 30-day window
ends November 12, 2026. A fixed random seed makes the simulated requests
reproducible. Costs use hypothetical rates of $0.15 per million input tokens and
$0.60 per million output tokens.

| Category | Question | Dashboard widget and data |
|---|---|---|
| Performance | How long does a typical request take? | Mean latency KPI, the average elapsed time across requests in the selected window. |
| Performance | Which feature has the slowest tail? | Response time chart, comparing P95 elapsed time by feature. |
| Performance | Which feature fails most often relative to its traffic? | System performance table, failed requests divided by total requests for each feature. |
| User behavior | On which day did traffic peak? | Daily requests chart, counting requests per date and labeling the peak day. |
| User behavior | Which input type accounts for the most requests? | Input-type breakdown, counts and shares for questions, grocery lists and task notes. |
| User behavior | Does the feature mix differ between the last week and month? | 7- and 30-day filters and the request-share bars, with each share recalculated for its window. |
| Cost | What is the estimated spend for the selected window? | Estimated cost KPI, summing each request's input and output token cost. |
| Cost | Which feature would cost the most per 1,000 requests? | Cost table, estimated feature spend divided by its request count and multiplied by 1,000. |
| Cost | Does a feature account for more spending than traffic? | Usage share vs. spend share chart, comparing the percentage of requests with the percentage of estimated cost. |

The screenshots show the authenticated Django dashboard rendered locally. The
required test credentials were verified against a disposable local database for
both time windows. The production route returned HTTP 404 during the final
check. The public dashboard URL is pending deployment verification.

## Production handoff

Use the existing PythonAnywhere product deployment described in
[`deployment.md`](../../deployment.md). The dashboard-only changes are commits
`c490c27` and `4c80f2a`. The analytics branch also contains receipt and
recurring-task changes, so its full branch tip is a wider release. Review and
integrate the dashboard commits against the accepted product branch using the
[team guide](../TEAM_MERGE_GUIDE.md) before publishing. These two dashboard commits
introduce no database migration. Collect the dashboard CSS and reload the web app
as part of the release.

Using the product deployment settings, provision the assignment account in the
product database with the course-specified password. Use a regular active account
without staff permissions or household memberships. Use Django's password prompt
to avoid storing the password in code or command history. If the account already
exists, verify it before changing the password. Verify an actual browser sign-in
and open both report windows after reloading.

After production login and both views are verified, paste this link into the
submission comments:

https://hestia12.pythonanywhere.com/analytics/ai/
