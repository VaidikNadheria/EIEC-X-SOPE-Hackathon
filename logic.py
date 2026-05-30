from __future__ import annotations

from typing import Any


BLEEDING_NONE = "none"
BLEEDING_BRIGHT = "bright red"
BLEEDING_DARK = "dark red or black-tarry"


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"yes", "true", "1"}
    return bool(value)


def _pain_level(answers: dict) -> int:
    try:
        return int(answers.get("pain_level", 0))
    except (TypeError, ValueError):
        return 0


def check_red_flags(answers: dict) -> dict:
    messages: list[str] = []
    urgent_messages: list[str] = []
    doctor_messages: list[str] = []

    bleeding = answers.get("rectal_bleeding", BLEEDING_NONE)
    duration = answers.get("symptom_duration", "less than 1 week")
    pain_level = _pain_level(answers)
    has_systemic_symptoms = _as_bool(answers.get("systemic_symptoms", False))
    has_bleeding = bleeding != BLEEDING_NONE

    if bleeding == BLEEDING_DARK:
        urgent_messages.append(
            "Dark red, black, or tarry stool can be a warning sign and needs urgent medical evaluation."
        )

    if has_systemic_symptoms:
        urgent_messages.append(
            "Fever, vomiting, constant abdominal pain, or unexplained weight loss needs urgent medical evaluation."
        )

    if has_bleeding and pain_level >= 7:
        urgent_messages.append(
            "Bleeding with severe pain should be checked urgently by a healthcare professional."
        )

    if has_bleeding:
        doctor_messages.append(
            "Rectal bleeding should be discussed with a healthcare professional rather than assumed to be hemorrhoids."
        )

    if has_bleeding and duration in {"1-3 weeks", "more than 3 weeks"}:
        doctor_messages.append(
            "Bleeding lasting more than one week should be evaluated by a healthcare professional."
        )

    if duration == "more than 3 weeks":
        doctor_messages.append(
            "Symptoms lasting more than three weeks should be evaluated by a healthcare professional."
        )

    if urgent_messages:
        level = "urgent"
        messages.extend(urgent_messages)
        messages.extend(msg for msg in doctor_messages if msg not in messages)
    elif doctor_messages:
        level = "doctor"
        messages.extend(doctor_messages)
    else:
        level = "none"
        messages.append(
            "No selected red flags were detected. Continue monitoring and seek care if symptoms worsen or persist."
        )

    return {
        "has_red_flags": level != "none",
        "level": level,
        "messages": messages,
    }


def calculate_risk_score(answers: dict) -> dict:
    score = 0

    if answers.get("stool_type") == "hard/lumpy":
        score += 2
    if answers.get("bowel_movements_per_week") == "0-2":
        score += 2
    if answers.get("straining") == "often":
        score += 3
    if answers.get("toilet_time") == "more than 10 min":
        score += 2
    if answers.get("water_intake") == "less than 4 cups":
        score += 1
    if answers.get("fiber_intake") == "low":
        score += 2
    if answers.get("exercise_walking") == "none":
        score += 1
    if _as_bool(answers.get("sitting_long_hours", False)):
        score += 1

    if score <= 3:
        category = "Low"
    elif score <= 7:
        category = "Moderate"
    else:
        category = "High"

    explanation = (
        f"Your constipation and straining risk score is {score}, which falls in the {category.lower()} range. "
        "This reflects modifiable habits such as stool hardness, bowel frequency, straining, toilet time, "
        "hydration, fiber, movement, and long sitting."
    )

    return {
        "score": score,
        "category": category,
        "explanation": explanation,
    }


def get_top_factors(answers: dict) -> list[str]:
    factors: list[str] = []

    if answers.get("stool_type") == "hard/lumpy":
        factors.append("Hard or lumpy stools")
    if answers.get("bowel_movements_per_week") == "0-2":
        factors.append("Infrequent bowel movements")
    if answers.get("straining") == "often":
        factors.append("Frequent straining")
    elif answers.get("straining") == "sometimes":
        factors.append("Occasional straining")
    if answers.get("toilet_time") == "more than 10 min":
        factors.append("Long toilet sitting time")
    if answers.get("water_intake") == "less than 4 cups":
        factors.append("Low water intake")
    if answers.get("fiber_intake") == "low":
        factors.append("Low fiber intake")
    if answers.get("exercise_walking") == "none":
        factors.append("Limited walking or exercise")
    if _as_bool(answers.get("sitting_long_hours", False)):
        factors.append("Long periods of sitting")

    if not factors:
        return ["No major modifiable constipation or straining factors were selected."]

    return factors


def generate_rule_based_plan(answers: dict, factors: list[str]) -> list[str]:
    recommendations: list[str] = []

    def add(item: str) -> None:
        if item not in recommendations:
            recommendations.append(item)

    if answers.get("fiber_intake") in {"low", "medium"} or "Hard or lumpy stools" in factors:
        add(
            "Increase fiber gradually through fruits, vegetables, beans, lentils, oats, or whole grains."
        )
    if answers.get("water_intake") in {"less than 4 cups", "4-7 cups"}:
        add("Drink water throughout the day, especially as fiber intake increases.")
    if answers.get("straining") in {"sometimes", "often"}:
        add("Avoid straining; pause and try again later if a bowel movement is not happening easily.")
    if answers.get("toilet_time") in {"5-10 min", "more than 10 min"}:
        add("Reduce toilet sitting time and avoid using the phone on the toilet.")
    if answers.get("exercise_walking") in {"none", "some"}:
        add("Walk daily, especially after meals, to support regular bowel habits.")
    if _as_bool(answers.get("sitting_long_hours", False)):
        add("Take short standing or walking breaks during long sitting periods.")
    if _pain_level(answers) > 0 or _as_bool(answers.get("itching_burning", False)):
        add("Try a warm sitz bath for 10-15 minutes for comfort.")

    add("Keep a simple 7-day log of bowel movements, pain, bleeding, water, fiber, and walking.")
    add(
        "Seek medical care for bleeding, severe pain, black or tarry stool, fever, vomiting, unexplained weight loss, or persistent symptoms."
    )

    return recommendations[:8]
