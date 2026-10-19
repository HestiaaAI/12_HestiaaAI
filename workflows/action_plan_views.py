"""Explicit, authenticated plan previews. Model output never writes to the DB."""
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from .action_plans import ActionPlanError, generate_action_plan
from .models import Task


def _member_task(user, pk):
    return get_object_or_404(
        Task.objects.filter(workspace__memberships__user=user,
                            workspace__memberships__is_active=True).select_related("workspace"),
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
    task = _member_task(request.user, pk)
    context = {"task": task, "plan": None, "error": None}
    status = 200
    if request.method == "POST":
        try:
            context["plan"] = _generate_for_user(request.user, task)
        except ActionPlanError as exc:
            context["error"] = exc.message
            status = exc.status
    return render(request, "tasks/action_plan.html", context, status=status)


@never_cache
@require_POST
def action_plan_api(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required."}, status=401)
    try:
        task = _member_task(request.user, pk)
    except Http404:
        return JsonResponse({"error": "Task not found."}, status=404)
    try:
        plan = _generate_for_user(request.user, task)
    except ActionPlanError as exc:
        return JsonResponse({"error": exc.message, "code": exc.code}, status=exc.status)
    return JsonResponse({"task_id": task.pk, "provider": "Groq",
                         "model": settings.GROQ_MODEL, "plan": plan})
