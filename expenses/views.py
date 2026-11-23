"""Signed-in, household-scoped pages for the shared expense ledger."""
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import OperationalError, transaction
from django.db.models import Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST
from django.utils import timezone

from households.models import Membership
from households.context import require_household
from .policies import circle_rows, visible_expenses, visible_settlements
from households.sharing import Visibility, active_readers, require_circle, visible_circles
from .forms import ExpenseForm, PaymentForm
from .models import Expense, Settlement, ExpenseEvent
from .services import balances, can_change, cents, request_payment, resolve_payment, save_expense, transfers, void_expense


def membership(request, workspace_id):
    actor = require_household(request)
    if actor.workspace_id != workspace_id:
        raise Http404
    return actor


def requested_circle(request, actor):
    value = request.GET.get("circle")
    if request.method == "POST" and "circle" in request.POST:
        posted = request.POST["circle"]
        if value and posted != value:
            raise Http404
        value = posted
    if value is None or value == "":
        return None
    try:
        value = int(value)
    except ValueError:
        raise Http404
    return require_circle(actor=actor, circle_id=value)


def ledger_redirect(route, workspace_id, circle):
    url = reverse(route, args=[workspace_id])
    return redirect(f"{url}?circle={circle.pk}" if circle else url)


def ledger_members(actor, circle):
    from django.db.models import Q
    members = actor.workspace.memberships.select_related("user", "user__hestia_avatar").order_by("membership_id")
    if circle is None or circle.visibility == Visibility.HOUSEHOLD:
        return members
    return members.filter(
        Q(pk__in=active_readers(actor.workspace, circle))
        | Q(paid_expenses__circle=circle) | Q(expense_shares__expense__circle=circle)
        | Q(sent_settlements__circle=circle) | Q(received_settlements__circle=circle)
    ).distinct()


def ledger_context(actor, circle):
    return {"workspace": actor.workspace, "actor": actor, "circle": circle,
            "housemates": list(ledger_members(actor, circle)),
            "circles": visible_circles(actor=actor).order_by("name", "pk"),
            "can_edit_circle": bool(circle and circle.created_by_id == actor.pk and not circle.purchase_lists.exists())}


def page_context(actor):
    return {"workspace": actor.workspace, "actor": actor, "housemates": list(actor.workspace.memberships.select_related("user", "user__hestia_avatar").order_by("membership_id"))}


@login_required
@never_cache
def households(request):
    actor = require_household(request)
    return redirect("expenses:overview", workspace_id=actor.workspace_id)


@login_required
@never_cache
def overview(request, workspace_id):
    actor = membership(request, workspace_id)
    circle = requested_circle(request, actor)
    context = ledger_context(actor, circle)
    people = {member.pk: member for member in context["housemates"]}
    net = balances(actor.workspace, circle=circle)
    from .services import payment_plan
    suggestions = payment_plan(actor.workspace, circle=circle)
    for transfer in suggestions:
        transfer.update(sender=people[transfer["sender_id"]], receiver=people[transfer["receiver_id"]])
    expenses = circle_rows(Expense.objects, actor.workspace, circle).filter(voided_at=None).select_related("paid_by").prefetch_related("shares")
    search = request.GET.get("q", "").strip()[:120]
    if search:
        expenses = expenses.filter(title__icontains=search)
    selected_person = request.GET.get("person", "")
    if selected_person in {str(pk) for pk in people}:
        from django.db.models import Q
        expenses = expenses.filter(Q(paid_by_id=selected_person) | Q(shares__member_id=selected_person)).distinct()
    category = request.GET.get("category", "")
    if category in Expense.Category.values:
        expenses = expenses.filter(category=category)
    date = request.GET.get("date", "")
    if date:
        from django.utils.dateparse import parse_date
        try:
            parsed = parse_date(date)
        except ValueError:
            parsed = None
        if parsed:
            expenses = expenses.filter(date=parsed)
    from .services import original_debts
    direct = original_debts(actor.workspace, circle=circle)
    for transfer in direct:
        transfer.update(sender=people[transfer["sender_id"]], receiver=people[transfer["receiver_id"]])
    owe = sum(x["amount_cents"] for x in direct if x["sender_id"] == actor.pk)
    owed = sum(x["amount_cents"] for x in direct if x["receiver_id"] == actor.pk)
    pair_rows = []
    for person in context["housemates"]:
        if person.pk == actor.pk:
            continue
        value = sum(x["amount_cents"] for x in direct if x["sender_id"] == person.pk and x["receiver_id"] == actor.pk) - sum(x["amount_cents"] for x in direct if x["sender_id"] == actor.pk and x["receiver_id"] == person.pk)
        pair_rows.append({"member": person, "balance": value, "amount": abs(value)})
    context.update(owe=owe, owed=owed, direct=direct, pair_rows=pair_rows, selected_person=selected_person, categories=Expense.Category.choices,
                   deleted_expenses=circle_rows(Expense.objects, actor.workspace, circle).filter(voided_at__isnull=False)[:5])
    all_expenses = circle_rows(Expense.objects, actor.workspace, circle).filter(voided_at=None)
    month_start = timezone.localdate().replace(day=1)
    context.update(
        expenses=expenses[:50], search=search,
        balance=net.get(actor.pk, 0), balance_abs=abs(net.get(actor.pk, 0)),
        transfers=suggestions,
        payments=circle_rows(Settlement.objects, actor.workspace, circle).filter(status="pending").select_related("sender", "receiver")[:30],
        month_total=all_expenses.filter(date__gte=month_start).aggregate(total=Sum("amount_cents"))["total"] or 0,
        your_paid=all_expenses.filter(paid_by=actor, date__gte=month_start).aggregate(total=Sum("amount_cents"))["total"] or 0,
    )
    from .settle_views import settlement_context
    context.update(settlement_context(actor, circle=circle))
    from .insight_views import activity_context
    context.update(activity_context(request,actor,circle=circle))
    return render(request, "expenses/overview.html", context)


