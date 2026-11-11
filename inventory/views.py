import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from households.models import Membership, Workspace
from inventory import grocery_ai
from inventory.expiry import (
    SOON_DAYS, batch_snapshot, expiring_batches, household_today, suggestion_inputs,
)
from inventory.forms import GroceryBatchForm, ReceiptBatchFormSet
from inventory.models import GroceryBatch
from inventory.receipt import MAX_RECEIPT_TEXT, receipt_drafts
from workflows.models import Task, TaskOccurrence


logger = logging.getLogger(__name__)
SUGGESTION_SALT = "inventory.grocery-suggestion"
SUGGESTION_AGE = 30 * 60


def memberships(request):
    return Membership.objects.filter(user=request.user, is_active=True).select_related("workspace")


def membership_for(request, workspace_id):
    return get_object_or_404(memberships(request), workspace_id=workspace_id)


def grocery_page(request, member, **extra):
    workspace = member.workspace
    today = household_today(workspace)
    batches = GroceryBatch.objects.filter(workspace=workspace)
    storage = request.GET.get("storage", "")
    active = batches.filter(state=GroceryBatch.State.ACTIVE)
    if storage in GroceryBatch.Storage.values:
        active = active.filter(storage=storage)
    alerts = expiring_batches(workspace, today)
    return render(request, "inventory/groceries.html", {
        "workspace": workspace,
        "memberships": memberships(request),
        "batches": active,
        "history": batches.exclude(state=GroceryBatch.State.ACTIVE).order_by("-closed_at")[:12],
        "today": today,
        "overdue": alerts.filter(expires_on__lt=today),
        "soon": alerts.filter(expires_on__gte=today),
        "soon_days": SOON_DAYS,
        "storage": storage,
        "storage_choices": GroceryBatch.Storage.choices,
        **extra,
    })


@login_required
def groceries(request, workspace_id=None):
    if workspace_id is None:
        member = memberships(request).first()
        if member is None:
            return render(request, "inventory/no_household.html")
        return redirect("groceries:workspace", workspace_id=member.workspace_id)
    return grocery_page(request, membership_for(request, workspace_id))


@login_required
def household(request):
    available = list(memberships(request))
    selected = request.GET.get("workspace")
    member = membership_for(request, selected) if selected and selected.isascii() and selected.isdecimal() else (
        available[0] if available else None
    )
    if member is None:
        return render(request, "inventory/no_household.html")
    return render(request, "inventory/household.html", {
        "workspace": member.workspace,
        "memberships": available,
        "roommates": member.workspace.memberships.filter(is_active=True),
    })


@login_required
@require_http_methods(["GET", "POST"])
def edit_batch(request, workspace_id, batch_id=None):
    workspace = membership_for(request, workspace_id).workspace
    batches = GroceryBatch.objects.filter(workspace=workspace, state=GroceryBatch.State.ACTIVE)
    with transaction.atomic():
        if request.method == "POST":
            Workspace.objects.select_for_update().get(pk=workspace_id)
            batches = batches.select_for_update()
        batch = get_object_or_404(batches, pk=batch_id) if batch_id else None
        form = GroceryBatchForm(request.POST if request.method == "POST" else None, instance=batch)
        if request.method == "POST" and form.is_valid():
            saved = form.save(commit=False)
            saved.workspace = workspace
            saved.save()
            messages.success(request, "Grocery batch updated." if batch_id else "Grocery batch added.")
            return redirect("groceries:workspace", workspace_id=workspace_id)
    return render(request, "inventory/batch_form.html", {
        "workspace": workspace, "batch": batch, "form": form,
    })


@login_required
@require_POST
def close_batch(request, workspace_id, batch_id):
    membership_for(request, workspace_id)
    state = request.POST.get("state")
    if state not in (GroceryBatch.State.CONSUMED, GroceryBatch.State.DISCARDED):
        raise Http404
    batch = get_object_or_404(GroceryBatch, workspace_id=workspace_id, pk=batch_id)
    with transaction.atomic():
        Workspace.objects.select_for_update().get(pk=workspace_id)
        changed = GroceryBatch.objects.filter(pk=batch.pk, state=GroceryBatch.State.ACTIVE).update(
            state=state, closed_at=timezone.now(),
        )
    if changed:
        messages.success(request, f"Marked {batch.name} as {state}.")
    return redirect("groceries:workspace", workspace_id=workspace_id)


