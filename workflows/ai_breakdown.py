"""Optional Person 3 integration contract; no external provider implementation."""
from django.conf import settings
from django.utils.module_loading import import_string

from .ai_forms import MAX_DESCRIPTION


def suggest_steps(title, description):
    """Call a server-configured provider and return bounded plain-text steps."""
    path = getattr(settings, "HESTIA_TASK_BREAKDOWN_CALLABLE", "")
    if not path:
        raise ValueError("Task breakdown is not configured")
    result = import_string(path)(title, description)
    if not isinstance(result, dict) or result.get("error") is not None:
        raise ValueError("Invalid task breakdown")
    steps = result.get("steps")
    if not isinstance(steps, list) or not 1 <= len(steps) <= 10:
        raise ValueError("Expected one to ten steps")
    if any(not isinstance(step, str) or not step.strip() or len(step) > 500 for step in steps):
        raise ValueError("Invalid step text")
    updated = description.rstrip() + "\n\nSuggested steps:\n" + "\n".join(
        f"{index}. {step.strip()}" for index, step in enumerate(steps, 1))
    if len(updated) > MAX_DESCRIPTION:
        raise ValueError("Description would exceed the review limit")
    return updated.strip()
