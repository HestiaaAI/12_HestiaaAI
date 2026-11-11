"""Canonical household settings and fresh administrative authorization."""
from datetime import datetime, timezone as dt_timezone
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from households.models import Membership, Workspace
from households.services import create_household
from workflows.models import Task
from inventory.models import GroceryBatch

class ManagementFixture:
    def setUp(self):
        self.owner=get_user_model().objects.create_user('manage-owner',email='owner-private@example.test')
        self.actor=create_household(user=self.owner,name='Maple home',timezone='America/Chicago')
        self.roommate=get_user_model().objects.create_user('manage-roommate',email='roommate-private@example.test')
        self.member=Membership.objects.create(workspace=self.actor.workspace,user=self.roommate,display_name='Maple roommate',role='ADULT',can_assign_tasks=True)
        self.outsider=get_user_model().objects.create_user('manage-outsider',email='outsider@example.test')
        self.other=create_household(user=self.outsider,name='Other secret household',timezone='UTC')
        self.task=Task.objects.create(workspace=self.actor.workspace,created_by_membership=self.actor,title='Shared Maple task')
        self.batch=GroceryBatch.objects.create(workspace=self.actor.workspace,name='Maple milk',quantity=1,expires_on='2026-01-04')
        Task.objects.create(workspace=self.other.workspace,title='Other secret task')
        GroceryBatch.objects.create(workspace=self.other.workspace,name='Other secret groceries',quantity=1)
        self.client.force_login(self.owner)

    def selected(self, user, workspace=None, client=None):
        client=client or self.client
        client.force_login(user)
        session=client.session
        session['active_workspace_id']=(workspace or self.actor.workspace).pk
        session.save()
        return client

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class HouseholdSettingsTests(ManagementFixture,TestCase):
    def test_canonical_detail_scoped_roster_roles_navigation_and_private_fields(self):
        page=self.client.get(reverse('households:detail'),{'workspace':self.other.workspace_id})
        self.assertContains(page,'Maple home')
        self.assertContains(page,'Maple roommate')
        self.assertContains(page,'Owner')
        self.assertContains(page,'Roommate')
        self.assertContains(page,'America/Chicago')
        self.assertContains(page,reverse('households:settings'))
        self.assertContains(page,reverse('households:invites'))
        self.assertNotContains(page,self.other.workspace.name)
        for private in [self.owner.email,self.roommate.email,self.outsider.email]:self.assertNotContains(page,private)
        self.assertContains(page,'href="'+reverse('households:detail')+'"')
        self.assertNotContains(page,'href="'+reverse('groceries:household')+'"')

    def test_old_roster_is_thin_redirect_and_requires_selection(self):
        self.assertRedirects(self.client.get(reverse('groceries:household'),{'workspace':self.other.workspace_id}),reverse('households:detail'))
        self.client.logout()
        self.assertEqual(self.client.get(reverse('households:detail')).status_code,302)
        self.client.force_login(self.outsider)
        Membership.objects.filter(pk=self.other.pk).update(is_active=False)
        self.assertRedirects(self.client.get(reverse('households:detail')),reverse('households:onboarding'))

    def test_roommate_shared_content_parity_without_administration_or_emails(self):
        from households.services import issue_invitation
        issue_invitation(actor=self.actor,email='invitation-private@example.test')
        for user in [self.owner,self.roommate]:
            self.selected(user)
            page=self.client.get(reverse('households:detail'))
            for private in [self.owner.email,self.roommate.email,'invitation-private@example.test','Other secret']:self.assertNotContains(page,private)
            self.assertContains(self.client.get(reverse('task_forms:board')),self.task.title)
            self.assertNotContains(self.client.get(reverse('task_forms:board')),'Other secret task')
            self.assertContains(self.client.get(reverse('groceries:list'),follow=True),self.batch.name)
            self.assertNotContains(self.client.get(reverse('groceries:list'),follow=True),'Other secret groceries')
            if user==self.roommate:
                self.assertNotContains(page,reverse('households:settings'))
                self.assertNotContains(page,reverse('households:invites'))

    def test_owner_updates_only_validated_name_and_timezone_with_prg(self):
        before=self.actor.workspace.created_at
        page=self.client.get(reverse('households:settings'))
        self.assertContains(page,'Maple home')
        response=self.client.post(reverse('households:settings'),{'name':'  Renamed Maple  ','timezone':'Pacific/Honolulu','workspace_id':self.other.workspace_id,'workspace_type':'TEAM','role':'ADULT','can_manage_sources':False})
        self.assertRedirects(response,reverse('households:detail'))
        self.actor.workspace.refresh_from_db();self.actor.refresh_from_db()
        self.assertEqual(self.actor.workspace.name,'Renamed Maple')
        self.assertEqual(self.actor.workspace.timezone,'Pacific/Honolulu')
        self.assertEqual(self.actor.workspace.workspace_type,'HOUSEHOLD')
        self.assertEqual(self.actor.workspace.created_at,before)
        self.assertEqual(self.actor.role,'OWNER')
        self.other.workspace.refresh_from_db();self.assertEqual(self.other.workspace.name,'Other secret household')
        self.assertContains(self.client.get(reverse('task_forms:board')),'Renamed Maple')

    def test_settings_invalid_inputs_are_accessible_and_preserved(self):
        for data,field in [({'name':'   ','timezone':'UTC'},'name'),({'name':'x'*121,'timezone':'UTC'},'name'),({'name':'Entered value','timezone':'Fake/Zone'},'timezone')]:
            page=self.client.post(reverse('households:settings'),data)
            self.assertEqual(page.status_code,200)
            self.assertIn(field,page.context['form'].errors)
            self.assertContains(page,'role="alert"')
            self.assertEqual(page.context['form'].data.dict(),data)
        self.actor.workspace.refresh_from_db();self.assertEqual(self.actor.workspace.name,'Maple home')

    def test_settings_deny_roommate_inactive_owner_and_wrong_methods(self):
        url=reverse('households:settings')
        self.selected(self.roommate)
        self.assertEqual(self.client.get(url).status_code,403)
        self.assertEqual(self.client.post(url,{'name':'Hacked','timezone':'UTC'}).status_code,403)
        self.selected(self.owner)
        self.assertEqual(self.client.delete(url).status_code,405)
        Membership.objects.filter(pk=self.actor.pk).update(is_active=False)
        self.assertRedirects(self.client.post(url,{'name':'Hacked','timezone':'UTC'}),reverse('households:onboarding'))

    def test_settings_recheck_owner_after_form_validation(self):
        from households.forms import HouseholdCreateForm
        original=HouseholdCreateForm.is_valid
        def demote(form):
            valid=original(form)
            Membership.objects.filter(pk=self.actor.pk).update(role='ADULT')
            return valid
        with patch.object(HouseholdCreateForm,'is_valid',demote):
            self.assertEqual(self.client.post(reverse('households:settings'),{'name':'Hacked','timezone':'UTC'}).status_code,403)
        self.actor.workspace.refresh_from_db();self.assertEqual(self.actor.workspace.name,'Maple home')

    def test_settings_csrf_get_read_only_and_fresh_timezone_expiry(self):
        url=reverse('households:settings')
        client=self.selected(self.owner,client=Client(enforce_csrf_checks=True))
        self.assertEqual(client.post(url,{'name':'Changed','timezone':'UTC'}).status_code,403)
        page=client.get(url)
        csrf=client.cookies['csrftoken'].value
        created=self.batch.created_at
        now=datetime(2026,1,1,4,tzinfo=dt_timezone.utc)
        with patch('inventory.expiry.timezone.now',return_value=now):
            old=self.client.get(reverse('groceries:workspace',args=[self.actor.workspace_id]))
            self.assertEqual(str(old.context['today']),'2025-12-31')
            self.assertContains(old,'Maple milk')
            self.assertEqual(len(old.context['soon']),0)
            self.assertEqual(client.post(url,{'name':'Maple home','timezone':'Asia/Tokyo','csrfmiddlewaretoken':csrf}).status_code,302)
            new=self.client.get(reverse('groceries:workspace',args=[self.actor.workspace_id]))
            self.assertEqual(str(new.context['today']),'2026-01-01')
            self.assertEqual(len(new.context['soon']),1)
        self.batch.refresh_from_db();self.assertEqual(self.batch.created_at,created)
