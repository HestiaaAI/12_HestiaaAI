from datetime import date, timedelta

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class VisibilityMigrationTests(TransactionTestCase):
    before = [
        ("households", "0005_merge_integration"),
        ("expenses", "0007_recurring_bill_task"),
    ]
    after = [("expenses", "0009_backfill_sharing_contexts")]

    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    def test_upgrade_preserves_ledger_and_allocation(self):
        self.addCleanup(self.restore_schema)
        old = self.migrate(self.before)
        workspace = old.get_model("households", "Workspace").objects.create(name="Home")
        historical = old.get_model("households", "Membership").objects.create(
            workspace=workspace, display_name="Former roommate", is_active=False,
        )
        roommate = old.get_model("households", "Membership").objects.create(
            workspace=workspace, display_name="Roommate",
        )
        items = old.get_model("expenses", "PurchaseItem").objects
        for scope in ("household", "personal"):
            items.create(workspace=workspace, name=scope, scope=scope, requested_by=historical)
        expenses = old.get_model("expenses", "Expense").objects
        expense = expenses.create(
            workspace=workspace, paid_by=roommate, created_by=roommate,
            amount_cents=901, title="Groceries", date=date(2026, 11, 23), split_method="custom",
        )
        expenses.create(
            workspace=workspace, paid_by=roommate, created_by=roommate,
            amount_cents=100, title="Voided", date=date(2026, 11, 23),
            split_method="custom", voided_at=timezone.now(),
        )
        old.get_model("expenses", "ExpenseShare").objects.create(
            expense=expense, member=historical, amount_cents=401,
        )
        payments = old.get_model("expenses", "Settlement").objects
        for status, amount in (("pending", 101), ("confirmed", 199)):
            payments.create(
                workspace=workspace, sender=historical, receiver=roommate,
                amount_cents=amount, status=status,
            )

        invitations = old.get_model("households", "HouseholdInvitation").objects
        invitation = invitations.create(
            workspace=workspace, email="invite@example.test", token_digest="token-digest",
            expires_at=timezone.now() + timedelta(days=1), invited_by=roommate,
        )
        drafts = old.get_model("expenses", "ReceiptDraft").objects
        draft = drafts.create(workspace=workspace, actor=roommate, confirmed_ids=[expense.pk])
        receipt = old.get_model("expenses", "PurchaseReceipt").objects.create(
            workspace=workspace, submitted_by=roommate, draft=draft, total_cents=901,
            fingerprint="test-fingerprint",
        )
        old.get_model("expenses", "ReceiptPurchaseLine").objects.create(
            receipt=receipt, item=items.get(scope="personal"), quantity=1, expense=expense,
        )
        old.get_model("expenses", "RecurringBill").objects.create(
            workspace=workspace, title="Rent", amount_cents=95000,
            paid_by=roommate, created_by=roommate, next_due=date(2026, 12, 1),
        )

        snapshots = {
            name: list(old.get_model("expenses", name).objects.order_by("pk").values())
            for name in (
                "PurchaseItem", "Expense", "ExpenseShare", "Settlement",
                "ReceiptDraft", "PurchaseReceipt", "ReceiptPurchaseLine", "RecurringBill",
            )
        }
        for _ in range(2):
            new = self.migrate(self.after)
            circle = new.get_model("households", "SharingCircle").objects.get(workspace=workspace.pk)
            self.assertEqual(circle.visibility, "HOUSEHOLD")
            self.assertIsNone(circle.created_by_id)
            grocery_list = new.get_model("expenses", "PurchaseList").objects.get(circle=circle.pk)
            self.assertTrue(grocery_list.is_default)
            for name, rows in snapshots.items():
                records = new.get_model("expenses", name).objects.order_by("pk")
                if name == "PurchaseItem":
                    self.assertEqual(set(records.values_list("list_id", flat=True)), {grocery_list.pk})
                if name in ("Expense", "Settlement"):
                    self.assertEqual(set(records.values_list("circle_id", flat=True)), {circle.pk})
                self.assertEqual(list(records.values(*rows[0])), rows)
            self.assertEqual(
                new.get_model("households", "HouseholdInvitation").objects.values().get(pk=invitation.pk),
                invitations.values().get(pk=invitation.pk),
            )
            self.migrate(self.before)

    def test_rollback_rejects_restricted_circles(self):
        self.addCleanup(self.restore_schema)
        apps = self.migrate(self.after)
        workspace = apps.get_model("households", "Workspace").objects.create(name="Home")
        member = apps.get_model("households", "Membership").objects.create(
            workspace=workspace, display_name="Roommate",
        )
        circle = apps.get_model("households", "SharingCircle").objects.create(
            workspace=workspace, created_by=member, name="Private", visibility="ONLY_ME",
        )
        with self.assertRaisesMessage(RuntimeError, "Sharing data would be lost on rollback"):
            self.migrate(self.before)
        self.assertTrue(type(circle).objects.filter(pk=circle.pk).exists())

    def restore_schema(self):
        self.migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())
