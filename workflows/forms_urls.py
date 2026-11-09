"""Canonical task board routes."""
from django.urls import path

from .forms_views import TaskBoardView

app_name = "task_forms"
urlpatterns = [path("", TaskBoardView.as_view(), name="board")]
