"""Ask Hestia's signed-in, read-only page."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from workflows.services.ask_hestia import AskHestiaError, UNKNOWN


class AskHestiaPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="ask-member")

    def setUp(self):
        self.url = reverse("ask-hestia")
        self.client.force_login(self.user)

    def test_get_and_navigation(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Ask Hestia")
        self.assertContains(response, 'name="question"')
        self.assertContains(response, self.url)

    def test_auth_and_method(self):
        self.assertEqual(self.client.put(self.url).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.assertEqual(self.client.post(self.url, {"question": "Where is the drill?"}).status_code, 302)

    @patch("workflows.ask_hestia_views.answer_question")
    def test_invalid_questions_never_call_model(self, answer):
        for question in (" \n ", "x" * 501):
            with self.subTest(question=question[:20]):
                response = self.client.post(self.url, {"question": question})
                self.assertContains(response, "question", status_code=200)
                self.assertTrue(response.context["form"].errors)
        answer.assert_not_called()

    @patch("workflows.ask_hestia_views.answer_question")
    def test_answer_sources_timing_and_escaping(self, answer):
        answer.return_value = {
            "status": "ok", "answer": "The drill is in the blue bin.",
            "sources": [{"id": "fixed-inventory-01", "document": "inventory.md",
                         "section": "Borrowing tools", "text": "<script>alert(1)</script> Blue bin.",
                         "score": 0.82}], "latency_seconds": 1.234,
        }
        response = self.client.post(self.url, {"question": "  Where is the drill?  "})
        answer.assert_called_once_with("Where is the drill?")
        self.assertContains(response, "The drill is in the blue bin.")
        self.assertContains(response, "fixed-inventory-01")
        self.assertContains(response, "1.234")
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")
        self.assertNotContains(response, "<script>alert(1)</script>")

    @patch("workflows.ask_hestia_views.answer_question")
    def test_abstentions(self, answer):
        for status in ("no_context", "insufficient_context"):
            with self.subTest(status=status):
                answer.return_value = {"status": status, "answer": UNKNOWN,
                                       "sources": [], "latency_seconds": 0.2}
                response = self.client.post(self.url, {"question": "Who won the game?"})
                self.assertContains(response, "I couldn&#x27;t find an answer in the household handbook.")
                self.assertContains(response, "could not find enough support")

    @patch("workflows.ask_hestia_views.answer_question")
    def test_service_and_unexpected_errors_are_safe(self, answer):
        for failure in (
            AskHestiaError("invalid_question", "Shorten your question and try again."),
            AskHestiaError("model_unavailable", "Ask Hestia is temporarily unavailable."),
            AskHestiaError("empty_answer", "The model returned an empty answer. Try again."),
            AskHestiaError("incomplete_answer", "The model did not finish its answer. Try a shorter question."),
            RuntimeError("private path or token"),
        ):
            with self.subTest(failure=failure):
                answer.side_effect = failure
                if isinstance(failure, RuntimeError):
                    with self.assertLogs("workflows.ask_hestia_views", level="ERROR"):
                        response = self.client.post(self.url, {"question": "Where is the drill?"})
                else:
                    response = self.client.post(self.url, {"question": "Where is the drill?"})
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Where is the drill?")
                self.assertContains(response, str(failure) if isinstance(failure, AskHestiaError)
                                    else "Ask Hestia is temporarily unavailable. Try again later.")
                self.assertNotContains(response, "private path or token")

    def test_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertContains(client.get(self.url), "csrfmiddlewaretoken")
        self.assertEqual(client.post(self.url, {"question": "Where is the drill?"}).status_code, 403)
