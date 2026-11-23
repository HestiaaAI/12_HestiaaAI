from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from households.models import Membership, Workspace
from households.sharing import change_circle_audience
from .models import Expense, PurchaseList, Settlement
from .purchases import confirm_receipts, create_item, prepare_receipts
from .services import balances, request_payment, save_expense


class VisibilityFlowTests(TestCase):
    def setUp(self):
        self.home = Workspace.objects.create(name="Test household")
        self.a, self.b, self.c, self.owner = [
            Membership.objects.create(
                workspace=self.home, role=role, display_name=name,
                user=get_user_model().objects.create_user(username=name),
            )
            for name, role in (("A", "ADULT"), ("B", "ADULT"), ("C", "ADULT"), ("D", "OWNER"))
        ]
        self.clients = {}
        for member in (self.a, self.b, self.c, self.owner):
            client = Client()
            client.force_login(member.user)
            self.clients[member.pk] = client

    def url(self, route, *args):
        return reverse(route, args=(self.home.pk, *args))

    def create_list(self):
        response = self.clients[self.a.pk].post(self.url("groceries:list-create"), {
            "title": "Surprise birthday", "visibility": "SELECTED",
            "readers": [self.b.pk, self.c.pk], "confirm": "on",
        })
        self.assertEqual(response.status_code, 302)
        return PurchaseList.objects.get(title="Surprise birthday")

    def test_receipt_ledger_and_pages_exclude_household_owner(self):
        shopping = self.create_list()
        item = create_item(self.a, "Birthday candles", 1, "household", purchase_list=shopping)
        public = create_item(self.a, "Public milk", 1, "household")
        owner = self.clients[self.owner.pk]
        self.assertContains(owner.get(reverse("expenses:today")), public.name)
        self.assertNotContains(owner.get(reverse("expenses:today")), item.name)
        self.assertEqual(owner.get(self.url("groceries:named-list", shopping.pk)).status_code, 404)
        self.assertEqual(owner.post(self.url("groceries:shopping-check", item.pk)).status_code, 404)
        self.assertContains(self.clients[self.b.pk].get(reverse("expenses:today")), item.name)
        source = {
            "payer": self.a, "date": str(timezone.localdate()), "total": Decimal("15"),
            "tax": Decimal("0"), "discount": Decimal("0"),
            "text": "Birthday candles 12.00\nPublic milk 3.00\nTOTAL 15.00",
        }
        draft = prepare_receipts(self.a, [source])
        rows = draft.payload["receipts"][0]["rows"]
        result = confirm_receipts(self.a, draft.pk, rows, confirmed=True)
        self.assertEqual(confirm_receipts(self.a, draft.pk, rows, confirmed=True), result)
        expense = Expense.objects.get(title=item.name)
        self.assertEqual(expense.circle, shopping.circle)
        self.assertEqual(balances(self.home, circle=shopping.circle)[self.b.pk], -400)
        self.assertEqual(balances(self.home)[self.b.pk], -75)
        self.assertEqual(owner.get(self.url("expenses:detail", expense.pk)).status_code, 404)
        self.assertEqual(owner.get(self.url("expenses:overview") + f"?circle={shopping.circle_id}").status_code, 404)
        for route in ("expenses:overview", "expenses:trends", "expenses:activity", "expenses:export"):
            self.assertNotContains(owner.get(self.url(route)), item.name)
        self.assertEqual(self.clients[self.b.pk].get(self.url("groceries:receipt-split-review", draft.pk)).status_code, 404)
        self.assertContains(self.clients[self.b.pk].get(self.url("expenses:detail", expense.pk)), item.name)
        payment = request_payment(self.b, self.a, 200, "", uuid4(), circle=shopping.circle)
        self.assertEqual(balances(self.home, circle=shopping.circle)[self.b.pk], -400)
        self.assertNotContains(owner.get(reverse("expenses:reminders")), "Review settlement")
        self.assertContains(self.clients[self.a.pk].get(reverse("expenses:reminders")), "Needs confirmation")
        self.assertEqual(owner.post(self.url("expenses:payment-action", payment.pk, "confirm")).status_code, 404)
        self.assertEqual(self.clients[self.a.pk].post(self.url("expenses:payment-action", payment.pk, "confirm")).status_code, 302)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Settlement.Status.CONFIRMED)
        self.assertEqual(balances(self.home, circle=shopping.circle)[self.b.pk], -200)
        self.assertEqual(balances(self.home)[self.b.pk], -75)
        with self.assertRaisesMessage(ValidationError, "financial history"):
            change_circle_audience(
                actor=self.a, circle_id=shopping.circle_id, visibility="ONLY_ME",
                member_ids=[], expected_version=shopping.circle.version,
            )
        Membership.objects.filter(pk=self.b.pk).update(is_active=False)
        self.assertEqual(self.clients[self.b.pk].get(self.url("expenses:detail", expense.pk)).status_code, 302)

    def test_private_expense_rejects_other_payer(self):
        response = self.clients[self.a.pk].post(self.url("groceries:list-create"), {
            "title": "Only my list", "visibility": "ONLY_ME", "confirm": "on",
        })
        self.assertEqual(response.status_code, 302)
        circle = PurchaseList.objects.get(title="Only my list").circle
        with self.assertRaises(ValidationError):
            save_expense(self.a, {"amount": Decimal("1"), "paid_by": self.b}, {self.a.pk: 100}, uuid4(), circle=circle)

    def test_named_list_edit_rejects_stale_item_form(self):
        shopping = self.create_list()
        client = self.clients[self.a.pk]
        edit = self.url("groceries:list-audience", shopping.pk)
        initial = f"{shopping.circle_id}:{shopping.circle.version}"
        response = client.post(edit, {"visibility": "HOUSEHOLD", "audience": initial, "confirm": "on"})
        self.assertEqual(response.status_code, 302)
        shopping.refresh_from_db()
        self.assertEqual(shopping.circle.visibility, "HOUSEHOLD")
        response = client.post(self.url("groceries:named-list", shopping.pk), {
            "name": "Old private note", "quantity": 1, "scope": "personal", "audience": initial,
        })
        self.assertContains(response, "Sharing changed")
        self.assertFalse(shopping.purchaseitem_set.exists())

    def test_restricted_receipt_cannot_be_posted_to_default_by_omitting_match(self):
        from unittest.mock import patch

        shopping = self.create_list()
        item = create_item(self.a, "Hidden flowers", 1, "personal", purchase_list=shopping)
        upload = self.url("groceries:receipt-split") + f"?list={shopping.pk}"
        page = self.clients[self.a.pk].get(upload)
        self.assertContains(page, f'name="audience" value="{shopping.circle_id}:{shopping.circle.version}"')
        self.assertEqual(self.clients[self.owner.pk].get(upload).status_code, 404)
        data = {
            "payer": self.a, "date": str(timezone.localdate()), "total": Decimal("12"),
            "tax": Decimal("0"), "discount": Decimal("0"), "text": "Hidden flowers 12.00",
        }
        with patch("expenses.purchase_matching.requests.post") as provider:
            draft = prepare_receipts(self.a, [data], use_ai=True, purchase_list=shopping)
            provider.assert_not_called()
        row = draft.payload["receipts"][0]["rows"][0]
        self.assertEqual(row["item_id"], item.pk)
        with self.assertRaises(ValidationError):
            confirm_receipts(self.a, draft.pk, [
                {**row, "item_id": None, "recipient_ids": [self.owner.pk]},
            ], confirmed=True)
        self.assertFalse(Expense.objects.exists())

    def test_inbox_joins_only_on_verified_recipient_post(self):
        from allauth.account.models import EmailAddress
        from households.models import HouseholdInvitation

        recipient = get_user_model().objects.create_user(username="guest", email="guest@example.test")
        address = EmailAddress.objects.create(user=recipient, email=recipient.email, verified=False)
        invite = HouseholdInvitation.objects.create(
            workspace=self.home, email=recipient.email, invited_by=self.owner, token_digest="digest-only",
            expires_at=timezone.now() + timedelta(days=1),
        )
        client = Client(enforce_csrf_checks=True)
        client.force_login(recipient)
        inbox = reverse("expenses:reminders")
        action = reverse("expenses:inbox-invite", args=[invite.pk])
        response = client.get(inbox)
        self.assertNotContains(response, self.home.name)
        address.verified = True
        address.save(update_fields=["verified"])
        response = client.get(inbox)
        self.assertContains(response, self.home.name)
        self.assertNotContains(response, invite.token_digest)
        self.assertFalse(Membership.objects.filter(user=recipient, workspace=self.home).exists())
        self.assertEqual(client.get(action).status_code, 405)
        self.assertEqual(client.post(action).status_code, 403)
        csrf = client.cookies["csrftoken"].value
        self.assertEqual(client.post(action, HTTP_X_CSRFTOKEN=csrf).status_code, 302)
        self.assertTrue(Membership.objects.filter(user=recipient, workspace=self.home, is_active=True).exists())
        self.assertEqual(client.post(action, HTTP_X_CSRFTOKEN=csrf).status_code, 404)

    def test_today_uses_household_day_and_deduplicates_bills(self):
        from datetime import datetime, timezone as utc
        from unittest.mock import patch
        from workflows.models import Task, TaskOccurrence
        from .models import RecurringBill

        self.home.timezone = "America/Chicago"
        self.home.save(update_fields=["timezone"])
        day = datetime(2026, 11, 24, 3, tzinfo=utc.utc)
        task = Task.objects.create(workspace=self.home, title="Wash dishes")
        TaskOccurrence.objects.create(task=task, due_at=day)
        upcoming = Task.objects.create(workspace=self.home, title="Take out bins")
        TaskOccurrence.objects.create(task=upcoming, due_at=day + timedelta(hours=4))
        bill_task = Task.objects.create(workspace=self.home, title="Generated electric task")
        TaskOccurrence.objects.create(task=bill_task, due_at=day)
        RecurringBill.objects.create(
            workspace=self.home, created_by=self.a, paid_by=self.a, title="Electricity due",
            amount_cents=4500, next_due=datetime(2026, 11, 23).date(), task=bill_task,
        )
        with patch("django.utils.timezone.now", return_value=day):
            response = self.clients[self.a.pk].get(reverse("expenses:today"))
        self.assertContains(response, "Wash dishes")
        self.assertContains(response, "Electricity due")
        self.assertNotContains(response, "Take out bins")
        self.assertNotContains(response, "Generated electric task")
        self.assertFalse(Expense.objects.exists())

    def test_settlement_queries_are_bounded_as_ledger_grows(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        from .models import ExpenseShare
        from .policies import household_circle

        circle = household_circle(self.home)

        def add_expenses(count):
            records = Expense.objects.bulk_create([
                Expense(
                    workspace=self.home, circle=circle, paid_by=self.a, created_by=self.a,
                    title="Public expense", amount_cents=100, date=timezone.localdate(),
                    split_method="equal",
                ) for _ in range(count)
            ])
            ExpenseShare.objects.bulk_create([
                ExpenseShare(expense=record, member=self.b, amount_cents=100) for record in records
            ])

        def query_count():
            with CaptureQueriesContext(connection) as captured:
                response = self.clients[self.b.pk].get(self.url("expenses:settle"))
            self.assertEqual(response.status_code, 200)
            return len(captured)

        add_expenses(10)
        small = query_count()
        add_expenses(990)
        self.assertEqual(query_count(), small)

    def test_switching_households_closes_direct_list_and_draft_routes(self):
        shopping = self.create_list()
        item = create_item(self.a, "Private decorations", 1, "personal", purchase_list=shopping)
        draft = prepare_receipts(self.a, [{
            "payer": self.a, "date": str(timezone.localdate()), "total": Decimal("4"),
            "tax": Decimal("0"), "discount": Decimal("0"), "text": "Private decorations 4.00",
        }], purchase_list=shopping)
        other = Workspace.objects.create(name="Other home")
        Membership.objects.create(workspace=other, user=self.a.user, display_name="A")
        client = self.clients[self.a.pk]
        self.assertEqual(client.post(reverse("households:switch"), {"workspace_id": other.pk}).status_code, 302)
        self.assertNotContains(client.get(reverse("expenses:today")), item.name)
        self.assertEqual(client.get(self.url("groceries:named-list", shopping.pk)).status_code, 404)
        self.assertEqual(client.get(self.url("groceries:receipt-split-review", draft.pk)).status_code, 404)


    def test_mutable_named_list_candidates_stay_local(self):
        from unittest.mock import patch

        response = self.clients[self.a.pk].post(self.url("groceries:list-create"), {
            "title": "Mutable public list", "visibility": "HOUSEHOLD", "confirm": "on",
        })
        self.assertEqual(response.status_code, 302)
        shopping = PurchaseList.objects.get(title="Mutable public list")
        item = create_item(self.a, "Gift wrap", 1, "personal", purchase_list=shopping)
        with patch("expenses.purchase_matching.requests.post") as provider:
            draft = prepare_receipts(self.a, [{
                "payer": self.a, "date": str(timezone.localdate()), "total": Decimal("3"),
                "tax": Decimal("0"), "discount": Decimal("0"), "text": "Gift wrap 3.00",
            }], use_ai=True)
            provider.assert_not_called()
        self.assertEqual(draft.payload["receipts"][0]["rows"][0]["item_id"], item.pk)

    def test_worker_checks_current_session_household_and_reminder_readership(self):
        from .models import BillReminder, RecurringBill

        bill = RecurringBill.objects.create(
            workspace=self.home, title="Utility bill", created_by=self.a, paid_by=self.a,
            next_due=timezone.localdate(), amount_cents=100,
        )
        notice = BillReminder.objects.create(bill=bill, user=self.a.user, due=bill.next_due)
        url = reverse("expenses:push-visible", args=[notice.pk])
        client = self.clients[self.a.pk]
        response = client.get(url)
        self.assertEqual(response.status_code, 204)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(self.clients[self.b.pk].get(url).status_code, 404)
        other = Workspace.objects.create(name="Other home")
        Membership.objects.create(workspace=other, user=self.a.user, display_name="A")
        client.post(reverse("households:switch"), {"workspace_id": other.pk})
        self.assertEqual(client.get(url).status_code, 404)
        client.logout()
        self.assertEqual(client.get(url).status_code, 401)
