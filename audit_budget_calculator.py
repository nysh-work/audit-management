import os
import sqlite3
import json
import shutil
import glob
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
import tempfile
import uuid
import io
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import tabula  # For PDF table extraction
import pytesseract # For OCR
import PyPDF2 # For merge function
from pdf2image import convert_from_bytes  # For scanned PDFs
import yaml
from yaml.loader import SafeLoader
from PIL import Image

# Load the image
icon_path = "streamlit_icon.png"
icon_image = Image.open(icon_path)

# Set the favicon
st.set_page_config(page_title="Audit Management Tool", page_icon=icon_image)

# Define the app data directory
home_dir = str(Path.home())
app_data_dir = os.path.join(home_dir, '.audit_management_app')
os.makedirs(app_data_dir, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(app_data_dir, 'app.log')),
        logging.StreamHandler()
    ]
)

# Log application start
logging.info("Application starting...")

# Define the database location (can be changed if needed)
def get_db_path():
    """Returns the path to the database file."""
    home_dir = str(Path.home())
    app_data_dir = os.path.join(home_dir, '.audit_management_app')
    data_dir = os.path.join(app_data_dir, 'data')
    db_file = os.path.join(data_dir, 'audit_management.db')
    os.makedirs(data_dir, exist_ok=True)
    return db_file

def init_db():
    """Initializes the SQLite database and creates tables if they don't exist."""
    try:
        db_path = get_db_path()
        logging.info("Initializing database at %s", db_path)
        conn = sqlite3.connect(db_path, check_same_thread=False)
        c = conn.cursor()

        # Create tables if they don't exist
        c.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL,
                client_code TEXT UNIQUE NOT NULL,
                business_sector TEXT NOT NULL,
                latest_turnover REAL NOT NULL,
                previous_year_turnover REAL NOT NULL,
                latest_borrowings REAL,
                previous_year_borrowings REAL,
                latest_profit_before_tax REAL NOT NULL,
                previous_year_profit_before_tax REAL NOT NULL,
                latest_net_worth REAL NOT NULL,
                previous_year_net_worth REAL NOT NULL,
                signing_director_1 TEXT NOT NULL,
                signing_director_2 TEXT NOT NULL,
                company_secretary TEXT,
                chief_financial_officer TEXT,
                managing_director TEXT,
                signing_director_3 TEXT
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                data TEXT,
                creation_date TEXT
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS time_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project TEXT,
                resource TEXT,
                phase TEXT,
                date TEXT,
                hours REAL,
                description TEXT,
                entry_time TEXT
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS team_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                role TEXT,
                skills TEXT,
                availability_hours REAL DEFAULT 40.0,
                hourly_rate REAL DEFAULT 0.0,
                data TEXT
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS schedule_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_member TEXT,
                project TEXT,
                start_date TEXT,
                end_date TEXT,
                hours_per_day REAL DEFAULT 8.0,
                phase TEXT,
                status TEXT DEFAULT 'scheduled',
                notes TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        ''')

        conn.commit()
        return conn
    except Exception as e:
        error_msg = "Database initialization error: %s" % str(e)
        logging.error(error_msg)
        st.error(error_msg)
        raise

def add_client(client_data):
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    try:
        c.execute('''
            INSERT INTO clients (
                client_name, client_code, business_sector, latest_turnover, previous_year_turnover,
                latest_borrowings, previous_year_borrowings, latest_profit_before_tax, previous_year_profit_before_tax,
                latest_net_worth, previous_year_net_worth, signing_director_1, signing_director_2,
                company_secretary, chief_financial_officer, managing_director, signing_director_3
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            client_data['client_name'], client_data['client_code'], client_data['business_sector'],
            client_data['latest_turnover'], client_data['previous_year_turnover'],
            client_data['latest_borrowings'], client_data['previous_year_borrowings'],
            client_data['latest_profit_before_tax'], client_data['previous_year_profit_before_tax'],
            client_data['latest_net_worth'], client_data['previous_year_net_worth'],
            client_data['signing_director_1'], client_data['signing_director_2'],
            client_data.get('company_secretary'), client_data.get('chief_financial_officer'),
            client_data.get('managing_director'), client_data.get('signing_director_3')
        ))

        conn.commit()
        return True, "Client added successfully"
    except sqlite3.IntegrityError as e:
        return False, f"Error: Client code must be unique. {str(e)}"
    except Exception as e:
        return False, f"Error adding client: {str(e)}"
    finally:
        conn.close()

def save_projects_to_db():
    """Saves projects from session state to the database."""
    conn = init_db()
    c = conn.cursor()
    c.execute("DELETE FROM projects")

    for name, project_data in st.session_state.projects.items():
        project_json = json.dumps(project_data)
        creation_date = project_data.get('creation_date', datetime.now().strftime("%Y-%m-%d"))
        c.execute("INSERT INTO projects (name, data, creation_date) VALUES (?, ?, ?)",
                  (name, project_json, creation_date))

    conn.commit()
    conn.close()

def load_projects_from_db():
    """Loads projects from the database into session state."""
    conn = init_db()
    c = conn.cursor()
    c.execute("SELECT name, data FROM projects")
    projects = {name: json.loads(data) for name, data in c.fetchall()}
    conn.close()
    return projects

