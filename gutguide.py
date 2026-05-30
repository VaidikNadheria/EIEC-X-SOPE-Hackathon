# %%writefile gutguide.py

import streamlit as st
import pandas as pd
import datetime
import calendar
import xml.etree.ElementTree as ET
import plotly.graph_objects as px_go
import plotly.express as px
import google.generativeai as genai
import json

# 1. AI Gemini API Configuration
# Replace with your secure environment variable or key in production
genai.configure(api_key="AQ.Ab8RN6JoTSZD9sSyfE_rTGmoDCrnhaq8SwOKzMWY3Kd43N1t_A")
model = genai.GenerativeModel("gemini-2.5-flash")

# App Configuration Setup
st.set_page_config(page_title="Comprehensive Health Tracker", layout="wide")
st.title("🌾 Unified Symptoms, Lifestyle & AI Fiber Tracker")

# 2. Initialize Session State Databases
if 'comprehensive_data' not in st.session_state:
    st.session_state.comprehensive_data = pd.DataFrame({
        'Date': [
            datetime.date(2026, 5, 25), datetime.date(2026, 5, 26), 
            datetime.date(2026, 5, 27), datetime.date(2026, 5, 28), 
            datetime.date(2026, 5, 29)
        ],
        'Water_Intake_Oz': [40, 80, 32, 96, 75],
        'Step_Count': [3000, 8000, 2500, 10000, 7000],
        'Active_Minutes': [15, 45, 10, 60, 30],
        'Pain_Scale': [8, 3, 9, 2, 4],
        'Bleeding_Numeric': [2, 0, 3, 0, 1], # 0: None, 1: Mild, 2: Moderate, 3: Severe
        'Total_Fiber_g': [12.0, 26.5, 8.0, 31.0, 18.5]
    })

if 'fiber_log' not in st.session_state:
    st.session_state.fiber_log = pd.DataFrame({
        'Date': [datetime.date(2026, 5, 25), datetime.date(2026, 5, 26)],
        'Food': ["Oatmeal", "Apple with Skin"],
        'Total_Fiber': [4.0, 4.4],
        'Soluble_Fiber': [2.0, 1.2],
        'Insoluble_Fiber': [2.0, 3.2]
    })

bleed_to_num = {"None": 0, "Mild (Spotting)": 1, "Moderate": 2, "Severe": 3}
num_to_bleed = {0: "None", 1: "Mild", 2: "Moderate", 3: "Severe"}

# Navigation Options
page = st.sidebar.radio("Navigation", ["Home & Analytics", "Fiber Insights Details"])

# 3. Apple Health XML Parser Engine
def parse_apple_health_xml(xml_file, target_date):
    target_date_str = target_date.strftime("%Y-%m-%d")
    total_steps, active_mins = 0, 0
    context = ET.iterparse(xml_file, events=('end',))
    for event, elem in context:
        if elem.tag == 'Record':
            creation_date = elem.get('creationDate', '')
            if creation_date.startswith(target_date_str):
                record_type = elem.get('type', '')
                if record_type == 'HKQuantityTypeIdentifierStepCount':
                    try: total_steps += int(float(elem.get('value', 0)))
                    except ValueError: pass
                elif record_type == 'HKQuantityTypeIdentifierAppleExerciseTime':
                    try: active_mins += int(float(elem.get('value', 0)))
                    except ValueError: pass
        elem.clear()
    return total_steps, active_mins

# 4. Sidebar Unified Entry Form
st.sidebar.header("📥 Data Entry Portal")
log_date = st.sidebar.date_input("Select Target Date", datetime.date.today())

st.sidebar.markdown("---")
st.sidebar.subheader("Automate via Apple Health")
uploaded_file = st.sidebar.file_uploader("Upload export.xml", type=["xml"])

