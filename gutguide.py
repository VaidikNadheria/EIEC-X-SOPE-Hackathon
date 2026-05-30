import streamlit as st
import pandas as pd
import datetime
import calendar
import xml.etree.ElementTree as ET
import plotly.graph_objects as px_go

# Set up page config
st.set_page_config(page_title="Comprehensive Health Tracker", layout="wide")
st.title("📊 Unified Patient Symptoms & Lifestyle Tracker")

# 1. Initialize Database with a sample month of history (May 2026)
if 'comprehensive_data' not in st.session_state:
    st.session_state.comprehensive_data = pd.DataFrame({
        'Date': [
            datetime.date(2026, 5, 1), datetime.date(2026, 5, 4), datetime.date(2026, 5, 5),
            datetime.date(2026, 5, 12), datetime.date(2026, 5, 15), datetime.date(2026, 5, 18), 
            datetime.date(2026, 5, 22), datetime.date(2026, 5, 25), datetime.date(2026, 5, 28), 
            datetime.date(2026, 5, 29)
        ],
        'Water_Intake_Oz': [85, 40, 90, 30, 80, 45, 80, 32, 95, 70],
        'Step_Count': [8000, 3000, 9000, 2000, 7600, 3200, 7500, 2100, 11000, 6800],
        'Active_Minutes': [35, 10, 40, 0, 30, 15, 45, 10, 60, 30],
        'Pain_Scale': [2, 7, 1, 9, 3, 8, 3, 9, 2, 4],
        'Bleeding_Numeric': [0, 2, 0, 3, 0, 2, 0, 3, 0, 1]
    })

bleed_to_num = {"None": 0, "Mild (Spotting)": 1, "Moderate": 2, "Severe": 3}
num_to_bleed = {0: "None", 1: "Mild", 2: "Moderate", 3: "Severe"}

# 2. Apple Health XML Parser
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

# 3. Sidebar Configuration Forms
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
            st.sidebar.success(f"Extracted data for {log_date}!")
        except Exception:
            st.sidebar.error("Error reading data.")

st.sidebar.markdown("---")

with st.sidebar.form(key='master_metrics_form'):
    st.write(f"Logging metrics for: **{log_date}**")
    st.subheader("Lifestyle Inputs")
    water = st.number_input("Water Intake (Ounces)", min_value=0, max_value=250, value=64)
    steps = st.number_input("Step Count", min_value=0, max_value=100000, value=default_steps, step=500)
    active_time = st.number_input("Active Exercise (Minutes)", min_value=0, max_value=480, value=default_mins)
    
    st.subheader("Symptom Outputs")
    pain = st.slider("Pain/Discomfort Index (1-10)", min_value=1, max_value=10, value=4)
    bleeding_label = st.select_slider("Bleeding Event Severity", options=["None", "Mild (Spotting)", "Moderate", "Severe"], value="None")
    
    submit = st.form_submit_button("Save Master Entry")

if submit:
    new_entry = pd.DataFrame({
        'Date': [log_date], 'Water_Intake_Oz': [water], 'Step_Count': [steps],
        'Active_Minutes': [active_time], 'Pain_Scale': [pain], 'Bleeding_Numeric': [bleed_to_num[bleeding_label]]
    })
    st.session_state.comprehensive_data = st.session_state.comprehensive_data[st.session_state.comprehensive_data['Date'] != log_date]
    st.session_state.comprehensive_data = pd.concat([st.session_state.comprehensive_data, new_entry], ignore_index=True)
    st.success("Entry safely recorded!")

# 4. Process Benchmark Compliance Scores
df = st.session_state.comprehensive_data.sort_values(by='Date').copy()

def calculate_day_score(row):
    score = 0
    if row['Water_Intake_Oz'] >= 80: score += 1
    if row['Step_Count'] >= 7500: score += 1
    if row['Active_Minutes'] >= 30: score += 1
    return score

df['Score'] = df.apply(calculate_day_score, axis=1)

# 5. GENERATE THE NATIVE MONTHLY CALENDAR MATRIX
st.subheader(f"🗓️ Monthly Habit Compliance Calendar ({log_date.strftime('%B %Y')})")
st.write("🟢 **Green:** Perfect Day (3/3) | 🟡 **Yellow:** Minor Compliance Gap (1-2/3) | 🔴 **Red:** Major Compliance Gap (0/3) | ⚪ **Gray:** Unlogged Day")

# Build calendar coordinates for the selected log month
target_year = log_date.year
target_month = log_date.month

cal = calendar.Calendar(firstweekday=6) # 6 = Start week on Sunday
month_weeks = cal.monthdayscalendar(target_year, target_month)

# Prepare lists to feed our Plotly calendar graphic array matrix
days_of_week = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
weeks_labels = [f"Week {i+1}" for i in range(len(month_weeks))]

