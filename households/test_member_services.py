"""Membership lifecycle invariants, historical preservation and rollback."""
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from allauth.account.models import EmailAddress
from .test_management import ManagementFixture
from .models import Membership, Workspace, HouseholdInvitation
from . import services

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class MemberServiceTests(ManagementFixture,TestCase):
    def assertError(self,code,call):
        with self.assertRaises(services.HouseholdError) as raised:call()
        self.assertEqual(raised.exception.code,code)

    def test_settings_service_validates_and_rechecks_owner(self):
        self.assertError('forbidden',lambda:services.update_household(actor=self.member,name='Hacked',timezone='UTC'))
        with self.assertRaises(ValidationError):services.update_household(actor=self.actor,name=' ',timezone='Invalid/Zone')
        self.actor.workspace.refresh_from_db();self.assertEqual(self.actor.workspace.name,'Maple home')
        Membership.objects.filter(pk=self.actor.pk).update(role='ADULT')
        self.assertError('forbidden',lambda:services.update_household(actor=self.actor,name='Hacked',timezone='UTC'))

    def test_remove_soft_deactivates_and_preserves_records_and_other_households(self):
        own=services.create_household(user=self.roommate,name='Roommate other home',timezone='UTC')
        self.task.created_by_membership=self.member;self.task.save()
        services.remove_member(actor=self.actor,membership_id=self.member.pk)
        self.member.refresh_from_db();self.assertFalse(self.member.is_active)
        self.assertEqual(self.member.user_id,self.roommate.pk)
        self.task.refresh_from_db();self.assertEqual(self.task.created_by_membership_id,self.member.pk)
        self.assertTrue(self.batch.__class__.objects.filter(pk=self.batch.pk).exists())
        own.refresh_from_db();self.assertTrue(own.is_active)
        self.assertEqual(Membership.objects.filter(workspace=self.actor.workspace).count(),2)

    def test_remove_denies_roommate_self_foreign_and_stale_target(self):
        self.assertError('forbidden',lambda:services.remove_member(actor=self.member,membership_id=self.actor.pk))
        self.assertError('self_remove',lambda:services.remove_member(actor=self.actor,membership_id=self.actor.pk))
        self.assertError('not_found',lambda:services.remove_member(actor=self.actor,membership_id=self.other.pk))
        Membership.objects.filter(pk=self.member.pk).update(is_active=False)
        self.assertError('inactive',lambda:services.remove_member(actor=self.actor,membership_id=self.member.pk))

    def test_stale_owner_inactive_owner_null_actor_and_deactivated_account_denied(self):
        for change in [{'role':'ADULT'},{'is_active':False},{'user':None}]:
            Membership.objects.filter(pk=self.actor.pk).update(**change)
            self.assertError('forbidden',lambda:services.remove_member(actor=self.actor,membership_id=self.member.pk))
            Membership.objects.filter(pk=self.actor.pk).update(role='OWNER',is_active=True,user=self.owner)
        get_user_model().objects.filter(pk=self.owner.pk).update(is_active=False)
        self.assertError('forbidden',lambda:services.transfer_ownership(actor=self.actor,membership_id=self.member.pk))
        self.member.refresh_from_db();self.assertTrue(self.member.is_active)

    def test_last_owner_must_transfer_before_leave_even_with_unusable_historical_owners(self):
        self.assertError('last_owner',lambda:services.leave_household(actor=self.actor))
        Membership.objects.create(workspace=self.actor.workspace,display_name='Historical owner',role='OWNER',is_active=True)
        self.assertError('last_owner',lambda:services.leave_household(actor=self.actor))
        blocked=get_user_model().objects.create_user('blocked-owner',is_active=False)
        Membership.objects.create(workspace=self.actor.workspace,user=blocked,display_name='Inactive account owner',role='OWNER')
        self.assertError('last_owner',lambda:services.leave_household(actor=self.actor))
        self.actor.refresh_from_db();self.assertTrue(self.actor.is_active)

    def test_roommate_can_leave_and_owner_can_leave_if_another_active_owner_exists(self):
        services.leave_household(actor=self.member)
        self.member.refresh_from_db();self.assertFalse(self.member.is_active)
        Membership.objects.filter(pk=self.member.pk).update(is_active=True,role='OWNER')
        services.leave_household(actor=self.actor)
        self.actor.refresh_from_db();self.assertFalse(self.actor.is_active)
        self.member.refresh_from_db();self.assertEqual(self.member.role,'OWNER')
        self.assertTrue(self.member.is_active)

    def test_an_owner_can_remove_another_owner_but_cannot_leave_ownerless(self):
        Membership.objects.filter(pk=self.member.pk).update(role='OWNER')
        services.remove_member(actor=self.actor,membership_id=self.member.pk)
        self.assertError('last_owner',lambda:services.leave_household(actor=self.actor))
        self.actor.refresh_from_db();self.assertTrue(self.actor.is_active)

    def test_transfer_applies_both_roles_and_permissions_and_preserves_other_owners(self):
        third=get_user_model().objects.create_user('historical-co-owner')
        co=Membership.objects.create(workspace=self.actor.workspace,user=third,display_name='Co-owner',role='OWNER',can_assign_tasks=False)
        before=Membership.objects.count()
        services.transfer_ownership(actor=self.actor,membership_id=self.member.pk)
        self.actor.refresh_from_db();self.member.refresh_from_db();co.refresh_from_db()
        self.assertEqual(self.actor.role,'ADULT')
        self.assertFalse(self.actor.can_manage_sources)
        self.assertTrue(self.actor.can_assign_tasks and self.actor.can_receive_assignments)
        self.assertEqual(self.member.role,'OWNER')
        self.assertTrue(self.member.can_manage_sources and self.member.can_assign_tasks and self.member.can_receive_assignments)
        self.assertEqual(co.role,'OWNER');self.assertFalse(co.can_assign_tasks)
        self.assertEqual(Membership.objects.count(),before)
        self.assertEqual(Workspace.objects.count(),2)

    def test_transfer_rejects_self_foreign_null_inactive_and_deactivated_target(self):
        self.assertError('self_transfer',lambda:services.transfer_ownership(actor=self.actor,membership_id=self.actor.pk))
        self.assertError('not_found',lambda:services.transfer_ownership(actor=self.actor,membership_id=self.other.pk))
        for change in [{'is_active':False},{'user':None}]:
            Membership.objects.filter(pk=self.member.pk).update(**change)
            self.assertError('invalid_target',lambda:services.transfer_ownership(actor=self.actor,membership_id=self.member.pk))
            Membership.objects.filter(pk=self.member.pk).update(is_active=True,user=self.roommate)
        get_user_model().objects.filter(pk=self.roommate.pk).update(is_active=False)
        self.assertError('invalid_target',lambda:services.transfer_ownership(actor=self.actor,membership_id=self.member.pk))

    def test_transfer_failure_rolls_back_both_memberships(self):
        original=Membership.save
        def fail(member,*args,**kwargs):
            original(member,*args,**kwargs)
            if member.pk==self.actor.pk:raise IntegrityError('Synthetic failure')
        with patch.object(Membership,'save',fail):
            with self.assertRaises(IntegrityError):services.transfer_ownership(actor=self.actor,membership_id=self.member.pk)
        self.actor.refresh_from_db();self.member.refresh_from_db()
        self.assertEqual(self.actor.role,'OWNER');self.assertEqual(self.member.role,'ADULT')
        self.assertTrue(self.actor.can_manage_sources);self.assertFalse(self.member.can_manage_sources)

    def test_remove_and_leave_rollback_preserve_active_history(self):
        for operation in [lambda:services.remove_member(actor=self.actor,membership_id=self.member.pk),lambda:services.leave_household(actor=self.member)]:
            with self.assertRaises(IntegrityError):
                with transaction.atomic():
                    operation();raise IntegrityError('Synthetic outer transaction failure')
            self.member.refresh_from_db();self.assertTrue(self.member.is_active)
            self.assertTrue(self.task.__class__.objects.filter(pk=self.task.pk).exists())

    def test_used_invitation_cannot_restore_removed_member_but_fresh_invitation_can(self):
        EmailAddress.objects.create(user=self.roommate,email=self.roommate.email,verified=True)
        Membership.objects.filter(pk=self.member.pk).update(is_active=False)
        old,token=services.issue_invitation(actor=self.actor,email=self.roommate.email)
        services.accept_invitation(user=self.roommate,raw_token=token)
        services.remove_member(actor=self.actor,membership_id=self.member.pk)
        with self.assertRaises(services.InvitationError) as error:services.accept_invitation(user=self.roommate,raw_token=token)
        self.assertEqual(error.exception.code,'used')
        fresh,new_token=services.issue_invitation(actor=self.actor,email=self.roommate.email)
        restored=services.accept_invitation(user=self.roommate,raw_token=new_token)
        self.assertEqual(restored.pk,self.member.pk);self.assertEqual(restored.role,'ADULT')
        self.assertFalse(restored.can_manage_sources)

    def test_pending_invitations_survive_transfer_and_new_owner_manages_them(self):
        invitation,token=services.issue_invitation(actor=self.actor,email='pending@example.test')
        services.transfer_ownership(actor=self.actor,membership_id=self.member.pk)
        invitation.refresh_from_db();self.assertIsNone(invitation.revoked_at)
        self.assertEqual(invitation.invited_by_id,self.actor.pk)
        with self.assertRaises(services.InvitationError):services.revoke_invitation(actor=self.actor,invitation_id=invitation.pk)
        self.member.refresh_from_db()
        services.revoke_invitation(actor=self.member,invitation_id=invitation.pk)
        invitation.refresh_from_db();self.assertIsNotNone(invitation.revoked_at)
        self.assertTrue(HouseholdInvitation.objects.filter(pk=invitation.pk).exists())
