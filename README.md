# 12_HestiaAI

Hestia AI is a household operations app for INFO 490 Team 12. It helps households organize documents, inventory, shopping needs, and shared responsibilities.

## Setup

```bash
python -m pip install -r requirements.txt
cp .env.example .env
```

Put a real Django `SECRET_KEY` in `.env`. Do not commit `.env`.

```bash
python manage.py migrate
```

## Development (`DEBUG = True`)

```bash
python manage.py runserver --settings=hestia_config.settings.development
```

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
