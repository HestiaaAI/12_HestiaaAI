from datetime import date,datetime,timezone as dt_timezone
from decimal import Decimal
from uuid import uuid4
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from households.models import Workspace,Membership
from expenses.models import Expense,ExpenseEvent,Settlement
from expenses.services import save_expense,void_expense,request_payment,resolve_payment
from expenses.insights import spending_report,activity_rows

class ExpenseInsightTests(TestCase):
    def setUp(self):
        self.home=Workspace.objects.create(name='Home')
        self.a,self.b=[Membership.objects.create(workspace=self.home,user=get_user_model().objects.create_user(username=n),display_name=n) for n in ['A','B']]
        self.other=Workspace.objects.create(name='Other')
        self.out=Membership.objects.create(workspace=self.other,user=get_user_model().objects.create_user(username='out'),display_name='Out')
        self.client.force_login(self.a.user)
    def add(self,title,amount,shares,day,payer=None,category='groceries'):
        return save_expense(self.a,{'title':title,'amount':Decimal(amount)/100,'paid_by':payer or self.a,'date':day,'category':category,'split_method':'custom'},shares,uuid4())
    def setup_months(self):
        self.add('Rice',3000,{self.a.pk:1000,self.b.pk:2000},date(2026,11,9))
        self.add('Personal shampoo',500,{self.a.pk:500},date(2026,11,10),payer=self.b,category='home')
        self.add('Early October',1000,{self.a.pk:400,self.b.pk:600},date(2026,10,5))
        self.add('Late October',1800,{self.a.pk:900,self.b.pk:900},date(2026,10,20))
    def test_shares_upfront_comparison_and_personal_shared_are_separate(self):
        self.setup_months();r=spending_report(self.a,2026,11,today=date(2026,11,11))
        self.assertEqual(r['your_spend'],1500);self.assertEqual(r['your_upfront'],3000);self.assertEqual(r['household_spend'],3500)
        self.assertEqual(r['previous_full'],1300);self.assertEqual(r['comparison_spend'],400)
        self.assertEqual(r['delta'],1100);self.assertEqual(r['change_percent'],275)
        self.assertEqual(r['personal_spend'],500);self.assertEqual(r['shared_spend'],1000)
        self.assertEqual(r['year_total'],2800);self.assertEqual(len(r['months']),12)
        self.assertEqual(r['months'][10]['total'],1500)
    def test_settlements_do_not_count_as_spending_and_voids_are_excluded(self):
        self.setup_months()
        before=spending_report(self.a,2026,11,today=date(2026,11,11))['your_spend']
        payment=request_payment(self.b,self.a,100,'cash',uuid4());resolve_payment(self.a,payment.pk,'confirm')
        self.assertEqual(spending_report(self.a,2026,11,today=date(2026,11,11))['your_spend'],before)
        e=Expense.objects.get(title='Rice');void_expense(self.a,e.pk,e.version)
        self.assertEqual(spending_report(self.a,2026,11,today=date(2026,11,11))['your_spend'],500)
    def test_january_rollover_and_zero_baseline(self):
        self.add('December',100,{self.a.pk:100},date(2025,12,5))
        self.add('January',200,{self.a.pk:200},date(2026,1,5))
        r=spending_report(self.a,2026,1,today=date(2026,1,11));self.assertEqual(r['comparison_spend'],100);self.assertEqual(r['delta'],100)
        r=spending_report(self.a,2025,12,today=date(2026,1,11));self.assertIsNone(r['change_percent'])
    def test_future_records_and_other_households_do_not_leak(self):
        self.setup_months();self.add('Future',9999,{self.a.pk:9999},date(2027,1,1))
        save_expense(self.out,{'title':'Private outside purchase','amount':Decimal('999'),'paid_by':self.out,'date':date(2026,11,1),'category':'home','split_method':'equal'},{self.out.pk:99900},uuid4())
        r=spending_report(self.a,2026,11,today=date(2026,11,11));self.assertEqual(r['year_total'],2800)
        for name in ['trends','activity']:
            url=reverse('expenses:'+name,args=[self.home.pk]);response=self.client.get(url)
            self.assertEqual(response.status_code,200);self.assertNotContains(response,'Private outside purchase')
            self.client.force_login(self.out.user);self.assertEqual(self.client.get(url).status_code,404);self.client.force_login(self.a.user)
    def test_activity_identifies_recording_and_receiving_actor(self):
        self.setup_months();p=request_payment(self.b,self.a,100,'cash',uuid4());resolve_payment(self.a,p.pk,'confirm')
        rows=activity_rows(self.home)
        recorded=[r for r in rows if r['kind']=='payment_recorded'];confirmed=[r for r in rows if r['kind']=='payment_confirmed']
        self.assertEqual(recorded[0]['actor_id'],self.b.pk);self.assertEqual(confirmed[0]['actor_id'],self.a.pk)
        self.assertEqual(len([r for r in rows if r['kind']=='created']),4)
    def test_invalid_filter_input_renders_feedback_not_server_error(self):
        self.assertEqual(self.client.get(reverse('expenses:trends',args=[self.home.pk]),{'year':'nope','month':'99'}).status_code,200)
        self.assertEqual(self.client.get(reverse('expenses:activity',args=[self.home.pk]),{'since':'bad','person':self.out.pk}).status_code,200)
    def test_activity_filters_confirmed_payment_by_receiver(self):
        self.setup_months();p=request_payment(self.b,self.a,100,'cash',uuid4());resolve_payment(self.a,p.pk,'confirm')
        response=self.client.get(reverse('expenses:activity',args=[self.home.pk]),{'kind':'payment_confirmed','person':self.a.pk})
        self.assertEqual(response.context['page'].paginator.count,1)
        self.assertEqual(response.context['page'][0]['actor_id'],self.a.pk)
    def test_empty_spending_does_not_show_fake_percentage(self):
        r=spending_report(self.a,2026,11,today=date(2026,11,11))
        self.assertEqual(r['your_spend'],0);self.assertIsNone(r['change_percent']);self.assertIsNone(r['peak'])
        response=self.client.get(reverse('expenses:trends',args=[self.home.pk]),{'year':2026,'month':11})
        self.assertContains(response,'empty-donut');self.assertContains(response,'No spending recorded for this period')