def save_time_entries_to_db():
    """Saves time entries from session state to the database."""
    conn = init_db()
    c = conn.cursor()
    c.execute("DELETE FROM time_entries")

    for entry in st.session_state.time_entries:
        c.execute("""
            INSERT INTO time_entries (project, resource, phase, date, hours, description, entry_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.get('project', ''),
            entry.get('resource', ''),
            entry.get('phase', ''),
            entry.get('date', ''),
            entry.get('hours', 0),
            entry.get('description', ''),
            entry.get('entry_time', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        ))

    conn.commit()
    conn.close()

def load_time_entries_from_db():
    """Loads time entries from the database into session state."""
    conn = init_db()
    c = conn.cursor()
    c.execute("SELECT project, resource, phase, date, hours, description, entry_time FROM time_entries")
    time_entries = [
        {
            'project': project,
            'resource': resource,
            'phase': phase,
            'date': date,
            'hours': hours,
            'description': description,
            'entry_time': entry_time
        } for project, resource, phase, date, hours, description, entry_time in c.fetchall()
    ]
    conn.close()
    return time_entries

def load_team_members_from_db():
    """Loads team members from the database into session state."""
    conn = init_db()
    c = conn.cursor()
    c.execute("SELECT name, role, skills, availability_hours, hourly_rate, data FROM team_members")
    team_members = {}
    for name, role, skills, availability_hours, hourly_rate, data in c.fetchall():
        team_member = {
            'name': name,
            'role': role,
            'skills': skills.split(',') if skills else [],
            'availability_hours': availability_hours,
            'hourly_rate': hourly_rate
        }
        if data:
            team_member.update(json.loads(data))
        team_members[name] = team_member
    conn.close()
    return team_members

def save_team_members_to_db():
    """Saves team members from session state to the database."""
    conn = init_db()
    c = conn.cursor()
    c.execute("DELETE FROM team_members")

    for name, member in st.session_state.team_members.items():
        skills = ','.join(member.get('skills', []))
        role = member.get('role', '')
        availability_hours = member.get('availability_hours', 40.0)
        hourly_rate = member.get('hourly_rate', 0.0)
        core_fields = {'name', 'role', 'skills', 'availability_hours', 'hourly_rate'}
        additional_data = {k: v for k, v in member.items() if k not in core_fields}
        data_json = json.dumps(additional_data) if additional_data else None

        c.execute("""
            INSERT INTO team_members (name, role, skills, availability_hours, hourly_rate, data)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, role, skills, availability_hours, hourly_rate, data_json))

    conn.commit()
    conn.close()

def load_schedule_entries_from_db():
    """Loads schedule entries from the database into session state."""
    conn = init_db()
    c = conn.cursor()
    c.execute("""
        SELECT team_member, project, start_date, end_date, hours_per_day,
               phase, status, notes, created_at, updated_at
        FROM schedule_entries
    """)
    schedule_entries = [
        {
            'team_member': team_member,
            'project': project,
            'start_date': start_date,
            'end_date': end_date,
            'hours_per_day': hours_per_day,
            'phase': phase,
            'status': status,
            'notes': notes,
            'created_at': created_at,
            'updated_at': updated_at
        } for team_member, project, start_date, end_date, hours_per_day,
            phase, status, notes, created_at, updated_at in c.fetchall()
    ]
    conn.close()
    return schedule_entries

def save_schedule_entries_to_db():
    """Saves schedule entries from session state to the database."""
    conn = init_db()
    c = conn.cursor()
    c.execute("DELETE FROM schedule_entries")

    for entry in st.session_state.schedule_entries:
        c.execute("""
            INSERT INTO schedule_entries (
                team_member, project, start_date, end_date, hours_per_day,
                phase, status, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.get('team_member', ''),
            entry.get('project', ''),
            entry.get('start_date', ''),
            entry.get('end_date', ''),
            entry.get('hours_per_day', 8.0),
            entry.get('phase', ''),
            entry.get('status', 'scheduled'),
            entry.get('notes', ''),
            entry.get('created_at', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            entry.get('updated_at', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        ))

    conn.commit()
    conn.close()

def save_clients_to_db():
    """Saves clients from session state to the database."""
    conn = init_db()
    c = conn.cursor()
    c.execute("DELETE FROM clients")

    for client_name, client_data in st.session_state.clients.items():
        c.execute('''
            INSERT INTO clients (
                client_name, client_code, business_sector, latest_turnover, previous_year_turnover,
                latest_borrowings, previous_year_borrowings, latest_profit_before_tax, previous_year_profit_before_tax,
                latest_net_worth, previous_year_net_worth, signing_director_1, signing_director_2,
                company_secretary, chief_financial_officer, managing_director, signing_director_3
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            client_data['client_name'], client_data['client_code'], client_data['business_sector'],
            client_data['latest_turnover'], client_data['previous_year_turnover'],
            client_data['latest_borrowings'], client_data['previous_year_borrowings'],
            client_data['latest_profit_before_tax'], client_data['previous_year_profit_before_tax'],
            client_data['latest_net_worth'], client_data['previous_year_net_worth'],
            client_data['signing_director_1'], client_data['signing_director_2'],
            client_data.get('company_secretary'), client_data.get('chief_financial_officer'),
            client_data.get('managing_director'), client_data.get('signing_director_3')
        ))

    conn.commit()
    conn.close()

def load_clients_from_db():
    """Loads clients from the database into session state."""
    conn = init_db()
    c = conn.cursor()
    c.execute('''
        SELECT client_name, client_code, business_sector, latest_turnover, previous_year_turnover,
               latest_borrowings, previous_year_borrowings, latest_profit_before_tax, previous_year_profit_before_tax,
               latest_net_worth, previous_year_net_worth, signing_director_1, signing_director_2,
               company_secretary, chief_financial_officer, managing_director, signing_director_3
        FROM clients
    ''')
    clients = {}
    for row in c.fetchall():
        client_data = {
            'client_name': row[0],
            'client_code': row[1],
            'business_sector': row[2],
            'latest_turnover': row[3],
            'previous_year_turnover': row[4],
            'latest_borrowings': row[5],
            'previous_year_borrowings': row[6],
            'latest_profit_before_tax': row[7],
            'previous_year_profit_before_tax': row[8],
            'latest_net_worth': row[9],
            'previous_year_net_worth': row[10],
            'signing_director_1': row[11],
            'signing_director_2': row[12],
            'company_secretary': row[13],
            'chief_financial_officer': row[14],
            'managing_director': row[15],
            'signing_director_3': row[16]
        }
        clients[row[0]] = client_data
    conn.close()
    return clients

def save_data():
    """Saves project and time entry data to the database and backup files."""
    save_projects_to_db()
    save_time_entries_to_db()
    save_team_members_to_db()
    save_schedule_entries_to_db()
    save_clients_to_db()

def load_data():
    """Loads project and time entry data from the database, with fallback to files."""
    try:
        st.session_state.projects = load_projects_from_db()
        st.session_state.time_entries = load_time_entries_from_db()
        st.session_state.team_members = load_team_members_from_db()
        st.session_state.schedule_entries = load_schedule_entries_from_db()
        st.session_state.clients = load_clients_from_db()
    except Exception as e:
        error_msg = f"Error loading data: {str(e)}"
        logging.error(error_msg)
        st.error(error_msg)
        if 'projects' not in st.session_state:
            st.session_state.projects = {}
        if 'time_entries' not in st.session_state:
            st.session_state.time_entries = []

# Initialize session state
if 'projects' not in st.session_state:
    st.session_state.projects = {}
if 'time_entries' not in st.session_state:
    st.session_state.time_entries = []
if 'current_project' not in st.session_state:
    st.session_state.current_project = {}
if 'team_members' not in st.session_state:
    st.session_state.team_members = {}
if 'schedule_entries' not in st.session_state:
    st.session_state.schedule_entries = []
if 'clients' not in st.session_state:
    st.session_state.clients = {}
if 'sidebar_authenticated' not in st.session_state:
    st.session_state.sidebar_authenticated = False
if 'sidebar_password_attempt' not in st.session_state:
    st.session_state.sidebar_password_attempt = False
if 'show_materiality_calculator' not in st.session_state:
    st.session_state.show_materiality_calculator = False
if 'theme' not in st.session_state:
    st.session_state.theme = 'dark'

# Load initial data
load_data()

# Function to create a professional header
def create_header():
    col1, col2 = st.columns([1, 5])
    with col1:
        st.image(icon_image, width=60)
    with col2:
        st.markdown("""
            <h1 style="color:#F0F2F8; margin-bottom:0; font-size:2.2rem;">Audit Management Tool</h1>
            <p style="color:#A3B1D7; margin-top:0; font-size:1.1rem;">Varma & Varma Chartered Accountants</p>
        """, unsafe_allow_html=True)
    st.markdown("<hr style='margin-top:0; margin-bottom:30px; border-color:#2E344D;'>", unsafe_allow_html=True)

# Apply visual enhancements
def enhance_visual_style():
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
            padding: 12px 24px ! important;
            font-size: 14px !important;
        }
        .stDataFrame td {
            color: #F0F2F8 !important;
            border-bottom: 1px solid #222741 !important;
            background-color: #1E2235 !important;
            padding: 10px 24px ! important;
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

    st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    """, unsafe_allow_html=True)

