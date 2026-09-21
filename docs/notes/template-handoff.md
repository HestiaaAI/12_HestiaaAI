# Section 3 template handoff

The implementation follows the earlier "Django Section Three Implementation"
conversation and the existing Task/TaskOccurrence model separation.

## Files and responsibilities

| File | Purpose |
| --- | --- |
| `templates/base.html` | Shared HTML shell, branding, navigation, static CSS, footer, reusable blocks |
| `templates/tasks/task_list.html` | Inherits base; displays `tasks`; uses `for`, `if`, and `empty` |
| `static files/css/style.css` | Local responsive styling with no CDN requirement |
| `workflows/views.py` | Four view styles with the same template/context and title search |
| `workflows/urls.py` | Four named, namespaced assignment routes |
| `hestia_config/settings/base.py` | Template discovery and static directory configuration |

The feature template requires `tasks`, an iterable of `workflows.Task` objects.
FBVs/base CBVs pass `{"tasks": queryset}`; ListView uses
`context_object_name = "tasks"`. Pass the request when rendering so the search
field can retain its value. No model or migration changes were needed.

The base blocks `content`, `send_search`, and `filter` hold the page heading,
search form, and results respectively. Optional `stats`, `extra_css`, and
`extra_js` blocks let later pages extend the shell. Django comments are used
for template explanations because HTML comments do not stop tag execution.

## Run locally (PowerShell, project root)

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_template_demo
.\.venv\Scripts\python.exe manage.py runserver
```

For a fresh checkout, install requirements and configure `.env` as described in
README.md first. The local environment was configured during validation; no
secret is committed. The seed command adds three fictional demo tasks and is
safe to rerun: existing matching tasks are left unchanged.

## Assignment routes and evidence

All URLs below use `http://127.0.0.1:8000` locally.

| View | URL | Browser capture |
| --- | --- | --- |
| Manual HttpResponse FBV | `/tasks/manual/` | [Manual](../screenshots/00-manual.png) |
| render FBV | `/tasks/render/` | [Render](../screenshots/01-render.png) |
| Base View CBV | `/tasks/cbv-base/` | [Base CBV](../screenshots/02-base-cbv.png) |
| Generic ListView / normal state | `/tasks/cbv-generic/` | [Normal state](../screenshots/03-generic-normal.png) |
| Same generic route / empty state | `/tasks/cbv-generic/?q=XYZNOTAREALTASK123` | [Empty state](../screenshots/04-empty-state.png) |

The captures are real browser page screenshots. The normal screenshot also
serves as the generic-view screenshot. Searching is read-only and preserves
all demo records. An entirely empty database also has a dedicated message.

## Verification

```powershell
.\.venv\Scripts\python.exe manage.py test workflows
.\.venv\Scripts\python.exe manage.py check --settings=hestia_config.settings.production
```

Both passed on September 19, 2026. The three tests exercise each of the four
routes, including populated data, search, empty results, empty database,
fallback text, inheritance, and escaping. Browser inspection confirmed all
four pages render and the search form reaches the empty state.

## Team handoff and submission

Section 3 is implemented locally. Coordinate the included minimal views and
URL names with the Section 2 owner before merging. Retain the template path
and context contract above if your teammate uses different view names.

Commit the templates, CSS, integration, tests, notes, and screenshots on your
team feature branch and merge through your agreed workflow. These changes
have not been committed or pushed by this task. The final Canvas submission
is the team's public GitHub repository link. Repository visibility,
collaborator access, and the team's merge history were not verified here.

The four current list views are classroom demonstrations and query all tasks.
Before using private household data in a deployed app, implement the team's
authentication and workspace-membership rules. Production static serving also
needs deployment configuration: `collectstatic` gathers assets into
`staticfiles/`, which the production web server must serve.
