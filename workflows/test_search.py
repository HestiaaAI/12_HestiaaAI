from django.test import Client, TestCase, override_settings
from django.urls import reverse

from households.models import Workspace
from .models import Task


@override_settings(ROOT_URLCONF="workflows.test_person2_urls")
class TaskSearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        demo = Workspace.objects.create(name="Demo Household")
        other = Workspace.objects.create(name="Lakeside Apartment")
        cls.demo_groceries = Task.objects.create(workspace=demo, title="Buy groceries", priority="HIGH")
        cls.other_groceries = Task.objects.create(workspace=other, title="Buy groceries for party")
        cls.demo_laundry = Task.objects.create(workspace=demo, title="Fold laundry")

    def result_pks(self, response):
        return [task.pk for task in response.context["tasks"]]

    def test_get_filters_title_and_workspace(self):
        url = reverse("task_search:get")
        response = self.client.get(url, {"q": "groceries"})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tasks/search.html")
        self.assertEqual(self.result_pks(response), [self.demo_groceries.pk, self.other_groceries.pk])

        # Related-model lookup: mixed-case name matched through Task.workspace.
        response = self.client.get(url, {"workspace_name": "dEMO hOUSE"})
        self.assertEqual(self.result_pks(response), [self.demo_groceries.pk, self.demo_laundry.pk])

        # Both filters must match.
        response = self.client.get(url, {"q": "groceries", "workspace_name": "lakeside"})
        self.assertEqual(self.result_pks(response), [self.other_groceries.pk])
        self.assertEqual(response.context["search_method"], "GET")
        self.assertContains(response, 'value="groceries"')
        self.assertContains(response, 'value="lakeside"')
        self.assertContains(response, self.other_groceries.get_absolute_url())

    def test_post_reads_body_not_query_string(self):
        url = reverse("task_search:post") + "?q=laundry&workspace_name=demo"
        response = self.client.post(url, {"q": "groceries", "workspace_name": "lakeside"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.result_pks(response), [self.other_groceries.pk])
        self.assertEqual(response.context["search_method"], "POST")
        self.assertTrue(response.context["submitted"])
        self.assertEqual(Task.objects.count(), 3)

    def test_blank_filters_return_all_tasks(self):
        all_pks = [self.demo_groceries.pk, self.other_groceries.pk, self.demo_laundry.pk]
        response = self.client.get(reverse("task_search:get"))
        self.assertEqual(self.result_pks(response), all_pks)
        response = self.client.get(reverse("task_search:get"), {"q": "   ", "workspace_name": ""})
        self.assertEqual(self.result_pks(response), all_pks)
        response = self.client.post(reverse("task_search:post"), {"q": "  ", "workspace_name": " "})
        self.assertEqual(self.result_pks(response), all_pks)

    def test_post_get_shows_prompt(self):
        response = self.client.get(reverse("task_search:post"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["submitted"])
        self.assertContains(response, "Submit the POST form to see results.")
        self.assertNotContains(response, 'class="task-card"')
        # Both forms render with named actions and unique field IDs.
        self.assertContains(response, f'action="{reverse("task_search:get")}" method="get"')
        self.assertContains(response, f'action="{reverse("task_search:post")}" method="post"')
        for field_id in ("get-q", "get-workspace-name", "post-q", "post-workspace-name"):
            self.assertContains(response, f'id="{field_id}"', count=1)

    def test_no_matches_and_empty_database(self):
        response = self.client.get(reverse("task_search:get"), {"q": "XYZNOTAREALTASK123"})
        self.assertEqual(self.result_pks(response), [])
        self.assertContains(response, "No tasks match")
        self.assertNotContains(response, 'class="task-card"')

        Task.objects.all().delete()
        response = self.client.post(reverse("task_search:post"), {"q": ""})
        self.assertContains(response, "No tasks match")

    def test_results_escape_html(self):
        payload = "<script>alert(1)</script>"
        response = self.client.get(reverse("task_search:get"), {"q": payload})
        self.assertNotContains(response, payload)
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")

        Task.objects.create(workspace=self.demo_groceries.workspace, title=payload)
        response = self.client.get(reverse("task_search:get"), {"q": "script"})
        self.assertNotContains(response, payload)
        self.assertContains(response, "&lt;script&gt;")

    def test_post_requires_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        url = reverse("task_search:post")
        response = csrf_client.post(url, {"q": "groceries"})
        self.assertEqual(response.status_code, 403)

        form_page = csrf_client.get(url)
        token = form_page.cookies["csrftoken"].value
        response = csrf_client.post(url, {"q": "groceries", "csrfmiddlewaretoken": token})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.result_pks(response), [self.demo_groceries.pk, self.other_groceries.pk])
        self.assertEqual(Task.objects.count(), 3)

    def test_get_route_rejects_post(self):
        response = self.client.post(reverse("task_search:get"), {"q": "groceries"})
        self.assertEqual(response.status_code, 405)

    def test_result_detail_links_resolve(self):
        response = self.client.get(reverse("task_search:get"), {"q": "laundry"})
        detail = self.client.get(self.demo_laundry.get_absolute_url())
        self.assertContains(response, self.demo_laundry.get_absolute_url())
        self.assertEqual(detail.status_code, 200)
