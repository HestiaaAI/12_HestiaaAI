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
        for name in ['task_forms:board','workflows:task-manual','workflows:task-render','workflows:task-cbv-base','workflows:task-cbv-generic','task_search:get','task_search:post']:
            with self.subTest(name=name):
                response = self.client.get(reverse(name), follow=True)
                self.assertContains(response, self.ta.title)
                self.assertNotContains(response, self.tb.title)

    def test_foreign_detail_returns_404(self):
        self.assertEqual(self.client.get(self.tb.get_absolute_url()).status_code,404)

    def test_dual_member_sees_only_selected_household(self):
        self.assertEqual(self.client.get(reverse('api:task-list')).json()['tasks'][0]['title'],self.ta.title)
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
        for name in ['api:task-list','reports:tasks-json','reports:tasks-csv']:
            response=self.client.get(reverse(name))
            self.assertContains(response,self.ta.title)
            self.assertNotContains(response,self.tb.title)

    def test_missing_household_returns_409_for_private_data(self):
        s=self.client.session;s.pop('active_workspace_id');s.save()
        for name,kwargs in [('api:task-list',{}),('reports:tasks-json',{}),('reports:tasks-csv',{}),('api:chart-creations',{}),('analytics:task-priority-chart',{}),('vega:spec',{'chart':'chart2'}),('vega:image',{'chart':'chart2'})]:
            response=self.client.get(reverse(name,kwargs=kwargs))
            self.assertEqual(response.status_code,409,name)
            self.assertEqual(response.json(),{'error':'Select a household to continue.','code':'household_required'})

    def test_private_responses_are_not_shared_cacheable(self):
        for name in ['task_forms:board','api:task-list','reports:tasks-csv','analytics:task-priority-chart']:
            response=self.client.get(reverse(name))
            self.assertIn('no-store',response['Cache-Control'])
            self.assertIn('Cookie',response['Vary'])

    @patch('workflows.action_plan_views.generate_action_plan')
    def test_foreign_action_plan_never_calls_provider(self,provider):
        self.assertEqual(self.client.post(reverse('api:task-action-plan',args=[self.tb.pk])).status_code,404)
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
