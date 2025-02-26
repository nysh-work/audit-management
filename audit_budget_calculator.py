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
from PIL import Image
import uuid
from io import BytesIO

# Set page config with mobile-friendly defaults
st.set_page_config(
    page_title="Audit Budget Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"  # Start with sidebar collapsed on mobile
)

# Custom CSS for mobile responsiveness
st.markdown("""
<style>
    /* Mobile-first approach */
    .stApp {
        max-width: 100%;
    }
    
    /* Make buttons easier to tap on mobile */
    .stButton>button {
        height: 3rem;
        font-size: 16px;
        width: 100%;
        margin-bottom: 10px;
    }
    
    /* Improve form controls on mobile */
    div[data-baseweb="select"] {
        min-height: 40px;
    }
    
    div[data-baseweb="input"] {
        min-height: 40px;
    }
    
    /* Adjust text sizes for readability */
    h1 {
        font-size: calc(1.375rem + 1.5vw);
    }
    
    h2 {
        font-size: calc(1.325rem + 0.9vw);
    }
    
    h3 {
        font-size: calc(1.3rem + 0.6vw);
    }
    
    @media (max-width: 768px) {
        .st-emotion-cache-ocqkz7 {
            flex-direction: column;
        }
        
        .row-widget.stRadio > div {
            flex-direction: column;
        }
    }
</style>
""", unsafe_allow_html=True)

# Create mobile detection function
def is_mobile():
    # This is a simple check - in production you might want to use a more robust method
    return st.session_state.get('mobile_view', False)

# Add mobile switcher in sidebar
with st.sidebar:
    st.session_state.mobile_view = st.checkbox("Mobile View", 
                                              value=st.session_state.get('mobile_view', False))

# Initialize session state for storing data
if 'projects' not in st.session_state:
    st.session_state.projects = {}

if 'time_entries' not in st.session_state:
    st.session_state.time_entries = []

if 'current_project' not in st.session_state:
    st.session_state.current_project = None

if 'photo_evidence' not in st.session_state:
    st.session_state.photo_evidence = {}

# Function to save data to files
def save_data():
    # Save projects
    with open('projects.json', 'w') as f:
        json.dump(st.session_state.projects, f)
    
    # Save time entries
    df = pd.DataFrame(st.session_state.time_entries)
    if not df.empty:
        df.to_csv('time_entries.csv', index=False)
    
    # Save photo evidence references
    with open('photo_evidence.json', 'w') as f:
        # Only save the metadata and references, not the actual images
        photo_metadata = {k: {
            'project': v.get('project', ''),
            'phase': v.get('phase', ''),
            'date': v.get('date', ''),
            'description': v.get('description', ''),
            'path': v.get('path', '')
        } for k, v in st.session_state.photo_evidence.items()}
        json.dump(photo_metadata, f)

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
        
        # Load photo evidence metadata
        if os.path.exists('photo_evidence.json'):
            with open('photo_evidence.json', 'r') as f:
                photo_metadata = json.load(f)
                # Only load the metadata, we'll load the actual images when needed
                st.session_state.photo_evidence = photo_metadata
    except Exception as e:
        st.error(f"Error loading data: {e}")

# Try to load data at startup
try:
    load_data()
except:
    # First run or file doesn't exist yet
    pass

# Function to save uploaded images
def save_image(uploaded_file, project, phase, description):
    if uploaded_file is not None:
        # Create unique ID for this image
        image_id = str(uuid.uuid4())
        
        # Create directory if it doesn't exist
        os.makedirs('evidence_photos', exist_ok=True)
        
        # Save image to file
        file_path = f"evidence_photos/{image_id}.jpg"
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Store metadata in session state
        st.session_state.photo_evidence[image_id] = {
            'project': project,
            'phase': phase,
            'date': date.today().strftime("%Y-%m-%d"),
            'description': description,
            'path': file_path
        }
        
        save_data()
        return image_id
    return None

