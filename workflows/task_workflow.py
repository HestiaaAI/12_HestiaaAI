"""Dynamic task workflow helpers: occurrences, assignments, lifecycle."""

from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.db.models import Max, Prefetch, Q
from django.utils import timezone

from households.models import Membership, Workspace

from .models import Assignment, Task, TaskOccurrence


def user_workspaces(user):
    """Households the signed-in user can access through an active membership."""
    if user is None or not user.is_authenticated:
        return Workspace.objects.none()
    return Workspace.objects.filter(
        memberships__user=user,
        memberships__is_active=True,
    ).distinct().order_by("name")


def user_memberships(user, workspace=None):
    qs = Membership.objects.filter(user=user, is_active=True).select_related("workspace", "user")
    if workspace is not None:
        qs = qs.filter(workspace=workspace)
    return qs


def active_membership(user, workspace):
    return user_memberships(user, workspace=workspace).first()


def workspace_assignees(workspace):
    return Membership.objects.filter(
        workspace=workspace,
        is_active=True,
        can_receive_assignments=True,
    ).select_related("user").order_by("display_name")


def member_can_access_task(user, task: Task) -> bool:
    return user_memberships(user, workspace=task.workspace).exists()


def current_occurrence(task: Task):
    """Prefer the latest incomplete occurrence; otherwise the newest one."""
    open_states = {
        TaskOccurrence.OccurrenceState.OPEN,
        TaskOccurrence.OccurrenceState.OFFER_PENDING,
        TaskOccurrence.OccurrenceState.ASSIGNED,
        TaskOccurrence.OccurrenceState.IN_PROGRESS,
        TaskOccurrence.OccurrenceState.OVERDUE,
    }
    qs = task.occurrences.all()
    current = qs.filter(state__in=open_states).order_by("due_at", "sequence").first()
    return current or qs.order_by("-sequence").first()


def active_assignment(occurrence: TaskOccurrence | None):
    if occurrence is None:
        return None
    return (
        occurrence.assignments.exclude(
            state__in=[
                Assignment.AssignmentState.DECLINED,
                Assignment.AssignmentState.WITHDRAWN,
                Assignment.AssignmentState.REASSIGNED,
            ]
        )
        .select_related("offered_to_membership")
        .order_by("-attempt_number")
        .first()
    )


def annotate_board_tasks(tasks):
    """Attach current occurrence + assignment for board cards without N+1."""
    task_list = list(tasks)
    if not task_list:
        return task_list
    ids = [task.pk for task in task_list]
    occurrences = (
        TaskOccurrence.objects.filter(task_id__in=ids)
        .prefetch_related(
            Prefetch(
                "assignments",
                queryset=Assignment.objects.select_related("offered_to_membership").order_by(
                    "-attempt_number"
                ),
            )
        )
        .order_by("task_id", "-sequence")
    )
    by_task: dict[int, list[TaskOccurrence]] = {}
    for occurrence in occurrences:
        by_task.setdefault(occurrence.task_id, []).append(occurrence)
    for task in task_list:
        occs = by_task.get(task.pk, [])
        open_states = {
            TaskOccurrence.OccurrenceState.OPEN,
            TaskOccurrence.OccurrenceState.OFFER_PENDING,
            TaskOccurrence.OccurrenceState.ASSIGNED,
            TaskOccurrence.OccurrenceState.IN_PROGRESS,
            TaskOccurrence.OccurrenceState.OVERDUE,
        }
        current = next((o for o in reversed(occs) if o.state in open_states), None)
        if current is None and occs:
            current = occs[0]
        task.board_occurrence = current
        task.board_assignment = active_assignment(current) if current else None
    return task_list


def _next_sequence(task: Task) -> int:
    latest = task.occurrences.aggregate(Max("sequence"))["sequence__max"] or 0
    return latest + 1


def _weekly_offsets(recurrence_rule: str) -> list[int]:
    """Return extra weekly offsets (1..n) when recurrence looks weekly."""
    text = (recurrence_rule or "").strip().lower()
    if not text:
        return []
    weekly_tokens = ("every week", "weekly", "every sunday", "every monday", "every tuesday",
                     "every wednesday", "every thursday", "every friday", "every saturday",
                     "each week")
    if any(token in text for token in weekly_tokens) or text.startswith("every "):
        return [1, 2, 3]
    return []


