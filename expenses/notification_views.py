import base64
import json
from urllib.parse import urlsplit
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render,redirect,get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from households.context import require_household
from .models import PushSubscription
from .reminders import collect_reminders,visible_reminders

@login_required
@never_cache
def inbox(request):
    membership = require_household(request)
    collect_reminders(membership.workspace)
    return render(request,'expenses/reminders.html',{'reminders':visible_reminders(request.user).filter(bill__workspace=require_household(request).workspace),'push_ready':bool(getattr(settings,'WEBPUSH_PUBLIC_KEY',''))})

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

def service_worker(request):
    response=HttpResponse(render_to_string('expenses/bill-worker.js'),content_type='application/javascript')
    response['Service-Worker-Allowed']='/';response['Cache-Control']='no-cache'
    return response

def manifest(request):
    return JsonResponse({'id':'/','name':'Hestia','short_name':'Hestia','start_url':'/expenses/','display':'standalone','background_color':'#fcf7e6','theme_color':'#4f7d76','icons':[{'src':'/static/images/hestia-app-192.png','sizes':'192x192','type':'image/png'},{'src':'/static/images/hestia-app-512.png','sizes':'512x512','type':'image/png'}]})
