from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    path("tasks/", views.task_stats, name="task-stats"),
    path("tasks/priority.png", views.task_priority_chart, name="task-priority-chart"),
]
