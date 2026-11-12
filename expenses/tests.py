"""Ledger correctness and household boundaries through the actual Django pages."""
from decimal import Decimal
from uuid import uuid4
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from households.models import Membership, Workspace
from .forms import ExpenseForm
from .models import Expense, ExpenseShare, Settlement
from .services import balances, request_payment, resolve_payment, save_expense, void_expense


class ExpenseTests(TestCase):
    def setUp(self):
        self.home = Workspace.objects.create(name="Maple House")
        self.other_home = Workspace.objects.create(name="Other House")
        self.members = []
        for name in ["Shivani", "Alex", "Jamie"]:
            user = get_user_model().objects.create_user(username=name.lower(), password="test-only-password")
            self.members.append(Membership.objects.create(workspace=self.home, user=user, display_name=name))
        self.shivani, self.alex, self.jamie = self.members
        self.stranger = Membership.objects.create(workspace=self.other_home,
            user=get_user_model().objects.create_user(username="outsider"), display_name="Outsider")
        self.client.force_login(self.shivani.user)

    def data(self, amount="10.00", **overrides):
        return {
            "title": "Our groceries", "amount": Decimal(amount), "paid_by": self.shivani,
            "date": timezone.localdate(), "category": "groceries", "split_method": "equal",
            "note": "", **overrides,
        }

    def expense(self):
        return save_expense(self.shivani, self.data(), {self.shivani.pk: 500, self.alex.pk: 500}, uuid4())

    def url(self, name="overview", **kwargs):
        return reverse("expenses:" + name, kwargs={"workspace_id": self.home.pk, **kwargs})

    def post_data(self, **overrides):
        return {"title": "Our groceries", "amount": "10.00", "paid_by": self.shivani.pk,
                "date": str(timezone.localdate()), "category": "groceries", "split_method": "equal",
                "participants": [self.shivani.pk, self.alex.pk, self.jamie.pk], "request_token": str(uuid4()),
                **overrides}

    def test_equal_split_accounts_for_every_cent_and_duplicate_submit(self):
        data = self.post_data()
        response = self.client.post(self.url("add"), data)
        self.assertEqual(response.status_code, 302)
        expense = Expense.objects.get()
        self.assertEqual(list(expense.shares.order_by("member_id").values_list("amount_cents", flat=True)), [334,333,333])
        self.client.post(self.url("add"), data)
        self.assertEqual(Expense.objects.count(), 1)
        self.assertEqual(sum(balances(self.home).values()), 0)

    def test_custom_split_must_match_and_members_cannot_be_forged(self):
        data = self.post_data(split_method="custom", **{
            f"share_{self.shivani.pk}": "2.00", f"share_{self.alex.pk}": "3.00", f"share_{self.jamie.pk}": "4.00"})
        self.assertContains(self.client.post(self.url("add"), data), "must add up")
        self.assertEqual(Expense.objects.count(), 0)
        data[f"share_{self.jamie.pk}"] = "5.00"
        self.assertEqual(self.client.post(self.url("add"), data).status_code, 302)
        forged = self.post_data(participants=[self.stranger.pk])
        self.assertEqual(self.client.post(self.url("add"), forged).status_code, 200)
        self.assertEqual(Expense.objects.count(), 1)

    def test_payer_can_be_outside_selected_split(self):
        data = self.post_data(participants=[self.alex.pk], amount="0.01")
        self.client.post(self.url("add"), data)
        self.assertEqual(balances(self.home), {self.shivani.pk: 1, self.alex.pk: -1})

    def test_household_isolation_including_read_edit_and_payments(self):
        expense = self.expense()
        self.client.force_login(self.stranger.user)
        for name, extra in [("overview", {}), ("detail", {"expense_id":expense.pk}),
                            ("edit", {"expense_id":expense.pk}), ("payment", {})]:
            self.assertEqual(self.client.get(self.url(name, **extra)).status_code, 404)
        self.assertEqual(self.client.post(self.url("delete", expense_id=expense.pk), {"version":1}).status_code, 404)
        self.assertFalse(Expense.objects.get().voided_at)

    def test_login_csrf_and_post_only_actions(self):
        expense = self.expense()
        self.assertEqual(self.client.get(self.url("delete", expense_id=expense.pk)).status_code, 405)
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.shivani.user)
        self.assertEqual(protected.post(self.url("add"), self.post_data()).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(self.url()).status_code, 302)

    def test_other_roommate_cannot_edit_and_owner_can(self):
        expense = self.expense()
        self.client.force_login(self.jamie.user)
        self.assertEqual(self.client.get(self.url("edit", expense_id=expense.pk)).status_code, 403)
        self.jamie.role = Membership.MemberRole.OWNER
        self.jamie.save()
        self.assertEqual(self.client.get(self.url("edit", expense_id=expense.pk)).status_code, 200)

    def test_edit_version_prevents_overwriting_later_changes(self):
        expense = self.expense()
        data = self.data("12.00")
        save_expense(self.shivani, data, {self.shivani.pk:600,self.alex.pk:600}, uuid4(), expense.pk, 1)
        with self.assertRaises(ValidationError):
            save_expense(self.shivani, data, {self.shivani.pk:600,self.alex.pk:600}, uuid4(), expense.pk, 1)
        self.assertEqual(balances(self.home)[self.alex.pk], -600)

    def test_soft_delete_updates_balances_and_preserves_purchase(self):
        expense = self.expense()
        void_expense(self.shivani, expense.pk, 1)
        self.assertEqual(balances(self.home), {})
        self.assertEqual(Expense.objects.count(), 1)

    def test_payment_waits_for_receiver_and_changes_balance_once(self):
        self.expense()
        token = uuid4()
        payment = request_payment(self.alex, self.shivani, 500, "Paid cash", token)
        self.assertEqual(request_payment(self.alex, self.shivani, 500, "", token).pk, payment.pk)
        self.assertEqual(balances(self.home)[self.alex.pk], -500)
        with self.assertRaises(PermissionDenied):
            resolve_payment(self.alex, payment.pk, "confirm")
        with self.assertRaises(PermissionDenied):
            resolve_payment(self.jamie, payment.pk, "confirm")
        self.client.post(self.url("payment-action", payment_id=payment.pk, action="confirm"))
        self.assertEqual(balances(self.home)[self.alex.pk], 0)
        self.client.post(self.url("payment-action", payment_id=payment.pk, action="confirm"))
        self.assertEqual(balances(self.home)[self.alex.pk], 0)

    def test_cannot_overpay_or_reserve_same_balance_twice(self):
        self.expense()
        with self.assertRaises(ValidationError):
            request_payment(self.alex, self.shivani, 501, "", uuid4())
        request_payment(self.alex, self.shivani, 400, "", uuid4())
        with self.assertRaises(ValidationError):
            request_payment(self.alex, self.shivani, 200, "", uuid4())

    def test_declined_payment_frees_reservation_without_changing_balance(self):
        self.expense()
        payment = request_payment(self.alex, self.shivani, 500, "", uuid4())
        resolve_payment(self.shivani, payment.pk, "reject")
        self.assertEqual(balances(self.home)[self.alex.pk], -500)
        self.assertEqual(request_payment(self.alex, self.shivani, 500, "", uuid4()).status, "pending")

    def test_confirmation_rechecks_changed_expenses(self):
        expense = self.expense()
        payment = request_payment(self.alex, self.shivani, 500, "", uuid4())
        void_expense(self.shivani, expense.pk, 1)
        with self.assertRaises(ValidationError):
            resolve_payment(self.shivani, payment.pk, "confirm")
        payment.refresh_from_db()
        self.assertEqual(payment.status, Settlement.Status.PENDING)

    def test_inactive_roommate_loses_access_but_keeps_history(self):
        self.expense()
        self.alex.is_active = False
        self.alex.save()
        self.client.force_login(self.alex.user)
        self.assertRedirects(self.client.get(self.url()), reverse("households:onboarding"), fetch_redirect_response=False)
        self.assertEqual(balances(self.home)[self.alex.pk], -500)

    def test_switcher_lists_only_current_memberships(self):
        self.client.force_login(self.stranger.user)
        self.assertEqual(self.client.get(reverse("expenses:home")).status_code, 302)
        self.assertEqual(self.client.get(self.url()).status_code, 404)

    def test_precision_and_negative_amounts_are_rejected(self):
        for value in ["1.001", "-2", "0", "NaN", "Infinity", "1000000.00"]:
            form = ExpenseForm(self.post_data(amount=value), workspace=self.home, actor=self.shivani)
            self.assertFalse(form.is_valid(), value)

    def test_display_escapes_notes_and_payment_prefill_preserves_cents(self):
        expense = self.expense()
        expense.title = "<script>alert(1)</script>"
        expense.save()
        response = self.client.get(self.url("detail", expense_id=expense.pk))
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.client.force_login(self.alex.user)
        response = self.client.get(self.url())
        self.assertContains(response, "amount=5.00")

    def test_percent_and_weighted_splits_round_to_exact_total(self):
        for method, weights, expected in [("percent", [34,33,33], [340,330,330]), ("shares", [1,1,1], [334,333,333])]:
            data = self.post_data(split_method=method, **{f"share_{m.pk}": str(v) for m,v in zip(self.members,weights)})
            form = ExpenseForm(data, workspace=self.home, actor=self.shivani)
            self.assertTrue(form.is_valid(), form.errors)
            self.assertEqual(list(form.shares.values()), expected)
            response = self.client.post(self.url("add"), data)
            self.assertEqual(response.status_code, 302)
            record = Expense.objects.latest("pk")
            edit = ExpenseForm(workspace=self.home, actor=self.shivani, expense=record)
            self.assertEqual(Decimal(edit.initial[f"share_{self.shivani.pk}"]), Decimal(weights[0]))
        bad = ExpenseForm(self.post_data(split_method="percent", **{f"share_{m.pk}": "30" for m in self.members}), workspace=self.home, actor=self.shivani)
        self.assertFalse(bad.is_valid())

    def test_itemization_requires_exact_total_and_own_household_members(self):
        lines = f"Milk | 6.00 | {self.shivani.pk}\nSoap | 4.00 | {self.alex.pk}"
        data = self.post_data(split_method="itemized", item_lines=lines)
        self.assertEqual(self.client.post(self.url("add"), data).status_code, 302)
        expense = Expense.objects.get()
        self.assertEqual(expense.shares.get(member=self.alex).amount_cents, 400)
        self.assertEqual(expense.split_data["item_lines"], lines)
        for invalid in [f"Milk | 10 | {self.stranger.pk}", f"Milk | 9 | {self.alex.pk}", "bad line"]:
            form = ExpenseForm(self.post_data(split_method="itemized", item_lines=invalid), workspace=self.home, actor=self.shivani)
            self.assertFalse(form.is_valid())

    def test_summary_original_simplified_comments_and_restore(self):
        from .services import original_debts, transfers
        expense = self.expense()
        for rows in [original_debts(self.home), transfers(self.home)]:
            actual = {}
            for row in rows:
                actual[row["sender_id"]] = actual.get(row["sender_id"],0)-row["amount_cents"]
                actual[row["receiver_id"]] = actual.get(row["receiver_id"],0)+row["amount_cents"]
            self.assertEqual(actual, balances(self.home))
        response = self.client.get(self.url())
        self.assertEqual(response.context["owed"],500)
        self.assertEqual(response.context["owe"],0)
        self.client.post(self.url("comment", expense_id=expense.pk), {"text":"<script>test</script>"})
        self.assertContains(self.client.get(self.url("detail",expense_id=expense.pk)),"&lt;script&gt;test&lt;/script&gt;")
        self.client.post(self.url("delete",expense_id=expense.pk),{"version":expense.version})
        expense.refresh_from_db()
        self.assertIsNotNone(expense.voided_at)
        self.client.post(self.url("restore",expense_id=expense.pk),{"version":expense.version})
        expense.refresh_from_db()
        self.assertIsNone(expense.voided_at)
        self.assertEqual(list(expense.events.values_list("kind",flat=True)),["created","comment","removed","restored"])

    def test_new_endpoints_preserve_household_boundaries(self):
        expense = self.expense()
        self.client.force_login(self.stranger.user)
        for route, kwargs in [("person",{"member_id":self.alex.pk}),("export",{}),("comment",{"expense_id":expense.pk}),("restore",{"expense_id":expense.pk})]:
            url = self.url(route, **kwargs)
            response = self.client.post(url,{"text":"Unauthorized"}) if route in ("comment","restore") else self.client.get(url)
            self.assertEqual(response.status_code,404)

    def test_csv_neutralizes_spreadsheet_formulas(self):
        expense = self.expense()
        expense.title = "=1+1"
        expense.save()
        response = self.client.get(self.url("export"))
        self.assertEqual(response["Content-Type"],"text/csv; charset=utf-8")
        self.assertIn("attachment",response["Content-Disposition"])
        self.assertIn("'=1+1",response.content.decode())
