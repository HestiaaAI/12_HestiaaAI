"""Google sign-in stays available without exposing credentials in the database."""
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from households.social_adapter import GoogleSocialAccountAdapter


TEST_GOOGLE_PROVIDERS = {
    "google": {
        "APPS": [{"client_id": "test-client.apps.googleusercontent.com", "secret": "test-secret", "key": ""}],
        "SCOPE": ["profile", "email"],
        "OAUTH_PKCE_ENABLED": True,
    }
}


@override_settings(GOOGLE_OAUTH_ENABLED=True, SOCIALACCOUNT_PROVIDERS=TEST_GOOGLE_PROVIDERS)
class GoogleOAuthTests(TestCase):
    def test_login_and_signup_offer_google_when_configured(self):
        for path in ("/accounts/login/", "/accounts/signup/"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertContains(response, "Continue with Google")
                self.assertContains(response, 'action="/accounts/google/login/"')

    def test_google_button_hidden_without_credentials(self):
        with override_settings(GOOGLE_OAUTH_ENABLED=False):
            self.assertNotContains(self.client.get("/accounts/login/"), "Continue with Google")

    def test_google_login_requires_post_and_uses_local_callback(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(reverse("google_login"), "/accounts/google/login/")
        self.assertEqual(reverse("google_callback"), "/accounts/google/login/callback/")
        self.assertEqual(client.get("/accounts/google/login/").status_code, 200)
        self.assertEqual(client.post("/accounts/google/login/").status_code, 403)
        client.get("/accounts/login/")
        response = client.post("/accounts/google/login/", {
            "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
        })
        self.assertEqual(response.status_code, 302)
        redirect = urlparse(response["Location"])
        self.assertEqual(redirect.netloc, "accounts.google.com")
        query = parse_qs(redirect.query)
        self.assertEqual(query["client_id"], ["test-client.apps.googleusercontent.com"])
        self.assertEqual(query["redirect_uri"], ["http://testserver/accounts/google/login/callback/"])

    def test_production_host_uses_https_callback(self):
        with override_settings(ALLOWED_HOSTS=["hestia12.pythonanywhere.com"]):
            response = self.client.post(
                "/accounts/google/login/", secure=True,
                HTTP_HOST="hestia12.pythonanywhere.com",
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            parse_qs(urlparse(response["Location"]).query)["redirect_uri"],
            ["https://hestia12.pythonanywhere.com/accounts/google/login/callback/"],
        )

    @override_settings(ACCOUNT_SIGNUP_ENABLED=False)
    def test_only_verified_google_identity_can_join_when_password_signup_closed(self):
        adapter = GoogleSocialAccountAdapter()
        def social(provider, verified):
            return SimpleNamespace(
                account=SimpleNamespace(provider=provider),
                email_addresses=[SimpleNamespace(verified=verified)],
            )

        self.assertTrue(adapter.is_open_for_signup(None, social("google", True)))
        self.assertFalse(adapter.is_open_for_signup(None, social("google", False)))
        self.assertFalse(adapter.is_open_for_signup(None, social("other", True)))
