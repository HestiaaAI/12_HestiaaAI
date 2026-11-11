"""Real account-to-household creation with server-owned actor and role."""
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse
from .models import Membership, Workspace
from .forms import HouseholdCreateForm
from .services import create_household

class HouseholdCreationTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user('new-owner',first_name='  Ada',last_name='Lovelace  ')
        self.client.force_login(self.user)

    def payload(self,**overrides):
        return {'name':'  Cedar home  ','timezone':'America/Chicago',**overrides}

    def test_name_and_timezone_validation_and_default(self):
        self.assertEqual(HouseholdCreateForm().fields['timezone'].initial,'America/Chicago')
        for changes,field in [({'name':'   '},'name'),({'name':'x'*121},'name'),({'timezone':'Fake/Zone'},'timezone'),({'timezone':'../etc/passwd'},'timezone')]:
            form=HouseholdCreateForm(self.payload(**changes))
            self.assertFalse(form.is_valid())
            self.assertIn(field,form.errors)
        form=HouseholdCreateForm(self.payload(timezone='Europe/London'))
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['name'],'Cedar home')

    def test_service_creates_active_owner_with_server_permissions(self):
        member=create_household(user=self.user,name='  Cedar home ',timezone='Europe/London')
        self.assertEqual(member.workspace.name,'Cedar home')
        self.assertEqual(member.workspace.timezone,'Europe/London')
        self.assertEqual(member.workspace.workspace_type,Workspace.WorkspaceType.HOUSEHOLD)
        self.assertEqual(member.user,self.user)
        self.assertEqual(member.role,Membership.MemberRole.OWNER)
        self.assertTrue(member.is_active)
        self.assertTrue(member.can_assign_tasks and member.can_manage_sources and member.can_receive_assignments)
        self.assertEqual(member.display_name,'Ada Lovelace')

    def test_service_authentication_and_validation(self):
        for actor in [AnonymousUser(),None]:
            with self.assertRaises(PermissionDenied):create_household(user=actor,name='Home',timezone='UTC')
        with self.assertRaises(ValidationError):create_household(user=self.user,name=' ',timezone='Invalid/Zone')
        self.assertFalse(Workspace.objects.exists())

    def test_display_name_falls_back_and_respects_model_limit(self):
        self.user.first_name='';self.user.last_name='';self.user.save()
        self.assertEqual(create_household(user=self.user,name='One',timezone='UTC').display_name,self.user.username)
        self.user.first_name='A'*150;self.user.last_name='B'*150;self.user.save()
        member=create_household(user=self.user,name='Two',timezone='UTC')
        self.assertEqual(len(member.display_name),Membership._meta.get_field('display_name').max_length)

    def test_duplicate_household_names_are_allowed(self):
        first=create_household(user=self.user,name='Same',timezone='UTC')
        second=create_household(user=self.user,name='Same',timezone='UTC')
        self.assertNotEqual(first.workspace_id,second.workspace_id)

    def test_membership_failure_rolls_back_workspace(self):
        with patch('households.services.Membership.objects.create',side_effect=IntegrityError('Synthetic failure')):
            with self.assertRaises(IntegrityError):create_household(user=self.user,name='Rollback',timezone='UTC')
        self.assertFalse(Workspace.objects.exists())
        self.assertFalse(Membership.objects.exists())

    def test_get_is_read_only_and_anonymous_requests_require_login(self):
        url=reverse('households:create')
        self.assertContains(self.client.get(url),'Create household')
        self.assertFalse(Workspace.objects.exists())
        self.client.logout()
        for response in [self.client.get(url),self.client.post(url,self.payload())]:
            self.assertRedirects(response,reverse('accounts:login')+'?next='+url,fetch_redirect_response=False)
        self.assertFalse(Workspace.objects.exists())

    def test_invalid_post_retains_input_and_errors(self):
        response=self.client.post(reverse('households:create'),self.payload(name='Keep this name',timezone='Fake/Zone'))
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'Keep this name')
        self.assertContains(response,'Fake/Zone')
        self.assertContains(response,'aria-invalid="true"')
        self.assertContains(response,'role="alert"')
        self.assertFalse(Workspace.objects.exists())
        self.assertNotIn('active_workspace_id',self.client.session)

    def test_valid_post_ignores_forged_fields_and_selects_empty_board(self):
        other=get_user_model().objects.create_user('other-actor')
        response=self.client.post(reverse('households:create'),self.payload(user=other.pk,role='ADULT',is_active='false',can_assign_tasks='false',workspace_type='TEAM',next='https://evil.invalid'))
        self.assertRedirects(response,reverse('task_forms:board'),fetch_redirect_response=False)
        member=Membership.objects.get(user=self.user)
        self.assertEqual(member.role,'OWNER')
        self.assertEqual(member.workspace.workspace_type,'HOUSEHOLD')
        self.assertTrue(member.can_assign_tasks)
        self.assertFalse(Membership.objects.filter(user=other).exists())
        self.assertEqual(self.client.session['active_workspace_id'],member.workspace_id)
        board=self.client.get(reverse('task_forms:board'))
        self.assertEqual(board.context['active_household'],member.workspace)
        self.assertEqual(board.context['paginator'].count,0)
        self.assertContains(board,'created')
        self.assertEqual(Workspace.objects.count(),1)

    def test_failed_creation_preserves_existing_selection(self):
        member=create_household(user=self.user,name='Existing',timezone='UTC')
        session=self.client.session;session['active_workspace_id']=member.workspace_id;session.save()
        with patch('households.services.Membership.objects.create',side_effect=IntegrityError('Synthetic failure')):
            with self.assertRaises(IntegrityError):self.client.post(reverse('households:create'),self.payload())
        self.assertEqual(self.client.session['active_workspace_id'],member.workspace_id)
        self.assertEqual(Workspace.objects.count(),1)

    def test_csrf_enforced_and_token_allows_creation(self):
        client=Client(enforce_csrf_checks=True);client.force_login(self.user)
        url=reverse('households:create')
        self.assertEqual(client.post(url,self.payload()).status_code,403)
        self.assertFalse(Workspace.objects.exists())
        client.get(url)
        response=client.post(url,self.payload(csrfmiddlewaretoken=client.cookies['csrftoken'].value))
        self.assertRedirects(response,reverse('task_forms:board'))
        self.assertEqual(Workspace.objects.count(),1)

    def test_existing_member_creates_second_household_without_data_mixing(self):
        from workflows.models import Task
        from inventory.models import GroceryBatch
        old=create_household(user=self.user,name='Original',timezone='UTC')
        Task.objects.create(workspace=old.workspace,title='Original task')
        GroceryBatch.objects.create(workspace=old.workspace,name='Original milk',quantity=1,unit='L',storage='fridge')
        self.client.post(reverse('households:create'),self.payload())
        new=Membership.objects.exclude(pk=old.pk).get(user=self.user)
        self.assertEqual(self.client.session['active_workspace_id'],new.workspace_id)
        board=self.client.get(reverse('task_forms:board'))
        self.assertNotContains(board,'Original task')
        groceries=self.client.get(reverse('groceries:list'),follow=True)
        self.assertNotContains(groceries,'Original milk')
        self.assertContains(groceries,new.workspace.name)
        roster=self.client.get(reverse('groceries:household'))
        self.assertEqual(roster.context['active_household'],new.workspace)
        self.assertEqual(self.client.get(reverse('workflows:task-insights')).context['total_tasks'],0)
        self.client.post(reverse('households:switch'),{'workspace_id':old.workspace_id})
        self.assertContains(self.client.get(reverse('task_forms:board')),'Original task')
        self.assertContains(self.client.get(reverse('groceries:list'),follow=True),'Original milk')

    def test_account_deactivated_after_authentication_cannot_create(self):
        get_user_model().objects.filter(pk=self.user.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            create_household(user=self.user,name='Denied',timezone='UTC')
        self.assertFalse(Workspace.objects.exists())
