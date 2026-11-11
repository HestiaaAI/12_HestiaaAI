from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase,override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.cache import cache
from households.models import Workspace,Membership
from expenses.purchases import create_item
from expenses.models import Expense

@override_settings(GROQ_API_KEY='')
class ReceiptDefaultFlowTests(TestCase):
    def setUp(self):
        cache.clear()
        self.home=Workspace.objects.create(name='Home')
        self.actor=Membership.objects.create(workspace=self.home,user=get_user_model().objects.create_user(username='receipt-owner'),display_name='Owner')
        create_item(self.actor,'Rice',1,'household');self.client.force_login(self.actor.user)
        self.url=reverse('groceries:receipt-split',args=[self.home.pk])
    def data(self):return {'receipts-TOTAL_FORMS':'1','receipts-INITIAL_FORMS':'0','receipts-MIN_NUM_FORMS':'1','receipts-MAX_NUM_FORMS':'5','receipts-0-payer':self.actor.pk,'receipts-0-date':'2026-11-11','receipts-0-total':'6.00','receipts-0-tax':'0','receipts-0-discount':'0','receipts-0-text':'RICE 6.00\nTOTAL 6.00'}
    def test_payer_is_explicit_and_appears_before_photo(self):
        response=self.client.get(self.url)
        html=response.content.decode()
        self.assertLess(html.index('name="receipts-0-payer"'),html.index('data-photo'))
        self.assertIsNone(response.context['forms'].forms[0].initial.get('payer'))
        self.assertContains(response,'name="matching" value="ai" checked')
    @patch('expenses.purchases.suggest_matches')
    def test_ai_is_default_and_local_is_explicit_optout(self,match):
        match.return_value=([{'item_id':1,'match':'test'}],'test')
        self.assertEqual(self.client.post(self.url,self.data()).status_code,302)
        self.assertTrue(match.call_args.args[2])
        data=self.data();data['matching']='local'
        self.assertEqual(self.client.post(self.url,data).status_code,302)
        self.assertFalse(match.call_args.args[2]);self.assertEqual(Expense.objects.count(),0)
    def test_missing_payer_cannot_prepare_review_or_add_costs(self):
        data=self.data();data['receipts-0-payer']=''
        response=self.client.post(self.url,data)
        self.assertEqual(response.status_code,200);self.assertContains(response,'This field is required')
        self.assertEqual(Expense.objects.count(),0)
    def test_local_selection_survives_invalid_form(self):
        data=self.data();data['matching']='local';data['receipts-0-total']=''
        response=self.client.post(self.url,data)
        self.assertEqual(response.context['matching_mode'],'local')
        self.assertContains(response,'name="matching" value="local" checked')
    def test_review_text_and_tick_come_before_totals(self):
        html=self.client.get(self.url).content.decode()
        self.assertLess(html.index('name="receipts-0-text"'),html.index('data-reviewed-bill'))
        self.assertLess(html.index('data-reviewed-bill'),html.index('name="receipts-0-total"'))
        self.assertNotIn('Read totals from text',html)
    def test_numbered_receipt_summaries_are_not_purchase_lines(self):
        from expenses.purchases import receipt_rows
        result=receipt_rows('1 RICE 6.00\n2 TAX 0.60\n3 TOTAL 6.60\n4 NOT A REAL PURCHASE')
        self.assertEqual(result,[{'name':'RICE','quantity':1,'amount_cents':600}])
