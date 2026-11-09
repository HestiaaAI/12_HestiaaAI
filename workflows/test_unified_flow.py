from unittest.mock import patch
from django.urls import reverse
from django.test import override_settings
from households import test_isolation

class UnifiedFlowTests(test_isolation.IsolationTests):
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

    def test_legacy_list_and_search_use_canonical_flow(self):
        for name in ['workflows:task-manual','workflows:task-render','workflows:task-cbv-base','workflows:task-cbv-generic','task_search:get','task_search:post']:
            response=self.client.get(reverse(name),{'q':'Alpha','next':'https://evil.invalid'})
            self.assertEqual(response.status_code,302)
            self.assertEqual(response.url,reverse('task_forms:board')+'?q=Alpha')
        response=self.client.post(reverse('task_search:post'),{'q':'Alpha','workspace':self.b.pk,'title':'No create'})
        self.assertEqual(response.status_code,200)
        self.assertNotContains(response,self.tb.title)
        self.assertFalse(self.ta.__class__.objects.filter(title='No create').exists())

    def test_insights_share_scoped_summary(self):
        response=self.client.get(reverse('workflows:task-insights'))
        self.assertEqual(response.context['total_tasks'],1)
        self.assertEqual(response.context['priority_summary'],[{'label':'Low','count':1}])
        self.assertNotContains(response,'Beta')
        for name in ['reports:task-report','analytics:task-stats','vega:charts']:
            self.assertRedirects(self.client.get(reverse(name)),reverse('workflows:task-insights'),fetch_redirect_response=False)

    @override_settings(HESTIA_BRAIN_DUMP_BACKEND='mock')
    @patch('workflows.ai_adapter.get_suggestions')
    def test_html_and_json_drafts_use_shared_extractor(self,shared):
        shared.return_value=[{'title':'Shared','description':'','priority':'LOW','task_type':'CHORE'}]
        response=self.client.post(reverse('api:brain-dump'),{'text':'work'})
        self.assertEqual(response.json()['tasks'],shared.return_value)
        shared.assert_called_once_with('work')

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

    @override_settings(HESTIA_BRAIN_DUMP_BACKEND='local')
    @patch('workflows.services.hf_local.extract_tasks')
    def test_shared_validation_preserves_provider_metadata_for_both_adapters(self,extract):
        extract.return_value={'tasks':[{'title':'Shared validated draft','task_type':'CHORE','priority':'LOW','description':'Draft only'}],'warnings':['Sample warning'],'model_id':'test-local-model'}
        html=self.client.post(reverse('ai_tasks:brain-dump'),{'action':'generate','workspace':self.a.pk,'text':'Shared input'})
        self.assertContains(html,'Shared validated draft')
        api=self.client.post(reverse('api:brain-dump'),{'text':'Shared input'}).json()
        self.assertEqual(api['warnings'],['Sample warning'])
        self.assertEqual(api['model_id'],'test-local-model')
        self.assertFalse(api['saved'])
        self.assertEqual(extract.call_count,2)
        self.assertFalse(self.ta.__class__.objects.filter(title='Shared validated draft').exists())

    @patch('workflows.ai_adapter.get_suggestions',side_effect=RuntimeError('private provider details'))
    def test_json_provider_failure_is_safe_and_never_saves(self,extract):
        response=self.client.post(reverse('api:brain-dump'),{'text':'New draft'})
        self.assertEqual(response.status_code,500)
        self.assertNotIn('private provider details',response.json()['error'])
        self.assertEqual(self.ta.__class__.objects.count(),2)
