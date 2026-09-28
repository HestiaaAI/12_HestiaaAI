from django.shortcuts import render
from django.views.decorators.http import require_GET, require_http_methods

from .models import Task
from .task_queries import filter_task_queryset


def _render_search(request, *, params, submitted, search_method):
    q = params.get("q", "").strip()
    workspace_name = params.get("workspace_name", "").strip()
    tasks = filter_task_queryset(Task.objects.all(), q=q, workspace_name=workspace_name) if submitted else Task.objects.none()
    return render(
        request,
        "tasks/search.html",
        {
            "tasks": tasks,
            "q": q,
            "workspace_name": workspace_name,
            "submitted": submitted,
            "search_method": search_method,
        },
    )


@require_GET
def task_search_get(request):
    """Section 2: read search terms from the query string (request.GET)."""
    return _render_search(request, params=request.GET, submitted=True, search_method="GET")


@require_http_methods(["GET", "POST"])
def task_search_post(request):
    """Section 2: read search terms from the form body (request.POST).

    GET shows the unsubmitted form. POST is read-only: it filters and renders
    results directly, never creating a Task or redirecting terms into the URL.
    """
    if request.method == "POST":
        return _render_search(request, params=request.POST, submitted=True, search_method="POST")
    return _render_search(request, params={}, submitted=False, search_method="POST")
