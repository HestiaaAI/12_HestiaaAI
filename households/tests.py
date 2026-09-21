from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.core.cache import cache
from allauth.account.models import EmailAddress


class LoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="priya", email="priya@example.com", password="test-only-password"
        )

        EmailAddress.objects.create(user=cls.user, email=cls.user.email, verified=True, primary=True)

    def setUp(self):
        cache.clear()

    def test_login_page_has_accessible_form(self):
        response = self.client.get("/accounts/login/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(reverse("accounts:login"), "/accounts/login/")
        self.assertTemplateUsed(response, "registration/login.html")
        self.assertTemplateUsed(response, "layouts/auth.html")
        self.assertContains(response, 'for="id_login"')
        self.assertContains(response, 'for="id_password"')
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertContains(response, 'autocomplete="current-password"')
        self.assertNotContains(response, "Household tasks")

    def test_success_without_next_has_working_confirmation(self):
        response = self.client.post("/accounts/login/", {
            "login": "priya@example.com", "password": "test-only-password"
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))
        self.assertContains(response, "You’re signed in")
        self.assertNotContains(response, 'type="password"')

    def test_safe_local_next_is_preserved_on_error_and_used_on_success(self):
        target = "/accounts/login/?welcome=1"
        response = self.client.post("/accounts/login/", {
            "login": "priya@example.com", "password": "wrong", "next": target
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="/accounts/login/?welcome=1"')
        response = self.client.post("/accounts/login/", {
            "login": "priya@example.com", "password": "test-only-password", "next": target
        })
        self.assertRedirects(response, target)

    def test_external_and_insecure_next_are_rejected(self):
        for target in ("https://evil.example/", "//evil.example/", "http://testserver/private/"):
            with self.subTest(target=target):
                self.client.logout()
                response = self.client.post("/accounts/login/", {
                    "login": "priya@example.com", "password": "test-only-password", "next": target
                }, secure=True)
                self.assertRedirects(response, "/accounts/login/", fetch_redirect_response=False)

    def test_bad_credentials_retain_username_never_password(self):
        response = self.client.post("/accounts/login/", {
            "login": "priya@example.com", "password": "secret-invalid-password"
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="priya@example.com"')
        self.assertNotContains(response, "secret-invalid-password")
        self.assertContains(response, 'role="alert"')
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_inactive_account_is_rejected(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        response = self.client.post("/accounts/login/", {
            "login": "priya@example.com", "password": "test-only-password"
        })
        self.assertRedirects(response, reverse("account_inactive"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_missing_fields_show_linked_errors(self):
        response = self.client.post("/accounts/login/", {})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="id_login_error"')
        self.assertContains(response, 'aria-describedby="id_login_error"')
        self.assertContains(response, 'aria-invalid="true"')

    def test_csrf_is_enforced_and_real_token_allows_login(self):
        client = Client(enforce_csrf_checks=True)
        credentials = {"login": "priya@example.com", "password": "test-only-password"}
        self.assertEqual(client.post("/accounts/login/", credentials).status_code, 403)
        self.assertEqual(client.get("/accounts/login/").status_code, 200)
        response = client.post("/accounts/login/", {
            **credentials, "csrfmiddlewaretoken": client.cookies["csrftoken"].value
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(client.session["_auth_user_id"], str(self.user.pk))


class LogoutTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="logout-test")
        self.client.force_login(self.user)

    def test_post_logs_out_and_returns_to_login(self):
        response = self.client.post("/accounts/logout/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(reverse("accounts:logout"), "/accounts/logout/")
        self.assertRedirects(response, reverse("accounts:login"))
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(response, "Sign in to Hestia")

    def test_get_does_not_log_out(self):
        response = self.client.get("/accounts/logout/")
        self.assertEqual(response.status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)

    def test_authenticated_header_has_post_form(self):
        response = self.client.get("/accounts/login/")
        self.assertContains(response, 'action="/accounts/logout/"')
        self.assertContains(response, 'method="post"')
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertContains(response, '>Sign out</button>')
        self.client.logout()
        self.assertNotContains(self.client.get("/accounts/login/"), '>Sign out</button>')

    def test_csrf_required_and_valid_token_ends_session(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post("/accounts/logout/").status_code, 403)
        self.assertIn("_auth_user_id", client.session)
        client.get("/accounts/login/")
        response = client.post("/accounts/logout/", {
            "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
        })
        self.assertRedirects(response, "/accounts/login/")
        self.assertNotIn("_auth_user_id", client.session)

    def test_external_next_cannot_redirect_logout(self):
        response = self.client.post("/accounts/logout/", {"next": "https://evil.example/"})
        self.assertRedirects(response, "/accounts/login/")
