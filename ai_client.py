from __future__ import annotations

import json
import os
from typing import Any

import streamlit as st


GEMINI_MODEL = "gemini-2.5-flash"

SAFETY_INSTRUCTION = (
    "You are not a doctor. Do not diagnose. Give educational self-care guidance only. "
    "Always recommend professional care for red flags. Do not override the rule-based safety result."
)


def _get_gemini_api_key() -> str:
    try:
        key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        key = ""
    return key or os.getenv("GEMINI_API_KEY", "")


def has_gemini_key() -> bool:
    return bool(_get_gemini_api_key())


def _fallback_summary(red_flags: dict, risk: dict, factors: list[str], plan: list[str]) -> str:
    safety_label = {
        "none": "No selected red flags were detected.",
        "doctor": "A healthcare professional should be contacted based on the selected symptoms.",
        "urgent": "Urgent medical evaluation is recommended based on the selected symptoms.",
    }.get(red_flags.get("level"), "Review symptoms with a healthcare professional.")

    factors_text = ", ".join(factors[:4]) if factors else "No major modifiable factors selected"
    plan_focus = (
        "; ".join(item.rstrip(".") for item in plan[:3])
        if plan
        else "Track symptoms and follow safe self-care basics"
    )

    return (
        "**1. Safety note**\n\n"
        f"{safety_label} This is educational guidance only and does not replace medical care.\n\n"
        "**2. What habits may be contributing**\n\n"
        f"Your risk score is {risk.get('score')} ({risk.get('category')}). Main factors: {factors_text}.\n\n"
        "**3. 7-day focus**\n\n"
        f"{plan_focus}.\n\n"
        "**4. When to seek medical care**\n\n"
        "Seek care for bleeding, severe pain, black or tarry stool, fever, vomiting, unexplained weight loss, or symptoms that persist or worsen."
    )


def generate_ai_summary(
    answers: dict[str, Any],
    red_flags: dict,
    risk: dict,
    factors: list[str],
    plan: list[str],
) -> str:
    api_key = _get_gemini_api_key()
    if not api_key:
        return _fallback_summary(red_flags, risk, factors, plan)

    prompt = f"""
{SAFETY_INSTRUCTION}

Write a short, structured patient-friendly explanation using exactly these headings:
1. Safety note
2. What habits may be contributing
3. 7-day focus
4. When to seek medical care

Use the rule-based result below as the source of truth. Do not add a diagnosis, do not say the patient has hemorrhoids, and do not recommend prescription medications.

Rule-based result:
{json.dumps({
    "answers": answers,
    "red_flags": red_flags,
    "risk": risk,
    "factors": factors,
    "plan": plan,
}, indent=2)}
""".strip()

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=500,
            ),
        )
        text = getattr(response, "text", "") or ""
        return text.strip() or _fallback_summary(red_flags, risk, factors, plan)
    except Exception:
        return _fallback_summary(red_flags, risk, factors, plan)
