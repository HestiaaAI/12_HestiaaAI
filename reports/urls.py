from django.urls import path

from . import views

app_name = "reports"
urlpatterns = [
    path("tasks/", views.task_report, name="task-report"),
    path("tasks/export.csv", views.tasks_csv, name="tasks-csv"),
    path("tasks/export.json", views.tasks_json, name="tasks-json"),
]
