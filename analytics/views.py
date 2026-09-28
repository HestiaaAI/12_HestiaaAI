"""Read-only assignment analytics for fictional Task data."""
from io import BytesIO
from threading import Lock

from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_safe
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

from workflows.models import Task

# Matplotlib rendering is not thread-safe. Serialize charts in each worker.
_chart_lock = Lock()


def priority_counts():
    """Aggregate in SQL, then include zero-count choices in model order."""
    grouped = Task.objects.order_by().values("priority").annotate(count=Count("pk"))
    counts = {row["priority"]: row["count"] for row in grouped}
    return [
        {"label": label, "count": counts.get(value, 0)}
        for value, label in Task.Priority.choices
    ]


@require_safe
def task_stats(request):
    """Show all task definitions and their total and priority summary."""
    return render(request, "analytics/task_stats.html", {
        "tasks": Task.objects.select_related("workspace").all(),
        "total_tasks": Task.objects.count(),
        "priority_counts": priority_counts(),
    })


@require_safe
def task_priority_chart(request):
    """Render fresh ORM counts as a PNG in memory, without pyplot or disk files."""
    rows = priority_counts()
    with _chart_lock:
        figure = Figure(figsize=(8, 4.5), dpi=120, layout="constrained")
        FigureCanvasAgg(figure)
        try:
            axes = figure.subplots()
            bars = axes.bar([row["label"] for row in rows],
                            [row["count"] for row in rows],
                            color="#5946a8", label="Task definitions")
            axes.set(title="Tasks by priority", xlabel="Priority", ylabel="Number of tasks")
            axes.yaxis.set_major_locator(MaxNLocator(integer=True))
            axes.set_ylim(0, max(1, max(row["count"] for row in rows) * 1.25))
            axes.bar_label(bars, padding=3)
            axes.legend(loc="upper right")
            if not any(row["count"] for row in rows):
                axes.text(.5, .5, "No tasks yet", transform=axes.transAxes, ha="center")
            with BytesIO() as buffer:
                figure.savefig(buffer, format="png")
                response = HttpResponse(buffer.getvalue(), content_type="image/png")
            response["Cache-Control"] = "no-store"
            return response
        finally:
            figure.clear()
