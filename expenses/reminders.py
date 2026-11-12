"""Idempotent reminder collection; scheduled command delivers optional web push."""
import json
from datetime import timedelta
from django.conf import settings
from django.db.models import F,Q
from django.utils import timezone
from .models import RecurringBill, BillReminder, PushSubscription, BillPushDelivery, RecurringBillEntry
from .insights import household_today

def collect_reminders(workspace=None):
    bills=RecurringBill.objects.filter(active=True,reminders_enabled=True).select_related('workspace','paid_by__user').prefetch_related('participants__user')
    if workspace:bills=bills.filter(workspace=workspace)
    created=0
    for bill in bills:
        today=household_today(bill.workspace)
        if bill.next_due-timedelta(days=bill.reminder_days)>today:continue
        if RecurringBillEntry.objects.filter(bill=bill,due=bill.next_due).exists():continue
        members={p.pk:p for p in bill.participants.all()};members[bill.paid_by_id]=bill.paid_by
        for person in members.values():
            if person.is_active and person.user_id:
                _,new=BillReminder.objects.get_or_create(bill=bill,user_id=person.user_id,due=bill.next_due)
                created+=new
    return created

def visible_reminders(user):
    return BillReminder.objects.filter(user=user,bill__active=True,bill__reminders_enabled=True,bill__workspace__memberships__user=user,bill__workspace__memberships__is_active=True).filter(due=F('bill__next_due')).filter(Q(bill__paid_by__user=user,bill__paid_by__is_active=True)|Q(bill__participants__user=user,bill__participants__is_active=True)).select_related('bill__workspace').distinct().order_by('due','-created_at')

def send_pending():
    # Generic lock-screen copy intentionally contains no bill amount or household details.
    private=getattr(settings,'WEBPUSH_PRIVATE_KEY','')
    subject=getattr(settings,'WEBPUSH_SUBJECT','')
    if not private or not subject:return {'sent':0,'failed':0,'configured':False}
    from pywebpush import webpush, WebPushException
    from requests import RequestException
    sent=failed=0
    for subscription in PushSubscription.objects.select_related('user'):
        for notice in visible_reminders(subscription.user).filter(read_at=None):
            delivery,_=BillPushDelivery.objects.get_or_create(reminder=notice,subscription=subscription)
            if delivery.sent_at:continue
            try:
                webpush(subscription_info={'endpoint':subscription.endpoint,'keys':subscription.keys},data=json.dumps({'title':'Hestia · bill reminder','body':'You have an upcoming or overdue bill. Open Hestia to review it.','url':'/expenses/reminders/','tag':f'bill-{notice.pk}'}),vapid_private_key=private,vapid_claims={'sub':subject},ttl=3600,timeout=10)
            except (WebPushException, RequestException, OSError) as exc:
                failed+=1
                if getattr(exc,'response',None) is not None and exc.response.status_code in (404,410):
                    subscription.delete();break
            else:
                delivery.sent_at=timezone.now();delivery.save(update_fields=['sent_at']);sent+=1
    return {'sent':sent,'failed':failed,'configured':True}
