"""Legacy GET redirects and POST stays a scoped read-only board adapter."""
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from households.models import Workspace, Membership
from .models import Task

class TaskSearchTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user('search')
        self.home=Workspace.objects.create(name='Search home')
        other=Workspace.objects.create(name='Foreign')
        Membership.objects.create(user=self.user,workspace=self.home,display_name='Reader')
        self.task=Task.objects.create(workspace=self.home,title='Buy groceries')
        Task.objects.create(workspace=other,title='Foreign groceries')
        self.client.force_login(self.user)

    def test_get_filters_and_detail_links(self):
        response=self.client.get(reverse('task_search:get'),{'q':'GROCERIES'},follow=True)
        self.assertContains(response,self.task.title)
        self.assertContains(response,self.task.get_absolute_url())
        self.assertNotContains(response,'Foreign groceries')
        self.assertEqual(self.client.get(self.task.get_absolute_url()).status_code,200)

    def test_post_body_filters_and_never_creates(self):
        response=self.client.post(reverse('task_search:post')+'?q=nothing',{'q':'groceries','title':'Never create','workspace':self.home.pk})
        self.assertContains(response,self.task.title)
        self.assertNotContains(response,'Foreign groceries')
        self.assertEqual(Task.objects.count(),2)
        self.assertFalse(Task.objects.filter(title='Never create').exists())

    def test_blank_and_no_match_filters(self):
        self.assertContains(self.client.post(reverse('task_search:post'),{'q':''}),self.task.title)
        self.assertContains(self.client.post(reverse('task_search:post'),{'q':'nothing'}),'No tasks found')

    def test_search_terms_and_titles_are_escaped(self):
        title='<script>alert(1)</script>'
        Task.objects.create(workspace=self.home,title=title)
        response=self.client.get(reverse('task_search:get'),{'q':title},follow=True)
        self.assertContains(response,'&lt;script&gt;')
        self.assertNotContains(response,title)

    def test_csrf_and_method_boundary(self):
        client=Client(enforce_csrf_checks=True);client.force_login(self.user)
        url=reverse('task_search:post')
        self.assertEqual(client.post(url,{'q':'groceries'}).status_code,403)
        client.get(reverse('task_forms:board'))
        response=client.post(url,{'q':'groceries','csrfmiddlewaretoken':client.cookies['csrftoken'].value})
        self.assertContains(response,self.task.title)
        self.assertEqual(self.client.post(reverse('task_search:get')).status_code,405)
