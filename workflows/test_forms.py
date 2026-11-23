from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from households.models import Membership, Workspace

from .models import Assignment, Task, TaskOccurrence


class TaskBoardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(username="forms-member")
        cls.roommate = User.objects.create_user(username="forms-roommate")
        cls.outsider = User.objects.create_user(username="forms-outsider")
        cls.home = Workspace.objects.create(name="Maple House")
        cls.other = Workspace.objects.create(name="Other household")
        cls.membership = Membership.objects.create(
            user=cls.user, workspace=cls.home, display_name="Member"
        )
        cls.roommate_membership = Membership.objects.create(
            user=cls.roommate, workspace=cls.home, display_name="Roommate"
        )
        Membership.objects.create(
            user=cls.outsider, workspace=cls.other, display_name="Outsider"
        )
        Task.objects.create(
            workspace=cls.home, title="Buy groceries", priority="HIGH", task_type="SHOPPING"
        )
        Task.objects.create(
            workspace=cls.home, title="Clean kitchen", priority="LOW", task_type="CHORE"
        )
        Task.objects.create(workspace=cls.other, title="Private other task")

    def test_recurring_bills_follow_the_visible_five_day_window(self):
        from expenses.models import RecurringBill
        from unittest.mock import patch
        from datetime import date
        regular=Task.objects.get(title="Buy groceries")
        for day in (9,10,14,15):
            task=Task.objects.create(workspace=self.home,title=f"Pay bill {day}")
            RecurringBill.objects.create(workspace=self.home,task=task,title=f"Bill {day}",paid_by=self.membership,created_by=self.membership,amount_cents=1000,next_due=date(2026,11,day))
        with patch("workflows.forms_views.timezone.localdate",return_value=date(2026,11,12)):
            response=self.client.get(reverse("task_forms:board"))
            names={t.title for t in response.context["tasks"]}
            self.assertIn("Pay bill 10",names)
            self.assertIn("Pay bill 14",names)
            self.assertNotIn("Pay bill 9",names)
            self.assertNotIn("Pay bill 15",names)
            self.assertIn(regular.title,names)
        with patch("workflows.forms_views.timezone.localdate",return_value=date(2026,11,13)):
            response=self.client.get(reverse("task_forms:board"))
            names={t.title for t in response.context["tasks"]}
            self.assertNotIn("Pay bill 10",names)
            self.assertIn("Pay bill 15",names)

    def setUp(self):
        self.client.force_login(self.user)
        session = self.client.session
        session["active_workspace_id"] = self.home.pk
        session.save()
        self.url = reverse("task_forms:board")

    def payload(self, **overrides):
        values = {
            "workspace": self.home.pk,
            "title": "Water the plants",
            "description": "Check the soil first.",
            "priority": "MEDIUM",
            "task_type": "CHORE",
            "default_location": "Living room",
            "recurrence_rule": "",
            "due_at": "",
            "assignee": "",
        }
        values.update(overrides)
        return values

    def test_get_filters_are_combined_read_only_and_case_insensitive(self):
        before = Task.objects.count()
        response = self.client.get(
            self.url,
            {
                "q": "  GROCERIES  ",
                "priority": "HIGH",
                "task_type": "SHOPPING",
                "workspace": self.home.pk,
            },
        )
        self.assertContains(response, "Buy groceries")
        self.assertNotContains(response, "Clean kitchen")
        self.assertNotContains(response, "Private other task")
        self.assertEqual(Task.objects.count(), before)
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, "css/hestia.css?v=")
        self.assertContains(response, "images/hestia-mark.svg")

    def test_empty_and_invalid_filters_have_clear_feedback(self):
        response = self.client.get(self.url, {"q": "does-not-exist"})
        self.assertContains(response, "No tasks found")
        self.assertContains(response, "Show all my tasks")
        response = self.client.get(self.url, {"priority": "INVALID"})
        self.assertContains(response, "Check the highlighted filters")
        self.assertContains(response, 'aria-invalid="true"')
        self.assertNotContains(response, "Buy groceries")

    def test_valid_post_creates_model_occurrence_and_redirects(self):
        before = Task.objects.count()
        due = timezone.now().replace(microsecond=0) + timezone.timedelta(days=2)
        response = self.client.post(
            self.url,
            self.payload(
                title="  Water the plants  ",
                created_by_membership="999",
                due_at=due.strftime("%Y-%m-%dT%H:%M"),
                assignee=self.roommate_membership.pk,
            ),
        )
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        task = Task.objects.get(title="Water the plants")
        self.assertEqual(task.created_by_membership, self.membership)
        self.assertEqual(task.workspace, self.home)
        occurrence = task.occurrences.get(sequence=1)
        self.assertEqual(occurrence.state, TaskOccurrence.OccurrenceState.ASSIGNED)
        self.assertEqual(
            occurrence.assignments.get().offered_to_membership,
            self.roommate_membership,
        )
        result = self.client.get(response.url)
        self.assertContains(result, "created.")
        self.assertContains(result, "Roommate")
        self.client.get(response.url)
        self.assertEqual(Task.objects.count(), before + 1)

    def test_invalid_post_keeps_input_and_does_not_save(self):
        before = Task.objects.count()
        response = self.client.post(
            self.url, self.payload(title=" ", description="Keep this description")
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Keep this description")
        self.assertContains(response, "This field is required.")
        self.assertEqual(Task.objects.count(), before)

    def test_duplicate_title_is_form_error_not_server_error(self):
        before = Task.objects.count()
        response = self.client.post(self.url, self.payload(title="Buy groceries"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["create_form"].errors)
        self.assertEqual(Task.objects.count(), before)

    def test_only_selected_household_is_available(self):
        response = self.client.get(self.url)
        self.assertNotContains(response, "Other household")
        self.assertNotContains(response, "Private other task")
        response = self.client.post(self.url, self.payload(workspace=self.other.pk))
        self.assertTrue(response.context["create_form"].has_error("workspace"))
        self.assertFalse(Task.objects.filter(title="Water the plants").exists())

    def test_inactive_membership_blocks_creation(self):
        Membership.objects.filter(pk=self.membership.pk).update(is_active=False)
        self.assertRedirects(self.client.get(self.url), reverse("households:onboarding"))
        self.client.post(self.url, self.payload())
        self.assertFalse(Task.objects.filter(title="Water the plants").exists())

    def test_anonymous_get_and_post_require_login_without_creating_task(self):
        self.client.logout()
        before = Task.objects.count()
        for response in (self.client.get(self.url), self.client.post(self.url, self.payload())):
            self.assertRedirects(
                response,
                "/accounts/login/?next=" + self.url,
                fetch_redirect_response=False,
            )
        self.assertEqual(Task.objects.count(), before)

    def test_unknown_household_is_rejected(self):
        response = self.client.post(self.url, self.payload(workspace=999999))
        self.assertTrue(response.context["create_form"].has_error("workspace"))
        self.assertFalse(Task.objects.filter(title="Water the plants").exists())

    def test_no_households_explains_setup(self):
        Workspace.objects.all().delete()
        self.assertRedirects(self.client.get(self.url), reverse("households:onboarding"))

    def test_real_csrf_protection_rejects_missing_token_and_accepts_valid_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        session = client.session
        session["active_workspace_id"] = self.home.pk
        session.save()
        page = client.get(self.url)
        self.assertContains(page, 'name="csrfmiddlewaretoken"')
        self.assertEqual(client.post(self.url, self.payload()).status_code, 403)
        token = client.cookies["csrftoken"].value
        response = client.post(self.url, self.payload(csrfmiddlewaretoken=token))
        self.assertEqual(response.status_code, 302)

    def test_pagination_preserves_filters(self):
        Task.objects.bulk_create(
            [Task(workspace=self.home, title=f"Garden {i}", priority="HIGH") for i in range(8)]
        )
        response = self.client.get(self.url, {"q": "Garden", "priority": "HIGH"})
        self.assertEqual(response.context["paginator"].count, 8)
        self.assertContains(response, "q=Garden&amp;priority=HIGH&amp;page=2")
        response = self.client.get(self.url, {"q": "Garden", "priority": "HIGH", "page": 2})
        self.assertEqual(len(response.context["tasks"]), 2)

    def test_user_input_remains_escaped(self):
        self.client.post(self.url, self.payload(title='<script>alert("x")</script>'))
        response = self.client.get(self.url)
        self.assertNotContains(response, '<script>alert("x")</script>')
        self.assertContains(response, "&lt;script&gt;")

    def test_weekly_recurrence_pre_schedules_occurrences(self):
        due = timezone.now().replace(microsecond=0) + timezone.timedelta(days=1)
        self.client.post(
            self.url,
            self.payload(
                title="Take out trash",
                recurrence_rule="Every Sunday",
                due_at=due.strftime("%Y-%m-%dT%H:%M"),
            ),
        )
        task = Task.objects.get(title="Take out trash")
        self.assertEqual(task.occurrences.count(), 4)

    def test_start_complete_edit_delete_and_reassign_flow(self):
        self.client.post(
            self.url,
            self.payload(title="Mop floors", assignee=self.membership.pk),
        )
        task = Task.objects.get(title="Mop floors")
        occurrence = task.occurrences.get(sequence=1)

        start = self.client.post(
            reverse("task_forms:occurrence_start", args=[occurrence.pk])
        )
        self.assertRedirects(start, self.url, fetch_redirect_response=False)
        occurrence.refresh_from_db()
        self.assertEqual(occurrence.state, TaskOccurrence.OccurrenceState.IN_PROGRESS)

        complete = self.client.post(
            reverse("task_forms:occurrence_complete", args=[occurrence.pk])
        )
        self.assertRedirects(complete, self.url, fetch_redirect_response=False)
        occurrence.refresh_from_db()
        self.assertEqual(
            occurrence.state, TaskOccurrence.OccurrenceState.REPORTED_COMPLETE
        )

        occurrence.state = TaskOccurrence.OccurrenceState.OPEN
        occurrence.save(update_fields=["state"])
        new_due = timezone.now() + timezone.timedelta(days=3)
        reassign = self.client.post(
            reverse("task_forms:occurrence_reassign", args=[occurrence.pk]),
            {
                "assignee": self.roommate_membership.pk,
                "due_at": new_due.strftime("%Y-%m-%dT%H:%M"),
            },
        )
        self.assertRedirects(reassign, self.url, fetch_redirect_response=False)
        occurrence.refresh_from_db()
        self.assertEqual(occurrence.state, TaskOccurrence.OccurrenceState.ASSIGNED)
        active_assignment = (
            occurrence.assignments.exclude(state=Assignment.AssignmentState.REASSIGNED)
            .exclude(state=Assignment.AssignmentState.WITHDRAWN)
            .latest("attempt_number")
        )
        self.assertEqual(
            active_assignment.offered_to_membership, self.roommate_membership
        )

        edit_url = reverse("task_forms:edit", args=[task.pk])
        response = self.client.get(edit_url)
        self.assertContains(response, "Mop floors")
        response = self.client.post(
            edit_url,
            {
                "title": "Mop floors thoroughly",
                "description": "Kitchen and hall",
                "task_type": "CHORE",
                "priority": "HIGH",
                "default_location": "Kitchen",
                "recurrence_rule": "",
                "due_at": new_due.strftime("%Y-%m-%dT%H:%M"),
                "assignee": self.roommate_membership.pk,
            },
        )
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        task.refresh_from_db()
        self.assertEqual(task.title, "Mop floors thoroughly")
        self.assertEqual(task.priority, "HIGH")

        delete = self.client.post(reverse("task_forms:delete", args=[task.pk]))
        self.assertRedirects(delete, self.url, fetch_redirect_response=False)
        self.assertFalse(Task.objects.filter(pk=task.pk).exists())

    def test_outsider_cannot_mutate_selected_household_task(self):
        task = Task.objects.get(title="Buy groceries")
        self.client.force_login(self.outsider)
        session = self.client.session
        session["active_workspace_id"] = self.other.pk
        session.save()
        response = self.client.get(reverse("task_forms:edit", args=[task.pk]))
        self.assertEqual(response.status_code, 404)
        response = self.client.post(reverse("task_forms:delete", args=[task.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Task.objects.filter(pk=task.pk).exists())

    def test_dual_member_sees_only_selected_household_tasks(self):
        Membership.objects.create(
            user=self.user, workspace=self.other, display_name="Also other"
        )
        session = self.client.session
        session["active_workspace_id"] = self.other.pk
        session.save()
        response = self.client.get(self.url)
        self.assertContains(response, "Private other task")
        self.assertNotContains(response, "Buy groceries")

    def test_little_home_club_theme_and_day_filter(self):
        due = timezone.now().replace(microsecond=0) + timezone.timedelta(days=1)
        self.client.post(
            self.url,
            self.payload(
                title="Plant watering",
                default_location="Living room",
                due_at=due.strftime("%Y-%m-%dT%H:%M"),
                assignee=self.roommate_membership.pk,
            ),
        )
        board = self.client.get(self.url)
        self.assertContains(board, "css/demo.css")
        self.assertContains(board, "A happy little home")
        self.assertContains(board, "Your spaces, in balance")
        self.assertContains(board, "Organize with AI")
        self.assertContains(board, "Ask Hestia")
        day = due.date().isoformat()
        filtered = self.client.get(self.url, {"day": day})
        self.assertContains(filtered, "Plant watering")
        self.assertContains(filtered, "Roommate")
        self.assertNotContains(filtered, "Buy groceries")
        self.assertContains(filtered, f'href="{self.url}"')
        self.assertContains(filtered, ">All</a>")
        cleared = self.client.get(self.url)
        self.assertContains(cleared, "Plant watering")
        self.assertContains(cleared, "Buy groceries")
        self.assertNotContains(cleared, ">All</a>")
