import datetime
import xml.etree.ElementTree as ET

import pandas as pd
import plotly.express as px
import streamlit as st

from ai_client import GEMINI_MODEL, generate_ai_summary, has_gemini_key
from logic import (
    calculate_risk_score,
    check_red_flags,
    generate_rule_based_plan,
    get_top_factors,
)


PRODUCT_NAME = "GutGuide"
FIBER_GOAL_GRAMS = 25

st.set_page_config(page_title=f"{PRODUCT_NAME} • Hemorrhoid Care", layout="wide")


if "lifestyle_data" not in st.session_state:
    st.session_state.lifestyle_data = pd.DataFrame(
        {
            "Date": [
                datetime.date(2026, 5, 25),
                datetime.date(2026, 5, 26),
                datetime.date(2026, 5, 27),
                datetime.date(2026, 5, 28),
                datetime.date(2026, 5, 29),
            ],
            "Water_Intake_Oz": [45, 80, 32, 90, 70],
            "Step_Count": [3200, 7500, 2100, 11000, 6800],
            "Active_Minutes": [15, 45, 10, 60, 30],
            "Pain_Scale": [5, 3, 7, 2, 4],
            "Bleeding_Numeric": [1, 0, 2, 0, 1],
            "Total_Fiber_g": [12.0, 26.5, 8.0, 31.0, 18.5],
        }
    )

if "movement_data" not in st.session_state:
    st.session_state.movement_data = pd.DataFrame(
        columns=["Date", "Time", "Stool_Type", "Straining", "Pain", "Bleeding"]
    )

if "fiber_log" not in st.session_state:
    st.session_state.fiber_log = pd.DataFrame(
        {
            "Date": [datetime.date(2026, 5, 25), datetime.date(2026, 5, 26)],
            "Food": ["Oatmeal", "Apple with skin"],
            "Total_Fiber_g": [4.0, 4.4],
        }
    )

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

if "goals" not in st.session_state:
    st.session_state.goals = {
        goal: goal in {"Minimize pain & discomfort", "Reduce or stop bleeding"}
        for goal in GOAL_OPTIONS
    }


def parse_apple_health_xml(xml_file, target_date):
    target_date_str = target_date.strftime("%Y-%m-%d")
    total_steps = 0
    active_mins = 0

    context = ET.iterparse(xml_file, events=("end",))
    for _event, elem in context:
        if elem.tag == "Record":
            creation_date = elem.get("creationDate", "")
            if creation_date.startswith(target_date_str):
                record_type = elem.get("type", "")

                if record_type == "HKQuantityTypeIdentifierStepCount":
                    try:
                        total_steps += int(float(elem.get("value", 0)))
                    except ValueError:
                        pass
                elif record_type == "HKQuantityTypeIdentifierAppleExerciseTime":
                    try:
                        active_mins += int(float(elem.get("value", 0)))
                    except ValueError:
                        pass
        elem.clear()
    return total_steps, active_mins


def render_welcome():
    st.title(f"👋 Welcome to {PRODUCT_NAME}")
    st.caption("Your personal companion for understanding hemorrhoid discomfort and bowel habits.")

    st.info(
        "**This tool is for education and self-tracking only — it is not medical "
        "advice and does not diagnose.** Always talk to a healthcare professional "
        "about concerning symptoms or treatment decisions."
    )

    st.header("📚 Learn the basics")

    with st.expander("🩺 What are hemorrhoids?", expanded=True):
        st.markdown(
            """
Hemorrhoids are swollen veins in and around the anus and lower rectum. Many people
experience hemorrhoid-like discomfort, but similar symptoms can have other causes,
so bleeding or persistent symptoms should be checked by a clinician.

Common symptom patterns can include itching, pain, swelling, or bright red blood,
but this app does not determine the cause of symptoms.
            """
        )

    with st.expander("⚠️ What can contribute to discomfort?"):
        st.markdown(
            """
Pressure and irritation around bowel movements can be influenced by:

- Straining during bowel movements
- Constipation or hard stools
- Low-fiber diet and not drinking enough water
- Sitting for long periods, especially on the toilet
- Low physical activity
            """
        )

    with st.expander("✅ Home habits that may help"):
        st.markdown(
            """
- Increase fiber gradually with fruits, vegetables, beans, lentils, oats, or whole grains.
- Drink water throughout the day.
- Avoid straining and long toilet sitting.
- Walk daily, especially after meals.
- Try a warm sitz bath for short-term discomfort.
            """
        )

    with st.expander("🚨 Red-flag symptoms — seek medical care"):
        st.error("Contact a healthcare professional promptly for possible red flags.")
        st.markdown(
            """
- Dark red, black, or tarry stool
- Rectal bleeding, especially with severe pain
- Fever, vomiting, constant abdominal pain, or unexplained weight loss
- Symptoms that persist or worsen despite home care
            """
        )

    st.divider()
    st.header("🎯 Set your goals")
    st.write("Choose what you'd like to work on. These goals personalize your journey.")

    cols = st.columns(2)
    for i, goal in enumerate(GOAL_OPTIONS):
        with cols[i % 2]:
            st.session_state.goals[goal] = st.checkbox(
                goal, value=st.session_state.goals.get(goal, False), key=f"goal_{i}"
            )

    selected = [goal for goal, on in st.session_state.goals.items() if on]
    if selected:
        st.success(f"You've set **{len(selected)}** goal(s):")
        st.markdown("\n".join(f"- {goal}" for goal in selected))
    else:
        st.warning("No goals selected yet — pick at least one to get started.")


