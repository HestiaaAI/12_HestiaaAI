from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET

from workflows.models import Task
from workflows.task_queries import filter_task_queryset

# Explicit allowlist: descriptions, locations, documents, and membership
# details stay out of the public response.
API_FIELDS = ("task_id", "title", "task_type", "priority")


@require_GET
def task_list_api(request):
    """Section 6: filtered task list as JSON, e.g. /api/tasks/?q=groceries&workspace_name=demo."""
    tasks = filter_task_queryset(
        Task.objects.all(),
        q=request.GET.get("q", ""),
        workspace_name=request.GET.get("workspace_name", ""),
    ).values(*API_FIELDS)
    data = [
        {"id": task["task_id"], "title": task["title"], "task_type": task["task_type"], "priority": task["priority"]}
        for task in tasks
    ]
    # JsonResponse serializes the dict and sets Content-Type: application/json.
    return JsonResponse({"tasks": data})


@require_GET
def response_demo(request):
    """Section 6 comparison: HttpResponse returns raw text with the MIME type we choose."""
    return HttpResponse("Hestia task API", content_type="text/plain")
