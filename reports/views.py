"""Private task export protected by the household access policy."""
import csv

from django.db.models import F
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from workflows.models import Task
from households.context import require_household

EXPORT_FIELDS = ("id", "title", "household", "task_type", "priority")


def task_records(tasks):
    """Both formats export the same explicit fields in primary-key order."""
    return tasks.order_by("pk").values(
        "title", "task_type", "priority", id=F("pk"), household=F("workspace__name")
    )


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
    for task in task_records(Task.objects.filter(workspace=require_household(request).workspace)).iterator():
        writer.writerow(csv_cell(task[field]) for field in EXPORT_FIELDS)
    return response
