import base64
import json
from urllib.parse import urlsplit
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse, HttpResponse
from django.shortcuts import render,redirect,get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST, require_safe
from django.views.decorators.cache import never_cache
from households.context import require_household, resolve_active_membership
from households.services import accept_received_invitation, received_invitations, InvitationError
from .models import PushSubscription, ReceiptDraft, Settlement
from .policies import visible_settlements
from .reminders import collect_reminders,visible_reminders

@login_required
@never_cache
@require_safe
def inbox(request):
    membership = resolve_active_membership(request)
    incoming = received_invitations(request.user).select_related("workspace").defer(
        "token_digest", "request_digest",
    )[:30]
    if membership is None:
        return render(request, "expenses/reminders.html", {"incoming": incoming})
    collect_reminders(membership.workspace)
    from django.db.models import Q

    payments = visible_settlements(actor=membership).filter(
        Q(receiver=membership, status=Settlement.Status.PENDING)
        | Q(sender=membership, status__in=(Settlement.Status.PENDING, Settlement.Status.REJECTED))
    ).select_related("circle", "sender", "receiver")[:30]
    drafts = ReceiptDraft.objects.filter(
        workspace=membership.workspace, actor=membership, confirmed_ids=[],
    ).defer("payload").order_by("-created_at")[:20]
    cutoff = timezone.now() - timezone.timedelta(hours=24)
    invitations = membership.workspace.invitations.none()
    invitation_nonce = ""
    if membership.role == "OWNER":
        from households.invitation_views import nonce_for

        invitation_nonce = nonce_for(request, membership)
        invitations = membership.workspace.invitations.filter(
            accepted_at__isnull=True, revoked_at__isnull=True,
        ).only("email", "expires_at", "accepted_at", "revoked_at")[:30]
    return render(request, "expenses/reminders.html", {
        "workspace": membership.workspace, "actor": membership, "incoming": incoming,
        "reminders": visible_reminders(request.user).filter(bill__workspace=membership.workspace),
        "payments": payments, "drafts": drafts, "cutoff": cutoff, "invitations": invitations, "invitation_nonce": invitation_nonce,
        "push_ready": bool(getattr(settings, "WEBPUSH_PUBLIC_KEY", "")),
    })


@login_required
@require_POST
def accept_inbox_invitation(request, invitation_id):
    from django.contrib import messages

    try:
        member = accept_received_invitation(user=request.user, invitation_id=invitation_id)
    except InvitationError as error:
        if error.code in {"not_found", "wrong_email", "email_unverified"}:
            raise Http404 from error
        messages.error(request, str(error))
        return redirect("expenses:reminders")
    request.session["active_workspace_id"] = member.workspace_id
    messages.success(request, f"Welcome to {member.workspace.name}.")
    return redirect("task_forms:board")


@login_required
@require_POST
def reminder_read(request,reminder_id):
    notice=get_object_or_404(visible_reminders(request.user).filter(bill__workspace=require_household(request).workspace),pk=reminder_id)
    notice.read_at=timezone.now();notice.save(update_fields=['read_at'])
    return redirect('expenses:reminders')

@login_required
@require_POST
def subscribe(request):
    if len(request.body)>5000:return JsonResponse({'error':'Subscription too large.'},status=400)
    try:
        data=json.loads(request.body);url=data['endpoint'];parts=urlsplit(url)
        hosts={'fcm.googleapis.com','updates.push.services.mozilla.com','web.push.apple.com'}
        if parts.scheme!='https' or parts.hostname not in hosts or parts.username or parts.password or parts.port not in (None,443):raise ValueError
        keys=data['keys']
        for key,size in [('auth',16),('p256dh',65)]:
            value=keys[key]
            if not isinstance(value,str) or len(base64.urlsafe_b64decode(value+'='*(-len(value)%4)))!=size:raise ValueError
        if len(url)>2000:raise ValueError
    except (ValueError,KeyError,TypeError,AttributeError):return JsonResponse({'error':'Invalid push subscription.'},status=400)
    PushSubscription.objects.update_or_create(endpoint=url,defaults={'user':request.user,'keys':{k:keys[k] for k in ('auth','p256dh')}})
    return JsonResponse({'ok':True})

@login_required
@require_POST
def unsubscribe(request):
    try:endpoint=json.loads(request.body).get('endpoint','')
    except (ValueError,AttributeError):return JsonResponse({'error':'Invalid request.'},status=400)
    PushSubscription.objects.filter(user=request.user,endpoint=endpoint).delete()
    return JsonResponse({'ok':True})

@login_required
@never_cache
def push_config(request):
    return JsonResponse({'publicKey':getattr(settings,'WEBPUSH_PUBLIC_KEY','')})


@login_required
@require_safe
@never_cache
def push_reminder_access(request, reminder_id):
    membership = require_household(request)
    get_object_or_404(
        visible_reminders(request.user).filter(bill__workspace=membership.workspace, read_at=None),
        pk=reminder_id,
    )
    return HttpResponse(status=204)


def service_worker(request):
    response=HttpResponse(render_to_string('expenses/bill-worker.js'),content_type='application/javascript')
    response['Service-Worker-Allowed']='/';response['Cache-Control']='no-cache'
    return response

def manifest(request):
    return JsonResponse({'id':'/','name':'Hestia','short_name':'Hestia','start_url':'/expenses/','display':'standalone','background_color':'#fcf7e6','theme_color':'#4f7d76','icons':[{'src':'/static/images/hestia-app-192.png','sizes':'192x192','type':'image/png'},{'src':'/static/images/hestia-app-512.png','sizes':'512x512','type':'image/png'}]})