@transaction.atomic
def create_task_with_schedule(
    *,
    task: Task,
    due_at=None,
    assignee: Membership | None = None,
    proposed_by: Membership | None = None,
):
    """Persist a task definition plus first occurrence (and optional assignment)."""
    task.save()
    now = timezone.now()
    due = due_at
    if due is not None and timezone.is_naive(due):
        due = timezone.make_aware(due, timezone.get_current_timezone())

    first = TaskOccurrence.objects.create(
        task=task,
        sequence=1,
        scheduled_for=due or now,
        due_at=due,
        state=(
            TaskOccurrence.OccurrenceState.ASSIGNED
            if assignee is not None
            else TaskOccurrence.OccurrenceState.OPEN
        ),
    )
    if assignee is not None:
        Assignment.objects.create(
            task_occurrence=first,
            proposed_by_membership=proposed_by,
            offered_to_membership=assignee,
            attempt_number=1,
            offered_at=now,
            state=Assignment.AssignmentState.ACCEPTED,
            responded_at=now,
            accepted_at=now,
        )

    for offset in _weekly_offsets(task.recurrence_rule):
        stamp = (due or now) + timedelta(weeks=offset)
        TaskOccurrence.objects.create(
            task=task,
            sequence=1 + offset,
            scheduled_for=stamp,
            due_at=stamp,
            state=TaskOccurrence.OccurrenceState.OPEN,
        )
    return task, first


@transaction.atomic
def assign_occurrence(
    occurrence: TaskOccurrence,
    *,
    assignee: Membership,
    proposed_by: Membership | None,
):
    current = active_assignment(occurrence)
    attempt = (occurrence.assignments.aggregate(Max("attempt_number"))["attempt_number__max"] or 0) + 1
    if current is not None:
        current.state = Assignment.AssignmentState.REASSIGNED
        current.responded_at = timezone.now()
        current.save(update_fields=["state", "responded_at"])
    assignment = Assignment.objects.create(
        task_occurrence=occurrence,
        proposed_by_membership=proposed_by,
        offered_to_membership=assignee,
        attempt_number=attempt,
        offered_at=timezone.now(),
        state=Assignment.AssignmentState.ACCEPTED,
        responded_at=timezone.now(),
        accepted_at=timezone.now(),
    )
    if occurrence.state in {
        TaskOccurrence.OccurrenceState.OPEN,
        TaskOccurrence.OccurrenceState.OFFER_PENDING,
        TaskOccurrence.OccurrenceState.REPORTED_COMPLETE,
        TaskOccurrence.OccurrenceState.CANCELLED,
        TaskOccurrence.OccurrenceState.SKIPPED,
    }:
        occurrence.state = TaskOccurrence.OccurrenceState.ASSIGNED
        occurrence.save(update_fields=["state", "updated_at"])
    elif occurrence.state == TaskOccurrence.OccurrenceState.IN_PROGRESS:
        pass
    else:
        occurrence.state = TaskOccurrence.OccurrenceState.ASSIGNED
        occurrence.save(update_fields=["state", "updated_at"])
    return assignment


@transaction.atomic
def reschedule_occurrence(occurrence: TaskOccurrence, due_at):
    if due_at is not None and timezone.is_naive(due_at):
        due_at = timezone.make_aware(due_at, timezone.get_current_timezone())
    occurrence.due_at = due_at
    occurrence.scheduled_for = due_at or occurrence.scheduled_for
    if (
        occurrence.state == TaskOccurrence.OccurrenceState.OVERDUE
        and due_at
        and due_at >= timezone.now()
    ):
        occurrence.state = TaskOccurrence.OccurrenceState.ASSIGNED if active_assignment(occurrence) else TaskOccurrence.OccurrenceState.OPEN
    occurrence.save(update_fields=["due_at", "scheduled_for", "state", "updated_at"])
    return occurrence


