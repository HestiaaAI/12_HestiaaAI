from django.urls import path

from .views import TaskBaseView, TaskListView, task_manual_view, task_render_view

app_name = "workflows"

urlpatterns = [
    path("manual/", task_manual_view, name="task-manual"),
    path("render/", task_render_view, name="task-render"),
    path("cbv-base/", TaskBaseView.as_view(), name="task-cbv-base"),
    path("cbv-generic/", TaskListView.as_view(), name="task-cbv-generic"),
]
