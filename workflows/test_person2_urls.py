"""Test-only URL configuration for Person 2's search and API routes.

Feature routes are mounted before the complete project URL configuration so
shared navigation in base.html can still reverse every existing route. Once
Person 1 mounts these includes in hestia_config/urls.py, delete this module
and the tests' ROOT_URLCONF overrides so each namespace is registered once.
"""
from django.urls import include, path

urlpatterns = [
    path("tasks/search/", include("workflows.search_urls")),
    path("api/", include("api.urls")),
    path("", include("hestia_config.urls")),
]
