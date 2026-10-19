"""Shared Brain Dump contract (aligned with ai_prototype.ipynb on main)."""

from __future__ import annotations

import json
import re
from typing import Any

from workflows.models import Task

TASK_TYPES = {choice.value for choice in Task.TaskType}
PRIORITIES = {choice.value for choice in Task.Priority}
REQUIRED_FIELDS = {"title", "task_type", "priority", "description"}
TITLE_MAX = 200

# Exact shared instruction from Person 1's notebook on main.
SYSTEM_INSTRUCTION = """You are Hestia's household task extraction assistant.
Convert the user's message into separate household tasks.
Return JSON only in this exact shape:
{"tasks":[{"title":"...","task_type":"CHORE|APPOINTMENT|DEADLINE|ERRAND|MAINTENANCE|SHOPPING|OTHER","priority":"LOW|MEDIUM|HIGH|URGENT","description":"..."}]}
Do not invent concerns that the user did not mention. Use URGENT only for an immediate safety risk or a deadline within 24 hours. Keep titles and descriptions concise."""

EXAMPLES = [
    {
        "input": "The trash is full and we are out of milk.",
        "output": {"tasks": [
            {"title": "Take out the trash", "task_type": "CHORE", "priority": "MEDIUM", "description": "Empty the full household trash bin."},
            {"title": "Buy milk", "task_type": "SHOPPING", "priority": "MEDIUM", "description": "Purchase milk for the household."},
        ]},
    },
    {
        "input": "The gas stove smells like gas, and the hallway light bulb needs replacing.",
        "output": {"tasks": [
            {"title": "Check gas leak", "task_type": "MAINTENANCE", "priority": "URGENT", "description": "Stop using the stove and arrange an immediate gas safety inspection."},
            {"title": "Replace hallway light bulb", "task_type": "MAINTENANCE", "priority": "LOW", "description": "Replace the burned-out hallway light bulb."},
        ]},
    },
    {
        "input": "The dog needs a vet appointment and the living room needs vacuuming.",
        "output": {"tasks": [
            {"title": "Book vet appointment", "task_type": "APPOINTMENT", "priority": "MEDIUM", "description": "Schedule a veterinary appointment for the dog."},
            {"title": "Vacuum living room", "task_type": "CHORE", "priority": "LOW", "description": "Vacuum the living-room floor."},
        ]},
    },
]

# Back-compat aliases used by older helpers/tests.
INSTRUCTION = SYSTEM_INSTRUCTION
ONE_SHOT_EXAMPLES = ""  # built via shot_mode instead
FEW_SHOT_EXAMPLES = ""
MANY_SHOT_EXAMPLES = ""


class BrainDumpError(ValueError):
    """Raised when the model output cannot be turned into task drafts."""


def build_user_prompt(text: str, shot_mode: str = "few") -> str:
    """Match Person 1 notebook prompt builder."""
    shot_counts = {"zero": 0, "one": 1, "few": 2, "many": 3}
    if shot_mode not in shot_counts:
        raise BrainDumpError(f"Unknown shot mode: {shot_mode}")
    cleaned = (text or "").strip()
    if not cleaned:
        raise BrainDumpError("Brain dump text is empty.")
    examples = EXAMPLES[: shot_counts[shot_mode]]
    example_text = "\n\n".join(
        f"Example input: {item['input']}\nExample output: {json.dumps(item['output'])}"
        for item in examples
    )
    prefix = f"{example_text}\n\n" if example_text else ""
    return f"{prefix}Household message: {cleaned}\nJSON output:"


def build_prompt(brain_dump: str, *, examples: str = "", shot_mode: str = "few") -> str:
    """Build the user-side prompt. `examples` is ignored; use shot_mode."""
    del examples  # shared examples come from EXAMPLES + shot_mode
    return build_user_prompt(brain_dump, shot_mode=shot_mode)


