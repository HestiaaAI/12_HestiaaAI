from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from .models import Workspace, Membership
from .context import resolve_active_membership

class ContextTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('context')
        self.a = Workspace.objects.create(name='Alpha')
        self.b = Workspace.objects.create(name='Beta')
        self.request = RequestFactory().get('/')
        self.request.user = self.user
        SessionMiddleware(lambda r: None).process_request(self.request)

    def member(self, workspace, **kwargs):
        return Membership.objects.create(user=self.user, workspace=workspace, display_name='Member', **kwargs)

    def test_zero_and_one_membership(self):
        self.assertIsNone(resolve_active_membership(self.request))
        m = self.member(self.a)
        self.assertEqual(resolve_active_membership(self.request), m)
        self.assertEqual(self.request.active_household, self.a)

    def test_multiple_and_stale_selection(self):
        self.member(self.a)
        self.member(self.b)
        self.assertIsNone(resolve_active_membership(self.request))
        self.request.session['active_workspace_id'] = self.a.pk
        self.assertEqual(resolve_active_membership(self.request).workspace, self.a)
        Membership.objects.filter(workspace=self.a).update(is_active=False)
        self.assertEqual(resolve_active_membership(self.request).workspace, self.b)
        Membership.objects.filter(workspace=self.b).update(is_active=False)
        self.assertIsNone(resolve_active_membership(self.request))
        self.assertNotIn('active_workspace_id', self.request.session)

    def test_staff_and_null_user_have_no_bypass(self):
        self.user.is_staff = True
        Membership.objects.create(workspace=self.a, display_name='Historical')
        self.member(self.b, is_active=False)
        self.assertIsNone(resolve_active_membership(self.request))
