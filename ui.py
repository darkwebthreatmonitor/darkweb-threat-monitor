import streamlit as st
import pandas as pd
import numpy as np
import io
import base64

# --- Utility Functions ---

# Function to convert DataFrame to CSV for download
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# Function to generate a dummy PDF report content (as Streamlit doesn't support PDF generation natively)
# In a real application, you would use a library like FPDF or ReportLab here.
def generate_pdf_report(organization_name, log_data):
    # This is a placeholder for actual PDF generation logic
    report_text = f"""
    --- Dark Web Threat Monitoring Report for {organization_name} ---

    Summary: 
    Total Threats: 457
    Critical Alerts: 15
    New Alerts (24h): 32

    Detailed Log Snippet:
    {log_data.to_string()}

    Note: This is a simulated report. For a full PDF, complex libraries are needed.
    """
    return report_text.encode('utf-8')

# --- Data Simulation Functions (Org-Specific) ---

def get_key_metrics(org_name):
    # Simple simulation: metrics change based on the organization name
    if org_name == "GlobalTech Inc.":
        return 457, 32, 15
    elif org_name == "SecureBank":
        return 210, 8, 5
    else:
        return 50, 2, 1

def get_threat_data(org_name):
    if org_name == "SecureBank":
        return pd.DataFrame({
            'Threat Type': ['Credential Leak', 'Impersonation', 'Phishing Kit', 'Fake Job Site'],
            'Count': [110, 50, 30, 20] 
        })
    else: # Default or GlobalTech Inc.
        return pd.DataFrame({
            'Threat Type': ['Credential Leak', 'Impersonation', 'Phishing Kit', 'Fake Job Site'],
            'Count': [90, 120, 60, 45] 
        })

def get_alerts(org_name):
    if org_name == "SecureBank":
        return [
            ("error", f"💥 **CRITICAL:** Large SQL dump of customer data found on forum."),
            ("warning", f"⚠️ **MEDIUM:** Phishing kit targeting '{org_name}' found."),
            ("info", f"✅ **LOW:** No critical new threats detected in the last 12 hours.")
        ]
    else:
        return [
            ("error", f"💡 **CRITICAL:** New brand impersonation detected for '{org_name}'. Contact legal team."),
            ("warning", f"⚠️ **HIGH:** 500+ user credentials leaked on forum."),
            ("warning", f"⚠️ **MEDIUM:** Phishing kit targeting '{org_name}' found."),
            ("info", f"✅ **LOW:** New fake job posting on dark web.")
        ]

def get_log_data(org_name):
    return pd.DataFrame({
        'Timestamp': ['2023-10-26 10:30', '2023-10-26 09:45', '2023-10-26 09:40', '2023-10-26 09:00', '2023-10-25 18:00'],
        'Threat Type': ['Credential Leak', 'Impersonation Leak', 'Phishing Kit', 'Credential Leak', 'Fake Job Site'],
        'Severity': ['CRITICAL', 'HIGH', 'MEDIUM', 'HIGH', 'LOW'],
        'Description': [
            f'Full user table snippet leaked (Org: {org_name})', 
            f'Fake login portal at mirrotech.onion', 
            f'New phishing kit targeting {org_name} logo found',
            '500+ user credentials leaked on forum', 
            'Job scam link posted on RAMP'
        ],
        'Source URL': [
            'http://ramblers.onion/leak', 
            'http://mirrotech.onion/fake_site', 
            'http://shadowdrop.onion/phish', 
            'http://leaks.onion/users', 
            'http://hireme.onion/jobs'
        ]
    })

# --- Streamlit UI Layout ---

# Set page configuration
st.set_page_config(page_title="Dark Web Threat Monitoring Dashboard", layout="wide")

# --- Sidebar and Organization Selection ---
with st.sidebar:
    st.title("Proactive Cyber Insights")
    st.header("DarkSight Crawler")
    
    # ORGANIZATION SELECTION - Makes the app organization-specific
    organization_options = ["GlobalTech Inc.", "SecureBank", "Acme University"]
    selected_org = st.selectbox(
        "Select Organization to Monitor",
        options=organization_options
    )

    st.subheader("Navigation")
    st.radio("Go to", ["Dashboard", "Crawler Settings", "Reports", "Team"])

# --- Main Dashboard Content ---

st.title(f"Dark Web Threat Monitoring Dashboard: {selected_org}")

# Export Report Button with Dynamic Download
total_threats, new_threats, critical_severity = get_key_metrics(selected_org)
log_data_df = get_log_data(selected_org)

# Create a container for the export button to place it high up
export_col, _ = st.columns([1, 4]) 
with export_col:
    # CSV Download Button
    csv = convert_df_to_csv(log_data_df)
    st.download_button(
        label="Download Full Log (.csv)",
        data=csv,
        file_name=f'{selected_org}_threat_log.csv',
        mime='text/csv',
        key='download_csv'
    )
    
    # PDF Placeholder Download Button (Actual PDF generation is complex)
    pdf_content = generate_pdf_report(selected_org, log_data_df)
    st.download_button(
        label="Generate Summary Report (.txt)", # Using .txt as placeholder for PDF
        data=pdf_content,
        file_name=f'{selected_org}_summary_report.txt',
        mime='application/octet-stream',
        key='download_pdf'
    )


# Key Metric Cards
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Threats Found", f"{total_threats}")
with col2:
    st.metric("New Threats (Last 24h)", f"{new_threats}")
with col3:
    st.metric("Critical Severity", f"{critical_severity}")
st.markdown("---")

# Charts and Alerts Columns
col_charts, col_alerts = st.columns([2, 1])

# Threats by Type Bar Chart
with col_charts:
    st.header("Threats by Type")
    threat_data = get_threat_data(selected_org)
    # Using st.bar_chart with dynamic data and colors
    st.bar_chart(
        threat_data, 
        x='Threat Type', 
        y='Count', 
        color='#008080', # Teal color for bars
        use_container_width=True
    )

    # Threat Trend Line Chart (Simulated)
    st.header("Threat Trend (Last 30 Days)")
    # Generate cumulative random data for a rising trend effect
    trend_data = pd.DataFrame(np.cumsum(np.random.randint(-1, 3, size=30)), columns=['Threats'])
    trend_data['Day'] = range(1, 31)
    
    st.line_chart(
        trend_data, 
        x='Day', 
        y='Threats', 
        color="#FFA500", # Orange color for line
        use_container_width=True
    )

# Alerts and Notifications
with col_alerts:
    st.header("Alerts & Notifications")
    alerts_list = get_alerts(selected_org)
    
    for alert_type, message in alerts_list:
        if alert_type == "error":
            st.error(message)
        elif alert_type == "warning":
            st.warning(message)
        else:
            st.info(message)
    
# Detailed Threat Log
st.markdown("---")
st.subheader("Detailed Threat Log")

st.dataframe(
    log_data_df,
    use_container_width=True,
    hide_index=True
)

st.markdown(f"---")
st.caption(f"Powered by Python & Tor. Data for: {', '.join(['Diya', 'Jithin', 'Levana', 'Mathew'])}")
