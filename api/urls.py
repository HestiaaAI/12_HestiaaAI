from django.urls import path

from .views import response_demo, task_list_api

app_name = "api"

urlpatterns = [
    path("tasks/", task_list_api, name="task-list"),
    path("response-demo/", response_demo, name="response-demo"),
]
