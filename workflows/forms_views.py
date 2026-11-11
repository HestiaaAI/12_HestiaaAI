"""Task board: selected-household filters, create/edit, and occurrence lifecycle."""
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.views.generic import ListView

from households.context import HouseholdRequired, require_household
from households.models import Membership, Workspace

from .models import Assignment, Task, TaskOccurrence
from .task_forms import TaskCreateForm, TaskEditForm, TaskFilterForm
from .task_workflow import (
    active_assignment,
    annotate_board_tasks,
    assign_occurrence,
    board_day_strip,
    complete_occurrence,
    create_task_with_schedule,
    current_occurrence,
    decorate_board_tasks,
    delete_task,
    reschedule_occurrence,
    start_occurrence,
    workspace_assignees,
)


def _lock_actor(membership, user):
    Workspace.objects.select_for_update().get(pk=membership.workspace_id)
    return Membership.objects.select_for_update(of=("self",)).get(
        pk=membership.pk,
        user=user,
        user__is_active=True,
        is_active=True,
    )


def _require_selected_task(request, task_id) -> tuple[Membership, Task]:
    membership = require_household(request)
    task = get_object_or_404(
        Task.objects.select_related("workspace", "created_by_membership"),
        pk=task_id,
        workspace_id=membership.workspace_id,
    )
    return membership, task


def _require_selected_occurrence(request, occurrence_id) -> tuple[Membership, TaskOccurrence]:
    membership = require_household(request)
    occurrence = get_object_or_404(
        TaskOccurrence.objects.select_related("task", "task__workspace"),
        pk=occurrence_id,
        task__workspace_id=membership.workspace_id,
    )
    return membership, occurrence


class TaskBoardView(ListView):
    model = Task
    template_name = "tasks/forms/task_board.html"
    context_object_name = "tasks"
    paginate_by = 6

    def _selected_day(self) -> date:
        raw = (self.request.GET.get("day") or "").strip()
        parsed = parse_date(raw) if raw else None
        return parsed or timezone.localdate()

    def get_queryset(self):
        queryset = (
            Task.objects.filter(workspace=require_household(self.request).workspace)
            .select_related("workspace", "created_by_membership")
            .order_by("-created_at", "-task_id")
        )
        self.filter_form = TaskFilterForm(
            self.request.GET, membership=self.request.active_membership
        )
        if not self.filter_form.is_valid():
            # An invalid/unauthorized filter must not silently expose a wider list.
            return queryset.none()
        filters = self.filter_form.cleaned_data
        if filters["q"]:
            queryset = queryset.filter(title__icontains=filters["q"])
        for field in ("workspace", "priority", "task_type"):
            if filters[field]:
                queryset = queryset.filter(**{field: filters[field]})
        self.selected_day = self._selected_day()
        if self.request.GET.get("day"):
            queryset = queryset.filter(
                occurrences__due_at__date=self.selected_day
            ).distinct()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tasks"] = decorate_board_tasks(
            annotate_board_tasks(list(context["tasks"])),
            viewer=self.request.user,
        )
        context["filter_form"] = self.filter_form
        context.setdefault(
            "create_form",
            TaskCreateForm(membership=self.request.active_membership),
        )
        context["has_workspaces"] = bool(self.request.active_membership)
        context["has_filters"] = any(
            self.request.GET.get(key) for key in self.filter_form.fields
        )
        params = self.request.GET.copy()
        params.pop("page", None)
        context["filter_query"] = params.urlencode()
        selected_day = getattr(self, "selected_day", self._selected_day())
        context["selected_day"] = selected_day
        context["day_strip"] = board_day_strip(selected_day)
        context["day_headline"] = (
            f"{selected_day.strftime('%A, %B')} {selected_day.day}"
        )
        context["today"] = timezone.localdate()
        context["day_filter_active"] = bool(self.request.GET.get("day"))
        # Associate inline errors/help with their input for screen readers.
        for form in (context["filter_form"], context["create_form"]):
            for field in form:
                described_by = []
                if field.help_text:
                    described_by.append(f"{field.auto_id}_help")
                if field.errors:
                    field.field.widget.attrs["aria-invalid"] = "true"
                    described_by.append(f"{field.auto_id}_errors")
                if described_by:
                    field.field.widget.attrs["aria-describedby"] = " ".join(described_by)
        return context

    def post(self, request, *args, **kwargs):
        membership = require_household(request)
        form = TaskCreateForm(request.POST, membership=membership)
        if form.is_valid():
            # Never accept a creator ID from the browser.
            form.instance.workspace = membership.workspace
            form.instance.created_by_membership = membership
            try:
                with transaction.atomic():
                    actor = _lock_actor(membership, request.user)
                    task = form.save(commit=False)
                    task.workspace = actor.workspace
                    task.created_by_membership = actor
                    create_task_with_schedule(
                        task=task,
                        due_at=form.cleaned_data.get("due_at"),
                        assignee=form.cleaned_data.get("assignee"),
                        proposed_by=actor,
                    )
            except Membership.DoesNotExist:
                raise HouseholdRequired()
            except IntegrityError:
                if not Task.objects.filter(
                    workspace=membership.workspace,
                    title=form.cleaned_data["title"],
                ).exists():
                    raise
                form.add_error(
                    "title",
                    "A task with this title already exists in this household.",
                )
            else:
                messages.success(request, f'Task “{task.title}” created.')
                # POST/Redirect/GET prevents accidental repeat submissions.
                return redirect("task_forms:board")
        self.object_list = self.get_queryset()
        return self.render_to_response(self.get_context_data(create_form=form))


