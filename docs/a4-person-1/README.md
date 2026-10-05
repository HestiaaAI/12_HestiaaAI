# A4 Person 1: Internal API and Vega-Lite

Built on `origin/main` at `66867de`, including Person 3's merged PR #13.
No new authentication, models, migrations, or Python dependencies are added.

## Run and review

```powershell
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe manage.py migrate
.venv/Scripts/python.exe manage.py runserver 8000
```

If the database has no tasks, the existing `seed_template_demo` command adds
three fictional task definitions without overwriting existing records.

| Deliverable | Route |
| --- | --- |
| Both embedded charts | `/vega-lite/` (Charts in the shared navigation) |
| Priority summary JSON | `/api/charts/task-priorities/` |
| Daily task creation JSON | `/api/charts/task-creations/` |
| Bar specification | `/vega-lite/chart1.json` |
| Line specification | `/vega-lite/chart2.json` |
| Saved bar PNG | `/vega-lite/chart1.png` |
| Saved line PNG | `/vega-lite/chart2.png` |

All routes are public and GET-only. The APIs return plain arrays from the Task
model, with numeric counts. They expose only aggregates, not names, descriptions,
locations, or account information. Their scope is all households, matching the
existing assignment reports. The priority API includes zero-count priorities.
Daily creation uses UTC and fills missing dates between the first and last task.
These counts describe task definitions, not scheduled occurrences or completions.

## Submission artifacts

- [Bar Vega-Lite JSON](specs/task-priorities.vl.json)
- [Line Vega-Lite JSON](specs/task-creations.vl.json)
- [Working embedded charts screenshot](screenshots/charts-page.jpg)
- [Bar chart working in the official Vega-Lite editor](screenshots/editor-bar.jpg)
- [Line chart working in the official Vega-Lite editor](screenshots/editor-line.jpg)
- [Bar PNG output](outputs/task-priorities.png)
- [Line PNG output](outputs/task-creations.png)

Both specifications use `data.url`; neither includes inline task data. The
checked-in specs target `127.0.0.1:8000`. The JSON routes substitute the current
request origin, so downloading them after deployment gives the deployed API URL.
The page uses pinned Vega 6.4.0, Vega-Lite 6.4.3 and Vega-Embed 7.1.0 from
jsDelivr; internet access is required for these scripts. Source JSON and saved
PNG links remain available when JavaScript fails.

The PNG endpoints serve saved Vega exports, including with DEBUG=False. They
are explicitly labeled snapshots, not live images. To refresh them, open the
chart menu, choose Save as PNG and replace the corresponding file in `outputs/`.
The embedded charts always load current API data when the page opens.

The original PNG snapshots use three demo tasks created on September 19, 2026.
The editor screenshots were captured on October 3, 2026 with four actual Task
records: three created September 19 and one created October 3. The editor bar
counts are Low 1, Medium 2, High 1, Urgent 0. The line shows 3 and 1 on those
dates, with zero-count dates between them. No timestamps were altered.

## Vega editor and deployment handoff

Open https://vega.github.io/editor/ and paste either saved specification, or use
Open in Vega Editor in the embedded chart menu. Run the spec with the Django
server running. The API permits cross-origin reads for the editor. A browser may
still restrict an HTTPS editor's access to localhost; after deployment, download
the spec from the deployed JSON route and use its public HTTPS API URL.

Both specifications were loaded and run successfully in the **official Vega
editor running locally**, with `data.url` fetching the live Django API on port
8000. No inline data or substitute data files were used. See the two editor
screenshots above. The local editor is the upstream `vega/editor` application,
not a custom chart preview. Its source revision is
`84a605ccc791fd73644ab86b7e25547af044accb`; Vega 6.4.0 and Vega-Lite 6.4.3.
The website and specs now use matching major versions, avoiding the old v5/v6
warning and displaying integer count-axis ticks correctly.

The hosted HTTPS editor did not render localhost data in the available browser.
Running the official editor locally resolved this without changing browser
security settings or exposing the development server publicly. The repeatable
Windows setup is in [local-editor.md](local-editor.md).

**Still pending for class:** deploy Hestia, download the specs from the deployed
`/vega-lite/chart1.json` and `/vega-lite/chart2.json` routes, and repeat the editor
check using the public HTTPS API URLs. Local editor verification does not claim
that deployment or the deployed-URL check is complete.

Person 4 still needs to remove `db.sqlite3` from `.gitignore`, prepare the team's
assignment database, and commit/push it before deployment. Parts 4.3/4.4 stay in
class. Person 3's reports and download routes are unchanged.

## Validation

```powershell
.venv/Scripts/python.exe manage.py test
.venv/Scripts/python.exe manage.py makemigrations --check --dry-run
git diff --check
```

89 tests pass, including six new tests for database counts and updates, UTC daily
grouping, missing days, empty data, public embedding/spec routes, PNG responses
with DEBUG=False, unknown chart IDs and rejected writes. No pending migrations.

References: [Vega-Lite URL data](https://vega.github.io/vega-lite/docs/data.html)
and [Vega-Embed](https://github.com/vega/vega-embed).
