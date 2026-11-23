"""Balance arithmetic and authorized ledger writes for a single household."""
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from households.models import Membership
from households.sharing import Visibility, active_readers, require_circle
from .policies import circle_rows, household_circle, visible_expenses, visible_settlements
from .models import Expense, ExpenseShare, Settlement, ExpenseEvent

MAX_CENTS = 99_999_999


def cents(value):
    try:
        number = Decimal(str(value))
        scaled = number * 100
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError("Enter a valid amount.")
    if not number.is_finite() or scaled != scaled.to_integral_value() or not 0 < scaled <= MAX_CENTS:
        raise ValidationError("Use a positive amount with at most two decimal places.")
    return int(scaled)


def balances(workspace, *, circle=None):
    totals = defaultdict(int)
    for payer, amount in circle_rows(Expense.objects, workspace, circle).filter(voided_at=None).values_list("paid_by_id", "amount_cents"):
        totals[payer] += amount
    for member, amount in ExpenseShare.objects.filter(expense__in=circle_rows(Expense.objects, workspace, circle).filter(voided_at=None)).values_list("member_id", "amount_cents"):
        totals[member] -= amount
    for sender, receiver, amount in circle_rows(Settlement.objects, workspace, circle).filter(status=Settlement.Status.CONFIRMED).values_list("sender_id", "receiver_id", "amount_cents"):
        totals[sender] += amount
        totals[receiver] -= amount
    return dict(totals)


def transfers(workspace, *, circle=None):
    """Propose a zero-sum settlement plan across the household's net balances."""
    net = balances(workspace, circle=circle)
    creditors = [[member, amount] for member, amount in sorted(net.items()) if amount > 0]
    debtors = [[member, -amount] for member, amount in sorted(net.items()) if amount < 0]
    result = []
    debtor_index = creditor_index = 0
    while debtor_index < len(debtors) and creditor_index < len(creditors):
        sender, owed = debtors[debtor_index]
        receiver, due = creditors[creditor_index]
        amount = min(owed, due)
        result.append({"sender_id": sender, "receiver_id": receiver, "amount_cents": amount})
        debtors[debtor_index][1] -= amount
        creditors[creditor_index][1] -= amount
        if debtors[debtor_index][1] == 0:
            debtor_index += 1
        if creditors[creditor_index][1] == 0:
            creditor_index += 1
    return result


def lock_household(actor):
    from households.services import locked_household, HouseholdError
    try:
        workspace, current, members = locked_household(actor)
    except HouseholdError:
        raise PermissionDenied
    current.workspace = workspace
    return current



def can_change(actor, expense):
    return visible_expenses(actor=actor).filter(pk=expense.pk).exists() and (
        actor.pk in (expense.created_by_id, expense.paid_by_id) or actor.role == Membership.MemberRole.OWNER
    )


