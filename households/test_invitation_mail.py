from smtplib import SMTPException
from unittest.mock import patch
from django.core import mail
from django.db import transaction,IntegrityError
from django.test import TestCase,override_settings
from django.urls import reverse
from .test_invitations import InvitationFixture
from .models import HouseholdInvitation
from .services import issue_invitation,accept_invitation

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',ACCOUNT_PUBLIC_ORIGIN='https://trusted.example.test')
class InvitationMailTests(InvitationFixture,TestCase):
    def test_delivery_is_after_commit_to_intended_address_with_trusted_link(self):
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            invitation,token=self.issue()
            self.assertEqual(len(mail.outbox),0)
        self.assertEqual(len(callbacks),1)
        callbacks[0]()
        self.assertEqual(len(mail.outbox),1)
        self.assertEqual(mail.outbox[0].to,[self.roommate.email])
        self.assertIn('https://trusted.example.test'+reverse('households:accept-invite',args=[token]),mail.outbox[0].body)
        self.assertEqual(invitation.delivery_status,'sent')

    def test_smtp_failure_keeps_valid_copy_link_and_honest_status(self):
        with patch('households.invitation_mail.send_mail',side_effect=SMTPException('Private provider detail')):
            with self.captureOnCommitCallbacks(execute=True):invitation,token=self.issue()
        self.assertEqual(invitation.delivery_status,'failed')
        self.assertTrue(HouseholdInvitation.objects.filter(pk=invitation.pk).exists())
        self.assertEqual(accept_invitation(user=self.roommate,raw_token=token).workspace_id,invitation.workspace_id)

    def test_rollback_sends_nothing_and_superseded_link_not_delivered(self):
        with self.captureOnCommitCallbacks(execute=True):
            try:
                with transaction.atomic():
                    self.issue();raise IntegrityError('Rollback fixture')
            except IntegrityError:pass
        self.assertEqual(len(mail.outbox),0)
        with self.captureOnCommitCallbacks(execute=True):
            first,old=self.issue()
            second,new=self.issue()
        self.assertEqual(len(mail.outbox),1)
        self.assertNotIn(old,mail.outbox[0].body)
        self.assertIn(new,mail.outbox[0].body)

    def test_owner_get_and_failure_message_do_not_claim_delivery(self):
        self.client.force_login(self.owner)
        page=self.client.get(reverse('households:invites'))
        with patch('households.invitation_mail.send_mail',side_effect=SMTPException('Secret diagnostic')):
            # Direct TestCase request remains inside outer transaction: response
            # honestly says queued, then the callback records the failure.
            with self.captureOnCommitCallbacks(execute=True):
                response=self.client.post(reverse('households:invites'),{'email':self.roommate.email,'nonce':page.context['form'].initial['nonce']})
        self.assertContains(response,'Copy invitation link')
        self.assertNotContains(response,'Email delivered')
        self.assertNotContains(response,'Secret diagnostic')

from django.test import TransactionTestCase

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class InvitationDeliveryResponseTests(InvitationFixture,TransactionTestCase):
    def test_actual_post_commit_failure_response_retains_copy_link(self):
        self.client.force_login(self.owner)
        page=self.client.get(reverse('households:invites'))
        with patch('households.invitation_mail.send_mail',side_effect=SMTPException('Hidden SMTP details')):
            response=self.client.post(reverse('households:invites'),{'email':self.roommate.email,'nonce':page.context['form'].initial['nonce']})
        self.assertContains(response,'Email could not be sent')
        self.assertContains(response,'Copy invitation link')
        self.assertNotContains(response,'Hidden SMTP details')
        self.assertEqual(HouseholdInvitation.objects.count(),1)
