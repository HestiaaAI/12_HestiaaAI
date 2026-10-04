from unittest.mock import patch

import requests
from django.test import TestCase
from django.urls import reverse

from households.models import Workspace
from inventory.models import Product, ShoppingListEntry
from workflows.models import Task

from .external import OPEN_FOOD_FACTS_SEARCH_URL, REQUEST_TIMEOUT_SECONDS


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Server Error")

    def json(self):
        return self.payload


PUBLIC_HITS = {
    "count": 42,
    "is_count_exact": True,
    "hits": [
        {
            "code": "111",
            "product_name": "Oat milk",
            "brands": ["Plain Oats"],
            "nutrition_grades": "b",
            "quantity": "1 L",
            "ingredients_text": "This private field must not be returned.",
        },
        {
            "code": "222",
            "product_name": "Barista oat milk",
            "brands": "Cafe Oats",
            "nutrition_grades": "c",
            "quantity": "",
        },
        {
            "code": "333",
            "product_name": "Sparkling water",
            "brands": [],
            "nutrition_grades": "",
            "quantity": "500 ml",
        },
    ],
}


class ProductCompareApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        demo = Workspace.objects.create(name="Demo Household")
        cls.product = Product.objects.create(workspace=demo, canonical_name="Oat milk")
        cls.item = ShoppingListEntry.objects.create(
            workspace=demo,
            item_name="Barista oat milk",
            state=ShoppingListEntry.EntryState.SUGGESTED,
            reason="Private shopping note",
        )
        cls.task = Task.objects.create(
            workspace=demo,
            title="Buy oat milk",
            task_type=Task.TaskType.SHOPPING,
            description="Private task note",
        )
        Task.objects.create(
            workspace=demo,
            title="Buy oat milk flour",
            task_type=Task.TaskType.CHORE,
        )

    def test_missing_query_does_not_call_the_api(self):
        with patch("api.external.requests.get") as get:
            response = self.client.get(reverse("api:product-compare"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"ok": False, "error": "Provide a search term with ?q=."})
        get.assert_not_called()

    def test_combines_public_products_with_household_rows(self):
        with patch("api.external.requests.get", return_value=FakeResponse(PUBLIC_HITS)) as get:
            response = self.client.get(reverse("api:product-compare"), {"q": "oat milk"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        get.assert_called_once_with(
            OPEN_FOOD_FACTS_SEARCH_URL,
            params={
                "q": "oat milk",
                "page_size": 5,
                "fields": "code,product_name,brands,nutrition_grades,quantity",
            },
            headers={"User-Agent": "HestiaAI-INFO490/1.0 (educational class project)"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["query"], "oat milk")
        self.assertEqual(body["source"]["name"], "Open Food Facts")
        self.assertEqual(
            body["internal"]["products"],
            [{"id": self.product.pk, "name": "Oat milk", "workspace": "Demo Household"}],
        )
        self.assertEqual(body["internal"]["shopping_items"][0]["name"], "Barista oat milk")
        self.assertEqual(body["internal"]["shopping_tasks"], [
            {"id": self.task.pk, "title": "Buy oat milk", "workspace": "Demo Household"},
        ])
        self.assertEqual(
            [product["name"] for product in body["external"]["products"]],
            ["Oat milk", "Barista oat milk", "Sparkling water"],
        )
        self.assertEqual(body["external"]["products"][0]["brands"], "Plain Oats")
        self.assertEqual(body["external"]["products"][1]["brands"], "Cafe Oats")
        self.assertNotIn("ingredients_text", body["external"]["products"][0])
        self.assertNotContains(response, "Private shopping note")
        self.assertNotContains(response, "Private task note")
        self.assertEqual(body["analysis"]["nutriscore_counts"], [
            {"grade": "b", "count": 1},
            {"grade": "c", "count": 1},
            {"grade": "unknown", "count": 1},
        ])
        self.assertEqual(body["analysis"]["already_in_household"], ["Oat milk", "Barista oat milk"])
        self.assertEqual(body["analysis"]["new_to_household"], ["Sparkling water"])
        self.assertEqual(body["analysis"]["internal_shopping_task_count"], 1)
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(ShoppingListEntry.objects.count(), 1)

    def test_upstream_http_error_is_handled(self):
        with patch("api.external.requests.get", return_value=FakeResponse({}, status_code=503)):
            response = self.client.get(reverse("api:product-compare"), {"q": "milk"})
        self.assertEqual(response.status_code, 502)
        self.assertFalse(response.json()["ok"])

    def test_timeout_is_handled(self):
        with patch("api.external.requests.get", side_effect=requests.Timeout("timed out")):
            response = self.client.get(reverse("api:product-compare"), {"q": "milk"})
        self.assertEqual(response.status_code, 502)
        self.assertIn("could not be reached", response.json()["error"])

    def test_api_is_read_only(self):
        response = self.client.post(reverse("api:product-compare"), {"q": "milk"})
        self.assertEqual(response.status_code, 405)

    def test_page_renders_the_comparison(self):
        with patch("api.external.requests.get", return_value=FakeResponse(PUBLIC_HITS)):
            response = self.client.get(reverse("product-lookup"), {"q": "oat milk"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Oat milk")
        self.assertContains(response, "Open the JSON API")
        self.assertContains(response, reverse("api:product-compare"))

    def test_blank_page_does_not_call_the_api(self):
        with patch("api.external.requests.get") as get:
            response = self.client.get(reverse("product-lookup"), {"q": "   "})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter a product name")
        get.assert_not_called()
