"""Local integration harness; leaves Person 1's root URLconf untouched."""
from django.urls import include, path
from hestia_config.urls import urlpatterns as project_patterns

urlpatterns = [path("tasks/manage/", include("workflows.forms_urls")), *project_patterns]
