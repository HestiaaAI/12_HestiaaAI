"""Person 4's temporary adapter; Person 2 owns ai_service and inference."""
from django.conf import settings

from .ai_forms import MAX_TASKS, ReviewTaskForm


class SuggestionsUnavailable(Exception):
    pass


def get_suggestions(text):
    mode = getattr(settings, "HESTIA_BRAIN_DUMP_BACKEND", "mock")
    if mode == "mock":
        result = {"tasks": [
            {"title": "Clean the kitchen", "task_type": "CHORE", "priority": "HIGH",
             "description": "Clean and organize the kitchen before guests arrive."},
            {"title": "Buy groceries", "task_type": "SHOPPING", "priority": "HIGH",
             "description": "Purchase groceries needed before the guests arrive."},
            {"title": "Repair bathroom tap", "task_type": "MAINTENANCE", "priority": "URGENT",
             "description": "Repair the leaking bathroom tap."},
        ], "error": None}
    elif mode == "local":
        # Lazy import: missing inference dependencies cannot break the rest of Hestia.
        from .ai_service import analyze_brain_dump
        result = analyze_brain_dump(text)
    else:
        raise SuggestionsUnavailable()
    return validate_suggestions(result)


def validate_suggestions(result):
    if not isinstance(result, dict) or result.get("error") is not None:
        raise SuggestionsUnavailable()
    tasks = result.get("tasks")
    if not isinstance(tasks, list) or len(tasks) > MAX_TASKS:
        raise SuggestionsUnavailable()
    validated = []
    for task in tasks:
        keys = ("title", "task_type", "priority", "description")
        if not isinstance(task, dict) or any(not isinstance(task.get(key), str) for key in keys):
            raise SuggestionsUnavailable()
        # This form validates the actual model enums and title length, plus our
        # UI description cap. Unknown/protected keys are never passed through.
        form = ReviewTaskForm({key: task[key] for key in keys})
        if not form.is_valid():
            raise SuggestionsUnavailable()
        validated.append({key: form.cleaned_data[key] for key in keys})
    return validated
