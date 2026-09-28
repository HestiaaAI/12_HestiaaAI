# 12_HestiaAI

Hestia AI is a household operations app for INFO 490 Team 12. It helps households organize documents, inventory, shopping needs, and shared responsibilities.

## Setup

Run these commands from the project root. The local setup is verified with Python
3.13.7 and uses SQLite; no separate database server is required.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp -n .env.example .env
```

Put a random Django `SECRET_KEY` in `.env`. You can generate one with
`python -c 'import secrets; print(secrets.token_urlsafe(64))'`.
`OPENAI_API_KEY` can be left blank for the current app; no AI API calls are
implemented yet. Do not commit `.env`, `.venv`, or `db.sqlite3`.

```bash
python manage.py migrate
```

Optional: add fictional example tasks with `python manage.py seed_template_demo`.
For admin access, create your own login with `python manage.py createsuperuser`.
The assignment Task board does not require sign-in; seed demo data before creating tasks.

Verify the environment:

```bash
python -m pip check
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

## Development (`DEBUG = True`)

Activate `.venv` in each new terminal before running Django commands.

```bash
python manage.py runserver --settings=hestia_config.settings.development
```

Home: http://127.0.0.1:8000/
Household tasks: http://127.0.0.1:8000/tasks/cbv-generic/
Task board: http://127.0.0.1:8000/tasks/manage/
Task titles on the list use `Task.get_absolute_url()` to open `/tasks/<pk>/`.

## P1-A3 grading guide (current assignment)

Everything below runs on `main` with the development server above and the
fictional tasks from `python manage.py seed_template_demo`. Each owner's section
further down has full details.

| Section | Owner | What to open | Evidence |
|---|---|---|---|
| 1. Home, named-URL navigation, detail page, static files, cache busting | Person 1 | http://127.0.0.1:8000/ and any task title, e.g. http://127.0.0.1:8000/tasks/1/ | [home-nav-detail/](docs/screenshots/home-nav-detail/) |
| 2. GET and POST search, `workspace__name__icontains` | Person 2 | http://127.0.0.1:8000/tasks/search/ | [P1-A3 Section-2 Search-GET-POST/](docs/screenshots/P1-A3%20Section-2%20Search-GET-POST/) |
| 2. Full list, total count, `annotate()` + `Count()` summary | Person 3 | http://127.0.0.1:8000/analytics/tasks/ | [person-3/](docs/screenshots/person-3/) |
| 3. Hestia UI styling (`hestia.css`, logo, cards) | Person 4 | http://127.0.0.1:8000/tasks/manage/ (no sign-in required) | [person-4/](docs/screenshots/person-4/) |
| 4. Matplotlib chart from ORM data via `BytesIO` | Person 3 | http://127.0.0.1:8000/analytics/tasks/priority.png | [person-3/](docs/screenshots/person-3/) |
| 5. GET filter form and POST ModelForm with `{% csrf_token %}` | Person 4 | http://127.0.0.1:8000/tasks/manage/ (no sign-in required) | [person-4/](docs/screenshots/person-4/) |
| 6. `JsonResponse` API with query filters; `HttpResponse` comparison | Person 2 | http://127.0.0.1:8000/api/tasks/?q=groceries&workspace_name=demo and http://127.0.0.1:8000/api/response-demo/ | [P1-A3 Section-2 Search-GET-POST/](docs/screenshots/P1-A3%20Section-2%20Search-GET-POST/) |

All screenshots are indexed in [docs/screenshots/README.md](docs/screenshots/README.md).
Written explanations are in [docs/notes/notes.txt](docs/notes/notes.txt).

### Task board access (no sign-in required)

Run `python manage.py migrate`, `python manage.py seed_template_demo`, and
`python manage.py runserver`. Open http://127.0.0.1:8000/tasks/manage/ to
filter and create tasks directly. No account, email verification, or household
membership is required. Choose an existing demo household in the creation form.

`python -m workflows.forms_demo` remains an optional disposable preview on port
8015; its printed credentials are not needed for the task board.
Anonymous submissions have no creator membership. Signed-in submissions use an
active membership only when it belongs to the selected household.

### Final verification

