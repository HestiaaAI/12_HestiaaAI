from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase,Client,override_settings
from django.urls import reverse
from django.core.cache import cache
from .test_invitations import InvitationFixture
from .models import Membership,HouseholdInvitation
from .services import create_household

class OwnerInvitationTests(InvitationFixture,TestCase):
    def setUp(self):
        super().setUp();self.client.force_login(self.owner)

    def payload(self,email=None):
        page=self.client.get(reverse('households:invites'))
        return {'email':email or self.roommate.email,'nonce':page.context['form'].initial['nonce']}

    def test_get_is_read_only_and_only_owner_can_manage(self):
        self.assertContains(self.client.get(reverse('households:invites')),'Invite a roommate')
        self.assertFalse(HouseholdInvitation.objects.exists())
        Membership.objects.create(workspace=self.actor.workspace,user=self.roommate,display_name='Roommate')
        self.client.force_login(self.roommate)
        self.assertEqual(self.client.get(reverse('households:invites')).status_code,403)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('households:invites')).status_code,302)

    @override_settings(ACCOUNT_PUBLIC_ORIGIN='https://hestia.example.test')
    def test_issue_shows_trusted_copy_link_only_once_and_replay_does_not_issue(self):
        data=self.payload()
        response=self.client.post(reverse('households:invites'),{**data,'role':'OWNER','workspace_id':99999})
        self.assertEqual(response.status_code,200)
        url=response.context['invite_url']
        self.assertTrue(url.startswith('https://hestia.example.test/households/invites/'))
        self.assertContains(response,'readonly')
        self.assertEqual(HouseholdInvitation.objects.count(),1)
        self.assertNotContains(self.client.get(reverse('households:invites')),url)
        response=self.client.post(reverse('households:invites'),data)
        self.assertEqual(response.status_code,409)
        self.assertEqual(HouseholdInvitation.objects.count(),1)
        self.assertIsNone(HouseholdInvitation.objects.get().revoked_at)
        self.assertNotIn(url,str(dict(self.client.session)))
        cache.clear()
        self.assertEqual(self.client.post(reverse('households:invites'),data).status_code,409)
        self.assertEqual(HouseholdInvitation.objects.count(),1)

    def test_foreign_invitation_ids_return_404_and_get_mutations_405(self):
        other=create_household(user=self.owner,name='Other',timezone='UTC')
        self.client.post(reverse('households:switch'),{'workspace_id':self.actor.workspace_id})
        from .services import issue_invitation
        invitation,token=issue_invitation(actor=other,email='foreign@example.test')
        for name in ['households:revoke-invite','households:resend-invite']:
            url=reverse(name,args=[invitation.pk])
            self.assertEqual(self.client.post(url,{'nonce':self.payload()['nonce']}).status_code,404)
        own,token=self.issue()
        for name in ['households:revoke-invite','households:resend-invite']:
            self.assertEqual(self.client.get(reverse(name,args=[own.pk])).status_code,405)

    def test_csrf_nonce_and_current_ownership_required(self):
        secure=Client(enforce_csrf_checks=True);secure.force_login(self.owner)
        url=reverse('households:invites')
        self.assertEqual(secure.post(url,{'email':self.roommate.email}).status_code,403)
        data=self.payload()
        self.assertEqual(self.client.post(url,{'email':self.roommate.email,'nonce':'forged'}).status_code,400)
        Membership.objects.filter(pk=self.actor.pk).update(role='ADULT')
        self.assertEqual(self.client.post(url,data).status_code,403)
        self.assertFalse(HouseholdInvitation.objects.exists())

    def test_resend_invalidates_old_link_and_revoke_blocks_join(self):
        invitation,token=self.issue()
        url=reverse('households:resend-invite',args=[invitation.pk])
        response=self.client.post(url,{'nonce':self.payload()['nonce']})
        self.assertEqual(response.status_code,200)
        invitation.refresh_from_db();self.assertIsNotNone(invitation.revoked_at)
        newer=HouseholdInvitation.objects.exclude(pk=invitation.pk).get()
        self.assertRedirects(self.client.post(reverse('households:revoke-invite',args=[newer.pk])),reverse('households:invites'))
        newer.refresh_from_db();self.assertIsNotNone(newer.revoked_at)

    def test_recipient_and_actor_issuance_limits(self):
        data=self.payload()
        self.assertEqual(self.client.post(reverse('households:invites'),data).status_code,200)
        self.assertEqual(self.client.post(reverse('households:invites'),self.payload()).status_code,429)
        self.assertEqual(HouseholdInvitation.objects.count(),1)
        cache.clear()
        for index in range(10):
            self.assertEqual(self.client.post(reverse('households:invites'),self.payload(f'invite{index}@example.test')).status_code,200)
        self.assertEqual(self.client.post(reverse('households:invites'),self.payload('limit@example.test')).status_code,429)

    def test_dual_member_nonce_cannot_target_other_selected_household(self):
        other=create_household(user=self.owner,name='Other',timezone='UTC')
        # Select first explicitly because this user is now dual-member.
        self.client.post(reverse('households:switch'),{'workspace_id':self.actor.workspace_id})
        data=self.payload()
        self.client.post(reverse('households:switch'),{'workspace_id':other.workspace_id})
        self.assertEqual(self.client.post(reverse('households:invites'),data).status_code,400)
        self.assertFalse(HouseholdInvitation.objects.exists())

    def test_ownership_loss_inside_issue_transaction_is_denied(self):
        from .services import issue_invitation
        data=self.payload()
        def changed(**kwargs):
            Membership.objects.filter(pk=self.actor.pk).update(role='ADULT')
            return issue_invitation(**kwargs)
        with patch('households.invitation_views.issue_invitation',side_effect=changed):
            self.assertEqual(self.client.post(reverse('households:invites'),data).status_code,403)
        self.assertFalse(HouseholdInvitation.objects.exists())

    def test_owner_mutations_accept_real_csrf_and_reject_missing_tokens(self):
        secure=Client(enforce_csrf_checks=True);secure.force_login(self.owner)
        listing=reverse('households:invites')
        page=secure.get(listing)
        csrf=secure.cookies['csrftoken'].value
        payload={'email':self.roommate.email,'nonce':page.context['form'].initial['nonce'],'csrfmiddlewaretoken':csrf}
        self.assertEqual(secure.post(listing,payload,HTTP_ORIGIN='http://testserver').status_code,200)
        original=HouseholdInvitation.objects.get()
        resend=reverse('households:resend-invite',args=[original.pk])
        revoke=reverse('households:revoke-invite',args=[original.pk])
        self.assertEqual(secure.post(resend).status_code,403)
        self.assertEqual(secure.post(revoke).status_code,403)
        cache.clear()
        page=secure.get(listing)
        self.assertEqual(secure.post(resend,{'nonce':page.context['form'].initial['nonce'],'csrfmiddlewaretoken':csrf},HTTP_ORIGIN='http://testserver').status_code,200)
        newer=HouseholdInvitation.objects.exclude(pk=original.pk).get()
        response=secure.post(reverse('households:revoke-invite',args=[newer.pk]),{'csrfmiddlewaretoken':csrf},HTTP_ORIGIN='http://testserver')
        self.assertEqual(response.status_code,302)
        newer.refresh_from_db();self.assertIsNotNone(newer.revoked_at)
        self.assertEqual(secure.post(listing,payload,HTTP_ORIGIN='https://attacker.example').status_code,403)
