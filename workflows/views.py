"""Selected-household task detail."""
from django.shortcuts import get_object_or_404, render
from django.views import View
from households.context import require_household
from .models import Task


class TaskDetailView(View):
    def get(self, request, pk):
        task = get_object_or_404(Task, workspace=require_household(request).workspace, pk=pk)
        return render(request, 'tasks/task_detail.html', {'task': task, 'can_generate_action_plan': True})
