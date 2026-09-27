"""Preview harness now reuses the shared root URLconf (includes /tasks/manage/)."""
from hestia_config.urls import urlpatterns as project_patterns

urlpatterns = list(project_patterns)
