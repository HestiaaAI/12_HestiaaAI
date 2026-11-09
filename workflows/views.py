"""Canonical detail and compatibility redirects for old task list URLs."""
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import View
from django.views.decorators.http import require_GET
from households.context import require_household
from .models import Task
from .task_forms import TaskFilterForm


@require_GET
def legacy_task_list(request):
    membership = require_household(request)
    params = request.GET.copy()
    for key in list(params):
        if key not in {'q', 'priority', 'task_type', 'page', 'workspace'}:
            params.pop(key)
    form = TaskFilterForm(params, membership=membership)
    if not form.is_valid():
        params = request.GET.copy()
        for key in list(params):
            if key not in {'q', 'priority', 'task_type', 'page'}:
                params.pop(key)
        # Preserve invalid supported filters so the board renders errors/zero
        # results; never widen a forged workspace filter to real tasks.
        if request.GET.get('workspace'):
            params['workspace'] = request.GET['workspace']
    else:
        params.pop('workspace', None)
    query = params.urlencode()
    return redirect(reverse('task_forms:board') + ('?' + query if query else ''))


class TaskDetailView(View):
    def get(self, request, pk):
        task = get_object_or_404(Task, workspace=require_household(request).workspace, pk=pk)
        return render(request, 'tasks/task_detail.html', {'task': task, 'can_generate_action_plan': True})