@login_required
@never_cache
def members(request, workspace_id):
    actor = membership(request, workspace_id)
    circle = requested_circle(request, actor)
    context = ledger_context(actor, circle)
    net = balances(actor.workspace, circle=circle)
    context["member_rows"] = [{"member": member, "balance": net.get(member.pk, 0), "amount": abs(net.get(member.pk, 0))} for member in context["housemates"]]
    return render(request, "expenses/members.html", context)


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def expense_form(request, workspace_id, expense_id=None):
    actor = membership(request, workspace_id)
    circle = requested_circle(request, actor)
    expense = get_object_or_404(visible_expenses(actor=actor).select_related("circle"), pk=expense_id, voided_at=None) if expense_id else None
    if expense:
        circle = expense.circle
    if expense and not can_change(actor, expense):
        raise PermissionDenied
    form = ExpenseForm(request.POST if request.method == "POST" else None, workspace=actor.workspace, actor=actor, expense=expense, circle=circle)
    if request.method == "POST" and form.is_valid():
        try:
            audience_version = request.POST.get("audience_version")
            if circle and circle.visibility != "HOUSEHOLD" and not str(audience_version).isdigit():
                raise ValidationError("Reload to confirm the expense audience.")
            result = save_expense(actor, form.cleaned_data, form.shares, form.cleaned_data["request_token"],
                                  expense_id=expense_id, version=form.cleaned_data["version"], circle=circle,
                                  audience_version=int(audience_version) if str(audience_version).isdigit() else None)
        except ValidationError as error:
            form.add_error(None, error)
        except (Expense.DoesNotExist, Membership.DoesNotExist):
            form.add_error(None, "The household or expense changed. Reload before trying again.")
        except OperationalError:
            form.add_error(None, "The household is being updated. Please try saving again.")
        else:
            messages.success(request, "Expense updated." if expense else "Expense added. Balances for this audience are up to date.")
            return redirect("expenses:detail", workspace_id=workspace_id, expense_id=result.pk)
    return render(request, "expenses/form.html", {**ledger_context(actor, circle), "form": form, "expense": expense})


@login_required
@never_cache
def detail(request, workspace_id, expense_id):
    actor = membership(request, workspace_id)
    expense = get_object_or_404(visible_expenses(actor=actor).select_related("paid_by__user__hestia_avatar", "created_by__user__hestia_avatar", "circle").prefetch_related("shares__member__user__hestia_avatar"), pk=expense_id, workspace=actor.workspace, voided_at=None)
    return render(request, "expenses/detail.html", {**ledger_context(actor, expense.circle), "expense": expense, "can_edit": can_change(actor, expense)})


@login_required
@require_POST
def delete(request, workspace_id, expense_id):
    actor = membership(request, workspace_id)
    try:
        version = int(request.POST.get("version", ""))
    except ValueError:
        raise Http404
    expense = get_object_or_404(visible_expenses(actor=actor).select_related("circle"), pk=expense_id, voided_at=None)
    try:
        void_expense(actor, expense_id, version)
    except ValidationError as error:
        messages.error(request, error.messages[0])
        return redirect("expenses:detail", workspace_id=workspace_id, expense_id=expense_id)
    except (Expense.DoesNotExist, Membership.DoesNotExist, OperationalError):
        messages.error(request, "The expense changed. Reload and try again.")
    else:
        messages.success(request, "Expense removed. Balances have been updated.")
    return ledger_redirect("expenses:overview", workspace_id, expense.circle)


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def payment_form(request, workspace_id):
    actor = membership(request, workspace_id)
    circle = requested_circle(request, actor)
    form = PaymentForm(request.POST if request.method == "POST" else None, actor=actor, circle=circle)
    from .settle_views import settlement_context
    settle_context = settlement_context(actor, circle=circle)
    if not form.is_bound:
        receiver = request.GET.get("receiver")
        if receiver in {str(member.pk) for member in form.fields["receiver"].queryset}:
            form.initial["receiver"] = receiver
            available = settle_context["payment_amounts"].get(receiver,0)
            if available:form.initial["amount"] = (Decimal(available)/100).quantize(Decimal(".01"))
        try:
            amount = Decimal(request.GET.get("amount", "0"))
            if amount.is_finite() and amount > 0 and amount*100 <= settle_context["payment_amounts"].get(receiver,0):
                form.initial["amount"] = amount
        except ArithmeticError:
            pass
    if request.method == "POST" and form.is_valid():
        try:
            request_payment(actor, form.cleaned_data["receiver"], cents(form.cleaned_data["amount"]),
                            form.cleaned_data["note"], form.cleaned_data["request_token"], circle=circle)
        except ValidationError as error:
            form.add_error(None, error)
        except (Membership.DoesNotExist, OperationalError):
            form.add_error(None, "The household balance changed. Reload and try again.")
        else:
            messages.success(request, "Payment recorded. Your roommate will confirm they received it.")
            return ledger_redirect("expenses:overview", workspace_id, circle)
    return render(request, "expenses/payment.html", {**ledger_context(actor, circle), **settle_context, "form": form})


