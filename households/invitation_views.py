"""Owner invitation controls and explicit, email-verified acceptance."""
import hashlib
import secrets
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.cache import cache
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.debug import sensitive_variables, sensitive_post_parameters
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from allauth.core import ratelimit

from .context import require_household
from .forms import InvitationForm
from .models import HouseholdInvitation
from .services import InvitationError, issue_invitation, revoke_invitation

NONCE_SALT = 'households.invitation-request'


def owner(request):
    member = require_household(request)
    if member.role != 'OWNER':
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied('Only household owners can manage invitations.')
    return member


def nonce_for(request, member):
    return signing.dumps({'user':request.user.pk,'workspace':member.workspace_id,'nonce':secrets.token_urlsafe(16)},salt=NONCE_SALT)


def invitation_page(request, member, *, form=None, status=200, **context):
    response = render(request,'households/invites.html',{
        'form':form or InvitationForm(initial={'nonce':nonce_for(request,member)}),
        'invitations':HouseholdInvitation.objects.filter(workspace_id=member.workspace_id),
        **context},status=status)
    response['Referrer-Policy']='no-referrer'
    return response


def consume_nonce(request, member, nonce):
    try:
        data=signing.loads(nonce,salt=NONCE_SALT,max_age=3600)
        if data['user'] != request.user.pk or data['workspace'] != member.workspace_id:
            raise signing.BadSignature()
    except (signing.BadSignature,KeyError,TypeError):
        return 400
    key='household-invite-nonce:'+hashlib.sha256(nonce.encode()).hexdigest()
    return None if cache.add(key,True,timeout=3600) else 409


@sensitive_variables()
def issue_response(request, member, *, form, email):
    replay=consume_nonce(request,member,form.cleaned_data['nonce'])
    if replay:
        return invitation_page(request,member,form=form,status=replay,error='This request is invalid or was already processed. Reload this page before issuing another link.')
    key=f'{request.user.pk}:{member.workspace_id}'
    recipient_key=f'{member.workspace_id}:'+hashlib.sha256(email.strip().lower().encode()).hexdigest()
    if not ratelimit.consume(request,action='household_invite',key=key) or not ratelimit.consume(request,action='household_invite_recipient',key=recipient_key):
        return invitation_page(request,member,form=form,status=429,error='Please wait before sending another invitation. Try again in a minute.')
    try:
        invitation,raw_token=issue_invitation(actor=member,email=email)
    except InvitationError as exc:
        status={'forbidden':403,'not_found':404}.get(exc.code,400)
        return invitation_page(request,member,form=form,status=status,error=str(exc))
    from django.conf import settings
    url=settings.ACCOUNT_PUBLIC_ORIGIN.rstrip('/')+reverse('households:accept-invite',args=[raw_token])
    return invitation_page(request,member,invite_url=url,issued_invitation=invitation)


@login_required
@require_http_methods(['GET','POST'])
@sensitive_post_parameters()
@sensitive_variables()
def invites(request):
    member=owner(request)
    if request.method == 'GET':
        return invitation_page(request,member)
    form=InvitationForm(request.POST)
    if not form.is_valid():
        return invitation_page(request,member,form=form)
    return issue_response(request,member,form=form,email=form.cleaned_data['email'])


@login_required
@require_POST
@sensitive_post_parameters()
def revoke(request, invitation_id):
    member=require_household(request)
    get_object_or_404(HouseholdInvitation,pk=invitation_id,workspace_id=member.workspace_id)
    owner(request)
    try:
        revoke_invitation(actor=member,invitation_id=invitation_id)
    except InvitationError as exc:
        from django.core.exceptions import PermissionDenied
        if exc.code == 'not_found':raise Http404
        raise PermissionDenied(str(exc))
    messages.success(request,'Invitation revoked.')
    return redirect('households:invites')


@login_required
@require_POST
@sensitive_post_parameters()
@sensitive_variables()
def resend(request, invitation_id):
    member=require_household(request)
    invitation=get_object_or_404(HouseholdInvitation,pk=invitation_id,workspace_id=member.workspace_id)
    owner(request)
    form=InvitationForm({'email':invitation.email,'nonce':request.POST.get('nonce','')})
    if not form.is_valid():
        return invitation_page(request,member,form=form,status=400)
    return issue_response(request,member,form=form,email=invitation.email)
