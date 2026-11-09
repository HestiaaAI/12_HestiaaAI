"""Task board with read-only filters and explicitly submitted task creation."""
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.shortcuts import redirect
from django.views.generic import ListView

from households.models import Membership
from households.context import HouseholdRequired, require_household
from .models import Task
from .task_forms import TaskCreateForm, TaskFilterForm


class TaskBoardView(ListView):
    model = Task
    template_name = "tasks/forms/task_board.html"
    context_object_name = "tasks"
    paginate_by = 6

    def get_queryset(self):
        queryset = Task.objects.filter(
            workspace=require_household(self.request).workspace
        ).select_related("workspace").order_by("-created_at", "-task_id")
        self.filter_form = TaskFilterForm(self.request.GET, membership=self.request.active_membership)
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
        context.setdefault("create_form", TaskCreateForm(membership=self.request.active_membership))
        context["has_workspaces"] = bool(self.request.active_membership)
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
        membership = require_household(request)
        form = TaskCreateForm(request.POST, membership=membership)
        if form.is_valid():
            # Never accept a creator ID from the browser.
            form.instance.workspace = membership.workspace
            form.instance.created_by_membership = membership
            try:
                with transaction.atomic():
                    Membership.objects.select_for_update().get(pk=membership.pk, user=request.user, is_active=True)
                    task = form.save()
            except Membership.DoesNotExist:
                raise HouseholdRequired()
            except IntegrityError:
                if not Task.objects.filter(workspace=form.cleaned_data["workspace"],
                                           title=form.cleaned_data["title"]).exists():
                    raise
                form.add_error("title", "A task with this title already exists in this household.")
            else:
                messages.success(request, f'Task “{task.title}” created.')
                # POST/Redirect/GET prevents accidental repeat submissions.
                return redirect("task_forms:board")
        self.object_list = self.get_queryset()
        return self.render_to_response(self.get_context_data(create_form=form))
