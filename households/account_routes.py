"""Allauth's internal reverse names, restricted to the shipped account flow.

The accounts namespace in auth_urls remains the public project interface.
"""
from allauth.account import views
from django.urls import path
from django.contrib.auth.views import LogoutView
from .account_views import ConfirmEmailView, LoginView, SignupView

urlpatterns = [
    path("login/", LoginView.as_view(), name="account_login"),
    path("signup/", SignupView.as_view(), name="account_signup"),
    path("logout/", LogoutView.as_view(next_page="accounts:login"), name="account_logout"),
    path("confirm-email/", views.EmailVerificationSentView.as_view(), name="account_email_verification_sent"),
    path("confirm-email/<str:key>/", ConfirmEmailView.as_view(), name="account_confirm_email"),
    path("inactive/", views.AccountInactiveView.as_view(), name="account_inactive"),
]
