"""Invitation state/identity rules using real database writes."""
import hashlib
from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from allauth.account.models import EmailAddress
from .models import Membership, HouseholdInvitation
from .services import create_household, issue_invitation, accept_invitation, revoke_invitation, InvitationError

class InvitationFixture:
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.owner=get_user_model().objects.create_user('invite-owner',email='owner@example.test')
        self.actor=create_household(user=self.owner,name='Maple private home',timezone='America/Chicago')
        self.roommate=get_user_model().objects.create_user('invite-roommate',email='roommate@example.test')
        EmailAddress.objects.create(user=self.roommate,email=self.roommate.email,verified=True,primary=True)

    def issue(self,email=None):
        return issue_invitation(actor=self.actor,email=email or self.roommate.email)

    def assertCode(self,code,call):
        with self.assertRaises(InvitationError) as raised:call()
        self.assertEqual(raised.exception.code,code)

class InvitationServiceTests(InvitationFixture,TestCase):
    def test_digest_entropy_normalization_and_seven_day_expiry(self):
        invitation,token=self.issue(' ROOMMATE@EXAMPLE.TEST ')
        self.assertGreaterEqual(len(token),43)
        self.assertEqual(invitation.token_digest,hashlib.sha256(token.encode()).hexdigest())
        self.assertNotIn(token,str(HouseholdInvitation.objects.values().get(pk=invitation.pk)))
        self.assertEqual(invitation.email,'roommate@example.test')
        self.assertAlmostEqual((invitation.expires_at-invitation.created_at).total_seconds(),7*86400,delta=2)
        self.assertTrue(timezone.is_aware(invitation.expires_at))
        self.assertEqual(invitation.status,'pending')

    def test_owner_is_rechecked_and_nullable_or_roommate_actors_denied(self):
        for changes in [{'role':'ADULT'},{'is_active':False},{'user':None}]:
            Membership.objects.filter(pk=self.actor.pk).update(**changes)
            self.assertCode('forbidden',self.issue)
            Membership.objects.filter(pk=self.actor.pk).update(role='OWNER',is_active=True,user=self.owner)
        self.assertFalse(HouseholdInvitation.objects.exists())

    def test_invalid_email_and_already_active_member(self):
        self.assertCode('invalid_email',lambda:self.issue('not-an-email'))
        Membership.objects.create(user=self.roommate,workspace=self.actor.workspace,display_name='Roommate')
        self.assertCode('already_member',self.issue)
        self.assertFalse(HouseholdInvitation.objects.exists())

    def test_reissue_revokes_old_pending_only_in_this_household(self):
        first,old=self.issue()
        another=create_household(user=self.owner,name='Other house',timezone='UTC')
        other,other_token=issue_invitation(actor=another,email=self.roommate.email)
        second,new=self.issue()
        first.refresh_from_db();other.refresh_from_db()
        self.assertIsNotNone(first.revoked_at)
        self.assertIsNone(other.revoked_at)
        self.assertNotEqual(old,new)
        self.assertCode('revoked',lambda:accept_invitation(user=self.roommate,raw_token=old))
        self.assertEqual(accept_invitation(user=self.roommate,raw_token=new).workspace_id,second.workspace_id)

    def test_matching_verified_email_required_not_user_email(self):
        invitation,token=self.issue()
        EmailAddress.objects.filter(user=self.roommate).update(verified=False)
        self.assertCode('email_unverified',lambda:accept_invitation(user=self.roommate,raw_token=token))
        EmailAddress.objects.filter(user=self.roommate).delete()
        self.assertCode('email_unverified',lambda:accept_invitation(user=self.roommate,raw_token=token))
        self.assertCode('authentication_required',lambda:accept_invitation(user=AnonymousUser(),raw_token=token))
        self.assertCode('wrong_email',lambda:accept_invitation(user=self.owner,raw_token=token))
        self.assertFalse(Membership.objects.filter(user=self.roommate).exists())

    def test_verified_secondary_email_is_sufficient(self):
        invitation,token=self.issue()
        self.roommate.email='different@example.test';self.roommate.save(update_fields=['email'])
        member=accept_invitation(user=self.roommate,raw_token=token)
        self.assertEqual(member.workspace_id,invitation.workspace_id)
        self.assertEqual(member.role,'ADULT')
        self.assertTrue(member.can_assign_tasks and member.can_receive_assignments)
        self.assertFalse(member.can_manage_sources)
        self.assertEqual(member.get_role_display(),'Roommate')

    def test_malformed_expired_boundary_and_revoked_cannot_join(self):
        invitation,token=self.issue()
        self.assertCode('invalid',lambda:accept_invitation(user=self.roommate,raw_token='bad'))
        with patch('households.services.timezone.now',return_value=invitation.expires_at):
            self.assertCode('expired',lambda:accept_invitation(user=self.roommate,raw_token=token))
        revoke_invitation(actor=self.actor,invitation_id=invitation.pk)
        self.assertCode('revoked',lambda:accept_invitation(user=self.roommate,raw_token=token))
        self.assertFalse(Membership.objects.filter(user=self.roommate).exists())

    def test_active_membership_is_not_duplicated_or_downgraded(self):
        invitation,token=self.issue()
        existing=Membership.objects.create(user=self.roommate,workspace=self.actor.workspace,display_name='Owner',role='OWNER',can_manage_sources=True)
        self.assertEqual(accept_invitation(user=self.roommate,raw_token=token).pk,existing.pk)
        existing.refresh_from_db();self.assertEqual(existing.role,'OWNER');self.assertTrue(existing.can_manage_sources)

    def test_inactive_owner_reinvite_resets_ordinary_permissions(self):
        old=Membership.objects.create(user=self.roommate,workspace=self.actor.workspace,display_name='Former owner',role='OWNER',can_manage_sources=True,is_active=False)
        invitation,token=self.issue()
        member=accept_invitation(user=self.roommate,raw_token=token)
        self.assertEqual(member.pk,old.pk)
        self.assertEqual(member.role,'ADULT')
        self.assertFalse(member.can_manage_sources)
        self.assertTrue(member.is_active and member.can_assign_tasks and member.can_receive_assignments)

    def test_used_token_never_reactivates_removed_member(self):
        invitation,token=self.issue()
        member=accept_invitation(user=self.roommate,raw_token=token)
        self.assertEqual(accept_invitation(user=self.roommate,raw_token=token).pk,member.pk)
        Membership.objects.filter(pk=member.pk).update(is_active=False)
        self.assertCode('used',lambda:accept_invitation(user=self.roommate,raw_token=token))
        member.refresh_from_db();self.assertFalse(member.is_active)

    def test_historical_null_user_membership_is_never_attached(self):
        old=Membership.objects.create(workspace=self.actor.workspace,display_name=self.roommate.username)
        invitation,token=self.issue()
        member=accept_invitation(user=self.roommate,raw_token=token)
        self.assertNotEqual(member.pk,old.pk)
        old.refresh_from_db();self.assertIsNone(old.user_id)

    def test_foreign_revoke_and_ownership_loss_are_denied(self):
        invitation,token=self.issue()
        other=create_household(user=self.owner,name='Other',timezone='UTC')
        self.assertCode('not_found',lambda:revoke_invitation(actor=other,invitation_id=invitation.pk))
        Membership.objects.filter(pk=self.actor.pk).update(role='ADULT')
        self.assertCode('forbidden',lambda:revoke_invitation(actor=self.actor,invitation_id=invitation.pk))
        invitation.refresh_from_db();self.assertIsNone(invitation.revoked_at)

    def test_acceptance_rollback_preserves_pending_invitation(self):
        invitation,token=self.issue()
        with patch('households.services.Membership.objects.create',side_effect=IntegrityError('Synthetic failure')):
            with self.assertRaises(IntegrityError):accept_invitation(user=self.roommate,raw_token=token)
        invitation.refresh_from_db();self.assertIsNone(invitation.accepted_at)
        self.assertFalse(Membership.objects.filter(user=self.roommate).exists())

    def test_failed_reissue_rolls_back_revocation(self):
        first,token=self.issue()
        with patch('households.services.HouseholdInvitation.objects.create',side_effect=IntegrityError('Synthetic failure')):
            with self.assertRaises(IntegrityError):self.issue()
        first.refresh_from_db();self.assertIsNone(first.revoked_at)
        self.assertEqual(HouseholdInvitation.objects.count(),1)

# Row-lock proof is intentionally database-specific, never claimed from SQLite.
from unittest import skipUnless
from django.db import connection, close_old_connections, connections
from django.test import TransactionTestCase

@skipUnless(connection.vendor == 'postgresql','PostgreSQL required for concurrent row-lock proof')
class InvitationConcurrencyTests(InvitationFixture,TransactionTestCase):
    def test_simultaneous_acceptance_creates_one_membership(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        invitation,token=self.issue()
        barrier=Barrier(2)
        user_id=self.roommate.pk
        def accept():
            close_old_connections()
            try:
                user=get_user_model().objects.get(pk=user_id)
                barrier.wait(timeout=10)
                return accept_invitation(user=user,raw_token=token).pk
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(accept) for _ in range(2)]
            ids=[f.result(timeout=20) for f in futures]
        self.assertEqual(ids[0],ids[1])
        self.assertEqual(Membership.objects.filter(user=self.roommate,workspace=invitation.workspace).count(),1)
