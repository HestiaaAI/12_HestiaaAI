from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from households.models import Workspace, Membership
from workflows.models import Task, TaskOccurrence


class TaskAnalyticsTests(TestCase):
    def setUp(self):
        self.auth_user = get_user_model().objects.create_user(username="feature-test-member")
        Membership.objects.create(user=self.auth_user, workspace=Workspace.objects.get(name="Analytics demo"), display_name="Reader")
        self.client.force_login(self.auth_user)

    @classmethod
    def setUpTestData(cls):
        home = Workspace.objects.create(name="Analytics demo")
        other = Workspace.objects.create(name="Second demo")
        task = Task.objects.create(workspace=home, title="<script>Unsafe title</script>", priority="HIGH")
        Task.objects.create(workspace=home, title="Weekly groceries", priority="HIGH")
        Task.objects.create(workspace=other, title="Water plants", priority="LOW")
        TaskOccurrence.objects.create(task=task, sequence=1)
        TaskOccurrence.objects.create(task=task, sequence=2)

    def test_summary_counts_tasks_not_occurrences_and_excludes_other_households(self):
        response = self.client.get(reverse('workflows:task-insights'), follow=True)
        self.assertEqual(response.context['total_tasks'], 2)
        self.assertEqual(response.context['priority_summary'], [{'label': 'High', 'count': 2}])
        self.assertNotContains(response, 'Second demo')
        self.assertContains(response, reverse('analytics:task-priority-chart'))
        self.assertContains(response, 'alt="')

    def test_empty_database_renders_page_and_chart(self):
        Task.objects.all().delete()
        response = self.client.get(reverse('workflows:task-insights'), follow=True)
        self.assertEqual(response.context['total_tasks'], 0)
        self.assertContains(response, 'No tasks yet')
        self.assertEqual(response.context['priority_summary'], [])
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
        for name in ("workflows:task-insights", "analytics:task-priority-chart"):
            self.assertEqual(self.client.post(reverse(name)).status_code, 405)
        self.assertEqual(Task.objects.count(), 3)

    def test_board_reaches_insights_and_selected_details(self):
        board = self.client.get(reverse('task_forms:board'))
        self.assertContains(board, reverse('workflows:task-insights'))
        for task in Task.objects.filter(workspace__name='Analytics demo'):
            self.assertContains(board, task.get_absolute_url())
            self.assertEqual(self.client.get(task.get_absolute_url()).status_code, 200)

    def test_task_board_creation_updates_analytics_and_chart(self):
        home = Workspace.objects.get(name="Analytics demo")
        before = self.assert_png()
        response = self.client.post(reverse("task_forms:board"), {
            "workspace": home.pk, "title": "Created through task board",
            "priority": "URGENT", "task_type": "CHORE",
        })
        self.assertEqual(response.status_code, 302)
        page = self.client.get(reverse("workflows:task-insights"), follow=True)
        self.assertContains(self.client.get(reverse("task_forms:board")), "Created through task board")
        self.assertEqual(page.context["total_tasks"], 3)
        self.assertEqual(page.context["priority_summary"][-1]["count"], 1)
        self.assertNotEqual(before, self.assert_png())
