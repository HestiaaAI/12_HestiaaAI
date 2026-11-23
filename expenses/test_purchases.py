from decimal import Decimal
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from unittest.mock import patch
from households.models import Workspace, Membership
from expenses.models import Expense
from expenses.purchases import create_item, join_item, claim_weights, receipt_rows, prepare_receipts, confirm_receipts

@override_settings(GROQ_API_KEY='')
class PurchaseTests(TestCase):
    def setUp(self):
        self.home=Workspace.objects.create(name='Maple')
        self.people=[Membership.objects.create(workspace=self.home,user=get_user_model().objects.create_user(username=p),display_name=p) for p in ['A','B','C']]
        self.a,self.b,self.c=self.people
        self.out=Membership.objects.create(workspace=Workspace.objects.create(name='Other'),user=get_user_model().objects.create_user(username='out'),display_name='Out')
        self.client.force_login(self.a.user)
    def item(self,name='Vaseline',scope='personal'):return create_item(self.a,name,1,scope)
    def receipt(self,text='VASELINE 6.00\nTOTAL 6.00',total='6.00'):return dict(payer=self.a,date='2026-11-11',total=Decimal(total),tax=Decimal('0'),discount=Decimal('0'),text=text)
    def rows(self,draft):return [r for receipt in draft.payload['receipts'] for r in receipt['rows']]
    def test_join_shared_and_own_units(self):
        item=self.item();join_item(self.b,item.pk,'shared',1)
        self.assertEqual(claim_weights(item),{self.a.pk:1,self.b.pk:1})
        join_item(self.c,item.pk,'own',2)
        self.assertEqual(claim_weights(item),{self.a.pk:1,self.b.pk:1,self.c.pk:4});self.assertEqual(item.total_units,3)
        for actor in [self.b,self.out]:
            with self.assertRaises(ValidationError):join_item(actor,item.pk,'own',1)
    def test_household_and_parser(self):
        self.assertEqual(set(claim_weights(self.item('Rice','household'))),{p.pk for p in self.people})
        self.assertEqual(receipt_rows('2 x VASELINE 12.00\nTAX 1.00\nTOTAL 13.00'),[dict(name='VASELINE',quantity=2,amount_cents=1200)])
    def test_confirmation_is_explicit_and_idempotent(self):
        item=self.item();join_item(self.b,item.pk,'shared',1)
        draft=prepare_receipts(self.a,[self.receipt()]);self.assertEqual(Expense.objects.count(),0)
        self.assertEqual(self.rows(draft)[0]['item_id'],item.pk)
        ids=confirm_receipts(self.a,draft.pk,self.rows(draft),True)
        self.assertEqual(list(Expense.objects.get().shares.order_by('member_id').values_list('amount_cents',flat=True)),[300,300])
        self.assertEqual(confirm_receipts(self.a,draft.pk,self.rows(draft),True),ids)
    def test_multiple_receipts_quantities_tax(self):
        item=self.item();join_item(self.b,item.pk,'own',1)
        first=self.receipt('VASELINE 6.00\nTOTAL 6.60','6.60');first['tax']=Decimal('.60')
        draft=prepare_receipts(self.a,[first,self.receipt('VASELINE 8.00\nSTORE B\nTOTAL 8.00','8.00')])
        self.assertEqual(len(confirm_receipts(self.a,draft.pk,self.rows(draft),True)),2)
        self.assertEqual(sum(Expense.objects.values_list('amount_cents',flat=True)),1460)
        self.assertEqual(sum(s.amount_cents for e in Expense.objects.all() for s in e.shares.filter(member=self.b)),730)
    def test_bad_total_unmatched_wrong_quantity(self):
        self.item()
        for text,total in [('UNMATCHED 6.00\nTOTAL 6.00','6.00'),('VASELINE 6.00\nTOTAL 7.00','7.00')]:
            draft=prepare_receipts(self.a,[self.receipt(text,total)])
            with self.assertRaises(ValidationError):confirm_receipts(self.a,draft.pk,self.rows(draft),True)
        self.assertEqual(Expense.objects.count(),0)
    def test_extra_shared_units_use_existing_participants(self):
        item=self.item('Milk','household')
        draft=prepare_receipts(self.a,[self.receipt('2 x MILK 9.00\nTOTAL 9.00','9.00')])
        confirm_receipts(self.a,draft.pk,self.rows(draft),True)
        expense=Expense.objects.get()
        self.assertEqual(list(expense.shares.order_by('member_id').values_list('amount_cents',flat=True)),[300,300,300])
        self.assertEqual(expense.purchase_line.quantity,2)

    def test_own_units_still_require_requested_quantity(self):
        item=self.item();join_item(self.b,item.pk,'own',1)
        draft=prepare_receipts(self.a,[self.receipt('3 x VASELINE 9.00\nTOTAL 9.00','9.00')])
        with self.assertRaises(ValidationError):confirm_receipts(self.a,draft.pk,self.rows(draft),True)
        self.assertFalse(Expense.objects.exists())

    def test_scoping_consent_and_duplicate(self):
        self.item();draft=prepare_receipts(self.a,[self.receipt()])
        with self.assertRaises(ValidationError):confirm_receipts(self.out,draft.pk,self.rows(draft),True)
        with self.assertRaises(ValidationError):confirm_receipts(self.a,draft.pk,self.rows(draft),False)
        confirm_receipts(self.a,draft.pk,self.rows(draft),True)
        with self.assertRaises(ValidationError):prepare_receipts(self.a,[self.receipt()])
        self.assertEqual(Expense.objects.count(),1)
    @override_settings(GROQ_API_KEY='test-key',GROQ_MODEL='test')
    @patch('expenses.purchase_matching.requests.post')
    def test_ai_names_only_and_no_invented_ids(self,post):
        self.item();post.return_value.json.return_value={'choices':[{'message':{'content':'{"matches":[{"line":0,"item_id":99999}]}'}}]}
        draft=prepare_receipts(self.a,[self.receipt('PET JELLY 6.00\nTOTAL 6.00')],use_ai=True)
        self.assertIsNone(self.rows(draft)[0]['item_id'])
        payload=str(post.call_args.kwargs['json'])
        for private in ['TOTAL','payer','6.00']:self.assertNotIn(private,payload)
    def test_pages_scope_and_escaping(self):
        self.item('<script>bad</script>');url=reverse('expenses:purchases',args=[self.home.pk])
        self.assertContains(self.client.get(url),'&lt;script&gt;')
        self.client.force_login(self.out.user);self.assertEqual(self.client.get(url).status_code,404)
    def test_actual_receipt_forms_review_then_save_without_double_charge(self):
        item=self.item();join_item(self.b,item.pk,'shared',1)
        url=reverse('expenses:receipts',args=[self.home.pk])
        payload={'receipts-TOTAL_FORMS':'1','receipts-INITIAL_FORMS':'0','receipts-MIN_NUM_FORMS':'1','receipts-MAX_NUM_FORMS':'5',
                 'receipts-0-payer':self.a.pk,'receipts-0-date':'2026-11-11','receipts-0-total':'6.00','receipts-0-tax':'0','receipts-0-discount':'0','receipts-0-text':'VASELINE 6.00\nTOTAL 6.00'}
        response=self.client.post(url,payload)
        self.assertEqual(response.status_code,302)
        review=response.url
        self.assertEqual(Expense.objects.count(),0)
        self.assertContains(self.client.get(review),'One last little look')
        data={'lines-TOTAL_FORMS':'1','lines-INITIAL_FORMS':'1','lines-MIN_NUM_FORMS':'1','lines-MAX_NUM_FORMS':'200','lines-0-line_id':0,'lines-0-item':item.pk,'lines-0-quantity':'1','lines-0-amount':'6.00'}
        self.assertContains(self.client.post(review,data),'Confirm the reviewed')
        self.assertEqual(Expense.objects.count(),0)
        data['confirm']='on'
        self.assertEqual(self.client.post(review,data).status_code,302)
        self.assertEqual(Expense.objects.count(),1)
        self.assertEqual(self.client.post(review,data).status_code,302)
        self.assertEqual(Expense.objects.count(),1)
        item.refresh_from_db();self.assertEqual(item.state,'purchased')

    def test_changed_participants_and_forged_line_ids_block_whole_batch(self):
        item=self.item();draft=prepare_receipts(self.a,[self.receipt()])
        wrong=[{**self.rows(draft)[0],'line_id':9876}]
        with self.assertRaises(ValidationError):confirm_receipts(self.a,draft.pk,wrong,True)
        join_item(self.b,item.pk,'shared',1)
        with self.assertRaises(ValidationError):confirm_receipts(self.a,draft.pk,self.rows(draft),True)
        self.assertEqual(Expense.objects.count(),0)

    @override_settings(GROQ_API_KEY='test-key',GROQ_MODEL='test')
    @patch('expenses.purchase_matching.requests.post')
    def test_broken_ai_response_falls_back_safely(self,post):
        self.item();post.return_value.json.return_value={'choices':[{'message':{'content':'{"matches":["bad"]}'}}]}
        draft=prepare_receipts(self.a,[self.receipt()],use_ai=True)
        self.assertEqual(self.rows(draft)[0]['item_id'],1)
        self.assertIn('invalid suggestion',draft.payload['matching_status'])
    def test_discount_rounding_and_atomic_multi_receipt_failure(self):
        self.item('Rice','household');self.item('Soap','personal')
        good=self.receipt('RICE 3.00\nSOAP 3.00\nTOTAL 5.00','5.00');good['discount']=Decimal('1.00')
        draft=prepare_receipts(self.a,[good]);ids=confirm_receipts(self.a,draft.pk,self.rows(draft),True)
        self.assertEqual(sum(Expense.objects.filter(pk__in=ids).values_list('amount_cents',flat=True)),500)
        self.assertTrue(all(sum(e.shares.values_list('amount_cents',flat=True))==e.amount_cents for e in Expense.objects.filter(pk__in=ids)))

    def test_join_post_uses_signed_in_member_not_forged_identity(self):
        item=self.item()
        self.client.force_login(self.b.user)
        url=reverse('expenses:purchase-join',args=[self.home.pk,item.pk])
        self.assertEqual(self.client.get(url).status_code,405)
        self.assertEqual(self.client.post(url,{'kind':'own','quantity':2,'member':self.c.pk}).status_code,302)
        self.assertTrue(item.claims.filter(member=self.b,kind='own',quantity=2).exists())
        self.assertFalse(item.claims.filter(member=self.c).exists())
    def test_review_with_missing_claims_shows_error_instead_of_crashing(self):
        item=self.item()
        draft=prepare_receipts(self.a,[self.receipt()])
        item.claims.all().delete()
        response=self.client.get(reverse('groceries:receipt-split-review',args=[self.home.pk,draft.pk]))
        self.assertContains(response,'has no participants')
        self.assertEqual(Expense.objects.count(),0)
    def test_unmatched_receipt_line_can_be_assigned_to_a_roommate_basket(self):
        draft=prepare_receipts(self.a,[self.receipt('SOAP 6.00\nTOTAL 6.00')])
        rows=self.rows(draft)
        self.assertIsNone(rows[0]['item_id'])
        rows[0]['recipient_ids']=[self.b.pk]
        self.assertEqual(Expense.objects.count(),0)
        ids=confirm_receipts(self.a,draft.pk,rows,True)
        expense=Expense.objects.get(pk=ids[0])
        self.assertEqual(list(expense.shares.values_list('member_id','amount_cents')),[(self.b.pk,600)])
        self.assertEqual(confirm_receipts(self.a,draft.pk,rows,True),ids)
    def test_unmatched_basket_rejects_outside_household(self):
        draft=prepare_receipts(self.a,[self.receipt('SOAP 6.00\nTOTAL 6.00')])
        rows=self.rows(draft);rows[0]['recipient_ids']=[self.out.pk]
        with self.assertRaises(ValidationError):confirm_receipts(self.a,draft.pk,rows,True)
        self.assertEqual(Expense.objects.count(),0)