def _bleeding_label(value: int) -> str:
    return {0: "None", 1: "Mild", 2: "Moderate", 3: "Severe"}.get(int(value), "None")


def build_tracker_physician_report() -> str:
    df = st.session_state.lifestyle_data.sort_values("Date")
    movement_df = st.session_state.movement_data.copy()
    start_date = df["Date"].min()
    end_date = df["Date"].max()

    report_lines = [
        f"{PRODUCT_NAME} patient-generated tracking summary",
        f"Date range: {start_date} to {end_date}",
        "",
        "Tracked averages:",
        f"- Water intake: {df['Water_Intake_Oz'].mean():.1f} oz/day",
        f"- Steps: {int(df['Step_Count'].mean()):,}/day",
        f"- Active minutes: {df['Active_Minutes'].mean():.1f} min/day",
        f"- Fiber: {df['Total_Fiber_g'].mean():.1f} g/day",
        f"- Pain score: {df['Pain_Scale'].mean():.1f}/10",
        "",
        "Notable latest values:",
        f"- Latest pain score: {int(df['Pain_Scale'].iloc[-1])}/10",
        f"- Latest bleeding level: {_bleeding_label(df['Bleeding_Numeric'].iloc[-1])}",
        f"- Latest fiber logged: {df['Total_Fiber_g'].iloc[-1]:.1f} g",
    ]

    if not movement_df.empty:
        report_lines.extend(
            [
                "",
                "Bowel movement log:",
                f"- Entries logged: {len(movement_df)}",
                f"- Most recent stool type: {movement_df.iloc[-1]['Stool_Type']}",
                f"- Most recent straining: {movement_df.iloc[-1]['Straining']}",
                f"- Most recent bleeding: {movement_df.iloc[-1]['Bleeding']}",
            ]
        )

    report_lines.extend(
        [
            "",
            "Clinical note:",
            "- This is a patient-generated educational summary, not a diagnosis.",
            "- Rectal bleeding, severe pain, black or tarry stool, fever, vomiting, unexplained weight loss, or persistent symptoms should be evaluated by a healthcare professional.",
        ]
    )
    return "\n".join(report_lines)


