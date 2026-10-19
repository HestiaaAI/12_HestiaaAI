from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from households.models import Membership, Workspace
from .action_plans import ActionPlanError
from .models import Task
from .test_action_plans import valid_plan


@override_settings(GROQ_API_KEY="test-key", GROQ_MODEL="test-model")
class ActionPlanViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="plan-member")
        cls.outsider = get_user_model().objects.create_user(username="outside-member")
        cls.home = Workspace.objects.create(name="Plan household")
        cls.membership = Membership.objects.create(user=cls.user, workspace=cls.home,
                                                   display_name="Planner")
        cls.task = Task.objects.create(workspace=cls.home, title="Prepare guest room",
                                       description="Guests arrive Friday.")

    def setUp(self):
        cache.clear()
        self.page = reverse("workflows:task-action-plan", args=[self.task.pk])
        self.api = reverse("api:task-action-plan", args=[self.task.pk])
        self.client.force_login(self.user)
        self.patcher = patch("workflows.action_plan_views.generate_action_plan", return_value=valid_plan())
        self.generate = self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_detail_link_is_visible_only_to_active_members(self):
        self.assertContains(self.client.get(self.task.get_absolute_url()), self.page)
        self.client.force_login(self.outsider)
        self.assertNotContains(self.client.get(self.task.get_absolute_url()), self.page)

    def test_get_previews_disclosure_and_never_calls_groq(self):
        response = self.client.get(self.page)
        self.assertContains(response, "sends this task's title, type, priority and description to Groq")
        self.assertContains(response, "csrfmiddlewaretoken")
        self.assertIn("no-store", response.headers["Cache-Control"])
        self.generate.assert_not_called()

    def test_post_renders_plan_without_creating_or_updating_tasks(self):
        before = list(Task.objects.values())
        response = self.client.post(self.page)
        self.assertContains(response, "Your draft action plan")
        self.assertContains(response, "Clean and restock")
        self.assertContains(response, "Towels")
        self.assertEqual(list(Task.objects.values()), before)
        self.assertEqual(self.generate.call_args.args[0].pk, self.task.pk)

    def test_provider_output_is_html_escaped(self):
        plan = valid_plan()
        plan["summary"] = '<script>alert("bad")</script>'
        self.generate.return_value = plan
        response = self.client.post(self.page)
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, "<script>")

    def test_json_api_returns_plan_metadata_and_no_cache(self):
        before = Task.objects.count()
        response = self.client.post(self.api, data="{}", content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"task_id": self.task.pk, "plan": valid_plan(),
                                           "provider": "Groq", "model": "test-model"})
        self.assertIn("no-store", response.headers["Cache-Control"])
        self.assertEqual(Task.objects.count(), before)

    def test_json_api_does_not_generate_on_get(self):
        self.assertEqual(self.client.get(self.api).status_code, 405)
        self.generate.assert_not_called()

    def test_anonymous_html_redirects_and_api_returns_401(self):
        self.client.logout()
        self.assertRedirects(self.client.get(self.page), f"/accounts/login/?next={self.page}")
        self.assertEqual(self.client.post(self.api).status_code, 401)
        self.generate.assert_not_called()

    def test_other_household_and_inactive_members_cannot_send_task_data(self):
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(self.page).status_code, 404)
        response = self.client.post(self.api)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"error": "Task not found."})
        self.client.force_login(self.user)
        self.membership.is_active = False
        self.membership.save(update_fields=["is_active"])
        self.assertEqual(self.client.post(self.api).status_code, 404)
        self.generate.assert_not_called()

    def test_missing_task_returns_json_404(self):
        response = self.client.post(reverse("api:task-action-plan", args=[999999]))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"error": "Task not found."})

    def test_csrf_protects_html_and_json(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(self.page).status_code, 403)
        self.assertEqual(client.post(self.api, data="{}", content_type="application/json").status_code, 403)
        client.get(self.page)
        response = client.post(self.api, data="{}", content_type="application/json",
                               HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value)
        self.assertEqual(response.status_code, 200)

    def test_provider_failure_has_safe_html_and_json_errors(self):
        self.generate.side_effect = ActionPlanError("Try again later.", 504, "timeout")
        self.assertContains(self.client.post(self.page), "Try again later.", status_code=504)
        cache.clear()
        response = self.client.post(self.api)
        self.assertEqual(response.status_code, 504)
        self.assertEqual(response.json(), {"error": "Try again later.", "code": "timeout"})

    def test_cooldown_prevents_duplicate_provider_calls(self):
        self.assertEqual(self.client.post(self.api).status_code, 200)
        response = self.client.post(self.api)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["code"], "cooldown")
        self.assertEqual(self.generate.call_count, 1)

    def test_cooldown_does_not_block_another_member(self):
        Membership.objects.create(user=self.outsider, workspace=self.home, display_name="Other")
        self.client.post(self.api)
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.post(self.api).status_code, 200)

    @override_settings(GROQ_API_KEY="")
    def test_missing_key_remains_503_instead_of_cooldown(self):
        self.generate.side_effect = ActionPlanError("Not configured.", 503, "not_configured")
        for _ in range(2):
            response = self.client.post(self.api)
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json()["code"], "not_configured")
