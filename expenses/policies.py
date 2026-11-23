"""Scope domain queries before totals, matching, exports, or object lookup."""
from households.sharing import Visibility, visible_circles
from households.models import SharingCircle
from .models import Expense, PurchaseItem, PurchaseList, Settlement


def household_circle(workspace):
    return SharingCircle.objects.get_or_create(
        workspace=workspace, visibility=Visibility.HOUSEHOLD, defaults={"name": "Household"},
    )[0]


def circle_rows(rows, workspace, circle=None):
    rows = rows.filter(workspace=workspace)
    if circle is None:
        return rows.filter(circle__visibility=Visibility.HOUSEHOLD, circle__workspace=workspace)
    if circle.workspace_id != workspace.pk:
        return rows.none()
    return rows.filter(circle=circle)


def visible_lists(*, actor):
    return PurchaseList.objects.filter(workspace_id=actor.workspace_id, circle__in=visible_circles(actor=actor))


def visible_items(*, actor):
    return PurchaseItem.objects.filter(workspace_id=actor.workspace_id, list__in=visible_lists(actor=actor))


def visible_expenses(*, actor):
    return Expense.objects.filter(workspace_id=actor.workspace_id, circle__in=visible_circles(actor=actor))


def visible_settlements(*, actor):
    return Settlement.objects.filter(workspace_id=actor.workspace_id, circle__in=visible_circles(actor=actor))
