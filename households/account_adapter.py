"""Project policy around allauth's registration and verification lifecycle."""
from django.conf import settings
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from allauth.core import context
from allauth.account.adapter import DefaultAccountAdapter


class AccountAdapter(DefaultAccountAdapter):
    def is_safe_url(self, url):
        request = context.request
        return url_has_allowed_host_and_scheme(
            url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
        )

    def is_open_for_signup(self, request):
        return settings.ACCOUNT_SIGNUP_ENABLED

    def get_email_confirmation_url(self, request, emailconfirmation):
        # A configured origin avoids trusting an incoming Host for emailed links.
        return settings.ACCOUNT_PUBLIC_ORIGIN.rstrip("/") + reverse(
            "account_confirm_email", args=[emailconfirmation.key]
        )

    def send_account_already_exists_mail(self, email):
        # Password recovery is a later feature; don't email an unshipped link.
        self.send_mail("account/email/account_already_exists", email, {
            "login_url": settings.ACCOUNT_PUBLIC_ORIGIN.rstrip("/") + reverse("accounts:login")
        })
