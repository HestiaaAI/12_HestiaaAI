"""Balance arithmetic and authorized ledger writes for a single household."""
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from households.models import Membership, Workspace
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


def balances(workspace):
    totals = defaultdict(int)
    for payer, amount in Expense.objects.filter(workspace=workspace, voided_at=None).values_list("paid_by_id", "amount_cents"):
        totals[payer] += amount
    for member, amount in ExpenseShare.objects.filter(expense__workspace=workspace, expense__voided_at=None).values_list("member_id", "amount_cents"):
        totals[member] -= amount
    for sender, receiver, amount in Settlement.objects.filter(workspace=workspace, status=Settlement.Status.CONFIRMED).values_list("sender_id", "receiver_id", "amount_cents"):
        totals[sender] += amount
        totals[receiver] -= amount
    return dict(totals)


def transfers(workspace):
    """Propose a zero-sum settlement plan across the household's net balances."""
    net = balances(workspace)
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
    return actor.workspace_id == expense.workspace_id and (
        actor.pk in (expense.created_by_id, expense.paid_by_id) or actor.role == Membership.MemberRole.OWNER
    )


@transaction.atomic
def save_expense(actor, values, shares, token, expense_id=None, version=None):
    actor = lock_household(actor)
    expense = None
    if expense_id is not None:
        expense = Expense.objects.get(pk=expense_id, workspace=actor.workspace, voided_at=None)
        if not can_change(actor, expense):
            raise PermissionDenied
        if expense.version != version:
            raise ValidationError("This expense changed while you were editing. Reload it before saving.")
    else:
        duplicate = Expense.objects.filter(request_token=token).first()
        if duplicate:
            if duplicate.workspace_id != actor.workspace_id or duplicate.created_by_id != actor.pk:
                raise PermissionDenied
            return duplicate

    allowed = set(Membership.objects.filter(workspace=actor.workspace, is_active=True, user__is_active=True).values_list("pk", flat=True))
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
        expense = Expense(workspace=actor.workspace, created_by=actor, request_token=token)
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
    expense = Expense.objects.get(pk=expense_id, workspace=actor.workspace, voided_at=None)
    if not can_change(actor, expense):
        raise PermissionDenied
    if expense.version != version:
        raise ValidationError("This expense changed. Reload it before deleting.")
    expense.voided_at = timezone.now()
    expense.version += 1
    expense.save(update_fields=["voided_at", "version", "updated_at"])
    ExpenseEvent.objects.create(expense=expense, actor=actor, kind="removed")


@transaction.atomic
def request_payment(actor, receiver, amount, note, token):
    actor = lock_household(actor)
    previous = Settlement.objects.filter(request_token=token).first()
    if previous:
        if previous.workspace_id != actor.workspace_id or previous.sender_id != actor.pk:
            raise PermissionDenied
        return previous
    if receiver.pk == actor.pk or not Membership.objects.filter(pk=receiver.pk, workspace=actor.workspace, is_active=True, user__isnull=False).exists():
        raise ValidationError("Choose another active roommate from this household.")
    available = payment_capacity(actor.workspace,actor.pk,receiver.pk)
    if not 0 < amount <= available:
        raise ValidationError("This amount exceeds the available balance. Check existing pending payments.")
    return Settlement.objects.create(workspace=actor.workspace, sender=actor, receiver=receiver,
                                     amount_cents=amount, note=note, request_token=token)


@transaction.atomic
def resolve_payment(actor, payment_id, action):
    actor = lock_household(actor)
    payment = Settlement.objects.select_related("receiver", "sender").get(pk=payment_id, workspace=actor.workspace)
    permitted = ((action in ("confirm", "reject") and payment.receiver_id == actor.pk)
                 or (action == "cancel" and payment.sender_id == actor.pk))
    if not permitted:
        raise PermissionDenied
    if payment.status != Settlement.Status.PENDING:
        return payment
    if action == "confirm":
        if payment.amount_cents > payment_capacity(actor.workspace,payment.sender_id,payment.receiver_id,exclude_payment=payment.pk):
            raise ValidationError("The household balance changed. Decline this payment and ask for an updated record.")
    payment.status = {"confirm": Settlement.Status.CONFIRMED, "reject": Settlement.Status.REJECTED, "cancel": Settlement.Status.CANCELLED}[action]
    payment.resolved_at = timezone.now()
    payment.save(update_fields=["status", "resolved_at"])
    return payment


def original_debts(workspace):
    """Direct payer/participant debts after bilateral offsets and confirmed payments."""
    matrix = defaultdict(int)
    for payer, member, amount in ExpenseShare.objects.filter(expense__workspace=workspace, expense__voided_at=None).values_list("expense__paid_by_id", "member_id", "amount_cents"):
        if payer != member:
            matrix[(member, payer)] += amount
    for sender, receiver, amount in Settlement.objects.filter(workspace=workspace, status="confirmed").values_list("sender_id", "receiver_id", "amount_cents"):
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
    expense = Expense.objects.get(pk=expense_id, workspace=actor.workspace, voided_at__isnull=False)
    if not can_change(actor, expense):
        raise PermissionDenied
    if expense.version != version:
        raise ValidationError("The expense changed. Reload it before restoring.")
    expense.voided_at = None
    expense.version += 1
    expense.save(update_fields=["voided_at", "version", "updated_at"])
    ExpenseEvent.objects.create(expense=expense, actor=actor, kind="restored")


def payment_plan(workspace):
    return transfers(workspace) if workspace.simplify_debts else original_debts(workspace)


def payment_capacity(workspace,sender_id,receiver_id,exclude_payment=None):
    pending=Settlement.objects.filter(workspace=workspace,status=Settlement.Status.PENDING)
    if exclude_payment:pending=pending.exclude(pk=exclude_payment)
    if workspace.simplify_debts:
        net=balances(workspace)
        return max(0,min(-net.get(sender_id,0)-sum(pending.filter(sender_id=sender_id).values_list('amount_cents',flat=True)),net.get(receiver_id,0)-sum(pending.filter(receiver_id=receiver_id).values_list('amount_cents',flat=True))))
    direct=next((row['amount_cents'] for row in original_debts(workspace) if row['sender_id']==sender_id and row['receiver_id']==receiver_id),0)
    reserved=sum(pending.filter(sender_id=sender_id,receiver_id=receiver_id).values_list('amount_cents',flat=True))
    return max(0,direct-reserved)