# Function to get image
def get_image(image_id):
    if image_id in st.session_state.photo_evidence:
        file_path = st.session_state.photo_evidence[image_id].get('path')
        if os.path.exists(file_path):
            return Image.open(file_path)
    return None

# Title and navigation - adaptive to mobile
if is_mobile():
    st.title("Audit Tracker")
    # Mobile navigation uses a selectbox instead of tabs
    app_mode = st.selectbox(
        "Select Function",
        ["Budget Calculator", "Time Tracking", "Project Reports", "Team Reports", "Evidence Capture"]
    )
else:
    st.title("Statutory Audit Budget Calculator & Time Tracker")
    # Desktop uses tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Budget Calculator", "Time Tracking", "Project Reports", "Team Reports", "Evidence Capture"
    ])
    # Map selection to tab index
    tab_mapping = {
        "Budget Calculator": 0,
        "Time Tracking": 1,
        "Project Reports": 2,
        "Team Reports": 3,
        "Evidence Capture": 4
    }
    app_mode = list(tab_mapping.keys())[0]  # Default

# Industry sector definitions and factors
industry_sectors = {
    "MFG": {"name": "Manufacturing", "factor": 1.0},
    "TRD": {"name": "Trading", "factor": 0.9},
    "SER": {"name": "Services", "factor": 0.95},
    "FIN": {"name": "Financial Services", "factor": 1.3},
    "REC": {"name": "Real Estate and Construction", "factor": 1.2},
    "NGO": {"name": "Not for profit", "factor": 0.85}
}

# Rest of your detailed time estimates, function definitions, etc. would go here
# (Not including all the logic from your original calculator to save space)

# Get list of available projects for selection
def get_project_list():
    if not st.session_state.projects:
        return ["No projects available"]
    return list(st.session_state.projects.keys())

# Define staff roles and audit phases
staff_roles = ["Partner", "Manager", "Qualified Assistant", "Senior Article", "Junior Article", "EQCR"]
audit_phases = ["Planning", "Fieldwork", "Manager Review", "Partner Review"]

