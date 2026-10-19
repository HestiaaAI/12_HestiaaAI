from unittest.mock import patch
import time

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from households.models import Membership, Workspace
from .ai_adapter import SuggestionsUnavailable, validate_suggestions
from .ai_forms import MAX_DESCRIPTION, ReviewTaskForm
from .models import Task


@override_settings(HESTIA_BRAIN_DUMP_BACKEND="mock")
class BrainDumpTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="brain-member")
        cls.home = Workspace.objects.create(name="Brain household")
        cls.other = Workspace.objects.create(name="Other household")
        cls.member = Membership.objects.create(user=cls.user, workspace=cls.home, display_name="Member")

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("ai_tasks:brain-dump")

    def generate(self, **kwargs):
        return self.client.post(self.url, {"action": "generate", "workspace": self.home.pk,
            "text": "  Guests are coming tomorrow and the tap leaks.  ", **kwargs})

    def payload(self, response):
        review = response.context["review"]
        data = {"action": "save", "draft_token": response.context["draft_token"], "confirm": "on",
                "form-TOTAL_FORMS": len(review.forms), "form-INITIAL_FORMS": len(review.forms),
                "form-MIN_NUM_FORMS": 0, "form-MAX_NUM_FORMS": 20}
        for index, form in enumerate(review.forms):
            for key, value in form.initial.items():
                data[f"form-{index}-{key}"] = value
        return data

    def test_page_and_authentication_and_methods(self):
        self.assertContains(self.client.get(self.url), "Organize My Tasks")
        self.assertEqual(self.client.put(self.url).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.assertEqual(self.generate().status_code, 302)

    def test_blank_and_oversized_input(self):
        for text in (" \n ", "a" * 4001):
            response = self.generate(text=text)
            self.assertTrue(response.context["input_form"].errors)
        self.assertFalse(Task.objects.exists())

    def test_mock_review_does_not_save(self):
        response = self.generate()
        self.assertContains(response, "Clean the kitchen")
        self.assertContains(response, "Repair bathroom tap")
        self.assertContains(response, "Demo mode")
        self.assertFalse(Task.objects.exists())

    def test_model_enums_and_lengths(self):
        for kind in Task.TaskType.values:
            for priority in Task.Priority.values:
                self.assertTrue(ReviewTaskForm({"title": "Task", "task_type": kind, "priority": priority}).is_valid())
        for changes in ({"title": "x" * 201}, {"description": "x" * (MAX_DESCRIPTION + 1)},
                        {"task_type": "BAD"}, {"priority": "BAD"}):
            form = ReviewTaskForm({"title": "Task", "task_type": "CHORE", "priority": "LOW", **changes})
            self.assertFalse(form.is_valid())

    def test_malformed_ai_rejected(self):
        for result in (None, [], {}, {"tasks": "bad", "error": None}, {"tasks": [{}]},
                       {"tasks": [], "error": "secret provider failure"},
                       {"tasks": [{"title": "Task", "task_type": "BAD", "priority": "LOW", "description": ""}]}):
            with self.assertRaises(SuggestionsUnavailable):
                validate_suggestions(result)
        with patch("workflows.ai_views.get_suggestions", side_effect=RuntimeError("secret")):
            response = self.generate()
        self.assertContains(response, "Suggestions are unavailable")
        self.assertNotContains(response, "secret")
        self.assertFalse(Task.objects.exists())

    def test_empty_ai_output(self):
        with patch("workflows.ai_views.get_suggestions", return_value=[]):
            self.assertContains(self.generate(), "No tasks were suggested")

    def test_confirmation_required(self):
        data = self.payload(self.generate())
        data.pop("confirm")
        response = self.client.post(self.url, data)
        self.assertTrue(response.context["confirmation"].errors)
        self.assertFalse(Task.objects.exists())

    def test_edit_remove_save_attribution_and_prg_replay(self):
        data = self.payload(self.generate())
        data.update({"form-0-title": "  Edited kitchen  ", "form-0-priority": "LOW",
                     "form-0-task_type": "OTHER", "form-0-description": "Edited description",
                     "form-1-DELETE": "on", "workspace": self.other.pk,
                     "created_by_membership": 999, "form-0-workspace": self.other.pk})
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.assertEqual(Task.objects.count(), 2)
        task = Task.objects.get(title="Edited kitchen")
        self.assertEqual(task.workspace, self.home)
        self.assertEqual(task.created_by_membership, self.member)
        self.assertEqual((task.priority, task.task_type, task.description), ("LOW", "OTHER", "Edited description"))
        self.assertContains(self.client.get(response.url), "Saved 2 approved task(s)")
        self.client.post(self.url, data)
        self.assertEqual(Task.objects.count(), 2)

    def test_invalid_review_and_duplicate_batch_save_nothing(self):
        for changes in ({"form-0-priority": "BAD"}, {"form-1-title": "Clean the kitchen"},
                        {"form-TOTAL_FORMS": "99999"}, {"form-TOTAL_FORMS": "1"}):
            data = self.payload(self.generate())
            data.update(changes)
            self.assertEqual(self.client.post(self.url, data).status_code, 200)
            self.assertFalse(Task.objects.exists())
        Task.objects.create(workspace=self.home, title="Clean the kitchen")
        self.client.post(self.url, self.payload(self.generate()))
        self.assertEqual(Task.objects.count(), 1)

    def test_integrity_failure_rolls_back_earlier_tasks(self):
        data = self.payload(self.generate())
        original_save = Task.save

        def fail_second(task, *args, **kwargs):
            if task.title == "Buy groceries":
                raise IntegrityError("simulated concurrent conflict")
            return original_save(task, *args, **kwargs)

        with patch.object(Task, "save", fail_second):
            self.assertContains(self.client.post(self.url, data), "Nothing was saved")
        self.assertFalse(Task.objects.exists())

    def test_blank_forged_extra_forms_are_validation_errors(self):
        data = self.payload(self.generate())
        data["form-INITIAL_FORMS"] = "0"
        for index in range(3):
            for key in ("title", "task_type", "priority", "description"):
                data[f"form-{index}-{key}"] = ""
        response = self.client.post(self.url, data)
        self.assertTrue(response.context["review"].errors)
        self.assertFalse(Task.objects.exists())

    def test_all_removed_and_invalid_deleted_form(self):
        data = self.payload(self.generate())
        data.update({f"form-{i}-DELETE": "on" for i in range(3)})
        self.assertContains(self.client.post(self.url, data), "Keep at least one task")
        self.assertFalse(Task.objects.exists())
        data.pop("form-0-DELETE")
        data["form-1-title"] = ""
        self.assertEqual(self.client.post(self.url, data).status_code, 302)
        self.assertEqual(Task.objects.count(), 1)

    def test_workspace_and_draft_boundaries(self):
        self.assertTrue(self.generate(workspace=self.other.pk).context["input_form"].errors)
        data = self.payload(self.generate())
        data["draft_token"] += "tamper"
        self.assertContains(self.client.post(self.url, data), "review expired")
        data = self.payload(self.generate())
        Membership.objects.filter(pk=self.member.pk).update(is_active=False)
        self.assertContains(self.client.post(self.url, data), "access changed")
        self.assertFalse(Task.objects.exists())

    def test_expired_draft(self):
        data = self.payload(self.generate())
        with patch("django.core.signing.time.time", return_value=time.time() + 3601):
            self.assertContains(self.client.post(self.url, data), "review expired")
        self.assertFalse(Task.objects.exists())

    def test_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertContains(client.get(self.url), "csrfmiddlewaretoken")
        self.assertEqual(client.post(self.url, {"action": "generate"}).status_code, 403)
        response = client.post(self.url, {"action": "generate", "text": "Clean up", "workspace": self.home.pk,
                                         "csrfmiddlewaretoken": client.cookies["csrftoken"].value})
        self.assertContains(response, "Review your tasks")
        data = self.payload(response)
        self.assertEqual(client.post(self.url, data).status_code, 403)
        data["csrfmiddlewaretoken"] = client.cookies["csrftoken"].value
        self.assertEqual(client.post(self.url, data).status_code, 302)

    @override_settings(HESTIA_BRAIN_DUMP_BACKEND="local")
    def test_local_missing_service_fails_gracefully(self):
        with patch("workflows.services.hf_local.extract_tasks", side_effect=ImportError("Missing model dependency")):
            self.assertContains(self.generate(), "Suggestions are unavailable")

    @override_settings(HESTIA_BRAIN_DUMP_BACKEND="local")
    def test_local_contract_receives_trimmed_input_and_is_validated(self):
        from unittest.mock import Mock
        extract = Mock(return_value={"tasks": [
            {"title": "Local suggestion", "task_type": "ERRAND", "priority": "MEDIUM", "description": "Review me"}
        ], "error": None})
        with patch("workflows.services.hf_local.extract_tasks", extract):
            response = self.generate(text="  Example input  ")
        extract.assert_called_once_with("Example input")
        self.assertContains(response, "Local suggestion")
        self.assertNotContains(response, "Demo mode")
        self.assertFalse(Task.objects.exists())

    def test_ai_text_is_escaped(self):
        data = self.payload(self.generate())
        data.update({"form-0-title": "<script>evil()</script>", "form-0-priority": "BAD"})
        response = self.client.post(self.url, data)
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, "<script>evil()</script>")

    @override_settings(HESTIA_TASK_BREAKDOWN_CALLABLE="team.provider")
    def test_breakdown_is_explicit_review_only(self):
        data = self.payload(self.generate())
        data["breakdown_index"] = "0"
        with patch("workflows.ai_breakdown.import_string") as loader:
            loader.return_value.return_value = {"steps": ["Clear surfaces", "Wipe counters"], "error": None}
            response = self.client.post(self.url, data)
        self.assertContains(response, "Clear surfaces")
        self.assertContains(response, "Nothing was saved")
        self.assertFalse(Task.objects.exists())
        self.assertFalse(response.context["confirmation"].is_bound)
        loader.return_value.assert_called_once_with("Clean the kitchen", "Clean and organize the kitchen before guests arrive.")

    def test_missing_or_invalid_breakdown_preserves_edits(self):
        data = self.payload(self.generate())
        data.update({"breakdown_index": "0", "form-0-title": "Edited task"})
        self.assertContains(self.client.post(self.url, data), "Edited task")
        self.assertFalse(Task.objects.exists())
        with self.settings(HESTIA_TASK_BREAKDOWN_CALLABLE="team.provider"):
            with patch("workflows.ai_breakdown.import_string") as loader:
                loader.return_value.return_value = {"steps": ["x" * 501], "error": None}
                self.assertContains(self.client.post(self.url, data), "breakdown is unavailable")
        self.assertFalse(Task.objects.exists())
