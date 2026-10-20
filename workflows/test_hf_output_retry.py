"""Malformed local output may be regenerated once, never silently repaired."""
import json
from unittest.mock import patch

from django.test import SimpleTestCase

from workflows.services.brain_dump import BrainDumpError
from workflows.services.hf_local import extract_tasks


class LocalOutputRetryTests(SimpleTestCase):
    def setUp(self):
        self.valid = json.dumps({"tasks": [
            {"title": "Wash dishes", "task_type": "CHORE", "priority": "MEDIUM",
             "description": "Wash the dirty dishes."},
            {"title": "Clean fridge", "task_type": "CHORE", "priority": "MEDIUM",
             "description": "Clean and organize the fridge."},
        ]})

    def test_duplicate_root_keys_trigger_one_fresh_generation(self):
        invalid = '{"tasks": [], "tasks": []}'
        with patch("workflows.services.hf_local._generate_raw", side_effect=[invalid, self.valid]) as generate:
            result = extract_tasks("Dishes are dirty and fridge is messy")
        self.assertEqual(len(result["tasks"]), 2)
        self.assertEqual(generate.call_count, 2)
        retry_prompt = generate.call_args_list[1].args[0]
        self.assertIn('single "tasks" key', retry_prompt)
        self.assertIn("Dishes are dirty and fridge is messy", retry_prompt)
        self.assertNotIn(invalid, retry_prompt)

    def test_a_second_invalid_response_is_rejected_without_more_retries(self):
        with patch("workflows.services.hf_local._generate_raw", return_value="not JSON") as generate:
            with self.assertRaises(BrainDumpError):
                extract_tasks("Wash dishes")
        self.assertEqual(generate.call_count, 2)

    def test_model_runtime_failure_is_not_retried(self):
        with patch("workflows.services.hf_local._generate_raw", side_effect=BrainDumpError("runtime failure")) as generate:
            with self.assertRaises(BrainDumpError):
                extract_tasks("Wash dishes")
        generate.assert_called_once()

    def test_valid_output_needs_only_one_generation(self):
        with patch("workflows.services.hf_local._generate_raw", return_value=self.valid) as generate:
            result = extract_tasks("Dishes are dirty and fridge is messy")
        generate.assert_called_once()
        self.assertEqual(result["raw"], self.valid)
