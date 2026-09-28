from io import BytesIO

from django.test import TestCase
from django.urls import reverse

from households.models import Workspace
from workflows.models import Task, TaskOccurrence


class TaskAnalyticsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        home = Workspace.objects.create(name="Analytics demo")
        other = Workspace.objects.create(name="Second demo")
        task = Task.objects.create(workspace=home, title="<script>Unsafe title</script>", priority="HIGH")
        Task.objects.create(workspace=home, title="Weekly groceries", priority="HIGH")
        Task.objects.create(workspace=other, title="Water plants", priority="LOW")
        TaskOccurrence.objects.create(task=task, sequence=1)
        TaskOccurrence.objects.create(task=task, sequence=2)

    def test_summary_counts_tasks_not_occurrences_and_lists_every_task(self):
        response = self.client.get(reverse("analytics:task-stats"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_tasks"], 3)
        self.assertEqual([(row["label"], row["count"]) for row in response.context["priority_counts"]],
                         [("Low", 1), ("Medium", 0), ("High", 2), ("Urgent", 0)])
        self.assertEqual(len(response.context["tasks"]), 3)
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, "Weekly groceries")
        self.assertContains(response, "Second demo")
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, "<script>Unsafe")
        self.assertContains(response, reverse("analytics:task-priority-chart"))
        self.assertContains(response, '<figcaption>')
        self.assertContains(response, 'alt="')

    def test_empty_database_renders_page_and_chart(self):
        Task.objects.all().delete()
        response = self.client.get(reverse("analytics:task-stats"))
        self.assertEqual(response.context["total_tasks"], 0)
        self.assertContains(response, "No tasks yet")
        self.assertEqual(sum(row["count"] for row in response.context["priority_counts"]), 0)
        self.assert_png()

    def assert_png(self):
        from PIL import Image
        response = self.client.get(reverse("analytics:task-priority-chart"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertTrue(response.content.startswith(b"\x89PNG\r\n\x1a\n"))
        with Image.open(BytesIO(response.content)) as image:
            image.verify()
        return response.content

    def test_chart_is_valid_png_and_changes_when_database_changes(self):
        before = self.assert_png()
        Task.objects.filter(priority="HIGH").update(priority="URGENT")
        self.assertNotEqual(before, self.assert_png())

    def test_chart_uses_same_grouped_counts_as_page(self):
        from unittest.mock import patch
        from analytics.views import priority_counts
        with patch("analytics.views.priority_counts", wraps=priority_counts) as counts:
            self.assert_png()
            counts.assert_called_once()

    def test_endpoints_reject_post_without_writing(self):
        for name in ("task-stats", "task-priority-chart"):
            self.assertEqual(self.client.post(reverse("analytics:" + name)).status_code, 405)
        self.assertEqual(Task.objects.count(), 3)

    def test_home_navigation_reaches_analytics_and_task_links_reach_details(self):
        home = self.client.get(reverse("home"))
        self.assertContains(home, 'href="' + reverse("analytics:task-stats") + '"')
        response = self.client.get(reverse("analytics:task-stats"))
        self.assertContains(response, "css/hestia.css?v=")
        for task in Task.objects.all():
            self.assertContains(response, 'href="' + task.get_absolute_url() + '"')
            self.assertEqual(self.client.get(task.get_absolute_url()).status_code, 200)

    def test_task_board_creation_updates_analytics_and_chart(self):
        home = Workspace.objects.get(name="Analytics demo")
        before = self.assert_png()
        response = self.client.post(reverse("task_forms:board"), {
            "workspace": home.pk, "title": "Created through task board",
            "priority": "URGENT", "task_type": "CHORE",
        })
        self.assertEqual(response.status_code, 302)
        page = self.client.get(reverse("analytics:task-stats"))
        self.assertContains(page, "Created through task board")
        self.assertEqual(page.context["total_tasks"], 4)
        self.assertEqual(page.context["priority_counts"][-1]["count"], 1)
        self.assertNotEqual(before, self.assert_png())
