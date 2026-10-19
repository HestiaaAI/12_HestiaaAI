from django.urls import path
from .ai_views import brain_dump

app_name = "ai_tasks"
urlpatterns = [path("", brain_dump, name="brain-dump")]
