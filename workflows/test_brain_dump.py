"""Unit tests for Brain Dump JSON parsing (no model download required)."""

import json

from django.test import SimpleTestCase

from workflows.services.brain_dump import (
    BrainDumpError,
    SYSTEM_INSTRUCTION,
    build_user_prompt,
    parse_tasks_payload,
    validate_payload,
    validate_task_draft,
)


class BrainDumpParseTests(SimpleTestCase):
    def test_shared_instruction_mentions_json_shape(self):
        self.assertIn('"tasks"', SYSTEM_INSTRUCTION)
        self.assertIn("SHOPPING", SYSTEM_INSTRUCTION)

    def test_build_user_prompt_rejects_empty(self):
        with self.assertRaises(BrainDumpError):
            build_user_prompt("   ")

    def test_few_shot_includes_examples_and_household_message(self):
        prompt = build_user_prompt("Need milk.", shot_mode="few")
        self.assertIn("Example input:", prompt)
        self.assertIn("Household message: Need milk.", prompt)
        self.assertIn("JSON output:", prompt)

    def test_zero_shot_has_no_examples(self):
        prompt = build_user_prompt("Need milk.", shot_mode="zero")
        self.assertNotIn("Example input:", prompt)

    def test_parse_valid_object(self):
        raw = json.dumps({
            "tasks": [{
                "title": "Buy dish soap",
                "task_type": "SHOPPING",
                "priority": "HIGH",
                "description": "Kitchen is out.",
            }]
        })
        tasks, warnings = parse_tasks_payload(raw)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["title"], "Buy dish soap")
        self.assertEqual(tasks[0]["task_type"], "SHOPPING")
        self.assertEqual(warnings, [])

    def test_parse_strips_leading_prose(self):
        payload = {
            "tasks": [{
                "title": "Call plumber",
                "task_type": "MAINTENANCE",
                "priority": "URGENT",
                "description": "Leak under sink.",
            }]
        }
        raw = "Sure.\n" + json.dumps(payload)
        tasks, _ = parse_tasks_payload(raw)
        self.assertEqual(tasks[0]["title"], "Call plumber")

    def test_validate_payload_rejects_empty_description(self):
        errors = validate_payload({
            "tasks": [{
                "title": "X",
                "task_type": "CHORE",
                "priority": "LOW",
                "description": "",
            }]
        })
        self.assertTrue(any("empty description" in e for e in errors))

    def test_unknown_enums_coerced_in_draft(self):
        draft, warnings = validate_task_draft({
            "title": "Something odd",
            "task_type": "not-a-type",
            "priority": "super",
            "description": "ok",
        })
        self.assertEqual(draft["task_type"], "OTHER")
        self.assertEqual(draft["priority"], "MEDIUM")
        self.assertEqual(len(warnings), 2)

    def test_invalid_json_raises(self):
        with self.assertRaises(BrainDumpError):
            parse_tasks_payload("not json at all")
