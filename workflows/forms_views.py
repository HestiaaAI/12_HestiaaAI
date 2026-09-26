"""Person 4: one ListView handles read-only GET filters and Task creation POST."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError, transaction
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import ListView

from households.models import Membership
from .models import Task
from .task_forms import TaskCreateForm, TaskFilterForm, available_workspaces


class TaskBoardView(LoginRequiredMixin, ListView):
    model = Task
    template_name = "tasks/forms/task_board.html"
    context_object_name = "tasks"
    paginate_by = 6

    def get_queryset(self):
        queryset = Task.objects.filter(
            workspace__in=available_workspaces(self.request.user)
        ).select_related("workspace").order_by("-created_at", "-task_id")
        self.filter_form = TaskFilterForm(self.request.GET, user=self.request.user)
        if not self.filter_form.is_valid():
            # An invalid/unauthorized filter must not silently expose a wider list.
            return queryset.none()
        filters = self.filter_form.cleaned_data
        if filters["q"]:
            queryset = queryset.filter(title__icontains=filters["q"])
        for field in ("workspace", "priority", "task_type"):
            if filters[field]:
                queryset = queryset.filter(**{field: filters[field]})
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.filter_form
        context.setdefault("create_form", TaskCreateForm(user=self.request.user))
        context["has_workspaces"] = available_workspaces(self.request.user).exists()
        context["has_filters"] = any(self.request.GET.get(key) for key in self.filter_form.fields)
        params = self.request.GET.copy()
        params.pop("page", None)
        context["filter_query"] = params.urlencode()
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
        form = TaskCreateForm(request.POST, user=request.user)
        if form.is_valid():
            # Never accept a creator ID from the browser.
            membership = Membership.objects.filter(
                user=request.user, workspace=form.cleaned_data["workspace"], is_active=True
            ).first()
            if membership is None:
                form.add_error("workspace", "Your household membership is no longer active.")
            else:
                form.instance.created_by_membership = membership
                try:
                    with transaction.atomic():
                        task = form.save()
                except IntegrityError:
                    # Cover a simultaneous duplicate submission as well as normal
                    # ModelForm constraint validation. Unexpected DB errors still surface.
                    if not Task.objects.filter(workspace=form.cleaned_data["workspace"],
                                               title=form.cleaned_data["title"]).exists():
                        raise
                    form.add_error("title", "A task with this title already exists in this household.")
                else:
                    messages.success(request, f'Task “{task.title}” created.')
                    # POST/Redirect/GET: refreshing the result cannot repeat the POST.
                    return redirect(reverse("task_forms:board") + f"?workspace={task.workspace_id}")
        self.object_list = self.get_queryset()
        return self.render_to_response(self.get_context_data(create_form=form))