On September 28, 2026, after all four members' work was merged into `main`,
`python manage.py test` ran **75 tests, all passing**. `python manage.py check`
reported no issues and `python manage.py makemigrations --check --dry-run`
reported no model changes. Earlier counts in this README and the notes (45 and 57
tests) are records from before the later merges.

### Data scope

The assignment task board allows public reads and task creation in all settings.
The search, API, analytics and list/detail teaching pages also show all tasks to
anyone. Use only fictional data. Applying household authorization consistently to those routes is
needed before Hestia holds real household data.

## Production mode (`DEBUG = False`)

```bash
python manage.py runserver 8001 --settings=hestia_config.settings.production --insecure
```

Development: http://127.0.0.1:8000/tasks/manual/

Local production-mode demonstration: http://127.0.0.1:8001/tasks/manual/

`--insecure` serves local CSS for this demonstration with `DEBUG=False`;
never use this development server as a public production deployment.
No public production website has been deployed. Both modes currently use
the same local SQLite database. Supabase staging belongs to the separate
product development branch.

Django Admin: http://127.0.0.1:8000/admin/

## Project structure

```
12_HestiaAI/
├── README.md
├── .env.example
├── manage.py
├── docs/
│   ├── wireframes/v1/
│   ├── branching_strategy/
│   └── notes/notes.txt
├── hestia_config/
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── households/
├── intake/
├── inventory/
└── workflows/
```

## Home, navigation, and task detail

The home page is `/` so the root URL is no longer a 404. Shared navigation in
`templates/base.html` uses named `{% url %}` links for Home, Household tasks,
Task board, Search tasks, and Sign in. Each task card links through `Task.get_absolute_url()`
to `/tasks/<pk>/`. Project CSS lives in `static files/` and is loaded with
`{% load static %}` plus a `?v={{ ts }}` cache-busting query string.

The Task board at `/tasks/manage/` lets visitors filter tasks
using bookmarkable GET parameters and create a Task through a CSRF-protected
ModelForm handled by one ListView. Its responsive Hestia UI uses local
`css/hestia.css` and `images/hestia-mark.svg`; validated errors retain input and
successful submissions redirect to the list to prevent accidental resubmission.

## Task search and JSON API

Task search at `/tasks/search/` has two forms. The GET form reads `q` (title)
and `workspace_name` (household) from `request.GET`, so each search has a
shareable URL. The POST form at `/tasks/search/post/` reads the same fields
from `request.POST` and includes `{% csrf_token %}`. It keeps the terms out of
the address bar, but it does not encrypt them. The household filter spans the
Task → Workspace foreign key with `workspace__name__icontains`. When both
fields are given, both must match. Results use `{% for %}` / `{% empty %}`, and
each title links to the task's detail page.

`/api/tasks/` returns tasks as JSON through `JsonResponse`, filtered by the
same query parameters, for example `/api/tasks/?q=groceries&workspace_name=demo`.
Each task includes only `id`, `title`, `task_type`, and `priority`. For
comparison, `/api/response-demo/` returns plain text through
`HttpResponse(..., content_type="text/plain")`. Both endpoints are GET-only and
public, so use them with the fictional demo data.

| Page | Named route | Open locally |
|---|---|---|
| GET search | `task_search:get` | http://127.0.0.1:8000/tasks/search/?q=groceries&workspace_name=demo |
| POST search | `task_search:post` | http://127.0.0.1:8000/tasks/search/post/ |
| JSON API | `api:task-list` | http://127.0.0.1:8000/api/tasks/?q=groceries&workspace_name=demo |
| HttpResponse text | `api:response-demo` | http://127.0.0.1:8000/api/response-demo/ |

- [Search and API details, screenshots, and header evidence](docs/person-2-handoff.md)

## P1-A2 (previous assignment): Sections 2 and 3 views and templates

