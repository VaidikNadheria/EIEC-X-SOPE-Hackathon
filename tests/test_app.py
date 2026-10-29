import datetime
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[1] / "app.py"


class AppFlowTests(unittest.TestCase):
    def setUp(self):
        # Force offline execution even if the developer has configured local secrets.
        key_patch = patch("ai_client._get_gemini_api_key", return_value="")
        key_patch.start()
        self.addCleanup(key_patch.stop)
        self.app = AppTest.from_file(str(APP), default_timeout=20).run()
        self.assertFalse(self.app.exception)

    def navigate(self, suffix):
        nav = self.app.sidebar.radio[0]
        value = next(option for option in nav.options if option.endswith(suffix))
        nav.set_value(value).run()
        self.assertFalse(self.app.exception)

    def test_assessment_and_assistant_work_without_a_key(self):
        self.navigate("Self-Care Check")
        self.app.button[0].click().run()
        self.assertFalse(self.app.exception)
        result = self.app.session_state["assessment_result"]
        self.assertEqual(result["red_flags"]["level"], "none")
        self.assertIn("Safety note", result["ai_summary"])
        headings = {heading.value for heading in self.app.subheader}
        self.assertTrue({"Safety Status", "Risk Score", "Main Contributing Factors", "Self-Care Plan", "AI Summary", "Doctor Summary"}.issubset(headings))
        self.navigate("AI Assistant")
        self.assertTrue(any("fallback" in warning.value for warning in self.app.warning))

    def test_dark_bleeding_renders_urgent_status_and_doctor_summary(self):
        self.navigate("Self-Care Check")
        self.app.selectbox[0].set_value("dark red or black-tarry")
        self.app.button[0].click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state["assessment_result"]["red_flags"]["level"], "urgent")
        self.assertTrue(any("Urgent" in error.value for error in self.app.error))
        self.assertTrue(any("Safety status: urgent" in area.value for area in self.app.text_area))

    def test_repeated_daily_save_replaces_fiber_total(self):
        self.navigate("Symptom Tracker")
        for _ in range(2):
            button = next(button for button in self.app.button if button.label == "Save Entry")
            button.click().run()
            self.assertFalse(self.app.exception)
        fiber = self.app.session_state["fiber_log"]
        today = fiber[fiber["Date"] == datetime.date.today()]
        self.assertEqual(len(today), 1)
        self.assertEqual(float(today.iloc[0]["Total_Fiber_g"]), 18.0)


if __name__ == "__main__":
    unittest.main()
