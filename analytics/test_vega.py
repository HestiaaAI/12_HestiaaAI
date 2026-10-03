from datetime import datetime, timezone

from django.test import TestCase, override_settings
from django.urls import reverse

from households.models import Workspace
from workflows.models import Task


class VegaChartTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        home = Workspace.objects.create(name="Chart demo")
        first = Task.objects.create(workspace=home, title="First", priority="HIGH")
        second = Task.objects.create(workspace=home, title="Second", priority="HIGH")
        third = Task.objects.create(workspace=home, title="Third", priority="LOW")
        Task.objects.filter(pk__in=[first.pk, second.pk]).update(created_at=datetime(2026, 9, 19, 23, 59, tzinfo=timezone.utc))
        Task.objects.filter(pk=third.pk).update(created_at=datetime(2026, 9, 21, 0, 1, tzinfo=timezone.utc))

    def test_public_priority_api_counts_and_zero_categories(self):
        response = self.client.get(reverse("api:chart-priorities"))
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(response["Access-Control-Allow-Origin"], "*")
        self.assertEqual(response.json(), [
            {"label": "Low", "count": 1}, {"label": "Medium", "count": 0},
            {"label": "High", "count": 2}, {"label": "Urgent", "count": 0},
        ])
        Task.objects.create(workspace=Workspace.objects.first(), title="New task", priority="URGENT")
        self.assertEqual(self.client.get(reverse("api:chart-priorities")).json()[-1]["count"], 1)

    def test_daily_counts_are_ordered_and_include_missing_days(self):
        self.assertEqual(self.client.get(reverse("api:chart-creations")).json(), [
            {"date": "2026-09-19", "count": 2},
            {"date": "2026-09-20", "count": 0},
            {"date": "2026-09-21", "count": 1},
        ])

    def test_empty_database(self):
        Task.objects.all().delete()
        self.assertEqual(self.client.get(reverse("api:chart-creations")).json(), [])
        self.assertTrue(all(row["count"] == 0 for row in self.client.get(reverse("api:chart-priorities")).json()))

    def test_embedded_charts_and_specs_use_real_api_urls(self):
        response = self.client.get(reverse("vega:charts"))
        self.assertTemplateUsed(response, "base.html")
        for chart, api in [("chart1", "chart-priorities"), ("chart2", "chart-creations")]:
            spec_url = reverse("vega:spec", args=[chart])
            self.assertContains(response, spec_url)
            spec = self.client.get(spec_url).json()
            self.assertEqual(spec["data"]["url"], "http://testserver" + reverse("api:" + api))
            self.assertNotIn("values", spec["data"])
            self.assertNotIn("datasets", spec)
            self.assertEqual(self.client.get(reverse("api:" + api)).status_code, 200)
        self.assertContains(self.client.get(reverse("home")), reverse("vega:charts"))

    @override_settings(DEBUG=False)
    def test_saved_outputs_and_specs_work_without_debug(self):
        for chart in ("chart1", "chart2"):
            response = self.client.get(reverse("vega:image", args=[chart]))
            self.assertEqual(response["Content-Type"], "image/png")
            self.assertTrue(b"".join(response.streaming_content).startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertEqual(self.client.get(reverse("vega:spec", args=[chart])).status_code, 200)

    def test_unknown_chart_and_write_requests(self):
        for suffix in ("json", "png"):
            self.assertEqual(self.client.get(f"/vega-lite/unknown.{suffix}").status_code, 404)
        for url in ("/api/charts/task-priorities/", "/api/charts/task-creations/", "/vega-lite/", "/vega-lite/chart1.json", "/vega-lite/chart1.png"):
            self.assertEqual(self.client.post(url).status_code, 405)
