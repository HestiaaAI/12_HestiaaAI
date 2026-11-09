from django.urls import path

from .action_plan_views import action_plan_page

from .views import TaskDetailView, legacy_task_list
from .task_insights import insights

app_name = "workflows"

urlpatterns = [
    path("insights/", insights, name="task-insights"),
    path("<int:pk>/action-plan/", action_plan_page, name="task-action-plan"),
    path("manual/", legacy_task_list, name="task-manual"),
    path("render/", legacy_task_list, name="task-render"),
    path("cbv-base/", legacy_task_list, name="task-cbv-base"),
    path("cbv-generic/", legacy_task_list, name="task-cbv-generic"),
    path("<int:pk>/", TaskDetailView.as_view(), name="task-detail"),
]
