"""Scoped task filters and model-backed task creation/edit."""
from django import forms
from django.utils import timezone

from households.models import Membership, Workspace

from .models import Task
from .task_workflow import workspace_assignees


def available_workspaces(membership=None):
    """Default-deny workspace choices for an explicitly supplied membership."""
    return (
        Workspace.objects.filter(pk=membership.workspace_id)
        if membership and membership.is_active
        else Workspace.objects.none()
    )


class TaskFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        max_length=200,
        label="Search tasks",
        widget=forms.TextInput(attrs={"type": "search", "placeholder": "Search by title…"}),
    )
    workspace = forms.ModelChoiceField(
        queryset=Workspace.objects.none(),
        required=False,
        empty_label="Selected household",
        label="Household",
    )
    priority = forms.ChoiceField(
        required=False,
        choices=[("", "All priorities"), *Task.Priority.choices],
    )
    task_type = forms.ChoiceField(
        required=False,
        choices=[("", "All types"), *Task.TaskType.choices],
        label="Task type",
    )

    def __init__(self, *args, membership=None, **kwargs):
        super().__init__(*args, auto_id="filter_%s", **kwargs)
        self.fields["workspace"].queryset = available_workspaces(membership)
        self.fields["workspace"].widget = forms.HiddenInput()


class TaskCreateForm(forms.ModelForm):
    due_at = forms.DateTimeField(
        required=False,
        label="Due",
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"],
        help_text="When this occurrence is due. Leave blank for an open backlog item.",
    )
    assignee = forms.ModelChoiceField(
        queryset=Membership.objects.none(),
        required=False,
        empty_label="Unassigned",
        label="Assign to",
        help_text="Roommate who should own this occurrence.",
    )

    class Meta:
        model = Task
        # Explicit allowlist: creator and other relationships are server-owned.
        fields = [
            "workspace",
            "title",
            "description",
            "task_type",
            "priority",
            "default_location",
            "recurrence_rule",
        ]
        labels = {
            "workspace": "Household",
            "default_location": "Location",
            "recurrence_rule": "Repeats",
        }
        help_texts = {
            "recurrence_rule": (
                "Optional. Weekly phrasing (e.g. Every Sunday) also pre-schedules "
                "the next few weekly occurrences from the due date."
            ),
        }
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. Plan the weekly groceries"}),
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": "What needs to be done?"}),
            "default_location": forms.TextInput(attrs={"placeholder": "e.g. Kitchen"}),
            "recurrence_rule": forms.TextInput(attrs={"placeholder": "One-time task"}),
        }

    def __init__(self, *args, membership=None, **kwargs):
        self.membership = membership
        super().__init__(*args, auto_id="create_%s", **kwargs)
        if "workspace" in self.fields:
            self.fields["workspace"].queryset = available_workspaces(membership)
            self.fields["workspace"].widget = forms.HiddenInput()
            if membership and not self.is_bound:
                self.initial.setdefault("workspace", membership.workspace_id)
        workspace = None
        if membership and membership.is_active:
            workspace = membership.workspace
        elif self.instance and getattr(self.instance, "workspace_id", None):
            workspace = self.instance.workspace
        if workspace is not None:
            self.fields["assignee"].queryset = workspace_assignees(workspace)
        else:
            self.fields["assignee"].queryset = Membership.objects.none()

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        if not title:
            raise forms.ValidationError("Enter a task title.")
        return title

    def clean_workspace(self):
        workspace = self.cleaned_data["workspace"]
        allowed = available_workspaces(self.membership)
        if not allowed.filter(pk=workspace.pk).exists():
            raise forms.ValidationError("Choose the selected household.")
        return workspace

    def clean_assignee(self):
        assignee = self.cleaned_data.get("assignee")
        workspace = self.cleaned_data.get("workspace")
        if assignee is None:
            return None
        if workspace is None or assignee.workspace_id != workspace.pk:
            raise forms.ValidationError("Assignee must belong to the selected household.")
        if not assignee.is_active or not assignee.can_receive_assignments:
            raise forms.ValidationError("That roommate cannot receive assignments.")
        return assignee

    def clean_due_at(self):
        due_at = self.cleaned_data.get("due_at")
        if due_at is None:
            return None
        if timezone.is_naive(due_at):
            due_at = timezone.make_aware(due_at, timezone.get_current_timezone())
        return due_at


class TaskEditForm(TaskCreateForm):
    """Edit definition fields plus the current occurrence’s due date / assignee."""

    class Meta(TaskCreateForm.Meta):
        fields = [
            "title",
            "description",
            "task_type",
            "priority",
            "default_location",
            "recurrence_rule",
        ]

    def __init__(self, *args, membership=None, **kwargs):
        super().__init__(*args, membership=membership, **kwargs)
        self.auto_id = "edit_%s"
        if self.instance and self.instance.pk:
            self.fields["assignee"].queryset = workspace_assignees(self.instance.workspace)

    def clean_assignee(self):
        assignee = self.cleaned_data.get("assignee")
        workspace = self.instance.workspace if self.instance and self.instance.pk else None
        if assignee is None:
            return None
        if workspace is None or assignee.workspace_id != workspace.pk:
            raise forms.ValidationError("Assignee must belong to this household.")
        if not assignee.is_active or not assignee.can_receive_assignments:
            raise forms.ValidationError("That roommate cannot receive assignments.")
        return assignee
