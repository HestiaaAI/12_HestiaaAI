from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from households.models import Workspace,Membership
from expenses.models import Expense
from expenses.purchases import create_item,check_item

class ChecklistNoteTests(TestCase):
    def setUp(self):
        self.home=Workspace.objects.create(name='Home')
        self.actor=Membership.objects.create(workspace=self.home,user=get_user_model().objects.create_user(username='note-reader'),display_name='Reader')
        self.item=create_item(self.actor,'Rice',1,'household')
        self.client.force_login(self.actor.user)
    def test_check_uncheck_is_separate_from_receipt_and_money(self):
        check_item(self.actor,self.item.pk,True);self.item.refresh_from_db()
        self.assertTrue(self.item.is_checked);self.assertEqual(self.item.state,'open');self.assertEqual(Expense.objects.count(),0)
        check_item(self.actor,self.item.pk,False);self.item.refresh_from_db();self.assertFalse(self.item.is_checked)
    def test_note_has_quick_entry_and_real_checkbox(self):
        r=self.client.get(reverse('expenses:purchases',args=[self.home.pk]))
        self.assertContains(r,'Add an item');self.assertContains(r,'type="checkbox"');self.assertNotContains(r,'Who starts in the split?')
    def test_check_requires_household_membership_and_post(self):
        url=reverse('expenses:purchase-check',args=[self.home.pk,self.item.pk])
        self.assertEqual(self.client.get(url).status_code,405)
        self.assertEqual(self.client.post(url,{'checked':'on'}).status_code,302)
        other=Membership.objects.create(workspace=Workspace.objects.create(name='Other'),user=get_user_model().objects.create_user(username='outsider'))
        with self.assertRaises(ValidationError):check_item(other,self.item.pk,False)
        self.client.force_login(other.user);self.assertEqual(self.client.post(url,{'checked':'on'}).status_code,404)
    def test_ajax_check_saves_without_expense_or_redirect(self):
        url=reverse('expenses:purchase-check',args=[self.home.pk,self.item.pk])
        response=self.client.post(url,{'checked':'on'},HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.json(),{'checked':True});self.assertEqual(Expense.objects.count(),0)
        response=self.client.post(url,{},HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.json(),{'checked':False})
