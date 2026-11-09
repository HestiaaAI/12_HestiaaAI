"""Selected-household chart rendering with explicit input rows."""
from io import BytesIO
from threading import Lock

from django.http import HttpResponse
from django.views.decorators.http import require_safe
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

from workflows.models import Task
from households.context import require_household
from workflows.task_insights import grouped_summary

# Matplotlib rendering is not thread-safe. Serialize charts in each worker.
_chart_lock = Lock()


def priority_counts(tasks):
    """Aggregate in SQL, then include zero-count choices in model order."""
    grouped = grouped_summary(tasks, 'priority', Task.Priority.choices)
    counts = {row['label']: row['count'] for row in grouped}
    return [{'label': label, 'count': counts.get(label, 0)} for _, label in Task.Priority.choices]


@require_safe
def task_priority_chart(request):
    """Render fresh ORM counts as a PNG in memory, without pyplot or disk files."""
    rows = priority_counts(Task.objects.filter(workspace=require_household(request).workspace))
    return render_priority_chart(rows)


def render_priority_chart(rows, *, title="Tasks by priority", xlabel="Priority"):
    rows = rows or [{"label": "No tasks", "count": 0}]
    with _chart_lock:
        figure = Figure(figsize=(8, 4.5), dpi=120, layout="constrained")
        FigureCanvasAgg(figure)
        try:
            axes = figure.subplots()
            bars = axes.bar([row["label"] for row in rows],
                            [row["count"] for row in rows],
                            color="#5946a8", label="Task definitions")
            axes.set(title=title, xlabel=xlabel, ylabel="Number of tasks")
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
