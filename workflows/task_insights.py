"""One explicit scoped summary for reports, insights and charts."""
from django.db.models import Count
from django.shortcuts import render
from django.views.decorators.http import require_GET
from households.context import require_household
from .models import Task


def grouped_summary(tasks, field, choices):
    labels = dict(choices)
    rows = tasks.order_by(field).values(field).annotate(count=Count('pk'))
    return [{'label': labels.get(row[field], row[field]), 'count': row['count']} for row in rows]


def task_summary(tasks):
    return {'total_tasks': tasks.count(),
            'priority_summary': grouped_summary(tasks, 'priority', Task.Priority.choices),
            'type_summary': grouped_summary(tasks, 'task_type', Task.TaskType.choices)}


@require_GET
def insights(request):
    return render(request, 'tasks/insights.html', task_summary(Task.objects.filter(workspace=require_household(request).workspace)))


def daily_task_counts(tasks):
    """UTC date buckets with zero days between first and last task."""
    from datetime import timedelta, timezone
    from django.db.models.functions import TruncDate
    grouped = list(tasks.order_by().annotate(date=TruncDate('created_at', tzinfo=timezone.utc))
                   .values('date').annotate(count=Count('pk')).order_by('date'))
    if not grouped:
        return []
    counts = {row['date']: row['count'] for row in grouped}
    day, last = grouped[0]['date'], grouped[-1]['date']
    rows = []
    while day <= last:
        rows.append({'date': day.isoformat(), 'count': counts.get(day, 0)})
        day += timedelta(days=1)
    return rows
