# Person 2 Handoff: Search and API

Person 2 delivers Section 2 GET/POST search and the Section 6 JSON API. The new routes live in their own modules and are mounted in the project URL config.

## Integration (done)

Person 2 made the shared-file changes on branch `dev-ddhene2-search-integration`:

- `hestia_config/urls.py` mounts both includes above the `tasks/manage/` and `tasks/` includes, so no `tasks/` route can catch `/tasks/search/` first:

  ```python
  path("api/", include("api.urls")),
  path("tasks/search/", include("workflows.search_urls")),
  ```

- `templates/base.html` has a "Search tasks" nav link: `{% url 'task_search:get' %}`.
- The test-only URL config (`workflows/test_person2_urls.py`) and the tests' `ROOT_URLCONF` overrides were removed. `ProjectUrlIntegrationTests` in `workflows/test_search.py` checks the real routes, the nav link, and that a result's detail link returns 200.
- The README and `docs/notes/notes.txt` include the Search and API text below.

`api` is a plain Python package, not an installed app, so `INSTALLED_APPS` stays the same. There are no migrations or new dependencies.

## Routes

| URL | Name | Behavior |
| --- | --- | --- |
| `/tasks/search/` | `task_search:get` | GET only. Reads `q` and `workspace_name` from `request.GET` and shows results. |
| `/tasks/search/post/` | `task_search:post` | A GET shows the empty form. A POST reads `q` and `workspace_name` from `request.POST` and shows results without redirecting or creating records. Requires a CSRF token. |
| `/api/tasks/` | `api:task-list` | GET only. JSON list with optional `q` and `workspace_name` query parameters. |
| `/api/response-demo/` | `api:response-demo` | GET only. `HttpResponse("Hestia task API", content_type="text/plain")`. |

Unsupported methods return 405. A browser POST to the API that has no CSRF token gets 403 instead, because Django's CSRF middleware rejects it before the view runs. The API is read-only either way. Blank or whitespace-only filters are ignored, and unknown parameters are ignored. Results are ordered by task primary key. `workspace_name` is a name substring. It is separate from the task board's `workspace` parameter, which holds a Workspace primary key.

Each search result title links to `task.get_absolute_url` (`workflows:task-detail`, `/tasks/<pk>/`). That route is Person 1's and is already on `main`.

## Example requests

```text
GET  /tasks/search/?q=groceries&workspace_name=demo
POST /tasks/search/post/            body: q=groceries&workspace_name=demo (+ csrfmiddlewaretoken)
GET  /api/tasks/?q=groceries&workspace_name=demo
GET  /api/response-demo/
```

## API schema

```json
{"tasks": [{"id": 1, "title": "Buy groceries", "task_type": "SHOPPING", "priority": "HIGH"}]}
```

`id` is the Task primary key (`task_id`). `task_type` and `priority` are the raw choice values. A search with no matches returns `{"tasks": []}`. The response includes only these four fields. Descriptions, locations, documents, and membership details are never sent.

The API is public, like the existing anonymous task-list teaching pages. Use it only with synthetic demo data. Access rules for real household records are a separate decision outside this assignment.

## Copy-ready README / notes text

**Section 2: Search.** Hestia's task search at `/tasks/search/` has two forms. The GET form reads `q` (title) and `workspace_name` (household) from `request.GET`, so every search has a shareable, bookmarkable URL. The POST form at `/tasks/search/post/` reads the same fields from `request.POST` and is protected with `{% csrf_token %}`. Its search terms stay out of the address bar, but POST does not encrypt data or control access. The household filter spans the Task → Workspace foreign key with the relationship lookup `workspace__name__icontains`, and the title filter uses `title__icontains`. When both are given, both must match. The results template loops with `{% for task in tasks %}` and shows a clear message through `{% empty %}` when nothing matches.

**Section 6: API.** `/api/tasks/` returns household tasks as JSON through `JsonResponse`, which serializes a Python dict and sets `Content-Type: application/json`. Clients filter with the same query parameters as the search page, for example `/api/tasks/?q=groceries&workspace_name=demo`. Each task includes only `id`, `title`, `task_type`, and `priority`. For comparison, `/api/response-demo/` returns plain text through `HttpResponse(..., content_type="text/plain")`. `HttpResponse` sends whatever bytes and MIME type you give it, while `JsonResponse` does the JSON encoding and header for you.

## Tests

```bash
.venv/bin/python manage.py test workflows.test_search workflows.test_api --settings=hestia_config.settings.development
```

These tests cover title, related-name, and combined filtering, POST reading the body instead of the query string, blank and empty states, HTML escaping, CSRF enforcement, method restrictions, the exact JSON field allowlist, and both MIME types.

## Evidence

Captured in a Chrome window from the integrated local dev server at `http://127.0.0.1:8000` (`hestia_config.settings.development`) with the fictional demo tasks. Each screenshot shows the page's URL in Chrome's address bar. Files are in `docs/screenshots/P1-A3 Section-2 Search-GET-POST/`:

| File | Shows |
| --- | --- |
| [01-get-search.png](screenshots/P1-A3%20Section-2%20Search-GET-POST/01-get-search.png) | GET search `?q=groceries&workspace_name=DEMO`: the mixed-case household name matches through `workspace__name__icontains`. |
| [02-post-form-unsubmitted.png](screenshots/P1-A3%20Section-2%20Search-GET-POST/02-post-form-unsubmitted.png) | The POST form before submission, with its prompt. |
| [03-post-search-results.png](screenshots/P1-A3%20Section-2%20Search-GET-POST/03-post-search-results.png) | POST search `air` + `demo`. The address bar shows `/tasks/search/post/` with no search terms. |
| [04-no-match.png](screenshots/P1-A3%20Section-2%20Search-GET-POST/04-no-match.png) | The `{% empty %}` state for an unmatched search. |
| [05-api-json-filtered.png](screenshots/P1-A3%20Section-2%20Search-GET-POST/05-api-json-filtered.png) | `/api/tasks/?q=groceries&workspace_name=demo` JSON. |
| [06-httpresponse-text.png](screenshots/P1-A3%20Section-2%20Search-GET-POST/06-httpresponse-text.png) | `/api/response-demo/` plain text. |
| [07-api-response-headers.txt](screenshots/P1-A3%20Section-2%20Search-GET-POST/07-api-response-headers.txt) | `curl -i` output: `Content-Type: application/json` vs `text/plain`, and 403 for a POST without a CSRF token. |
