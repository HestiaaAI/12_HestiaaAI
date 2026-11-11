import re
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client,TestCase,override_settings
from django.urls import reverse
from allauth.account.models import EmailAddress
from .test_invitations import InvitationFixture
from .models import Membership

class InvitationAcceptanceTests(InvitationFixture,TestCase):
    def setUp(self):
        super().setUp()
        self.invitation,self.token=self.issue()
        self.url=reverse('households:accept-invite',args=[self.token])

    def test_anonymous_preview_is_private_generic_and_read_only(self):
        response=self.client.get(self.url)
        self.assertEqual(response.status_code,200)
        self.assertContains(response,reverse('accounts:login'))
        self.assertContains(response,reverse('accounts:signup'))
        self.assertNotContains(response,self.invitation.email)
        self.assertNotContains(response,self.actor.workspace.name)
        self.assertIn('no-store',response['Cache-Control'])
        self.assertEqual(response['Referrer-Policy'],'no-referrer')
        self.assertIn("default-src 'self'",response['Content-Security-Policy'])
        self.assertFalse(Membership.objects.filter(user=self.roommate).exists())
        self.assertEqual(self.client.post(self.url).status_code,302)

    def test_wrong_account_and_invalid_token_do_not_reveal_recipient_or_join(self):
        self.client.force_login(self.owner)
        response=self.client.get(self.url)
        self.assertContains(response,'different email address')
        self.assertNotContains(response,self.invitation.email)
        self.assertNotContains(response,'href="'+reverse('accounts:logout')+'"')
        self.assertEqual(self.client.post(self.url).status_code,403)
        response=self.client.get(reverse('households:accept-invite',args=['malformed']))
        self.assertContains(response,'invalid or no longer available',status_code=404)
        self.assertFalse(Membership.objects.filter(user=self.roommate).exists())

    def test_explicit_verified_accept_selects_household_and_replay_cannot_reactivate(self):
        self.client.force_login(self.roommate)
        self.assertContains(self.client.get(self.url),self.actor.workspace.name)
        self.assertFalse(Membership.objects.filter(user=self.roommate).exists())
        response=self.client.post(self.url)
        self.assertRedirects(response,reverse('task_forms:board'))
        member=Membership.objects.get(user=self.roommate)
        self.assertEqual(member.workspace_id,self.actor.workspace_id)
        self.assertEqual(self.client.session['active_workspace_id'],member.workspace_id)
        self.assertRedirects(self.client.post(self.url),reverse('task_forms:board'))
        Membership.objects.filter(pk=member.pk).update(is_active=False)
        self.assertEqual(self.client.post(self.url).status_code,400)
        member.refresh_from_db();self.assertFalse(member.is_active)

    def test_acceptance_requires_real_csrf_token(self):
        client=Client(enforce_csrf_checks=True);client.force_login(self.roommate)
        self.assertEqual(client.post(self.url).status_code,403)
        client.get(self.url)
        self.assertRedirects(client.post(self.url,{'csrfmiddlewaretoken':client.cookies['csrftoken'].value}),reverse('task_forms:board'))

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',ACCOUNT_EMAIL_VERIFICATION='none')
    def test_optional_signup_verification_still_required_for_invitation(self):
        EmailAddress.objects.filter(user=self.roommate).update(verified=False)
        self.client.force_login(self.roommate)
        self.assertEqual(self.client.post(self.url).status_code,403)
        response=self.client.post(self.url,{'action':'verify'})
        self.assertRedirects(response,self.url)
        self.assertEqual(len(mail.outbox),1)
        confirmation=re.search(r'https?://[^\s]+(/accounts/confirm-email/[^\s]+)',mail.outbox[0].body).group(1)
        self.client.get(confirmation)
        self.assertFalse(EmailAddress.objects.get(user=self.roommate).verified)
        self.client.post(confirmation)
        self.assertTrue(EmailAddress.objects.get(user=self.roommate).verified)
        response=self.client.get(self.url)
        self.assertContains(response,'Join household')
        self.client.post(self.url)
        self.assertTrue(Membership.objects.filter(user=self.roommate,is_active=True).exists())

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',ACCOUNT_EMAIL_VERIFICATION='mandatory',ACCOUNT_SIGNUP_FIELDS=['email*','password1*','password2*'],ACCOUNT_LOGIN_METHODS={'email'})
    def test_full_signup_verify_login_explicit_accept_chain(self):
        self.roommate.delete()
        response=self.client.get(self.url)
        password='New-roommate-passphrase-927!'
        response=self.client.post(reverse('accounts:signup')+'?next='+self.url,{'email':'roommate@example.test','password1':password,'password2':password,'next':self.url})
        user=get_user_model().objects.get(email='roommate@example.test')
        self.assertNotIn('_auth_user_id',self.client.session)
        self.assertFalse(Membership.objects.filter(user=user).exists())
        confirmation=re.search(r'https?://[^\s]+(/accounts/confirm-email/[^\s]+)',mail.outbox[0].body).group(1)
        self.client.get(confirmation)
        self.assertFalse(EmailAddress.objects.get(user=user).verified)
        response=self.client.post(confirmation,follow=True)
        self.assertNotIn('_auth_user_id',self.client.session)
        response=self.client.post(reverse('accounts:login'),{'login':user.email,'password':password},follow=True)
        self.assertEqual(response.request['PATH_INFO'],self.url)
        self.assertContains(response,'Join household')
        self.assertFalse(Membership.objects.filter(user=user).exists())
        self.assertRedirects(self.client.post(self.url),reverse('task_forms:board'))
        self.assertEqual(Membership.objects.get(user=user).workspace_id,self.actor.workspace_id)

    def test_revoked_or_expired_tokens_cannot_join(self):
        from django.utils import timezone
        self.client.force_login(self.roommate)
        from .models import HouseholdInvitation
        HouseholdInvitation.objects.filter(pk=self.invitation.pk).update(expires_at=timezone.now())
        self.assertEqual(self.client.post(self.url).status_code,400)
        HouseholdInvitation.objects.filter(pk=self.invitation.pk).update(revoked_at=timezone.now())
        self.assertEqual(self.client.post(self.url).status_code,400)
        self.assertFalse(Membership.objects.filter(user=self.roommate).exists())
