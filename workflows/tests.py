"""Historical implementation routes now deliberately share the canonical board."""
from django.test import TestCase, SimpleTestCase
from django.contrib.auth import get_user_model
from django.urls import resolve, reverse
from households.models import Membership, Workspace
from .models import Task
from .views import TaskDetailView

class TaskTemplateTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user('templates')
        home=Workspace.objects.create(name='Template household')
        Membership.objects.create(user=self.user,workspace=home,display_name='Reader')
        self.task=Task.objects.create(workspace=home,title='Buy groceries',description='<script>alert(1)</script>',priority='HIGH')
        self.client.force_login(self.user)

    def test_board_renders_canonical_fields_and_escapes_content(self):
        for name in ['task_forms:board']:
            response=self.client.get(reverse(name),follow=True)
            self.assertTemplateUsed(response,'tasks/forms/task_board.html')
            self.assertContains(response,self.task.title)
            self.assertContains(response,self.task.get_absolute_url())
            self.assertContains(response,'High')
            self.assertContains(response,'&lt;script&gt;')
            self.assertNotContains(response,'<script>alert(1)</script>')

    def test_search_and_empty_states(self):
        for name in ['task_forms:board']:
            response=self.client.get(reverse(name),{'q':'nothing'},follow=True)
            self.assertContains(response,'No tasks found')
            self.assertNotContains(response,self.task.title)
        Task.objects.all().delete()
        self.assertContains(self.client.get(reverse('task_forms:board')),'Add your first task')

    def test_home_navigation_and_detail(self):
        self.assertRedirects(self.client.get('/'),reverse('task_forms:board'))
        board=self.client.get(reverse('task_forms:board'))
        self.assertContains(board,reverse('households:list'))
        detail=self.client.get(self.task.get_absolute_url())
        self.assertIs(resolve(self.task.get_absolute_url()).func.view_class,TaskDetailView)
        self.assertContains(detail,'&lt;script&gt;')
        self.assertEqual(self.client.get('/tasks/999999/').status_code,404)
