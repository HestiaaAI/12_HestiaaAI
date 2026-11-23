"""Audience checks for the membership in the selected household."""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Exists, Q
from django.shortcuts import get_object_or_404

from .models import Membership, SharingCircle
from .services import HouseholdError, locked_household

Visibility = SharingCircle.Visibility


def current_actor(actor):
    return Membership.objects.filter(
        pk=actor.pk, workspace_id=actor.workspace_id, user_id=actor.user_id,
        is_active=True, user__is_active=True,
    )


def visible_circles(*, actor):
    selected = SharingCircle.selected_readers.through.objects.filter(membership_id=actor.pk)
    return SharingCircle.objects.filter(workspace_id=actor.workspace_id).filter(
        Exists(current_actor(actor)),
    ).filter(
        Q(visibility=Visibility.HOUSEHOLD)
        | Q(visibility=Visibility.ONLY_ME, created_by=actor)
        | Q(visibility=Visibility.SELECTED, created_by=actor)
        | Q(visibility=Visibility.SELECTED, pk__in=selected.values("sharingcircle_id"))
    )


def require_circle(*, actor, circle_id, for_update=False):
    circles = visible_circles(actor=actor)
    if for_update:
        circles = circles.select_for_update()
    return get_object_or_404(circles, pk=circle_id)


def active_readers(workspace, circle=None):
    members = Membership.objects.filter(workspace=workspace, is_active=True, user__is_active=True)
    if circle is None or circle.visibility == Visibility.HOUSEHOLD:
        return members
    if circle.visibility == Visibility.ONLY_ME:
        return members.filter(pk=circle.created_by_id)
    return members.filter(
        Q(pk=circle.created_by_id) | Q(pk__in=circle.selected_readers.values("pk"))
    )


def selected_members(actor, members, visibility, member_ids):
    if visibility not in (Visibility.ONLY_ME, Visibility.SELECTED):
        raise ValidationError("Choose Only me or Selected roommates.")
    ids = set(member_ids)
    allowed = {member.pk for member in members if member.is_active and member.user_id and member.user.is_active}
    if ids - allowed:
        raise ValidationError("Choose active roommates from this household.")
    if visibility == Visibility.ONLY_ME:
        if ids - {actor.pk}:
            raise ValidationError("Only me includes just you.")
        return set()
    ids.add(actor.pk)
    if len(ids) < 2:
        raise ValidationError("Choose at least one other active roommate.")
    return ids


def lock_actor(actor):
    try:
        return locked_household(actor)
    except HouseholdError as error:
        raise PermissionDenied from error


@transaction.atomic
def create_circle(*, actor, name, visibility, member_ids):
    workspace, actor, members = lock_actor(actor)
    readers = selected_members(actor, members, visibility, member_ids)
    name = name.strip()
    if not name or len(name) > 120:
        raise ValidationError("Enter a name of up to 120 characters.")
    circle = SharingCircle.objects.create(
        workspace=workspace, created_by=actor, name=name, visibility=visibility,
    )
    circle.selected_readers.set(readers)
    return circle


@transaction.atomic
def change_circle_audience(*, actor, circle_id, visibility, member_ids, expected_version):
    from expenses.models import Expense, Settlement

    _, actor, members = lock_actor(actor)
    circle = require_circle(actor=actor, circle_id=circle_id, for_update=True)
    if circle.created_by_id != actor.pk or circle.visibility == Visibility.HOUSEHOLD:
        raise PermissionDenied
    if circle.version != expected_version:
        raise ValidationError("Sharing changed. Reload before trying again.")
    if Expense.objects.filter(circle=circle).exists() or Settlement.objects.filter(circle=circle).exists():
        raise ValidationError("Sharing is locked because this group has financial history.")
    if visibility == Visibility.HOUSEHOLD:
        from expenses.policies import household_circle

        if circle.purchase_lists.exists():
            raise ValidationError("Open the shopping list to change its audience.")
        if member_ids:
            raise ValidationError("Clear selected roommates to share with everyone.")
        target = household_circle(actor.workspace)
        circle.delete()
        return target
    readers = selected_members(actor, members, visibility, member_ids)
    # Existing allocations must stay within the new audience.
    from expenses.models import PurchaseItem, PurchaseClaim
    if PurchaseItem.objects.filter(list__circle=circle).exclude(
        requested_by_id__in=readers | {actor.pk},
    ).exists():
        raise ValidationError("The new audience must include everyone with an existing request.")
    if PurchaseClaim.objects.filter(item__list__circle=circle).exclude(
        member_id__in=readers | {actor.pk},
    ).exists():
        raise ValidationError("The new audience must include everyone with an existing claim.")
    circle.visibility = visibility
    circle.version += 1
    circle.save(update_fields=["visibility", "version"])
    circle.selected_readers.set(readers)
    return circle


@transaction.atomic
def change_list_audience(*, actor, list_id, visibility, member_ids, expected_version, expected_circle):
    from expenses.models import Expense, PurchaseClaim, ReceiptPurchaseLine, Settlement
    from expenses.policies import household_circle, visible_lists

    workspace, actor, members = lock_actor(actor)
    purchase_list = get_object_or_404(visible_lists(actor=actor).select_for_update(), pk=list_id)
    circle = require_circle(actor=actor, circle_id=purchase_list.circle_id, for_update=True)
    if purchase_list.created_by_id != actor.pk or purchase_list.is_default:
        raise PermissionDenied
    if circle.pk != expected_circle or circle.version != expected_version:
        raise ValidationError("Sharing changed. Reload before trying again.")
    if circle.visibility != Visibility.HOUSEHOLD and visibility != Visibility.HOUSEHOLD:
        return change_circle_audience(
            actor=actor, circle_id=circle.pk, visibility=visibility,
            member_ids=member_ids, expected_version=expected_version,
        )
    if visibility == circle.visibility:
        return circle
    if ReceiptPurchaseLine.objects.filter(item__list=purchase_list).exists() or (
        circle.visibility != Visibility.HOUSEHOLD and (
            Expense.objects.filter(circle=circle).exists() or Settlement.objects.filter(circle=circle).exists()
        )
    ):
        raise ValidationError("Sharing is locked because this group has financial history.")
    if visibility == Visibility.HOUSEHOLD:
        if member_ids:
            raise ValidationError("Clear selected roommates to share with everyone.")
        target = household_circle(workspace)
    else:
        readers = selected_members(actor, members, visibility, member_ids) | {actor.pk}
        if purchase_list.purchaseitem_set.exclude(requested_by_id__in=readers).exists() or (
            PurchaseClaim.objects.filter(item__list=purchase_list).exclude(member_id__in=readers).exists()
        ):
            raise ValidationError("The new audience must include everyone with an existing request or claim.")
        target = create_circle(
            actor=actor, visibility=visibility, member_ids=member_ids, name=purchase_list.title,
        )
    purchase_list.circle = target
    purchase_list.save(update_fields=["circle"])
    if circle.visibility != Visibility.HOUSEHOLD and not circle.purchase_lists.exists():
        circle.delete()
    return target
