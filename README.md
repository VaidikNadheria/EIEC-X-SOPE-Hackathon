# GutGuide

Educational self-care support for people tracking hemorrhoid-like discomfort, constipation habits, and daily routines.

## Problem

Patients with rectal discomfort, constipation, bleeding, or straining often need a simple way to understand which symptoms require medical attention and which daily habits may be contributing.

## Solution

GutGuide combines a symptom and routine check, a lightweight tracker, safe rule-based recommendations, and an optional Gemini patient-friendly summary. Safety decisions are rule-based; Gemini only rephrases the result and never overrides red-flag logic.

## Features

- Welcome and education flow with patient goals
- Lifestyle tracker for water, steps, activity, pain, bleeding, and fiber
- Bowel movement log inspired by teammate tracker prototypes
- Fiber insights from safe manual tracking
- Rule-based safety status for red flags
- Constipation and straining risk score
- Main contributing factors and personalized self-care plan
- Optional Gemini summary with a non-AI fallback
- Doctor summary and downloadable physician report

## Tech Stack

- Python
- Streamlit
- pandas
- Plotly
- Google Gemini via `google-genai`

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

The demo works without a Gemini API key. In that case, the AI Summary section shows a clean rule-based fallback summary.

## Add Gemini API Key

Create `.streamlit/secrets.toml` locally and add a `GEMINI_API_KEY` entry. Use `.streamlit/secrets.toml.example` as the template. The real secrets file is ignored by Git.

You can also set the `GEMINI_API_KEY` environment variable.

## Safety Disclaimer

GutGuide is for educational guidance and self-tracking only. It does not diagnose hemorrhoids or any other condition and does not replace professional medical care. Seek medical care for bleeding, severe pain, black or tarry stool, fever, vomiting, unexplained weight loss, or symptoms that persist or worsen.

## Demo Patient Example

- Bright red bleeding
- Pain level 4/10
- Hard/lumpy stool
- Bowel movements 0-2 times per week
- Often straining
- More than 10 minutes on the toilet
- Less than 4 cups of water daily
- Low fiber and no exercise

Expected demo result: doctor recommended for bleeding, high constipation/straining risk, top factors around hard stool, infrequent bowel movements, straining, toilet time, low fiber, low water, and a self-care plan.

## Future Improvements

- Persist tracker data in a database
- Add clinician-exportable PDF summaries
- Add reminders for hydration, fiber, walking, and symptom checks
- Add optional Apple Health integration beyond XML upload
- Expand accessibility and multilingual support
