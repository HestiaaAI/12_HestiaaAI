from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from .context import active_memberships, resolve_active_membership
from .forms import HouseholdCreateForm
from .services import create_household


@login_required
@require_GET
def onboarding(request):
    if request.active_membership:
        return redirect('task_forms:board')
    if request.household_memberships:
        return redirect('households:list')
    return render(request, 'households/onboarding.html')


@login_required
@require_GET
def household_list(request):
    return render(request, 'households/list.html', {'memberships': request.household_memberships})


@login_required
@require_POST
def switch(request):
    choice = request.POST.get('workspace_id', '')
    membership = next((m for m in active_memberships(request.user) if str(m.workspace_id) == choice), None)
    if membership is None:
        return HttpResponseBadRequest('Choose an active household membership.')
    request.session['active_workspace_id'] = membership.workspace_id
    return redirect('task_forms:board')


@login_required
@require_http_methods(['GET', 'POST'])
def create(request):
    form = HouseholdCreateForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        membership = create_household(user=request.user, **form.cleaned_data)
        # The atomic service has committed before session selection changes.
        request.session['active_workspace_id'] = membership.workspace_id
        resolve_active_membership(request, refresh=True)
        messages.success(request, f'Household “{membership.workspace.name}” created. Add your first task to get started.')
        return redirect('task_forms:board')
    return render(request, 'households/create.html', {'form': form})
