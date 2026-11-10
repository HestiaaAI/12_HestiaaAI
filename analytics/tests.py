"""Insights replaces PNGs and assignment analytics with scoped text summaries."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from households.models import Membership, Workspace
from workflows.models import Task, TaskOccurrence

class InsightTests(TestCase):
    def setUp(self):
        user=get_user_model().objects.create_user('insights-reader')
        self.home=Workspace.objects.create(name='Current household')
        other=Workspace.objects.create(name='Foreign household')
        Membership.objects.create(user=user,workspace=self.home,display_name='Reader')
        task=Task.objects.create(workspace=self.home,title='Chore one',priority='HIGH',task_type='CHORE')
        Task.objects.create(workspace=self.home,title='Chore two',priority='LOW',task_type='CHORE')
        Task.objects.create(workspace=other,title='Foreign urgent',priority='URGENT',task_type='SHOPPING')
        TaskOccurrence.objects.create(task=task,sequence=1)
        TaskOccurrence.objects.create(task=task,sequence=2)
        self.client.force_login(user)

    def test_real_tasks_counted_once_and_foreign_data_excluded(self):
        response=self.client.get(reverse('workflows:task-insights'))
        self.assertEqual(response.context['total_tasks'],2)
        self.assertEqual(response.context['priority_summary'],[{'label':'High','count':1},{'label':'Low','count':1}])
        self.assertContains(response,'Chore: 2')
        self.assertNotContains(response,'Urgent')
        self.assertNotContains(response,'Foreign')
        self.assertNotContains(response,'priority.png')

    def test_empty_state_and_export(self):
        Task.objects.filter(workspace=self.home).delete()
        response=self.client.get(reverse('workflows:task-insights'))
        self.assertEqual(response.context['total_tasks'],0)
        self.assertContains(response,'No tasks yet')
        self.assertContains(response,reverse('workflows:task-export-csv'))
        self.assertNotContains(self.client.get(reverse('workflows:task-export-csv')),'Foreign urgent')

    def test_created_task_updates_real_summary(self):
        self.client.post(reverse('task_forms:board'),{'workspace':self.home.pk,'title':'New urgent','task_type':'CHORE','priority':'URGENT'})
        response=self.client.get(reverse('workflows:task-insights'))
        self.assertEqual(response.context['total_tasks'],3)
        self.assertContains(response,'Urgent: 1')

    def test_household_name_is_escaped_and_insights_is_read_only(self):
        self.home.name='<script>unsafe</script>'
        self.home.save(update_fields=['name'])
        response=self.client.get(reverse('workflows:task-insights'))
        self.assertContains(response,'&lt;script&gt;unsafe&lt;/script&gt;')
        self.assertNotContains(response,self.home.name)
        self.assertEqual(self.client.post(reverse('workflows:task-insights')).status_code,405)
        self.assertEqual(Task.objects.count(),3)