def extract_json(text: str) -> Any:
    """Extract the first complete JSON object (Person 1 notebook logic)."""

    def reject_duplicate_keys(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"Duplicate JSON key: {key}")
            value[key] = item
        return value

    decoder = json.JSONDecoder(object_pairs_hook=reject_duplicate_keys)
    for match in re.finditer(r"\{", text):
        try:
            value, _ = decoder.raw_decode(text[match.start() :])
            return value
        except json.JSONDecodeError:
            continue
    raise ValueError("No valid JSON object found")


def validate_payload(payload: Any) -> list[str]:
    """Schema check matching the notebook (strict empty description)."""
    errors = []
    if not isinstance(payload, dict) or not isinstance(payload.get("tasks"), list):
        return ["Root must be an object containing a tasks list"]
    if not payload["tasks"]:
        errors.append("tasks must not be empty")
    for index, task in enumerate(payload["tasks"], start=1):
        if not isinstance(task, dict):
            errors.append(f"Task {index} is not an object")
            continue
        missing = REQUIRED_FIELDS - task.keys()
        if missing:
            errors.append(f"Task {index} missing: {sorted(missing)}")
        if task.get("task_type") not in TASK_TYPES:
            errors.append(f"Task {index} has invalid task_type")
        if task.get("priority") not in PRIORITIES:
            errors.append(f"Task {index} has invalid priority")
        if not str(task.get("title", "")).strip():
            errors.append(f"Task {index} has an empty title")
        if not str(task.get("description", "")).strip():
            errors.append(f"Task {index} has an empty description")
    return errors


def validate_task_draft(raw: Any) -> tuple[dict[str, str], list[str]]:
    """Normalize one task for Django drafts (coerce unknown enums)."""
    if not isinstance(raw, dict):
        raise BrainDumpError("Each task must be a JSON object.")
    title = str(raw.get("title") or "").strip()
    if not title:
        raise BrainDumpError("Task title is required.")
    if len(title) > TITLE_MAX:
        title = title[:TITLE_MAX]
    description = str(raw.get("description") or "").strip()
    warnings: list[str] = []
    task_type = str(raw.get("task_type") or "").strip().upper().replace(" ", "_")
    if task_type not in TASK_TYPES:
        warnings.append(f"unknown task_type {raw.get('task_type')!r}; defaulted to OTHER")
        task_type = Task.TaskType.OTHER
    priority = str(raw.get("priority") or "").strip().upper().replace(" ", "_")
    if priority not in PRIORITIES:
        warnings.append(f"unknown priority {raw.get('priority')!r}; defaulted to MEDIUM")
        priority = Task.Priority.MEDIUM
    return {
        "title": title,
        "task_type": task_type,
        "priority": priority,
        "description": description,
    }, warnings


def parse_tasks_payload(raw_text: str) -> tuple[list[dict[str, str]], list[str]]:
    """Parse model text into validated task drafts plus warnings."""
    text = (raw_text or "").strip()
    if not text:
        raise BrainDumpError("Model returned empty output.")
    try:
        payload = extract_json(text)
    except ValueError as exc:
        raise BrainDumpError(f"Model output is not valid JSON: {exc}") from exc

    schema_errors = validate_payload(payload)
    warnings = list(schema_errors)

    items = payload.get("tasks") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        raise BrainDumpError('JSON must be {"tasks": [...]}')

    drafts: list[dict[str, str]] = []
    for index, item in enumerate(items):
        try:
            draft, item_warnings = validate_task_draft(item)
        except BrainDumpError as exc:
            warnings.append(f"skipped task[{index}]: {exc}")
            continue
        # Notebook rejects empty description; for Django drafts allow blank after warn.
        if not draft["description"]:
            warnings.append(f"task[{index}]: empty description")
        drafts.append(draft)
        warnings.extend(f"task[{index}]: {w}" for w in item_warnings)

    if not drafts:
        raise BrainDumpError(
            "No valid tasks could be parsed from model output."
            + ((" " + " | ".join(schema_errors)) if schema_errors else "")
        )
    return drafts, warnings
