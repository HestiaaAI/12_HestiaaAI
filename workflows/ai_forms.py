"""Human review forms built on the existing task creation form."""
from django import forms
from django.forms import BaseFormSet, formset_factory

from households.models import Workspace
from .models import Task
from .task_forms import TaskCreateForm

MAX_TASKS = 20
MAX_DESCRIPTION = Task._meta.get_field("description").max_length or 5000


class BrainDumpForm(forms.Form):
    workspace = forms.ModelChoiceField(queryset=Workspace.objects.none(), label="Household")
    text = forms.CharField(max_length=4000, label="What's on your mind?",
                           widget=forms.Textarea(attrs={"rows": 7, "placeholder":
                               "Guests are coming tomorrow, the kitchen is messy, we need groceries, and the bathroom tap is leaking."}))

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["workspace"].queryset = Workspace.objects.filter(
            memberships__user=user, memberships__is_active=True)


class ReviewTaskForm(TaskCreateForm):
    description = forms.CharField(required=False, max_length=MAX_DESCRIPTION,
                                  widget=forms.Textarea(attrs={"rows": 3}))

    class Meta(TaskCreateForm.Meta):
        fields = ["title", "task_type", "priority", "description"]

    def __init__(self, *args, **kwargs):
        # TaskCreateForm assumes a workspace field. Reuse its model fields and
        # clean_title while keeping every relationship outside browser control.
        forms.ModelForm.__init__(self, *args, **kwargs)


class ReviewFormSet(BaseFormSet):
    def _construct_form(self, index, **kwargs):
        kwargs["empty_permitted"] = False
        return super()._construct_form(index, **kwargs)

    def __init__(self, *args, workspace, **kwargs):
        self.workspace = workspace
        super().__init__(*args, **kwargs)

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        titles = set()
        kept = 0
        for form in self.forms:
            if self._should_delete_form(form):
                continue
            kept += 1
            title = form.cleaned_data["title"]
            if title in titles or Task.objects.filter(workspace=self.workspace, title=title).exists():
                form.add_error("title", "This title already exists in this household or review. Choose another title.")
            titles.add(title)
        if not kept:
            raise forms.ValidationError("Keep at least one task, or start a new brain dump.")


TaskReviewFormSet = formset_factory(ReviewTaskForm, formset=ReviewFormSet,
    extra=0, can_delete=True, max_num=MAX_TASKS, validate_max=True,
    absolute_max=MAX_TASKS)


class ConfirmationForm(forms.Form):
    confirm = forms.BooleanField(label="I reviewed these tasks and want to save the tasks I kept.")