# Mobile-friendly time entry form
def mobile_time_entry_form(project_options):
    st.subheader("Log Time")
    
    if "No projects available" not in project_options:
        selected_project = st.selectbox("Project", options=project_options)
        
        if selected_project in st.session_state.projects:
            project = st.session_state.projects[selected_project]
            
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
            
            # Use number input with step buttons for easier touch input
            hours_col, mins_col = st.columns(2)
            with hours_col:
                hours = st.number_input("Hours", min_value=0, max_value=24, value=8, step=1)
            with mins_col:
                minutes = st.number_input("Minutes", min_value=0, max_value=59, value=0, step=15)
            
            total_hours = hours + (minutes / 60)
            
            description = st.text_area("Description", "", height=100)
            
            if st.button("Submit Time", use_container_width=True):
                # Create time entry
                time_entry = {
                    "project": selected_project,
                    "resource": selected_resource,
                    "phase": selected_phase,
                    "date": entry_date.strftime("%Y-%m-%d"),
                    "hours": total_hours,
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
                
                project['actual_hours'][selected_phase] += total_hours
                project['actual_hours']['total'] += total_hours
                
                # Save data
                save_data()
                
                st.success(f"✅ {total_hours} hours logged successfully!")
                st.rerun()
    else:
        st.info("No projects available. Please create a project first.")

# Mobile-friendly photo evidence capture form
def mobile_evidence_capture_form(project_options):
    st.subheader("Capture Audit Evidence")
    
    if "No projects available" not in project_options:
        selected_project = st.selectbox("Project", options=project_options, key="evidence_project")
        
        if selected_project in st.session_state.projects:
            project = st.session_state.projects[selected_project]
            
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
                format_func=lambda x: phase_options[x],
                key="evidence_phase"
            )
            
            description = st.text_area("Description (what document/evidence is this?)", "", height=100, key="evidence_desc")
            
            uploaded_file = st.file_uploader("Take or Upload Photo", type=["jpg", "jpeg", "png"], key="evidence_upload")
            
            if uploaded_file is not None:
                st.image(uploaded_file, caption="Preview", width=300)
            
            if st.button("Save Evidence", use_container_width=True):
                if uploaded_file is not None:
                    # Save the image
                    image_id = save_image(uploaded_file, selected_project, selected_phase, description)
                    if image_id:
                        st.success("✅ Evidence photo saved successfully!")
                        
                        # Add a note about this evidence to the time entries
                        time_entry = {
                            "project": selected_project,
                            "resource": "System",  # Could also get the user's name from a global setting
                            "phase": selected_phase,
                            "date": date.today().strftime("%Y-%m-%d"),
                            "hours": 0,  # Zero hours as this is just recording evidence
                            "description": f"Evidence captured: {description} [ID: {image_id}]",
                            "entry_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "evidence_id": image_id
                        }
                        st.session_state.time_entries.append(time_entry)
                        save_data()
                        st.rerun()
                else:
                    st.error("Please upload a photo.")
            
            # Display existing evidence for this project
            st.subheader("Existing Evidence")
            
            # Filter evidence for this project
            project_evidence = {k: v for k, v in st.session_state.photo_evidence.items() 
                              if v.get('project') == selected_project}
            
            if project_evidence:
                # Display in a grid
                cols = st.columns(2)  # 2 columns for mobile
                
                for i, (image_id, metadata) in enumerate(project_evidence.items()):
                    col_idx = i % 2
                    with cols[col_idx]:
                        st.markdown(f"**{metadata.get('description', 'No description')}**")
                        st.markdown(f"Phase: {phase_options.get(metadata.get('phase', ''), metadata.get('phase', ''))}")
                        st.markdown(f"Date: {metadata.get('date', 'Unknown')}")
                        
                        # Try to display the image if it exists
                        try:
                            if os.path.exists(metadata.get('path', '')):
                                st.image(metadata.get('path', ''), width=150)
                            else:
                                st.info("Image file not found")
                        except Exception as e:
                            st.error(f"Error loading image: {e}")
                        
                        st.markdown("---")
            else:
                st.info("No evidence captured for this project yet.")
    else:
        st.info("No projects available. Please create a project first.")

# Mobile-friendly project progress card
def mobile_project_card(project):
    with st.container():
        st.markdown(f"### {project['company_name']}")
        st.markdown(f"**Industry:** {project['industry_name']}")
        
        # Progress bar
        total_planned = project['total_hours']
        total_actual = project.get('actual_hours', {}).get('total', 0)
        progress = (total_actual / total_planned * 100) if total_planned > 0 else 0
        
        st.progress(min(progress/100, 1.0))
        
        cols = st.columns(2)
        with cols[0]:
            st.metric("Planned", f"{total_planned}h")
        with cols[1]:
            st.metric("Actual", f"{total_actual}h", delta=f"{round(progress)}%")
        
        # Quick action buttons
        if st.button(f"Log Time for {project['company_name']}", key=f"log_{project['company_name']}"):
            st.session_state.current_project = project['company_name']
            st.session_state.app_mode = "Time Tracking"
            st.rerun()
            
        st.markdown("---")

# Mobile-friendly alerts and notifications
def show_mobile_notifications():
    alerts = []
    
    # Check for projects nearing budget
    for project_name, project in st.session_state.projects.items():
        total_planned = project['total_hours']
        total_actual = project.get('actual_hours', {}).get('total', 0)
        
        if total_actual > 0 and total_planned > 0:
            progress = (total_actual / total_planned * 100)
            
            # Alert if over 90% of budget
            if progress >= 90 and progress < 100:
                alerts.append({
                    "type": "warning",
                    "message": f"⚠️ {project_name} is at {round(progress)}% of budget"
                })
            # Alert if over budget
            elif progress >= 100:
                alerts.append({
                    "type": "error",
                    "message": f"🚨 {project_name} is over budget by {round(total_actual - total_planned)} hours"
                })
    
    # Display alerts
    if alerts:
        for alert in alerts:
            if alert["type"] == "warning":
                st.warning(alert["message"])
            elif alert["type"] == "error":
                st.error(alert["message"])
    else:
        st.success("No budget alerts at this time")

