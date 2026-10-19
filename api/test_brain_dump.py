"""API tests for local Brain Dump extraction (model calls are mocked)."""

import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from workflows.services.brain_dump import BrainDumpError


class BrainDumpApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user = User.objects.create_user(username="braindump", password="pass-12345")

    def test_anonymous_gets_401(self):
        response = self.client.post(
            "/api/ai/brain-dump/",
            data=json.dumps({"text": "Buy milk"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_empty_text_400(self):
        self.client.login(username="braindump", password="pass-12345")
        response = self.client.post(
            "/api/ai/brain-dump/",
            data=json.dumps({"text": "  "}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    @patch("api.brain_dump.extract_tasks")
    def test_success_returns_drafts_not_saved(self, mock_extract):
        mock_extract.return_value = {
            "tasks": [
                {
                    "title": "Buy milk",
                    "task_type": "SHOPPING",
                    "priority": "MEDIUM",
                    "description": "2%",
                }
            ],
            "warnings": [],
            "model_id": "google/flan-t5-base",
            "raw": "{}",
        }
        self.client.login(username="braindump", password="pass-12345")
        response = self.client.post(
            "/api/ai/brain-dump/",
            data=json.dumps({"text": "We need milk and the sink is clogged."}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["saved"])
        self.assertEqual(payload["tasks"][0]["title"], "Buy milk")
        mock_extract.assert_called_once()

    @patch("api.brain_dump.extract_tasks")
    def test_model_error_422(self, mock_extract):
        mock_extract.side_effect = BrainDumpError("Model output is not valid JSON")
        self.client.login(username="braindump", password="pass-12345")
        response = self.client.post(
            "/api/ai/brain-dump/",
            data=json.dumps({"text": "fix the lawn"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("error", response.json())
