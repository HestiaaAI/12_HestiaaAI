import csv
import io
from datetime import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from households.models import Workspace, Membership
from workflows.models import Task


class ReportTests(TestCase):
    def setUp(self):
        self.auth_user = get_user_model().objects.create_user(username="feature-test-member")
        Membership.objects.create(user=self.auth_user, workspace=self.first.workspace, display_name="Reader")
        self.client.force_login(self.auth_user)

    @classmethod
    def setUpTestData(cls):
        home = Workspace.objects.create(name="Reports demo")
        cls.first = Task.objects.create(workspace=home, title='Café, "kitchen"\ncleaning', priority="HIGH", task_type="CHORE")
        cls.second = Task.objects.create(workspace=home, title="Shopping", priority="LOW", task_type="SHOPPING")
        Task.objects.create(workspace=home, title="Laundry", priority="HIGH", task_type="CHORE")

    def test_authenticated_report_totals_groups_and_download_links(self):
        response = self.client.get(reverse("workflows:task-insights"), follow=True)
        self.assertEqual(response.context["total_tasks"], 3)
        self.assertEqual({r["label"]: r["count"] for r in response.context["priority_summary"]}, {"High": 2, "Low": 1})
        self.assertEqual({r["label"]: r["count"] for r in response.context["type_summary"]}, {"Chore": 2, "Shopping": 1})
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, reverse("workflows:task-export-csv"))
        self.assertContains(self.client.get(reverse("task_forms:board")), reverse("workflows:task-insights"))

    def test_csv_headers_order_and_quoting(self):
        response = self.client.get(reverse("workflows:task-export-csv"))
        self.assertTrue(response["Content-Type"].startswith("text/csv"))
        self.assertRegex(response["Content-Disposition"], r'^attachment; filename="tasks_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}\.csv"$')
        rows = list(csv.DictReader(io.StringIO(response.content.decode())))
        self.assertEqual(list(rows[0]), ["id", "title", "household", "task_type", "priority"])
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["title"], self.first.title)
        self.assertEqual([int(row["id"]) for row in rows], sorted(int(row["id"]) for row in rows))


    def test_empty_reports_and_exports(self):
        Task.objects.all().delete()
        response = self.client.get(reverse("workflows:task-insights"), follow=True)
        self.assertContains(response, "No tasks yet", count=2)
        self.assertEqual(response.context["total_tasks"], 0)
        rows = list(csv.reader(io.StringIO(self.client.get(reverse("workflows:task-export-csv")).content.decode())))
        self.assertEqual(len(rows), 1)

    def test_csv_neutralizes_spreadsheet_formulas(self):
        Task.objects.filter(pk=self.first.pk).update(title="=1+1")
        rows = list(csv.DictReader(io.StringIO(self.client.get(reverse("workflows:task-export-csv")).content.decode())))
        self.assertEqual(rows[0]["title"], "'=1+1")

    def test_export_and_report_reject_writes(self):
        for name in ("task-insights", "task-export-csv"):
            self.assertEqual(self.client.post(reverse("workflows:" + name)).status_code, 405)
        self.assertEqual(Task.objects.count(), 3)
