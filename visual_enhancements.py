import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import base64
from pathlib import Path

# Define color palette
COLOR_PRIMARY = "#4F6DF5"       # A softer blue as primary
COLOR_SECONDARY = "#05CE91"     # A teal green for success/action
COLOR_WARNING = "#FFA941"       # A warmer orange for warnings
COLOR_DANGER = "#F55252"        # A slightly softer red
COLOR_BACKGROUND = "#121726"    # A blue-tinted dark background
COLOR_CARD_BACKGROUND = "#1E2235"  # Slightly lighter for cards
COLOR_TEXT = "#F0F2F8"          # Off-white text for better readability
COLOR_TEXT_MUTED = "#A3B1D7"    # Blue-tinted gray for secondary text

# Function to apply custom styling
def enhance_visual_style():
    """Apply enhanced visual styles to the Streamlit app"""
    
    # Apply base theme
    st.markdown("""
    <style>
        /* Main background and text colors */
        .stApp {
            background-color: #121726;
            color: #F0F2F8;
        }
        
        /* Headers */
        h1, h2, h3, h4, h5, h6 {
            color: #F0F2F8 !important;
            font-family: 'Inter', 'Segoe UI', sans-serif !important;
            font-weight: 600 !important;
            letter-spacing: -0.01em !important;
        }
        
        /* Typography */
        body {
            font-family: 'Inter', 'Segoe UI', sans-serif !important;
            line-height: 1.6 !important;
            font-size: 16px !important;
        }
        
        /* Metrics */
        [data-testid="stMetricValue"] {
            background-color: #1E2235;
            border-radius: 8px;
            padding: 15px;
            color: #F0F2F8 !important;
            font-size: 28px !important;
            font-weight: 600 !important;
        }
        
        [data-testid="stMetricLabel"] {
            font-size: 14px !important;
            color: #A3B1D7 !important;
        }
        
        /* Metric delta colors */
        [data-testid="stMetricDelta"] svg {
            stroke: #05CE91 !important;
        }
        
        [data-testid="stMetricDelta"] [data-testid="stMetricDelta"] svg {
            stroke: #F55252 !important;
        }
        
        /* Tables */
        .stDataFrame {
            border-radius: 8px !important;
            overflow: hidden !important;
        }
        
        .stDataFrame table {
            border: 1px solid #2E344D !important;
        }
        
        .stDataFrame th {
            background-color: #222741 !important;
            color: #F0F2F8 !important;
            font-weight: 600 !important;
            border-bottom: 1px solid #2E344D !important;
            padding: 12px 24px !important;
            font-size: 14px !important;
        }
        
        .stDataFrame td {
            color: #F0F2F8 !important;
            border-bottom: 1px solid #222741 !important;
            background-color: #1E2235 !important;
            padding: 10px 24px !important;
            font-size: 14px !important;
        }
        
        /* Buttons */
        .stButton button {
            background-color: #4F6DF5 !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 6px !important;
            padding: 6px 18px !important;
            font-weight: 500 !important;
            transition: all 0.2s ease !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
        }
        
        .stButton button:hover {
            background-color: #3A56CC !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 8px rgba(0,0,0,0.15) !important;
        }
        
        /* Input fields */
        .stTextInput input, .stNumberInput input, .stDateInput input {
            background-color: #1A1F33 !important;
            color: #F0F2F8 !important;
            border: 1px solid #2E344D !important;
            border-radius: 6px !important;
            padding: 10px 12px !important;
        }
        
        .stTextInput input:focus, .stNumberInput input:focus, .stDateInput input:focus {
            border-color: #4F6DF5 !important;
            box-shadow: 0 0 0 2px rgba(79, 109, 245, 0.2) !important;
        }
        
        /* Select boxes */
        .stSelectbox > div > div {
            background-color: #1A1F33 !important;
            color: #F0F2F8 !important;
            border: 1px solid #2E344D !important;
            border-radius: 6px !important;
        }
        
        /* Dropdowns */
        .stSelectbox > div > div > div {
            background-color: #1A1F33 !important;
            color: #F0F2F8 !important;
        }
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            background-color: #1A1F33 !important;
            border-radius: 8px !important;
            padding: 5px !important;
        }
        
        .stTabs [data-baseweb="tab"] {
            color: #A3B1D7 !important;
            border-radius: 6px !important;
            padding: 8px 16px !important;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: #4F6DF5 !important;
            color: white !important;
        }
        
        /* Expanders */
        .streamlit-expanderHeader {
            background-color: #1E2235 !important;
            color: #F0F2F8 !important;
            border-radius: 6px !important;
            padding: 12px 15px !important;
            font-weight: 500 !important;
        }
        
        .streamlit-expanderContent {
            background-color: #1A1F33 !important;
            border: 1px solid #2E344D !important;
            border-radius: 0 0 6px 6px !important;
            padding: 15px !important;
        }
        
        /* Checkboxes */
        .stCheckbox > div > div > div {
            background-color: #4F6DF5 !important;
        }
        
        /* Radio buttons */
        .stRadio > div {
            background-color: transparent !important;
        }
        
        .stRadio label {
            color: #F0F2F8 !important;
            padding: 4px 8px !important;
        }
        
        /* Sidebar */
        [data-testid="stSidebar"] {
            background-color: #1A1F33 !important;
            border-right: 1px solid #2E344D !important;
        }
        
        [data-testid="stSidebar"] hr {
            border-color: #2E344D !important;
        }
        
        /* Info, warning and error boxes */
        .stInfo, .stSuccess {
            background-color: rgba(79, 109, 245, 0.1) !important;
            color: #F0F2F8 !important;
            border-left-color: #4F6DF5 !important;
            padding: 15px !important;
            border-radius: 0 6px 6px 0 !important;
        }
        
        .stWarning {
            background-color: rgba(255, 169, 65, 0.1) !important;
            color: #F0F2F8 !important;
            border-left-color: #FFA941 !important;
            padding: 15px !important;
            border-radius: 0 6px 6px 0 !important;
        }
        
        .stError {
            background-color: rgba(245, 82, 82, 0.1) !important;
            color: #F0F2F8 !important;
            border-left-color: #F55252 !important;
            padding: 15px !important;
            border-radius: 0 6px 6px 0 !important;
        }
        
        /* Slider */
        .stSlider div[data-baseweb="slider"] div {
            background-color: #4F6DF5 !important;
        }
        
        /* Pagination buttons */
        .stPagination button {
            background-color: #1E2235 !important;
            color: #F0F2F8 !important;
            border: 1px solid #2E344D !important;
        }
        
        .stPagination button:hover {
            background-color: #4F6DF5 !important;
        }
        
        /* Better spacing */
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 3rem !important;
            max-width: 1200px !important;
        }
        
        /* Progress bar */
        .stProgress > div > div > div > div {
            background-color: #4F6DF5 !important;
        }
        
        /* Text areas */
        .stTextArea textarea {
            background-color: #1A1F33 !important;
            color: #F0F2F8 !important;
            border: 1px solid #2E344D !important;
            border-radius: 6px !important;
        }
        
        .stTextArea textarea:focus {
            border-color: #4F6DF5 !important;
            box-shadow: 0 0 0 2px rgba(79, 109, 245, 0.2) !important;
        }
        
        /* File uploader */
        .stFileUploader {
            background-color: #1A1F33 !important;
            border: 1px dashed #2E344D !important;
            border-radius: 6px !important;
            padding: 15px !important;
        }
        
        .uploadedFile {
            background-color: #1A1F33 !important;
            color: #F0F2F8 !important;
            border: 1px solid #2E344D !important;
            border-radius: 6px !important;
        }
    </style>
    """, unsafe_allow_html=True)

