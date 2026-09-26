# P1-A3 — Person 4: Forms + UI

Implemented on `dev-cn32-v3`, based on fetched `origin/main` at `1938f90`
(Final Submission), September 26, 2026. The latest main includes the prior
assignment, allauth login/signup/logout, and optional shared database settings.

## Ownership and integration

Only new Person 4 files were added. `base.html`, root `urls.py`, README, team notes,
models, migrations, and teammates' existing views have not been changed.

**Person 1 must add this route to `hestia_config/urls.py`:**

```python
path("tasks/manage/", include("workflows.forms_urls")),
```

`path` and `include` are already imported there. Add the following link to your
shared navigation alongside the other assignment sections:

```django
<a class="nav-link" href="{% url 'task_forms:board' %}">Task board</a>
```

The feature template extends the existing base and loads `hestia.css` in its
`extra_css` block. No shared-base edit is needed for this page's styling.
Person 1 can use the new logo in the shared header with:

```django
<img src="{% static 'images/hestia-mark.svg' %}" alt="Hestia" width="48" height="48">
```

Keep the existing `{% load static %}` in the base. The feature has its own visible
logo and favicon already. The base's existing navigation is inherited until
Person 1 integrates the new link; the separate preview proves the route works.

## Your files

| File | Responsibility |
| --- | --- |
| `workflows/task_forms.py` | GET filter Form and Task creation ModelForm |
| `workflows/forms_views.py` | TaskBoardView: ListView GET and explicit POST |
| `workflows/forms_urls.py` | Namespaced `task_forms:board` route |
| `templates/tasks/forms/task_board.html` | GET/POST forms, CSRF, cards, empty states, messages, pagination |
| `templates/tasks/forms/field.html` | Shared labels, fields, help, and errors |
| `static files/css/hestia.css` | Scoped responsive styles |
| `static files/images/hestia-mark.svg` | Original vector home/hearth logo |
| `workflows/test_forms.py` | Eleven behavioral tests |
| `workflows/forms_preview_settings.py`, `forms_preview_urls.py` | Independent local route integration |
| `workflows/forms_demo.py` | Disposable SQLite demo with fictional tasks and a temporary login |

## Quick preview, before Person 1 merges the root route

From the repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m workflows.forms_demo
```

The repository's usual `.env` with a local SECRET_KEY is required. Open
`http://127.0.0.1:8015/tasks/manage/` and sign in with the email and random password
printed in that terminal. The demo creates a verified fictional user and active
membership; it does not email anyone. Stop with Ctrl+C. Demo records are temporary
and do not modify `db.sqlite3` or the shared staging database. Port 8015 must be free.

To preview against your existing local SQLite data instead:

```powershell
.\.venv\Scripts\python.exe manage.py migrate --settings=workflows.forms_preview_settings
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8015 --settings=workflows.forms_preview_settings
```

Use an existing verified account with an active Membership. A superuser alone
does not bypass household membership restrictions. An administrator can create
the Workspace and Membership through the existing admin. After Person 1 adds the
route, run the normal development settings and visit `/tasks/manage/`.

The preview URLconf is only a harness. Once the real root includes forms_urls,
retire the duplicate route in forms_preview_urls (or stop using the preview
URLconf in tests) to avoid registering the namespace twice.

## Section 5 behavior

- GET accepts `q`, `workspace`, `priority`, and `task_type`. The trimmed title
  search uses `icontains`; filters combine with AND. Applying filters never
  writes rows, and the URL can be bookmarked. Results paginate six at a time;
  pagination retains filter parameters. Invalid choices show errors and no rows.
- POST uses `TaskCreateForm(request.POST, user=request.user)`, validates model
  fields and the existing workspace/title uniqueness constraint, and saves one
  Task. The existing Task model has no due date or completion status; those
  belong to TaskOccurrence and are not invented by this form.
- The POST template includes `{% csrf_token %}`. Existing CsrfViewMiddleware
  enforces the token; a real-CSRF client test proves a tokenless POST returns 403.
- A successful save redirects to a GET for that household and displays a success
  message. Refresh does not repeat creation. Failed validation keeps entered data
  and displays inline/non-field errors. Duplicate submissions get form feedback.
- Login is required. Both the list and workspace selectors are restricted to the
  user's active memberships. The server assigns created_by_membership; a submitted
  creator ID is ignored. No new model migrations are required.

This is the Section 5 **creation POST**. It does not replace Person 2's separate
Section 2 POST search. POST keeps input out of URL query parameters; it does not
make data secret. The legacy assignment demonstration views remain unchanged.

## Section 3 styling and cache busting

The existing `STATICFILES_DIRS` points to `static files/`; the new CSS and SVG use
that configured folder. Templates load assets through `{% static %}`. No external
font/CDN or JavaScript dependency is needed. Hestia violet, warm clay, and ivory
are combined with a system font stack, task cards, focus outlines, accessible
labels, and a responsive layout. CSS selectors use the `hf-` prefix to avoid
changing teammates' existing components.

`hestia.css?v=20260926-1` is the asset version. Increment it when CSS changes so
browsers request a fresh URL while otherwise retaining useful caching. The base
also retains its existing timestamp version for the older stylesheet.

## Text for Person 1 to incorporate into README

The Task board at `/tasks/manage/` lets signed-in household members filter tasks
using bookmarkable GET parameters and create a Task through a CSRF-protected
ModelForm handled by one ListView. Its responsive Hestia UI uses local
`css/hestia.css` and `images/hestia-mark.svg`; validated errors retain input and
successful submissions redirect to the list to prevent accidental resubmission.

## Text for Person 1 to incorporate into team notes

Person 4 implemented TaskBoardView with a validated GET filter form and a POST
Task ModelForm. The view limits reads and creation to active memberships and
assigns the creator on the server. POST includes CSRF protection and uses
POST/Redirect/GET; errors retain user input. Shared static assets remain in the
existing project-level `static files/` directory. The version suffix on
hestia.css provides cache busting. The feature extends base.html through its
existing blocks; root URL/nav integration remains with Person 1.

## Verification and browser evidence

```powershell
.\.venv\Scripts\python.exe manage.py test --verbosity 1
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py check --settings=workflows.forms_preview_settings
```

All 45 tests passed on September 26, 2026, including 11 new tests covering GET
filtering, successful creation, invalid/duplicate creation, redirect/refresh,
CSRF rejection and acceptance, access boundaries, escaping, and pagination.
Browser testing verified a filtered result, an empty result, successful creation,
duplicate rejection with retained text, and the 375px mobile layout without
horizontal overflow.

Evidence uses fictional records in the isolated demo:

- [Styled board](../docs/screenshots/person-4/01-task-board.png)
- [GET search](../docs/screenshots/person-4/02-get-filter.png)
- [Empty results](../docs/screenshots/person-4/03-empty-state.png)
- [Created task and success message](../docs/screenshots/person-4/04-task-created.png)
- [Duplicate validation](../docs/screenshots/person-4/05-validation-error.png)
- [Mobile layout](../docs/screenshots/person-4/06-mobile.png)

Before group submission, Person 1 must integrate the route/nav and shared
documentation. Sections 1, 2, 4, and 6 remain the other owners' work. This branch's
changes still need your team's commit, push, review, and merge workflow.
