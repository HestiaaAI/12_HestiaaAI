"""Public, aggregate-only Task data for the A4 Vega-Lite charts."""
from datetime import timedelta, timezone

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from analytics.views import priority_counts
from workflows.models import Task


def chart_response(rows):
    response = JsonResponse(rows, safe=False)
    # These anonymous aggregate endpoints can also be read by the Vega editor.
    response["Access-Control-Allow-Origin"] = "*"
    response["Cache-Control"] = "no-store"
    return response


@require_GET
def task_priority_summary(request):
    return chart_response(priority_counts())


@require_GET
def task_creation_summary(request):
    """Daily task definitions, including zero days between first and last creation."""
    grouped = list(Task.objects.order_by().annotate(date=TruncDate("created_at", tzinfo=timezone.utc))
                   .values("date").annotate(count=Count("pk")).order_by("date"))
    if not grouped:
        return chart_response([])
    counts = {row["date"]: row["count"] for row in grouped}
    day, last = grouped[0]["date"], grouped[-1]["date"]
    rows = []
    while day <= last:
        rows.append({"date": day.isoformat(), "count": counts.get(day, 0)})
        day += timedelta(days=1)
    return chart_response(rows)
