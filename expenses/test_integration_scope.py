from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.test import TestCase
from django.urls import reverse
from households.models import Membership, Workspace
from .services import lock_household

class SelectedHouseholdIntegrationTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user(username='integration-user')
        self.one=Workspace.objects.create(name='First home')
        self.two=Workspace.objects.create(name='Second home')
        self.actor=Membership.objects.create(user=self.user,workspace=self.one,display_name='Owner',role='OWNER')
        Membership.objects.create(user=self.user,workspace=self.two,display_name='Owner',role='OWNER')
        self.client.force_login(self.user)
        session=self.client.session;session['active_workspace_id']=self.one.pk;session.save()

    def test_dual_member_cannot_open_other_household_finances_or_provider(self):
        for name in ('expenses:overview','expenses:trends','expenses:recurring','groceries:shopping','groceries:receipt-split','groceries:energy'):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name,args=[self.two.pk])).status_code,404)
        with patch('inventory.views.find_location') as provider:
            self.assertEqual(self.client.get(reverse('groceries:energy',args=[self.two.pk]),{'period':'day'}).status_code,404)
            provider.assert_not_called()

    def test_expenses_home_uses_shared_selection(self):
        self.assertRedirects(self.client.get(reverse('expenses:home')),reverse('expenses:overview',args=[self.one.pk]),fetch_redirect_response=False)

    def test_deactivated_user_or_membership_cannot_mutate(self):
        self.user.is_active=False;self.user.save(update_fields=['is_active'])
        with transaction.atomic(), self.assertRaises(PermissionDenied):lock_household(self.actor)
        self.user.is_active=True;self.user.save(update_fields=['is_active'])
        self.actor.is_active=False;self.actor.save(update_fields=['is_active'])
        with transaction.atomic(), self.assertRaises(PermissionDenied):lock_household(self.actor)

    def test_financial_export_has_private_http_contract(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('expenses:export',args=[self.one.pk])).status_code,401)
        self.client.force_login(self.user)
        session=self.client.session;session.pop('active_workspace_id',None);session.save()
        self.assertEqual(self.client.get(reverse('expenses:export',args=[self.one.pk])).status_code,409)

    def test_pages_never_cache_finances(self):
        response=self.client.get(reverse('expenses:overview',args=[self.one.pk]))
        self.assertEqual(response.status_code,200)
        self.assertIn('no-store',response['Cache-Control'])

    def test_owner_transfer_between_request_and_save_blocks_payment_mode(self):
        from .views import membership
        def stale_actor(request, workspace_id):
            actor=membership(request,workspace_id)
            Membership.objects.filter(pk=actor.pk).update(role='MEMBER')
            return actor
        with patch('expenses.settle_views.membership',side_effect=stale_actor):
            response=self.client.post(reverse('expenses:payment-mode',args=[self.one.pk]),{'mode':'original'})
        self.assertEqual(response.status_code,403)
        self.one.refresh_from_db();self.assertTrue(self.one.simplify_debts)

    def test_removed_member_cannot_save_thermostat_from_stale_request(self):
        from inventory.views import membership_for
        def revoked(request, workspace_id):
            actor=membership_for(request,workspace_id)
            Membership.objects.filter(pk=actor.pk).update(is_active=False)
            return actor
        with patch('inventory.views.membership_for',side_effect=revoked):
            response=self.client.post(reverse('groceries:energy',args=[self.one.pk]),{'action':'preferences','day_min':68,'day_max':72,'night_min':65,'night_max':70})
        self.assertEqual(response.status_code,403)
        from households.models import ThermostatPreference
        self.assertFalse(ThermostatPreference.objects.exists())

    def test_removed_member_cannot_comment_from_stale_request(self):
        from .services import save_expense
        from .models import ExpenseEvent
        from uuid import uuid4
        from django.utils import timezone
        expense=save_expense(self.actor,{'title':'Local test','amount':'2.00','paid_by':self.actor,'category':'other','date':timezone.localdate(),'split_method':'equal','note':''},{self.actor.pk:200},uuid4())
        from .views import membership
        def revoked(request,workspace_id):
            actor=membership(request,workspace_id)
            Membership.objects.filter(pk=actor.pk).update(is_active=False)
            return actor
        with patch('expenses.views.membership',side_effect=revoked):
            response=self.client.post(reverse('expenses:comment',args=[self.one.pk,expense.pk]),{'text':'Should not be stored'})
        self.assertEqual(response.status_code,403)
        self.assertFalse(ExpenseEvent.objects.filter(kind='comment').exists())

    def test_receipt_revocation_before_provider_blocks_disclosure(self):
        from .purchases import prepare_receipts
        from django.core.exceptions import ValidationError
        from django.utils import timezone
        def revoke_during_parse(text):
            Membership.objects.filter(pk=self.actor.pk).update(is_active=False)
            return [{'name':'Rice','quantity':1,'amount_cents':200}]
        with patch('expenses.purchases.receipt_rows',side_effect=revoke_during_parse), patch('expenses.purchases.suggest_matches') as provider:
            with self.assertRaises(ValidationError):
                prepare_receipts(self.actor,[{'text':'Rice 2.00','payer':self.actor,'date':str(timezone.localdate()),'total':'2.00','tax':'0','discount':'0'}],use_ai=True)
            provider.assert_not_called()

    def test_newly_onboarded_household_needs_no_seed_records(self):
        user=get_user_model().objects.create_user(username='brand-new-roommate')
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse('households:onboarding')).status_code,200)
        response=self.client.post(reverse('households:create'),{'name':'Created through onboarding','timezone':'America/Chicago'})
        self.assertRedirects(response,reverse('task_forms:board'),fetch_redirect_response=False)
        home=Workspace.objects.get(name='Created through onboarding')
        for name in ('expenses:overview','expenses:trends','expenses:recurring','groceries:shopping','groceries:receipt-split','groceries:energy'):
            with self.subTest(name=name):self.assertEqual(self.client.get(reverse(name,args=[home.pk])).status_code,200)
