from django.test import TestCase
from django.urls import reverse

from households.models import Workspace
from .models import Task


class TaskTemplateTests(TestCase):
    routes = ("task-manual", "task-render", "task-cbv-base", "task-cbv-generic")

    @classmethod
    def setUpTestData(cls):
        workspace = Workspace.objects.create(name="Template test household")
        Task.objects.create(workspace=workspace, title="Buy groceries", priority="HIGH")
        Task.objects.create(workspace=workspace, title="Clean kitchen", description="<script>alert(1)</script>")

    def test_all_views_reuse_the_template_and_render_model_fields(self):
        for route in self.routes:
            with self.subTest(route=route):
                response = self.client.get(reverse("workflows:" + route))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, "tasks/task_list.html")
                self.assertTemplateUsed(response, "base.html")
                self.assertContains(response, "Buy groceries")
                self.assertContains(response, "High")
                self.assertContains(response, "One-time task")
                self.assertContains(response, "No description provided.")
                self.assertContains(response, "&lt;script&gt;")
                self.assertNotContains(response, "<script>alert(1)</script>")

    def test_search_and_empty_state_on_every_view(self):
        for route in self.routes:
            with self.subTest(route=route):
                url = reverse("workflows:" + route)
                response = self.client.get(url, {"q": "  GROCERIES  "})
                self.assertContains(response, "Buy groceries")
                self.assertNotContains(response, "Clean kitchen")
                response = self.client.get(url, {"q": "XYZNOTAREALTASK123"})
                self.assertContains(response, "No tasks found")
                self.assertContains(response, "Show all tasks")
                self.assertNotContains(response, 'class="task-card"')
        self.assertEqual(Task.objects.count(), 2)

    def test_empty_database_has_a_helpful_message(self):
        Task.objects.all().delete()
        for route in self.routes:
            with self.subTest(route=route):
                response = self.client.get(reverse("workflows:" + route))
                self.assertContains(response, "Your household has no tasks yet.")
