from unittest.mock import patch
from django.urls import reverse
from django.test import override_settings, TestCase
from households import test_isolation

class UnifiedFlowTests(TestCase):
    setUp = test_isolation.IsolationTests.setUp
    def test_canonical_task_journey(self):
        response=self.client.get(reverse('task_forms:board'))
        self.assertContains(response,'Organize with AI')
        self.assertContains(response,reverse('workflows:task-insights'))
        self.assertContains(self.client.get(self.ta.get_absolute_url()),reverse('task_forms:board'))

    def test_navigation_has_one_task_destination(self):
        response=self.client.get(reverse('task_forms:board'))
        self.assertNotContains(response,'href="/tasks/cbv-generic/"')
        self.assertNotContains(response,'href="/tasks/search/"')
        self.assertContains(response,'Household')

    def test_no_assignment_implementation_copy_in_product_pages(self):
        for url in [reverse('task_forms:board'),self.ta.get_absolute_url()]:
            response=self.client.get(url)
            for text in ['seed_template_demo','primary key','ORM','CBV','assignment demo']:
                self.assertNotContains(response,text)

    def test_home_respects_household_state(self):
        self.assertRedirects(self.client.get('/'),reverse('task_forms:board'),fetch_redirect_response=False)
        session=self.client.session;session.pop('active_workspace_id');session.save()
        self.assertRedirects(self.client.get('/'),reverse('households:list'),fetch_redirect_response=False)


    def test_insights_share_scoped_summary(self):
        response=self.client.get(reverse('workflows:task-insights'))
        self.assertEqual(response.context['total_tasks'],1)
        self.assertEqual(response.context['priority_summary'],[{'label':'Low','count':1}])
        self.assertNotContains(response,'Beta')


    @patch('workflows.ai_views.get_suggestions',side_effect=RuntimeError('private failure'))
    def test_provider_failure_preserves_manual_task_path(self,provider):
        response=self.client.post(reverse('ai_tasks:brain-dump'),{'action':'generate','workspace':self.a.pk,'text':'Keep this draft text'})
        self.assertContains(response,'Keep this draft text')
        self.assertContains(response,reverse('task_forms:board'))
        self.assertNotContains(response,'private failure')

    @override_settings(HESTIA_BRAIN_DUMP_BACKEND='mock')
    def test_ai_confirmation_returns_to_selected_board(self):
        from workflows.test_ai import BrainDumpTests
        response=self.client.post(reverse('ai_tasks:brain-dump'),{'action':'generate','workspace':self.a.pk,'text':'Plan chores'})
        payload=BrainDumpTests.payload(self,response)
        response=self.client.post(reverse('ai_tasks:brain-dump'),payload)
        self.assertRedirects(response,reverse('task_forms:board'))
        self.assertEqual(self.ta.__class__.objects.filter(workspace=self.a).count(),4)
        self.assertEqual(self.ta.__class__.objects.filter(workspace=self.b).count(),1)