@login_required
def task_edit(request, task_id):
    membership, task = _require_selected_task(request, task_id)
    occurrence = current_occurrence(task)
    assignment = active_assignment(occurrence)
    roommates = workspace_assignees(task.workspace)

    if request.method == "POST":
        form = TaskEditForm(request.POST, instance=task, membership=membership)
        if form.is_valid():
            try:
                with transaction.atomic():
                    actor = _lock_actor(membership, request.user)
                    if task.workspace_id != actor.workspace_id:
                        raise HouseholdRequired()
                    form.save()
                    due_at = form.cleaned_data.get("due_at")
                    assignee = form.cleaned_data.get("assignee")
                    if occurrence is None:
                        create_task_with_schedule(
                            task=task,
                            due_at=due_at,
                            assignee=assignee,
                            proposed_by=actor,
                        )
                    else:
                        reschedule_occurrence(occurrence, due_at)
                        if assignee is not None:
                            assign_occurrence(
                                occurrence,
                                assignee=assignee,
                                proposed_by=actor,
                            )
                        elif active_assignment(occurrence) is not None:
                            current = active_assignment(occurrence)
                            current.state = Assignment.AssignmentState.WITHDRAWN
                            current.save(update_fields=["state"])
                            if occurrence.state in {
                                TaskOccurrence.OccurrenceState.ASSIGNED,
                                TaskOccurrence.OccurrenceState.OFFER_PENDING,
                            }:
                                occurrence.state = TaskOccurrence.OccurrenceState.OPEN
                                occurrence.save(update_fields=["state", "updated_at"])
            except Membership.DoesNotExist:
                raise HouseholdRequired()
            messages.success(request, f'Task “{task.title}” updated.')
            return redirect("task_forms:board")
    else:
        initial = {}
        if occurrence and occurrence.due_at:
            initial["due_at"] = occurrence.due_at.strftime("%Y-%m-%dT%H:%M")
        if assignment:
            initial["assignee"] = assignment.offered_to_membership_id
        form = TaskEditForm(instance=task, membership=membership, initial=initial)

    return render(
        request,
        "tasks/forms/task_edit.html",
        {
            "form": form,
            "task": task,
            "occurrence": occurrence,
            "roommates": roommates,
        },
    )


@login_required
def task_delete(request, task_id):
    if request.method != "POST":
        return HttpResponseForbidden("POST required")
    membership, task = _require_selected_task(request, task_id)
    title = task.title
    try:
        with transaction.atomic():
            actor = _lock_actor(membership, request.user)
            if task.workspace_id != actor.workspace_id:
                raise HouseholdRequired()
            delete_task(task)
    except Membership.DoesNotExist:
        raise HouseholdRequired()
    messages.success(request, f'Task “{title}” deleted.')
    return redirect("task_forms:board")


@login_required
def occurrence_start(request, occurrence_id):
    if request.method != "POST":
        return HttpResponseForbidden("POST required")
    membership, occurrence = _require_selected_occurrence(request, occurrence_id)
    try:
        with transaction.atomic():
            actor = _lock_actor(membership, request.user)
            if occurrence.task.workspace_id != actor.workspace_id:
                raise HouseholdRequired()
            start_occurrence(occurrence)
        messages.success(request, f'Started “{occurrence.task.title}”.')
    except Membership.DoesNotExist:
        raise HouseholdRequired()
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("task_forms:board")


@login_required
def occurrence_complete(request, occurrence_id):
    if request.method != "POST":
        return HttpResponseForbidden("POST required")
    membership, occurrence = _require_selected_occurrence(request, occurrence_id)
    try:
        with transaction.atomic():
            actor = _lock_actor(membership, request.user)
            if occurrence.task.workspace_id != actor.workspace_id:
                raise HouseholdRequired()
            complete_occurrence(occurrence)
        messages.success(request, f'Marked “{occurrence.task.title}” complete.')
    except Membership.DoesNotExist:
        raise HouseholdRequired()
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("task_forms:board")


@login_required
def occurrence_reassign(request, occurrence_id):
    """POST assignee=<membership_id> and/or due_at to reassign / reschedule."""
    if request.method != "POST":
        return HttpResponseForbidden("POST required")
    membership, occurrence = _require_selected_occurrence(request, occurrence_id)
    assignee_id = request.POST.get("assignee")
    due_raw = (request.POST.get("due_at") or "").strip()
    try:
        with transaction.atomic():
            actor = _lock_actor(membership, request.user)
            if occurrence.task.workspace_id != actor.workspace_id:
                raise HouseholdRequired()
            changed = False
            if due_raw:
                parsed = (
                    parse_datetime(due_raw.replace("T", " ", 1))
                    if "T" in due_raw
                    else parse_datetime(due_raw)
                )
                if parsed is None:
                    messages.error(request, "Could not parse the new due date.")
                    return redirect("task_forms:board")
                reschedule_occurrence(occurrence, parsed)
                changed = True
            if assignee_id:
                assignee = get_object_or_404(
                    Membership,
                    pk=assignee_id,
                    workspace_id=actor.workspace_id,
                    is_active=True,
                    can_receive_assignments=True,
                )
                assign_occurrence(occurrence, assignee=assignee, proposed_by=actor)
                changed = True
            if changed:
                messages.success(request, f'Updated “{occurrence.task.title}”.')
            else:
                messages.error(request, "Choose a roommate or a new due date.")
    except Membership.DoesNotExist:
        raise HouseholdRequired()
    return redirect("task_forms:board")
