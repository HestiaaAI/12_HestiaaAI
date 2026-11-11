"""PostgreSQL-only race proof; SQLite is explicitly not a locking substitute."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from django.db import connection, close_old_connections, connections
from django.db.models import Count
from django.test import TransactionTestCase, override_settings
from allauth.account.models import EmailAddress
from .test_management import ManagementFixture
from .models import Membership
from . import services

@skipUnless(connection.vendor=='postgresql','PostgreSQL required: workspace/membership row-lock races are unverified on SQLite')
@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class MemberConcurrencyTests(ManagementFixture,TransactionTestCase):
    def race(self, first, second):
        barrier=Barrier(2)
        def run(operation):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:operation();return 'ok'
                except (services.HouseholdError,services.InvitationError) as error:return error.code
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(run,operation) for operation in [first,second]]
            results=[future.result(timeout=20) for future in futures]
        owners=Membership.objects.filter(workspace=self.actor.workspace,is_active=True,role='OWNER',user__is_active=True)
        self.assertGreaterEqual(owners.count(),1)
        self.assertFalse(Membership.objects.exclude(user=None).values('workspace_id','user_id').annotate(n=Count('pk')).filter(n__gt=1).exists())
        self.assertIn('ok',results)
        return results

    def test_concurrent_owner_departures_cannot_remove_last_owner(self):
        Membership.objects.filter(pk=self.member.pk).update(role='OWNER')
        results=self.race(lambda:services.leave_household(actor=self.actor),lambda:services.leave_household(actor=self.member))
        self.assertCountEqual(results,['ok','last_owner'])
        self.assertEqual(Membership.objects.filter(workspace=self.actor.workspace,is_active=True).count(),1)

    def test_concurrent_owner_removals_leave_one_active_owner(self):
        Membership.objects.filter(pk=self.member.pk).update(role='OWNER')
        results=self.race(lambda:services.remove_member(actor=self.actor,membership_id=self.member.pk),lambda:services.remove_member(actor=self.member,membership_id=self.actor.pk))
        self.assertCountEqual(results,['ok','forbidden'])
        self.assertEqual(Membership.objects.filter(workspace=self.actor.workspace,is_active=True,role='OWNER').count(),1)

    def test_transfer_racing_with_target_leave_preserves_owner(self):
        self.race(lambda:services.transfer_ownership(actor=self.actor,membership_id=self.member.pk),lambda:services.leave_household(actor=self.member))
        self.actor.refresh_from_db();self.member.refresh_from_db()
        if self.member.is_active:
            self.assertEqual(self.member.role,'OWNER');self.assertEqual(self.actor.role,'ADULT')
        else:self.assertEqual(self.actor.role,'OWNER')

    def test_transfer_racing_with_actor_removing_target_rechecks_actor(self):
        self.race(lambda:services.transfer_ownership(actor=self.actor,membership_id=self.member.pk),lambda:services.remove_member(actor=self.actor,membership_id=self.member.pk))
        self.actor.refresh_from_db();self.member.refresh_from_db()
        if self.member.is_active:
            self.assertEqual(self.member.role,'OWNER');self.assertEqual(self.actor.role,'ADULT')
        else:self.assertEqual(self.actor.role,'OWNER')

    def test_transfer_racing_with_invitation_issuance_is_authorized_at_its_lock(self):
        results=self.race(lambda:services.transfer_ownership(actor=self.actor,membership_id=self.member.pk),lambda:services.issue_invitation(actor=self.actor,email='race@example.test'))
        invitations=self.actor.workspace.invitations.filter(email='race@example.test')
        self.assertEqual(invitations.count(),1 if results.count('ok')==2 else 0)
        if invitations.exists():self.assertEqual(invitations.get().invited_by_id,self.actor.pk)
        self.actor.refresh_from_db();self.assertEqual(self.actor.role,'ADULT')

    def test_removal_racing_with_fresh_acceptance_never_duplicates_or_restores_owner(self):
        EmailAddress.objects.create(user=self.roommate,email=self.roommate.email,verified=True)
        Membership.objects.filter(pk=self.member.pk).update(is_active=False,role='OWNER',can_manage_sources=True)
        invitation,token=services.issue_invitation(actor=self.actor,email=self.roommate.email)
        Membership.objects.filter(pk=self.member.pk).update(is_active=True,role='ADULT',can_manage_sources=False)
        self.race(lambda:services.remove_member(actor=self.actor,membership_id=self.member.pk),lambda:services.accept_invitation(user=self.roommate,raw_token=token))
        self.member.refresh_from_db();invitation.refresh_from_db()
        self.assertEqual(self.member.role,'ADULT');self.assertFalse(self.member.can_manage_sources)
        self.assertIsNotNone(invitation.accepted_at)
        self.assertEqual(Membership.objects.filter(user=self.roommate,workspace=self.actor.workspace).count(),1)

    def test_removal_racing_with_used_acceptance_never_reactivates(self):
        EmailAddress.objects.create(user=self.roommate,email=self.roommate.email,verified=True)
        Membership.objects.filter(pk=self.member.pk).update(is_active=False)
        invitation,token=services.issue_invitation(actor=self.actor,email=self.roommate.email)
        services.accept_invitation(user=self.roommate,raw_token=token)
        self.race(lambda:services.remove_member(actor=self.actor,membership_id=self.member.pk),lambda:services.accept_invitation(user=self.roommate,raw_token=token))
        self.member.refresh_from_db();self.assertFalse(self.member.is_active)
