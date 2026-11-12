from decimal import Decimal
from uuid import uuid4
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from households.models import Workspace,Membership
from expenses.services import save_expense,balances,payment_plan,request_payment,resolve_payment

class PaymentModeTests(TestCase):
    def setUp(self):
        self.h=Workspace.objects.create(name='Home')
        self.people=[Membership.objects.create(workspace=self.h,user=get_user_model().objects.create_user(username=x),display_name=x,role='OWNER' if x=='A' else 'ADULT') for x in 'ABC']
        a,b,c=self.people
        for payer,debtor in [(a,b),(b,c)]:
            save_expense(payer,dict(title='Demo',amount=Decimal('30'),paid_by=payer,date=timezone.localdate(),category='home',split_method='equal'),{debtor.pk:3000},uuid4())
    def test_original_and_simplified_preserve_net_and_allow_pair_payment(self):
        a,b,c=self.people;net=balances(self.h)
        self.assertEqual(payment_plan(self.h),[{'sender_id':c.pk,'receiver_id':a.pk,'amount_cents':3000}])
        self.h.simplify_debts=False;self.h.save()
        self.assertEqual(len(payment_plan(self.h)),2)
        self.assertEqual(net,balances(self.h))
        payment=request_payment(b,a,1000,'Partial original',uuid4())
        resolve_payment(a,payment.pk,'confirm')
        self.assertEqual(next(x['amount_cents'] for x in payment_plan(self.h) if x['sender_id']==b.pk),2000)
    def test_setting_is_owner_only_and_blocks_pending(self):
        a,b,c=self.people;url=reverse('expenses:payment-mode',args=[self.h.pk])
        self.client.force_login(b.user)
        self.assertEqual(self.client.post(url,{'mode':'original'}).status_code,403)
        self.client.force_login(a.user)
        self.assertEqual(self.client.post(url,{'mode':'original'}).status_code,302)
        self.h.refresh_from_db();self.assertFalse(self.h.simplify_debts)
        request_payment(b,a,1000,'Pending',uuid4())
        self.client.post(url,{'mode':'simplified'});self.h.refresh_from_db();self.assertFalse(self.h.simplify_debts)

    def test_original_mode_cannot_reintroduce_circular_settled_debts(self):
        a,b,c=self.people
        payment=request_payment(c,a,3000,'Simplified chain settlement',uuid4())
        resolve_payment(a,payment.pk,'confirm')
        self.assertFalse(any(balances(self.h).values()))
        self.client.force_login(a.user)
        response=self.client.post(reverse('expenses:payment-mode',args=[self.h.pk]),{'mode':'original'},follow=True)
        self.h.refresh_from_db()
        self.assertTrue(self.h.simplify_debts)
        self.assertContains(response,'circular debts')
