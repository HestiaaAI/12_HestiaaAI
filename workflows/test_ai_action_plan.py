"""P4 review/save → P3 saved-task action plan integration, no external calls."""
import json
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from households.models import Membership, Workspace
from .models import Task


@override_settings(HESTIA_BRAIN_DUMP_BACKEND="mock", GROQ_API_KEY="test-only-key", GROQ_MODEL="test-model")
class BrainDumpToActionPlanTests(TestCase):
    def test_reviewed_tasks_reach_disclosed_plan_without_automatic_calls_or_writes(self):
        user = get_user_model().objects.create_user(username="p4-p3-member")
        home = Workspace.objects.create(name="P4 P3 integration")
        member = Membership.objects.create(user=user, workspace=home, display_name="Integration member")
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)
        url = reverse("ai_tasks:brain-dump")
        client.get(url)
        token = client.cookies["csrftoken"].value
        cache.clear()
        result = Mock(status_code=200)
        result.json.return_value = {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps({
            "summary": "Review these kitchen steps.",
            "steps": [{"title": "Clear counters", "description": "Put loose items away."}],
            "supplies": [], "cautions": []})}}]}
        with patch("workflows.action_plans.requests.post", return_value=result) as provider:
            generated = client.post(url, {"action": "generate", "workspace": home.pk,
                                         "text": "Kitchen, groceries and tap", "csrfmiddlewaretoken": token})
            self.assertFalse(Task.objects.exists())
            self.assertFalse(provider.called)
            forms = generated.context["review"].forms
            data = {"action": "save", "draft_token": generated.context["draft_token"],
                    "form-TOTAL_FORMS": len(forms), "form-INITIAL_FORMS": len(forms),
                    "csrfmiddlewaretoken": token, "form-1-DELETE": "on"}
            for i, form in enumerate(forms):
                data.update({f"form-{i}-{key}": value for key, value in form.initial.items()})
            data.update({"form-0-title": "Reviewed kitchen", "form-0-priority": "LOW"})
            self.assertEqual(client.post(url, data).status_code, 200)
            self.assertFalse(Task.objects.exists())
            data["confirm"] = "on"
            self.assertEqual(client.post(url, data).status_code, 302)
            self.assertEqual(Task.objects.count(), 2)
            self.assertFalse(provider.called)
            task = Task.objects.get(title="Reviewed kitchen")
            self.assertEqual((task.workspace, task.created_by_membership, task.priority), (home, member, "LOW"))
            self.assertContains(client.get(task.get_absolute_url()), "Create an AI action plan")
            plan_url = reverse("workflows:task-action-plan", args=[task.pk])
            self.assertContains(client.get(plan_url), "description to Groq")
            self.assertFalse(provider.called)
            self.assertEqual(client.post(plan_url).status_code, 403)
            self.assertFalse(provider.called)
            self.assertContains(client.post(plan_url, {"csrfmiddlewaretoken": token}), "Clear counters")
            provider.assert_called_once()
            sent = json.loads(provider.call_args.kwargs["json"]["messages"][1]["content"])
            self.assertEqual(set(sent), {"title", "task_type", "priority", "description"})
            self.assertEqual(Task.objects.count(), 2)
            task.refresh_from_db()
            self.assertEqual(task.priority, "LOW")
