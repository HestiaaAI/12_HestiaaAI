from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from .models import Workspace, Membership

class SelectionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('selector')
        self.a = Workspace.objects.create(name='Alpha selected')
        self.b = Workspace.objects.create(name='Foreign hidden')
        self.client.force_login(self.user)

    def test_onboarding_and_picker(self):
        self.assertContains(self.client.get(reverse('households:onboarding')), 'Sign out')
        Membership.objects.create(user=self.user, workspace=self.a, display_name='A')
        page = self.client.get(reverse('households:list'))
        self.assertContains(page, self.a.name)
        self.assertNotContains(page, self.b.name)

    def test_switch_validation_and_csrf(self):
        url = reverse('households:switch')
        Membership.objects.create(user=self.user, workspace=self.a, display_name='A')
        self.assertEqual(self.client.get(url).status_code, 405)
        before = dict(self.client.session)
        self.assertEqual(self.client.post(url, {'workspace_id': self.b.pk}).status_code, 400)
        self.assertEqual(dict(self.client.session), before)
        self.assertRedirects(self.client.post(url, {'workspace_id': self.a.pk, 'next': 'https://evil.invalid'}), reverse('task_forms:board'), fetch_redirect_response=False)
        self.assertEqual(self.client.session['active_workspace_id'], self.a.pk)
        secure = Client(enforce_csrf_checks=True)
        secure.force_login(self.user)
        self.assertEqual(secure.post(url, {'workspace_id': self.a.pk}).status_code, 403)

    def test_login_boundary(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('households:list')).status_code, 302)
