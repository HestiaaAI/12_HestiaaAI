from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST
from .context import active_memberships


@login_required
@require_GET
def onboarding(request):
    return render(request, 'households/onboarding.html')


@login_required
@require_GET
def household_list(request):
    return render(request, 'households/list.html', {'memberships': active_memberships(request.user)})


@login_required
@require_POST
def switch(request):
    choice = request.POST.get('workspace_id', '')
    membership = next((m for m in active_memberships(request.user) if str(m.workspace_id) == choice), None)
    if membership is None:
        return HttpResponseBadRequest('Choose an active household membership.')
    request.session['active_workspace_id'] = membership.workspace_id
    return redirect('task_forms:board')
