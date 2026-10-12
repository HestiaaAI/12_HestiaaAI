# A5 Member 3 — public API and production Vega-Lite chart

## Submission files

- Public production API: https://hestia12.pythonanywhere.com/api/charts/task-priorities/
- Full script to submit: [group-12-vega-lite-API-demo.txt](group-12-vega-lite-API-demo.txt)
- Editor evidence: [production-vega-editor.jpg](screenshots/production-vega-editor.jpg)

Paste the entire `.txt` file into https://vega.github.io/editor/, select
Vega-Lite, and Run. It uses the actual HTTPS production API in `data.url`,
with no inline values, credentials, local files, or localhost addresses.

On October 11, 2026, this exact script rendered successfully in the hosted
editor (Vega 6.4.0, Vega-Lite 6.5.0, editor 1747515). The screenshot shows
the production URL, rendered bars, and data viewer. Production returned
Low 1, Medium 1, High 1, Urgent 0 at capture time; future counts can change.
These are task definitions, not completed tasks or individual customers.

## Public/private contract

The existing priority endpoint is the single public database-backed data API.
It groups actual `Task` records in SQL and returns only `label` and `count`,
including zero-count priorities. It exposes no task titles, notes, identifiers,
or household names. GET needs no login; writes are rejected. The response has
`Content-Type: application/json`, `Access-Control-Allow-Origin: *`, and
`Cache-Control: no-store`. Credentials are not enabled for cross-origin reads.

`api.middleware.ApiAccessMiddleware` protects every other resolved route in
the `api` namespace by default, including future additions. Anonymous requests
receive HTTP 401 with `{"error": "Authentication required."}`, rather than an
HTML login page disguised as JSON. Authenticated Django sessions can access
the existing responses. Private responses use `no-store` and `Vary: Cookie`.

| Route | Anonymous behavior after deployment |
| --- | --- |
| `/api/charts/task-priorities/` | 200, aggregate JSON |
| `/api/charts/task-creations/` | 401, JSON error |
| `/api/tasks/` | 401, JSON error |
| `/api/external/products/?q=milk` | 401 before calling the external service |
| `/api/response-demo/` | 401, JSON error |
| `/reports/tasks/export.json` and `export.csv` | 401; exports cannot bypass API protection |
| `/vega-lite/chart2.json` and `chart2.png` | 401; daily chart artifacts require login |
| `/reports/tasks/` and `/lookup/` | Redirect to login |

The chart page displays the public priority chart anonymously. Daily chart
embedding and report links appear after login. `chart1.json` is a chart
specification (not another database API); `chart1.png` remains a saved snapshot.

## Authentication integration and deployment handoff

Keep `ApiAccessMiddleware` immediately after Django's
`AuthenticationMiddleware`, before any team-wide `LoginRequiredMiddleware`.
The priority view has `@login_not_required` so it remains public when the team
enables Django's login-by-default middleware. Do not put a login decorator on
this one view. Existing login and Google OAuth work remains with its owners.

This change adds a session requirement; it does not introduce household-level
authorization. Existing signed-in queries still have their previous scope.
The authentication owner should handle private HTML pages and any membership
restrictions as part of the combined application.

**Deployment status (October 12, 2026):** The combined A5 changes are deployed
on PythonAnywhere at `00d1f4c`. Anonymous live requests to the priority API
return 200, while the daily-creation and task APIs return JSON 401. Anonymous
report exports return 401 and private HTML redirects to login. A signed-in
browser renders both the priority bar chart and daily creation line chart.
The submitted production-API Vega-Lite spec and editor screenshot remain the
chart evidence.

Run regression checks with:

All 105 tests passed on October 11, 2026, including anonymous denial, session
access and logout, public data privacy, and compatibility with Django's
login-required middleware.

```powershell
.venv/Scripts/python.exe manage.py test
```

Part 3.4's three alternative API demonstrations are assigned to another member.
They should all reuse the public production priority API above. Google OAuth,
the remaining private HTML pages, and the group video are outside this contribution.
