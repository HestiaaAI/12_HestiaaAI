"""Regression checks for the public/private API boundary, including export aliases."""
import json
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import resolve, reverse

from api.middleware import ApiAccessMiddleware
from households.models import Workspace
from workflows.models import Task


class ApiAccessTests(TestCase):
    private_routes = (
        "/api/tasks/", "/api/response-demo/", "/api/external/products/?q=milk",
        "/api/charts/task-creations/", "/reports/tasks/export.json",
        "/reports/tasks/export.csv", "/vega-lite/chart2.json", "/vega-lite/chart2.png",
    )

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="reader")
        workspace = Workspace.objects.create(name="Private household")
        Task.objects.create(workspace=workspace, title="Private task", priority="HIGH")

    def test_anonymous_requests_cannot_read_other_apis_or_exports(self):
        with patch("api.external.requests.get") as upstream:
            for url in self.private_routes:
                with self.subTest(url=url):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 401)
                    self.assertEqual(response.json(), {"error": "Authentication required."})
                    self.assertNotIn("Location", response)
                    self.assertNotIn("Access-Control-Allow-Origin", response)
                    self.assertIn("no-store", response["Cache-Control"])
                    self.assertIn("Cookie", response["Vary"])
            upstream.assert_not_called()

    def test_public_api_is_database_backed_and_aggregate_only(self):
        response = self.client.get(reverse("api:chart-priorities"), HTTP_ORIGIN="https://vega.github.io")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(response["Access-Control-Allow-Origin"], "*")
        self.assertNotIn("Access-Control-Allow-Credentials", response)
        self.assertEqual(sum(row["count"] for row in response.json()), 1)
        for row in response.json():
            self.assertEqual(set(row), {"label", "count"})
        self.assertNotContains(response, "Private")
        Task.objects.update(priority="URGENT")
        self.assertEqual(self.client.get(reverse("api:chart-priorities")).json()[-1]["count"], 1)
        self.assertEqual(self.client.post(reverse("api:chart-priorities")).status_code, 405)

    def test_session_access_and_logout(self):
        self.client.force_login(self.user)
        for url in self.private_routes:
            if "external" in url:
                continue  # Successful external responses are covered with mocks in api.tests.
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            self.assertIn("no-store", response["Cache-Control"])
            if response.streaming:
                response.close()
        self.client.logout()
        self.assertEqual(self.client.get("/api/tasks/").status_code, 401)

    def test_anonymous_chart_page_only_embeds_public_data(self):
        response = self.client.get("/vega-lite/")
        self.assertContains(response, 'id="priority-chart"')
        self.assertNotContains(response, 'id="creation-chart"')
        self.assertNotContains(response, "/reports/tasks/")
        self.assertContains(response, "Log in")
        for url in ("/lookup/?q=milk", "/reports/tasks/"):
            self.assertEqual(self.client.get(url).status_code, 302)

    def test_future_api_route_is_private_by_default(self):
        from django.contrib.auth.models import AnonymousUser
        request = RequestFactory().get("/api/new-route/")
        request.user = AnonymousUser()
        request.resolver_match = resolve("/api/tasks/")
        request.resolver_match.url_name = "new-route"
        request.resolver_match.view_name = "api:new-route"
        response = ApiAccessMiddleware(lambda req: JsonResponse({})).process_view(request, lambda req: None, (), {})
        self.assertEqual(response.status_code, 401)

    def test_public_api_survives_team_login_required_middleware(self):
        middleware = list(settings.MIDDLEWARE)
        middleware.insert(middleware.index("api.middleware.ApiAccessMiddleware") + 1,
                          "django.contrib.auth.middleware.LoginRequiredMiddleware")
        with override_settings(MIDDLEWARE=middleware):
            response = Client().get(reverse("api:chart-priorities"))
            self.assertEqual(response.status_code, 200)

    def test_submission_spec_uses_exact_production_api_and_schema(self):
        spec = json.loads((settings.BASE_DIR / "docs/a5-member-3/group-12-vega-lite-API-demo.txt").read_text())
        self.assertEqual(spec["data"]["url"], "https://hestia12.pythonanywhere.com/api/charts/task-priorities/")
        self.assertNotIn("values", spec["data"])
        self.assertNotIn("datasets", spec)
        self.assertEqual(spec["encoding"]["x"]["field"], "label")
        self.assertEqual(spec["encoding"]["y"]["field"], "count")
