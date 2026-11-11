"""One selected household roster and current-owner settings."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods
from .context import require_household
from .forms import HouseholdCreateForm
from .models import Membership
from .services import HouseholdError, update_household


def detail_response(request, *, status=200, error=None):
    member = require_household(request)
    return render(request, 'households/detail.html', {
        'workspace': member.workspace,
        'roommates': Membership.objects.filter(workspace=member.workspace, is_active=True),
        'error': error,
    }, status=status)


@login_required
@require_GET
def detail(request):
    return detail_response(request)


@login_required
@require_http_methods(['GET', 'POST'])
def settings(request):
    actor = require_household(request)
    if actor.role != Membership.MemberRole.OWNER:
        raise PermissionDenied('Only current household owners can edit settings.')
    form = HouseholdCreateForm(request.POST if request.method == 'POST' else None,
                               initial={'name': actor.workspace.name, 'timezone': actor.workspace.timezone})
    if request.method == 'POST' and form.is_valid():
        try:
            update_household(actor=actor, **form.cleaned_data)
        except HouseholdError as exc:
            raise PermissionDenied(str(exc))
        messages.success(request, 'Household settings updated.')
        return redirect('households:detail')
    return render(request, 'households/settings.html', {'form': form})
