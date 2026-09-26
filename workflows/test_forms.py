from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from households.models import Membership, Workspace
from .models import Task


@override_settings(ROOT_URLCONF="workflows.forms_preview_urls")
class TaskBoardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="forms-member")
        cls.home = Workspace.objects.create(name="Maple House")
        cls.other = Workspace.objects.create(name="Other household")
        cls.membership = Membership.objects.create(user=cls.user, workspace=cls.home, display_name="Member")
        Task.objects.create(workspace=cls.home, title="Buy groceries", priority="HIGH", task_type="SHOPPING")
        Task.objects.create(workspace=cls.home, title="Clean kitchen", priority="LOW", task_type="CHORE")
        Task.objects.create(workspace=cls.other, title="Private other task")

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("task_forms:board")

    def payload(self, **overrides):
        values = {"workspace": self.home.pk, "title": "Water the plants", "description": "Check the soil first.",
                  "priority": "MEDIUM", "task_type": "CHORE", "default_location": "Living room", "recurrence_rule": ""}
        values.update(overrides)
        return values

    def test_get_filters_are_combined_read_only_and_case_insensitive(self):
        before = Task.objects.count()
        response = self.client.get(self.url, {"q": "  GROCERIES  ", "priority": "HIGH", "task_type": "SHOPPING", "workspace": self.home.pk})
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

    def test_valid_post_creates_model_and_redirects_without_repeat_on_refresh(self):
        before = Task.objects.count()
        response = self.client.post(self.url, self.payload(title="  Water the plants  ", created_by_membership="999"))
        self.assertRedirects(response, self.url + f"?workspace={self.home.pk}", fetch_redirect_response=False)
        task = Task.objects.get(title="Water the plants")
        self.assertEqual(task.created_by_membership, self.membership)
        self.assertEqual(task.workspace, self.home)
        result = self.client.get(response.url)
        self.assertContains(result, "created.")
        self.client.get(response.url)
        self.assertEqual(Task.objects.count(), before + 1)

    def test_invalid_post_keeps_input_and_does_not_save(self):
        before = Task.objects.count()
        response = self.client.post(self.url, self.payload(title=" ", description="Keep this description"))
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

    def test_other_household_cannot_be_selected_or_forged(self):
        response = self.client.get(self.url)
        self.assertNotContains(response, "Other household")
        response = self.client.post(self.url, self.payload(workspace=self.other.pk))
        self.assertTrue(response.context["create_form"].has_error("workspace"))
        self.assertFalse(Task.objects.filter(title="Water the plants").exists())
        response = self.client.get(self.url, {"workspace": self.other.pk})
        self.assertTrue(response.context["filter_form"].has_error("workspace"))
        self.assertNotContains(response, "Private other task")

    def test_inactive_membership_has_no_read_or_create_access(self):
        Membership.objects.filter(pk=self.membership.pk).update(is_active=False)
        response = self.client.get(self.url)
        self.assertContains(response, "Join a household to get started.")
        self.assertNotContains(response, "Buy groceries")
        self.client.post(self.url, self.payload())
        self.assertFalse(Task.objects.filter(title="Water the plants").exists())

    def test_anonymous_get_and_post_require_login(self):
        self.client.logout()
        for response in (self.client.get(self.url), self.client.post(self.url, self.payload())):
            self.assertEqual(response.status_code, 302)
            self.assertIn("/accounts/login/?next=", response.url)
        self.assertFalse(Task.objects.filter(title="Water the plants").exists())

    def test_real_csrf_protection_rejects_missing_token_and_accepts_valid_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        page = client.get(self.url)
        self.assertContains(page, 'name="csrfmiddlewaretoken"')
        self.assertEqual(client.post(self.url, self.payload()).status_code, 403)
        token = client.cookies["csrftoken"].value
        response = client.post(self.url, self.payload(csrfmiddlewaretoken=token))
        self.assertEqual(response.status_code, 302)

    def test_pagination_preserves_filters(self):
        Task.objects.bulk_create([Task(workspace=self.home, title=f"Garden {i}", priority="HIGH") for i in range(8)])
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
