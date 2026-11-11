"""One selected household roster and current-owner settings."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from .context import HouseholdRequired, require_household, resolve_active_membership
from .forms import HouseholdCreateForm
from .models import Membership
from .services import HouseholdError, update_household, remove_member, leave_household, transfer_ownership


@login_required
@require_GET
def detail(request):
    member = require_household(request)
    return render(request, 'households/detail.html', {
        'workspace': member.workspace,
        'roommates': Membership.objects.filter(workspace=member.workspace, is_active=True).select_related('user'),
    })


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


def membership_action(request, operation, membership_id=None):
    actor = require_household(request)
    target = None
    if membership_id is not None:
        target = get_object_or_404(Membership, pk=membership_id, workspace_id=actor.workspace_id)
        if actor.role != Membership.MemberRole.OWNER:
            raise PermissionDenied('Only current household owners can manage members.')
    if request.POST.get('confirm') != 'yes':
        messages.error(request, 'Confirm this action using the form below. Nothing changed.')
        return redirect('households:detail')
    try:
        if operation == 'leave':
            leave_household(actor=actor)
        elif operation == 'remove':
            remove_member(actor=actor, membership_id=membership_id)
        else:
            transfer_ownership(actor=actor, membership_id=membership_id)
    except HouseholdError as exc:
        resolve_active_membership(request, refresh=True)
        if exc.code == 'not_found':
            raise Http404
        if exc.code == 'forbidden':
            if request.active_membership is None:
                raise HouseholdRequired()
            raise PermissionDenied(str(exc))
        messages.error(request, str(exc))
        return redirect('households:detail')
    if operation == 'leave':
        request.session.pop('active_workspace_id', None)
        resolve_active_membership(request, refresh=True)
        messages.success(request, 'You left the household. Your account and other household memberships remain.')
        if request.active_membership:
            return redirect('task_forms:board')
        return redirect('households:list' if request.household_memberships else 'households:onboarding')
    resolve_active_membership(request, refresh=True)
    if operation == 'remove':
        messages.success(request, f'{target.display_name} no longer has household access. Shared records remain.')
    else:
        messages.success(request, f'{target.display_name} is now an owner. You are now a roommate.')
    return redirect('households:detail')


@login_required
@require_POST
def remove(request, membership_id):
    return membership_action(request, 'remove', membership_id)


@login_required
@require_POST
def leave(request):
    return membership_action(request, 'leave')


@login_required
@require_POST
def transfer(request, membership_id):
    return membership_action(request, 'transfer', membership_id)