# Function to create a consistent header
def create_header(logo_path=None):
    """Create a professional header with optional logo"""
    col1, col2 = st.columns([1, 5])
    
    with col1:
        if logo_path and Path(logo_path).exists():
            # If logo file exists, display it
            with open(logo_path, "rb") as img_file:
                img_bytes = img_file.read()
                encoded = base64.b64encode(img_bytes).decode()
                st.markdown(f"""
                <img src="data:image/png;base64,{encoded}" width="80px">
                """, unsafe_allow_html=True)
        else:
            # Display a default placeholder logo using CSS
            st.markdown("""
            <div style="background-color:#4F6DF5; width:60px; height:60px; border-radius:50%; display:flex; 
            justify-content:center; align-items:center; color:white; font-weight:bold; font-size:24px;">
            A
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <h1 style="color:#F0F2F8; margin-bottom:0; font-size:2.2rem;">Audit Budget Calculator</h1>
        <p style="color:#A3B1D7; margin-top:0; font-size:1.1rem;">Professional Audit Management Solution</p>
        """, unsafe_allow_html=True)
    
    st.markdown("<hr style='margin-top:0; margin-bottom:30px; border-color:#2E344D;'>", unsafe_allow_html=True)

# Function to create styled cards
def styled_card(title, content, icon=None):
    """Create a styled card with title and content"""
    icon_html = f"""<span style="margin-right:10px; font-size:1.3rem;">{icon}</span>""" if icon else ""
    
    st.markdown(f"""
    <div style="background-color:#1E2235; border-radius:10px; padding:20px; margin-bottom:20px; 
    border-left:4px solid #4F6DF5; box-shadow:0 4px 6px rgba(0,0,0,0.1);">
        <h3 style="color:#F0F2F8; margin-top:0; margin-bottom:15px; font-size:1.3rem;">{icon_html}{title}</h3>
        <div style="color:#F0F2F8;">{content}</div>
    </div>
    """, unsafe_allow_html=True)

