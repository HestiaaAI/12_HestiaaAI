from unittest.mock import patch

from django.test import SimpleTestCase

from workflows.services.ask_hestia import AskHestiaError, answer_question


class AskHestiaTests(SimpleTestCase):
    @patch("workflows.services.ask_hestia._generate")
    @patch("workflows.services.ask_hestia._retrieve")
    def test_service_contract_preserves_retrieved_sources(self, retrieve, generate):
        retrieve.return_value = [{"id": "fixed-guests-02", "text": "Put out two towels.",
                                  "paragraph_ids": ("guests-02",), "score": 0.8}]
        generate.return_value = "Put out two towels."
        result = answer_question("  How many towels?  ")
        generate.assert_called_once_with("How many towels?", retrieve.return_value)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["answer"], generate.return_value)
        self.assertEqual(result["sources"], retrieve.return_value)
        self.assertGreaterEqual(result["latency_seconds"], 0)

    @patch("workflows.services.ask_hestia._generate")
    @patch("workflows.services.ask_hestia._retrieve", return_value=[])
    def test_no_context_skips_generation(self, retrieve, generate):
        self.assertEqual(answer_question("Who won the tournament?")["status"], "no_context")
        generate.assert_not_called()

    @patch("workflows.services.ask_hestia._retrieve")
    def test_invalid_input_skips_retrieval(self, retrieve):
        for question in (None, "   ", "x" * 501):
            with self.subTest(question=question), self.assertRaises(AskHestiaError) as error:
                answer_question(question)
            self.assertEqual(error.exception.code, "invalid_question")
        retrieve.assert_not_called()

    @patch("workflows.services.ask_hestia._retrieve", side_effect=OSError("private path"))
    def test_model_error_is_safe_for_view(self, retrieve):
        with self.assertLogs("workflows.services.ask_hestia", level="ERROR"):
            with self.assertRaises(AskHestiaError) as error:
                answer_question("Where is the drill?")
        self.assertEqual(error.exception.code, "model_unavailable")
        self.assertNotIn("private path", str(error.exception))
