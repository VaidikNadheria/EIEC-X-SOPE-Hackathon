import streamlit as st
import pandas as pd
import datetime
import xml.etree.ElementTree as ET
import plotly.express as px

# Set up page config
st.set_page_config(page_title="Health Metrics Progression", layout="wide")
st.title("📈 Patient Lifestyle & Activity Progress")
st.write("Track daily progressions and toggle individual metrics in the chart legend to isolate trends.")

# 1. Initialize Mock Database (Purely Lifestyle Variables)
if 'lifestyle_data' not in st.session_state:
    st.session_state.lifestyle_data = pd.DataFrame({
        'Date': [datetime.date(2026, 5, 25), datetime.date(2026, 5, 26), datetime.date(2026, 5, 27), datetime.date(2026, 5, 28), datetime.date(2026, 5, 29)],
        'Water_Intake_Oz': [45, 80, 32, 90, 70],
        'Step_Count': [3200, 7500, 2100, 11000, 6800],
        'Active_Minutes': [15, 45, 10, 60, 30]
    })

# 2. Apple Health XML Parser
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

# 3. Sidebar Log Form
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

# 4. Preparing Visualizations
df = st.session_state.lifestyle_data.sort_values(by='Date')

# To allow a togglable interactive list, we "melt" the data from wide format to long format
df_melted = df.melt(id_vars=['Date'], 
                    value_vars=['Water_Intake_Oz', 'Step_Count', 'Active_Minutes'],
                    var_name='Metric', value_name='Value')

# Create a clean line plot over time where each metric has its own distinct color line
fig = px.line(df_melted, x='Date', y='Value', color='Metric', markers=True,
              title="Daily Multi-Metric Timeline Progression",
              labels={'Value': 'Logged Amount', 'Metric': 'Tracked Variables'})

# Customize interactions: Layout styling for clear hover data points
fig.update_layout(
    hovermode="x unified",
    legend=dict(
        title="Click to Toggle Variables:",
        orientation="h",  # Horizontal layout above/below chart
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    )
)

# Display Chart Natively in Streamlit
st.plotly_chart(fig, use_container_width=True)

# 5. Raw Data Inspection Option
if st.checkbox("Show historical table view"):
    st.dataframe(df)