# Function to create consistent section headers
def section_header(title, icon=None):
    """Create a styled section header"""
    icon_html = f"""<span style="margin-right:10px; font-size:1.5rem;">{icon}</span>""" if icon else ""
    
    st.markdown(f"""
    <div style="background-color:#1E2235; border-radius:10px; padding:15px 20px; margin-bottom:20px; 
    border-bottom:2px solid #4F6DF5;">
        <h2 style="color:#F0F2F8; margin:0; font-size:1.5rem;">{icon_html}{title}</h2>
    </div>
    """, unsafe_allow_html=True)

# Function to style Plotly charts
def style_plotly_chart(fig, title=None):
    """Apply consistent styling to Plotly charts"""
    fig.update_layout(
        font_family="Inter, Segoe UI, sans-serif",
        title_font_size=18,
        title_font_color="#F0F2F8",
        title=title,
        legend_title_font_color="#F0F2F8",
        legend_font_color="#A3B1D7",
        paper_bgcolor=COLOR_CARD_BACKGROUND,
        plot_bgcolor=COLOR_CARD_BACKGROUND,
        margin=dict(l=40, r=40, t=50, b=40),
    )
    
    fig.update_xaxes(
        gridcolor="#2E344D",
        zerolinecolor="#2E344D",
        tickfont=dict(color="#A3B1D7")
    )
    
    fig.update_yaxes(
        gridcolor="#2E344D",
        zerolinecolor="#2E344D",
        tickfont=dict(color="#A3B1D7")
    )
    
    return fig

# Function to create stats tiles
def stat_tile(title, value, subtitle=None, delta=None, delta_color="normal"):
    """Create a styled stat tile for dashboards"""
    delta_html = ""
    if delta is not None:
        delta_color_value = "#05CE91" if delta_color == "normal" else "#F55252" if delta_color == "inverse" else "#FFA941"
        delta_icon = "↑" if delta >= 0 else "↓"
        delta_html = f"""
        <div style="color:{delta_color_value}; font-size:0.9rem; margin-top:5px;">
            {delta_icon} {abs(delta)}%
        </div>
        """
    
    subtitle_html = f"""<div style="color:#A3B1D7; font-size:0.9rem; margin-top:5px;">{subtitle}</div>""" if subtitle else ""
    
    st.markdown(f"""
    <div style="background-color:#1E2235; border-radius:10px; padding:20px; text-align:center; height:100%;">
        <div style="color:#A3B1D7; font-size:0.9rem; margin-bottom:10px;">{title}</div>
        <div style="color:#F0F2F8; font-size:1.8rem; font-weight:600;">{value}</div>
        {subtitle_html}
        {delta_html}
    </div>
    """, unsafe_allow_html=True)

# Function to create a status indicator
def status_indicator(status):
    """Create a styled status indicator"""
    if status.lower() == "completed":
        return f"""<span style="color:#05CE91; font-weight:500;">✓ Completed</span>"""
    elif status.lower() == "in progress":
        return f"""<span style="color:#FFA941; font-weight:500;">⋯ In Progress</span>"""
    else:
        return f"""<span style="color:#A3B1D7; font-weight:500;">○ Not Started</span>"""

# Function to create progress indicators
def progress_indicator(percentage, label=None):
    """Create a styled progress indicator"""
    # Determine color based on percentage
    if percentage >= 80:
        color = "#05CE91"  # Green for high completion
    elif percentage >= 50:
        color = "#FFA941"  # Orange for medium completion
    else:
        color = "#F55252"  # Red for low completion
        
    label_html = f"""<div style="color:#A3B1D7; font-size:0.9rem; margin-bottom:5px;">{label}</div>""" if label else ""
    
    st.markdown(f"""
    {label_html}
    <div style="background-color:#2E344D; border-radius:5px; height:10px; width:100%;">
        <div style="background-color:{color}; width:{percentage}%; height:10px; border-radius:5px;"></div>
    </div>
    <div style="color:#F0F2F8; text-align:right; font-size:0.8rem; margin-top:3px;">{percentage}%</div>
    """, unsafe_allow_html=True)

