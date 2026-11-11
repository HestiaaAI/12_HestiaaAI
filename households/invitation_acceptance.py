"""No membership on GET; allauth verifies identity before explicit acceptance."""
from urllib.parse import urlencode
from smtplib import SMTPException
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponse
from django.shortcuts import render,redirect
from django.urls import reverse
from django.views.decorators.debug import sensitive_variables,sensitive_post_parameters
from django.views.decorators.http import require_http_methods
from allauth.account.models import EmailAddress
from allauth.account.internal.flows.email_verification import send_verification_email_to_address
from allauth.account.internal.flows.manage_email import sync_user_email_address

from .context import resolve_active_membership
from .invitation_continuation import INVITE_NEXT
from .services import invitation_for_token,invitation_identity,accept_invitation,InvitationError


def private_invitation_response(response):
    from django.utils.cache import add_never_cache_headers,patch_vary_headers
    add_never_cache_headers(response)
    patch_vary_headers(response,('Cookie',))
    response['Referrer-Policy']='no-referrer'
    response['X-Robots-Tag']='noindex, nofollow, noarchive'
    response['Content-Security-Policy']="default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; script-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"
    return response


@require_http_methods(['GET','POST'])
@sensitive_post_parameters()
@sensitive_variables()
def accept(request,token):
    if request.method == 'POST' and request.POST.get('action','accept') not in {'accept','verify'}:
        return private_invitation_response(HttpResponse('Choose Join household or Send verification email.',status=400))
    context={'error':None,'can_accept':False,'needs_verification':False}
    status=200
    try:
        invitation=invitation_for_token(token)
        if invitation.revoked_at:raise InvitationError('revoked')
        if not invitation.accepted_at and invitation.status == 'expired':raise InvitationError('expired')
    except InvitationError:
        context['error']='This invitation is invalid or no longer available. Ask the owner for a new link.'
        return private_invitation_response(render(request,'households/accept_invite.html',context,status=404 if request.method == 'GET' else 400))
    # Necessary temporary navigation state, never an authorization grant.
    request.session[INVITE_NEXT]=reverse('households:accept-invite',args=[token])
    path=request.session[INVITE_NEXT]
    context['login_url']=reverse('accounts:login')+'?'+urlencode({'next':path})
    context['signup_url']=reverse('accounts:signup')+'?'+urlencode({'next':path})
    context['logout_next']=context['login_url']
    if not request.user.is_authenticated:
        if request.method == 'POST':
            return private_invitation_response(redirect_to_login(path))
    else:
        try:
            invitation_identity(request.user,invitation)
            context.update(can_accept=True,invitation=invitation)
            if request.method == 'POST' and request.POST.get('action') == 'verify':
                messages.info(request,'Your email is already verified. Review this invitation and choose Join household.')
                return private_invitation_response(redirect(path))
            if request.method == 'POST':
                member=accept_invitation(user=request.user,raw_token=token)
                request.session['active_workspace_id']=member.workspace_id
                request.session.pop(INVITE_NEXT,None)
                resolve_active_membership(request,refresh=True)
                messages.success(request,f'Welcome to {member.workspace.name}. You can now share household tasks and groceries.')
                return private_invitation_response(redirect('task_forms:board'))
        except InvitationError as exc:
            context['error']=str(exc)
            context['needs_verification']=exc.code == 'email_unverified'
            if request.method == 'POST':
                status=403 if exc.code in {'wrong_email','email_unverified','authentication_required'} else 400
            if context['needs_verification'] and request.method == 'POST' and request.POST.get('action') == 'verify':
                address=EmailAddress.objects.filter(user=request.user,email__iexact=invitation.email).first()
                if address is None:
                    sync_user_email_address(request.user)
                    address=EmailAddress.objects.filter(user=request.user,email__iexact=invitation.email).first()
                if address:
                    try:
                        sent=send_verification_email_to_address(request,address)
                    except (SMTPException,OSError):
                        context['error']='Verification email could not be sent. Please try again later.'
                        status=503
                    else:
                        if sent:
                            messages.success(request,'Verification email requested. Open its link, verify, then return here to join.')
                            return private_invitation_response(redirect(path))
                        context['error']='Please wait before requesting another verification email.'
                        status=429
    return private_invitation_response(render(request,'households/accept_invite.html',context,status=status))