@transaction.atomic
def save_expense(actor, values, shares, token, expense_id=None, version=None, *, circle=None, audience_version=None):
    actor = lock_household(actor)
    circle = require_circle(actor=actor, circle_id=circle.pk, for_update=True) if circle else household_circle(actor.workspace)
    if audience_version is not None and circle.version != audience_version:
        raise ValidationError("Sharing changed. Reload before saving.")
    expense = None
    if expense_id is not None:
        expense = visible_expenses(actor=actor).select_related("circle").get(pk=expense_id, voided_at=None)
        if expense.circle_id and expense.circle_id != circle.pk:
            raise PermissionDenied
        if not can_change(actor, expense):
            raise PermissionDenied
        if expense.version != version:
            raise ValidationError("This expense changed while you were editing. Reload it before saving.")
    else:
        duplicate = Expense.objects.filter(request_token=token).first()
        if duplicate:
            if duplicate.workspace_id != actor.workspace_id or duplicate.created_by_id != actor.pk or duplicate.circle_id != circle.pk:
                raise PermissionDenied
            return duplicate

    allowed = set(active_readers(actor.workspace, circle).values_list("pk", flat=True))
    if expense:
        allowed.update(expense.shares.values_list("member_id", flat=True))
        allowed.add(expense.paid_by_id)
    amount = cents(values["amount"])
    if not shares or set(shares) - allowed or values["paid_by"].pk not in allowed:
        raise ValidationError("Choose roommates from this household.")
    if any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in shares.values()) or sum(shares.values()) != amount:
        raise ValidationError("The split must add up to the expense amount.")
    creating = expense is None
    if expense is None:
        expense = Expense(workspace=actor.workspace, circle=circle, created_by=actor, request_token=token)
    expense.paid_by = values["paid_by"]
    expense.title = values["title"]
    expense.amount_cents = amount
    expense.date = values["date"]
    expense.category = values["category"]
    expense.note = values.get("note", "")
    expense.split_method = values["split_method"]
    expense.split_data = values.get("split_data", {})
    if expense.pk:
        expense.version += 1
    expense.save()
    expense.shares.all().delete()
    ExpenseShare.objects.bulk_create([ExpenseShare(expense=expense, member_id=member, amount_cents=share) for member, share in shares.items()])
    ExpenseEvent.objects.create(expense=expense, actor=actor, kind="created" if creating else "edited")
    return expense


@transaction.atomic
def void_expense(actor, expense_id, version):
    actor = lock_household(actor)
    expense = visible_expenses(actor=actor).select_related("circle").get(pk=expense_id, voided_at=None)
    if not can_change(actor, expense):
        raise PermissionDenied
    if expense.version != version:
        raise ValidationError("This expense changed. Reload it before deleting.")
    expense.voided_at = timezone.now()
    expense.version += 1
    expense.save(update_fields=["voided_at", "version", "updated_at"])
    ExpenseEvent.objects.create(expense=expense, actor=actor, kind="removed")


@transaction.atomic
def request_payment(actor, receiver, amount, note, token, *, circle=None):
    actor = lock_household(actor)
    circle = require_circle(actor=actor, circle_id=circle.pk, for_update=True) if circle else household_circle(actor.workspace)
    if circle.visibility == Visibility.ONLY_ME:
        raise ValidationError("Private expenses do not have settlements.")
    previous = Settlement.objects.filter(request_token=token).first()
    if previous:
        if previous.workspace_id != actor.workspace_id or previous.sender_id != actor.pk or previous.circle_id != circle.pk:
            raise PermissionDenied
        return previous
    if receiver.pk == actor.pk or not active_readers(actor.workspace, circle).filter(pk=receiver.pk).exists():
        raise ValidationError("Choose another active roommate from this household.")
    available = payment_capacity(actor.workspace,actor.pk,receiver.pk,circle=circle)
    if not 0 < amount <= available:
        raise ValidationError("This amount exceeds the available balance. Check existing pending payments.")
    return Settlement.objects.create(workspace=actor.workspace, circle=circle, sender=actor, receiver=receiver,
                                     amount_cents=amount, note=note, request_token=token)


@transaction.atomic
def resolve_payment(actor, payment_id, action):
    actor = lock_household(actor)
    payment = visible_settlements(actor=actor).select_related("receiver", "sender", "circle").get(pk=payment_id)
    permitted = ((action in ("confirm", "reject") and payment.receiver_id == actor.pk)
                 or (action == "cancel" and payment.sender_id == actor.pk))
    if not permitted:
        raise PermissionDenied
    if payment.status != Settlement.Status.PENDING:
        return payment
    if action == "confirm":
        if payment.amount_cents > payment_capacity(actor.workspace,payment.sender_id,payment.receiver_id,exclude_payment=payment.pk,circle=payment.circle):
            raise ValidationError("The household balance changed. Decline this payment and ask for an updated record.")
    payment.status = {"confirm": Settlement.Status.CONFIRMED, "reject": Settlement.Status.REJECTED, "cancel": Settlement.Status.CANCELLED}[action]
    payment.resolved_at = timezone.now()
    payment.save(update_fields=["status", "resolved_at"])
    return payment