# Create responsive grid
def responsive_grid(num_items, min_width=300):
    """Creates a responsive grid based on screen width and number of items"""
    # Calculate columns based on viewport width (approximation)
    viewport_width = 1000  # Approximate default width in Streamlit
    max_columns = max(1, viewport_width // min_width)
    columns = min(max_columns, num_items)
    return st.columns(columns)

# Demo usage for dashboard redesign
def sample_dashboard():
    """Creates a sample dashboard with the enhanced visual style"""
    # Apply the custom styling
    enhance_visual_style()
    
    # Create header
    create_header()
    
    # Section header
    section_header("Dashboard Overview", icon="📊")
    
    # Key metrics
    st.markdown("### Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        stat_tile("Total Projects", "24", delta=15)
    
    with col2:
        stat_tile("Active Projects", "12", subtitle="50% of total", delta=-8, delta_color="inverse")
    
    with col3:
        stat_tile("Team Members", "8", delta=0)
    
    with col4:
        stat_tile("Avg. Completion", "68%", subtitle="2% this week", delta=2)
    
    # Project status and charts
    st.markdown("### Project Status")
    
    # Two-column layout for charts
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        # Phase distribution chart
        phase_data = {
            'Phase': ['Planning', 'Fieldwork', 'Manager Review', 'Partner Review'],
            'Hours': [120, 350, 80, 40]
        }
        phase_df = pd.DataFrame(phase_data)
        
        fig = px.pie(
            phase_df, 
            values='Hours', 
            names='Phase',
            hole=0.4,
            color_discrete_sequence=['#4F6DF5', '#05CE91', '#FFA941', '#F55252']
        )
        
        fig = style_plotly_chart(fig, title="Hours by Audit Phase")
        st.plotly_chart(fig, use_container_width=True)
        
        # Add progress indicators below
        st.markdown("#### Phase Completion")
        progress_indicator(85, "Planning")
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        progress_indicator(62, "Fieldwork")
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        progress_indicator(35, "Manager Review")
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        progress_indicator(10, "Partner Review")
    
    with chart_col2:
        # Team utilization chart
        team_data = {
            'Team Member': ['John D.', 'Sarah M.', 'Michael T.', 'Linda K.', 'Robert P.'],
            'Hours': [145, 132, 98, 76, 42]
        }
        team_df = pd.DataFrame(team_data)
        
        fig = px.bar(
            team_df,
            y='Team Member',
            x='Hours',
            orientation='h',
            color='Hours',
            color_continuous_scale=['#1E2235', '#4F6DF5'],
            height=400
        )
        
        fig = style_plotly_chart(fig, title="Team Member Utilization")
        st.plotly_chart(fig, use_container_width=True)
    
    # Project list with enhanced styling
    st.markdown("### Active Projects")
    
    # Create sample project data
    projects_data = {
        'Project': ['ABC Corporation', 'XYZ Enterprises', 'Northern Holdings', 'Tech Solutions'],
        'Category': ['Medium', 'Large', 'Small', 'Medium'],
        'Industry': ['Manufacturing', 'Technology', 'Retail', 'Financial Services'],
        'Planned Hours': [320, 450, 180, 280],
        'Actual Hours': [272, 225, 162, 84],
        'Completion': [85, 50, 90, 30],
        'Status': ['In Progress', 'In Progress', 'In Progress', 'Not Started']
    }
    
    projects_df = pd.DataFrame(projects_data)
    
    # Display as a styled table
    for i, project in projects_df.iterrows():
        with st.container():
            st.markdown(f"""
            <div style="background-color:#1E2235; border-radius:8px; padding:15px; margin-bottom:15px; border-left:4px solid 
            {'#05CE91' if project['Completion'] >= 80 else '#FFA941' if project['Completion'] >= 40 else '#F55252'};">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <h3 style="margin:0; font-size:1.2rem; color:#F0F2F8;">{project['Project']}</h3>
                        <div style="color:#A3B1D7; font-size:0.9rem; margin-top:3px;">
                            {project['Category']} | {project['Industry']}
                        </div>
                    </div>
                    <div style="text-align:right;">
                        <div style="color:#F0F2F8; font-weight:600; font-size:1.1rem;">
                            {project['Actual Hours']} / {project['Planned Hours']} hrs
                        </div>
                        <div style="margin-top:5px;">
                            {status_indicator(project['Status'])}
                        </div>
                    </div>
                </div>
                <div style="margin-top:12px;">
                    <div style="background-color:#2E344D; border-radius:5px; height:8px; width:100%;">
                        <div style="background-color:
                        {'#05CE91' if project['Completion'] >= 80 else '#FFA941' if project['Completion'] >= 40 else '#F55252'}; 
                        width:{project['Completion']}%; height:8px; border-radius:5px;"></div>
                    </div>
                    <div style="display:flex; justify-content:space-between; margin-top:3px;">
                        <span style="color:#A3B1D7; font-size:0.8rem;">Progress</span>
                        <span style="color:#F0F2F8; font-size:0.8rem;">{project['Completion']}%</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Recent activity feed
    st.markdown("### Recent Activity")
    
    # Sample activity data
    activities = [
        {"user": "Robert P.", "action": "added 8 hours to", "project": "ABC Corporation", "phase": "Fieldwork", "time": "2 hours ago"},
        {"user": "Sarah M.", "action": "completed", "project": "Tech Solutions", "phase": "Planning", "time": "Yesterday"},
        {"user": "John D.", "action": "added new project", "project": "Global Traders", "phase": "", "time": "Yesterday"},
        {"user": "Linda K.", "action": "updated budget for", "project": "Northern Holdings", "phase": "", "time": "2 days ago"},
    ]
    
    # Display as styled activity feed
    for activity in activities:
        phase_info = f" - {activity['phase']}" if activity['phase'] else ""
        st.markdown(f"""
        <div style="display:flex; align-items:center; padding:8px 5px; border-bottom:1px solid #2E344D;">
            <div style="background-color:#4F6DF5; width:36px; height:36px; border-radius:50%; display:flex; 
            justify-content:center; align-items:center; color:white; font-weight:bold; margin-right:15px;">
            {activity['user'][0]}
            </div>
            <div style="flex-grow:1;">
                <div style="color:#F0F2F8;">
                    <span style="font-weight:500;">{activity['user']}</span> {activity['action']} 
                    <span style="color:#4F6DF5;">{activity['project']}</span>{phase_info}
                </div>
                <div style="color:#A3B1D7; font-size:0.8rem;">{activity['time']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# Function to improve the budget calculator screen
def enhance_budget_calculator():
    """Apply enhanced styling to the budget calculator screen"""
    # Section header
    section_header("Budget Calculator", icon="💼")
    
    # Create a cleaner two-column layout
    col1, col2 = st.columns([3, 2])
    
    with col1:
        # Input form with better styling
        st.markdown("""
        <div style="background-color:#1E2235; border-radius:10px; padding:20px; margin-bottom:20px;">
            <h3 style="color:#F0F2F8; margin-top:0; margin-bottom:15px;">Project Details</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Form fields would go here
        
    with col2:
        # Risk assessment with better styling
        st.markdown("""
        <div style="background-color:#1E2235; border-radius:10px; padding:20px; margin-bottom:20px;">
            <h3 style="color:#F0F2F8; margin-top:0; margin-bottom:15px;">Risk Assessment</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Risk assessment fields would go here

# Function to improve the time tracking screen
def enhance_time_tracking():
    """Apply enhanced styling to the time tracking screen"""
    # Section header
    section_header("Time Tracking", icon="⏱️")
    
    # Create a two-column layout
    col1, col2 = st.columns([2, 3])
    
    with col1:
        # Time entry form
        st.markdown("""
        <div style="background-color:#1E2235; border-radius:10px; padding:20px; margin-bottom:20px;">
            <h3 style="color:#F0F2F8; margin-top:0; margin-bottom:15px;">Record Time</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Form fields would go here
        
    with col2:
        # Current time entries
        st.markdown("""
        <div style="background-color:#1E2235; border-radius:10px; padding:20px; margin-bottom:20px;">
            <h3 style="color:#F0F2F8; margin-top:0; margin-bottom:15px;">Recent Time Entries</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Time entries table would go here

# Main function to implement all visual enhancements
def implement_visual_enhancements():
    """Implement all visual enhancements to the application"""
    # Apply the base styling
    enhance_visual_style()
    
    # Create header
    create_header()
    
    # Check the current tab and apply appropriate enhancements
    # This would need to be integrated with your tab system
    
    # Example usage:
    # if current_tab == "Dashboard":
    #     sample_dashboard()
    # elif current_tab == "Budget Calculator":
    #     enhance_budget_calculator()
    # elif current_tab == "Time Tracking":
    #     enhance_time_tracking()
    # etc.

# This would typically be called at the beginning of your app
# implement_visual_enhancements()