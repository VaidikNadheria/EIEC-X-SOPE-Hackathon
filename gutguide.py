import streamlit as st
import pandas as pd
import datetime
import xml.etree.ElementTree as ET
import plotly.express as px

# Set up page config
st.set_page_config(page_title="GutGuide • Hemorrhoid Care", layout="wide")

# ---------------------------------------------------------------------------
# Shared State Setup
# ---------------------------------------------------------------------------
# Mock database of lifestyle metrics (in a real app: SQLite/Postgres/Supabase).
if 'lifestyle_data' not in st.session_state:
    st.session_state.lifestyle_data = pd.DataFrame({
        'Date': [datetime.date(2026, 5, 25), datetime.date(2026, 5, 26), datetime.date(2026, 5, 27), datetime.date(2026, 5, 28), datetime.date(2026, 5, 29)],
        'Water_Intake_Oz': [45, 80, 32, 90, 70],
        'Step_Count': [3200, 7500, 2100, 11000, 6800],
        'Active_Minutes': [15, 45, 10, 60, 30]
    })

# All goals a patient can opt into. Stored as {label: bool} so selections persist
# across page switches and can later be used to personalize the experience.
GOAL_OPTIONS = [
    "Minimize pain & discomfort",
    "Reduce or stop bleeding",
    "Increase daily water intake",
    "Eat more fiber",
    "Stay more physically active (steps)",
    "Reduce time spent straining on the toilet",
    "Have softer, more regular bowel movements",
    "Reduce itching & irritation",
    "Avoid recurrence / flare-ups",
]
if 'goals' not in st.session_state:
    # Default a couple of common starter goals to on.
    st.session_state.goals = {g: g in {
        "Minimize pain & discomfort",
        "Reduce or stop bleeding",
    } for g in GOAL_OPTIONS}


# ---------------------------------------------------------------------------
# Apple Health XML Parser (used by the tracker page)
# ---------------------------------------------------------------------------
def parse_apple_health_xml(xml_file, target_date):
    target_date_str = target_date.strftime("%Y-%m-%d")
    total_steps = 0
    active_mins = 0

    context = ET.iterparse(xml_file, events=('end',))
    for event, elem in context:
        if elem.tag == 'Record':
            creation_date = elem.get('creationDate', '')
            if creation_date.startswith(target_date_str):
                record_type = elem.get('type', '')

                # Extract Step Count
                if record_type == 'HKQuantityTypeIdentifierStepCount':
                    try:
                        total_steps += int(float(elem.get('value', 0)))
                    except ValueError:
                        pass

                # Extract Active/Exercise Time (Apple tracks this via AppleExerciseTime)
                elif record_type == 'HKQuantityTypeIdentifierAppleExerciseTime':
                    try:
                        active_mins += int(float(elem.get('value', 0)))
                    except ValueError:
                        pass
        elem.clear()
    return total_steps, active_mins


