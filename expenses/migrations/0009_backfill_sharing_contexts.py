from django.db import migrations, models


HOUSEHOLD_NAME = "Household"
DEFAULT_LIST_TITLE = "Shopping list"


def backfill_sharing_contexts(apps, schema_editor):
    database = schema_editor.connection.alias
    workspaces = apps.get_model("households", "Workspace").objects.using(database)
    circles = apps.get_model("households", "SharingCircle").objects.using(database)
    lists = apps.get_model("expenses", "PurchaseList").objects.using(database)
    items = apps.get_model("expenses", "PurchaseItem").objects.using(database)
    expenses = apps.get_model("expenses", "Expense").objects.using(database)
    settlements = apps.get_model("expenses", "Settlement").objects.using(database)

    for workspace_id in workspaces.order_by("pk").values_list("pk", flat=True).iterator():
        circle, _ = circles.get_or_create(
            workspace_id=workspace_id, visibility="HOUSEHOLD", defaults={"name": HOUSEHOLD_NAME},
        )
        default_list, _ = lists.get_or_create(
            workspace_id=workspace_id, is_default=True,
            defaults={"title": DEFAULT_LIST_TITLE, "circle_id": circle.pk},
        )
        items.filter(workspace_id=workspace_id, list__isnull=True).update(list_id=default_list.pk)
        expenses.filter(workspace_id=workspace_id, circle__isnull=True).update(circle_id=circle.pk)
        settlements.filter(workspace_id=workspace_id, circle__isnull=True).update(circle_id=circle.pk)


def guard_rollback(apps, schema_editor):
    database = schema_editor.connection.alias
    circles = apps.get_model("households", "SharingCircle").objects.using(database)
    lists = apps.get_model("expenses", "PurchaseList").objects.using(database)

    for model_name, link in (("PurchaseItem", "list"), ("Expense", "circle"), ("Settlement", "circle")):
        records = apps.get_model("expenses", model_name).objects.using(database)
        linked = records.filter(**{f"{link}__isnull": False})
        if linked.exclude(**{f"{link}__workspace_id": models.F("workspace_id")}).exists():
            raise RuntimeError("Cross-household sharing links prevent a safe rollback.")

    if (
        circles.exclude(
            visibility="HOUSEHOLD", name=HOUSEHOLD_NAME, created_by__isnull=True,
            version=1, selected_readers__isnull=True,
        ).exists()
        or lists.exclude(
            is_default=True, title=DEFAULT_LIST_TITLE, created_by__isnull=True,
            circle__workspace_id=models.F("workspace_id"),
        ).exists()
    ):
        raise RuntimeError(
            "Sharing data would be lost on rollback. Restore a verified pre-sharing backup "
            "instead of reversing these migrations."
        )


class Migration(migrations.Migration):
    dependencies = [("expenses", "0008_purchase_lists_and_circle")]

    operations = [migrations.RunPython(backfill_sharing_contexts, guard_rollback)]
