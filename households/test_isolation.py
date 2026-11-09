from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from .models import Workspace, Membership
from workflows.models import Task

class IsolationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('dual')
        self.a = Workspace.objects.create(name='Alpha')
        self.b = Workspace.objects.create(name='Beta secret')
        self.ma = Membership.objects.create(user=self.user, workspace=self.a, display_name='A')
        self.mb = Membership.objects.create(user=self.user, workspace=self.b, display_name='B')
        self.ta = Task.objects.create(workspace=self.a, title='Alpha visible', priority='LOW', task_type='CHORE')
        self.tb = Task.objects.create(workspace=self.b, title='Beta secret', priority='URGENT', task_type='CHORE')
        self.client.force_login(self.user)
        s = self.client.session
        s['active_workspace_id'] = self.a.pk
        s.save()

    def test_task_routes_exclude_foreign_household(self):
        for name in ['task_forms:board']:
            with self.subTest(name=name):
                response = self.client.get(reverse(name), follow=True)
                self.assertContains(response, self.ta.title)
                self.assertNotContains(response, self.tb.title)

    def test_foreign_detail_returns_404(self):
        self.assertEqual(self.client.get(self.tb.get_absolute_url()).status_code,404)

    def test_dual_member_sees_only_selected_household(self):
        self.assertContains(self.client.get(reverse('task_forms:board')), self.ta.title)
        self.client.post(reverse('households:switch'), {'workspace_id':self.b.pk})
        response=self.client.get(reverse('task_forms:board'))
        self.assertContains(response,self.tb.title)
        self.assertNotContains(response,self.ta.title)

    def test_forged_workspace_cannot_create_task(self):
        self.client.post(reverse('task_forms:board'), {'workspace':self.b.pk,'title':'Forged','priority':'HIGH','task_type':'CHORE'})
        self.assertFalse(Task.objects.filter(title='Forged').exists())

    def test_valid_create_uses_active_membership(self):
        self.client.post(reverse('task_forms:board'), {'workspace':self.a.pk,'title':'Valid','priority':'HIGH','task_type':'CHORE','created_by_membership':self.mb.pk})
        task=Task.objects.get(title='Valid')
        self.assertEqual(task.workspace,self.a)
        self.assertEqual(task.created_by_membership,self.ma)

    def test_no_membership_cannot_read_or_create(self):
        Membership.objects.filter(user=self.user).update(is_active=False)
        self.assertRedirects(self.client.get(reverse('task_forms:board')),reverse('households:onboarding'),fetch_redirect_response=False)
        self.client.post(reverse('task_forms:board'), {'workspace':self.a.pk,'title':'Forbidden','priority':'HIGH','task_type':'CHORE'})
        self.assertFalse(Task.objects.filter(title='Forbidden').exists())

    def test_private_api_and_exports_are_household_scoped(self):
        for name in ['workflows:task-export-csv']:
            response=self.client.get(reverse(name))
            self.assertContains(response,self.ta.title)
            self.assertNotContains(response,self.tb.title)

    def test_missing_household_returns_409_for_private_data(self):
        s=self.client.session;s.pop('active_workspace_id');s.save()
        for name,kwargs in [('workflows:task-export-csv',{})]:
            response=self.client.get(reverse(name,kwargs=kwargs))
            self.assertEqual(response.status_code,409,name)
            self.assertEqual(response.json(),{'error':'Select a household to continue.','code':'household_required'})

    def test_private_responses_are_not_shared_cacheable(self):
        for name in ['task_forms:board','workflows:task-export-csv']:
            response=self.client.get(reverse(name))
            self.assertIn('no-store',response['Cache-Control'])
            self.assertIn('Cookie',response['Vary'])

    @patch('workflows.action_plan_views.generate_action_plan')
    def test_foreign_action_plan_never_calls_provider(self,provider):
        self.assertEqual(self.client.post(reverse('workflows:task-action-plan',args=[self.tb.pk])).status_code,404)
        provider.assert_not_called()

    @patch('workflows.ai_views.get_suggestions')
    def test_brain_dump_confirmation_rejects_other_selected_household(self, provider):
        provider.return_value=[{'title':'Draft A','description':'','priority':'LOW','task_type':'CHORE'}]
        response=self.client.post(reverse('ai_tasks:brain-dump'),{'action':'generate','workspace':self.a.pk,'text':'Work'})
        token=response.context['draft_token']
        self.client.post(reverse('households:switch'),{'workspace_id':self.b.pk})
        data={'action':'save','draft_token':token,'confirm':'on','form-TOTAL_FORMS':1,'form-INITIAL_FORMS':1,'form-0-title':'Draft A','form-0-description':'','form-0-priority':'LOW','form-0-task_type':'CHORE'}
        self.client.post(reverse('ai_tasks:brain-dump'),data)
        self.assertFalse(Task.objects.filter(title='Draft A').exists())

    @patch('workflows.ai_views.get_suggestions')
    def test_membership_revoked_between_preview_and_save(self, provider):
        provider.return_value=[{'title':'Revoked draft','description':'','priority':'LOW','task_type':'CHORE'}]
        response=self.client.post(reverse('ai_tasks:brain-dump'),{'action':'generate','workspace':self.a.pk,'text':'Work'})
        token=response.context['draft_token']
        Membership.objects.filter(pk=self.ma.pk).update(is_active=False)
        self.client.post(reverse('ai_tasks:brain-dump'),{'action':'save','draft_token':token,'confirm':'on','form-TOTAL_FORMS':1,'form-INITIAL_FORMS':1,'form-0-title':'Revoked draft','form-0-priority':'LOW','form-0-task_type':'CHORE'})
        self.assertFalse(Task.objects.filter(title='Revoked draft').exists())

    @patch('workflows.ai_views.get_suggestions')
    def test_foreign_brain_dump_never_calls_provider(self, provider):
        self.client.post(reverse('ai_tasks:brain-dump'),{'action':'generate','workspace':self.b.pk,'text':'Secret'})
        provider.assert_not_called()

    def test_review_form_subclass_preserves_scoped_validation(self):
        from workflows.ai_forms import ReviewTaskForm
        from workflows.task_forms import TaskCreateForm
        self.assertTrue(issubclass(ReviewTaskForm,TaskCreateForm))
        self.assertTrue(ReviewTaskForm({'title':'Reviewed','description':'','priority':'LOW','task_type':'CHORE'}).is_valid())

    def test_lookup_scopes_products_entries_and_tasks(self):
        from inventory.models import Product, ShoppingListEntry
        from api.external import compare_products
        Product.objects.create(workspace=self.a,canonical_name='Milk A')
        Product.objects.create(workspace=self.b,canonical_name='Milk B')
        ShoppingListEntry.objects.create(workspace=self.a,item_name='Milk A')
        ShoppingListEntry.objects.create(workspace=self.b,item_name='Milk B')
        Task.objects.create(workspace=self.a,title='Milk A',task_type='SHOPPING')
        Task.objects.create(workspace=self.b,title='Milk B',task_type='SHOPPING')
        with patch('api.external._fetch_open_food_facts',return_value={'products':[],'match_count':0,'match_count_exact':True}):
            result=compare_products('Milk',workspace=self.a)
        for key in ['products','shopping_items','shopping_tasks']:
            self.assertEqual(len(result['internal'][key]),1)
            self.assertEqual(result['internal'][key][0]['workspace'],self.a.name)



    @patch('workflows.ai_views.get_suggestions')
    def test_no_membership_does_not_call_draft_provider(self,provider):
        Membership.objects.filter(user=self.user).update(is_active=False)
        self.client.post(reverse('ai_tasks:brain-dump'),{'action':'generate','workspace':self.a.pk,'text':'No access'})
        provider.assert_not_called()

    def test_unselected_legacy_routes_and_anonymous_data_boundary(self):
        session=self.client.session;session.pop('active_workspace_id');session.save()
        for name in ['task_forms:board','workflows:task-insights','ai_tasks:brain-dump']:
            self.assertRedirects(self.client.get(reverse(name)),reverse('households:list'),fetch_redirect_response=False)
        self.client.logout()
        for name in ['workflows:task-export-csv']:
            self.assertEqual(self.client.get(reverse(name)).status_code,401)

    def test_membership_missing_inside_create_transaction_cannot_save(self):
        with patch('workflows.forms_views.Membership.objects.select_for_update') as locked:
            locked.return_value.get.side_effect=Membership.DoesNotExist
            response=self.client.post(reverse('task_forms:board'),{'workspace':self.a.pk,'title':'Revoked during create','priority':'HIGH','task_type':'CHORE'})
        self.assertEqual(response.status_code,302)
        self.assertFalse(Task.objects.filter(title='Revoked during create').exists())

    def test_independent_user_sessions_never_share_data(self):
        from django.test import Client
        other=get_user_model().objects.create_user('independent')
        Membership.objects.create(user=other,workspace=self.b,display_name='B only')
        separate=Client();separate.force_login(other)
        self.assertContains(separate.get(reverse('task_forms:board')),self.tb.title)
        self.assertNotContains(separate.get(reverse('task_forms:board')),self.ta.title)
        self.assertContains(self.client.get(reverse('task_forms:board')),self.ta.title)
        self.assertNotContains(self.client.get(reverse('task_forms:board')),self.tb.title)
        self.assertEqual(separate.get(self.ta.get_absolute_url()).status_code,404)

    def test_insights_excludes_foreign_counts(self):
        response=self.client.get(reverse('workflows:task-insights'))
        self.assertEqual(response.context['total_tasks'],1)
        self.assertEqual(response.context['priority_summary'],[{'label':'Low','count':1}])
        self.assertNotContains(response,self.b.name)
