"""Post-commit invitation mail; never print bearer links to preview logs."""
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables


def console_preview_backend():
    return settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend'


@sensitive_variables()
def schedule_invitation_email(invitation, raw_token):
    invitation.delivery_status='queued'
    @sensitive_variables()
    def deliver():
        from .models import HouseholdInvitation
        if not HouseholdInvitation.objects.filter(pk=invitation.pk,revoked_at__isnull=True,accepted_at__isnull=True,expires_at__gt=timezone.now()).exists():
            invitation.delivery_status='superseded'
            return
        if console_preview_backend():
            invitation.delivery_status='copy_only'
            return
        url=settings.ACCOUNT_PUBLIC_ORIGIN.rstrip('/')+reverse('households:accept-invite',args=[raw_token])
        try:
            sent=send_mail('Your Hestia household invitation',
                'You are invited to join a Hestia household. Sign in or create an account using this email, verify it, and explicitly accept:\n\n'+url+'\n\nThis link expires in seven days. If this was unexpected, ignore it.',
                settings.DEFAULT_FROM_EMAIL,[invitation.email])
        except Exception:
            # Do not log SMTP exceptions: they may embed recipients or message bodies.
            invitation.delivery_status='failed'
        else:
            invitation.delivery_status='sent' if sent else 'failed'
    transaction.on_commit(deliver)
