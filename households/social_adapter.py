"""Allow a verified Google identity to join while password signup is closed."""
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class GoogleSocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin):
        if sociallogin.account.provider == "google":
            return any(address.verified for address in sociallogin.email_addresses)
        return super().is_open_for_signup(request, sociallogin)
