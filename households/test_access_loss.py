"""Next-request denial and stale forms cannot call providers or save records."""
from unittest.mock import patch
from django.test import TestCase,override_settings
from django.urls import reverse
from django.utils import timezone
from workflows.models import Task
from workflows.ai_forms import BrainDumpForm,TaskReviewFormSet
from workflows.task_forms import TaskCreateForm
from inventory.forms import GroceryBatchForm,ReceiptBatchFormSet
from .test_management import ManagementFixture
from .models import Membership
from .services import remove_member,leave_household,create_household,issue_invitation

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AccessLossTests(ManagementFixture,TestCase):
    def removed(self):remove_member(actor=self.actor,membership_id=self.member.pk)

    def test_removal_and_departure_deny_next_request_across_all_private_surfaces(self):
        invitation,token=issue_invitation(actor=self.actor,email='pending@example.test')
        wid=self.actor.workspace_id
        routes=[('task_forms:board',[],{}),('workflows:task-detail',[self.task.pk],{}),('workflows:task-insights',[],{}),
                ('workflows:task-action-plan',[self.task.pk],{}),('ai_tasks:brain-dump',[],{'action':'generate','workspace':wid,'text':'Work'}),
                ('groceries:workspace',[wid],{}),('groceries:edit',[wid,self.batch.pk],{}),('groceries:close',[wid,self.batch.pk],{'state':'consumed'}),
                ('groceries:scan',[wid],{'action':'save'}),('groceries:suggest',[wid],{}),('groceries:approve',[wid],{'suggestion':'forged'}),
                ('households:detail',[],{}),('households:settings',[],{}),('households:invites',[],{'email':'forged@example.test'}),
                ('households:resend-invite',[invitation.pk],{}),('households:revoke-invite',[invitation.pk],{})]
        for operation in ['removed','left']:
            Membership.objects.filter(pk=self.member.pk).update(is_active=True)
            self.selected(self.roommate)
            if operation=='removed':self.removed()
            else:leave_household(actor=self.member)
            with patch('workflows.ai_views.get_suggestions') as ai,patch('workflows.action_plan_views.generate_action_plan') as plan,patch('inventory.grocery_ai.meal_idea') as meal,patch('inventory.views.receipt_drafts') as receipt:
                for name,args,data in routes:
                    with self.subTest(operation=operation,route=name):
                        for method in ['get','post']:
                            response=getattr(self.client,method)(reverse(name,args=args),data)
                            if (name=='households:detail' and method=='post') or (name in {'households:resend-invite','households:revoke-invite'} and method=='get'):
                                self.assertEqual(response.status_code,405);continue
                            self.assertEqual(response.status_code,302)
                            self.assertIn(reverse('households:onboarding'),response['Location'])
                ai.assert_not_called();plan.assert_not_called();meal.assert_not_called();receipt.assert_not_called()
            self.assertEqual(self.client.get(reverse('workflows:task-export-csv')).status_code,409)
            self.assertEqual(self.client.get(reverse('ask-hestia')).status_code,200)
            self.assertEqual(Task.objects.filter(workspace_id=wid).count(),1)
            self.batch.refresh_from_db();self.assertEqual(self.batch.state,'active')
            invitation.refresh_from_db();self.assertIsNone(invitation.revoked_at)

    def test_other_household_works_and_old_direct_ids_stay_inaccessible(self):
        other=create_household(user=self.roommate,name='Still my household',timezone='UTC')
        other_task=Task.objects.create(workspace=other.workspace,title='Other retained task')
        self.selected(self.roommate)
        self.removed()
        self.assertContains(self.client.get(reverse('task_forms:board')),other_task.title)
        self.assertNotContains(self.client.get(reverse('task_forms:board')),self.task.title)
        self.assertEqual(self.client.get(self.task.get_absolute_url()).status_code,404)
        self.assertEqual(self.client.get(reverse('groceries:workspace',args=[self.actor.workspace_id])).status_code,404)
        self.assertContains(self.client.get(reverse('households:detail')),'Still my household')
        self.assertNotContains(self.client.get(reverse('households:detail')),'Maple home')

    def test_stale_manual_task_and_grocery_forms_do_not_save(self):
        for formclass,url,data in [
            (TaskCreateForm,reverse('task_forms:board'),{'workspace':self.actor.workspace_id,'title':'Forbidden new task','task_type':'CHORE','priority':'LOW'}),
            (GroceryBatchForm,reverse('groceries:add',args=[self.actor.workspace_id]),{'name':'Forbidden batch','quantity':1,'unit':'item','storage':'fridge'})]:
            Membership.objects.filter(pk=self.member.pk).update(is_active=True)
            self.selected(self.roommate)
            original=formclass.is_valid
            def revoke(form):
                result=original(form)
                if result and Membership.objects.filter(pk=self.member.pk,is_active=True).exists():
                    form._phase4_removed=True;self.removed()
                return result
            with patch.object(formclass,'is_valid',revoke):self.client.post(url,data)
            self.assertFalse(Task.objects.filter(title='Forbidden new task').exists())
            self.assertFalse(self.batch.__class__.objects.filter(name='Forbidden batch').exists())

    def test_removed_during_receipt_validation_cannot_save_batches(self):
        self.selected(self.roommate)
        original=ReceiptBatchFormSet.is_valid
        def revoke(form):
            result=original(form)
            if result and Membership.objects.filter(pk=self.member.pk,is_active=True).exists():
                    form._phase4_removed=True;self.removed()
            return result
        data={'action':'save','form-TOTAL_FORMS':'1','form-INITIAL_FORMS':'1','form-0-name':'Forbidden receipt row','form-0-quantity':'1','form-0-unit':'item','form-0-storage':'fridge'}
        with patch.object(ReceiptBatchFormSet,'is_valid',revoke):self.client.post(reverse('groceries:scan',args=[self.actor.workspace_id]),data)
        self.assertFalse(self.batch.__class__.objects.filter(name='Forbidden receipt row').exists())

    def generate_draft(self):
        self.selected(self.roommate)
        with patch('workflows.ai_views.get_suggestions',return_value=[{'title':'Staged task','description':'','task_type':'CHORE','priority':'LOW'}]):
            response=self.client.post(reverse('ai_tasks:brain-dump'),{'action':'generate','workspace':self.actor.workspace_id,'text':'Plan housework'})
        return {'action':'save','draft_token':response.context['draft_token'],'confirm':'on','form-TOTAL_FORMS':1,'form-INITIAL_FORMS':1,'form-0-title':'Staged task','form-0-description':'','form-0-task_type':'CHORE','form-0-priority':'LOW'}

    def test_staged_draft_loaded_before_removal_cannot_be_confirmed(self):
        data=self.generate_draft();self.removed()
        self.assertRedirects(self.client.post(reverse('ai_tasks:brain-dump'),data),reverse('households:onboarding'))
        self.assertFalse(Task.objects.filter(title='Staged task').exists())

    def test_ai_review_revoked_during_validation_does_not_save(self):
        data=self.generate_draft()
        original=TaskReviewFormSet.is_valid
        def revoke(form):
            result=original(form)
            if result and Membership.objects.filter(pk=self.member.pk,is_active=True).exists():
                    form._phase4_removed=True;self.removed()
            return result
        with patch.object(TaskReviewFormSet,'is_valid',revoke):self.client.post(reverse('ai_tasks:brain-dump'),data)
        self.assertFalse(Task.objects.filter(title='Staged task').exists())

    def test_revoked_during_ai_input_validation_never_calls_provider(self):
        self.selected(self.roommate)
        original=BrainDumpForm.is_valid
        def revoke(form):
            result=original(form)
            if result and Membership.objects.filter(pk=self.member.pk,is_active=True).exists():
                    form._phase4_removed=True;self.removed()
            return result
        with patch.object(BrainDumpForm,'is_valid',revoke),patch('workflows.ai_views.get_suggestions') as provider:
            response=self.client.post(reverse('ai_tasks:brain-dump'),{'action':'generate','workspace':self.actor.workspace_id,'text':'Plan housework'})
        provider.assert_not_called();self.assertEqual(response.status_code,302)

    def test_revoked_after_plan_lookup_never_calls_provider(self):
        from workflows import action_plan_views
        self.selected(self.roommate)
        original=action_plan_views._member_task
        def revoke(*args,**kwargs):
            task=original(*args,**kwargs);self.removed();return task
        with patch.object(action_plan_views,'_member_task',side_effect=revoke),patch.object(action_plan_views,'generate_action_plan') as provider:
            response=self.client.post(reverse('workflows:task-action-plan',args=[self.task.pk]))
        provider.assert_not_called();self.assertEqual(response.status_code,302)

    def test_revoked_after_grocery_lookup_never_calls_meal_or_receipt_provider(self):
        from inventory import views
        self.batch.expires_on=timezone.localdate();self.batch.save()
        original=views.membership_for
        for route,provider_name,data in [('suggest','meal_idea',{}),('scan','receipt_drafts',{'action':'review','receipt_text':'Oat milk 2'})]:
            Membership.objects.filter(pk=self.member.pk).update(is_active=True)
            self.selected(self.roommate)
            def revoke(*args,**kwargs):
                member=original(*args,**kwargs);self.removed();return member
            target='inventory.grocery_ai.meal_idea' if provider_name=='meal_idea' else 'inventory.views.receipt_drafts'
            with patch.object(views,'membership_for',side_effect=revoke),patch(target,return_value='Meal idea' if provider_name=='meal_idea' else []) as provider:
                response=self.client.post(reverse('groceries:'+route,args=[self.actor.workspace_id]),data)
            provider.assert_not_called();self.assertEqual(response.status_code,302)

    def test_grocery_suggestion_loaded_before_removal_cannot_create_task(self):
        self.selected(self.roommate)
        self.batch.expires_on=timezone.localdate();self.batch.save()
        with patch('inventory.grocery_ai.meal_idea',return_value='Make a simple meal'):
            page=self.client.post(reverse('groceries:suggest',args=[self.actor.workspace_id]))
        token=page.context['suggestion_token'];self.removed()
        self.assertRedirects(self.client.post(reverse('groceries:approve',args=[self.actor.workspace_id]),{'suggestion':token}),reverse('households:onboarding'))
        self.assertEqual(Task.objects.filter(workspace=self.actor.workspace).count(),1)

    def test_revoked_during_breakdown_validation_never_calls_provider(self):
        data=self.generate_draft();data['breakdown_index']='0'
        original=TaskReviewFormSet.is_valid
        def revoke(form):
            result=original(form)
            if result and Membership.objects.filter(pk=self.member.pk,is_active=True).exists():
                form._phase4_removed=True;self.removed()
            return result
        with patch.object(TaskReviewFormSet,'is_valid',revoke),patch('workflows.ai_views.suggest_steps',return_value='Suggested details') as provider:
            response=self.client.post(reverse('ai_tasks:brain-dump'),data)
        provider.assert_not_called();self.assertEqual(response.status_code,302)

    def test_revoked_after_meal_draft_validation_cannot_approve(self):
        from inventory import views
        self.selected(self.roommate)
        self.batch.expires_on=timezone.localdate();self.batch.save()
        with patch('inventory.grocery_ai.meal_idea',return_value='Make a simple meal'):
            token=self.client.post(reverse('groceries:suggest',args=[self.actor.workspace_id])).context['suggestion_token']
        original=views.signing.loads
        def revoke(*args,**kwargs):
            draft=original(*args,**kwargs);self.removed();return draft
        with patch.object(views.signing,'loads',side_effect=revoke):
            response=self.client.post(reverse('groceries:approve',args=[self.actor.workspace_id]),{'suggestion':token})
        self.assertEqual(response.status_code,302)
        self.assertEqual(Task.objects.filter(workspace=self.actor.workspace).count(),1)
