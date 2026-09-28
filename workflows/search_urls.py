from django.urls import path

from .search_views import task_search_get, task_search_post

app_name = "task_search"

urlpatterns = [
    path("", task_search_get, name="get"),
    path("post/", task_search_post, name="post"),
]
