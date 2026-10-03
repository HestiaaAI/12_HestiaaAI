"""Public A4 reports and downloads for fictional assignment Task data."""
import csv

from django.db.models import Count, F
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET

from workflows.models import Task

EXPORT_FIELDS = ("id", "title", "household", "task_type", "priority")


def task_records():
    """Both formats export the same explicit fields in primary-key order."""
    return Task.objects.order_by("pk").values(
        "title", "task_type", "priority", id=F("pk"), household=F("workspace__name")
    )


def grouped_summary(field, choices):
    labels = dict(choices)
    rows = Task.objects.order_by(field).values(field).annotate(count=Count("pk"))
    return [{"label": labels.get(row[field], row[field]), "count": row["count"]} for row in rows]


@require_GET
def task_report(request):
    return render(request, "reports/tasks.html", {
        "total_tasks": Task.objects.count(),
        "priority_summary": grouped_summary("priority", Task.Priority.choices),
        "type_summary": grouped_summary("task_type", Task.TaskType.choices),
    })


def csv_cell(value):
    # Spreadsheet applications may execute formula-looking user text.
    if isinstance(value, str) and (value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n"))):
        return "'" + value
    return value


@require_GET
def tasks_csv(request):
    stamp = timezone.now().strftime("%Y-%m-%d_%H-%M")
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="tasks_{stamp}.csv"'
    writer = csv.writer(response)
    writer.writerow(EXPORT_FIELDS)
    for task in task_records().iterator():
        writer.writerow(csv_cell(task[field]) for field in EXPORT_FIELDS)
    return response


@require_GET
def tasks_json(request):
    generated_at = timezone.now()
    tasks = [{field: task[field] for field in EXPORT_FIELDS} for task in task_records()]
    response = JsonResponse({
        "generated_at": generated_at.isoformat(),
        "record_count": len(tasks),
        "tasks": tasks,
    }, json_dumps_params={"indent": 2})
    stamp = generated_at.strftime("%Y-%m-%d_%H-%M")
    response["Content-Disposition"] = f'attachment; filename="tasks_{stamp}.json"'
    return response