def render_lifestyle_tracker():
    st.subheader("Lifestyle & Activity Progress")
    st.write("Track water, steps, activity, fiber, pain, and bleeding over time.")

    st.sidebar.header("📥 Data Input Controls")
    log_date = st.sidebar.date_input("Select Target Date", datetime.date.today())

    st.sidebar.markdown("---")
    st.sidebar.subheader("Automate via Apple Health")
    uploaded_file = st.sidebar.file_uploader("Upload export.xml", type=["xml"])

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

    bleeding_options = {"None": 0, "Mild (spotting)": 1, "Moderate": 2, "Severe": 3}
    with st.sidebar.form(key="metrics_form"):
        st.write(f"Logging for: **{log_date}**")
        water = st.number_input("Water Intake (Ounces)", min_value=0, max_value=250, value=64)
        steps = st.number_input("Step Count", min_value=0, max_value=100000, value=default_steps, step=500)
        active_time = st.number_input("Active Exercise (Minutes)", min_value=0, max_value=480, value=default_mins)
        fiber = st.number_input("Fiber Today (grams)", min_value=0.0, max_value=80.0, value=18.0, step=0.5)
        pain = st.slider("Pain/Discomfort Level", min_value=0, max_value=10, value=3)
        bleeding = st.select_slider("Bleeding Level", options=list(bleeding_options), value="None")
        food_note = st.text_input("Optional fiber food note", placeholder="e.g., oats, beans, berries")
        submit = st.form_submit_button("Save Entry")

    if submit:
        new_entry = pd.DataFrame(
            {
                "Date": [log_date],
                "Water_Intake_Oz": [water],
                "Step_Count": [steps],
                "Active_Minutes": [active_time],
                "Pain_Scale": [pain],
                "Bleeding_Numeric": [bleeding_options[bleeding]],
                "Total_Fiber_g": [fiber],
            }
        )
        st.session_state.lifestyle_data = st.session_state.lifestyle_data[
            st.session_state.lifestyle_data["Date"] != log_date
        ]
        st.session_state.lifestyle_data = pd.concat(
            [st.session_state.lifestyle_data, new_entry], ignore_index=True
        )
        if food_note or fiber:
            fiber_entry = pd.DataFrame(
                {
                    "Date": [log_date],
                    "Food": [food_note or "Daily fiber total"],
                    "Total_Fiber_g": [fiber],
                }
            )
            st.session_state.fiber_log = pd.concat(
                [st.session_state.fiber_log, fiber_entry], ignore_index=True
            )
        st.success("Entry added!")

    selected = [goal for goal, on in st.session_state.goals.items() if on]
    if selected:
        st.caption("🎯 Your goals: " + " · ".join(selected))

    df = st.session_state.lifestyle_data.sort_values(by="Date").copy()
    df["Bleeding_Level"] = df["Bleeding_Numeric"].map(_bleeding_label)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Latest Pain", f"{int(df['Pain_Scale'].iloc[-1])}/10")
    col2.metric("Latest Water", f"{int(df['Water_Intake_Oz'].iloc[-1])} oz")
    col3.metric("Latest Steps", f"{int(df['Step_Count'].iloc[-1]):,}")
    col4.metric("Latest Fiber", f"{df['Total_Fiber_g'].iloc[-1]:.1f} g")

    st.divider()
    st.subheader("📈 Interactive Diagnostic & Lifestyle Trends")
    df_melted = df.melt(
        id_vars=["Date"],
        value_vars=[
            "Water_Intake_Oz",
            "Step_Count",
            "Active_Minutes",
            "Pain_Scale",
            "Bleeding_Numeric",
            "Total_Fiber_g",
        ],
        var_name="Metric",
        value_name="Value",
    )
    fig = px.line(
        df_melted,
        x="Date",
        y="Value",
        color="Metric",
        markers=True,
        title="Daily Multi-Metric Timeline Progression",
        labels={"Value": "Logged Amount", "Metric": "Tracked Variables"},
    )
    fig.update_layout(hovermode="x unified", legend=dict(orientation="h", y=1.02, x=1))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("🧾 Physician Report")
    report_text = build_tracker_physician_report()
    st.text_area("Patient-generated tracking summary", report_text, height=220)
    st.download_button(
        "Download Physician Report (.txt)",
        data=report_text,
        file_name="gutguide_physician_report.txt",
        mime="text/plain",
    )

    if st.checkbox("Show historical table view"):
        st.dataframe(df, use_container_width=True)


def _severity_value(label: str) -> int:
    return {"None": 0, "Mild": 1, "Moderate": 2, "Severe": 3, "Spotting": 1, "Heavy": 3}.get(label, 0)