def original_debts(workspace, *, circle=None):
    """Direct payer/participant debts after bilateral offsets and confirmed payments."""
    matrix = defaultdict(int)
    for payer, member, amount in ExpenseShare.objects.filter(expense__in=circle_rows(Expense.objects, workspace, circle).filter(voided_at=None)).values_list("expense__paid_by_id", "member_id", "amount_cents"):
        if payer != member:
            matrix[(member, payer)] += amount
    for sender, receiver, amount in circle_rows(Settlement.objects, workspace, circle).filter(status="confirmed").values_list("sender_id", "receiver_id", "amount_cents"):
        matrix[(sender, receiver)] -= amount
    pairs = {tuple(sorted(pair)) for pair in matrix}
    result = []
    for a, b in sorted(pairs):
        value = matrix[(a, b)] - matrix[(b, a)]
        if value:
            result.append({"sender_id": a if value > 0 else b, "receiver_id": b if value > 0 else a, "amount_cents": abs(value)})
    return result


@transaction.atomic
def restore_expense(actor, expense_id, version):
    actor = lock_household(actor)
    expense = visible_expenses(actor=actor).get(pk=expense_id, voided_at__isnull=False)
    if not can_change(actor, expense):
        raise PermissionDenied
    if expense.version != version:
        raise ValidationError("The expense changed. Reload it before restoring.")
    expense.voided_at = None
    expense.version += 1
    expense.save(update_fields=["voided_at", "version", "updated_at"])
    ExpenseEvent.objects.create(expense=expense, actor=actor, kind="restored")


def simplified(workspace, circle):
    return workspace.simplify_debts and (circle is None or circle.visibility == Visibility.HOUSEHOLD)


def payment_plan(workspace, *, circle=None):
    calculate = transfers if simplified(workspace, circle) else original_debts
    return calculate(workspace, circle=circle)


def payment_capacity(workspace,sender_id,receiver_id,exclude_payment=None, *, circle=None):
    pending=circle_rows(Settlement.objects, workspace, circle).filter(status=Settlement.Status.PENDING)
    if exclude_payment:pending=pending.exclude(pk=exclude_payment)
    if simplified(workspace, circle):
        net=balances(workspace, circle=circle)
        return max(0,min(-net.get(sender_id,0)-sum(pending.filter(sender_id=sender_id).values_list('amount_cents',flat=True)),net.get(receiver_id,0)-sum(pending.filter(receiver_id=receiver_id).values_list('amount_cents',flat=True))))
    direct=next((row['amount_cents'] for row in original_debts(workspace, circle=circle) if row['sender_id']==sender_id and row['receiver_id']==receiver_id),0)
    reserved=sum(pending.filter(sender_id=sender_id,receiver_id=receiver_id).values_list('amount_cents',flat=True))
    return max(0,direct-reserved)


def available_payments(workspace, actor_id, receiver_ids, *, circle, net, direct, pending):
    """Compute the actor's capacity to pay each eligible reader in one pass."""
    if simplified(workspace, circle):
        sent = sum(payment.amount_cents for payment in pending if payment.sender_id == actor_id)
        incoming = defaultdict(int)
        for payment in pending:
            incoming[payment.receiver_id] += payment.amount_cents
        remaining = -net.get(actor_id, 0) - sent
        return {pk: max(0, min(remaining, net.get(pk, 0) - incoming[pk])) for pk in receiver_ids}
    original = {row["receiver_id"]: row["amount_cents"] for row in direct if row["sender_id"] == actor_id}
    reservations = defaultdict(int)
    for payment in pending:
        if payment.sender_id == actor_id:
            reservations[payment.receiver_id] += payment.amount_cents
    return {pk: max(0, original.get(pk, 0) - reservations[pk]) for pk in receiver_ids}
