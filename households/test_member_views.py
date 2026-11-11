"""Explicit confirmation, real CSRF, selected-household scope and PRG."""
from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse
from .test_management import ManagementFixture
from .models import Membership
from . import services

class MemberActionTests(ManagementFixture,TestCase):
    def action(self,name,member=None):
        return reverse('households:'+name,args=[(member or self.member).pk] if name!='leave' else [])

    def test_detail_explains_actions_without_private_account_information(self):
        page=self.client.get(reverse('households:detail'))
        for text in ['<details','Shared records','other household memberships','become a roommate','confirm','Remove','Transfer ownership','Leave household']:
            self.assertContains(page,text)
        for action in ['remove-member','transfer-owner','leave']:self.assertContains(page,self.action(action))
        for private in [self.owner.email,self.roommate.email]:self.assertNotContains(page,private)
        self.selected(self.roommate)
        page=self.client.get(reverse('households:detail'))
        self.assertContains(page,self.action('leave'))
        self.assertNotContains(page,self.action('remove-member',self.actor))
        self.assertNotContains(page,self.action('transfer-owner',self.actor))

    def test_all_actions_are_post_only_and_confirmation_required(self):
        for name in ['remove-member','transfer-owner','leave']:
            url=self.action(name)
            self.assertEqual(self.client.get(url).status_code,405)
            page=self.client.post(url,follow=True)
            self.assertContains(page,'Confirm')
            self.assertEqual(page.redirect_chain[0][0],reverse('households:detail'))
        self.actor.refresh_from_db();self.member.refresh_from_db()
        self.assertTrue(self.member.is_active);self.assertEqual(self.actor.role,'OWNER')
        self.assertEqual(self.member.role,'ADULT')

    def test_real_csrf_required_for_remove_leave_and_transfer(self):
        secure=self.selected(self.owner,client=Client(enforce_csrf_checks=True))
        for name in ['remove-member','transfer-owner','leave']:
            self.assertEqual(secure.post(self.action(name),{'confirm':'yes'}).status_code,403)
        secure.get(reverse('households:detail'))
        csrf=secure.cookies['csrftoken'].value
        response=secure.post(self.action('transfer-owner'),{'confirm':'yes','csrfmiddlewaretoken':csrf})
        self.assertRedirects(response,reverse('households:detail'))
        response=secure.post(self.action('leave'),{'confirm':'yes','csrfmiddlewaretoken':csrf})
        self.assertRedirects(response,reverse('households:onboarding'))
        secure=self.selected(self.roommate,client=Client(enforce_csrf_checks=True))
        secure.get(reverse('households:detail'));csrf=secure.cookies['csrftoken'].value
        # A different active member can be removed with a valid token.
        target=Membership.objects.create(workspace=self.actor.workspace,user=self.outsider,display_name='Temporary roommate')
        response=secure.post(self.action('remove-member',target),{'confirm':'yes','csrfmiddlewaretoken':csrf})
        self.assertRedirects(response,reverse('households:detail'))
        target.refresh_from_db();self.assertFalse(target.is_active)

    def test_roommate_direct_owner_actions_403_and_foreign_ids_404_even_for_dual_member(self):
        Membership.objects.create(workspace=self.other.workspace,user=self.owner,display_name='Dual owner')
        self.selected(self.owner)
        for name in ['remove-member','transfer-owner']:
            self.assertEqual(self.client.post(self.action(name,self.other),{'confirm':'yes'}).status_code,404)
        self.selected(self.roommate)
        for name in ['remove-member','transfer-owner']:
            self.assertEqual(self.client.post(self.action(name,self.actor),{'confirm':'yes'}).status_code,403)
            self.assertEqual(self.client.post(self.action(name,self.other),{'confirm':'yes'}).status_code,404)

    def test_remove_uses_url_target_not_forged_fields_and_preserves_history(self):
        page=self.client.post(self.action('remove-member'),{'confirm':'yes','membership_id':self.other.pk,'workspace_id':self.other.workspace_id,'role':'OWNER'},follow=True)
        self.assertContains(page,'Shared records remain')
        self.member.refresh_from_db();self.other.refresh_from_db()
        self.assertFalse(self.member.is_active);self.assertTrue(self.other.is_active)
        self.assertTrue(self.task.__class__.objects.filter(pk=self.task.pk).exists())

    def test_sole_owner_leave_blocked_and_self_remove_explained(self):
        self.assertContains(self.client.post(self.action('leave'),{'confirm':'yes'},follow=True),'Transfer ownership')
        self.assertContains(self.client.post(self.action('remove-member',self.actor),{'confirm':'yes'},follow=True),'use Leave household')
        self.actor.refresh_from_db();self.assertTrue(self.actor.is_active)

    def test_transfer_refreshes_capabilities_and_pending_invitation_controls(self):
        response=self.client.post(self.action('transfer-owner'),{'confirm':'yes'},follow=True)
        self.assertContains(response,'You are now a roommate')
        self.assertNotContains(response,reverse('households:settings'))
        self.assertEqual(self.client.get(reverse('households:invites')).status_code,403)
        self.selected(self.roommate)
        self.assertContains(self.client.get(reverse('households:detail')),reverse('households:settings'))
        self.assertEqual(self.client.get(reverse('households:invites')).status_code,200)

    def test_leave_preserves_sign_in_and_zero_one_multiple_remaining_selection(self):
        for count in [0,1,2]:
            with self.subTest(remaining=count):
                Membership.objects.filter(pk=self.member.pk).update(is_active=True)
                self.selected(self.roommate)
                extras=[services.create_household(user=self.roommate,name=f'Other {i}',timezone='UTC') for i in range(count)]
                page=self.client.post(self.action('leave'),{'confirm':'yes'},follow=True)
                expected='households:onboarding' if count==0 else ('task_forms:board' if count==1 else 'households:list')
                self.assertRedirects(page,reverse(expected))
                self.assertContains(page,'You left the household')
                self.assertIn('_auth_user_id',self.client.session)
                self.assertNotIn('active_workspace_id',self.client.session)
                for m in extras:m.refresh_from_db();self.assertTrue(m.is_active)
                # Remove only this subcase's synthetic extra memberships.
                Membership.objects.filter(pk__in=[m.pk for m in extras]).update(is_active=False)

    def test_stale_forms_recheck_actor_and_target_inside_transaction(self):
        real=services.remove_member
        def demote(**kwargs):
            Membership.objects.filter(pk=self.actor.pk).update(role='ADULT')
            return real(**kwargs)
        with patch('households.management_views.remove_member',side_effect=demote):
            self.assertEqual(self.client.post(self.action('remove-member'),{'confirm':'yes'}).status_code,403)
        self.member.refresh_from_db();self.assertTrue(self.member.is_active)
        Membership.objects.filter(pk=self.actor.pk).update(role='OWNER')
        real_transfer=services.transfer_ownership
        def deactivate(**kwargs):
            Membership.objects.filter(pk=self.member.pk).update(is_active=False)
            return real_transfer(**kwargs)
        with patch('households.management_views.transfer_ownership',side_effect=deactivate):
            page=self.client.post(self.action('transfer-owner'),{'confirm':'yes'},follow=True)
        self.assertContains(page,'active member')
        self.actor.refresh_from_db();self.assertEqual(self.actor.role,'OWNER')

    def test_blocked_action_returns_to_canonical_get_so_refresh_is_safe(self):
        response=self.client.post(self.action('leave'),{'confirm':'yes'},follow=True)
        self.assertRedirects(response,reverse('households:detail'))
        page=response
        self.assertEqual(self.client.get(reverse('households:detail')).status_code,200)
        self.assertContains(page,'Transfer ownership')
        self.assertContains(page,'role="alert"')
        self.actor.refresh_from_db();self.assertTrue(self.actor.is_active)
