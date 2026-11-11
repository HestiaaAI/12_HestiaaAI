"""Atomic household writes with an authenticated, server-owned actor."""
import hashlib
import re
import secrets
from datetime import timedelta
from allauth.account.models import EmailAddress
from django.core.validators import validate_email
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from .forms import HouseholdCreateForm
from .models import HouseholdInvitation, Membership, Workspace


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


# Locks: workspace → invitation → account (acceptance) → membership.


class InvitationError(Exception):
    """Safe domain errors; messages never contain tokens or recipient details."""
    messages = {
        'invalid': 'This invitation is invalid or no longer available.',
        'request_used': 'This request was already processed. Reload before creating another invitation.',
        'forbidden': 'Only a current household owner can manage invitations.',
        'not_found': 'Invitation not found.',
        'invalid_email': 'Enter a valid email address.',
        'already_member': 'This person is already an active household member.',
        'authentication_required': 'Sign in to accept this invitation.',
        'wrong_email': 'This invitation is for a different email address. Sign in with the invited account.',
        'email_unverified': 'Verify your invited email address before joining.',
        'expired': 'This invitation has expired. Ask the owner for a new link.',
        'revoked': 'This invitation is no longer available. Ask the owner for a new link.',
        'used': 'This invitation has already been used. Ask the owner for a new invitation.',
    }
    def __init__(self, code):
        self.code = code
        super().__init__(self.messages[code])


def normalized_email(value):
    value = (value or '').strip().lower()
    try:
        validate_email(value)
        if len(value) > 254:
            raise ValidationError('Too long')
    except ValidationError:
        raise InvitationError('invalid_email')
    return value


@sensitive_variables()
def invitation_for_token(raw_token):
    if not isinstance(raw_token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43,128}', raw_token):
        raise InvitationError('invalid')
    digest = hashlib.sha256(raw_token.encode()).hexdigest()
    try:
        return HouseholdInvitation.objects.select_related('workspace').get(token_digest=digest)
    except HouseholdInvitation.DoesNotExist:
        raise InvitationError('invalid')


def invitation_identity(user, invitation):
    if not getattr(user, 'is_authenticated', False) or not user.is_active:
        raise InvitationError('authentication_required')
    addresses = EmailAddress.objects.filter(user=user, email__iexact=invitation.email)
    if addresses.filter(verified=True).exists():
        return
    if addresses.exists() or user.email.strip().lower() == invitation.email:
        raise InvitationError('email_unverified')
    raise InvitationError('wrong_email')


def locked_owner(actor):
    # Caller holds the workspace row before reaching a membership lock.
    try:
        return Membership.objects.select_for_update().get(
            pk=actor.pk, workspace_id=actor.workspace_id, user_id=actor.user_id,
            user__is_active=True, is_active=True, role=Membership.MemberRole.OWNER,
        )
    except (Membership.DoesNotExist, AttributeError):
        raise InvitationError('forbidden')


@transaction.atomic
@sensitive_variables()
def issue_invitation(*, actor, email, request_digest=None):
    workspace = Workspace.objects.select_for_update().get(pk=actor.workspace_id)
    pending = HouseholdInvitation.objects.select_for_update().filter(
        workspace=workspace, email=normalized_email(email), accepted_at__isnull=True, revoked_at__isnull=True)
    list(pending)
    used_request = HouseholdInvitation.objects.select_for_update().filter(request_digest=request_digest).exists() if request_digest else False
    owner = locked_owner(actor)
    if used_request:
        raise InvitationError("request_used")
    email = normalized_email(email)
    active = Membership.objects.filter(workspace=workspace, is_active=True).filter(
        Q(user__email__iexact=email) | Q(user__emailaddress__email__iexact=email, user__emailaddress__verified=True))
    if active.exists():
        raise InvitationError('already_member')
    now = timezone.now()
    pending.update(revoked_at=now)
    raw_token = secrets.token_urlsafe(32)
    invitation = HouseholdInvitation.objects.create(
        workspace=workspace, email=email, token_digest=hashlib.sha256(raw_token.encode()).hexdigest(),
        invited_by=owner, expires_at=now+timedelta(days=7), request_digest=request_digest)
    from .invitation_mail import schedule_invitation_email
    schedule_invitation_email(invitation, raw_token)
    return invitation, raw_token


@transaction.atomic
@sensitive_variables()
def revoke_invitation(*, actor, invitation_id):
    Workspace.objects.select_for_update().get(pk=actor.workspace_id)
    try:
        invitation = HouseholdInvitation.objects.select_for_update().get(pk=invitation_id, workspace_id=actor.workspace_id)
    except HouseholdInvitation.DoesNotExist:
        raise InvitationError('not_found')
    locked_owner(actor)
    if invitation.status == 'pending':
        invitation.revoked_at = timezone.now()
        invitation.save(update_fields=['revoked_at'])


@transaction.atomic
@sensitive_variables()
def accept_invitation(*, user, raw_token):
    candidate = invitation_for_token(raw_token)
    Workspace.objects.select_for_update().get(pk=candidate.workspace_id)
    invitation = HouseholdInvitation.objects.select_for_update().get(pk=candidate.pk)
    if not getattr(user, 'is_authenticated', False):
        raise InvitationError('authentication_required')
    try:
        user = get_user_model().objects.select_for_update().get(pk=user.pk,is_active=True)
    except get_user_model().DoesNotExist:
        raise InvitationError('authentication_required')
    invitation_identity(user, invitation)
    if invitation.revoked_at:
        raise InvitationError('revoked')
    if invitation.accepted_at:
        existing = Membership.objects.select_for_update().filter(user=user, workspace_id=invitation.workspace_id, is_active=True).first()
        if invitation.accepted_by_id == user.pk and existing:
            return existing
        raise InvitationError('used')
    if invitation.expires_at <= timezone.now():
        raise InvitationError('expired')
    member = Membership.objects.select_for_update().filter(user=user, workspace_id=invitation.workspace_id).first()
    if member is None:
        member = Membership.objects.create(workspace_id=invitation.workspace_id, user=user,
            display_name=(user.get_full_name().strip() or user.get_username().strip())[:100],
            role=Membership.MemberRole.ADULT, is_active=True, can_assign_tasks=True,
            can_manage_sources=False, can_receive_assignments=True)
    elif not member.is_active:
        member.is_active = True
        member.role = Membership.MemberRole.ADULT
        member.can_assign_tasks = True
        member.can_manage_sources = False
        member.can_receive_assignments = True
        member.save(update_fields=['is_active','role','can_assign_tasks','can_manage_sources','can_receive_assignments'])
    invitation.accepted_at = timezone.now()
    invitation.accepted_by = user
    invitation.save(update_fields=['accepted_at','accepted_by'])
    return member
