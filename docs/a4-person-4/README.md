# A4 Person 4: static files and deployment readiness

Prepared October 3, 2026 on `dev-ddhene2-a4-static-deployment`, based on
`origin/main` at `0ff762f`, then synchronized October 4 with `d8b7ec1` (external API and Vega editor fixes included). This guide implements
Parts 4.1/4.2 and prepares the in-class Parts 4.3/4.4. It does not claim a live
deployment or completion of another member's missing feature.

## Requirement checklist

| Requirement | Implementation and evidence |
| --- | --- |
| Separate dev/prod settings and correct paths | Both use the repository-root `BASE_DIR` and SQLite; production has `DEBUG=False`. |
| Static structure | Existing project-level `static files/` holds CSS, logo, and chart JavaScript. |
| Static settings | `STATIC_URL=/static/`, `STATICFILES_DIRS=[BASE_DIR / "static files"]`, `STATIC_ROOT=BASE_DIR / "staticfiles"`. |
| Base template | `templates/base.html` loads static and uses the static tag for CSS/logo; full assignment pages extend it. Form partials and email templates are not standalone pages. |
| CSS visible on at least two pages | Reports and charts verified in both settings; four screenshots below. |
| Production collection | `collectstatic` copied 135 assets; collection remains ignored. |
| Requirements | Exact installed versions and transitive dependencies frozen; includes `requests` for Person 2 and existing SQLite-era app dependencies. |
| Ignore rules | Virtualenvs, Python caches, `.env`, generated static, logs, local database backups and SQLite sidecars ignored; `db.sqlite3` deliberately tracked. Existing local chat-history ignore preserved. |
| Database | Fresh migrated SQLite, one fictional household, three seed tasks, zero users, memberships, sessions, email addresses or documents. Integrity and foreign-key checks pass. |
| No authentication yet | No authentication added. All 20 assignment routes tested anonymously. Legacy account/admin pages remain outside A4; no instructor account is needed for A4 pages. |
| Cleanup | Assignment view imports inspected; no debug print/breakpoint calls in request handlers. Prints in the optional CLI demo are intentional. Five unused imports were removed from empty starter modules. API routes remain grouped under `/api/`. |
| Size | Local virtualenv 192 MiB, Git history 7.2 MiB, collected static 1.8 MiB, documentation about 5.5 MiB, SQLite 344 KiB; comfortably below 512 MB. Recheck Linux disk usage in class. |
| GitHub | This branch must be pushed with `db.sqlite3` and merged before the class clones `main`. |

The pre-A4 local database was backed up outside version control before creating
the submission database. Do not replace this demo database with local account
data when committing later work. Tasks are dated when the seed ran; the line
chart correctly has one point. Person 1's saved PNGs are labeled earlier snapshots.

## Local verification

Python 3.13.7; both full suites passed **91 tests**. A newly created virtualenv also installed solely from `requirements.txt`, passed `pip check`, and passed all 91 production tests. `pip check`, Django system
checks, and migration-drift checks pass. The host-configuration regression test
failed with the former localhost-only configuration and passed after the fix.

```bash
python -m pip install --no-cache-dir -r requirements.txt
python -m pip check
python manage.py check --settings=hestia_config.settings.development
python manage.py check --settings=hestia_config.settings.production
python manage.py migrate --check --settings=hestia_config.settings.production
python manage.py makemigrations --check --dry-run
python manage.py test --settings=hestia_config.settings.development
python manage.py test --settings=hestia_config.settings.production
python manage.py collectstatic --noinput --settings=hestia_config.settings.production
```

Run these servers in separate terminals:

```bash
python manage.py runserver 127.0.0.1:8040 --settings=hestia_config.settings.development
python manage.py runserver 127.0.0.1:8041 --settings=hestia_config.settings.production --insecure
```

`--insecure` is only the local DEBUG=False demonstration. PythonAnywhere serves
the collected static directory through its Web-tab mapping, not `runserver`.

Twenty routes returned HTTP 200 in each mode, including home, list/detail, board,
search, analytics, reports, both downloads, chart APIs/specs and PNG endpoints.
Every local asset referenced by these pages returned 200 and matched its source.
See [machine-readable results](verification.json). Both charts rendered in the
browser in each mode, with no captured warning/error console entries.

| Mode | Reports | Charts |
| --- | --- | --- |
| Development | [Screenshot](screenshots/development-reports.png) | [Screenshot](screenshots/development-charts.png) |
| Production settings locally | [Screenshot](screenshots/production-reports.png) | [Screenshot](screenshots/production-charts.png) |