def start_occurrence(occurrence: TaskOccurrence):
    if occurrence.state in {
        TaskOccurrence.OccurrenceState.REPORTED_COMPLETE,
        TaskOccurrence.OccurrenceState.CANCELLED,
        TaskOccurrence.OccurrenceState.SKIPPED,
    }:
        raise ValueError("This occurrence cannot be started.")
    occurrence.state = TaskOccurrence.OccurrenceState.IN_PROGRESS
    occurrence.save(update_fields=["state", "updated_at"])
    return occurrence


def complete_occurrence(occurrence: TaskOccurrence):
    if occurrence.state in {
        TaskOccurrence.OccurrenceState.CANCELLED,
        TaskOccurrence.OccurrenceState.SKIPPED,
    }:
        raise ValueError("This occurrence cannot be completed.")
    occurrence.state = TaskOccurrence.OccurrenceState.REPORTED_COMPLETE
    occurrence.save(update_fields=["state", "updated_at"])
    return occurrence


@transaction.atomic
def delete_task(task: Task):
    occurrence_ids = list(task.occurrences.values_list("pk", flat=True))
    Assignment.objects.filter(task_occurrence_id__in=occurrence_ids).delete()
    task.delete()


def tasks_for_user(user):
    return (
        Task.objects.filter(workspace__in=user_workspaces(user))
        .select_related("workspace", "created_by_membership")
        .order_by("-created_at", "-task_id")
    )


def open_occurrence_filter():
    return Q(
        state__in=[
            TaskOccurrence.OccurrenceState.OPEN,
            TaskOccurrence.OccurrenceState.OFFER_PENDING,
            TaskOccurrence.OccurrenceState.ASSIGNED,
            TaskOccurrence.OccurrenceState.IN_PROGRESS,
            TaskOccurrence.OccurrenceState.OVERDUE,
        ]
    )


def location_tone(location: str | None) -> str:
    """Map a free-text location to Little Home Club card tones."""
    text = (location or "").strip().lower()
    if any(token in text for token in ("kitchen", "cook", "dish", "fridge")):
        return "peach"
    if any(token in text for token in ("living", "plant", "sofa", "lounge", "bedroom")):
        return "sage"
    if any(token in text for token in ("out", "recycl", "yard", "garage", "garden", "porch")):
        return "paper"
    return "paper"


def board_day_strip(selected_day, *, span: int = 2):
    """Return nearby calendar days for the Tasks date scroller."""
    from datetime import timedelta

    days = []
    for offset in range(-span, span + 1):
        day = selected_day + timedelta(days=offset)
        days.append(
            {
                "date": day,
                "label": day.strftime("%a")[0],
                "number": day.day,
                "selected": day == selected_day,
                "iso": day.isoformat(),
            }
        )
    return days


def decorate_board_tasks(tasks, *, viewer=None):
    """Attach tone + friendly assignee/due labels used by the themed board."""
    from datetime import timedelta

    from django.utils import timezone as dj_tz

    today = dj_tz.localdate()
    for task in tasks:
        task.board_tone = location_tone(task.default_location)
        occurrence = getattr(task, "board_occurrence", None)
        assignment = getattr(task, "board_assignment", None)
        if assignment and assignment.offered_to_membership:
            member = assignment.offered_to_membership
            if viewer is not None and member.user_id == getattr(viewer, "pk", None):
                task.board_assignee_label = "You"
            else:
                task.board_assignee_label = member.display_name
        else:
            task.board_assignee_label = "Unassigned"
        if occurrence and occurrence.due_at:
            local_due = dj_tz.localtime(occurrence.due_at)
            due_day = local_due.date()
            if due_day == today:
                task.board_due_label = local_due.strftime("%I:%M %p").lstrip("0")
            elif due_day == today + timedelta(days=1):
                task.board_due_label = "Tomorrow"
            elif due_day == today - timedelta(days=1):
                task.board_due_label = "Yesterday"
            else:
                task.board_due_label = local_due.strftime("%b %d").replace(" 0", " ")
        else:
            task.board_due_label = "Flexible"
        task.board_space = (task.default_location or task.get_task_type_display()).upper()
    return tasks
