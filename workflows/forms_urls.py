"""Canonical task board routes."""
from django.urls import path

from . import forms_views

app_name = "task_forms"
urlpatterns = [
    path("", forms_views.TaskBoardView.as_view(), name="board"),
    path("<int:task_id>/edit/", forms_views.task_edit, name="edit"),
    path("<int:task_id>/delete/", forms_views.task_delete, name="delete"),
    path(
        "occurrences/<int:occurrence_id>/start/",
        forms_views.occurrence_start,
        name="occurrence_start",
    ),
    path(
        "occurrences/<int:occurrence_id>/complete/",
        forms_views.occurrence_complete,
        name="occurrence_complete",
    ),
    path(
        "occurrences/<int:occurrence_id>/reassign/",
        forms_views.occurrence_reassign,
        name="occurrence_reassign",
    ),
]
