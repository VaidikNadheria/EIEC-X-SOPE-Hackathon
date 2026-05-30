import streamlit as st
import pandas as pd
import datetime
import plotly.express as px

# Set up page config
st.set_page_config(page_title="Hemorrhoid Symptom Tracker", layout="wide")
st.title("📊 Patient Symptom & Lifestyle Tracker")

# 1. Simulate a Database (In a real app, connect this to SQLite, PostgreSQL, or Supabase)
if 'tracker_data' not in st.session_state:
    # Starting with some dummy historical data to show the live visualization immediately
    st.session_state.tracker_data = pd.DataFrame({
        'Date': [datetime.date(2026, 5, 25), datetime.date(2026, 5, 26), datetime.date(2026, 5, 27), datetime.date(2026, 5, 28), datetime.date(2026, 5, 29)],
        'Water_Oz': [40, 80, 32, 96, 75],
        'Steps': [3000, 8000, 2500, 10000, 7000],
        'Pain_Scale': [8, 3, 9, 2, 4]
    })

# 2. Sidebar Layout for Data Entry (Inputs)
st.sidebar.header("📥 Log Today's Metrics")
with st.sidebar.form(key='log_form', clear_on_submit=True):
    log_date = st.date_input("Date", datetime.date.today())
    water = st.number_input("Water Intake (Ounces)", min_value=0, max_value=200, value=64)
    steps = st.number_input("Steps Per Day", min_value=0, max_value=50000, value=5000, step=500)
    pain = st.slider("Pain/Discomfort Level (1-10)", min_value=1, max_value=10, value=5)
    
    submit_button = st.form_submit_button(label='Submit Entry')

# Handle form submission to update our data
if submit_button:
    new_entry = pd.DataFrame({'Date': [log_date], 'Water_Oz': [water], 'Steps': [steps], 'Pain_Scale': [pain]})
    # Append data and reset index
    st.session_state.tracker_data = pd.concat([st.session_state.tracker_data, new_entry], ignore_index=True)
    st.success("Metrics logged successfully!")

# 3. Main Dashboard Layout (Visualizations)
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

# --- Physician Report Generator ---
st.write("---")
st.subheader("🧾 Physician Report")

start_date = df["Date"].min()
end_date = df["Date"].max()

avg_water = round(df["Water_Oz"].mean(), 1)
avg_steps = int(df["Steps"].mean())
avg_pain = round(df["Pain_Scale"].mean(), 1)

max_pain_row = df.loc[df["Pain_Scale"].idxmax()]
min_water_row = df.loc[df["Water_Oz"].idxmin()]

report_text = f"""
Hemorrhoid Symptom Summary
Date range: {start_date} to {end_date}

Tracked metrics:
- Average water intake: {avg_water} oz/day
- Average steps: {avg_steps:,}/day
- Average pain score: {avg_pain} / 10

Notable days:
- Highest pain: {int(max_pain_row['Pain_Scale'])} / 10 on {max_pain_row['Date']}
- Lowest water intake: {int(min_water_row['Water_Oz'])} oz on {min_water_row['Date']}

Clinical note:
- This is a patient-generated symptom summary for review.
- Persistent bleeding, worsening pain, or poor response to home care should be discussed with the clinician.
""".strip()

st.text_area("Physician Summary", report_text, height=220)

st.download_button(
    label="Download Physician Report (.txt)",
    data=report_text,
    file_name="hemorrhoid_physician_report.txt",
    mime="text/plain",
)