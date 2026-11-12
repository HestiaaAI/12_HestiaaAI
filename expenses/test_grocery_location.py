from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from households.models import Workspace,Membership
from expenses.purchases import create_item,join_item

class GroceryChecklistLocationTests(TestCase):
    def setUp(self):
        self.home=Workspace.objects.create(name='Home')
        self.a=Membership.objects.create(workspace=self.home,user=get_user_model().objects.create_user(username='alice'),display_name='Alice')
        self.b=Membership.objects.create(workspace=self.home,user=get_user_model().objects.create_user(username='bea'),display_name='Bea')
        self.client.force_login(self.a.user)
    def test_groceries_links_to_checklist_and_split_receipt_flow(self):
        note=reverse('groceries:shopping',args=[self.home.pk]);scan=reverse('groceries:receipt-split',args=[self.home.pk])
        response=self.client.get(reverse('groceries:workspace',args=[self.home.pk]))
        self.assertContains(response,note);self.assertContains(response,scan)
        self.assertContains(self.client.get(note),'Shared list')
        self.assertContains(self.client.get(scan),reverse('groceries:scan',args=[self.home.pk]))
        overview=self.client.get(reverse('expenses:overview',args=[self.home.pk]))
        self.assertNotContains(overview,'Purchase lists ↗')
    def test_personal_notes_and_subgroup_notes_use_groceries_navigation(self):
        create_item(self.a,'Rice',1,'household')
        create_item(self.a,'Oil',1,'personal')
        vaseline=create_item(self.b,'Vaseline',1,'personal');join_item(self.a,vaseline.pk,'shared')
        response=self.client.get(reverse('groceries:shopping',args=[self.home.pk]))
        for text in ['Shared list','Personal lists','Shared between','Alice','Bea','Rice','Oil','Vaseline']:
            self.assertContains(response,text)
        self.assertEqual(response.wsgi_request.resolver_match.namespace,'groceries')
        self.assertNotContains(response,'Who starts in the split?')
