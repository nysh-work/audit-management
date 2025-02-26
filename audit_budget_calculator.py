import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import io
import base64
import json
import os

# Define color palette - Medium-inspired dark mode
COLOR_PRIMARY = "#1e88e5"       # Primary blue
COLOR_SECONDARY = "#00e676"     # Success green
COLOR_WARNING = "#ff9800"       # Warning orange
COLOR_DANGER = "#f44336"        # Danger red
COLOR_BACKGROUND = "#121212"    # Main background
COLOR_CARD_BACKGROUND = "#1e1e1e"  # Lighter background for cards
COLOR_TEXT = "#e6e6e6"          # Main text color
COLOR_TEXT_MUTED = "#9e9e9e"    # Muted text color

# Set page config
st.set_page_config(
    page_title="Statutory Audit Budget Calculator & Time Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom theme
def apply_custom_theme():
    # Medium-inspired dark theme
    st.markdown("""
    <style>
        /* Main background and text colors */
        .stApp {
            background-color: #121212;
            color: #e6e6e6;
        }
        
        /* Headers */
        h1, h2, h3, h4, h5, h6 {
            color: #f0f0f0 !important;
            font-family: 'Arial', sans-serif;
        }
        
        /* Metrics */
        .css-1xarl3l, .css-1offfwp, [data-testid="stMetricValue"] {
            background-color: #1e1e1e;
            border: 1px solid #333333;
            border-radius: 5px;
            padding: 10px;
            color: #f0f0f0 !important;
        }
        
        /* Metric delta colors */
        [data-testid="stMetricDelta"] svg {
            stroke: #00e676 !important;
        }
        
        [data-testid="stMetricDelta"] [data-testid="stMetricDelta"] svg {
            stroke: #f44336 !important;
        }
        
        /* Tables */
        .stDataFrame {
            background-color: #1e1e1e;
        }
        
        .stDataFrame table {
            border: 1px solid #333333;
        }
        
        .stDataFrame th {
            background-color: #2d2d2d !important;
            color: #e6e6e6 !important;
            font-weight: 600;
            border-bottom: 1px solid #444444 !important;
        }
        
        .stDataFrame td {
            color: #e6e6e6 !important;
            border-bottom: 1px solid #333333 !important;
            background-color: #1e1e1e !important;
        }
        
        /* Buttons */
        .stButton button {
            background-color: #1e88e5 !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 5px !important;
            padding: 5px 15px !important;
            transition: background-color 0.3s !important;
        }
        
        .stButton button:hover {
            background-color: #1565c0 !important;
        }
        
        /* Input fields */
        .stTextInput input, .stNumberInput input, .stDateInput input {
            background-color: #2d2d2d !important;
            color: #e6e6e6 !important;
            border: 1px solid #444444 !important;
            border-radius: 5px !important;
        }
        
        /* Select boxes */
        .stSelectbox > div > div {
            background-color: #2d2d2d !important;
            color: #e6e6e6 !important;
            border: 1px solid #444444 !important;
            border-radius: 5px !important;
        }
        
        /* Dropdowns */
        .stSelectbox > div > div > div {
            background-color: #2d2d2d !important;
            color: #e6e6e6 !important;
        }
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            background-color: #1a1a1a !important;
            border-radius: 5px !important;
            padding: 5px !important;
        }
        
        .stTabs [data-baseweb="tab"] {
            color: #e6e6e6 !important;
            border-radius: 5px !important;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: #1e88e5 !important;
            color: white !important;
        }
        
        /* Expanders */
        .streamlit-expanderHeader {
            background-color: #1e1e1e !important;
            color: #e6e6e6 !important;
            border-radius: 5px !important;
        }
        
        .streamlit-expanderContent {
            background-color: #1a1a1a !important;
            border: 1px solid #333333 !important;
            border-radius: 0 0 5px 5px !important;
        }
        
        /* Checkboxes */
        .stCheckbox > div > div > div {
            background-color: #1e88e5 !important;
        }
        
        /* Radio buttons */
        .stRadio > div {
            background-color: transparent !important;
        }
        
        .stRadio label {
            color: #e6e6e6 !important;
        }
        
        /* Sidebar */
        [data-testid="stSidebar"] {
            background-color: #1a1a1a !important;
            border-right: 1px solid #333333 !important;
        }
        
        [data-testid="stSidebar"] hr {
            border-color: #333333 !important;
        }
        
        /* Info, warning and error boxes */
        .stInfo, .stSuccess {
            background-color: rgba(30, 136, 229, 0.2) !important;
            color: #e6e6e6 !important;
            border-left-color: #1e88e5 !important;
        }
        
        .stWarning {
            background-color: rgba(255, 152, 0, 0.2) !important;
            color: #e6e6e6 !important;
            border-left-color: #ff9800 !important;
        }
        
        .stError {
            background-color: rgba(244, 67, 54, 0.2) !important;
            color: #e6e6e6 !important;
            border-left-color: #f44336 !important;
        }
        
        /* Box shadows for cards */
        div.row-widget.stButton {
            box-shadow: rgba(0, 0, 0, 0.2) 0px 2px 4px !important;
        }
        
        /* Medium-like typography */
        body {
            font-family: 'Charter', 'Georgia', serif !important;
            line-height: 1.8 !important;
        }
        
        /* Custom card styling */
        .custom-card {
            background-color: #1e1e1e;
            border-radius: 10px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            border: 1px solid #333;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        .card-title {
            color: #f0f0f0;
            font-family: 'Arial', sans-serif;
            font-size: 1.3rem;
            margin-bottom: 1rem;
        }
        
        /* File uploader */
        .uploadedFile {
            background-color: #2d2d2d !important;
            color: #e6e6e6 !important;
            border: 1px solid #444444 !important;
        }
        
        /* Slider */
        .stSlider div[data-baseweb="slider"] div {
            background-color: #1e88e5 !important;
        }
        
        /* Pagination buttons */
        .stPagination button {
            background-color: #1e1e1e !important;
            color: #e6e6e6 !important;
            border: 1px solid #333333 !important;
        }
        
        .stPagination button:hover {
            background-color: #1e88e5 !important;
        }
    </style>
    """, unsafe_allow_html=True)

# Apply the custom theme
apply_custom_theme()

# Function to create a styled card container
def styled_card(title, content):
    st.markdown(f"""
    <div class="custom-card">
        <h3 class="card-title">{title}</h3>
        {content}
    </div>
    """, unsafe_allow_html=True)

# Initialize session state for storing data
if 'projects' not in st.session_state:
    st.session_state.projects = {}

if 'time_entries' not in st.session_state:
    st.session_state.time_entries = []

if 'current_project' not in st.session_state:
    st.session_state.current_project = None

if 'theme' not in st.session_state:
    st.session_state.theme = 'dark'

# Function to toggle theme
def toggle_theme():
    st.session_state.theme = 'light' if st.session_state.theme == 'dark' else 'dark'
    st.rerun()

# Theme toggle in sidebar
with st.sidebar:
    st.title("Audit Management")
    st.button('Toggle Light/Dark Mode', on_click=toggle_theme)
    st.divider()

# Function to save data to files
def save_data():
    # Save projects
    with open('projects.json', 'w') as f:
        json.dump(st.session_state.projects, f)
    
    # Save time entries
    df = pd.DataFrame(st.session_state.time_entries)
    if not df.empty:
        df.to_csv('time_entries.csv', index=False)

# Function to load data from files
def load_data():
    try:
        # Load projects
        if os.path.exists('projects.json'):
            with open('projects.json', 'r') as f:
                st.session_state.projects = json.load(f)
        
        # Load time entries
        if os.path.exists('time_entries.csv'):
            df = pd.read_csv('time_entries.csv')
            st.session_state.time_entries = df.to_dict('records')
    except Exception as e:
        st.error(f"Error loading data: {e}")

# Try to load data at startup
try:
    load_data()
except:
    # First run or file doesn't exist yet
    pass

# Title and navigation
st.title("Statutory Audit Budget Calculator & Time Tracker")

# Create tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["Budget Calculator", "Time Tracking", "Project Reports", "Team Reports"])

# Define industry sector definitions and factors
industry_sectors = {
    "MFG": {"name": "Manufacturing", "factor": 1.0},
    "TRD": {"name": "Trading", "factor": 0.9},
    "SER": {"name": "Services", "factor": 0.95},
    "FIN": {"name": "Financial Services", "factor": 1.3},
    "REC": {"name": "Real Estate and Construction", "factor": 1.2},
    "NGO": {"name": "Not for profit", "factor": 0.85}
}

# Detailed time estimates based on size and sector (same as in the original code)
detailed_time_estimates = {
    # Small category
    "SMFG": {"planning": 72, "fieldwork": 288, "managerReview": 72, "partnerReview": 48, "total": 480},
    "STRD": {"planning": 48, "fieldwork": 240, "managerReview": 48, "partnerReview": 24, "total": 360},
    "SSER": {"planning": 48, "fieldwork": 240, "managerReview": 48, "partnerReview": 24, "total": 360},
    "SREC": {"planning": 72, "fieldwork": 288, "managerReview": 72, "partnerReview": 48, "total": 480},
    
    # Medium category
    "MMFG": {"planning": 120, "fieldwork": 336, "managerReview": 72, "partnerReview": 72, "total": 600},
    "MTRD": {"planning": 72, "fieldwork": 288, "managerReview": 72, "partnerReview": 48, "total": 480},
    "MSER": {"planning": 72, "fieldwork": 288, "managerReview": 72, "partnerReview": 48, "total": 480},
    "MFIN": {"planning": 120, "fieldwork": 336, "managerReview": 72, "partnerReview": 72, "total": 600},
    "MREC": {"planning": 120, "fieldwork": 336, "managerReview": 72, "partnerReview": 72, "total": 600},
    
    # Large category
    "LMFG": {"planning": 120, "fieldwork": 528, "managerReview": 96, "partnerReview": 96, "total": 840},
    "LTRD": {"planning": 72, "fieldwork": 360, "managerReview": 72, "partnerReview": 96, "total": 600},
    "LSER": {"planning": 72, "fieldwork": 360, "managerReview": 72, "partnerReview": 96, "total": 600},
    "LFIN": {"planning": 120, "fieldwork": 480, "managerReview": 120, "partnerReview": 120, "total": 840},
    "LREC": {"planning": 120, "fieldwork": 480, "managerReview": 120, "partnerReview": 120, "total": 840},
    
    # Very Large category
    "VLMFG": {"planning": 120, "fieldwork": 600, "managerReview": 120, "partnerReview": 120, "total": 960},
    "VLSER": {"planning": 72, "fieldwork": 600, "managerReview": 72, "partnerReview": 96, "total": 840},
    "VLFIN": {"planning": 72, "fieldwork": 600, "managerReview": 144, "partnerReview": 144, "total": 960},
    "VLREC": {"planning": 120, "fieldwork": 600, "managerReview": 120, "partnerReview": 120, "total": 960}
}

# Default time for combinations not specified (using small manufacturing as default)
default_time_estimate = {"planning": 72, "fieldwork": 288, "managerReview": 72, "partnerReview": 48, "total": 480}

# Staff roles
staff_roles = ["Partner", "Manager", "Qualified Assistant", "Senior Article", "Junior Article", "EQCR"]

# Audit phases
audit_phases = ["Planning", "Fieldwork", "Manager Review", "Partner Review"]

# Get list of available projects for selection
def get_project_list():
    if not st.session_state.projects:
        return ["No projects available"]
    return list(st.session_state.projects.keys())

# Calculate budget based on inputs
def calculate_budget(company_name, turnover, is_listed, industry_sector, controls_risk, inherent_risk, complexity, info_delay_risk):
    # Determine audit category based on turnover
    if turnover <= 50:
        audit_category = "micro"
        audit_category_display = "Micro (≤ Rs. 50 Cr)"
    elif turnover <= 250:
        audit_category = "small"
        audit_category_display = "Small (Rs. 50-250 Cr)"
    elif turnover <= 500:
        audit_category = "medium"
        audit_category_display = "Medium (Rs. 250-500 Cr)"
    elif turnover <= 1000:
        audit_category = "large"
        audit_category_display = "Large (Rs. 500-1000 Cr)"
    else:
        audit_category = "veryLarge"
        audit_category_display = "Very Large (> Rs. 1000 Cr)"
    
    # Get the lookup key based on size and sector
    size_prefix = "S" if audit_category in ["micro", "small"] else "M" if audit_category == "medium" else "L" if audit_category == "large" else "VL"
    lookup_key = size_prefix + industry_sector
    
    # Get baseline hours from detailed estimates or fall back to default
    baseline_estimate = detailed_time_estimates.get(lookup_key, default_time_estimate)
    
    # Extract phase hours
    base_planning = baseline_estimate["planning"]
    base_fieldwork = baseline_estimate["fieldwork"]
    base_manager_review = baseline_estimate["managerReview"]
    base_partner_review = baseline_estimate["partnerReview"]
    base_total = baseline_estimate["total"]
    
    # Apply 0.8 scaling factor for Micro category
    if audit_category == "micro":
        base_planning = round(base_planning * 0.8)
        base_fieldwork = round(base_fieldwork * 0.8)
        base_manager_review = round(base_manager_review * 0.8)
        base_partner_review = round(base_partner_review * 0.8)
        base_total = round(base_total * 0.8)
    
    # Risk adjustment multipliers
    controls_risk_factor = 1 if controls_risk == 1 else (1.2 if controls_risk == 2 else 1.4)
    inherent_risk_factor = 1 if inherent_risk == 1 else (1.25 if inherent_risk == 2 else 1.5)
    complexity_factor = 1 if complexity == 1 else (1.3 if complexity == 2 else 1.6)
    info_delay_factor = 1 if info_delay_risk == 1 else (1.15 if info_delay_risk == 2 else 1.3)
    
    # Calculate adjusted phase hours
    adjusted_planning = round(base_planning * controls_risk_factor * inherent_risk_factor)
    adjusted_fieldwork = round(base_fieldwork * controls_risk_factor * inherent_risk_factor * complexity_factor * info_delay_factor)
    adjusted_manager_review = round(base_manager_review * complexity_factor)
    adjusted_partner_review = round(base_partner_review * complexity_factor)
    
    # Set phase hours
    phase_hours = {
        "planning": adjusted_planning,
        "fieldwork": adjusted_fieldwork,
        "managerReview": adjusted_manager_review,
        "partnerReview": adjusted_partner_review
    }
    
    # Calculate total adjusted hours
    total_hours = adjusted_planning + adjusted_fieldwork + adjusted_manager_review + adjusted_partner_review
    total_days = round(total_hours / 8 * 10) / 10  # Round to 1 decimal place
    
    # Staff allocation
    staff_hours = {
        "partner": phase_hours["partnerReview"],
        "manager": phase_hours["managerReview"],
        "qualifiedAssistant": 0,
        "seniorArticle": 0,
        "juniorArticle": 0,
        "eqcr": 0,
    }
    
    # Add planning hours based on audit size
    if audit_category in ["medium", "large", "veryLarge"]:
        # Partner gets 30% of planning hours for larger audits
        staff_hours["partner"] += round(phase_hours["planning"] * 0.3)
        # Manager gets 30% of planning hours for larger audits
        staff_hours["manager"] += round(phase_hours["planning"] * 0.3)
    else:
        # For small and micro, only manager is involved in planning (no partner)
        staff_hours["manager"] += round(phase_hours["planning"] * 0.4)
    
    # Qualified Assistant hours
    if audit_category in ["medium", "large", "veryLarge"]:
        # For larger audits, QA gets 40% of planning
        staff_hours["qualifiedAssistant"] = round(
            phase_hours["planning"] * 0.4 + 
            phase_hours["fieldwork"] * 0.3
        )
    else:
        # For smaller audits, QA gets 60% of planning
        staff_hours["qualifiedAssistant"] = round(
            phase_hours["planning"] * 0.6 + 
            phase_hours["fieldwork"] * 0.3
        )
    
    # Senior Article hours - not allocated for Micro audits
    if audit_category != "micro":
        staff_hours["seniorArticle"] = round(
            phase_hours["planning"] * 0.3 + 
            phase_hours["fieldwork"] * 0.4
        )
    
    # Junior Article hours
    junior_article_count = 2 if audit_category == "veryLarge" else 1
    
    if junior_article_count == 1:
        # Single junior article
        staff_hours["juniorArticle"] = round(phase_hours["fieldwork"] * 0.3)
    else:
        # Two junior articles for very large audits
        staff_hours["juniorArticle"] = round(phase_hours["fieldwork"] * 0.5)
    
    # Add EQCR hours if required
    eqcr_required = is_listed or turnover > 1000
    if eqcr_required:
        staff_hours["eqcr"] = round(staff_hours["partner"] * 0.4)
    
    # Create detailed staff allocation by phase
    staff_allocation_by_phase = {
        "planning": {},
        "fieldwork": {},
        "managerReview": {},
        "partnerReview": {}
    }
    
    # Planning phase allocation
    if audit_category in ["medium", "large", "veryLarge"]:
        # For larger audits
        staff_allocation_by_phase["planning"]["partner"] = round(phase_hours["planning"] * 0.3)
        staff_allocation_by_phase["planning"]["manager"] = round(phase_hours["planning"] * 0.3)
        staff_allocation_by_phase["planning"]["qualifiedAssistant"] = round(phase_hours["planning"] * 0.4)
        if audit_category != "micro":
            staff_allocation_by_phase["planning"]["seniorArticle"] = round(phase_hours["planning"] * 0.3)
    else:
        # For smaller audits
        staff_allocation_by_phase["planning"]["manager"] = round(phase_hours["planning"] * 0.4)
        staff_allocation_by_phase["planning"]["qualifiedAssistant"] = round(phase_hours["planning"] * 0.6)
    
    # Fieldwork phase allocation
    staff_allocation_by_phase["fieldwork"]["qualifiedAssistant"] = round(phase_hours["fieldwork"] * 0.3)
    if audit_category != "micro":
        staff_allocation_by_phase["fieldwork"]["seniorArticle"] = round(phase_hours["fieldwork"] * 0.4)
    
    if junior_article_count == 1:
        staff_allocation_by_phase["fieldwork"]["juniorArticle"] = round(phase_hours["fieldwork"] * 0.3)
    else:
        staff_allocation_by_phase["fieldwork"]["juniorArticle"] = round(phase_hours["fieldwork"] * 0.5)
    
    # Manager Review phase - all to manager
    staff_allocation_by_phase["managerReview"]["manager"] = phase_hours["managerReview"]
    
    # Partner Review phase - all to partner
    staff_allocation_by_phase["partnerReview"]["partner"] = phase_hours["partnerReview"]
    
    # EQCR if required
    if eqcr_required:
        staff_allocation_by_phase["partnerReview"]["eqcr"] = round(staff_hours["partner"] * 0.4)
    
    # Generate risk adjustment notes
    risk_notes = [
        f"Size-Sector Baseline: {lookup_key}{' (scaled to 80% for Micro)' if audit_category == 'micro' else ''}",
        f"Base Hours: Planning: {base_planning}h, Fieldwork: {base_fieldwork}h, Manager Review: {base_manager_review}h, Partner Review: {base_partner_review}h",
        f"Controls Risk: {'Low' if controls_risk == 1 else ('Medium' if controls_risk == 2 else 'High')} (factor: {controls_risk_factor:.2f})",
        f"Inherent Risk: {'Low' if inherent_risk == 1 else ('Medium' if inherent_risk == 2 else 'High')} (factor: {inherent_risk_factor:.2f})",
        f"Complexity: {'Low' if complexity == 1 else ('Medium' if complexity == 2 else 'High')} (factor: {complexity_factor:.2f})",
        f"Information Delay Risk: {'Low' if info_delay_risk == 1 else ('Medium' if info_delay_risk == 2 else 'High')} (factor: {info_delay_factor:.2f})",
    ]
    
    # Create result dictionary
    result = {
        "company_name": company_name,
        "turnover": turnover,
        "industry_sector": industry_sector,
        "industry_name": industry_sectors[industry_sector]["name"],
        "is_listed": is_listed,
        "audit_category": audit_category,
        "audit_category_display": audit_category_display,
        "phase_hours": phase_hours,
        "total_hours": total_hours,
        "total_days": total_days,
        "staff_hours": staff_hours,
        "staff_allocation_by_phase": staff_allocation_by_phase,
        "eqcr_required": eqcr_required,
        "risk_notes": risk_notes,
        "risk_factors": {
            "controls_risk": controls_risk,
            "inherent_risk": inherent_risk,
            "complexity": complexity,
            "info_delay_risk": info_delay_risk
        },
        "creation_date": datetime.now().strftime("%Y-%m-%d"),
        "financial_year_end": None,  # To be set later
        "team_members": {},  # To be set later
        "actual_hours": {
            "planning": 0,
            "fieldwork": 0,
            "managerReview": 0,
            "partnerReview": 0,
            "total": 0
        }
    }
    
    return result

# Tab 1: Budget Calculator
with tab1:
    st.markdown("### Audit Budget Calculator")
    st.markdown("Calculate audit budgets based on company size, industry, and risk factors.")
    
    # Create layout with columns for input and results
    col1, col2 = st.columns([1, 2])
    
    # Input form in the left column
    with col1:
        with st.container():
            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
            st.subheader("Audit Details")
            
            company_name = st.text_input("Company Name")
            turnover = st.number_input("Turnover (in Rs. Crore)", min_value=0.0, step=10.0)
            is_listed = st.checkbox("Listed Company")
            
            industry_sector = st.selectbox(
                "Industry Sector",
                options=list(industry_sectors.keys()),
                format_func=lambda x: industry_sectors[x]["name"]
            )
            
            # Financial year end
            fy_end = st.date_input("Financial Year End", datetime.now().date())
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Risk factors with expanders
        with st.expander("Risk Factors", expanded=True):
            controls_risk = st.selectbox(
                "Controls Risk",
                options=[1, 2, 3],
                format_func=lambda x: "Low" if x == 1 else ("Medium" if x == 2 else "High")
            )
            
            inherent_risk = st.selectbox(
                "Inherent Risk",
                options=[1, 2, 3],
                format_func=lambda x: "Low" if x == 1 else ("Medium" if x == 2 else "High")
            )
            
            complexity = st.selectbox(
                "Complexity",
                options=[1, 2, 3],
                format_func=lambda x: "Low" if x == 1 else ("Medium" if x == 2 else "High")
            )
            
            info_delay_risk = st.selectbox(
                "Information Delay Risk",
                options=[1, 2, 3],
                format_func=lambda x: "Low" if x == 1 else ("Medium" if x == 2 else "High")
            )
        
        # Team assignment
        with st.expander("Team Assignment", expanded=True):
            st.markdown("Assign specific team members to the audit")
            
            partner_name = st.text_input("Partner Name")
            manager_name = st.text_input("Manager Name")
            qa_name = st.text_input("Qualified Assistant Name")
            senior_name = st.text_input("Senior Article Name")
            junior_name = st.text_input("Junior Article Name")
            eqcr_name = st.text_input("EQCR Partner Name (if applicable)")
        
        # Calculate and Save button
        if st.button("Calculate and Save Project"):
            if company_name and turnover > 0:
                # Calculate budget
                budget_result = calculate_budget(
                    company_name, turnover, is_listed, industry_sector,
                    controls_risk, inherent_risk, complexity, info_delay_risk
                )
                
                # Add financial year end
                budget_result["financial_year_end"] = fy_end.strftime("%Y-%m-%d")
                
                # Add team members
                budget_result["team_members"] = {
                    "partner": partner_name,
                    "manager": manager_name,
                    "qualifiedAssistant": qa_name,
                    "seniorArticle": senior_name,
                    "juniorArticle": junior_name,
                    "eqcr": eqcr_name if budget_result["eqcr_required"] else ""
                }
                
                # Save to session state
                st.session_state.projects[company_name] = budget_result
                st.session_state.current_project = company_name
                
                # Save to file
                save_data()
                
                st.success(f"Project '{company_name}' saved successfully!")
            else:
                st.error("Please enter company name and turnover.")
    
    # Results display in the right column
    with col2:
        if not company_name and not st.session_state.current_project:
            st.info("Please enter company details and risk factors to generate the audit budget.")
            
            # Instructions card
            st.markdown("""
            <div class="custom-card">
                <h3 class="card-title">How to use this calculator:</h3>
                <ol>
                    <li>Enter the company name and turnover</li>
                    <li>Specify if the company is listed</li>
                    <li>Select the industry sector</li>
                    <li>Adjust risk factors as needed</li>
                    <li>Enter the team members assigned to the audit</li>
                    <li>Calculate and save the project</li>
                    <li>Use the Time Tracking tab to log hours</li>
                </ol>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Determine which project to display
            display_project = st.session_state.current_project if not company_name else company_name
            
            if display_project in st.session_state.projects:
                project = st.session_state.projects[display_project]
                
                st.markdown(f"""
                <div class="custom-card">
                    <h3 class="card-title">Budget Summary: {project['company_name']}</h3>
                </div>
                """, unsafe_allow_html=True)
                
                # Top summary cards in custom styled boxes
                summary_col1, summary_col2, summary_col3 = st.columns(3)
                
                with summary_col1:
                    st.metric("Total Planned Hours", f"{project['total_hours']}")
                
                with summary_col2:
                    st.metric("Total Planned Days", f"{round(project['total_days'])}")
                
                with summary_col3:
                    actual_hours = project.get('actual_hours', {}).get('total', 0)
                    delta = actual_hours - project['total_hours']
                    delta_color = "normal" if delta <= 0 else "inverse"
                    st.metric("Actual Hours Logged", f"{actual_hours}", delta=f"{delta}", delta_color=delta_color)
                
                # Phase hours
                st.markdown("""
                <div class="custom-card">
                    <h3 class="card-title">Audit Phase Hours</h3>
                </div>
                """, unsafe_allow_html=True)
                
                phase_cols = st.columns(4)
                
                phase_names = {
                    "planning": "Planning",
                    "fieldwork": "Fieldwork",
                    "managerReview": "Manager Review",
                    "partnerReview": "Partner Review"
                }
                
                for i, (phase_key, phase_name) in enumerate(phase_names.items()):
                    with phase_cols[i]:
                        planned = project['phase_hours'][phase_key]
                        actual = project.get('actual_hours', {}).get(phase_key, 0)
                        st.metric(
                            phase_name,
                            f"{planned}h planned",
                            delta=f"{actual}h logged" if actual > 0 else "No hours logged"
                        )
                
                # Staff allocation
                st.markdown("""
                <div class="custom-card">
                    <h3 class="card-title">Staff Allocation</h3>
                </div>
                """, unsafe_allow_html=True)
                
                # Create a DataFrame for staff allocation table
                staff_data = []
                
                # Role name mapping
                role_display = {
                    "partner": "Partner",
                    "manager": "Manager",
                    "qualifiedAssistant": "Qualified Assistant",
                    "seniorArticle": "Senior Article",
                    "juniorArticle": "Junior Article(s)",
                    "eqcr": "EQCR"
                }
                
                for role, hours in project['staff_hours'].items():
                    if hours == 0:
                        continue
                        
                    days = round(hours / 8)
                    percentage = round(hours / project['total_hours'] * 100) if project['total_hours'] else 0
                    
                    # Get actual hours for this role
                    actual_hours = 0
                    if 'team_members' in project and project['team_members'].get(role):
                        team_member = project['team_members'].get(role)
                        # Sum hours logged by this team member for this project
                        for entry in st.session_state.time_entries:
                            if entry.get('project') == project['company_name'] and entry.get('resource') == team_member:
                                actual_hours += entry.get('hours', 0)
                    
                    staff_data.append({
                        "Role": role_display.get(role, role),
                        "Staff Member": project['team_members'].get(role, "Unassigned"),
                        "Planned Hours": hours,
                        "Actual Hours": actual_hours,
                        "Variance": actual_hours - hours,
                        "% Complete": round((actual_hours / hours * 100) if hours > 0 else 0)
                    })
                
                # Display staff allocation table
                staff_df = pd.DataFrame(staff_data)
                st.dataframe(staff_df, hide_index=True, use_container_width=True)
                
                # Bar chart visualization
                st.markdown("""
                <div class="custom-card">
                    <h3 class="card-title">Staff Hours Visualization</h3>
                </div>
                """, unsafe_allow_html=True)
                
                # Prepare chart data
                chart_data = []
                for row in staff_data:
                    chart_data.append({
                        "Role": row["Role"], 
                        "Planned Hours": row["Planned Hours"],
                        "Actual Hours": row["Actual Hours"]
                    })
                
                chart_df = pd.DataFrame(chart_data)
                
                if not chart_df.empty:
                    # Create bar chart with dark mode styling
                    fig = px.bar(
                        chart_df, 
                        x="Role", 
                        y=["Planned Hours", "Actual Hours"],
                        title="Staff Hours Allocation - Planned vs. Actual",
                        barmode='group',
                        color_discrete_sequence=[COLOR_PRIMARY, COLOR_SECONDARY]
                    )
                    
                    fig.update_layout(
                        plot_bgcolor=COLOR_CARD_BACKGROUND,
                        paper_bgcolor=COLOR_CARD_BACKGROUND,
                        font_color=COLOR_TEXT,
                        xaxis_title="Staff Role",
                        yaxis_title="Hours",
                        height=400,
                        legend_title_font_color=COLOR_TEXT,
                        legend_font_color=COLOR_TEXT,
                        title_font_color=COLOR_TEXT
                    )
                    
                    fig.update_xaxes(color=COLOR_TEXT)
                    fig.update_yaxes(color=COLOR_TEXT)
                    
                    st.plotly_chart(fig, use_container_width=True)

# Tab 2: Time Tracking
with tab2:
    st.markdown("### Time Tracking")
    st.markdown("Log and view time entries for each project and team member.")
    
    # Project selection
    project_options = get_project_list()
    if "No projects available" not in project_options:
        selected_project = st.selectbox(
            "Select Project",
            options=project_options,
            key="time_tracking_project"
        )
        
        if selected_project in st.session_state.projects:
            project = st.session_state.projects[selected_project]
            
            # Display project info
            st.markdown(f"""
            <div class="custom-card">
                <h3 class="card-title">Project Information</h3>
                <p><strong>Company:</strong> {project['company_name']}</p>
                <p><strong>Industry:</strong> {project['industry_name']}</p>
                <p><strong>Financial Year End:</strong> {project['financial_year_end']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Create columns for time entry form
            col1, col2 = st.columns(2)
            
            with col1:
                # Time entry form
                st.markdown("""
                <div class="custom-card">
                    <h3 class="card-title">Add Time Entry</h3>
                </div>
                """, unsafe_allow_html=True)
                
                # Get the list of team members for this project
                team_members = [v for k, v in project['team_members'].items() if v]
                selected_resource = st.selectbox("Team Member", options=team_members)
                
                # Map phase keys to display names
                phase_options = {
                    "planning": "Planning",
                    "fieldwork": "Fieldwork",
                    "managerReview": "Manager Review",
                    "partnerReview": "Partner Review"
                }
                
                selected_phase = st.selectbox(
                    "Audit Phase",
                    options=list(phase_options.keys()),
                    format_func=lambda x: phase_options[x]
                )
                
                entry_date = st.date_input("Date", datetime.now().date())
                hours_spent = st.number_input("Hours Spent", min_value=0.1, max_value=24.0, value=8.0, step=0.5)
                description = st.text_area("Description", "")
                
                if st.button("Add Time Entry", key="add_time_entry"):
                    # Create time entry
                    time_entry = {
                        "project": selected_project,
                        "resource": selected_resource,
                        "phase": selected_phase,
                        "date": entry_date.strftime("%Y-%m-%d"),
                        "hours": hours_spent,
                        "description": description,
                        "entry_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    # Add to time entries list
                    st.session_state.time_entries.append(time_entry)
                    
                    # Update actual hours in project
                    if 'actual_hours' not in project:
                        project['actual_hours'] = {
                            "planning": 0,
                            "fieldwork": 0,
                            "managerReview": 0,
                            "partnerReview": 0,
                            "total": 0
                        }
                    
                    project['actual_hours'][selected_phase] += hours_spent
                    project['actual_hours']['total'] += hours_spent
                    
                    # Save data
                    save_data()
                    
                    st.success("Time entry added successfully!")
                    st.rerun()
            
            with col2:
                # Display time entries for this project
                st.markdown("""
                <div class="custom-card">
                    <h3 class="card-title">Recent Time Entries</h3>
                </div>
                """, unsafe_allow_html=True)
                
                # Filter time entries for this project
                project_entries = [entry for entry in st.session_state.time_entries if entry.get('project') == selected_project]
                
                if project_entries:
                    entries_df = pd.DataFrame(project_entries)
                    entries_df = entries_df.sort_values('date', ascending=False)
                    
                    # Format columns for display
                    display_df = entries_df[['date', 'resource', 'phase', 'hours', 'description']].copy()
                    display_df['phase'] = display_df['phase'].map(lambda x: phase_options.get(x, x))
                    
                    st.dataframe(display_df, hide_index=True, use_container_width=True)
                else:
                    st.info("No time entries found for this project.")
    else:
        st.info("No projects available. Please create a project in the Budget Calculator tab first.")

# Tab 3: Project Reports
with tab3:
    st.markdown("### Project Reports")
    st.markdown("View detailed reports on project progress and time utilization.")
    
    # Project selection
    project_options = get_project_list()
    if "No projects available" not in project_options:
        selected_project = st.selectbox(
            "Select Project",
            options=project_options,
            key="project_report_selection"
        )
        
        if selected_project in st.session_state.projects:
            project = st.session_state.projects[selected_project]
            
            # Display project overview
            st.markdown(f"""
            <div class="custom-card">
                <h3 class="card-title">Project Overview: {project['company_name']}</h3>
            </div>
            """, unsafe_allow_html=True)
            
            # Create columns for metrics
            metrics_cols = st.columns(4)
            
            with metrics_cols[0]:
                st.metric("Turnover", f"Rs. {project['turnover']} Cr")
            
            with metrics_cols[1]:
                st.metric("Industry", project['industry_name'])
            
            with metrics_cols[2]:
                st.metric("Category", project['audit_category_display'])
            
            with metrics_cols[3]:
                st.metric("Listed", "Yes" if project['is_listed'] else "No")
            
            # Progress metrics
            st.markdown("""
            <div class="custom-card">
                <h3 class="card-title">Progress Metrics</h3>
            </div>
            """, unsafe_allow_html=True)
            
            progress_cols = st.columns(3)
            
            # Calculate total progress
            total_planned = project['total_hours']
            total_actual = project.get('actual_hours', {}).get('total', 0)
            total_progress = (total_actual / total_planned * 100) if total_planned > 0 else 0
            
            with progress_cols[0]:
                st.metric("Overall Progress", f"{round(total_progress)}%")
            
            with progress_cols[1]:
                st.metric("Planned Hours", total_planned)
            
            with progress_cols[2]:
                delta = total_actual - total_planned
                delta_color = "normal" if delta <= 0 else "inverse"
                st.metric("Actual Hours", total_actual, delta=delta, delta_color=delta_color)
            
            # Phase progress visualization
            st.markdown("""
            <div class="custom-card">
                <h3 class="card-title">Progress by Phase</h3>
            </div>
            """, unsafe_allow_html=True)
            
            # Prepare data for phase progress
            phase_data = []
            for phase_key, phase_name in {
                "planning": "Planning",
                "fieldwork": "Fieldwork",
                "managerReview": "Manager Review",
                "partnerReview": "Partner Review"
            }.items():
                planned = project['phase_hours'][phase_key]
                actual = project.get('actual_hours', {}).get(phase_key, 0)
                progress = (actual / planned * 100) if planned > 0 else 0
                
                phase_data.append({
                    "Phase": phase_name,
                    "Planned Hours": planned,
                    "Actual Hours": actual,
                    "Progress": progress
                })
            
            phase_df = pd.DataFrame(phase_data)
            
            # Create horizontal bar chart for phase progress with dark mode styling
            fig = go.Figure()
            
            # Add planned hours bars
            fig.add_trace(go.Bar(
                y=phase_df['Phase'],
                x=phase_df['Planned Hours'],
                name='Planned Hours',
                orientation='h',
                marker=dict(color='rgba(30, 136, 229, 0.5)')
            ))
            
            # Add actual hours bars
            fig.add_trace(go.Bar(
                y=phase_df['Phase'],
                x=phase_df['Actual Hours'],
                name='Actual Hours',
                orientation='h',
                marker=dict(color='rgba(0, 230, 118, 0.8)')
            ))
            
            fig.update_layout(
                title='Planned vs. Actual Hours by Phase',
                barmode='overlay',
                height=400,
                margin=dict(l=20, r=20, t=40, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                plot_bgcolor=COLOR_CARD_BACKGROUND,
                paper_bgcolor=COLOR_CARD_BACKGROUND,
                font_color=COLOR_TEXT,
                title_font_color=COLOR_TEXT
            )
            
            fig.update_xaxes(color=COLOR_TEXT)
            fig.update_yaxes(color=COLOR_TEXT)
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Resource utilization
            st.markdown("""
            <div class="custom-card">
                <h3 class="card-title">Resource Utilization</h3>
            </div>
            """, unsafe_allow_html=True)
            
            # Get time entries by resource
            resource_hours = {}
            
            for entry in st.session_state.time_entries:
                if entry.get('project') == selected_project:
                    resource = entry.get('resource')
                    hours = entry.get('hours', 0)
                    
                    if resource not in resource_hours:
                        resource_hours[resource] = {
                            "total": 0,
                            "planning": 0,
                            "fieldwork": 0,
                            "managerReview": 0,
                            "partnerReview": 0
                        }
                    
                    resource_hours[resource]['total'] += hours
                    resource_hours[resource][entry.get('phase', 'other')] += hours
            
            # Create resource utilization data
            resource_data = []
            for resource, hours in resource_hours.items():
                resource_data.append({
                    "Resource": resource,
                    "Total Hours": hours['total'],
                    "Planning": hours['planning'],
                    "Fieldwork": hours['fieldwork'],
                    "Manager Review": hours['managerReview'],
                    "Partner Review": hours['partnerReview']
                })
            
            if resource_data:
                resource_df = pd.DataFrame(resource_data)
                st.dataframe(resource_df, hide_index=True, use_container_width=True)
                
                # Create stacked bar chart for resource utilization with dark mode styling
                fig = px.bar(
                    resource_df, 
                    x="Resource", 
                    y=["Planning", "Fieldwork", "Manager Review", "Partner Review"],
                    title="Hours Breakdown by Resource",
                    barmode='stack',
                    color_discrete_sequence=[COLOR_PRIMARY, COLOR_SECONDARY, COLOR_WARNING, "#9c27b0"]
                )
                
                fig.update_layout(
                    xaxis_title="Team Member",
                    yaxis_title="Hours",
                    height=400,
                    legend_title="Audit Phase",
                    plot_bgcolor=COLOR_CARD_BACKGROUND,
                    paper_bgcolor=COLOR_CARD_BACKGROUND,
                    font_color=COLOR_TEXT,
                    title_font_color=COLOR_TEXT
                )
                
                fig.update_xaxes(color=COLOR_TEXT)
                fig.update_yaxes(color=COLOR_TEXT)
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No time entries recorded yet for this project.")
            
            # Timeline view
            st.markdown("""
            <div class="custom-card">
                <h3 class="card-title">Project Timeline</h3>
            </div>
            """, unsafe_allow_html=True)
            
            # Filter time entries for this project
            timeline_entries = [entry for entry in st.session_state.time_entries if entry.get('project') == selected_project]
            
            if timeline_entries:
                # Create DataFrame for timeline
                timeline_df = pd.DataFrame(timeline_entries)
                timeline_df['date'] = pd.to_datetime(timeline_df['date'])
                
                # Group by date and phase
                daily_hours = timeline_df.groupby(['date', 'phase']).agg({'hours': 'sum'}).reset_index()
                
                # Map phase names
                phase_map = {
                    "planning": "Planning",
                    "fieldwork": "Fieldwork",
                    "managerReview": "Manager Review",
                    "partnerReview": "Partner Review"
                }
                daily_hours['phase'] = daily_hours['phase'].map(lambda x: phase_map.get(x, x))
                
                # Create line chart with dark mode styling
                fig = px.line(
                    daily_hours,
                    x='date',
                    y='hours',
                    color='phase',
                    title='Daily Hours by Phase',
                    markers=True,
                    color_discrete_sequence=[COLOR_PRIMARY, COLOR_SECONDARY, COLOR_WARNING, "#9c27b0"]
                )
                
                fig.update_layout(
                    xaxis_title="Date",
                    yaxis_title="Hours Logged",
                    height=400,
                    plot_bgcolor=COLOR_CARD_BACKGROUND,
                    paper_bgcolor=COLOR_CARD_BACKGROUND,
                    font_color=COLOR_TEXT,
                    title_font_color=COLOR_TEXT
                )
                
                fig.update_xaxes(color=COLOR_TEXT)
                fig.update_yaxes(color=COLOR_TEXT)
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Create cumulative hours chart with dark mode styling
                timeline_df = timeline_df.sort_values('date')
                timeline_df['cumulative_hours'] = timeline_df.groupby('phase')['hours'].cumsum()
                
                # Map phase names
                timeline_df['phase'] = timeline_df['phase'].map(lambda x: phase_map.get(x, x))
                
                fig = px.line(
                    timeline_df,
                    x='date',
                    y='cumulative_hours',
                    color='phase',
                    title='Cumulative Hours by Phase',
                    line_shape='hv',
                    color_discrete_sequence=[COLOR_PRIMARY, COLOR_SECONDARY, COLOR_WARNING, "#9c27b0"]
                )
                
                fig.update_layout(
                    xaxis_title="Date",
                    yaxis_title="Cumulative Hours",
                    height=400,
                    plot_bgcolor=COLOR_CARD_BACKGROUND,
                    paper_bgcolor=COLOR_CARD_BACKGROUND,
                    font_color=COLOR_TEXT,
                    title_font_color=COLOR_TEXT
                )
                
                fig.update_xaxes(color=COLOR_TEXT)
                fig.update_yaxes(color=COLOR_TEXT)
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No time entries recorded yet for this project.")
            
            # Export options
            st.markdown("""
            <div class="custom-card">
                <h3 class="card-title">Export Report</h3>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Export Project Report", key="export_project_report"):
                # Create Excel report
                output = io.BytesIO()
                
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    # Project Summary
                    summary_data = {
                        "Item": [
                            "Company", "Turnover (Rs. Crore)", "Industry", "Audit Category", 
                            "Financial Year End", "Listed", "Total Planned Hours", 
                            "Total Actual Hours", "Progress"
                        ],
                        "Value": [
                            project['company_name'], project['turnover'], project['industry_name'], 
                            project['audit_category_display'], project['financial_year_end'],
                            "Yes" if project['is_listed'] else "No", total_planned, 
                            total_actual, f"{round(total_progress)}%"
                        ]
                    }
                    summary_df = pd.DataFrame(summary_data)
                    summary_df.to_excel(writer, sheet_name='Summary', index=False)
                    
                    # Phase Progress
                    phase_df.to_excel(writer, sheet_name='Phase Progress', index=False)
                    
                    # Resource Utilization
                    if resource_data:
                        resource_df.to_excel(writer, sheet_name='Resource Utilization', index=False)
                    
                    # Time Entries Detail
                    if timeline_entries:
                        entries_df = pd.DataFrame(timeline_entries)
                        entries_df['phase'] = entries_df['phase'].map(lambda x: phase_map.get(x, x))
                        entries_df.to_excel(writer, sheet_name='Time Entries', index=False)
                
                # Create download link
                output.seek(0)
                b64 = base64.b64encode(output.read()).decode()
                filename = f"project_report_{project['company_name'].replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d')}.xlsx"
                href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}" style="text-decoration:none;"><button style="background-color:{COLOR_PRIMARY};color:white;padding:10px 20px;border:none;border-radius:5px;cursor:pointer;">Download Excel Report</button></a>'
                st.markdown(href, unsafe_allow_html=True)
    else:
        st.info("No projects available. Please create a project in the Budget Calculator tab first.")

# Tab 4: Team Reports
with tab4:
    st.markdown("### Team Reports")
    st.markdown("View reports on team member utilization across all projects.")
    
    # Get all team members across projects
    all_team_members = set()
    for project_name, project in st.session_state.projects.items():
        if 'team_members' in project:
            for role, member in project['team_members'].items():
                if member:  # Only add non-empty team members
                    all_team_members.add(member)
    
    if all_team_members:
        # Team member selection
        selected_member = st.selectbox(
            "Select Team Member",
            options=sorted(list(all_team_members))
        )
        
        st.markdown("""
        <div class="custom-card">
            <h3 class="card-title">Date Range</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Date range selection for filtering
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", datetime.now().replace(day=1).date())
        with col2:
            end_date = st.date_input("End Date", datetime.now().date())
        
        # Filter time entries for selected team member and date range
        member_entries = [
            entry for entry in st.session_state.time_entries 
            if entry.get('resource') == selected_member
            and start_date.strftime('%Y-%m-%d') <= entry.get('date', '') <= end_date.strftime('%Y-%m-%d')
        ]
        
        if member_entries:
            # Calculate total hours
            total_hours = sum(entry.get('hours', 0) for entry in member_entries)
            
            # Group hours by project
            project_hours = {}
            for entry in member_entries:
                project = entry.get('project', 'Unknown')
                if project not in project_hours:
                    project_hours[project] = 0
                project_hours[project] += entry.get('hours', 0)
            
            # Group hours by phase
            phase_hours = {}
            for entry in member_entries:
                phase = entry.get('phase', 'Unknown')
                if phase not in phase_hours:
                    phase_hours[phase] = 0
                phase_hours[phase] += entry.get('hours', 0)
            
            # Display summary metrics
            st.markdown(f"""
            <div class="custom-card">
                <h3 class="card-title">Summary for {selected_member}</h3>
            </div>
            """, unsafe_allow_html=True)
            
            metrics_cols = st.columns(3)
            with metrics_cols[0]:
                st.metric("Total Hours", f"{total_hours}")
            
            with metrics_cols[1]:
                st.metric("Projects", f"{len(project_hours)}")
            
            with metrics_cols[2]:
                daily_avg = total_hours / max(1, (end_date - start_date).days + 1)
                st.metric("Daily Average", f"{round(daily_avg, 1)}")
            
            # Create charts
            chart_cols = st.columns(2)
            
            with chart_cols[0]:
                st.markdown("""
                <div class="custom-card">
                    <h3 class="card-title">Hours by Project</h3>
                </div>
                """, unsafe_allow_html=True)
                
                # Project distribution pie chart with dark mode styling
                project_data = pd.DataFrame({
                    'Project': list(project_hours.keys()),
                    'Hours': list(project_hours.values())
                })
                
                fig = px.pie(
                    project_data,
                    values='Hours',
                    names='Project',
                    title=f'Hours by Project ({start_date.strftime("%d %b")} - {end_date.strftime("%d %b")})',
                    color_discrete_sequence=px.colors.sequential.Blues_r
                )
                
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(
                    height=400,
                    plot_bgcolor=COLOR_CARD_BACKGROUND,
                    paper_bgcolor=COLOR_CARD_BACKGROUND,
                    font_color=COLOR_TEXT,
                    title_font_color=COLOR_TEXT
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            with chart_cols[1]:
                st.markdown("""
                <div class="custom-card">
                    <h3 class="card-title">Hours by Phase</h3>
                </div>
                """, unsafe_allow_html=True)
                
                # Phase distribution pie chart with dark mode styling
                phase_map = {
                    "planning": "Planning",
                    "fieldwork": "Fieldwork",
                    "managerReview": "Manager Review",
                    "partnerReview": "Partner Review"
                }
                
                phase_data = pd.DataFrame({
                    'Phase': [phase_map.get(p, p) for p in phase_hours.keys()],
                    'Hours': list(phase_hours.values())
                })
                
                fig = px.pie(
                    phase_data,
                    values='Hours',
                    names='Phase',
                    title=f'Hours by Audit Phase ({start_date.strftime("%d %b")} - {end_date.strftime("%d %b")})',
                    color_discrete_sequence=[COLOR_PRIMARY, COLOR_SECONDARY, COLOR_WARNING, "#9c27b0"]
                )
                
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(
                    height=400,
                    plot_bgcolor=COLOR_CARD_BACKGROUND,
                    paper_bgcolor=COLOR_CARD_BACKGROUND,
                    font_color=COLOR_TEXT,
                    title_font_color=COLOR_TEXT
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            # Time entries table
            st.markdown("""
            <div class="custom-card">
                <h3 class="card-title">Time Entries</h3>
            </div>
            """, unsafe_allow_html=True)
            
            entries_df = pd.DataFrame(member_entries)
            if not entries_df.empty:
                entries_df['date'] = pd.to_datetime(entries_df['date'])
                entries_df = entries_df.sort_values('date', ascending=False)
                
                # Map phase names
                entries_df['phase'] = entries_df['phase'].map(lambda x: phase_map.get(x, x))
                
                # Display entries
                st.dataframe(
                    entries_df[['date', 'project', 'phase', 'hours', 'description']],
                    hide_index=True,
                    use_container_width=True
                )
            
            # Daily hours chart
            st.markdown("""
            <div class="custom-card">
                <h3 class="card-title">Daily Hours Trend</h3>
            </div>
            """, unsafe_allow_html=True)
            
            # Create daily hours DataFrame
            entries_df['date'] = pd.to_datetime(entries_df['date'])
            daily_df = entries_df.groupby(entries_df['date'].dt.date).agg({'hours': 'sum'}).reset_index()
            
            fig = px.bar(
                daily_df,
                x='date',
                y='hours',
                title=f'Daily Hours ({start_date.strftime("%d %b")} - {end_date.strftime("%d %b")})',
                color_discrete_sequence=[COLOR_PRIMARY]
            )
            
            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Hours",
                height=400,
                plot_bgcolor=COLOR_CARD_BACKGROUND,
                paper_bgcolor=COLOR_CARD_BACKGROUND,
                font_color=COLOR_TEXT,
                title_font_color=COLOR_TEXT
            )
            
            fig.update_xaxes(color=COLOR_TEXT)
            fig.update_yaxes(color=COLOR_TEXT)
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Export team member report
            st.markdown("""
            <div class="custom-card">
                <h3 class="card-title">Export Report</h3>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Export Team Member Report", key="export_team_report"):
                # Create Excel report
                output = io.BytesIO()
                
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    # Summary
                    summary_data = {
                        "Item": ["Team Member", "Date Range", "Total Hours", "Projects", "Daily Average"],
                        "Value": [
                            selected_member,
                            f"{start_date.strftime('%d %b %Y')} - {end_date.strftime('%d %b %Y')}",
                            total_hours,
                            len(project_hours),
                            f"{round(daily_avg, 1)}"
                        ]
                    }
                    summary_df = pd.DataFrame(summary_data)
                    summary_df.to_excel(writer, sheet_name='Summary', index=False)
                    
                    # Project Hours
                    project_data.to_excel(writer, sheet_name='Project Hours', index=False)
                    
                    # Phase Hours
                    phase_data.to_excel(writer, sheet_name='Phase Hours', index=False)
                    
                    # Daily Hours
                    daily_df.to_excel(writer, sheet_name='Daily Hours', index=False)
                    
                    # Time Entries
                    entries_df[['date', 'project', 'phase', 'hours', 'description']].to_excel(
                        writer, sheet_name='Time Entries', index=False
                    )
                
                # Create download link
                output.seek(0)
                b64 = base64.b64encode(output.read()).decode()
                filename = f"team_report_{selected_member.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d')}.xlsx"
                href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}" style="text-decoration:none;"><button style="background-color:{COLOR_PRIMARY};color:white;padding:10px 20px;border:none;border-radius:5px;cursor:pointer;">Download Excel Report</button></a>'
                st.markdown(href, unsafe_allow_html=True)
        else:
            st.info(f"No time entries found for {selected_member} in the selected date range.")
    else:
        st.info("No team members assigned to any projects yet.")

# Add a new Dashboard tab and make it the first tab
# Add this before creating the other tabs
def create_dashboard():
    st.markdown("### Dashboard")
    st.markdown("Overview of all audit projects and team activities.")
    
    # Check if projects exist
    if not st.session_state.projects:
        st.info("No projects available. Please create a project in the Budget Calculator tab first.")
        return
    
    # Summary metrics
    projects_count = len(st.session_state.projects)
    total_planned_hours = sum(project.get('total_hours', 0) for project in st.session_state.projects.values())
    total_actual_hours = sum(project.get('actual_hours', {}).get('total', 0) for project in st.session_state.projects.values())
    
    # Team members
    all_team_members = set()
    for project in st.session_state.projects.values():
        if 'team_members' in project:
            for role, member in project['team_members'].items():
                if member:
                    all_team_members.add(member)
    
    # Create metrics layout
    st.markdown("""
    <div class="custom-card">
        <h3 class="card-title">Summary Metrics</h3>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Projects", f"{projects_count}")
    
    with col2:
        st.metric("Total Team Members", f"{len(all_team_members)}")
    
    with col3:
        st.metric("Total Planned Hours", f"{total_planned_hours}")
    
    with col4:
        completion_pct = round((total_actual_hours / total_planned_hours * 100) if total_planned_hours else 0)
        st.metric("Overall Completion", f"{completion_pct}%", f"{total_actual_hours} hours")
    
    # Project status overview
    st.markdown("""
    <div class="custom-card">
        <h3 class="card-title">Project Status Overview</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Create project status dataframe
    project_status = []
    for name, project in st.session_state.projects.items():
        planned = project.get('total_hours', 0)
        actual = project.get('actual_hours', {}).get('total', 0)
        completion = round((actual / planned * 100) if planned else 0)
        
        project_status.append({
            "Project": name,
            "Category": project.get('audit_category_display', ''),
            "Industry": project.get('industry_name', ''),
            "Planned Hours": planned,
            "Actual Hours": actual,
            "Completion": f"{completion}%",
            "Completion_Value": completion,  # For sorting
            "Status": "Completed" if completion >= 95 else "In Progress" if completion > 0 else "Not Started"
        })
    
    # Sort by completion (descending)
    project_status = sorted(project_status, key=lambda x: x["Completion_Value"], reverse=True)
    
    # Display as dataframe
    status_df = pd.DataFrame(project_status)
    if 'Completion_Value' in status_df.columns:
        status_df = status_df.drop('Completion_Value', axis=1)
    
    st.dataframe(status_df, hide_index=True, use_container_width=True)
    
    # Recent activity
    st.markdown("""
    <div class="custom-card">
        <h3 class="card-title">Recent Activity</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Get recent time entries
    recent_entries = sorted(
        st.session_state.time_entries,
        key=lambda x: x.get('entry_time', ''),
        reverse=True
    )[:10]  # Get 10 most recent entries
    
    if recent_entries:
        # Convert to dataframe
        recent_df = pd.DataFrame(recent_entries)
        
        # Format display
        phase_map = {
            "planning": "Planning",
            "fieldwork": "Fieldwork",
            "managerReview": "Manager Review",
            "partnerReview": "Partner Review"
        }
        
        recent_df['phase'] = recent_df['phase'].map(lambda x: phase_map.get(x, x))
        recent_df['entry_time'] = pd.to_datetime(recent_df['entry_time'])
        
        # Display recent entries
        st.dataframe(
            recent_df[['entry_time', 'project', 'resource', 'phase', 'hours']],
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("No time entries recorded yet.")
    
    # Team utilization chart
    st.markdown("""
    <div class="custom-card">
        <h3 class="card-title">Team Utilization</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Aggregate hours by team member
    team_hours = {}
    for entry in st.session_state.time_entries:
        resource = entry.get('resource', 'Unknown')
        hours = entry.get('hours', 0)
        
        if resource not in team_hours:
            team_hours[resource] = 0
        team_hours[resource] += hours
    
    if team_hours:
        # Create dataframe for chart
        team_df = pd.DataFrame({
            'Team Member': list(team_hours.keys()),
            'Hours': list(team_hours.values())
        }).sort_values('Hours', ascending=False)
        
        # Horizontal bar chart with dark mode styling
        fig = px.bar(
            team_df,
            y='Team Member',
            x='Hours',
            title='Total Hours by Team Member',
            orientation='h',
            color='Hours',
            color_continuous_scale='Blues'
        )
        
        fig.update_layout(
            xaxis_title="Hours",
            yaxis_title="",
            height=400,
            plot_bgcolor=COLOR_CARD_BACKGROUND,
            paper_bgcolor=COLOR_CARD_BACKGROUND,
            font_color=COLOR_TEXT,
            title_font_color=COLOR_TEXT
        )
        
        fig.update_xaxes(color=COLOR_TEXT)
        fig.update_yaxes(color=COLOR_TEXT)
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No time entries recorded yet.")
    
    # Hours by audit phase
    st.markdown("""
    <div class="custom-card">
        <h3 class="card-title">Hours by Audit Phase</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Aggregate hours by phase
    phase_hours = {"planning": 0, "fieldwork": 0, "managerReview": 0, "partnerReview": 0}
    for entry in st.session_state.time_entries:
        phase = entry.get('phase', 'Unknown')
        hours = entry.get('hours', 0)
        
        if phase in phase_hours:
            phase_hours[phase] += hours
    
    # Create dataframe for chart
    phase_df = pd.DataFrame({
        'Phase': [phase_map.get(p, p) for p in phase_hours.keys()],
        'Hours': list(phase_hours.values())
    })
    
    # Create doughnut chart with dark mode styling
    fig = px.pie(
        phase_df,
        values='Hours',
        names='Phase',
        title='Distribution of Hours by Audit Phase',
        hole=0.4,
        color_discrete_sequence=[COLOR_PRIMARY, COLOR_SECONDARY, COLOR_WARNING, "#9c27b0"]
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(
        height=400,
        plot_bgcolor=COLOR_CARD_BACKGROUND,
        paper_bgcolor=COLOR_CARD_BACKGROUND,
        font_color=COLOR_TEXT,
        title_font_color=COLOR_TEXT
    )
    
    st.plotly_chart(fig, use_container_width=True)

# Add dashboard as the first tab
tab_dashboard, tab1, tab2, tab3, tab4 = st.tabs(["Dashboard", "Budget Calculator", "Time Tracking", "Project Reports", "Team Reports"])

with tab_dashboard:
    create_dashboard()

# Footer
st.markdown("---")
st.caption("Statutory Audit Budget Calculator & Time Tracker - A tool for audit planning and resource tracking")