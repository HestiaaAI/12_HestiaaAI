"""Generate, review, and explicitly confirm tasks without automatic writes."""
import secrets

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from households.models import Membership
from .ai_adapter import get_suggestions
from .ai_forms import BrainDumpForm, ConfirmationForm, TaskReviewFormSet

SALT = "workflows.brain-dump-review"
DRAFT_KEY = "brain_dump_draft"


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def brain_dump(request):
    context = {"input_form": BrainDumpForm(user=request.user),
               "mock_mode": getattr(settings, "HESTIA_BRAIN_DUMP_BACKEND", "mock") == "mock"}
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "generate":
            form = BrainDumpForm(request.POST, user=request.user)
            context["input_form"] = form
            if form.is_valid():
                try:
                    tasks = get_suggestions(form.cleaned_data["text"])
                except Exception:
                    # Never expose provider exceptions, credentials, or raw output.
                    context["error"] = "Suggestions are unavailable or invalid. Please try again later. You can still use the Task board."
                else:
                    if not tasks:
                        context["error"] = "No tasks were suggested. Try describing the responsibilities more clearly."
                    else:
                        workspace = form.cleaned_data["workspace"]
                        draft = {"user": request.user.pk, "workspace": workspace.pk,
                                 "count": len(tasks), "nonce": secrets.token_hex(16)}
                        token = signing.dumps(draft, salt=SALT)
                        request.session[DRAFT_KEY] = draft
                        context.update(review=TaskReviewFormSet(initial=tasks, workspace=workspace),
                                       confirmation=ConfirmationForm(), draft_token=token, workspace=workspace)
        elif action == "save":
            token = request.POST.get("draft_token", "")
            try:
                draft = signing.loads(token, salt=SALT, max_age=3600)
                if draft != request.session.get(DRAFT_KEY) or draft["user"] != request.user.pk:
                    raise signing.BadSignature()
                membership = Membership.objects.select_related("workspace").get(
                    user=request.user, workspace_id=draft["workspace"], is_active=True)
            except (signing.BadSignature, KeyError, Membership.DoesNotExist):
                context["error"] = "This review expired or household access changed. Please organize your tasks again."
            else:
                review = TaskReviewFormSet(request.POST, workspace=membership.workspace)
                confirmation = ConfirmationForm(request.POST)
                context.update(review=review, confirmation=confirmation, draft_token=token,
                               workspace=membership.workspace)
                valid = review.is_valid()
                confirmed = confirmation.is_valid()
                if review.total_form_count() != draft["count"]:
                    context["error"] = "The review changed unexpectedly. Please organize your tasks again."
                elif valid and confirmed:
                    try:
                        with transaction.atomic():
                            # Recheck membership inside the save transaction.
                            Membership.objects.select_for_update().get(
                                pk=membership.pk, user=request.user,
                                workspace_id=draft["workspace"], is_active=True)
                            count = 0
                            for form in review.forms:
                                if form.cleaned_data.get("DELETE"):
                                    continue
                                form.instance.workspace = membership.workspace
                                form.instance.created_by_membership = membership
                                form.save()
                                count += 1
                    except (IntegrityError, Membership.DoesNotExist):
                        context["error"] = "Tasks could not be saved because a title or household access changed. Nothing was saved. Please review or start again."
                    else:
                        request.session.pop(DRAFT_KEY, None)
                        messages.success(request, f"Saved {count} approved task(s) to {membership.workspace.name}.")
                        return redirect("ai_tasks:brain-dump")
        else:
            context["error"] = "Choose Organize My Tasks or confirm your reviewed tasks."
    context["has_workspaces"] = context["input_form"].fields["workspace"].queryset.exists()
    return render(request, "tasks/ai_brain_dump.html", context)