# ---------------------------------------------------------------------------
# Page: Welcome & Setup
# ---------------------------------------------------------------------------
def render_welcome():
    st.title("👋 Welcome to GutGuide")
    st.caption("Your personal companion for understanding and managing hemorrhoids.")

    st.info(
        "**This tool is for education and self-tracking only — it is not medical "
        "advice.** Always talk to a healthcare professional about your symptoms, "
        "especially before starting any treatment."
    )

    # --- Education ---------------------------------------------------------
    st.header("📚 Learn the basics")

    with st.expander("🩺 What are hemorrhoids?", expanded=True):
        st.markdown(
            """
Hemorrhoids (also called *piles*) are **swollen veins in and around the anus and
lower rectum** — similar to varicose veins. They are extremely common: by age 50,
roughly **half of adults** have had them at some point.

There are two main types:

- **Internal** — inside the rectum. Usually painless, but may bleed or, when
  enlarged, *prolapse* (bulge outside the anus).
- **External** — under the skin around the anus. These can be itchy, painful, and
  may form a painful clot (*thrombosis*).

The good news: most hemorrhoids are **harmless and improve with simple lifestyle
changes and home care.**
            """
        )

    with st.expander("⚠️ What causes them?"):
        st.markdown(
            """
Hemorrhoids develop when there is **increased pressure** on the veins around the
anus and rectum. Common contributors include:

- **Straining** during bowel movements
- **Constipation** or chronic diarrhea
- **Low-fiber diet** and not drinking enough water
- **Sitting for long periods**, especially on the toilet
- **Pregnancy** (pressure from the growing uterus)
- **Heavy lifting** done repeatedly
- **Obesity** and a sedentary lifestyle
- **Aging** (the supporting tissues weaken over time)
            """
        )

    with st.expander("✅ How to manage & prevent them"):
        st.markdown(
            """
Most cases respond well to **lifestyle and home measures**:

**Diet & hydration**
- Eat more **fiber** (fruits, vegetables, whole grains, legumes) — aim for 25–35 g/day.
- **Drink plenty of water** to keep stools soft.

**Bathroom habits**
- **Don't strain** or sit on the toilet for long periods.
- **Go when you feel the urge** — don't hold it.

**Activity & comfort**
- Stay **physically active** to keep bowels regular.
- Try **warm sitz baths** (sitting in a few inches of warm water for 10–15 min).
- Over-the-counter creams, wipes, or cold packs may ease symptoms short-term.

**When home care isn't enough**, a clinician can offer treatments such as rubber
band ligation or minor procedures. *Discuss options with your provider.*
            """
        )

    with st.expander("🚨 Red-flag symptoms — seek medical care"):
        st.error(
            """
**Contact a healthcare provider promptly if you notice any of the following.**
These can signal a more serious condition that needs evaluation:
            """
        )
        st.markdown(
            """
- **Heavy or persistent rectal bleeding**, or blood that won't stop
- **Black, tarry, or maroon-colored stools**
- **Dizziness, lightheadedness, or fainting** (possible significant blood loss)
- **Severe or worsening pain**, especially a sudden, very painful anal lump
- **Fever, chills, or pus/discharge** (possible infection)
- **A change in bowel habits** lasting more than a couple of weeks
- **Unexplained weight loss**
- Symptoms that **don't improve after about a week** of home care
- You are **over 40 with new rectal bleeding** — get it checked to rule out other causes

> ⚠️ Rectal bleeding should never be assumed to be "just hemorrhoids" without a
> proper evaluation, as other conditions can cause similar symptoms.
            """
        )

    st.divider()

    # --- Goal Setup --------------------------------------------------------
    st.header("🎯 Set your goals")
    st.write(
        "Choose what you'd like to work on. These goals personalize your journey — "
        "you can change them anytime."
    )

    cols = st.columns(2)
    for i, goal in enumerate(GOAL_OPTIONS):
        with cols[i % 2]:
            st.session_state.goals[goal] = st.checkbox(
                goal, value=st.session_state.goals.get(goal, False), key=f"goal_{i}"
            )

    selected = [g for g, on in st.session_state.goals.items() if on]
    st.divider()
    if selected:
        st.success(f"You've set **{len(selected)}** goal(s):")
        st.markdown("\n".join(f"- {g}" for g in selected))
        st.caption("Head to the **📊 Symptom Tracker** in the sidebar to start logging.")
    else:
        st.warning("No goals selected yet — pick at least one to get started.")


