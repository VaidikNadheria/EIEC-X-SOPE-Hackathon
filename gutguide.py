import streamlit as st
import pandas as pd
import datetime
import plotly.express as px

# Set up page config
st.set_page_config(page_title="GutGuide • Hemorrhoid Care", layout="wide")

# ---------------------------------------------------------------------------
# Shared State Setup
# ---------------------------------------------------------------------------
# 1. Simulate a Database (In a real app, connect this to SQLite, PostgreSQL, or Supabase)
if 'tracker_data' not in st.session_state:
    # Starting with some dummy historical data to show the live visualization immediately
    st.session_state.tracker_data = pd.DataFrame({
        'Date': [datetime.date(2026, 5, 25), datetime.date(2026, 5, 26), datetime.date(2026, 5, 27), datetime.date(2026, 5, 28), datetime.date(2026, 5, 29)],
        'Water_Oz': [40, 80, 32, 96, 75],
        'Steps': [3000, 8000, 2500, 10000, 7000],
        'Pain_Scale': [8, 3, 9, 2, 4]
    })

# All goals a patient can opt into. Stored as {label: bool} so selections persist
# across page switches and can later be used to personalize the tracker.
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
# Page: Symptom Tracker
# ---------------------------------------------------------------------------
def render_tracker():
    st.title("📊 Patient Symptom & Lifestyle Tracker")

    # Remind the patient of their chosen goals.
    selected = [g for g, on in st.session_state.goals.items() if on]
    if selected:
        st.caption("🎯 Your goals: " + " · ".join(selected))

    # Sidebar Layout for Data Entry (Inputs)
    st.sidebar.header("📥 Log Today's Metrics")
    with st.sidebar.form(key='log_form', clear_on_submit=True):
        log_date = st.date_input("Date", datetime.date.today())

        # Existing metrics
        water = st.number_input("Water Intake (Ounces)", min_value=0, max_value=200, value=64)
        steps = st.number_input("Steps Per Day", min_value=0, max_value=50000, value=5000, step=500)
        pain = st.slider("Pain/Discomfort Level (1-10)", min_value=1, max_value=10, value=5)

        st.markdown("---")
        st.subheader("GI & Activity Metrics")

        # 1. Bleeding Level (Categorical Mapping)
        bleeding = st.select_slider(
            "Bleeding Level",
            options=["None", "Mild (Spotting)", "Moderate", "Severe"],
            value="None"
        )

        # 2. Time Spent on Toilet (Minutes)
        toilet_time = st.slider("Time on Toilet (Minutes)", min_value=0, max_value=60, value=5)

        # 3. Exercise Type
        exercise_type = st.selectbox(
            "Primary Exercise Today",
            options=["None", "Walking", "Running/Cardio", "Yoga/Stretching", "Heavy Weightlifting", "Other"]
        )

        submit_button = st.form_submit_button(label='Submit Entry')

    # Handle form submission to update our data
    if submit_button:
        new_entry = pd.DataFrame({
            'Date': [log_date],
            'Water_Oz': [water],
            'Steps': [steps],
            'Pain_Scale': [pain],
            'Bleeding': [bleeding],
            'Toilet_Min': [toilet_time],
            'Exercise': [exercise_type]
        })
        # Append data and reset index
        st.session_state.tracker_data = pd.concat([st.session_state.tracker_data, new_entry], ignore_index=True)
        st.success("Metrics logged successfully!")

    # Main Dashboard Layout (Visualizations)
    df = st.session_state.tracker_data.sort_values(by='Date')

    # Summary Metrics at the top
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Latest Pain Score", value=f"{df['Pain_Scale'].iloc[-1]} / 10")
    with col2:
        st.metric(label="Latest Water Intake", value=f"{df['Water_Oz'].iloc[-1]} oz")
    with col3:
        st.metric(label="Latest Step Count", value=f"{df['Steps'].iloc[-1]:,}")

    st.write("---")
    st.subheader("📈 Live Correlation Trends")

    # Live Plotly Chart: Water Intake vs. Pain Levels over time
    fig = px.line(df, x='Date', y=['Water_Oz', 'Pain_Scale'],
                  title="Water Intake vs. Pain Levels Over Time",
                  labels={'value': 'Measurement', 'variable': 'Metrics'},
                  markers=True)

    # Update layout to make it cleaner
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(fig, width='stretch')
    # Display raw data option for validation
    if st.checkbox("Show raw logs table"):
        st.dataframe(df)


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------
st.sidebar.title("🧭 GutGuide")
page = st.sidebar.radio("Go to", ["👋 Welcome & Setup", "📊 Symptom Tracker"])
st.sidebar.divider()

if page == "👋 Welcome & Setup":
    render_welcome()
else:
    render_tracker()
