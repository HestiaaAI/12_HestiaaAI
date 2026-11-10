from django.urls import path

from .action_plan_views import action_plan_page

from .views import TaskDetailView
from .task_insights import insights
from reports.views import tasks_csv

app_name = "workflows"

urlpatterns = [
    path("export.csv", tasks_csv, name="task-export-csv"),
    path("insights/", insights, name="task-insights"),
    path("<int:pk>/action-plan/", action_plan_page, name="task-action-plan"),
    path("<int:pk>/", TaskDetailView.as_view(), name="task-detail"),
]
