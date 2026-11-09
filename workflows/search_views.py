"""Legacy read-only search adapters to the canonical board."""
from django.views.decorators.http import require_GET, require_http_methods
from .views import legacy_task_list
from .forms_views import TaskBoardView


@require_GET
def task_search_get(request):
    return legacy_task_list(request)


@require_http_methods(['GET', 'POST'])
def task_search_post(request):
    if request.method == 'GET':
        return legacy_task_list(request)
    # Render the canonical GET handler with body filters; never invoke create.
    request.GET = request.POST.copy()
    view = TaskBoardView()
    view.setup(request)
    return view.get(request)
