from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from households.models import Membership, Workspace
from inventory.expiry import household_today
from inventory.models import GroceryBatch
from workflows.models import Task, TaskOccurrence


class GroceryTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.home = Workspace.objects.create(name="Maple House")
        users = get_user_model().objects
        cls.owner = users.create_user(username="sam")
        cls.roommate = users.create_user(username="alex")
        cls.outsider = users.create_user(username="taylor")
        for user in (cls.owner, cls.roommate):
            Membership.objects.create(workspace=cls.home, user=user, display_name=user.username)
        other = Workspace.objects.create(name="Other House")
        Membership.objects.create(workspace=other, user=cls.outsider, display_name="Taylor")
        cls.today = household_today(cls.home)

    def url(self, page, batch=None):
        args = [self.home.pk]
        if batch:
            args.append(batch.pk)
        return reverse(f"groceries:{page}", args=args)

    def add(self, day, quantity="1"):
        return self.client.post(self.url("add"), {
            "name": "Whole milk", "quantity": quantity, "unit": "carton",
            "storage": "fridge", "expires_on": day.isoformat(),
        })

class GroceryWorkflowTests(GroceryTestCase):
    def test_roommates_share_distinct_batches_and_can_edit_or_close_them(self):
        self.client.force_login(self.owner)
        self.assertRedirects(self.add(self.today + timedelta(days=1)), self.url("workspace"))
        self.assertRedirects(self.add(self.today + timedelta(days=8)), self.url("workspace"))
        self.assertContains(self.add(self.today, quantity="0"), "greater than or equal")
        first, second = GroceryBatch.objects.order_by("expires_on")
        self.client.force_login(self.roommate)
        page = self.client.get(self.url("workspace"))
        self.assertContains(page, "Due within 3 days")
        self.assertContains(page, "Whole milk", count=3)
        form = self.client.get(self.url("edit", first))
        self.assertContains(form, first.expires_on.isoformat())
        self.client.post(self.url("edit", first), {
            "name": first.name, "quantity": "0.5", "unit": first.unit, "storage": first.storage,
            "expires_on": first.expires_on.isoformat(),
        })
        first.refresh_from_db()
        self.assertEqual(str(first.quantity), "0.500")
        self.assertEqual(self.client.get(self.url("close", first)).status_code, 405)
        self.client.post(self.url("close", first), {"state": "consumed"})
        self.client.post(self.url("close", first), {"state": "discarded"})
        self.client.post(self.url("close", second), {"state": "discarded"})
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.state, "consumed")
        self.assertEqual(second.state, "discarded")

    @patch("inventory.grocery_ai.meal_idea", return_value="Use the milk to make pancakes.")
    def test_suggestion_is_explicitly_approved_and_private(self, model):
        self.client.force_login(self.owner)
        self.add(self.today - timedelta(days=1))
        self.add(self.today)
        draft = self.client.post(self.url("suggest"))
        self.assertContains(draft, "Use the milk to make pancakes.")
        self.assertEqual([batch.expires_on for batch in model.call_args.args[0]], [self.today])
        self.assertFalse(Task.objects.exists())
        token = draft.context["suggestion_token"]
        self.client.force_login(self.roommate)
        self.client.post(self.url("approve"), {"suggestion": token})
        self.assertFalse(Task.objects.exists())
        self.client.force_login(self.owner)
        self.client.post(self.url("approve"), {"suggestion": token})
        self.client.post(self.url("approve"), {"suggestion": token})
        task = Task.objects.get()
        self.assertEqual(TaskOccurrence.objects.filter(task=task).count(), 1)
        self.client.force_login(self.roommate)
        self.assertContains(self.client.get(task.get_absolute_url()), "Use the milk to make pancakes.")
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(self.url("workspace")).status_code, 404)
        self.assertEqual(self.client.get(task.get_absolute_url()).status_code, 404)
        self.assertNotContains(self.client.get(reverse("workflows:task-cbv-generic")), task.title)

    @patch("inventory.grocery_ai.meal_idea", return_value="Use the milk to make pancakes.")
    def test_changed_stock_invalidates_draft_and_expiry_command_uses_same_window(self, model):
        self.client.force_login(self.owner)
        self.add(self.today + timedelta(days=3))
        self.add(self.today + timedelta(days=4))
        self.add(self.today - timedelta(days=1))
        report = StringIO()
        call_command("check_grocery_expiry", stdout=report)
        self.assertIn("1 past date, 1 due soon", report.getvalue())
        draft = self.client.post(self.url("suggest")).context["suggestion_token"]
        batch = GroceryBatch.objects.get(expires_on=self.today + timedelta(days=3))
        self.client.post(self.url("close", batch), {"state": "consumed"})
        self.assertRedirects(self.client.post(self.url("approve"), {"suggestion": draft}),
                             self.url("workspace"))
        self.assertFalse(Task.objects.exists())


class ReceiptScanTests(GroceryTestCase):
    def test_receipt_review_does_not_save_until_confirmed(self):
        self.client.force_login(self.owner)
        page = self.client.post(self.url("scan"), {
            "action": "review",
            "receipt_text": "2 x WHOLE MILK 5.98\nBANANAS 0.82\n1.12 lb @ $0.73/lb\nTOTAL 6.80\n",
        })
        self.assertContains(page, "WHOLE MILK")
        self.assertContains(page, "BANANAS")
        self.assertEqual(len(page.context["review"].initial), 2)
        self.assertEqual(page.context["review"].initial[1]["quantity"], "1.12")
        self.assertFalse(GroceryBatch.objects.exists())

        data = {
            "action": "save", "form-TOTAL_FORMS": "2", "form-INITIAL_FORMS": "2",
            "form-0-name": "Whole milk", "form-0-quantity": "2", "form-0-unit": "carton",
            "form-0-storage": "fridge", "form-0-expires_on": self.today.isoformat(),
            "form-1-name": "Bananas", "form-1-quantity": "", "form-1-unit": "lb",
            "form-1-storage": "pantry",
        }
        self.assertContains(self.client.post(self.url("scan"), data), "This field is required.")
        self.assertFalse(GroceryBatch.objects.exists())
        data["form-1-DELETE"] = "on"
        self.assertRedirects(self.client.post(self.url("scan"), data), self.url("workspace"))
        batch = GroceryBatch.objects.get()
        self.assertEqual((batch.workspace, batch.name, batch.expires_on), (self.home, "Whole milk", self.today))

    def test_outsider_cannot_scan_for_another_household(self):
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(self.url("scan")).status_code, 404)
