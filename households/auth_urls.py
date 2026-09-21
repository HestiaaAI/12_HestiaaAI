"""Account routes use Django's authentication views and validation."""
from django.contrib.auth.views import LogoutView
from .account_views import LoginView, SignupView
from django.urls import path

app_name = "accounts"

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("logout/", LogoutView.as_view(next_page="accounts:login"), name="logout"),
    path("login/", LoginView.as_view(template_name="registration/login.html"), name="login"),
]