## Parts 4.3/4.4: complete in class

Do not check these boxes based on local results. Use the actual PythonAnywhere
username/domain displayed in the team's account. Confirm a Python 3.13 runtime
is available in both the Bash console and Web tab for the pinned environment;
otherwise verify the dependency set on an available supported runtime first.

- [ ] Merge the Person 4 branch into `main` (Person 2 is already merged); confirm
  GitHub shows `db.sqlite3`. Keep the deployment on SQLite for A4.
- [ ] In a PythonAnywhere Bash console:

```bash
git clone --depth 1 https://github.com/HestiaaAI/12_HestiaaAI.git
cd 12_HestiaaAI
mkvirtualenv --python=/usr/bin/python3.13 myenv-django
python -m pip install --no-cache-dir -r requirements.txt
cp -n .env.example .env
```

- [ ] In the server's untracked `.env`, set a fresh random `SECRET_KEY` and
  `DJANGO_ALLOWED_HOSTS` to the exact site hostname (for example,
  `your-username.pythonanywhere.com`). Use the actual domain, without scheme
  or slash. No external database URI or API key is needed for the current A4 pages.
- [ ] Verify the committed database and collect server assets:

```bash
test -f db.sqlite3
python manage.py check --settings=hestia_config.settings.production
python manage.py migrate --check --settings=hestia_config.settings.production
python manage.py collectstatic --noinput --settings=hestia_config.settings.production
du -sh . "$VIRTUAL_ENV"
```

The committed database already has migrations and sample tasks. Only run
`migrate` (without `--check`) if it is missing or later model changes require it.
Do not create the PDF's optional instructor account merely to view public A4 pages.

- [ ] Create a Web app using Manual configuration and the same Python version.
  Set source/working directory to `/home/<username>/12_HestiaaAI` and virtualenv
  to `/home/<username>/.virtualenvs/myenv-django`.
- [ ] Edit the WSGI file linked in the PythonAnywhere **Web tab**, using the
  following code with the actual username:

```python
import os
import sys

project = "/home/<username>/12_HestiaaAI"
if project not in sys.path:
    sys.path.insert(0, project)
os.environ["DJANGO_SETTINGS_MODULE"] = "hestia_config.settings.production"
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

The project's settings load `.env` from its absolute project path automatically.

- [ ] Add Web-tab static mapping: URL `/static/`, directory
  `/home/<username>/12_HestiaaAI/staticfiles`; reload the app.
- [ ] Open `/static/css/style.css`, `/reports/tasks/`, `/vega-lite/`,
  `/api/charts/task-priorities/`, and `/api/charts/task-creations/` on the deployed
  HTTPS site. Download CSV/JSON and check that counts match the database.
- [ ] Download `/vega-lite/chart1.json` and `/vega-lite/chart2.json` from the
  deployed site, open both in the Vega editor, and capture working screenshots.
  Confirm each spec uses the deployed API URL and no inline data.
- [ ] Test Person 2's merged external API on the server (free-account outbound
  access may differ from local networking); record the actual route and result.
- [ ] Record the deployment URL, deployed commit, screenshots, and checklist
  results in this guide. Only then mark Parts 4.3/4.4 complete.

## Remaining team requirements

Person 2's Open Food Facts integration is now merged: `/lookup/?q=eggs`
and `/api/external/products/?q=eggs`. It performs the required keyless request,
handles failures, combines internal records, and does not store external rows.
The committed fictional database has three tasks but no product/shopping-list
rows, so the older Person 2 screenshot's Maple Street counts are illustrative
historical evidence, not expected counts for this database.

Person 1 has supplied screenshots of both charts working in the official Vega
editor locally. The updated website/specs use compatible Vega 6 / Vega-Lite 6
versions. The deployment and editor recheck against public HTTPS URLs remain.

October 3's `verification.json` is historical evidence. See `sync-verification.txt`
for the October 4 integrated branch check. The dependency merge retains our
pinned `requests==2.34.2`, verified against Person 2's tests rather than downgrading
the frozen environment to their separate `2.32.5` pin.

Official deployment references:
[PythonAnywhere existing Django projects](https://help.pythonanywhere.com/pages/DeployExistingDjangoProject/)
and [static file mapping](https://help.pythonanywhere.com/pages/DjangoStaticFiles/).
