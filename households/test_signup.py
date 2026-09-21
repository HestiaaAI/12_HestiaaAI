"""Integration tests for registration and verified email sign-in."""
import re
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", ACCOUNT_SIGNUP_ENABLED=True)
class SignupTests(TestCase):
    def setUp(self):
        cache.clear()
        self.data = {"email": "person@example.com", "password1": "Fictional-passphrase-823!", "password2": "Fictional-passphrase-823!"}

    def signup(self, **extra):
        return self.client.post("/accounts/signup/", {**self.data, **extra})

    def confirmation_path(self):
        return re.search(r"https?://[^\s]+(/accounts/confirm-email/[^\s]+/)", mail.outbox[-1].body).group(1)

    def test_signup_page_and_reciprocal_login_links(self):
        response = self.client.get("/accounts/signup/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(reverse("accounts:signup"), "/accounts/signup/")
        self.assertContains(response, 'name="email"')
        self.assertNotContains(response, 'name="username"')
        self.assertContains(response, 'href="/accounts/login/"')
        self.assertContains(self.client.get("/accounts/login/"), 'href="/accounts/signup/"')

    def test_signup_requires_verification_then_email_login_works(self):
        response = self.signup(is_staff="true", is_superuser="true", workspace_id="1")
        self.assertEqual(response.status_code, 302)
        user = get_user_model().objects.get(email=self.data["email"])
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.hestia_memberships.exists())
        self.assertTrue(user.check_password(self.data["password1"]))
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(len(mail.outbox), 1)
        url = self.confirmation_path()
        from allauth.account.models import EmailAddress
        address = EmailAddress.objects.get(user=user)
        self.assertFalse(address.verified)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        address.refresh_from_db()
        self.assertFalse(address.verified)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        address.refresh_from_db()
        self.assertTrue(address.verified)
        self.assertNotIn("_auth_user_id", self.client.session)
        response = self.client.post("/accounts/login/", {"login":"PERSON@example.com", "password":self.data["password1"]}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("_auth_user_id", self.client.session)

    def test_unverified_password_cannot_log_in(self):
        self.signup()
        self.client.post("/accounts/login/", {"login":self.data["email"], "password":self.data["password1"]})
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_invalid_signup_preserves_email_not_password(self):
        for changes in ({"password2":"different"}, {"password1":"123", "password2":"123"}, {"email":"invalid"}):
            with self.subTest(changes=changes):
                response = self.signup(**changes)
                self.assertEqual(response.status_code, 200)
                self.assertFalse(get_user_model().objects.exists())
                self.assertNotContains(response, self.data["password1"])
                self.assertContains(response, 'role="alert"')

    def test_duplicate_verified_email_does_not_create_or_replace_user(self):
        self.signup()
        self.client.post(self.confirmation_path())
        original = get_user_model().objects.get(email=self.data["email"])
        self.client.logout()
        self.signup(email="PERSON@example.com", password1="Different-password-349!", password2="Different-password-349!")
        self.assertEqual(get_user_model().objects.count(), 1)
        original.refresh_from_db()
        self.assertTrue(original.check_password(self.data["password1"]))

    def test_invalid_expired_and_used_links_never_sign_in(self):
        self.signup()
        url = self.confirmation_path()
        response = self.client.get("/accounts/confirm-email/not-a-real-key/")
        self.assertContains(response, "invalid")
        from django.utils import timezone
        with patch("django.core.signing.time.time", return_value=(timezone.now()+timedelta(days=4)).timestamp()):
            self.assertContains(self.client.get(url), "expired")
        self.client.post(url)
        self.assertEqual(self.client.post(url).status_code, 404)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_signup_and_confirmation_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post("/accounts/signup/", self.data).status_code, 403)
        self.signup()
        self.assertEqual(client.post(self.confirmation_path()).status_code, 403)

    @override_settings(ACCOUNT_SIGNUP_ENABLED=False)
    def test_signup_disabled_without_staging_delivery(self):
        response = self.signup()
        self.assertContains(response, "Registration is unavailable")
        self.assertFalse(get_user_model().objects.exists())

    def test_mail_failure_has_recovery_and_no_session(self):
        from smtplib import SMTPException
        with patch("django.core.mail.message.EmailMultiAlternatives.send", side_effect=SMTPException("private-provider-details")):
            response = self.signup()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "could not send")
        self.assertNotContains(response, "private-provider-details")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_resend_is_limited_and_can_retry_after_cooldown(self):
        self.signup()
        self.client.post("/accounts/login/", {"login":self.data["email"], "password":self.data["password1"]})
        self.assertEqual(len(mail.outbox), 1)
        cache.clear()  # Simulate expiration of the configured resend cooldown.
        self.client.post("/accounts/login/", {"login":self.data["email"], "password":self.data["password1"]})
        self.assertEqual(len(mail.outbox), 2)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_existing_admin_keeps_admin_login_without_becoming_email_verified(self):
        user = get_user_model().objects.create_superuser("existing-admin", "admin@example.com", "Admin-password-837!")
        response = self.client.post("/admin/login/?next=/admin/", {"username":user.username, "password":"Admin-password-837!", "next":"/admin/"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)
        self.client.logout()
        self.client.post("/accounts/login/", {"login":user.email,"password":"Admin-password-837!"})
        self.assertNotIn("_auth_user_id", self.client.session)
        from allauth.account.models import EmailAddress
        self.assertFalse(EmailAddress.objects.get(user=user).verified)

    def test_verification_get_does_not_log_out_another_user(self):
        self.signup()
        other = get_user_model().objects.create_user("other")
        self.client.force_login(other, backend="django.contrib.auth.backends.ModelBackend")
        self.client.get(self.confirmation_path())
        self.assertEqual(self.client.session.get("_auth_user_id"), str(other.pk))

    def test_signup_uses_configured_origin_not_request_host(self):
        with override_settings(ACCOUNT_PUBLIC_ORIGIN="https://hestia.example.com"):
            self.signup()
        self.assertIn("https://hestia.example.com/accounts/confirm-email/", mail.outbox[0].body)
        self.assertNotIn("http://testserver", mail.outbox[0].body)

    def test_username_is_not_a_public_login_identifier(self):
        self.signup()
        self.client.post(self.confirmation_path())
        user = get_user_model().objects.get(email=self.data["email"])
        self.client.post("/accounts/login/", {"login":user.username, "password":self.data["password1"]})
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_failed_delivery_explains_cooldown_and_recovers(self):
        from smtplib import SMTPException
        with patch("django.core.mail.message.EmailMultiAlternatives.send", side_effect=SMTPException):
            response = self.signup()
        self.assertContains(response, "3 minutes")
        response = self.client.post("/accounts/login/", {"login":self.data["email"], "password":self.data["password1"]}, follow=True)
        self.assertEqual(len(mail.outbox), 0)
        self.assertContains(response, "may be delayed")
        cache.clear()
        self.client.post("/accounts/login/", {"login":self.data["email"], "password":self.data["password1"]})
        self.assertEqual(len(mail.outbox), 1)
