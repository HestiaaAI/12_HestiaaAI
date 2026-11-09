"""Task aggregates: priorities are public; daily creation data requires login."""
from django.contrib.auth.decorators import login_not_required

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from workflows.models import Task
from households.context import require_household

SAMPLE_PRIORITIES = [{"label": label, "count": count} for (_, label), count in zip(Task.Priority.choices, (2, 4, 3, 1))]


def chart_response(rows, *, public=False):
    response = JsonResponse(rows, safe=False)
    if public:
        # No credentials or task-level details are exposed to the editor.
        response["Access-Control-Allow-Origin"] = "*"
    response["Cache-Control"] = "no-store"
    return response


@login_not_required
@require_GET
def task_priority_summary(request):
    return chart_response(SAMPLE_PRIORITIES, public=True)


@require_GET
def task_creation_summary(request):
    """Daily task definitions, including zero days between first and last creation."""
    from workflows.task_insights import daily_task_counts
    tasks = Task.objects.filter(workspace=require_household(request).workspace)
    return chart_response(daily_task_counts(tasks))
