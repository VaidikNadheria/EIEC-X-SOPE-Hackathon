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

# Updated Sidebar Layout for Data Entry (Inputs)
st.sidebar.header("📥 Log Today's Metrics")
with st.sidebar.form(key='log_form', clear_on_submit=True):
    log_date = st.date_input("Date", datetime.date.today())
    
    # Existing metrics
    water = st.number_input("Water Intake (Ounces)", min_value=0, max_value=200, value=64)
    steps = st.number_input("Steps Per Day", min_value=0, max_value=50000, value=5000, step=500)
    pain = st.slider("Pain/Discomfort Level (1-10)", min_value=1, max_value=10, value=5)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("New GI & Activity Metrics")
    
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

# Handle form submission to update your data structure
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