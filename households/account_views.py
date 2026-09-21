"""Thin UI wrappers; allauth owns password and verification security."""
from smtplib import SMTPException

from django.conf import settings
from django.shortcuts import redirect
from allauth.account.views import ConfirmEmailView as AllauthConfirmEmailView
from allauth.account.views import LoginView as AllauthLoginView
from allauth.account.views import SignupView as AllauthSignupView


class MailFailureMixin:
    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except (SMTPException, OSError):
            # Registration can already exist; retry login to request verification.
            form.add_error(None, "We could not send your verification email. Wait at least 3 minutes, then sign in again to request another email, or contact your administrator.")
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["local_email_preview"] = settings.EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend"
        return context


class LoginView(MailFailureMixin, AllauthLoginView):
    template_name = "registration/login.html"


class SignupView(MailFailureMixin, AllauthSignupView):
    template_name = "registration/signup.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("accounts:login")
        return super().dispatch(request, *args, **kwargs)


class ConfirmEmailView(AllauthConfirmEmailView):
    def logout_other_user(self, confirmation):
        # Visiting a link (including an email scanner) must not end a session.
        if self.request.method == "POST":
            return super().logout_other_user(confirmation)
