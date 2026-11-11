"""Atomic household writes with an authenticated, server-owned actor."""
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from .forms import HouseholdCreateForm
from .models import Membership, Workspace


@transaction.atomic
def create_household(*, user, name: str, timezone: str) -> Membership:
    if not getattr(user, 'is_authenticated', False) or not user.is_active:
        raise PermissionDenied('Sign in to create a household.')
    form = HouseholdCreateForm({'name': name, 'timezone': timezone})
    if not form.is_valid():
        raise ValidationError(form.errors.as_data())
    # Account activation can change after the request's authentication snapshot.
    try:
        actor = get_user_model().objects.select_for_update().get(pk=user.pk, is_active=True)
    except get_user_model().DoesNotExist:
        raise PermissionDenied('Sign in to create a household.')
    workspace = Workspace.objects.create(
        name=form.cleaned_data['name'], timezone=form.cleaned_data['timezone'],
        workspace_type=Workspace.WorkspaceType.HOUSEHOLD,
    )
    display_name = actor.get_full_name().strip() or actor.get_username().strip()
    return Membership.objects.create(
        workspace=workspace, user=actor,
        display_name=display_name[:Membership._meta.get_field('display_name').max_length],
        role=Membership.MemberRole.OWNER, is_active=True,
        can_assign_tasks=True, can_manage_sources=True, can_receive_assignments=True,
    )