# Conditional rendering based on mobile/desktop view and selected mode
if is_mobile():
    # Mobile view implementation
    if app_mode == "Budget Calculator":
        st.markdown("#### Budget Calculator")
        st.info("For optimal experience, please use desktop view to create detailed budgets")
        
        # Simplified budget calculator for mobile
        st.markdown("#### Quick Budget Estimate")
        company_name = st.text_input("Company Name")
        turnover = st.number_input("Turnover (in Rs. Crore)", min_value=0.0, step=10.0)
        industry_sector = st.selectbox(
            "Industry",
            options=list(industry_sectors.keys()),
            format_func=lambda x: industry_sectors[x]["name"]
        )
        is_listed = st.checkbox("Listed Company")
        
        # Simplified risk factors
        risk_level = st.radio("Overall Risk Level", ["Low", "Medium", "High"])
        risk_mapping = {"Low": 1, "Medium": 2, "High": 3}
        
        if st.button("Generate Quick Estimate", use_container_width=True):
            if company_name and turnover > 0:
                # Use the same risk level for all risk factors
                risk_value = risk_mapping[risk_level]
                
                # This is where you would call your calculate_budget function
                # with the simplified parameters
                st.success(f"Budget estimate for {company_name} generated!")
                st.markdown("View detailed breakdown in desktop mode")
            else:
                st.error("Please enter company name and turnover.")
                
    elif app_mode == "Time Tracking":
        # Mobile optimized time tracking
        project_options = get_project_list()
        mobile_time_entry_form(project_options)
        
    elif app_mode == "Project Reports":
        # Mobile project overview
        st.subheader("Projects Overview")
        show_mobile_notifications()
        
        for project_name, project in st.session_state.projects.items():
            mobile_project_card(project)
            
    elif app_mode == "Team Reports":
        st.subheader("Your Recent Activity")
        
        # Get a simple view of recent time entries
        if st.session_state.time_entries:
            recent_entries = sorted(
                st.session_state.time_entries,
                key=lambda x: x.get('entry_time', ''),
                reverse=True
            )[:10]  # Get 10 most recent
            
            for entry in recent_entries:
                with st.container():
                    st.markdown(f"**{entry.get('project', 'Unknown Project')}**")
                    st.markdown(f"{entry.get('date', 'Unknown date')} - {entry.get('hours', 0)}h")
                    st.markdown(f"_{entry.get('description', 'No description')}_")
                    st.markdown("---")
        else:
            st.info("No time entries recorded yet")
            
    elif app_mode == "Evidence Capture":
        # Mobile optimized evidence capture
        project_options = get_project_list()
        mobile_evidence_capture_form(project_options)
        
