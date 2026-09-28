from django.test import TestCase
from django.urls import reverse

from households.models import Workspace
from .models import Task


class TaskApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        demo = Workspace.objects.create(name="Demo Household")
        other = Workspace.objects.create(name="Lakeside Apartment")
        cls.demo_groceries = Task.objects.create(
            workspace=demo,
            title="Buy groceries",
            task_type="SHOPPING",
            priority="HIGH",
            description="Private note",
            default_location="Corner store",
        )
        cls.other_groceries = Task.objects.create(workspace=other, title="Buy groceries for party")
        cls.demo_laundry = Task.objects.create(workspace=demo, title="Fold laundry", task_type="CHORE")

    def get_tasks(self, **params):
        response = self.client.get(reverse("api:task-list"), params)
        self.assertEqual(response.status_code, 200)
        return response.json()["tasks"]

    def ids(self, tasks):
        return [task["id"] for task in tasks]

    def test_api_returns_exact_schema(self):
        response = self.client.get(reverse("api:task-list"))
        self.assertEqual(response["Content-Type"], "application/json")
        body = response.json()
        self.assertEqual(list(body), ["tasks"])
        self.assertEqual(
            body["tasks"][0],
            {"id": self.demo_groceries.pk, "title": "Buy groceries", "task_type": "SHOPPING", "priority": "HIGH"},
        )
        for task in body["tasks"]:
            self.assertEqual(set(task), {"id", "title", "task_type", "priority"})
        self.assertNotContains(response, "Private note")
        self.assertNotContains(response, "Corner store")
        # Deterministic primary-key ordering, independent of Task.Meta.ordering.
        self.assertEqual(
            self.ids(body["tasks"]),
            [self.demo_groceries.pk, self.other_groceries.pk, self.demo_laundry.pk],
        )

    def test_api_filters_title_and_workspace(self):
        self.assertEqual(self.ids(self.get_tasks(q="GROCERIES")), [self.demo_groceries.pk, self.other_groceries.pk])
        self.assertEqual(self.ids(self.get_tasks(workspace_name="demo")), [self.demo_groceries.pk, self.demo_laundry.pk])
        self.assertEqual(self.ids(self.get_tasks(q="groceries", workspace_name="LAKESIDE")), [self.other_groceries.pk])
        # Unknown parameters are ignored.
        self.assertEqual(len(self.get_tasks(workspace="1", page="2")), 3)

    def test_api_blank_filters_and_no_matches(self):
        self.assertEqual(len(self.get_tasks(q="   ", workspace_name="")), 3)
        self.assertEqual(self.get_tasks(q="XYZNOTAREALTASK123"), [])
        Task.objects.all().delete()
        self.assertEqual(self.get_tasks(), [])

    def test_api_is_read_only(self):
        for name in ("api:task-list", "api:response-demo"):
            with self.subTest(name=name):
                response = self.client.post(reverse(name), {"title": "Injected"})
                self.assertEqual(response.status_code, 405)
        self.assertEqual(Task.objects.count(), 3)

    def test_response_mime_types(self):
        text = self.client.get(reverse("api:response-demo"))
        self.assertEqual(text.status_code, 200)
        self.assertEqual(text["Content-Type"], "text/plain")
        self.assertEqual(text.content, b"Hestia task API")

        json_response = self.client.get(reverse("api:task-list"))
        self.assertEqual(json_response["Content-Type"], "application/json")

    def test_routes(self):
        self.assertEqual(reverse("api:task-list"), "/api/tasks/")
        self.assertEqual(reverse("api:response-demo"), "/api/response-demo/")
