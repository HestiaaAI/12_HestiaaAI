from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from workflows.models import Task
from workflows.task_queries import filter_task_queryset

from .external import ExternalAPIError, compare_products

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


@require_GET
def product_compare_api(request):
    """A4: JSON comparison of ?q= against Open Food Facts and Hestia rows."""
    try:
        payload = compare_products(request.GET.get("q", ""))
    except ExternalAPIError as exc:
        return JsonResponse({"ok": False, "error": exc.message}, status=exc.status)
    return JsonResponse(payload)


@require_GET
def product_compare_page(request):
    """Same comparison as the JSON API, rendered for a browser."""
    query = request.GET.get("q", "")
    if not query.strip():
        return render(
            request,
            "lookup/products.html",
            {"q": "", "result": None, "error": None},
        )
    try:
        result = compare_products(query)
    except ExternalAPIError as exc:
        return render(
            request,
            "lookup/products.html",
            {"q": query.strip(), "result": None, "error": exc.message},
            status=exc.status,
        )
    return render(
        request,
        "lookup/products.html",
        {"q": result["query"], "result": result, "error": None},
    )