# Core storage grids for colors and numerical text labels
color_grid = []
text_grid = []

# Map our daily database entries into the structured coordinate calendar boxes
for week in month_weeks:
    color_row = []
    text_row = []
    for index, day_num in enumerate(week):
        if day_num == 0:
            # Day belongs to the previous/next month border
            color_row.append(None)
            text_row.append("")
        else:
            current_lookup_date = datetime.date(target_year, target_month, day_num)
            match = df[df['Date'] == current_lookup_date]
            
            text_row.append(f"<b>{day_num}</b>")
            
            if not match.empty:
                score = match['Score'].values[0]
                # Store numeric flags to color code map: 1 = Red, 2 = Yellow, 3 = Green
                if score == 3: color_row.append(3)
                elif score in [1, 2]: color_row.append(2)
                else: color_row.append(1)
            else:
                # Unlogged, empty data placeholder color code
                color_row.append(0)
                
    color_grid.append(color_row)
    text_grid.append(text_row)

# Invert calendar row structures vertically so Week 1 renders neatly at the top of the grid
color_grid.reverse()
text_grid.reverse()
weeks_labels.reverse()

# Render Calendar Heatmap using a categorical discrete color matrix map
calendar_fig = px_go.Figure(data=px_go.Heatmap(
    z=color_grid,
    x=days_of_week,
    y=weeks_labels,
    text=text_grid,
    texttemplate="%{text}",
    textfont={"size": 16, "color": "black"},
    colorscale=[
        [0.0, '#e5e7eb'],  # 0 = Light Gray (Unlogged)
        [0.25, '#e5e7eb'],
        [0.25, '#fc8d62'], # 1 = Soft Red (0/3 Goals)
        [0.5, '#fc8d62'],
        [0.5, '#ffd92f'],  # 2 = Yellow (1-2/3 Goals)
        [0.75, '#ffd92f'],
        [0.75, '#66c2a5'], # 3 = Emerald Green (3/3 Goals)
        [1.0, '#66c2a5']
    ],
    showscale=False,
    xgap=4,
    ygap=4
))

calendar_fig.update_layout(
    height=320,
    margin=dict(l=40, r=40, t=10, b=10),
    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, fixedrange=True),
    xaxis=dict(showgrid=False, zeroline=False, position=1, side="top", fixedrange=True)
)

st.plotly_chart(calendar_fig, use_container_width=True)

st.write("---")

# 6. Constructing the Line Graph
st.subheader("📈 Live Correlation Trends")
fig = px_go.Figure()

fig.add_trace(px_go.Scatter(x=df['Date'], y=df['Step_Count'], name='Step Count', mode='lines+markers', line=dict(color='#1f77b4', width=3)))
fig.add_trace(px_go.Scatter(x=df['Date'], y=df['Water_Intake_Oz'], name='Water Intake (Oz)', mode='lines+markers', line=dict(color='#aec7e8', width=3)))
fig.add_trace(px_go.Scatter(x=df['Date'], y=df['Active_Minutes'], name='Active Exercise (Min)', mode='lines+markers', line=dict(color='#2ca02c', width=3)))
fig.add_trace(px_go.Scatter(x=df['Date'], y=df['Pain_Scale'], name='Pain Level (1-10)', mode='lines+markers', yaxis='y2', line=dict(color='#d62728', width=4, dash='dot')))
fig.add_trace(px_go.Scatter(x=df['Date'], y=df['Bleeding_Numeric'], name='Bleeding Level (0-3)', mode='lines+markers', yaxis='y2', line=dict(color='#9467bd', width=4, dash='dashdot')))

fig.update_layout(
    xaxis=dict(title="Timeline History"),
    yaxis=dict(title=dict(text="Lifestyle Scale (Steps/Water/Time)", font=dict(color="#1f77b4")), tickfont=dict(color="#1f77b4")),
    yaxis2=dict(title=dict(text="Symptom Scale (Pain/Bleeding)", font=dict(color="#d62728")), tickfont=dict(color="#d62728"), anchor="x", overlaying="y", side="right", range=[0, 10.5]),
    hovermode="x unified",
    legend=dict(title="<b>Interactive Display Legend</b>", orientation="h", yanchor="bottom", y=-0.4, xanchor="center", x=0.5)
)

st.plotly_chart(fig, use_container_width=True)

# 7. Diagnostic History Table
if st.checkbox("Show diagnostic history table"):
    readable_df = df.copy()
    readable_df['Bleeding_Level'] = readable_df['Bleeding_Numeric'].map(num_to_bleed)
    st.dataframe(readable_df[['Date', 'Water_Intake_Oz', 'Step_Count', 'Active_Minutes', 'Pain_Scale', 'Bleeding_Level']])