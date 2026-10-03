import csv
import io
from datetime import datetime

from django.test import TestCase
from django.urls import reverse

from households.models import Workspace
from workflows.models import Task


class ReportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        home = Workspace.objects.create(name="Reports demo")
        cls.first = Task.objects.create(workspace=home, title='Café, "kitchen"\ncleaning', priority="HIGH", task_type="CHORE")
        cls.second = Task.objects.create(workspace=home, title="Shopping", priority="LOW", task_type="SHOPPING")
        Task.objects.create(workspace=home, title="Laundry", priority="HIGH", task_type="CHORE")

    def test_public_report_totals_groups_and_download_links(self):
        response = self.client.get(reverse("reports:task-report"))
        self.assertEqual(response.context["total_tasks"], 3)
        self.assertEqual({r["label"]: r["count"] for r in response.context["priority_summary"]}, {"High": 2, "Low": 1})
        self.assertEqual({r["label"]: r["count"] for r in response.context["type_summary"]}, {"Chore": 2, "Shopping": 1})
        self.assertTemplateUsed(response, "base.html")
        for name in ("tasks-csv", "tasks-json"):
            self.assertContains(response, reverse("reports:" + name))
        self.assertContains(self.client.get(reverse("home")), reverse("reports:task-report"))

    def test_csv_headers_order_and_quoting(self):
        response = self.client.get(reverse("reports:tasks-csv"))
        self.assertTrue(response["Content-Type"].startswith("text/csv"))
        self.assertRegex(response["Content-Disposition"], r'^attachment; filename="tasks_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}\.csv"$')
        rows = list(csv.DictReader(io.StringIO(response.content.decode())))
        self.assertEqual(list(rows[0]), ["id", "title", "household", "task_type", "priority"])
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["title"], self.first.title)
        self.assertEqual([int(row["id"]) for row in rows], sorted(int(row["id"]) for row in rows))

    def test_json_metadata_and_same_records_as_csv(self):
        response = self.client.get(reverse("reports:tasks-json"))
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertRegex(response["Content-Disposition"], r'tasks_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}\.json')
        data = response.json()
        self.assertIsNotNone(datetime.fromisoformat(data["generated_at"]).tzinfo)
        self.assertEqual(data["record_count"], len(data["tasks"]))
        self.assertEqual(data["record_count"], 3)
        self.assertIn(b'\n  "generated_at"', response.content)
        csv_rows = list(csv.DictReader(io.StringIO(self.client.get(reverse("reports:tasks-csv")).content.decode())))
        self.assertEqual([{k: str(v) for k, v in row.items()} for row in data["tasks"]], csv_rows)

    def test_empty_reports_and_exports(self):
        Task.objects.all().delete()
        response = self.client.get(reverse("reports:task-report"))
        self.assertContains(response, "No tasks yet", count=2)
        self.assertEqual(response.context["total_tasks"], 0)
        data = self.client.get(reverse("reports:tasks-json")).json()
        self.assertEqual(data["tasks"], [])
        self.assertEqual(data["record_count"], 0)
        rows = list(csv.reader(io.StringIO(self.client.get(reverse("reports:tasks-csv")).content.decode())))
        self.assertEqual(len(rows), 1)

    def test_csv_neutralizes_spreadsheet_formulas_and_json_preserves_text(self):
        Task.objects.filter(pk=self.first.pk).update(title="=1+1")
        rows = list(csv.DictReader(io.StringIO(self.client.get(reverse("reports:tasks-csv")).content.decode())))
        self.assertEqual(rows[0]["title"], "'=1+1")
        self.assertEqual(self.client.get(reverse("reports:tasks-json")).json()["tasks"][0]["title"], "=1+1")

    def test_export_and_report_reject_writes(self):
        for name in ("task-report", "tasks-csv", "tasks-json"):
            self.assertEqual(self.client.post(reverse("reports:" + name)).status_code, 405)
        self.assertEqual(Task.objects.count(), 3)
