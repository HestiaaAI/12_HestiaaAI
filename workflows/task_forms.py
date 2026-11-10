"""Scoped task filters and model-backed task creation."""
from django import forms

from households.models import Workspace
from .models import Task


def available_workspaces(membership=None):
    """Default-deny workspace choices for an explicitly supplied membership."""
    return Workspace.objects.filter(pk=membership.workspace_id) if membership and membership.is_active else Workspace.objects.none()


class TaskFilterForm(forms.Form):
    q = forms.CharField(required=False, max_length=200, label="Search tasks",
                        widget=forms.TextInput(attrs={"type": "search", "placeholder": "Search by title…"}))
    workspace = forms.ModelChoiceField(queryset=Workspace.objects.none(), required=False,
                                       empty_label="Selected household", label="Household")
    priority = forms.ChoiceField(required=False, choices=[("", "All priorities"), *Task.Priority.choices])
    task_type = forms.ChoiceField(required=False, choices=[("", "All types"), *Task.TaskType.choices], label="Task type")

    def __init__(self, *args, membership=None, **kwargs):
        super().__init__(*args, auto_id="filter_%s", **kwargs)
        self.fields["workspace"].queryset = available_workspaces(membership)
        self.fields["workspace"].widget = forms.HiddenInput()


class TaskCreateForm(forms.ModelForm):
    class Meta:
        model = Task
        # Explicit allowlist: creator and other relationships are server-owned.
        fields = ["workspace", "title", "description", "task_type", "priority",
                  "default_location", "recurrence_rule"]
        labels = {"workspace": "Household", "default_location": "Location",
                  "recurrence_rule": "Repeats"}
        help_texts = {"recurrence_rule": "Optional. For example, Every Sunday. This does not schedule occurrences."}
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. Plan the weekly groceries"}),
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": "What needs to be done?"}),
            "default_location": forms.TextInput(attrs={"placeholder": "e.g. Kitchen"}),
            "recurrence_rule": forms.TextInput(attrs={"placeholder": "One-time task"}),
        }

    def __init__(self, *args, membership=None, **kwargs):
        super().__init__(*args, auto_id="create_%s", **kwargs)
        self.fields["workspace"].queryset = available_workspaces(membership)
        self.fields["workspace"].widget = forms.HiddenInput()
        if membership and not self.is_bound:
            self.initial.setdefault('workspace', membership.workspace_id)

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        if not title:
            raise forms.ValidationError("Enter a task title.")
        return title