default_steps, default_mins = 5000, 20
if uploaded_file is not None:
    with st.spinner("Processing XML data..."):
        try:
            uploaded_file.seek(0)
            parsed_steps, parsed_mins = parse_apple_health_xml(uploaded_file, log_date)
            default_steps, default_mins = int(parsed_steps), int(parsed_mins)
            st.sidebar.success(f"Extracted device metrics for {log_date}!")
        except Exception:
            st.sidebar.error("Error processing XML file automation.")

st.sidebar.markdown("---")

with st.sidebar.form(key='master_metrics_form'):
    st.write(f"Logging metrics for: **{log_date}**")
    
    st.subheader("Lifestyle Inputs")
    water = st.number_input("Water Intake (Ounces)", min_value=0, max_value=250, value=64)
    steps = st.number_input("Step Count", min_value=0, max_value=100000, value=default_steps, step=500)
    active_time = st.number_input("Active Exercise (Minutes)", min_value=0, max_value=480, value=default_mins)
    
    st.subheader("AI Dietary Fiber Logger")
    food = st.text_input("🍎 Food Consumed", placeholder="e.g., Avocado toast, Chia pudding")
    
    st.subheader("Symptom Outputs")
    pain = st.slider("Pain/Discomfort Index (1-10)", min_value=1, max_value=10, value=4)
    bleeding_label = st.select_slider("Bleeding Event Severity", options=["None", "Mild (Spotting)", "Moderate", "Severe"], value="None")
    
    submit = st.form_submit_button("Save Entry Metrics")

# 5. Form Processing & AI Graph Appends
if submit:
    # A. Process AI Fiber estimation if a food item was entered
    calculated_fiber = 0.0
    if food:
        prompt = f"""
Food item: {food}
Return ONLY valid JSON. Keep formatting exact.

{{
  "food": "{food}",
  "total_fiber": 0,
  "soluble_fiber": 0,
  "insoluble_fiber": 0
}}
"""
        try:
            response = model.generate_content(prompt)
            clean = response.text.replace("```json", "").replace("```", "").strip()
            fiber_data = json.loads(clean)
            
            # Record individual item log
            fiber_entry = pd.DataFrame({
                "Date": [log_date],
                "Food": [fiber_data["food"]],
                "Total_Fiber": [float(fiber_data["total_fiber"])],
                "Soluble_Fiber": [float(fiber_data["soluble_fiber"])],
                "Insoluble_Fiber": [float(fiber_data["insoluble_fiber"])]
            })
            st.session_state.fiber_log = pd.concat([st.session_state.fiber_log, fiber_entry], ignore_index=True)
            calculated_fiber = float(fiber_data["total_fiber"])
        except Exception as e:
            st.error(f"AI Fiber Estimation Error: {e}")

    # B. Calculate total fiber for this date across all logs to save to time series
    day_fiber_df = st.session_state.fiber_log[st.session_state.fiber_log['Date'] == log_date]
    cumulative_day_fiber = day_fiber_df['Total_Fiber'].sum() + calculated_fiber

    # C. Update the Master Timeline Database
    new_entry = pd.DataFrame({
        'Date': [log_date],
        'Water_Intake_Oz': [water],
        'Step_Count': [steps],
        'Active_Minutes': [active_time],
        'Pain_Scale': [pain],
        'Bleeding_Numeric': [bleed_to_num[bleeding_label]],
        'Total_Fiber_g': [cumulative_day_fiber]
    })
    
    st.session_state.comprehensive_data = st.session_state.comprehensive_data[st.session_state.comprehensive_data['Date'] != log_date]
    st.session_state.comprehensive_data = pd.concat([st.session_state.comprehensive_data, new_entry], ignore_index=True)
    st.success(f"Metrics effectively recorded for {log_date}!")

# Load DataFrames for rendering
df = st.session_state.comprehensive_data.sort_values(by='Date').copy()
fiber_df = st.session_state.fiber_log

# Compute Dynamic Metric Flags
def calculate_day_score(row):
    score = 0
    if row['Water_Intake_Oz'] >= 80: score += 1
    if row['Step_Count'] >= 7500: score += 1
    if row['Total_Fiber_g'] >= 25: score += 1  # Swapped active time for fiber target benchmark
    return score

