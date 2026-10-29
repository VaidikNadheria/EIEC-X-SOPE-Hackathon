import copy
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import ai_client


class GeminiSummaryTests(unittest.TestCase):
    def setUp(self):
        self.args = (
            {"rectal_bleeding": "bright red"},
            {"level": "doctor", "has_red_flags": True, "messages": ["Contact a clinician."]},
            {"score": 8, "category": "High"},
            ["Frequent straining"],
            ["Avoid straining.", "Seek medical care for bleeding."],
        )

    def test_secrets_take_precedence_over_environment(self):
        with patch.object(ai_client.st, "secrets", {"GEMINI_API_KEY": "secrets-placeholder"}):
            with patch.dict(os.environ, {"GEMINI_API_KEY": "environment-placeholder"}):
                self.assertEqual(ai_client._get_gemini_api_key(), "secrets-placeholder")

    def test_environment_fallback_when_secrets_missing(self):
        with patch.object(ai_client.st, "secrets", {}):
            with patch.dict(os.environ, {"GEMINI_API_KEY": "environment-placeholder"}):
                self.assertEqual(ai_client._get_gemini_api_key(), "environment-placeholder")

    def test_no_key_does_not_create_a_client(self):
        with patch.object(ai_client, "_get_gemini_api_key", return_value=""):
            with patch("google.genai.Client") as client:
                summary = ai_client.generate_ai_summary(*self.args)
                client.assert_not_called()
        self.assertIn("healthcare professional", summary)
        self.assertIn("8 (High)", summary)
        for heading in ["Safety note", "What habits may be contributing", "7-day focus", "When to seek medical care"]:
            self.assertIn(heading, summary)

    def test_api_failure_returns_fallback_without_error_details(self):
        with patch.object(ai_client, "_get_gemini_api_key", return_value="unit-test-placeholder"):
            with patch("google.genai.Client", side_effect=RuntimeError("private-error-detail")):
                summary = ai_client.generate_ai_summary(*self.args)
        self.assertIn("Safety note", summary)
        self.assertNotIn("private-error-detail", summary)

    def test_empty_api_response_uses_fallback(self):
        with patch.object(ai_client, "_get_gemini_api_key", return_value="unit-test-placeholder"):
            with patch("google.genai.Client") as client:
                client.return_value.models.generate_content.return_value = SimpleNamespace(text="")
                summary = ai_client.generate_ai_summary(*self.args)
        self.assertIn("8 (High)", summary)

    def test_success_uses_model_and_guardrails_without_mutating_rules(self):
        original = copy.deepcopy(self.args)
        with patch.object(ai_client, "_get_gemini_api_key", return_value="unit-test-placeholder"):
            with patch("google.genai.Client") as client:
                generate = client.return_value.models.generate_content
                generate.return_value = SimpleNamespace(text="Patient-friendly explanation")
                summary = ai_client.generate_ai_summary(*self.args)
        self.assertEqual(summary, "Patient-friendly explanation")
        self.assertEqual(self.args, original)
        self.assertEqual(generate.call_args.kwargs["model"], ai_client.GEMINI_MODEL)
        prompt = generate.call_args.kwargs["contents"]
        self.assertIn(ai_client.SAFETY_INSTRUCTION, prompt)
        self.assertIn('"level": "doctor"', prompt)
        self.assertIn("do not recommend prescription medications", prompt)

    def test_urgent_fallback_preserves_urgent_advice(self):
        args = list(self.args)
        args[1] = {"level": "urgent", "messages": ["Urgent evaluation needed."]}
        with patch.object(ai_client, "_get_gemini_api_key", return_value=""):
            summary = ai_client.generate_ai_summary(*args)
        self.assertIn("Urgent medical evaluation", summary)


if __name__ == "__main__":
    unittest.main()