@login_required
@require_POST
def suggest(request, workspace_id):
    member = membership_for(request, workspace_id)
    batches = suggestion_inputs(member.workspace, household_today(member.workspace))
    if not batches:
        messages.info(request, "Add a grocery batch expiring soon to get a meal idea.")
        return redirect("groceries:workspace", workspace_id=workspace_id)
    try:
        idea = grocery_ai.meal_idea(batches)
    except Exception:
        logger.exception("Grocery suggestion failed")
        return grocery_page(request, member, suggestion_error="Meal ideas are unavailable right now. Try again shortly.")
    token = signing.dumps({
        "member": member.pk, "workspace": workspace_id, "idea": idea, "batches": batch_snapshot(batches),
    }, salt=SUGGESTION_SALT)
    return grocery_page(request, member, idea=idea, suggestion_token=token)


@login_required
@require_POST
def approve(request, workspace_id):
    member = membership_for(request, workspace_id)
    try:
        draft = signing.loads(request.POST.get("suggestion", ""), salt=SUGGESTION_SALT,
                              max_age=SUGGESTION_AGE)
        if draft["member"] != member.pk or draft["workspace"] != workspace_id:
            raise signing.BadSignature
    except signing.BadSignature:
        messages.error(request, "This suggestion has expired or is invalid. Generate another meal idea.")
        return redirect("groceries:workspace", workspace_id=workspace_id)

    with transaction.atomic():
        workspace = Workspace.objects.select_for_update().get(pk=workspace_id)
        today = household_today(workspace)
        batches = suggestion_inputs(workspace, today)
        if draft["batches"] != batch_snapshot(batches):
            messages.info(request, "Your groceries have changed. Generate a new idea using the current batches.")
            return redirect("groceries:workspace", workspace_id=workspace_id)
        names = ", ".join(dict.fromkeys(batch.name for batch in batches))
        title = f"Use up {names[:145]} ({today:%Y-%m-%d}) · groceries"
        task, created = Task.objects.get_or_create(
            workspace=workspace, title=title, household_only=True,
            defaults={
                "description": draft["idea"], "created_by_membership": member,
                "task_type": Task.TaskType.CHORE,
            },
        )
        if created:
            TaskOccurrence.objects.create(task=task)
    messages.success(request, "Added the meal idea to Tasks." if created else "This grocery task is already on the board.")
    return redirect(task)



@login_required
@require_http_methods(["GET", "POST"])
def scan_receipt(request, workspace_id):
    workspace = membership_for(request, workspace_id).workspace
    review = None
    receipt_error = ""
    if request.method == "POST":
        if request.POST.get("action") == "review":
            receipt_text = request.POST.get("receipt_text", "")
            if len(receipt_text) > MAX_RECEIPT_TEXT:
                receipt_error = "The receipt text is too long. Use a shorter receipt or add batches manually."
            else:
                rows = receipt_drafts(receipt_text)
                if rows:
                    review = ReceiptBatchFormSet(initial=rows)
                else:
                    receipt_error = "No grocery rows found. Try a clearer photo or add batches manually."
        elif request.POST.get("action") == "save":
            review = ReceiptBatchFormSet(request.POST)
            if review.is_valid():
                with transaction.atomic():
                    Workspace.objects.select_for_update().get(pk=workspace_id)
                    for form in review.forms:
                        if form.cleaned_data.get("DELETE"):
                            continue
                        batch = form.save(commit=False)
                        batch.workspace = workspace
                        batch.save()
                messages.success(request, "Reviewed groceries added to your household.")
                return redirect("groceries:workspace", workspace_id=workspace_id)
        else:
            raise Http404
    return render(request, "inventory/scan_receipt.html", {
        "workspace": workspace, "review": review, "receipt_error": receipt_error,
    })
