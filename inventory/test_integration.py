from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from households.models import Membership, Workspace
from inventory.models import GroceryBatch

class SharedHouseholdTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='dual')
        self.a = Workspace.objects.create(name='Alpha')
        self.b = Workspace.objects.create(name='Beta')
        for workspace in (self.a, self.b):
            Membership.objects.create(user=self.user, workspace=workspace, display_name='Dual')
        self.client.force_login(self.user)
        session = self.client.session
        session['active_workspace_id'] = self.a.pk
        session.save()

    def test_foreign_selected_workspace_is_denied_even_for_dual_member(self):
        self.assertEqual(self.client.get(reverse('groceries:workspace', args=[self.b.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('groceries:add', args=[self.b.pk]), {'name':'Milk','quantity':1,'unit':'item','storage':'fridge'}).status_code, 404)
        self.assertFalse(GroceryBatch.objects.exists())

    def test_list_uses_active_household(self):
        session = self.client.session
        session['active_workspace_id'] = self.b.pk
        session.save()
        self.assertRedirects(self.client.get(reverse('groceries:list')), reverse('groceries:workspace', args=[self.b.pk]))

    def test_roster_cannot_override_selection_with_query(self):
        response = self.client.get(reverse('households:detail'), {'workspace':self.b.pk})
        self.assertEqual(response.context['workspace'], self.a)

    def test_no_selection_requires_shared_picker(self):
        session = self.client.session
        session.pop('active_workspace_id')
        session.save()
        self.assertRedirects(self.client.get(reverse('groceries:list')), reverse('households:list'))

    def test_revoked_during_validation_cannot_write(self):
        from inventory.forms import GroceryBatchForm
        original = GroceryBatchForm.is_valid
        def revoke(form):
            result = original(form)
            Membership.objects.filter(user=self.user, workspace=self.a).update(is_active=False)
            return result
        with patch.object(GroceryBatchForm, 'is_valid', revoke):
            response = self.client.post(reverse('groceries:add', args=[self.a.pk]), {'name':'Milk','quantity':1,'unit':'item','storage':'fridge'})
        self.assertFalse(GroceryBatch.objects.exists())
        self.assertEqual(response.status_code, 302)

    def test_foreign_actions_never_call_provider_or_mutate(self):
        batch = GroceryBatch.objects.create(workspace=self.b, name='Private apples', quantity=1, unit='item')
        urls = [reverse('groceries:close', args=[self.b.pk, batch.pk]),
                reverse('groceries:suggest', args=[self.b.pk]),
                reverse('groceries:approve', args=[self.b.pk]),
                reverse('groceries:scan', args=[self.b.pk])]
        with patch('inventory.grocery_ai.meal_idea') as provider:
            for url in urls:
                self.assertEqual(self.client.post(url, {'state':'discarded','action':'save'}).status_code, 404)
            provider.assert_not_called()
        batch.refresh_from_db()
        self.assertEqual(batch.state, 'active')

    def test_grocery_posts_require_csrf(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        session = client.session
        session['active_workspace_id'] = self.a.pk
        session.save()
        self.assertEqual(client.post(reverse('groceries:add', args=[self.a.pk]), {}).status_code, 403)

    def test_grocery_response_is_private_and_never_cached(self):
        response = self.client.get(reverse('groceries:workspace', args=[self.a.pk]))
        self.assertIn('no-store', response['Cache-Control'])
        self.assertIn('Cookie', response['Vary'])