@login_required
@require_POST
def payment_action(request, workspace_id, payment_id, action):
    actor = membership(request, workspace_id)
    if action not in ("confirm", "reject", "cancel"):
        raise Http404
    payment = get_object_or_404(visible_settlements(actor=actor).select_related("circle"), pk=payment_id)
    try:
        resolve_payment(actor, payment_id, action)
    except ValidationError as error:
        messages.error(request, error.messages[0])
    except (Membership.DoesNotExist, OperationalError):
        messages.error(request, "The household balance changed. Please try again.")
    else:
        messages.success(request, {"confirm": "Payment confirmed. Your balances are updated.", "reject": "Payment declined. Balances stay as they were.", "cancel": "Payment record cancelled."}[action])
    return ledger_redirect("expenses:overview", workspace_id, payment.circle)


@login_required
@never_cache
def person_history(request, workspace_id, member_id):
    actor = membership(request, workspace_id)
    circle = requested_circle(request, actor)
    roommate = get_object_or_404(ledger_members(actor, circle), pk=member_id)
    from django.db.models import Q
    records = circle_rows(Expense.objects, actor.workspace, circle).filter(voided_at=None).filter(
        Q(paid_by=actor, shares__member=roommate) | Q(paid_by=roommate, shares__member=actor)).distinct()
    from .settle_views import settlement_context
    data=settlement_context(actor, circle=circle)
    pair_option=next((row for row in data['settle_options'] if row['member'].pk==roommate.pk),None)
    pair_pending=[p for p in data['settle_pending'] if roommate.pk in (p.sender_id,p.receiver_id)]
    return render(request, "expenses/history.html", {**ledger_context(actor, circle), "roommate": roommate, "records": records, "pair_option":pair_option, "pair_pending":pair_pending})


@login_required
@require_POST
@transaction.atomic
def comment(request, workspace_id, expense_id):
    from .services import lock_household
    actor = lock_household(membership(request, workspace_id))
    expense = get_object_or_404(visible_expenses(actor=actor), workspace=actor.workspace, pk=expense_id, voided_at=None)
    text = request.POST.get("text", "").strip()
    if not text or len(text) > 500:
        messages.error(request, "Comments must contain between 1 and 500 characters.")
    else:
        ExpenseEvent.objects.create(expense=expense, actor=actor, kind="comment", text=text)
    return redirect("expenses:detail", workspace_id=workspace_id, expense_id=expense_id)


@login_required
@require_POST
def restore(request, workspace_id, expense_id):
    actor = membership(request, workspace_id)
    expense = get_object_or_404(visible_expenses(actor=actor).select_related("circle"), pk=expense_id, voided_at__isnull=False)
    try:
        from .services import restore_expense
        restore_expense(actor, expense_id, int(request.POST.get("version", "")))
    except (ValueError, ValidationError, Expense.DoesNotExist, OperationalError):
        messages.error(request, "The expense changed. Reload before restoring.")
    else:
        messages.success(request, "Expense restored. Balances updated.")
    return ledger_redirect("expenses:overview", workspace_id, expense.circle)


@login_required
@never_cache
def export_csv(request, workspace_id):
    import csv
    from django.http import HttpResponse
    actor = membership(request, workspace_id)
    circle = requested_circle(request, actor)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="expenses_' + timezone.now().strftime("%Y-%m-%d_%H-%M") + '.csv"'
    writer = csv.writer(response)
    writer.writerow(["Title", "USD", "Paid by", "Date", "Category", "Split"])
    def safe(text):
        text = str(text)
        return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text
    for expense in circle_rows(Expense.objects, actor.workspace, circle).filter(voided_at=None).select_related("paid_by"):
        writer.writerow([safe(expense.title), f"{expense.amount_cents / 100:.2f}", safe(expense.paid_by.display_name), expense.date, expense.category, expense.get_split_method_display()])
    return response