# ---------------------------------------------------------------------------
# Page: Symptom / Lifestyle Tracker
# ---------------------------------------------------------------------------
def render_tracker():
    st.title("📈 Patient Lifestyle & Activity Progress")
    st.write("Track daily progressions and toggle individual metrics in the chart legend to isolate trends.")

    # Sidebar Log Form
    st.sidebar.header("📥 Data Input Controls")
    log_date = st.sidebar.date_input("Select Target Date", datetime.date.today())

    st.sidebar.markdown("---")
    st.sidebar.subheader("Automate via Apple Health")
    uploaded_file = st.sidebar.file_uploader("Upload export.xml", type=["xml"])

    # Default fallback values for inputs
    default_steps = 5000
    default_mins = 20

    if uploaded_file is not None:
        with st.spinner("Parsing XML file..."):
            try:
                uploaded_file.seek(0)
                parsed_steps, parsed_mins = parse_apple_health_xml(uploaded_file, log_date)
                default_steps = int(parsed_steps)
                default_mins = int(parsed_mins)
                st.sidebar.success(f"Extracted data for {log_date}!")
            except Exception:
                st.sidebar.error("Could not parse file formatting.")

    st.sidebar.markdown("---")

    with st.sidebar.form(key='metrics_form'):
        st.write(f"Logging for: **{log_date}**")
        water = st.number_input("Water Intake (Ounces)", min_value=0, max_value=250, value=64)
        steps = st.number_input("Step Count", min_value=0, max_value=100000, value=default_steps, step=500)
        active_time = st.number_input("Active Exercise (Minutes)", min_value=0, max_value=480, value=default_mins)

        submit = st.form_submit_button("Save Entry")

    if submit:
        new_entry = pd.DataFrame({
            'Date': [log_date],
            'Water_Intake_Oz': [water],
            'Step_Count': [steps],
            'Active_Minutes': [active_time]
        })
        # Remove existing row for that date to prevent duplicates
        st.session_state.lifestyle_data = st.session_state.lifestyle_data[st.session_state.lifestyle_data['Date'] != log_date]
        # Append data
        st.session_state.lifestyle_data = pd.concat([st.session_state.lifestyle_data, new_entry], ignore_index=True)
        st.success("Entry added!")

    # Remind the patient of their chosen goals.
    selected = [g for g, on in st.session_state.goals.items() if on]
    if selected:
        st.caption("🎯 Your goals: " + " · ".join(selected))

    # Preparing Visualizations
    df = st.session_state.lifestyle_data.sort_values(by='Date')

    # Melt the data from wide to long format so each metric is a togglable line.
    df_melted = df.melt(id_vars=['Date'],
                        value_vars=['Water_Intake_Oz', 'Step_Count', 'Active_Minutes'],
                        var_name='Metric', value_name='Value')

    fig = px.line(df_melted, x='Date', y='Value', color='Metric', markers=True,
                  title="Daily Multi-Metric Timeline Progression",
                  labels={'Value': 'Logged Amount', 'Metric': 'Tracked Variables'})

    fig.update_layout(
        hovermode="x unified",
        legend=dict(
            title="Click to Toggle Variables:",
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    st.plotly_chart(fig, use_container_width=True)

    # Raw Data Inspection Option
    if st.checkbox("Show historical table view"):
        st.dataframe(df)


# ---------------------------------------------------------------------------
# Page: AI Assistant (Gemini)
# ---------------------------------------------------------------------------
GEMINI_MODEL = "gemini-2.5-flash"

# Safety-conscious persona. The model is told to educate, reference the patient's
# own logged data, and ALWAYS escalate red-flag symptoms to a real clinician.
SYSTEM_INSTRUCTION = """You are "GutGuide AI", a supportive, plain-spoken health \
assistant inside a hemorrhoid symptom- and lifestyle-tracking app. Your job is to help \
the patient understand their logged data, discuss how they're feeling, and suggest \
evidence-based self-care.

Rules you must always follow:
- You are NOT a doctor and you do NOT diagnose. You provide general education and \
self-care suggestions only. Remind the user to consult a healthcare professional for \
diagnosis or treatment, especially before starting medication or procedures.
- Ground your observations in the patient's actual logged data when it is provided \
(reference specific numbers and trends, e.g. water intake, steps, active minutes, and \
any symptoms they mention).
- Be encouraging and non-judgmental. Use clear, everyday language. Keep answers \
concise and well-structured (short paragraphs or bullet points).
- RED FLAGS: if the user reports heavy/persistent bleeding, black or tarry stools, \
dizziness/fainting, severe or sudden worsening pain, fever, or unexplained weight \
loss, you MUST clearly and promptly urge them to seek medical care, and not downplay it.
- Tie suggestions to the patient's stated goals when relevant.
- Never invent data the patient did not provide."""


def summarize_tracker_data():
    """Build a compact, schema-agnostic summary of whatever the patient has logged,
    plus their goals, to feed Gemini as context. Works regardless of which columns
    the tracker currently uses."""
    # Find the active data table (lifestyle tracker, or older symptom table).
    df = None
    for key in ("lifestyle_data", "tracker_data"):
        if key in st.session_state and isinstance(st.session_state[key], pd.DataFrame):
            df = st.session_state[key]
            break
    if df is None or df.empty:
        return "No tracker data has been logged yet."

    df = df.sort_values(by='Date') if 'Date' in df.columns else df
    lines = []

    selected_goals = [g for g, on in st.session_state.goals.items() if on]
    if selected_goals:
        lines.append("Patient's stated goals: " + "; ".join(selected_goals) + ".")

    n = len(df)
    lines.append(f"Number of logged days: {n}.")
    if 'Date' in df.columns:
        lines.append(f"Date range: {df['Date'].iloc[0]} to {df['Date'].iloc[-1]}.")

    latest = df.iloc[-1]
    # Describe every metric column generically.
    for col in df.columns:
        if col == 'Date':
            continue
        series = df[col]
        label = col.replace('_', ' ')
        if pd.api.types.is_numeric_dtype(series):
            lines.append(
                f"{label}: latest {latest[col]}, average {series.mean():.1f}, "
                f"range {series.min()}-{series.max()}."
            )
        else:
            recent = [v for v in series.tail(5).tolist() if pd.notna(v)]
            if recent:
                lines.append(f"{label} (recent, oldest→newest): " + ", ".join(map(str, recent)) + ".")

    return "\n".join(lines)


def get_gemini_api_key():
    """Resolve the Gemini API key from secrets, environment, or a user-entered value."""
    import os
    # 1. Streamlit secrets (.streamlit/secrets.toml)
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    # 2. Environment variables
    for var in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        if os.environ.get(var):
            return os.environ[var]
    # 3. Session-entered key
    return st.session_state.get("gemini_api_key", "")


def call_gemini(api_key, history, data_summary):
    """Send the full conversation to Gemini and return the assistant's reply text."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    # Prepend the latest data snapshot so every reply reflects current logs.
    system_instruction = (
        SYSTEM_INSTRUCTION
        + "\n\n--- PATIENT'S CURRENT TRACKER DATA ---\n"
        + data_summary
    )

    contents = [
        types.Content(role=m["role"], parts=[types.Part(text=m["content"])])
        for m in history
    ]

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.7,
        ),
    )
    return response.text


def render_assistant():
    st.title("🤖 GutGuide AI Assistant")
    st.caption("Discuss your symptoms and get self-care suggestions based on your logged data.")

    st.info(
        "**This AI provides general education only — it is not a doctor and cannot "
        "diagnose.** For any red-flag symptoms (heavy bleeding, severe pain, dizziness, "
        "fever), contact a healthcare professional right away."
    )

    # --- API key handling --------------------------------------------------
    api_key = get_gemini_api_key()
    if not api_key:
        st.warning("A Google Gemini API key is required to use the assistant.")
        with st.expander("🔑 Enter your Gemini API key", expanded=True):
            st.markdown(
                "Get a free key at [Google AI Studio](https://aistudio.google.com/app/apikey). "
                "You can also set it as an environment variable `GEMINI_API_KEY` or in "
                "`.streamlit/secrets.toml`."
            )
            entered = st.text_input("Gemini API key", type="password", key="gemini_api_key_input")
            if entered:
                st.session_state.gemini_api_key = entered
                st.rerun()
        return

    # --- Chat state --------------------------------------------------------
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    data_summary = summarize_tracker_data()

    # Action buttons.
    col_a, col_b = st.columns([1, 1])
    with col_a:
        review_clicked = st.button("📋 Review my tracker data", use_container_width=True)
    with col_b:
        if st.button("🗑️ Clear conversation", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

    with st.expander("👀 What the assistant can see (your data summary)"):
        st.code(data_summary, language="text")

    # Render existing conversation.
    for msg in st.session_state.chat_history:
        role = "assistant" if msg["role"] == "model" else "user"
        with st.chat_message(role):
            st.markdown(msg["content"])

    # Helper to send a message and append the reply to history.
    def send(user_text):
        st.session_state.chat_history.append({"role": "user", "content": user_text})
        with st.chat_message("user"):
            st.markdown(user_text)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    reply = call_gemini(api_key, st.session_state.chat_history, data_summary)
                except Exception as e:
                    reply = f"⚠️ Sorry, I couldn't reach Gemini: `{e}`"
            st.markdown(reply)
        st.session_state.chat_history.append({"role": "model", "content": reply})

    # Seed a data review on demand.
    if review_clicked:
        send(
            "Please review my logged data above. Point out any notable trends or "
            "correlations (e.g. between water, steps, and activity), flag anything I "
            "should watch, and give me 2-3 concrete self-care suggestions tied to my goals."
        )
        st.rerun()

    # Free-form chat input.
    prompt = st.chat_input("Ask about your symptoms, trends, or what you can try...")
    if prompt:
        send(prompt)
        st.rerun()


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------
st.sidebar.title("🧭 GutGuide")
page = st.sidebar.radio(
    "Go to",
    ["👋 Welcome & Setup", "📊 Symptom Tracker", "🤖 AI Assistant"],
)
st.sidebar.divider()

if page == "👋 Welcome & Setup":
    render_welcome()
elif page == "📊 Symptom Tracker":
    render_tracker()
else:
    render_assistant()