df['Score'] = df.apply(calculate_day_score, axis=1)

# --- PAGE 1: HOME & GENERAL ANALYTICS ---
if page == "Home & Analytics":
    
    # KPIs Ribbon
    if not df.empty:
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.metric("Latest Pain Score", f"{df['Pain_Scale'].iloc[-1]}/10")
        with col2: st.metric("Latest Water Intake", f"{df['Water_Intake_Oz'].iloc[-1]} oz")
        with col3: st.metric("Latest Daily Steps", f"{int(df['Step_Count'].iloc[-1]):,}")
        with col4: st.metric("Latest Fiber Logged", f"{df['Total_Fiber_g'].iloc[-1]:.1f} g")

    st.write("---")
    
    # A. Custom Monthly Calendar Heatmap Component
    st.subheader(f"🗓️ Lifestyle Compliance Heatmap Calendar ({log_date.strftime('%B %Y')})")
    st.write("🟢 **Green:** Excellent Compliance (3/3 Goals) | 🟡 **Yellow:** Minor Gap (1-2/3) | 🔴 **Red:** Critical Gap (0/3) | ⚪ **Gray:** Unlogged Day")
    st.caption("Benchmarks: Water $\ge$ 80oz, Steps $\ge$ 7,500, Fiber Content $\ge$ 25g")
    
    target_year, target_month = log_date.year, log_date.month
    cal = calendar.Calendar(firstweekday=6)
    month_weeks = cal.monthdayscalendar(target_year, target_month)
    
    days_of_week = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    weeks_labels = [f"Week {i+1}" for i in range(len(month_weeks))]
    color_grid, text_grid = [], []

    for week in month_weeks:
        color_row, text_row = [], []
        for index, day_num in enumerate(week):
            if day_num == 0:
                color_row.append(None); text_row.append("")
            else:
                current_lookup_date = datetime.date(target_year, target_month, day_num)
                match = df[df['Date'] == current_lookup_date]
                text_row.append(f"<b>{day_num}</b>")
                if not match.empty:
                    score = match['Score'].values[0]
                    if score == 3: color_row.append(3)
                    elif score in [1, 2]: color_row.append(2)
                    else: color_row.append(1)
                else:
                    color_row.append(0)
        color_grid.append(color_row); text_grid.append(text_row)

    color_grid.reverse(); text_grid.reverse(); weeks_labels.reverse()

    calendar_fig = px_go.Figure(data=px_go.Heatmap(
        z=color_grid, x=days_of_week, y=weeks_labels, text=text_grid,
        texttemplate="%{text}", textfont={"size": 15, "color": "black"},
        colorscale=[
            [0.0, '#e5e7eb'], [0.25, '#e5e7eb'], # Unlogged
            [0.25, '#fc8d62'], [0.5, '#fc8d62'],  # Red
            [0.5, '#ffd92f'], [0.75, '#ffd92f'],  # Yellow
            [0.75, '#66c2a5'], [1.0, '#66c2a5']   # Green
        ],
        showscale=False, xgap=4, ygap=4
    ))
    calendar_fig.update_layout(height=280, margin=dict(l=40, r=40, t=10, b=10),
                              yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, fixedrange=True),
                              xaxis=dict(showgrid=False, zeroline=False, position=1, side="top", fixedrange=True))
    st.plotly_chart(calendar_fig, use_container_width=True)

    st.write("---")

    # B. Interactive Multi-Metric Line Graph Component (Now Includes Fiber!)
    st.subheader("📈 Interactive Diagnostic & Lifestyle Trends")
    fig = px_go.Figure()
    
    # Left Axis Plots
    fig.add_trace(px_go.Scatter(x=df['Date'], y=df['Step_Count'], name='Step Count', mode='lines+markers', line=dict(color='#1f77b4', width=3)))
    fig.add_trace(px_go.Scatter(x=df['Date'], y=df['Water_Intake_Oz'], name='Water Intake (Oz)', mode='lines+markers', line=dict(color='#aec7e8', width=3)))
    fig.add_trace(px_go.Scatter(x=df['Date'], y=df['Active_Minutes'], name='Active Exercise (Min)', mode='lines+markers', line=dict(color='#2ca02c', width=3)))
    fig.add_trace(px_go.Scatter(x=df['Date'], y=df['Total_Fiber_g'], name='Total Fiber (g)', mode='lines+markers', line=dict(color='#ff7f0e', width=3)))
    
    # Right Axis Plots
    fig.add_trace(px_go.Scatter(x=df['Date'], y=df['Pain_Scale'], name='Pain Level (1-10)', mode='lines+markers', yaxis='y2', line=dict(color='#d62728', width=4, dash='dot')))
    fig.add_trace(px_go.Scatter(x=df['Date'], y=df['Bleeding_Numeric'], name='Bleeding Level (0-3)', mode='lines+markers', yaxis='y2', line=dict(color='#9467bd', width=4, dash='dashdot')))

    fig.update_layout(
        xaxis=dict(title="Timeline History"),
        yaxis=dict(title=dict(text="Lifestyle Scales", font=dict(color="#1f77b4")), tickfont=dict(color="#1f77b4")),
        yaxis2=dict(title=dict(text="Clinical Symptom Scales", font=dict(color="#d62728")), tickfont=dict(color="#d62728"), anchor="x", overlaying="y", side="right", range=[0, 10.5]),
        hovermode="x unified",
        legend=dict(title="<b>Interactive Display Legend</b><br><i>Click entries to isolate metrics:</i>", orientation="h", yanchor="bottom", y=-0.4, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig, use_container_width=True)

    # C. AI Assistant Personal Recommendations Block
    current_day_fiber = df['Total_Fiber_g'].iloc[-1] if not df.empty else 0
    if current_day_fiber > 0:
        st.write("---")
        st.subheader("🤖 Personalized AI Insights")
        rec_prompt = f"Current Fiber Intake: {current_day_fiber:.1f}g. Target: 25g. Provide short food, hydration, and lifestyle advice under 50 words tailored for regular bowel health."
        try:
            rec_response = model.generate_content(rec_prompt)
            st.info(rec_response.text)
        except Exception as e:
            st.caption(f"Recommendations unretrievable: {e}")

    # Raw Master Logs Table Option
    if st.checkbox("Show diagnostic master history table"):
        readable_df = df.copy()
        readable_df['Bleeding_Level'] = readable_df['Bleeding_Numeric'].map(num_to_bleed)
        st.dataframe(readable_df[['Date', 'Water_Intake_Oz', 'Step_Count', 'Active_Minutes', 'Total_Fiber_g', 'Pain_Scale', 'Bleeding_Level']])

# --- PAGE 2: FIBER INSIGHTS DETAILS ---
else:
    st.title("🌾 Deep Fiber Insights Dashboard")
    
    # Summing calculations across our fiber logging frame
    total_fiber = fiber_df["Total_Fiber"].sum() if not fiber_df.empty else 0.0
    total_soluble = fiber_df["Soluble_Fiber"].sum() if not fiber_df.empty else 0.0
    total_insoluble = fiber_df["Insoluble_Fiber"].sum() if not fiber_df.empty else 0.0
    
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("Cumulative Total Fiber", f"{total_fiber:.1f} g")
    with col2: st.metric("Total Soluble Fiber", f"{total_soluble:.1f} g")
    with col3: st.metric("Total Insoluble Fiber", f"{total_insoluble:.1f} g")
    
    st.write("---")
    st.subheader("Dietary Food Entry Logs")
    st.dataframe(fiber_df, use_container_width=True)
    
    if not fiber_df.empty:
        fig_bar = px.bar(
            fiber_df, x="Food", y="Total_Fiber", color="Food",
            title="Fiber Gram Contribution by Logged Item",
            labels={"Total_Fiber": "Fiber Weight (grams)"}
        )
        st.plotly_chart(fig_bar, use_container_width=True)