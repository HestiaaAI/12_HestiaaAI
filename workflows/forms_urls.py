"""Person 1 includes these routes at tasks/manage/ in the shared root URLconf."""
from django.urls import path

from .forms_views import TaskBoardView

app_name = "task_forms"
urlpatterns = [path("", TaskBoardView.as_view(), name="board")]
