from django.urls import path

from .action_plan_views import action_plan_page

from .views import (
    TaskBaseView,
    TaskDetailView,
    TaskListView,
    task_manual_view,
    task_render_view,
)

app_name = "workflows"

urlpatterns = [
    path("<int:pk>/action-plan/", action_plan_page, name="task-action-plan"),
    path("manual/", task_manual_view, name="task-manual"),
    path("render/", task_render_view, name="task-render"),
    path("cbv-base/", TaskBaseView.as_view(), name="task-cbv-base"),
    path("cbv-generic/", TaskListView.as_view(), name="task-cbv-generic"),
    path("<int:pk>/", TaskDetailView.as_view(), name="task-detail"),
]
