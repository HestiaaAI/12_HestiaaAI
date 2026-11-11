from decimal import Decimal
from uuid import uuid4
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from households.models import Workspace,Membership
from expenses.services import save_expense,request_payment,resolve_payment
from expenses.settle_views import settlement_context

class SettleUITests(TestCase):
    def setUp(self):
        self.home=Workspace.objects.create(name='Test')
        self.a=Membership.objects.create(workspace=self.home,user=get_user_model().objects.create_user(username='a'),display_name='A')
        self.b=Membership.objects.create(workspace=self.home,user=get_user_model().objects.create_user(username='b'),display_name='B')
        save_expense(self.a,dict(title='Groceries',amount=Decimal('60'),paid_by=self.a,date=timezone.localdate(),category='groceries',split_method='equal'),{self.a.pk:3000,self.b.pk:3000},uuid4())
        self.client.force_login(self.b.user)
    def test_prefill_and_pending_then_all_settled(self):
        url=reverse('expenses:settle',args=[self.home.pk])
        self.assertContains(self.client.get(url),'$30.00')
        page=self.client.get(reverse('expenses:payment',args=[self.home.pk])+f'?receiver={self.a.pk}')
        self.assertContains(page,'value="30.00"')
        payment=request_payment(self.b,self.a,3000,'Cash',uuid4())
        self.assertFalse(settlement_context(self.b)['all_settled'])
        self.assertContains(self.client.get(url),'Waiting for confirmation')
        resolve_payment(self.a,payment.pk,'confirm')
        self.assertContains(self.client.get(url),'All settled')
    def test_partial_payment_leaves_remaining_and_no_cross_household_access(self):
        payment=request_payment(self.b,self.a,1000,'Partial',uuid4());resolve_payment(self.a,payment.pk,'confirm')
        self.assertEqual(settlement_context(self.b)['settle_net'],-2000)
        self.assertContains(self.client.get(reverse('expenses:settle',args=[self.home.pk])),'$20.00')
        self.assertEqual(self.client.get(reverse('expenses:settle',args=[9999])).status_code,404)

    def test_incoming_rows_open_roommate_balance(self):
        self.client.force_login(self.a.user)
        page=self.client.get(reverse('expenses:settle',args=[self.home.pk]))
        self.assertContains(page,reverse('expenses:person',args=[self.home.pk,self.b.pk]))
        detail=self.client.get(reverse('expenses:person',args=[self.home.pk,self.b.pk]))
        self.assertContains(detail,'$30.00')
        self.assertContains(detail,'Waiting for a payment record')