def render_bowel_tracker():
    st.subheader("Bowel Movement Log")
    st.caption("Based on the tracker prototypes: stool type, straining, pain, bleeding, and trends.")

    with st.form("movement_form"):
        cols = st.columns(4)
        with cols[0]:
            log_date = st.date_input("Date", datetime.date.today(), key="movement_date")
            stool_type = st.selectbox(
                "Stool type",
                [
                    "Bristol 1 - hard lumps",
                    "Bristol 2 - lumpy sausage",
                    "Bristol 3 - cracked sausage",
                    "Bristol 4 - smooth",
                    "Bristol 5 - soft blobs",
                    "Bristol 6 - mushy",
                    "Bristol 7 - watery",
                ],
            )
        with cols[1]:
            straining = st.selectbox("Straining effort", ["None", "Mild", "Moderate", "Severe"])
            pain = st.selectbox("Pain level", ["None", "Mild", "Moderate", "Severe"])
        with cols[2]:
            bleeding = st.selectbox("Bleeding", ["None", "Spotting", "Moderate", "Heavy"])
            log_time = st.time_input("Time", datetime.datetime.now().time().replace(second=0, microsecond=0))
        with cols[3]:
            st.write("")
            st.write("")
            submitted = st.form_submit_button("Save this movement", use_container_width=True)

    if submitted:
        new_row = pd.DataFrame(
            {
                "Date": [log_date],
                "Time": [log_time.strftime("%H:%M")],
                "Stool_Type": [stool_type],
                "Straining": [straining],
                "Pain": [pain],
                "Bleeding": [bleeding],
            }
        )
        st.session_state.movement_data = pd.concat(
            [st.session_state.movement_data, new_row], ignore_index=True
        )
        st.success("Movement saved.")

    df = st.session_state.movement_data.copy()
    if df.empty:
        st.info("No movements logged yet. Add one above to start seeing trends.")
        return

    today = datetime.date.today()
    today_df = df[df["Date"] == today]
    st.markdown("**Today's log**")
    if today_df.empty:
        st.caption("No movements logged today.")
    else:
        st.dataframe(today_df.sort_values("Time"), use_container_width=True, hide_index=True)

    trend_df = df.copy()
    trend_df["Date"] = pd.to_datetime(trend_df["Date"])
    trend_df["Straining_Score"] = trend_df["Straining"].map(_severity_value)
    trend_df["Bleeding_Score"] = trend_df["Bleeding"].map(_severity_value)

    last_week = pd.Timestamp(today - datetime.timedelta(days=6))
    trend_df = trend_df[trend_df["Date"] >= last_week]
    grouped = (
        trend_df.groupby("Date")
        .agg(
            Movement_Count=("Date", "size"),
            Avg_Straining=("Straining_Score", "mean"),
            Avg_Bleeding=("Bleeding_Score", "mean"),
        )
        .reset_index()
    )

    tab_strain, tab_count = st.tabs(["Straining vs bleeding", "Movement count"])
    with tab_strain:
        melted = grouped.melt(
            id_vars=["Date"],
            value_vars=["Avg_Straining", "Avg_Bleeding"],
            var_name="Metric",
            value_name="Score",
        )
        fig = px.bar(melted, x="Date", y="Score", color="Metric", barmode="group")
        st.plotly_chart(fig, use_container_width=True)
    with tab_count:
        fig = px.bar(grouped, x="Date", y="Movement_Count")
        st.plotly_chart(fig, use_container_width=True)


