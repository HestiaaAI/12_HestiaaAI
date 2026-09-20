from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase
from django.urls import resolve, reverse

from households.models import Workspace
from .models import Task
from .views import TaskBaseView, TaskListView, task_manual_view, task_render_view


class AssignmentRoutingTests(SimpleTestCase):
    def test_routes_reach_four_distinct_implementations(self):
        expected = {
            "task-manual": task_manual_view,
            "task-render": task_render_view,
            "task-cbv-base": TaskBaseView,
            "task-cbv-generic": TaskListView,
        }
        for name, target in expected.items():
            with self.subTest(name=name):
                resolved = resolve(reverse("workflows:" + name))
                actual = getattr(resolved.func, "view_class", resolved.func)
                self.assertIs(actual, target)


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

    def test_each_demonstration_identifies_its_style_and_links_all_four_routes(self):
        styles = {
            "task-manual": "HttpResponse FBV",
            "task-render": "render() FBV",
            "task-cbv-base": "Base CBV",
            "task-cbv-generic": "Generic CBV",
        }
        for route, style in styles.items():
            with self.subTest(route=route):
                response = self.client.get(reverse("workflows:" + route))
                self.assertContains(response, "Assignment demonstration: " + style)
                self.assertContains(response, 'aria-label="View implementation examples"')
                for name in styles:
                    self.assertContains(response, 'href="' + reverse("workflows:" + name) + '"')

    def test_shared_template_without_view_style_omits_teaching_controls(self):
        html = render_to_string("tasks/task_list.html", {"tasks": []})
        self.assertNotIn("Assignment demonstration:", html)
        self.assertNotIn('aria-label="View implementation examples"', html)
        self.assertIn("Your household has no tasks yet.", html)
