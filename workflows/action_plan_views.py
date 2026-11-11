"""Explicit, authenticated plan previews. Model output never writes to the DB."""
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .action_plans import ActionPlanError, generate_action_plan
from .models import Task
from households.context import require_household, fresh_household


def _member_task(request, pk):
    return get_object_or_404(
        Task.objects.filter(workspace=require_household(request).workspace).select_related("workspace"),
        pk=pk,
    )


def _generate_for_user(user, task):
    # LocMemCache limits accidental repeats per worker; shared production caches
    # can enforce this across workers. Never cache task content or provider output.
    if settings.GROQ_API_KEY.strip() and not cache.add(f"groq-plan:{user.pk}", True, timeout=15):
        raise ActionPlanError("Please wait 15 seconds before generating another plan.",
                              429, "cooldown")
    return generate_action_plan(task)


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def action_plan_page(request, pk):
    task = _member_task(request, pk)
    context = {"task": task, "plan": None, "error": None}
    status = 200
    if request.method == "POST":
        fresh_household(request)
        try:
            context["plan"] = _generate_for_user(request.user, task)
        except ActionPlanError as exc:
            context["error"] = exc.message
            status = exc.status
    return render(request, "tasks/action_plan.html", context, status=status)
