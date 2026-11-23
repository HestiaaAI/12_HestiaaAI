from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from households.models import Workspace, Membership
from expenses.models import RecurringBill, Expense

class RecurringTests(TestCase):
    def setUp(self):
        self.home=Workspace.objects.create(name='Home')
        self.a=Membership.objects.create(workspace=self.home,user=get_user_model().objects.create_user(username='a'),display_name='A')
        self.b=Membership.objects.create(workspace=self.home,user=get_user_model().objects.create_user(username='b'),display_name='B')
        self.client.force_login(self.a.user)
        self.url=reverse('expenses:recurring',args=[self.home.pk])
    def test_create_and_record_once(self):
        data={'title':'Rent','amount':'1800.00','paid_by':self.a.pk,'participants':[self.a.pk,self.b.pk],'next_due':'2026-11-30','frequency':'monthly','category':'bills'}
        self.assertEqual(self.client.post(self.url,data).status_code,302)
        bill=RecurringBill.objects.get()
        self.assertIsNotNone(bill.task_id)
        self.assertEqual(str(bill.task.occurrences.get().due_at.date()),'2026-11-30')
        self.assertEqual(Expense.objects.count(),0)
        url=reverse('expenses:recurring-action',args=[self.home.pk,bill.pk])
        payload={'action':'record','due':'2026-11-30','amount':'1810.00'}
        self.assertEqual(self.client.post(url,payload).status_code,302)
        self.client.post(url,payload)
        self.assertEqual(Expense.objects.count(),1)
        self.assertEqual(Expense.objects.get().amount_cents,181000)
        bill.refresh_from_db();self.assertEqual(str(bill.next_due),'2026-12-30')
        occurrences=list(bill.task.occurrences.order_by('sequence'))
        self.assertEqual(len(occurrences),2)
        self.assertEqual(occurrences[0].state,'REPORTED_COMPLETE')
        self.assertEqual(str(occurrences[1].due_at.date()),'2026-12-30')
    def test_household_isolation(self):
        other=Membership.objects.create(workspace=Workspace.objects.create(name='Other'),user=get_user_model().objects.create_user(username='out'),display_name='Out')
        self.assertEqual(self.client.post(self.url,{'paid_by':other.pk}).status_code,200)
        self.assertFalse(RecurringBill.objects.exists())
        self.client.force_login(other.user)
        self.assertEqual(self.client.get(self.url).status_code,404)

    def test_calendar_and_reminders_are_scoped(self):
        from expenses.models import BillReminder
        from expenses.reminders import collect_reminders
        from django.utils import timezone
        bill=RecurringBill.objects.create(workspace=self.home,created_by=self.a,paid_by=self.a,title='Electricity',amount_cents=10000,next_due=timezone.localdate(),icon='electricity',reminder_days=3)
        bill.participants.set([self.a,self.b])
        collect_reminders();collect_reminders()
        self.assertEqual(BillReminder.objects.count(),2)
        response=self.client.get(self.url)
        self.assertContains(response,'bill-calendar')
        self.assertContains(response,'⚡')
        self.assertContains(self.client.get(reverse('expenses:reminders')),'Electricity')

    def test_reminder_read_cannot_touch_other_user(self):
        from expenses.models import BillReminder
        from django.utils import timezone
        bill=RecurringBill.objects.create(workspace=self.home,created_by=self.a,paid_by=self.a,title='Water',amount_cents=4000,next_due=timezone.localdate())
        notice=BillReminder.objects.create(bill=bill,user=self.b.user,due=bill.next_due)
        self.assertEqual(self.client.post(reverse('expenses:reminder-read',args=[notice.pk])).status_code,404)

    def test_subscription_rejects_arbitrary_server_urls(self):
        import json
        response=self.client.post(reverse('expenses:push-subscribe'),data=json.dumps({'endpoint':'https://127.0.0.1/private','keys':{'auth':'x','p256dh':'y'}}),content_type='application/json')
        self.assertEqual(response.status_code,400)

    def test_month_end_and_projected_dates(self):
        from datetime import date
        from expenses.bill_calendar import advance,month_calendar
        self.assertEqual(advance(date(2026,1,31),'monthly',31),date(2026,2,28))
        self.assertEqual(advance(date(2026,2,28),'monthly',31),date(2026,3,31))
        bill=RecurringBill.objects.create(workspace=self.home,created_by=self.a,paid_by=self.a,title='Netflix',amount_cents=1599,next_due=date(2026,11,30),anchor_day=30,icon='streaming')
        cal=month_calendar([bill],2026,12,date(2026,11,11))
        events=[event for week in cal['weeks'] for day in week for event in day['events']]
        self.assertEqual(events[0]['due'],date(2026,12,30))
        self.assertEqual(Expense.objects.count(),0)

    def test_editing_and_pause_are_restricted(self):
        bill=RecurringBill.objects.create(workspace=self.home,created_by=self.a,paid_by=self.a,title='Rent',amount_cents=10000,next_due='2026-12-01')
        self.client.force_login(self.b.user)
        self.assertEqual(self.client.get(self.url+'?edit='+str(bill.pk)).status_code,403)
        self.assertEqual(self.client.post(reverse('expenses:recurring-action',args=[self.home.pk,bill.pk]),{'action':'pause'}).status_code,403)

    def test_push_delivery_is_generic_and_not_sent_twice(self):
        from unittest.mock import patch
        from django.test import override_settings
        from django.utils import timezone
        from expenses.models import BillReminder,PushSubscription,BillPushDelivery
        from expenses.reminders import send_pending
        bill=RecurringBill.objects.create(workspace=self.home,created_by=self.a,paid_by=self.a,title='Private rent',amount_cents=12345,next_due=timezone.localdate())
        notice=BillReminder.objects.create(bill=bill,user=self.a.user,due=bill.next_due)
        PushSubscription.objects.create(user=self.a.user,endpoint='https://fcm.googleapis.com/fcm/send/example',keys={'auth':'example','p256dh':'example'})
        with override_settings(WEBPUSH_PRIVATE_KEY='dummy',WEBPUSH_SUBJECT='mailto:test@example.test'),patch('pywebpush.webpush') as send:
            send_pending();send_pending()
            self.assertEqual(send.call_count,1)
            self.assertNotIn('Private rent',send.call_args.kwargs['data'])
            self.assertNotIn('12345',send.call_args.kwargs['data'])
            self.assertEqual(BillPushDelivery.objects.filter(sent_at__isnull=False).count(),1)

    def test_removed_bill_participant_does_not_receive_old_reminders(self):
        from django.utils import timezone
        from expenses.models import BillReminder
        from expenses.reminders import visible_reminders
        bill=RecurringBill.objects.create(workspace=self.home,created_by=self.a,paid_by=self.a,title='Rent',amount_cents=10000,next_due=timezone.localdate())
        bill.participants.set([self.a,self.b])
        BillReminder.objects.create(bill=bill,user=self.b.user,due=bill.next_due)
        self.assertEqual(visible_reminders(self.b.user).count(),1)
        bill.participants.remove(self.b)
        self.assertFalse(visible_reminders(self.b.user).exists())

    def test_bill_task_sync_is_idempotent_and_pause_cancels_upcoming_task(self):
        from expenses.bill_tasks import sync_bill_task
        from datetime import date
        from workflows.models import Task
        bill=RecurringBill.objects.create(workspace=self.home,created_by=self.a,paid_by=self.a,title='Water',amount_cents=4000,next_due=date(2026,11,15))
        sync_bill_task(bill);sync_bill_task(bill)
        bill.refresh_from_db()
        self.assertEqual(Task.objects.filter(workspace=self.home).count(),1)
        self.assertEqual(bill.task.occurrences.count(),1)
        bill.next_due=date(2026,11,18);bill.save();sync_bill_task(bill)
        self.assertEqual(str(bill.task.occurrences.get().due_at.date()),'2026-11-18')
        bill.active=False;bill.save();sync_bill_task(bill)
        self.assertEqual(bill.task.occurrences.get().state,'CANCELLED')
        bill.active=True;bill.save();sync_bill_task(bill)
        self.assertEqual(bill.task.occurrences.get().state,'OPEN')
        self.assertFalse(Expense.objects.exists())
