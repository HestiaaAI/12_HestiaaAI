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

    def test_product_pages_have_no_dead_links_or_coursework(self):
        from html.parser import HTMLParser
        from urllib.parse import urlsplit
        from django.urls import resolve
        class Links(HTMLParser):
            def __init__(self):
                super().__init__();self.urls=[]
            def handle_starttag(self,tag,attrs):
                for key,value in attrs:
                    if (tag,key) in {('a','href'),('form','action')} and value:
                        self.urls.append(value)
        for url in [reverse('task_forms:board'),self.ta.get_absolute_url(),reverse('workflows:task-insights'),reverse('ai_tasks:brain-dump'),reverse('product-lookup'),reverse('households:list')]:
            response=self.client.get(url)
            self.assertEqual(response.status_code,200)
            for text in ['INFO 490','University of Illinois','Bundled sample handbook','primary key','Open the JSON API']:
                self.assertNotContains(response,text)
            parser=Links();parser.feed(response.content.decode())
            for href in parser.urls:
                target=urlsplit(href)
                if not target.netloc and target.path and not target.path.startswith('/static/'):
                    self.assertIsNotNone(resolve(target.path))

    def test_draft_form_uses_selected_household_without_another_picker(self):
        from django.forms import HiddenInput
        response=self.client.get(reverse('ai_tasks:brain-dump'))
        form=response.context['input_form']
        self.assertIsInstance(form.fields['workspace'].widget,HiddenInput)
        self.assertEqual(form.initial['workspace'],self.a.pk)

    def test_required_handbook_route_is_restored(self):
        from django.urls import resolve
        self.assertEqual(resolve('/tasks/ask/').view_name, 'ask-hestia')
