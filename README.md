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

## Local production-settings preview (`DEBUG = False`)

```bash
python manage.py runserver 127.0.0.1:8000 --settings=hestia_config.settings.production --insecure
```

`--insecure` lets Django's development server serve CSS while `DEBUG=False` for
this local assignment preview. It does not change DEBUG. Do not use this command
as a public production deployment. A deployed production server should run
`python manage.py collectstatic --noinput --settings=hestia_config.settings.production`
and serve `staticfiles/` through its configured web server.

Django Admin: http://127.0.0.1:8000/admin/

## Windows PowerShell setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Replace the placeholder SECRET_KEY in .env before continuing.
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_template_demo
.\.venv\Scripts\python.exe manage.py runserver
```

## Assignment routes and template evidence

All four routes reuse `templates/tasks/task_list.html`, which extends
`templates/base.html`. The list uses `for`, `if`, and `empty`, and renders
fields from `workflows.Task`. Supply an iterable named `tasks` from any view.

| View | Local URL | Screenshot |
| --- | --- | --- |
| HttpResponse FBV | http://127.0.0.1:8000/tasks/manual/ | [Manual](docs/screenshots/section-2/01-httpresponse.jpg) |
| render FBV | http://127.0.0.1:8000/tasks/render/ | [Render](docs/screenshots/section-2/02-render.jpg) |
| Base View CBV | http://127.0.0.1:8000/tasks/cbv-base/ | [Base CBV](docs/screenshots/section-2/03-base-cbv.jpg) |
| Generic ListView | http://127.0.0.1:8000/tasks/cbv-generic/ | [Normal list](docs/screenshots/section-2/04-generic-cbv.jpg) |

[Populated details](docs/screenshots/section-2/05-populated-details.jpg) and
[empty database](docs/screenshots/section-2/08-empty-database.jpg) provide Section 3
evidence. To reproduce an empty result without deleting tasks, search for
`XYZNOTAREALTASK123` on any of the four routes. The template's `empty` clause
handles both a no-match search and a database with no tasks.

See [team notes](docs/notes/notes.txt) for view purposes, comparisons, and evidence.
Canvas requires only the team's public GitHub repository link; ensure the final
changes are committed, pushed, and merged into the submission branch.

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
