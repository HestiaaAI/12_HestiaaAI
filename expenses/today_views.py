"""Actionable due work for the selected household."""
from datetime import datetime, time, timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_safe

from households.context import require_household
from inventory.expiry import expiring_batches
from workflows.models import TaskOccurrence
from .insights import household_today, household_zone
from .policies import visible_items

SECTION_LIMIT = 12


@login_required
@require_safe
def today(request):
    actor = require_household(request)
    workspace = actor.workspace
    day = household_today(workspace)
    tomorrow = datetime.combine(day + timedelta(days=1), time.min, household_zone(workspace))
    states = TaskOccurrence.OccurrenceState
    chores = TaskOccurrence.objects.filter(
        task__workspace=workspace, task__recurring_bill__isnull=True, due_at__lt=tomorrow,
    ).exclude(state__in=(states.REPORTED_COMPLETE, states.SKIPPED, states.CANCELLED)).select_related("task")
    return render(request, "expenses/today.html", {
        "workspace": workspace,
        "day": day,
        "chores": chores[:SECTION_LIMIT],
        "bills": workspace.recurring_bills.filter(active=True, next_due__lte=day)[:SECTION_LIMIT],
        "expiry": expiring_batches(workspace, day)[:SECTION_LIMIT],
        "shopping": visible_items(actor=actor).filter(state="open", is_checked=False).select_related("list")[:SECTION_LIMIT],
    })
