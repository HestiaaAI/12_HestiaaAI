"""A5 access contract: one public API, private HTML and remaining APIs."""
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase, override_settings


class AssignmentAuthTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_private_pages_redirect_and_navigation_is_hidden(self):
        for url in ('/tasks/manage/', '/tasks/manual/', '/tasks/render/', '/tasks/cbv-base/',
                    '/tasks/cbv-generic/', '/tasks/1/', '/tasks/search/', '/tasks/search/post/',
                    '/reports/tasks/',
                    '/analytics/tasks/', '/analytics/tasks/priority.png', '/lookup/'):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.url.startswith('/accounts/login/?next='))
        home = self.client.get('/')
        self.assertContains(home, 'Sign in')
        self.assertNotContains(home, 'href="/tasks/manage/"')
        self.assertNotContains(home, 'href="/reports/tasks/"')

    def test_exactly_one_public_json_endpoint(self):
        response = self.client.get('/api/charts/task-priorities/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        for url in ('/api/tasks/', '/api/response-demo/', '/api/external/products/', '/api/charts/task-creations/', '/reports/tasks/export.csv', '/reports/tasks/export.json'):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json(), {'error': 'Authentication required.'})

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_username_signup_login_and_logout(self):
        data = dict(username='newmember', email='member@example.test', password1='New-member-passphrase-903!', password2='New-member-passphrase-903!')
        response = self.client.post('/accounts/signup/', data)
        self.assertRedirects(response, '/')
        user = get_user_model().objects.get(username='newmember')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(len(mail.outbox), 0)
        self.assertContains(self.client.get('/'), 'href="/reports/tasks/"')
        self.client.post('/accounts/logout/')
        self.assertNotIn('_auth_user_id', self.client.session)
        response = self.client.post('/accounts/login/', {'login': 'newmember', 'password': data['password1'], 'next': '/reports/tasks/'})
        self.assertRedirects(response, '/reports/tasks/')
        self.assertEqual(self.client.get('/api/tasks/').status_code, 200)

    def test_invalid_and_duplicate_username_signup(self):
        data = dict(username='member', email='member@example.test', password1='Strong-member-pass-392!', password2='different')
        self.assertEqual(self.client.post('/accounts/signup/', data).status_code, 200)
        self.assertFalse(get_user_model().objects.exists())
        get_user_model().objects.create_user(username='member')
        data['password2'] = data['password1']
        self.assertEqual(self.client.post('/accounts/signup/', data).status_code, 200)
        self.assertEqual(get_user_model().objects.count(), 1)

    @override_settings(DEBUG=False)
    def test_access_policy_does_not_depend_on_debug(self):
        self.assertEqual(self.client.get("/reports/tasks/").status_code, 302)
        self.assertEqual(self.client.get("/api/tasks/").status_code, 401)
        self.assertEqual(self.client.get("/api/charts/task-priorities/").status_code, 200)

    def test_signup_requires_csrf_and_accepts_real_token(self):
        client = Client(enforce_csrf_checks=True)
        data = dict(username="csrfmember", email="csrf@example.test",
                    password1="Strong-csrf-passphrase-392!", password2="Strong-csrf-passphrase-392!")
        self.assertEqual(client.post("/accounts/signup/", data).status_code, 403)
        self.assertFalse(get_user_model().objects.exists())
        page = client.get("/accounts/signup/")
        self.assertContains(page, 'name="username"')
        data["csrfmiddlewaretoken"] = client.cookies["csrftoken"].value
        self.assertRedirects(client.post("/accounts/signup/", data), "/")
        self.assertIn("_auth_user_id", client.session)

    def test_weak_password_and_invalid_email_do_not_create_accounts(self):
        for email, password in (("valid@example.test", "123"), ("invalid", "Strong-member-pass-392!")):
            with self.subTest(email=email):
                response = self.client.post("/accounts/signup/", dict(
                    username="invalidmember", email=email, password1=password, password2=password))
                self.assertEqual(response.status_code, 200)
                self.assertFalse(get_user_model().objects.exists())