def render_fiber_insights():
    st.subheader("🌾 Fiber Insights")
    st.caption("Manual fiber tracking keeps the demo safe and does not require Gemini to estimate nutrition.")

    fiber_df = st.session_state.fiber_log.copy()
    total_fiber = fiber_df["Total_Fiber_g"].sum() if not fiber_df.empty else 0
    latest_day = st.session_state.lifestyle_data.sort_values("Date").iloc[-1]["Total_Fiber_g"]
    progress = min(float(latest_day) / FIBER_GOAL_GRAMS, 1.0)

    col1, col2, col3 = st.columns(3)
    col1.metric("Latest Day Fiber", f"{latest_day:.1f} g")
    col2.metric("Daily Goal", f"{FIBER_GOAL_GRAMS} g")
    col3.metric("Logged Total", f"{total_fiber:.1f} g")
    st.progress(progress)

    if not fiber_df.empty:
        fig = px.bar(
            fiber_df,
            x="Food",
            y="Total_Fiber_g",
            color="Food",
            title="Fiber Contribution by Logged Item",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(fiber_df, use_container_width=True, hide_index=True)


def render_tracker():
    st.title("📈 Patient Lifestyle & Activity Progress")
    tab_lifestyle, tab_bowel, tab_fiber = st.tabs(
        ["Lifestyle metrics", "Bowel movement log", "Fiber insights"]
    )
    with tab_lifestyle:
        render_lifestyle_tracker()
    with tab_bowel:
        render_bowel_tracker()
    with tab_fiber:
        render_fiber_insights()


def _yes_no(label: str, key: str) -> bool:
    return st.radio(label, ["No", "Yes"], horizontal=True, key=key) == "Yes"


def build_doctor_summary(result: dict) -> str:
    answers = result["answers"]
    red_flags = result["red_flags"]
    risk = result["risk"]
    factors = result["factors"]
    plan = result["plan"]

    return "\n".join(
        [
            f"Product: {PRODUCT_NAME}",
            "Purpose: Educational self-care support; not diagnostic.",
            "",
            "Selected symptoms:",
            f"- Rectal bleeding: {answers['rectal_bleeding']}",
            f"- Pain level: {answers['pain_level']}/10",
            f"- Itching/burning: {'yes' if answers['itching_burning'] else 'no'}",
            f"- Swelling/lump: {'yes' if answers['swelling_lump'] else 'no'}",
            f"- Symptom duration: {answers['symptom_duration']}",
            f"- Fever/vomiting/constant abdominal pain/unexplained weight loss: {'yes' if answers['systemic_symptoms'] else 'no'}",
            "",
            "Bowel habits:",
            f"- Bowel movements per week: {answers['bowel_movements_per_week']}",
            f"- Stool type: {answers['stool_type']}",
            f"- Straining: {answers['straining']}",
            f"- Time on toilet: {answers['toilet_time']}",
            "",
            "Routine factors:",
            f"- Water intake: {answers['water_intake']}",
            f"- Fiber intake: {answers['fiber_intake']}",
            f"- Sitting long hours daily: {'yes' if answers['sitting_long_hours'] else 'no'}",
            f"- Exercise/walking: {answers['exercise_walking']}",
            "",
            f"Safety status: {red_flags['level']}",
            f"Safety messages: {'; '.join(red_flags['messages'])}",
            f"Risk score: {risk['score']} ({risk['category']})",
            f"Top factors: {', '.join(factors)}",
            "Plan: " + " ".join(f"{i + 1}. {item}" for i, item in enumerate(plan)),
        ]
    )


def render_results(result: dict):
    red_flags = result["red_flags"]
    risk = result["risk"]
    factors = result["factors"]
    plan = result["plan"]

    st.divider()
    st.header("Results")
    st.caption("Educational guidance only. This app does not diagnose hemorrhoids or replace medical care.")

    st.subheader("Safety Status")
    if red_flags["level"] == "urgent":
        st.error("Urgent: medical evaluation is recommended.")
    elif red_flags["level"] == "doctor":
        st.warning("Doctor recommended: contact a healthcare professional.")
    else:
        st.success("No selected red flags detected.")
    for message in red_flags["messages"]:
        st.write(f"- {message}")

    st.subheader("Risk Score")
    col_score, col_category = st.columns([1, 3])
    with col_score:
        st.metric("Score", risk["score"])
    with col_category:
        st.metric("Category", risk["category"])
        st.progress(min(risk["score"] / 14, 1.0))
    st.write(risk["explanation"])

    st.subheader("Main Contributing Factors")
    st.markdown("\n".join(f"- {factor}" for factor in factors))

    st.subheader("Self-Care Plan")
    st.markdown("\n".join(f"{i + 1}. {item}" for i, item in enumerate(plan)))

    st.subheader("AI Summary")
    if has_gemini_key():
        st.caption(f"Generated with Gemini using `{GEMINI_MODEL}`. Rule-based safety status remains the source of truth.")
    else:
        st.caption("No Gemini key found, so GutGuide is showing a non-AI fallback summary.")
    st.markdown(result["ai_summary"])

    st.subheader("Doctor Summary")
    summary = build_doctor_summary(result)
    st.text_area("Copy or discuss this concise summary with a healthcare professional.", value=summary, height=280)
    st.download_button(
        "Download Doctor Summary (.txt)",
        data=summary,
        file_name="gutguide_doctor_summary.txt",
        mime="text/plain",
    )


def render_assessment():
    st.title("🧭 Self-Care Check")
    st.info(
        "GutGuide provides educational guidance only. It does not diagnose hemorrhoids, "
        "and Gemini cannot override the rule-based safety result."
    )

    with st.form("self_care_form"):
        st.subheader("Symptoms")
        cols = st.columns(2)
        with cols[0]:
            rectal_bleeding = st.selectbox(
                "Rectal bleeding",
                ["none", "bright red", "dark red or black-tarry"],
            )
            pain_level = st.slider("Pain level", 0, 10, 2)
            itching_burning = _yes_no("Itching or burning", "itching_burning")
        with cols[1]:
            swelling_lump = _yes_no("Swelling or lump", "swelling_lump")
            symptom_duration = st.selectbox(
                "Symptom duration",
                ["less than 1 week", "1-3 weeks", "more than 3 weeks"],
            )
            systemic_symptoms = _yes_no(
                "Fever, vomiting, constant abdominal pain, or unexplained weight loss",
                "systemic_symptoms",
            )

        st.subheader("Bowel habits")
        cols = st.columns(2)
        with cols[0]:
            bowel_movements_per_week = st.selectbox("Bowel movements per week", ["0-2", "3-6", "daily"])
            stool_type = st.selectbox("Stool type", ["hard/lumpy", "normal", "loose"])
        with cols[1]:
            straining = st.selectbox("Straining", ["never", "sometimes", "often"])
            toilet_time = st.selectbox("Time on toilet", ["less than 5 min", "5-10 min", "more than 10 min"])

        st.subheader("Routine")
        cols = st.columns(2)
        with cols[0]:
            water_intake = st.selectbox("Water intake", ["less than 4 cups", "4-7 cups", "8+ cups"])
            fiber_intake = st.selectbox("Fiber intake", ["low", "medium", "high"])
        with cols[1]:
            sitting_long_hours = _yes_no("Sitting long hours daily", "sitting_long_hours")
            exercise_walking = st.selectbox("Exercise/walking", ["none", "some", "daily"])

        submitted = st.form_submit_button("Create my self-care plan", use_container_width=True)

    if submitted:
        answers = {
            "rectal_bleeding": rectal_bleeding,
            "pain_level": pain_level,
            "itching_burning": itching_burning,
            "swelling_lump": swelling_lump,
            "symptom_duration": symptom_duration,
            "systemic_symptoms": systemic_symptoms,
            "bowel_movements_per_week": bowel_movements_per_week,
            "stool_type": stool_type,
            "straining": straining,
            "toilet_time": toilet_time,
            "water_intake": water_intake,
            "fiber_intake": fiber_intake,
            "sitting_long_hours": sitting_long_hours,
            "exercise_walking": exercise_walking,
        }
        red_flags = check_red_flags(answers)
        risk = calculate_risk_score(answers)
        factors = get_top_factors(answers)
        plan = generate_rule_based_plan(answers, factors)
        ai_summary = generate_ai_summary(answers, red_flags, risk, factors, plan)
        st.session_state.assessment_result = {
            "answers": answers,
            "red_flags": red_flags,
            "risk": risk,
            "factors": factors,
            "plan": plan,
            "ai_summary": ai_summary,
        }

    if "assessment_result" in st.session_state:
        render_results(st.session_state.assessment_result)


def render_assistant():
    st.title("🤖 GutGuide AI Assistant")
    st.caption("A short patient-friendly explanation of your latest rule-based GutGuide result.")
    st.info(
        "Gemini is used only to rephrase the rule-based result. It does not decide safety status "
        "and cannot override red-flag recommendations."
    )

    if "assessment_result" not in st.session_state:
        st.warning("Complete the Self-Care Check first to generate an AI-ready summary.")
        return

    result = st.session_state.assessment_result
    if st.button("Refresh AI summary", use_container_width=True):
        result["ai_summary"] = generate_ai_summary(
            result["answers"],
            result["red_flags"],
            result["risk"],
            result["factors"],
            result["plan"],
        )
        st.session_state.assessment_result = result

    if has_gemini_key():
        st.success(f"Gemini key detected. Summaries use `{GEMINI_MODEL}`.")
    else:
        st.warning("No Gemini key detected. The app is using the built-in non-AI fallback summary.")

    st.markdown(result["ai_summary"])


st.sidebar.title(f"🧭 {PRODUCT_NAME}")
page = st.sidebar.radio(
    "Go to",
    ["👋 Welcome & Setup", "📊 Symptom Tracker", "🧭 Self-Care Check", "🤖 AI Assistant"],
)
st.sidebar.divider()
st.sidebar.caption("Educational self-care support. Not a diagnosis or replacement for medical care.")

if page == "👋 Welcome & Setup":
    render_welcome()
elif page == "📊 Symptom Tracker":
    render_tracker()
elif page == "🧭 Self-Care Check":
    render_assessment()
else:
    render_assistant()