This section documents the previous assignment. For the current assignment, see
[P1-A3 grading guide](#p1-a3-grading-guide-current-assignment).

The selected domain model is `Task`.
The four grading views share one list template; authentication and other
product features on the development branch are outside this grading set.

Create and activate a virtual environment before the setup commands above:

```bash
python3 -m venv .venv
source .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

For a fresh clone, copy `.env.example` to `.env` once and set `SECRET_KEY`.
Keep an existing `.env` rather than overwriting it. SQLite is local; neither
Supabase credentials nor an OpenAI API key are needed for these four pages.

```bash
python manage.py migrate
python manage.py seed_template_demo
python manage.py runserver --settings=hestia_config.settings.development
```

`seed_template_demo` creates three fictional tasks and can be rerun without
duplicating them or overwriting existing tasks. No login is needed.

| Required style | View | Named route | Open locally |
|---|---|---|---|
| HttpResponse FBV | `task_manual_view` | `workflows:task-manual` | http://127.0.0.1:8000/tasks/manual/ |
| render() FBV | `task_render_view` | `workflows:task-render` | http://127.0.0.1:8000/tasks/render/ |
| Base CBV | `TaskBaseView` | `workflows:task-cbv-base` | http://127.0.0.1:8000/tasks/cbv-base/ |
| Generic CBV | `TaskListView` | `workflows:task-cbv-generic` | http://127.0.0.1:8000/tasks/cbv-generic/ |

- [View purposes and comparison notes](docs/notes/notes.txt)
- [Four view screenshots and template empty-state evidence](docs/screenshots/README.md#p1-a2-views-and-templates-previous-assignment)
- [Shared base template](templates/base.html)
- [Reused task list template](templates/tasks/task_list.html)

To see a genuinely empty list on a fresh local database, run migrations and
open any grading route **before** running the seed command. On a populated
database, search for `XYZNOTAREALTASK123` to see the separate no-match state.
Neither demonstration requires deleting existing data.

```bash
python manage.py test
python manage.py check
```

The test suite covers the grading views, normal and empty rendering,
inheritance, search, escaping, authentication, forms, navigation and analytics. All styling is
local CSS; no additional frontend runtime or build tools are needed.

The production-mode `runserver` command above is only a configuration demo,
not a deployment procedure. Both commands serve local CSS for grading.
Submit the public GitHub repository link on Canvas after reviewing and
committing/pushing the notes and screenshot files. Uncommitted files are not
visible to the professor through GitHub.


## P1-A3 — Person 3: Task statistics and charts

The statistics page displays all Task definitions, their total count and counts
grouped by priority using Django ORM `annotate()` and `Count()`. A Matplotlib
bar chart uses those database counts and is served as an in-memory PNG through
`BytesIO` and `HttpResponse`; the page includes a caption, alt text and textual
counts. Scheduled task occurrences are not counted.

With the virtual environment activated and `.env` configured:

```bash
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_template_demo
python manage.py runserver 8021
```

The seed command is optional when fictional tasks already exist.

| Output | URL | Named route |
|---|---|---|
| Statistics, summaries and full list | http://127.0.0.1:8021/analytics/tasks/ | `analytics:task-stats` |
| PNG chart | http://127.0.0.1:8021/analytics/tasks/priority.png | `analytics:task-priority-chart` |

Use **Task statistics** in the shared navigation. Task titles link to detail
pages through `get_absolute_url()`. The page reuses `base.html` and the shared
Hestia card styles. Tasks created through the task board appear after reloading
the statistics page. These are local development URLs, not a deployed site.

Run `python manage.py test analytics` for the seven analytics tests, or
`python manage.py test` for the combined suite. The integration run on September
28, 2026 passed all 57 tests.

Screenshot evidence (captured September 28 from the local browser):

- [Statistics totals and priority summary](docs/screenshots/person-3/01-task-statistics.png)
- [Direct PNG endpoint](docs/screenshots/person-3/02-priority-chart.png)
- [Embedded chart, caption and first task](docs/screenshots/person-3/03-embedded-chart.png)
- [Remaining tasks and footer](docs/screenshots/person-3/04-task-list.png)

The page screenshots cover successive portions of the current narrow browser
viewport. They show three fictional tasks: Low=1, Medium=1, High=1, Urgent=0.

Assignment analytics and the legacy task list/detail pages display global demo
data; the task board now also allows public access for the assignment. Use fictional
data for this assignment. Apply household authorization consistently to both
analytics endpoints before using them for private household data.