# Load the image
icon_path = "streamlit_icon.png"
icon_image = Image.open(icon_path)

# Function to create a professional header
def create_header():
    """Create a professional header for the application"""
    col1, col2 = st.columns([1, 5])

    with col1:
        # Display the logo image
        st.image(icon_image, width=60)

    with col2:
        st.markdown("""
        <h1 style="color:#F0F2F8; margin-bottom:0; font-size:2.2rem;">Audit Management Tool</h1>
        <p style="color:#A3B1D7; margin-top:0; font-size:1.1rem;">Varma & Varma Chartered Accountants</p>
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

# --- APP LOGIC AND UI ---
# Initialize session state
if 'projects' not in st.session_state:
    st.session_state.projects = {}
if 'time_entries' not in st.session_state:
    st.session_state.time_entries = []
if 'current_project' not in st.session_state:
    st.session_state.current_project = {}
if 'team_members' not in st.session_state:
    st.session_state.team_members = {}
if 'schedule_entries' not in st.session_state:
    st.session_state.schedule_entries = []
if 'clients' not in st.session_state:
    st.session_state.clients = {}
if 'sidebar_authenticated' not in st.session_state:
    st.session_state.sidebar_authenticated = False
if 'sidebar_password_attempt' not in st.session_state:
    st.session_state.sidebar_password_attempt = False
if 'show_materiality_calculator' not in st.session_state:
    st.session_state.show_materiality_calculator = False
if 'theme' not in st.session_state:  # Example for theme switching (optional)
    st.session_state.theme = 'dark'

# Load initial data
load_data()

# --- SIDEBAR ---
SIDEBAR_PASSWORD = os.environ.get("SIDEBAR_PASSWORD", "Athens@425")  # Use environment variable

def toggle_theme():
    if 'theme' not in st.session_state:
        st.session_state.theme = 'dark'
    else:
        st.session_state.theme = 'light' if st.session_state.theme == 'dark' else 'dark'

with st.sidebar:
    st.title("Audit Management")

    # Theme toggle
    st.button('Toggle Light/Dark Mode', on_click=toggle_theme)

    # Materiality Calculator (Corrected integration)
    with st.expander("Materiality Calculator", expanded=False):
        st.markdown("### Materiality Calculator")
        st.caption("Calculate audit materiality based on ISA 320 guidelines.")
        if st.button("Open Materiality Calculator"):
            create_materiality_calculator_dialog()

    # Add converter tool expander
    with st.expander("PDF Converter Tool", expanded=False):
        st.markdown("### Convert PDF to Excel/CSV")
        st.caption("Upload a PDF file containing tables to convert to Excel or CSV format.")

        uploaded_file = st.file_uploader("Choose a PDF file", type="pdf", key="pdf_converter")

        if uploaded_file is not None:
            # Create a tab system for different conversion options
            converter_tabs = st.tabs(["Simple Tables", "Complex Tables", "Scanned PDF"])

            with converter_tabs[0]:
                st.caption("Use this for PDFs with simple, well-defined tables")
                pages = st.text_input("Pages to extract (e.g. 1,3-5 or 'all')", "all")
                export_format = st.radio("Export Format", ["Individual Tables", "Combined Excel (all tables)", "Combined CSV (all tables)"])

                if st.button("Convert Simple Tables", key="convert_simple"):
                    # Save uploaded PDF temporarily
                    with st.spinner("Processing PDF..."):
                        try:

                            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                                tmp_file.write(uploaded_file.getvalue())
                                pdf_path = tmp_file.name

                            # Parse pages parameter
                            if pages.lower() == 'all':
                                page_numbers = None
                            else:
                                page_numbers = []
                                for page_range in pages.split(','):
                                    if '-' in page_range:
                                        start, end = map(int, page_range.split('-'))
                                        page_numbers.extend(range(start, end + 1))
                                    else:
                                        page_numbers.append(int(page_range))

                            # Extract tables
                            tables = tabula.read_pdf(pdf_path,
                                                   pages=pages if pages.lower() != 'all' else 'all',
                                                   multiple_tables=True)

                            # Remove temporary file
                            os.unlink(pdf_path)

                            if len(tables) == 0:
                                st.error("No tables found in the PDF. Try the Complex Tables or Scanned PDF options.")
                            else:
                                # Display and provide download options for each table
                                for i, table in enumerate(tables):
                                    st.subheader(f"Table {i+1}")
                                    st.dataframe(table, height=150)

                                    # Create Excel download
                                    excel_buffer = io.BytesIO()
                                    # Create a single Excel file with multiple sheets
                                    combined_excel_buffer = io.BytesIO()
                                    with pd.ExcelWriter(combined_excel_buffer, engine='xlsxwriter') as writer:
                                        for i, table in enumerate(tables):
                                            sheet_name = f'Table_{i+1}'

                                            # Prepare column names if they're numeric or empty
                                            if table.columns.dtype == 'int64' or table.columns.isna().any():
                                                table.columns = [f'Column_{j+1}' for j in range(len(table.columns))]

                                            table.to_excel(writer, sheet_name=sheet_name, index=False)

                                            # Add some formatting
                                            workbook = writer.book
                                            worksheet = writer.sheets[sheet_name]

                                            # Format headers
                                            header_format = workbook.add_format({
                                                'bold': True,
                                                'text_wrap': True,
                                                'valign': 'top',
                                                'fg_color': '#D7E4BC',
                                                'border': 1
                                            })

                                            # Apply header format
                                            for col_num, value in enumerate(table.columns.values):
                                                worksheet.write(0, col_num, value, header_format)

                                            # Auto-fit columns
                                            for col_num, column in enumerate(table.columns):
                                                column_width = max(
                                                    table[column].astype(str).map(len).max(),
                                                    len(str(column))
                                                )
                                                worksheet.set_column(col_num, col_num, column_width + 2)

                                    combined_excel_data = combined_excel_buffer.getvalue()

                                    # Provide download button for combined Excel
                                    st.download_button(
                                        label="Download All Tables as Excel",
                                        data=combined_excel_data,
                                        file_name=f"{uploaded_file.name.split('.')[0]}_all_tables.xlsx",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                    )

                                # Handle other export formats within the loop
                                if export_format == "Combined Excel (all tables)":
                                     # ... existing Combined Excel code ...
                                     pass #already handled
                                elif export_format == "Combined CSV (all tables)":  # Correct placement
                                        # Create a single CSV file with all tables concatenated
                                        # First add a separator column to identify the tables
                                        all_tables = []
                                        for i, table in enumerate(tables):
                                            # Add a table identifier column
                                            table['Table_Number'] = i + 1
                                            all_tables.append(table)

                                        # Concatenate all tables
                                        combined_df = pd.concat(all_tables, ignore_index=True)

                                        # Create CSV download
                                        csv_data = combined_df.to_csv(index=False).encode('utf-8')

                                        # Provide download button for combined CSV
                                        st.download_button(
                                            label="Download All Tables as CSV",
                                            data=csv_data,
                                            file_name=f"{uploaded_file.name.split('.')[0]}_all_tables.csv",
                                            mime="text/csv"
                                        )

                        except Exception as e:
                            st.error(f"Error processing simple tables: {str(e)}")

            with converter_tabs[1]:
                st.caption("Use this for PDFs with complex tables, merged cells, or unusual layouts")
                area = st.text_input("Area to extract (top,left,bottom,right in % of page, e.g. '10,10,90,90')", "")
                complex_pages = st.text_input("Pages to extract", "1")
                complex_export_format = st.radio(
                    "Export Format",
                    ["Individual Tables", "Combined Excel (all tables)", "Combined CSV (all tables)"],
                    key="complex_export_format"
                )

                if st.button("Convert Complex Tables", key="convert_complex"):
                    with st.spinner("Processing complex tables..."):
                        try:
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                                tmp_file.write(uploaded_file.getvalue())
                                pdf_path = tmp_file.name

                            # Parse area parameter
                            area_rect = None
                            if area:
                                try:
                                    area_rect = [float(x) for x in area.split(',')]
                                except:
                                    st.error("Invalid area format. Use top,left,bottom,right in % of page.")

                            # Extract tables with more advanced options
                            tables = tabula.read_pdf(
                                pdf_path,
                                pages=complex_pages,
                                multiple_tables=True,
                                area=area_rect,
                                lattice=True,  # For tables with ruling lines
                                guess=True     # Try to guess table structure
                            )

                            # Remove temporary file
                            os.unlink(pdf_path)

                            if len(tables) == 0:
                                st.error("No tables found in the PDF. Try different area coordinates or the Scanned PDF option.")
                            else:

                                if complex_export_format == "Individual Tables":
                                    # Display and provide download options for each table
                                    for i, table in enumerate(tables):
                                        st.subheader(f"Table {i+1}")
                                        st.dataframe(table, height=150)
                                        col1, col2 = st.columns(2)

                                        # Create Excel download
                                        excel_buffer = io.BytesIO()
                                        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                                            table.to_excel(writer, sheet_name=f'Table_{i+1}', index=False)
                                        excel_data = excel_buffer.getvalue()

                                        # Create CSV download
                                        csv_buffer = io.BytesIO()
                                        table.to_csv(csv_buffer, index=False)
                                        csv_data = csv_buffer.getvalue()

                                        with col1:
                                            st.download_button(
                                                label=f"Download Table {i+1} as Excel",
                                                data=excel_data,
                                                file_name=f"table_{i+1}.xlsx",
                                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                            )
                                        with col2:
                                            st.download_button(
                                                label=f"Download Table {i+1} as CSV",
                                                data=csv_data,
                                                file_name=f"table_{i+1}.csv",
                                                mime="text/csv"
                                            )

                                elif complex_export_format == "Combined Excel (all tables)":
                                    # Create a single Excel file with multiple sheets
                                    combined_excel_buffer = io.BytesIO()
                                    with pd.ExcelWriter(combined_excel_buffer, engine='xlsxwriter') as writer:
                                        for i, table in enumerate(tables):
                                            sheet_name = f'Table_{i+1}'

                                            # Prepare column names if they're numeric or empty
                                            if table.columns.dtype == 'int64' or table.columns.isna().any():
                                                table.columns = [f'Column_{j+1}' for j in range(len(table.columns))]

                                            table.to_excel(writer, sheet_name=sheet_name, index=False)

                                            # Add some formatting
                                            workbook = writer.book
                                            worksheet = writer.sheets[sheet_name]

                                            # Format headers
                                            header_format = workbook.add_format({
                                                'bold': True,
                                                'text_wrap': True,
                                                'valign': 'top',
                                                'fg_color': '#D7E4BC',
                                                'border': 1
                                            })

                                            # Apply header format
                                            for col_num, value in enumerate(table.columns.values):
                                                worksheet.write(0, col_num, value, header_format)

                                            # Auto-fit columns
                                            for col_num, column in enumerate(table.columns):
                                                column_width = max(
                                                    table[column].astype(str).map(len).max(),
                                                    len(str(column))
                                                )
                                                worksheet.set_column(col_num, col_num, column_width + 2)

                                    combined_excel_data = combined_excel_buffer.getvalue()

                                    # Provide download button for combined Excel
                                    st.download_button(
                                        label="Download All Tables as Excel",
                                        data=combined_excel_data,
                                        file_name=f"{uploaded_file.name.split('.')[0]}_all_tables.xlsx",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                    )

                                elif complex_export_format == "Combined CSV (all tables)":
                                    # Create a single CSV file with all tables concatenated
                                    all_tables = []
                                    for i, table in enumerate(tables):
                                       # Add a table identifier column
                                        table['Table_Number'] = i + 1
                                        all_tables.append(table)

                                    # Concatenate all tables
                                    combined_df = pd.concat(all_tables, ignore_index=True)

                                    # Create CSV download
                                    csv_data = combined_df.to_csv(index=False).encode('utf-8')
                                    st.download_button(
                                        label="Download All Tables as CSV",
                                        data=csv_data,
                                        file_name=f"{uploaded_file.name.split('.')[0]}_all_tables.csv",
                                        mime="text/csv"
                                    )
                        except Exception as e:
                            st.error(f"Error processing complex tables: {str(e)}")

            with converter_tabs[2]:
                st.caption("Use this for scanned PDFs that need OCR (Optical Character Recognition)")
                st.warning("This option requires that you have Tesseract OCR installed on your system.")

                if st.button("Convert Scanned PDF", key="convert_scanned"):
                    with st.spinner("Processing scanned PDF with OCR (this may take a while)..."):
                        try:
                            # Save PDF content to a temporary file
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                                tmp_file.write(uploaded_file.getvalue())
                                pdf_path = tmp_file.name

                            # Convert PDF to images
                            images = convert_from_bytes(uploaded_file.getvalue())

                            # Process each page
                            all_text = []
                            for i, image in enumerate(images):
                                # Extract text using OCR
                                text = pytesseract.image_to_string(image)
                                all_text.append(text)

                                # Display extracted text
                                st.subheader(f"Page {i+1} Text")
                                st.text_area(f"Extracted Text - Page {i+1}", text, height=150)

                            # Create a combined text file for download
                            combined_text = "\n\n--- PAGE BREAK ---\n\n".join(all_text)

                            st.download_button(
                                label="Download All Text",
                                data=combined_text,
                                file_name="extracted_text.txt",
                                mime="text/plain"
                            )

                            # Clean up
                            os.unlink(pdf_path)

                            st.info("For scanned PDFs, the text extraction is provided. You may need to manually format this into a spreadsheet.")

                        except ImportError:
                            st.error("OCR libraries not available. Please install pdf2image and pytesseract.")
                        except Exception as e:
                            st.error(f"Error processing scanned PDF: {str(e)}")
                            
    # Add PDF merge functionality to the sidebar
    with st.sidebar.expander("PDF Merge Tool", expanded=False):
        st.markdown("### Merge Multiple PDFs")
        st.caption("Upload multiple PDF files to merge them into a single PDF document.")

        uploaded_files = st.file_uploader("Choose PDF files", type="pdf", accept_multiple_files=True, key="pdf_merger")

        if uploaded_files:
            if st.button("Merge PDFs"):
                # Create a PDF writer object
                pdf_writer = PyPDF2.PdfWriter()

                # Iterate over the uploaded files and add them to the writer
                for uploaded_file in uploaded_files:
                    # Read the PDF file
                    pdf_reader = PyPDF2.PdfReader(uploaded_file)
                    # Add each page to the writer
                    for page in range(len(pdf_reader.pages)):
                        pdf_writer.add_page(pdf_reader.pages[page])

                # Create a BytesIO object to save the merged PDF
                merged_pdf = io.BytesIO()
                pdf_writer.write(merged_pdf)
                merged_pdf.seek(0)

                # Provide a download button for the merged PDF
                st.download_button(
                    label="Download Merged PDF",
                    data=merged_pdf,
                    file_name="merged_document.pdf",
                    mime="application/pdf"
                )
    st.divider()
    
    # Database management section with password protection
    with st.expander("Database Management", expanded=False):
        if not st.session_state.sidebar_authenticated:
            if not st.session_state.sidebar_password_attempt:
                # Show a button to trigger password entry
                if st.button("Unlock Admin Features"):
                    st.session_state.sidebar_password_attempt = True
                    st.rerun()  # Rerun to show password field
            else:
                # Show password field
                password = st.text_input("Enter admin password:", type="password")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Submit"):
                        if password == SIDEBAR_PASSWORD:
                            st.session_state.sidebar_authenticated = True
                            st.rerun()  # Rerun to refresh the sidebar
                        else:
                            st.error("Incorrect password")
                with col2:
                    # Option to cancel
                    if st.button("Cancel"):
                        st.session_state.sidebar_password_attempt = False
                        st.rerun()
        else:
            # Show admin controls when authenticated
            if st.button("Lock Admin Features"):
                st.session_state.sidebar_authenticated = False
                st.rerun()

            st.caption("Backup and restore your database")

            # Backup button
            if st.button("Create Database Backup"):
                success, message = backup_database()
                if success:
                    st.success(message)
                else:
                    st.error(message)

            # Restore from backup
            st.subheader("Restore from Backup")
            backups = list_backups()

            if backups:
                backup_options = [f"{b['filename']} ({b['modified']})" for b in backups]
                selected_backup = st.selectbox("Select a backup to restore", backup_options)

                # Get the selected backup file path or blob name
                selected_index = backup_options.index(selected_backup)
                selected_file_or_blob = backups[selected_index]['path']

                # Confirm restore
                if st.button("Restore Selected Backup"):
                    confirm = st.checkbox("I understand this will replace the current database")
                    if confirm:
                        with st.spinner("Restoring backup..."):
                            success, message = restore_database(selected_file_or_blob)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                    else:
                        st.warning("Please confirm that you want to restore from backup")
            else:
                st.info("No backups found")

# --- MAIN APP UI ---

# Apply visual enhancements
enhance_visual_style()
create_header()


# --- DEFINE TABS (OUTSIDE OF ANY FUNCTION) ---
tab_dashboard, tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Dashboard", "Budget Calculator", "Time Tracking", "Project Reports", "Team Reports", "Client Management"
])

# --- DASHBOARD FUNCTION (Content for the Dashboard Tab) ---

def create_dashboard():
    """Creates the content for the dashboard tab."""

    st.markdown("### Dashboard")
    st.markdown("Overview of all audit projects and team activities.")

    # Check if projects exist
    if not st.session_state.projects:
        st.info("No projects available. Please create a project in the Budget Calculator tab first.")
        return  # Exit early if no projects

    # Summary metrics
    projects_count = len(st.session_state.projects)
    total_planned_hours = sum(project.get('total_hours', 0) for project in st.session_state.projects.values())
    total_actual_hours = sum(project.get('actual_hours', {}).get('total', 0) for project in st.session_state.projects.values())

    # Team members (deduplicated using a set)
    all_team_members = set()
    for project in st.session_state.projects.values():
        if 'team_members' in project:
            all_team_members.update(member for member in project['team_members'].values() if member)


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

    # Create project status dataframe (using a list comprehension)
    project_status = [
        {
            "Project": name,
            "Category": project.get('audit_category_display', ''),
            "Industry": project.get('industry_name', ''),
            "Planned Hours": project.get('total_hours', 0),
            "Actual Hours": project.get('actual_hours', {}).get('total', 0),
            "Completion": f"{round((project.get('actual_hours', {}).get('total', 0) / project.get('total_hours', 1) * 100),2) if project.get('total_hours', 1) else 0}%",  # Avoid division by zero
            "Status": "Completed" if project.get('actual_hours', {}).get('total', 0) >= project.get('total_hours', 0) * 0.95 else "In Progress" if project.get('actual_hours', {}).get('total', 0) > 0 else "Not Started"
        }
        for name, project in st.session_state.projects.items()
    ]

    status_df = pd.DataFrame(project_status)
    st.dataframe(status_df, hide_index=True, use_container_width=True)


    # Recent activity
    st.markdown("""
    <div class="custom-card">
        <h3 class="card-title">Recent Activity</h3>
    </div>
    """, unsafe_allow_html=True)

    # Get recent time entries (sorted by entry_time, descending)
    recent_entries = sorted(
        st.session_state.time_entries,
        key=lambda x: x.get('entry_time', ''),
        reverse=True
    )[:10]

    if recent_entries:
        recent_df = pd.DataFrame(recent_entries)
        # Consistent phase mapping
        phase_map = {
            "planning": "Planning",
            "fieldwork": "Fieldwork",
            "managerReview": "Manager Review",
            "partnerReview": "Partner Review"
        }
        recent_df['phase'] = recent_df['phase'].map(phase_map)  # Apply the mapping

        recent_df['entry_time'] = pd.to_datetime(recent_df['entry_time'])
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

    # Aggregate hours by team member (using a dictionary)
    team_hours = {}
    for entry in st.session_state.time_entries:
        resource = entry.get('resource', 'Unknown')
        hours = entry.get('hours', 0)
        team_hours[resource] = team_hours.get(resource, 0) + hours

    if team_hours:
        team_df = pd.DataFrame(
            {'Team Member': list(team_hours.keys()), 'Hours': list(team_hours.values())}
        ).sort_values('Hours', ascending=False)

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


    # Hours by audit phase (Corrected Phase Aggregation)
    st.markdown("""
    <div class="custom-card">
        <h3 class="card-title">Hours by Audit Phase</h3>
    </div>
    """, unsafe_allow_html=True)

    # Aggregate hours by phase
    phase_hours = {"planning": 0, "fieldwork": 0, "managerReview": 0, "partnerReview": 0}
    for entry in st.session_state.time_entries:
      phase = entry.get('phase')
      if phase in phase_hours:  # Only count known phases
          phase_hours[phase] += entry.get('hours', 0)


    phase_data = [
        {"Phase": phase_map[phase], "Hours": hours}  # Use the consistent mapping
        for phase, hours in phase_hours.items()
        if hours > 0  # Only include phases with actual hours
    ]

    if phase_data:  # Check if there's any data before creating the chart
      phase_df = pd.DataFrame(phase_data)
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
    else:
        st.info("No time entries recorded yet.")

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

# --- TAB CONTENT (Using 'with' blocks for each tab) ---

with tab_dashboard:
    create_dashboard()  # Call the function to populate the dashboard *inside* its tab

with tab1:
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

with tab2:
    # ... (Your existing code for tab2 - Time Tracking) ...
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

                # Get the list of team members for this project (handling potential missing keys)
                team_members = [v for k, v in project.get('team_members', {}).items() if v]
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
                        "date": entry_date.strftime("%Y-%m-%d"),  # Consistent date format
                        "hours": hours_spent,
                        "description": description,
                        "entry_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Consistent datetime format
                    }

                    # Add to time entries list
                    st.session_state.time_entries.append(time_entry)

                    # Update actual hours in project (handling missing 'actual_hours')
                    if 'actual_hours' not in project:
                        project['actual_hours'] = {
                            "planning": 0,
                            "fieldwork": 0,
                            "managerReview": 0,
                            "partnerReview": 0,
                            "total": 0
                        }
                    project['actual_hours'][selected_phase] = project['actual_hours'].get(selected_phase, 0) + hours_spent
                    project['actual_hours']['total'] = project['actual_hours'].get('total', 0) + hours_spent

                    # Save data
                    save_data()

                    st.success("Time entry added successfully!")

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
                    display_df['phase'] = display_df['phase'].map(phase_options)  # Use the phase_options mapping

                    st.dataframe(display_df, hide_index=True, use_container_width=True)
                else:
                    st.info("No time entries found for this project.")
    else:
        st.info("No projects available.  Please create a project in the Budget Calculator tab first.")

with tab3:
    # ... (Your existing code for tab3 - Project Reports) ...
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

            # Prepare data for phase progress (using a list comprehension)
            phase_data = [
                {
                    "Phase": phase_name,
                    "Planned Hours": project['phase_hours'][phase_key],
                    "Actual Hours": project.get('actual_hours', {}).get(phase_key, 0),
                    "Progress": (project.get('actual_hours', {}).get(phase_key, 0) / project['phase_hours'][phase_key] * 100) if project['phase_hours'][phase_key] > 0 else 0
                }
                for phase_key, phase_name in {
                    "planning": "Planning",
                    "fieldwork": "Fieldwork",
                    "managerReview": "Manager Review",
                    "partnerReview": "Partner Review"
                }.items()
            ]

            phase_df = pd.DataFrame(phase_data)

            # Create horizontal bar chart for phase progress
            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=phase_df['Phase'],
                x=phase_df['Planned Hours'],
                name='Planned Hours',
                orientation='h',
                marker=dict(color='rgba(30, 136, 229, 0.5)')  # Use named colors or rgba
            ))
            fig.add_trace(go.Bar(
                y=phase_df['Phase'],
                x=phase_df['Actual Hours'],
                name='Actual Hours',
                orientation='h',
                marker=dict(color='rgba(0, 230, 118, 0.8)')  # Use named colors or rgba
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
                title_font_color = COLOR_TEXT
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

            # Get time entries by resource (using a dictionary)
            resource_hours = {}
            for entry in st.session_state.time_entries:
                if entry.get('project') == selected_project:
                    resource = entry.get('resource')
                    hours = entry.get('hours', 0)
                    if resource not in resource_hours:
                        resource_hours[resource] = {
                            "total": 0, "planning": 0, "fieldwork": 0,
                            "managerReview": 0, "partnerReview": 0
                        }
                    resource_hours[resource]['total'] += hours
                    resource_hours[resource][entry.get('phase', 'other')] += hours

            # Create resource utilization data (using a list comprehension)
            resource_data = [
                {
                    "Resource": resource,
                    "Total Hours": hours['total'],
                    "Planning": hours['planning'],
                    "Fieldwork": hours['fieldwork'],
                    "Manager Review": hours['managerReview'],
                    "Partner Review": hours['partnerReview']
                }
                for resource, hours in resource_hours.items()
            ]

            if resource_data:
                resource_df = pd.DataFrame(resource_data)
                st.dataframe(resource_df, hide_index=True, use_container_width=True)

                # Create stacked bar chart for resource utilization
                fig = px.bar(
                    resource_df,
                    x="Resource",
                    y=["Planning", "Fieldwork", "Manager Review", "Partner Review"],
                    title="Hours Breakdown by Resource",
                    barmode='stack',
                    color_discrete_sequence=[COLOR_PRIMARY, COLOR_SECONDARY, COLOR_WARNING, "#9c27b0"]  # Use named colors
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
                timeline_df = pd.DataFrame(timeline_entries)
                timeline_df['date'] = pd.to_datetime(timeline_df['date'])

                # Group by date and phase
                daily_hours = timeline_df.groupby(['date', 'phase']).agg({'hours': 'sum'}).reset_index()

                # Consistent phase mapping
                phase_map = {
                    "planning": "Planning",
                    "fieldwork": "Fieldwork",
                    "managerReview": "Manager Review",
                    "partnerReview": "Partner Review"
                }
                daily_hours['phase'] = daily_hours['phase'].map(phase_map)  # Use consistent mapping

                fig = px.line(
                    daily_hours,
                    x='date',
                    y='hours',
                    color='phase',
                    title='Daily Hours by Phase',
                    markers=True,
                    color_discrete_sequence=[COLOR_PRIMARY, COLOR_SECONDARY, COLOR_WARNING, "#9c27b0"]  # Use named colors
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

                # Create cumulative hours chart
                timeline_df = timeline_df.sort_values('date')
                timeline_df['cumulative_hours'] = timeline_df.groupby('phase')['hours'].cumsum()
                timeline_df['phase'] = timeline_df['phase'].map(phase_map) #Use consistent mapping

                fig = px.line(
                    timeline_df,
                    x='date',
                    y='cumulative_hours',
                    color='phase',
                    title='Cumulative Hours by Phase',
                    line_shape='hv',
                    color_discrete_sequence=[COLOR_PRIMARY, COLOR_SECONDARY, COLOR_WARNING, "#9c27b0"]  # Use named colors
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
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    # Project Summary Sheet
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

                    # Phase Progress Sheet
                    phase_df.to_excel(writer, sheet_name='Phase Progress', index=False)

                    # Resource Utilization Sheet (if data exists)
                    if resource_data:
                        resource_df.to_excel(writer, sheet_name='Resource Utilization', index=False)

                    # Time Entries Detail Sheet (if data exists)
                    if timeline_entries:
                        entries_df = pd.DataFrame(timeline_entries)
                        entries_df['phase'] = entries_df['phase'].map(phase_map)  # Consistent mapping
                        entries_df.to_excel(writer, sheet_name='Time Entries', index=False)

                # Create download link (Corrected MIME type and button styling)
                output.seek(0)
                b64 = base64.b64encode(output.read()).decode()
                filename = f"project_report_{project['company_name'].replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d')}.xlsx"
                href = (
                    f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" '
                    f'download="{filename}" style="text-decoration:none;">'
                    f'<button style="background-color:{COLOR_PRIMARY};color:white;padding:10px 20px;border:none;border-radius:5px;cursor:pointer;">'
                    f'Download Excel Report'
                    f'</button></a>'
                )
                st.markdown(href, unsafe_allow_html=True)

    else:
        st.info("No projects available. Please create a project in the Budget Calculator tab first.")

with tab4:
    # ... (Your existing code for tab4 - Team Reports) ...
    st.markdown("### Team Reports")
    st.markdown("View reports on team member utilization across all projects.")

    # Get all team members across projects (deduplicated with a set)
    all_team_members = set()
    for project in st.session_state.projects.values():
        if 'team_members' in project:
            all_team_members.update(member for member in project['team_members'].values() if member)

    if all_team_members:
        selected_member = st.selectbox(
            "Select Team Member",
            options=sorted(list(all_team_members))  # Sort for consistent order
        )

        st.markdown("""
        <div class="custom-card">
            <h3 class="card-title">Date Range</h3>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", datetime.now().replace(day=1).date())
        with col2:
            end_date = st.date_input("End Date", datetime.now().date())

        # Filter time entries by team member and date range
        member_entries = [
            entry for entry in st.session_state.time_entries
            if entry.get('resource') == selected_member
            and start_date <= datetime.strptime(entry.get('date', '1900-01-01'), '%Y-%m-%d').date() <= end_date  # Correct date comparison
        ]

        if member_entries:
          # Calculate total hours
          total_hours = sum(entry.get('hours', 0) for entry in member_entries)

          # Group hours by project
          project_hours = {}
          for entry in member_entries:
              project = entry.get('project', 'Unknown')
              project_hours[project] = project_hours.get(project, 0) + entry.get('hours', 0)

          # Group hours by phase
          phase_hours = {}
          for entry in member_entries:
              phase = entry.get('phase', 'Unknown')
              phase_hours[phase] = phase_hours.get(phase, 0) + entry.get('hours', 0)

          # Summary metrics
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
              daily_avg = total_hours / max(1, (end_date - start_date).days + 1)  # Avoid division by zero
              st.metric("Daily Average", f"{round(daily_avg, 1)}")

          # Charts
          chart_cols = st.columns(2)

          with chart_cols[0]:
              st.markdown("""
              <div class="custom-card">
                  <h3 class="card-title">Hours by Project</h3>
              </div>
              """, unsafe_allow_html=True)

              project_data = pd.DataFrame({
                  'Project': list(project_hours.keys()),
                  'Hours': list(project_hours.values())
              })
              fig = px.pie(
                  project_data,
                  values='Hours',
                  names='Project',
                  title=f'Hours by Project ({start_date.strftime("%d %b")} - {end_date.strftime("%d %b")})',
                  color_discrete_sequence=px.colors.sequential.Blues_r  # Use a named color sequence
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

              phase_map = {  # Consistent mapping
                  "planning": "Planning",
                  "fieldwork": "Fieldwork",
                  "managerReview": "Manager Review",
                  "partnerReview": "Partner Review"
              }
              phase_data = pd.DataFrame({
                  'Phase': [phase_map.get(p, p) for p in phase_hours.keys()],  # Use consistent mapping
                  'Hours': list(phase_hours.values())
              })
              fig = px.pie(
                  phase_data,
                  values='Hours',
                  names='Phase',
                  title=f'Hours by Audit Phase ({start_date.strftime("%d %b")} - {end_date.strftime("%d %b")})',
                  color_discrete_sequence=[COLOR_PRIMARY, COLOR_SECONDARY, COLOR_WARNING, "#9c27b0"]  # Use named colors
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
              entries_df['phase'] = entries_df['phase'].map(phase_map)  # Use consistent mapping
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
          entries_df['date'] = pd.to_datetime(entries_df['date'])
          daily_df = entries_df.groupby(entries_df['date'].dt.date).agg({'hours': 'sum'}).reset_index()
          fig = px.bar(
              daily_df,
              x='date',
              y='hours',
              title=f'Daily Hours ({start_date.strftime("%d %b")} - {end_date.strftime("%d %b")})',
              color_discrete_sequence=[COLOR_PRIMARY]  # Use named color
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
              output = io.BytesIO()
              with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                  # Summary Sheet
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

                  # Project Hours Sheet
                  project_data.to_excel(writer, sheet_name='Project Hours', index=False)

                  # Phase Hours Sheet
                  phase_data.to_excel(writer, sheet_name='Phase Hours', index=False)

                  # Daily Hours Sheet
                  daily_df.to_excel(writer, sheet_name='Daily Hours', index=False)

                  # Time Entries Sheet
                  entries_df[['date', 'project', 'phase', 'hours', 'description']].to_excel(
                      writer, sheet_name='Time Entries', index=False
                  )

              # Create download link (Corrected MIME type and button styling)
              output.seek(0)
              b64 = base64.b64encode(output.read()).decode()
              filename = f"team_report_{selected_member.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d')}.xlsx"
              href = (
                  f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" '
                  f'download="{filename}" style="text-decoration:none;">'
                  f'<button style="background-color:{COLOR_PRIMARY};color:white;padding:10px 20px;border:none;border-radius:5px;cursor:pointer;">'
                  f'Download Excel Report'
                  f'</button></a>'
              )
              st.markdown(href, unsafe_allow_html=True)
        else:
            st.info(f"No time entries found for {selected_member} in the selected date range.")
    else:
        st.info("No team members assigned to any projects yet.")

with tab5:
    st.markdown("### Add New Client")
    st.markdown("Use the form below to add a new client to the database.")

    # Create a form for client details
    with st.form("client_form"):
        client_name = st.text_input("Client Name", "")
        client_code = st.text_input("Client Code", "")
        business_sector = st.text_input("Business Sector", "")
        latest_turnover = st.number_input("Latest Turnover (in Lakhs)", min_value=0.0, step=0.1)
        previous_year_turnover = st.number_input("Previous Year Turnover (in Lakhs)", min_value=0.0, step=0.1)
        latest_borrowings = st.number_input("Latest Borrowings (in Lakhs)", min_value=0.0, step=0.1)
        previous_year_borrowings = st.number_input("Previous Year Borrowings (in Lakhs)", min_value=0.0, step=0.1)
        latest_profit_before_tax = st.number_input("Latest Profit Before Tax (in Lakhs)", min_value=0.0, step=0.1)
        previous_year_profit_before_tax = st.number_input("Previous Year Profit Before Tax (in Lakhs)", min_value=0.0, step=0.1)
        latest_net_worth = st.number_input("Latest Net Worth (in Lakhs)", min_value=0.0, step=0.1)
        previous_year_net_worth = st.number_input("Previous Year Net Worth (in Lakhs)", min_value=0.0, step=0.1)
        signing_director_1 = st.text_input("Signing Director 1", "")
        signing_director_2 = st.text_input("Signing Director 2", "")
        company_secretary = st.text_input("Company Secretary (if applicable)", "")
        chief_financial_officer = st.text_input("Chief Financial Officer (if applicable)", "")
        managing_director = st.text_input("Managing Director (if applicable)", "")
        signing_director_3 = st.text_input("Signing Director 3 (if applicable)", "")

        # Submit button
        submitted = st.form_submit_button("Add Client")

        if submitted:
            # Collect client data
            client_data = {
                'client_name': client_name,
                'client_code': client_code,
                'business_sector': business_sector,
                'latest_turnover': latest_turnover,
                'previous_year_turnover': previous_year_turnover,
                'latest_borrowings': latest_borrowings,
                'previous_year_borrowings': previous_year_borrowings,
                'latest_profit_before_tax': latest_profit_before_tax,
                'previous_year_profit_before_tax': previous_year_profit_before_tax,
                'latest_net_worth': latest_net_worth,
                'previous_year_net_worth': previous_year_net_worth,
                'signing_director_1': signing_director_1,
                'signing_director_2': signing_director_2,
                'company_secretary': company_secretary,
                'chief_financial_officer': chief_financial_officer,
                'managing_director': managing_director,
                'signing_director_3': signing_director_3
            }

            # Add client to the database
            add_client(client_data)
            st.success(f"Client '{client_name}' added successfully!")

# --- FOOTER ---
st.markdown("---")
st.caption("Statutory Audit Budget Calculator & Time Tracker - A tool for audit planning and resource tracking")