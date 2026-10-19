import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase, override_settings

from .action_plans import ActionPlanError, generate_action_plan


def valid_plan():
    return {
        "summary": "Prepare the guest room before the visit.",
        "steps": [
            {"title": "Check the room", "description": "List the cleaning and supply needs."},
            {"title": "Clean and restock", "description": "Wash sheets and set out fresh towels."},
        ],
        "supplies": ["Clean sheets", "Towels"],
        "cautions": ["Ask for help moving heavy furniture."],
    }


@override_settings(GROQ_API_KEY="test-key", GROQ_MODEL="openai/gpt-oss-20b")
class ActionPlanServiceTests(SimpleTestCase):
    def setUp(self):
        self.task = SimpleNamespace(title="Prepare guest room", description="Guests arrive Friday.",
                                    task_type="CHORE", priority="MEDIUM")
        self.response = Mock(status_code=200)
        self.response.json.return_value = {
            "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(valid_plan())}}]
        }
        self.patcher = patch("workflows.action_plans.requests.post", return_value=self.response)
        self.post = self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def assert_error(self, status, code):
        with self.assertRaises(ActionPlanError) as caught:
            generate_action_plan(self.task)
        self.assertEqual(caught.exception.status, status)
        self.assertEqual(caught.exception.code, code)
        self.assertNotIn("test-key", caught.exception.message)

    def test_uses_fixed_endpoint_bounded_request_and_only_task_fields(self):
        self.task.private_household_note = "must not be transmitted"
        result = generate_action_plan(self.task)
        self.assertEqual(result, valid_plan())
        args, kwargs = self.post.call_args
        self.assertEqual(args, ("https://api.groq.com/openai/v1/chat/completions",))
        self.assertEqual(kwargs["timeout"], (3.05, 30))
        self.assertFalse(kwargs["allow_redirects"])
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")
        payload = kwargs["json"]
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertEqual(json.loads(payload["messages"][1]["content"]), {
            "title": self.task.title, "description": self.task.description,
            "task_type": "CHORE", "priority": "MEDIUM",
        })
        self.assertNotIn("must not be transmitted", json.dumps(payload))

    @override_settings(GROQ_API_KEY="")
    def test_missing_key_is_actionable_and_does_not_call_provider(self):
        self.assert_error(503, "not_configured")
        self.post.assert_not_called()

    def test_oversized_or_invalid_task_never_reaches_provider(self):
        for field, bad in [("description", "x" * 4001), ("title", " "),
                           ("task_type", "invalid"), ("priority", "invalid")]:
            with self.subTest(field=field):
                original = getattr(self.task, field)
                setattr(self.task, field, bad)
                self.assert_error(400, "invalid_task")
                setattr(self.task, field, original)
        self.post.assert_not_called()

    def test_timeout_and_network_failure_hide_upstream_details(self):
        for error, status, code in [(requests.Timeout("test-key"), 504, "timeout"),
                                    (requests.ConnectionError("test-key"), 502, "unavailable")]:
            with self.subTest(code=code):
                self.post.side_effect = error
                self.assert_error(status, code)

    def test_upstream_status_mapping(self):
        for status, expected, code in [(401, 503, "provider_configuration"),
                                       (403, 503, "provider_configuration"),
                                       (429, 429, "rate_limited"),
                                       (500, 502, "unavailable"),
                                       (302, 502, "unavailable"),
                                       (400, 502, "unavailable")]:
            with self.subTest(status=status):
                self.response.status_code = status
                self.assert_error(expected, code)

    def test_bad_provider_envelope_or_non_json_is_rejected(self):
        for envelope in [{}, [], {"choices": []}, {"choices": [None]},
                         {"choices": [{"message": {"content": "not JSON"}, "finish_reason": "stop"}]}]:
            with self.subTest(envelope=envelope):
                self.response.json.return_value = envelope
                self.assert_error(502, "invalid_output")
        self.response.json.side_effect = ValueError("bad JSON")
        self.assert_error(502, "invalid_output")

    def test_truncation_and_refusal_are_not_displayed_as_plans(self):
        for finish, message in [("length", {"content": json.dumps(valid_plan())}),
                                ("stop", {"refusal": "Cannot comply", "content": None})]:
            self.response.json.return_value = {"choices": [{"finish_reason": finish, "message": message}]}
            self.assert_error(502, "invalid_output")

    def test_enforces_exact_fields_types_lengths_and_step_count(self):
        for field, value in [("summary", 7), ("summary", "x" * 601),
                             ("steps", []), ("steps", [valid_plan()["steps"][0]] * 11),
                             ("steps", [{"title": "Step", "description": "Do it", "url": "extra"}]),
                             ("supplies", "rope"), ("supplies", [4]),
                             ("cautions", ["x" * 401]), ("extra", "ignored?")]:
            with self.subTest(field=field, value=value):
                plan = valid_plan()
                plan[field] = value
                self.response.json.return_value["choices"][0]["message"]["content"] = json.dumps(plan)
                self.assert_error(502, "invalid_output")

    def test_duplicate_keys_and_extra_prose_are_rejected(self):
        for raw in ['{"summary":"one","summary":"two"}',
                    '```json\n' + json.dumps(valid_plan()) + '\n```',
                    json.dumps(valid_plan()) + "\nExtra instructions"]:
            self.response.json.return_value["choices"][0]["message"]["content"] = raw
            self.assert_error(502, "invalid_output")
