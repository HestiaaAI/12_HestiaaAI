from django.urls import path

from .views import response_demo, task_list_api
from .chart_views import task_creation_summary, task_priority_summary

app_name = "api"

urlpatterns = [
    path("charts/task-priorities/", task_priority_summary, name="chart-priorities"),
    path("charts/task-creations/", task_creation_summary, name="chart-creations"),
    path("tasks/", task_list_api, name="task-list"),
    path("response-demo/", response_demo, name="response-demo"),
]