else:
    # Desktop view implementation - your original tabbed interface
    # Note: I've only implementing the new Evidence Capture tab here as an example
    if app_mode == "Budget Calculator" or 'tab1' in locals():
        with tab1:
            st.markdown("Original Budget Calculator Tab Content")
            # Your existing budget calculator code would go here
    
    if app_mode == "Time Tracking" or 'tab2' in locals():
        with tab2:
            st.markdown("Original Time Tracking Tab Content")
            # Your existing time tracking code would go here
    
    if app_mode == "Project Reports" or 'tab3' in locals():
        with tab3:
            st.markdown("Original Project Reports Tab Content")
            # Your existing project reports code would go here
    
    if app_mode == "Team Reports" or 'tab4' in locals():
        with tab4:
            st.markdown("Original Team Reports Tab Content")
            # Your existing team reports code would go here
    
    if app_mode == "Evidence Capture" or 'tab5' in locals():
        with tab5:
            st.header("Audit Evidence Capture")
            st.markdown("Upload photos of audit evidence for documentation and review.")
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                # Desktop evidence upload form
                st.subheader("Upload Evidence")
                
                project_options = get_project_list()
                
                if "No projects available" not in project_options:
                    selected_project = st.selectbox(
                        "Project", 
                        options=project_options, 
                        key="desktop_evidence_project"
                    )
                    
                    if selected_project in st.session_state.projects:
                        project = st.session_state.projects[selected_project]
                        
                        phase_options = {
                            "planning": "Planning",
                            "fieldwork": "Fieldwork",
                            "managerReview": "Manager Review",
                            "partnerReview": "Partner Review"
                        }
                        
                        selected_phase = st.selectbox(
                            "Audit Phase",
                            options=list(phase_options.keys()),
                            format_func=lambda x: phase_options[x],
                            key="desktop_evidence_phase"
                        )
                        
                        description = st.text_area(
                            "Description",
                            "",
                            height=100,
                            key="desktop_evidence_desc"
                        )
                        
                        uploaded_file = st.file_uploader(
                            "Upload Photo", 
                            type=["jpg", "jpeg", "png"],
                            key="desktop_evidence_upload"
                        )
                        
                        if uploaded_file is not None:
                            st.image(uploaded_file, caption="Preview", width=300)
                        
                        if st.button("Save Evidence"):
                            if uploaded_file is not None:
                                # Save the image
                                image_id = save_image(
                                    uploaded_file,
                                    selected_project,
                                    selected_phase,
                                    description
                                )
                                
                                if image_id:
                                    st.success("Evidence saved successfully!")
                                    # Add system note
                                    time_entry = {
                                        "project": selected_project,
                                        "resource": "System",
                                        "phase": selected_phase,
                                        "date": date.today().strftime("%Y-%m-%d"),
                                        "hours": 0,
                                        "description": f"Evidence added: {description} [ID: {image_id}]",
                                        "entry_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "evidence_id": image_id
                                    }
                                    st.session_state.time_entries.append(time_entry)
                                    save_data()
                                    st.rerun()
                            else:
                                st.error("Please upload a photo.")
                else:
                    st.info("No projects available. Please create a project first.")
            
            with col2:
                # Evidence gallery
                st.subheader("Evidence Gallery")
                
                # Filter options
                filter_project = st.selectbox(
                    "Filter by Project",
                    options=["All Projects"] + get_project_list(),
                    key="gallery_filter_project"
                )
                
                # Get evidence matching filter
                if filter_project == "All Projects" or filter_project == "No projects available":
                    filtered_evidence = st.session_state.photo_evidence
                else:
                    filtered_evidence = {
                        k: v for k, v in st.session_state.photo_evidence.items() 
                        if v.get('project') == filter_project
                    }
                
                if filtered_evidence:
                    # Display in a grid - 3 columns for desktop
                    cols = st.columns(3)
                    
                    for i, (image_id, metadata) in enumerate(filtered_evidence.items()):
                        col_idx = i % 3
                        with cols[col_idx]:
                            st.markdown(f"**{metadata.get('description', 'No description')}**")
                            st.markdown(f"Project: {metadata.get('project', 'Unknown')}")
                            st.markdown(f"Phase: {phase_options.get(metadata.get('phase', ''), metadata.get('phase', ''))}")
                            st.markdown(f"Date: {metadata.get('date', 'Unknown')}")
                            
                            # Try to display the image
                            try:
                                if os.path.exists(metadata.get('path', '')):
                                    st.image(metadata.get('path', ''), width=200)
                                else:
                                    st.info("Image file not found")
                            except Exception as e:
                                st.error(f"Error loading image: {e}")
                            
                            st.markdown("---")
                else:
                    st.info("No evidence found matching the filter criteria.")

# Footer
st.markdown("---")
st.caption("Statutory Audit Budget Calculator & Time Tracker - Mobile Compatible")
