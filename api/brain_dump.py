"""A6 Person 2: local HF Brain Dump → structured task drafts (JSON API)."""

from __future__ import annotations

from django.http import JsonResponse
from django.views.decorators.http import require_POST

from workflows.services.brain_dump import BrainDumpError
from workflows.services.hf_local import extract_tasks

# Guardrail: keep prompts bounded for local CPU inference.
MAX_BRAIN_DUMP_CHARS = 4000


@require_POST
def brain_dump_extract(request):
    """
    POST JSON {"text": "..."} or form field text=...

    Returns validated task drafts. Does not save Tasks — Person 4 confirms first.
    """
    if request.content_type and "application/json" in request.content_type:
        try:
            import json

            body = json.loads(request.body.decode("utf-8") or "{}")
        except ValueError:
            return JsonResponse({"error": "Request body must be JSON."}, status=400)
        text = str(body.get("text") or "")
    else:
        text = str(request.POST.get("text") or "")

    text = text.strip()
    if not text:
        return JsonResponse({"error": "Brain dump text is required."}, status=400)
    if len(text) > MAX_BRAIN_DUMP_CHARS:
        return JsonResponse(
            {
                "error": f"Brain dump exceeds {MAX_BRAIN_DUMP_CHARS} characters.",
                "max_chars": MAX_BRAIN_DUMP_CHARS,
            },
            status=400,
        )

    try:
        result = extract_tasks(text)
    except BrainDumpError as exc:
        return JsonResponse({"error": str(exc)}, status=422)
    except Exception as exc:  # noqa: BLE001
        return JsonResponse(
            {"error": f"Unexpected Brain Dump failure: {exc}"},
            status=500,
        )

    return JsonResponse(
        {
            "tasks": result["tasks"],
            "warnings": result["warnings"],
            "model_id": result["model_id"],
            "saved": False,
            "message": "Review and confirm before saving through the Task module.",
        }
    )
