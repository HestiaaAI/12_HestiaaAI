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
python manage.py runserver --settings=hestia_config.settings.production
```

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
