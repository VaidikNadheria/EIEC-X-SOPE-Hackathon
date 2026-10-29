import itertools
import unittest

from logic import (
    calculate_risk_score,
    check_red_flags,
    generate_rule_based_plan,
    get_top_factors,
)


BASE_ANSWERS = {
    "rectal_bleeding": "none",
    "pain_level": 0,
    "itching_burning": False,
    "swelling_lump": False,
    "symptom_duration": "less than 1 week",
    "systemic_symptoms": False,
    "bowel_movements_per_week": "daily",
    "stool_type": "normal",
    "straining": "never",
    "toilet_time": "less than 5 min",
    "water_intake": "8+ cups",
    "fiber_intake": "high",
    "sitting_long_hours": False,
    "exercise_walking": "daily",
}

# The hackathon rubric is an educational heuristic, not a validated clinical score.
RISK_FACTORS = [
    ("stool_type", "hard/lumpy", 2),
    ("bowel_movements_per_week", "0-2", 2),
    ("straining", "often", 3),
    ("toilet_time", "more than 10 min", 2),
    ("water_intake", "less than 4 cups", 1),
    ("fiber_intake", "low", 2),
    ("exercise_walking", "none", 1),
    ("sitting_long_hours", True, 1),
]


class RedFlagTests(unittest.TestCase):
    def test_required_escalation_rules(self):
        cases = [
            ({}, "none"),
            ({"rectal_bleeding": "bright red"}, "doctor"),
            ({"rectal_bleeding": "dark red or black-tarry"}, "urgent"),
            ({"systemic_symptoms": True}, "urgent"),
            ({"rectal_bleeding": "bright red", "pain_level": 6}, "doctor"),
            ({"rectal_bleeding": "bright red", "pain_level": 7}, "urgent"),
            ({"rectal_bleeding": "bright red", "symptom_duration": "1-3 weeks"}, "doctor"),
            ({"symptom_duration": "more than 3 weeks"}, "doctor"),
        ]
        for changes, level in cases:
            with self.subTest(changes=changes):
                result = check_red_flags({**BASE_ANSWERS, **changes})
                self.assertEqual(result["level"], level)
                self.assertEqual(result["has_red_flags"], level != "none")
                self.assertTrue(result["messages"])

    def test_urgent_wins_over_multiple_doctor_rules(self):
        result = check_red_flags({
            **BASE_ANSWERS,
            "rectal_bleeding": "bright red",
            "systemic_symptoms": True,
            "symptom_duration": "more than 3 weeks",
        })
        self.assertEqual(result["level"], "urgent")
        self.assertGreater(len(result["messages"]), 1)

    def test_string_boolean_does_not_make_no_truthy(self):
        for value, expected in [("No", "none"), ("Yes", "urgent")]:
            with self.subTest(value=value):
                result = check_red_flags({**BASE_ANSWERS, "systemic_symptoms": value})
                self.assertEqual(result["level"], expected)

    def test_persistent_bleeding_has_duration_message(self):
        result = check_red_flags({
            **BASE_ANSWERS, "rectal_bleeding": "bright red", "symptom_duration": "1-3 weeks"
        })
        self.assertTrue(any("one week" in message for message in result["messages"]))


class RiskAndPlanTests(unittest.TestCase):
    def test_all_256_combinations_of_risk_factors(self):
        for selected in itertools.product([False, True], repeat=len(RISK_FACTORS)):
            answers = BASE_ANSWERS.copy()
            expected = 0
            for enabled, (key, value, points) in zip(selected, RISK_FACTORS):
                if enabled:
                    answers[key] = value
                    expected += points
            with self.subTest(selected=selected):
                result = calculate_risk_score(answers)
                self.assertEqual(result["score"], expected)
                category = "Low" if expected <= 3 else "Moderate" if expected <= 7 else "High"
                self.assertEqual(result["category"], category)

    def test_factors_match_selected_habits(self):
        factors = get_top_factors({**BASE_ANSWERS, "straining": "often", "fiber_intake": "low"})
        self.assertEqual(factors, ["Frequent straining", "Low fiber intake"])

    def test_long_plan_preserves_medical_care_reminder(self):
        answers = {**BASE_ANSWERS, **{key: value for key, value, _ in RISK_FACTORS}, "pain_level": 4}
        plan = generate_rule_based_plan(answers, get_top_factors(answers))
        self.assertLessEqual(len(plan), 8)
        self.assertEqual(len(plan), len(set(plan)))
        self.assertIn("Seek medical care", plan[-1])
        self.assertTrue(any("7-day log" in item for item in plan))

    def test_plan_personalizes_fiber_and_straining(self):
        answers = {**BASE_ANSWERS, "fiber_intake": "low", "straining": "often"}
        plan = generate_rule_based_plan(answers, get_top_factors(answers))
        self.assertTrue(any("Increase fiber gradually" in item for item in plan))
        self.assertTrue(any("Avoid straining" in item for item in plan))


if __name__ == "__main__":
    unittest.main()
