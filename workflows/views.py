from django.http import HttpResponse
from django.shortcuts import render
from django.template import loader
from django.views import View
from django.views.generic import ListView

from .models import Task


def filter_tasks(queryset, request):
    """Apply the same optional title search to each view's queryset."""
    query = request.GET.get("q", "").strip()
    return queryset.filter(title__icontains=query) if query else queryset


def task_manual_view(request):
    """Section 2: load and render the template manually into HttpResponse."""
    tasks = filter_tasks(Task.objects.all(), request)
    template = loader.get_template("tasks/task_list.html")
    return HttpResponse(template.render({"tasks": tasks, "view_style": "HttpResponse FBV"}, request))


def task_render_view(request):
    """Section 2: the render shortcut combines loading and responding."""
    tasks = filter_tasks(Task.objects.all(), request)
    return render(request, "tasks/task_list.html", {"tasks": tasks, "view_style": "render() FBV"})


class TaskBaseView(View):
    """Section 2: a base View with an explicit GET handler and model query."""

    def get(self, request):
        tasks = filter_tasks(Task.objects.all(), request)
        return render(request, "tasks/task_list.html", {"tasks": tasks, "view_style": "Base CBV"})


class TaskListView(ListView):
    """Section 2: Django handles the list response using the same template."""

    model = Task
    template_name = "tasks/task_list.html"
    context_object_name = "tasks"
    extra_context = {"view_style": "Generic CBV"}

    def get_queryset(self):
        return filter_tasks(super().get_queryset(), self.request)
