from django.urls import path

from .views import product_compare_api, response_demo, task_list_api
from .chart_views import task_creation_summary, task_priority_summary

app_name = "api"

urlpatterns = [
    path("charts/task-priorities/", task_priority_summary, name="chart-priorities"),
    path("charts/task-creations/", task_creation_summary, name="chart-creations"),
    path("external/products/", product_compare_api, name="product-compare"),
    path("tasks/", task_list_api, name="task-list"),
    path("response-demo/", response_demo, name="response-demo"),
]
