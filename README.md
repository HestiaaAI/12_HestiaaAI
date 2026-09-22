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

Household tasks: http://127.0.0.1:8000/tasks/cbv-generic/
The root URL (`/`) does not currently have a page.

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

## Sections 2 and 3: grading instructions

Use `main` for this assignment. The selected domain model is `Task`.
The four grading views share one list template; authentication and other
product features on the development branch are outside this grading set.

Create and activate a virtual environment before the setup commands above:

```bash
python3 -m venv venv
source venv/bin/activate
# Windows PowerShell: .\venv\Scripts\Activate.ps1
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
- [Four view screenshots and template empty-state evidence](docs/screenshots/README.md)
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

The main-branch suite has three test methods covering all four grading views,
normal and empty rendering, inheritance, search and escaping. All styling is
local CSS; no additional frontend runtime or build tools are needed.

The production-mode `runserver` command above is only a configuration demo,
not a deployment procedure. Both commands serve local CSS for grading.
Submit the public GitHub repository link on Canvas after reviewing and
committing/pushing the notes and screenshot files. Uncommitted files are not
visible to the professor through GitHub.
