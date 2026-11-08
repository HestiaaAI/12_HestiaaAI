"""Signed-in page for asking questions about the bundled household handbook."""

import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from workflows.ask_hestia_forms import AskHestiaForm
from workflows.services.ask_hestia import AskHestiaError, answer_question


logger = logging.getLogger(__name__)


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def ask_hestia_page(request):
    form = AskHestiaForm(request.POST if request.method == "POST" else None)
    context = {"form": form}
    if request.method == "POST" and form.is_valid():
        try:
            result = answer_question(form.cleaned_data["question"])
        except AskHestiaError as exc:
            context["error"] = str(exc)
        except Exception:
            logger.exception("Unexpected Ask Hestia page failure")
            context["error"] = "Ask Hestia is temporarily unavailable. Try again later."
        else:
            context["result"] = result
    return render(request, "tasks/ask_hestia.html", context)
