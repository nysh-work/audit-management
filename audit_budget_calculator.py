import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import io
import base64
import json
import shutil
import os
import glob
import reportlab
import weasyprint
    # Import the materiality calculator module
from materiality_calculator import create_materiality_calculator_dialog

# --- DATABASE FUNCTIONS (Same as before - no changes needed here) ---
# --- LOGGING SETUP ---
import logging
from pathlib import Path

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

# Cloud Storage initialization
is_cloud = os.environ.get('CLOUD_RUN_SERVICE', False)
if is_cloud:
    from cloud_storage import CloudStorageManager
    BUCKET_NAME = os.environ.get('BUCKET_NAME', 'audit-app-storage')
    cloud_storage = CloudStorageManager(BUCKET_NAME)
else:
    cloud_storage = None

# Define the database location (can be changed if needed)
def get_db_path():
    """Returns the path to the database file."""
    # Define local paths
    home_dir = str(Path.home())
    app_data_dir = os.path.join(home_dir, '.audit_management_app')
    data_dir = os.path.join(app_data_dir, 'data')
    db_file = os.path.join(data_dir, 'audit_management.db')
    
    # Create necessary directories
    os.makedirs(data_dir, exist_ok=True)
    
    # In cloud environment, download the DB file from Cloud Storage if it exists
    is_cloud = os.environ.get('CLOUD_RUN_SERVICE', False)
    if is_cloud:
        # Check if DB file exists in Cloud Storage
        if cloud_storage.file_exists('data/audit_management.db'):
            # Download the file from Cloud Storage
            cloud_storage.download_file('data/audit_management.db', db_file)
    
    return db_file

def init_db():
    """Initializes the SQLite database and creates tables if they don't exist."""
    try:
        # Get the database path
        db_path = get_db_path()
        logging.info(f"Initializing database at {db_path}")
        
        # Connect to the database
        conn = sqlite3.connect(db_path, check_same_thread=False)
        c = conn.cursor()

        # Create projects table if it doesn't exist
        c.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                data TEXT,
                creation_date TEXT
            )
        ''')

        # Create time_entries table if it doesn't exist
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
        
        # Create team_members table if it doesn't exist
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
        
        # Create schedule_entries table if it doesn't exist
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
        error_msg = f"Database initialization error: {str(e)}"
        logging.error(error_msg)
        st.error(error_msg)
        raise

def save_projects_to_db():
    """Saves projects from session state to the database."""
    conn = init_db()  # This now uses the absolute path
    c = conn.cursor()
    c.execute("DELETE FROM projects")  # Clear existing data

    for name, project_data in st.session_state.projects.items():
        project_json = json.dumps(project_data)
        creation_date = project_data.get('creation_date', datetime.now().strftime("%Y-%m-%d"))
        c.execute("INSERT INTO projects (name, data, creation_date) VALUES (?, ?, ?)",
                  (name, project_json, creation_date))

    conn.commit()
    conn.close()

def load_projects_from_db():
    """Loads projects from the database into session state."""
    conn = init_db()  # This now uses the absolute path
    c = conn.cursor()
    c.execute("SELECT name, data FROM projects")
    projects = {name: json.loads(data) for name, data in c.fetchall()}
    conn.close()
    return projects

def save_time_entries_to_db():
    """Saves time entries from session state to the database."""
    conn = init_db()
    c = conn.cursor()
    c.execute("DELETE FROM time_entries")  # Clear existing data

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
    conn = init_db()  # This now uses the absolute path
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
    c.execute("DELETE FROM team_members")  # Clear existing data

    for name, member in st.session_state.team_members.items():
        skills = ','.join(member.get('skills', []))
        # Extract core fields
        role = member.get('role', '')
        availability_hours = member.get('availability_hours', 40.0)
        hourly_rate = member.get('hourly_rate', 0.0)
        
        # Store additional data as JSON
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
    c.execute("DELETE FROM schedule_entries")  # Clear existing data

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

# --- DATA LOADING AND SAVING (Corrected Order) ---

def save_data():
    """Saves project and time entry data to the database and backup files."""
    save_projects_to_db()
    save_time_entries_to_db()
    save_team_members_to_db()
    save_schedule_entries_to_db()

    # Define paths
    home_dir = str(Path.home())
    app_data_dir = os.path.join(home_dir, '.audit_management_app')
    data_dir = os.path.join(app_data_dir, 'data')
    
    # Create necessary directories
    os.makedirs(data_dir, exist_ok=True)

    # Get the database file path
    db_file = get_db_path()
    
    # In cloud environment, upload the DB file to Cloud Storage
    is_cloud = os.environ.get('CLOUD_RUN_SERVICE', False)
    if is_cloud and os.path.exists(db_file) and 'cloud_storage' in globals():
        cloud_storage.upload_file(db_file, 'data/audit_management.db')
        
        # Also save projects and time entries directly to Cloud Storage as backup
        try:
            # Save projects to a temp file and upload
            projects_file = os.path.join(data_dir, 'projects.json')
            with open(projects_file, 'w') as f:
                json.dump(st.session_state.projects, f)
            cloud_storage.upload_file(projects_file, 'data/projects.json')
            
            # Save time entries to a temp file and upload
            time_entries_file = os.path.join(data_dir, 'time_entries.csv')
            df = pd.DataFrame(st.session_state.time_entries)
            if not df.empty:
                df.to_csv(time_entries_file, index=False)
                cloud_storage.upload_file(time_entries_file, 'data/time_entries.csv')
        except Exception as e:
            logging.error(f"Error saving data to cloud storage: {e}")
    
    # Backup to local files (for local development or extra safety)
    try:
        projects_file = os.path.join(data_dir, 'projects.json')
        with open(projects_file, 'w') as f:
            json.dump(st.session_state.projects, f)

        time_entries_file = os.path.join(data_dir, 'time_entries.csv')
        df = pd.DataFrame(st.session_state.time_entries)
        if not df.empty:
            df.to_csv(time_entries_file, index=False)
    except Exception as e:
        st.error(f"Error saving data to files: {e}")

def load_data():
    """Loads project and time entry data from the database, with fallback to files."""
    try:
        # Import necessary modules
        import os
        from pathlib import Path
        
        # Define the app data paths
        home_dir = str(Path.home())
        app_data_dir = os.path.join(home_dir, '.audit_management_app')
        data_dir = os.path.join(app_data_dir, 'data')
        
        # Load from database
        st.session_state.projects = load_projects_from_db()
        st.session_state.time_entries = load_time_entries_from_db()
        st.session_state.team_members = load_team_members_from_db()
        st.session_state.schedule_entries = load_schedule_entries_from_db()

        # Fallback to files if database is empty (for backward compatibility)
        projects_file = os.path.join(data_dir, 'projects.json')
        time_entries_file = os.path.join(data_dir, 'time_entries.csv')
        
        if not st.session_state.projects and os.path.exists(projects_file):
            with open(projects_file, 'r') as f:
                st.session_state.projects = json.load(f)
            save_projects_to_db()  # Save loaded data to DB

        if not st.session_state.time_entries and os.path.exists(time_entries_file):
            df = pd.read_csv(time_entries_file)
            st.session_state.time_entries = df.to_dict('records')
            save_time_entries_to_db()  # Save loaded data to DB

        # Log the loading operation
        logging.info(f"Data loaded successfully. Projects: {len(st.session_state.projects)}, Time entries: {len(st.session_state.time_entries)}, Team members: {len(st.session_state.team_members)}, Schedule entries: {len(st.session_state.schedule_entries)}")

    except Exception as e:
        error_msg = f"Error loading data: {str(e)}"
        logging.error(error_msg)
        st.error(error_msg)
        
        # Initialize with empty data if loading fails
        if 'projects' not in st.session_state:
            st.session_state.projects = {}
        if 'time_entries' not in st.session_state:
            st.session_state.time_entries = []

def backup_database(event=None, context=None):
    """Creates a timestamped backup of the database."""
    # Check if we're in the cloud environment
    is_cloud = os.environ.get('CLOUD_RUN_SERVICE', False)
    
    # Define paths for local backup
    home_dir = str(Path.home())
    app_data_dir = os.path.join(home_dir, '.audit_management_app')
    data_dir = os.path.join(app_data_dir, 'data')
    backups_dir = os.path.join(app_data_dir, 'backups')
    
    # Create backups directory if it doesn't exist
    os.makedirs(backups_dir, exist_ok=True)
    
    # Create timestamp for backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # If we're in the cloud, backup to Cloud Storage
    if is_cloud and 'cloud_storage' in globals():
        try:
            # Reference to the main database blob
            db_blob = cloud_storage.bucket.blob('data/audit_management.db')
            
            if db_blob.exists():
                # Create the backup blob name
                backup_blob_name = f"backups/audit_management_{timestamp}.db"
                
                # Copy the blob to the backup location
                cloud_storage.bucket.copy_blob(db_blob, cloud_storage.bucket, backup_blob_name)
                
                # Also backup projects.json and time_entries.csv if they exist
                projects_blob = cloud_storage.bucket.blob('data/projects.json')
                if projects_blob.exists():
                    cloud_storage.bucket.copy_blob(
                        projects_blob, 
                        cloud_storage.bucket, 
                        f"backups/projects_{timestamp}.json"
                    )
                
                entries_blob = cloud_storage.bucket.blob('data/time_entries.csv')
                if entries_blob.exists():
                    cloud_storage.bucket.copy_blob(
                        entries_blob, 
                        cloud_storage.bucket, 
                        f"backups/time_entries_{timestamp}.csv"
                    )
                
                return True, f"Cloud backup created successfully: {backup_blob_name}"
            else:
                return False, "Database file not found in cloud storage."
        except Exception as e:
            return False, f"Cloud backup failed: {str(e)}"
    
    # For local environment, use the existing code
    db_file = os.path.join(data_dir, 'audit_management.db')
    
    # Check if database exists
    if not os.path.exists(db_file):
        return False, "Database file not found."
    
    backup_file = os.path.join(backups_dir, f"audit_management_{timestamp}.db")
    
    try:
        # Copy the database file
        shutil.copy2(db_file, backup_file)
        
        # Also backup the JSON and CSV files if they exist
        json_file = os.path.join(data_dir, 'projects.json')
        if os.path.exists(json_file):
            shutil.copy2(json_file, os.path.join(backups_dir, f"projects_{timestamp}.json"))
            
        csv_file = os.path.join(data_dir, 'time_entries.csv')
        if os.path.exists(csv_file):
            shutil.copy2(csv_file, os.path.join(backups_dir, f"time_entries_{timestamp}.csv"))
        
        return True, f"Local backup created successfully: audit_management_{timestamp}.db"
    except Exception as e:
        return False, f"Local backup failed: {str(e)}"

def restore_database(backup_file_or_blob):
    """Restores the database from a backup file or blob."""
    # Check if we're in the cloud environment
    is_cloud = os.environ.get('CLOUD_RUN_SERVICE', False)
    
    if is_cloud and 'cloud_storage' in globals():
        try:
            # Create a backup of the current database first
            backup_database()
            
            # Assume backup_file_or_blob is a blob name in Cloud Storage
            backup_blob = cloud_storage.bucket.blob(backup_file_or_blob)
            
            if not backup_blob.exists():
                return False, "Backup file not found in cloud storage."
            
            # Copy the backup over the current database
            cloud_storage.bucket.copy_blob(
                backup_blob, 
                cloud_storage.bucket, 
                'data/audit_management.db'
            )
            
            # Extract the timestamp from the backup filename
            # Format: backups/audit_management_YYYYMMDD_HHMMSS.db
            filename = os.path.basename(backup_file_or_blob)
            timestamp = filename.split('audit_management_')[1].split('.db')[0]
            
            # Also restore projects.json and time_entries.csv if they exist
            projects_backup = cloud_storage.bucket.blob(f"backups/projects_{timestamp}.json")
            if projects_backup.exists():
                cloud_storage.bucket.copy_blob(
                    projects_backup, 
                    cloud_storage.bucket, 
                    'data/projects.json'
                )
                
            entries_backup = cloud_storage.bucket.blob(f"backups/time_entries_{timestamp}.csv")
            if entries_backup.exists():
                cloud_storage.bucket.copy_blob(
                    entries_backup, 
                    cloud_storage.bucket, 
                    'data/time_entries.csv'
                )
            
            # Force a reload of the database
            db_path = get_db_path()
            cloud_storage.download_file('data/audit_management.db', db_path)
            
            return True, "Database restored successfully from cloud backup. Please refresh the page."
        except Exception as e:
            return False, f"Cloud restore failed: {str(e)}"
    
    # For local environment, use the existing code
    home_dir = str(Path.home())
    app_data_dir = os.path.join(home_dir, '.audit_management_app')
    data_dir = os.path.join(app_data_dir, 'data')
    
    # Target database file
    db_file = os.path.join(data_dir, 'audit_management.db')
    
    try:
        # Create a backup of the current database before restoring
        if os.path.exists(db_file):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            shutil.copy2(db_file, os.path.join(data_dir, f"audit_management_pre_restore_{timestamp}.db"))
        
        # Copy the backup file to the database location
        shutil.copy2(backup_file_or_blob, db_file)
        
        return True, "Database restored successfully. Please restart the application."
    except Exception as e:
        return False, f"Local restore failed: {str(e)}"

def list_backups():
    """Lists all available database backups."""
    # Check if we're in the cloud environment
    is_cloud = os.environ.get('CLOUD_RUN_SERVICE', False)
    
    if is_cloud and 'cloud_storage' in globals():
        try:
            # List all backup blobs in cloud storage
            blobs = list(cloud_storage.client.list_blobs(
                cloud_storage.bucket_name, 
                prefix="backups/audit_management_"
            ))
            
            # Sort by creation time (most recent first)
            blobs.sort(key=lambda x: x.time_created, reverse=True)
            
            backups = []
            for blob in blobs:
                backups.append({
                    "filename": os.path.basename(blob.name),
                    "path": blob.name,  # Store the blob name as the path
                    "modified": blob.time_created.strftime("%Y-%m-%d %H:%M:%S"),
                    "size_mb": round(blob.size / (1024 * 1024), 2)
                })
            
            return backups
        except Exception as e:
            logging.error(f"Error listing cloud backups: {e}")
            return []
    
    # For local environment, use the existing code
    home_dir = str(Path.home())
    backups_dir = os.path.join(home_dir, '.audit_management_app', 'backups')
    
    # Check if backups directory exists
    if not os.path.exists(backups_dir):
        return []
    
    # Get all database backup files
    backup_files = glob.glob(os.path.join(backups_dir, "audit_management_*.db"))
    
    # Sort by modification time (most recent first)
    backup_files.sort(key=os.path.getmtime, reverse=True)
    
    # Format the list for display
    backups = []
    for file in backup_files:
        filename = os.path.basename(file)
        mod_time = datetime.fromtimestamp(os.path.getmtime(file)).strftime("%Y-%m-%d %H:%M:%S")
        size_mb = os.path.getsize(file) / (1024 * 1024)
        backups.append({
            "filename": filename,
            "path": file,
            "modified": mod_time,
            "size_mb": round(size_mb, 2)
        })
    
    return backups

# --- STREAMLIT SETUP AND INITIALIZATION ---

# Set page config (do this first)
st.set_page_config(
    page_title="Statutory Audit Budget Calculator & Time Tracker",
    page_icon="streamlit_icon.png",
    layout="wide",
    initial_sidebar_state="collapsed"
)
# Define color palette - Medium-inspired dark mode
COLOR_PRIMARY = "#1e88e5"       # Primary blue
COLOR_SECONDARY = "#00e676"     # Success green
COLOR_WARNING = "#ff9800"       # Warning orange
COLOR_DANGER = "#f44336"        # Danger red
COLOR_BACKGROUND = "#121212"    # Main background
COLOR_CARD_BACKGROUND = "#1e1e1e"  # Lighter background for cards
COLOR_TEXT = "#e6e6e6"          # Main text color
COLOR_TEXT_MUTED = "#9e9e9e"    # Muted text color
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

# --- INITIALIZE AND LOAD DATA ---
init_db()  # Initialize the database *first*
load_data() # *Then* load data

# Initialize session state (do this before using it)
if 'projects' not in st.session_state:
    st.session_state.projects = {}
if 'time_entries' not in st.session_state:
    st.session_state.time_entries = []
if 'team_members' not in st.session_state:
    st.session_state.team_members = {}
if 'schedule_entries' not in st.session_state:
    st.session_state.schedule_entries = []
if 'current_project' not in st.session_state:
    st.session_state.current_project = None
if 'theme' not in st.session_state:  # Example for theme switching (optional)
    st.session_state.theme = 'dark'
if 'sidebar_authenticated' not in st.session_state:
    st.session_state.sidebar_authenticated = False
if 'sidebar_password_attempt' not in st.session_state:
    st.session_state.sidebar_password_attempt = False
if 'show_materiality_calculator' not in st.session_state:
    st.session_state.show_materiality_calculator = False

# Set the sidebar password (you should store this more securely in a real app)
SIDEBAR_PASSWORD = "audit2025"

# Function to authenticate sidebar
def authenticate_sidebar():
    password = st.text_input("Enter admin password:", type="password", key="sidebar_password")
    if st.button("Submit"):
        if password == SIDEBAR_PASSWORD:
            st.session_state.sidebar_authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password")

# Function to toggle theme (Example - optional)
def toggle_theme():
    st.session_state.theme = 'light' if st.session_state.theme == 'dark' else 'dark'

# Sidebar (optional, but good for navigation/settings)
# Sidebar content
with st.sidebar:
    st.title("Audit Management")
    
    # Theme toggle available to everyone
    st.button('Toggle Light/Dark Mode', on_click=toggle_theme)
    
    # Add Materiality Calculator to sidebar
    with st.expander("Materiality Calculator", expanded=False):
        st.markdown("### Materiality Calculator")
        st.caption("Calculate audit materiality based on ISA 320 guidelines.")
        if st.button("Open Materiality Calculator"):
            st.session_state.show_materiality_calculator = True
            st.rerun()
    
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
                            import tempfile
                            import os
                            import tabula
                            import pandas as pd
                            
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

                                    # Handle different export formats
                                    if export_format == "Individual Tables":
                                        # Display and provide download options for each table
                                        for i, table in enumerate(tables):
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
                                   
                                    col1, col2 = st.columns(2)
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
                                
                                if export_format == "Combined Excel (all tables)":
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
                                        file_name="all_tables.xlsx",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                    )
                        except Exception as e:
                            st.error(f"Error processing PDF: {str(e)}")
            
            with converter_tabs[1]:
                st.caption("Use this for PDFs with complex tables, merged cells, or unusual layouts")
                area = st.text_input("Area to extract (top,left,bottom,right in % of page, e.g. '10,10,90,90')", "")
                complex_pages = st.text_input("Pages to extract", "1")
                complex_export_format = st.radio("Export Format", 
                                                ["Individual Tables", "Combined Excel (all tables)", "Combined CSV (all tables)"], 
                                                key="complex_export_format")
                
                if st.button("Convert Complex Tables", key="convert_complex"):
                    with st.spinner("Processing complex tables..."):
                        try:
                            import tempfile
                            import os
                            import tabula
                            import pandas as pd
                            import io
                            
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
                                # Display individual tables
                                for i, table in enumerate(tables):
                                    st.subheader(f"Table {i+1}")
                                    st.dataframe(table, height=150)
                                
                                # Handle different export formats
                                if complex_export_format == "Individual Tables":
                                    # Display and provide download options for each table
                                    for i, table in enumerate(tables):
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
                                    
                                    # Also provide option for Excel with single sheet
                                    st.write("The combined CSV format might be difficult to read for multiple tables. Here's also a single-sheet Excel option:")
                                    
                                    excel_buffer = io.BytesIO()
                                    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                                        combined_df.to_excel(writer, sheet_name='All_Tables', index=False)
                                        
                                        # Add some formatting
                                        workbook = writer.book
                                        worksheet = writer.sheets['All_Tables']
                                        
                                        # Format headers
                                        header_format = workbook.add_format({
                                            'bold': True,
                                            'text_wrap': True,
                                            'valign': 'top',
                                            'fg_color': '#D7E4BC',
                                            'border': 1
                                        })
                                        
                                        # Apply header format
                                        for col_num, value in enumerate(combined_df.columns.values):
                                            worksheet.write(0, col_num, value, header_format)
                                            
                                        # Add table filter
                                        worksheet.autofilter(0, 0, len(combined_df), len(combined_df.columns)-1)
                                    
                                    excel_data = excel_buffer.getvalue()
                                    
                                    st.download_button(
                                        label="Download All Tables as Single-Sheet Excel",
                                        data=excel_data,
                                        file_name=f"{uploaded_file.name.split('.')[0]}_all_tables_single_sheet.xlsx",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                    )
                        except Exception as e:
                            st.error(f"Error processing complex tables: {str(e)}")
            
            with converter_tabs[2]:
                st.caption("Use this for scanned PDFs that need OCR (Optical Character Recognition)")
                st.warning("This option requires that you have Tesseract OCR installed on your system.")
                
                if st.button("Convert Scanned PDF", key="convert_scanned"):
                    with st.spinner("Processing scanned PDF with OCR (this may take a while)..."):
                        try:
                            import tempfile
                            import os
                            import pytesseract
                            from pdf2image import convert_from_bytes
                            import pandas as pd
                            
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

# --- DEFINE TABS (OUTSIDE OF ANY FUNCTION) ---
tab_dashboard, tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Dashboard", "Budget Calculator", "Time Tracking", "Project Reports", "Team Reports", "Team Scheduling"
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

# Main content area
if 'show_materiality_calculator' in st.session_state and st.session_state.show_materiality_calculator:
    create_materiality_calculator_dialog()
    if st.button("Return to Main Application"):
        st.session_state.show_materiality_calculator = False
        st.rerun()
else:
    # Dashboard Tab
    with tab_dashboard:
        create_dashboard()

    # Budget Calculator Tab
    with tab1:
        create_budget_calculator()

    # Time Tracking Tab
    with tab2:
        create_time_tracking()

    # Project Reports Tab
    with tab3:
        create_project_reports()

    # Team Reports Tab
    with tab4:
        create_team_reports()

    # Team Scheduling Tab
    with tab5:
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.markdown("### Team Management")
            manage_team_members()
        
        with col2:
            manage_team_scheduling()

def create_team_reports():
    """Creates the content for the team reports tab."""
    st.markdown("### Team Reports")
    st.markdown("Analysis of team member utilization and performance across projects.")

def manage_team_scheduling():
    """Manages team scheduling with general availability and specific phase allocation."""
    st.markdown("### Team Scheduling")
    
    # Get projects and team members
    projects = get_project_list()
    team_members = list(st.session_state.team_members.keys())
    
    if not projects or not team_members:
        st.warning("Please add projects and team members first.")
        return
    
    # Define audit phases
    audit_phases = [
        "Planning", 
        "Risk Assessment",
        "Internal Controls Testing",
        "Substantive Testing",
        "Completion",
        "Reporting"
    ]
    
    # Create a new schedule entry
    st.markdown("#### Create New Schedule Entry")
    with st.form("schedule_entry_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            selected_team_member = st.selectbox("Team Member", team_members)
            selected_project = st.selectbox("Project", projects)
            selected_phase = st.selectbox("Audit Phase", audit_phases)
        
        with col2:
            start_date = st.date_input("Start Date", value=datetime.now().date())
            end_date = st.date_input("End Date", value=(datetime.now() + pd.Timedelta(days=7)).date())
            hours_per_day = st.number_input("Hours Per Day", min_value=0.5, max_value=12.0, value=8.0, step=0.5)
        
        notes = st.text_area("Notes", height=100)
        submit_button = st.form_submit_button("Add Schedule Entry")
    
    if submit_button:
        # Calculate total days and hours
        days = (end_date - start_date).days + 1
        total_hours = days * hours_per_day
        
        # Get team member's weekly availability
        member_availability = st.session_state.team_members[selected_team_member]['availability_hours']
        
        # Calculate current allocation for this team member in the date range
        current_allocation = 0
        for entry in st.session_state.schedule_entries:
            if entry['team_member'] == selected_team_member:
                entry_start = datetime.strptime(entry['start_date'], '%Y-%m-%d').date()
                entry_end = datetime.strptime(entry['end_date'], '%Y-%m-%d').date()
                
                # Check for overlap
                if (entry_start <= end_date and entry_end >= start_date):
                    # Calculate overlapping days
                    overlap_start = max(start_date, entry_start)
                    overlap_end = min(end_date, entry_end)
                    overlap_days = (overlap_end - overlap_start).days + 1
                    
                    # Add to current allocation
                    current_allocation += overlap_days * entry['hours_per_day']
        
        # Check if new allocation exceeds availability
        weeks_span = max(1, days / 7)
        total_available_hours = member_availability * weeks_span
        
        if current_allocation + total_hours > total_available_hours:
            st.error(f"This allocation exceeds {selected_team_member}'s availability. " +
                    f"Available: {total_available_hours} hours, " +
                    f"Currently allocated: {current_allocation} hours, " +
                    f"Attempting to allocate: {total_hours} hours.")
        else:
            # Add new schedule entry
            new_entry = {
                'team_member': selected_team_member,
                'project': selected_project,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'hours_per_day': hours_per_day,
                'phase': selected_phase,
                'status': 'scheduled',
                'notes': notes,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            st.session_state.schedule_entries.append(new_entry)
            save_schedule_entries_to_db()
            st.success(f"Schedule entry added for {selected_team_member} on project {selected_project}.")
    
    # Display current schedule
    st.markdown("#### Current Schedule")
    
    # Filter options
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        filter_team_member = st.selectbox("Filter by Team Member", ["All"] + team_members)
    with filter_col2:
        filter_project = st.selectbox("Filter by Project", ["All"] + projects)
    
    # Prepare data for display
    if st.session_state.schedule_entries:
        filtered_entries = st.session_state.schedule_entries.copy()
        
        # Apply filters
        if filter_team_member != "All":
            filtered_entries = [e for e in filtered_entries if e['team_member'] == filter_team_member]
        if filter_project != "All":
            filtered_entries = [e for e in filtered_entries if e['project'] == filter_project]
        
        if filtered_entries:
            # Convert to DataFrame for display
            df = pd.DataFrame(filtered_entries)
            
            # Format dates
            df['start_date'] = pd.to_datetime(df['start_date']).dt.strftime('%Y-%m-%d')
            df['end_date'] = pd.to_datetime(df['end_date']).dt.strftime('%Y-%m-%d')
            
            # Calculate total days and hours
            df['days'] = [(datetime.strptime(end, '%Y-%m-%d') - datetime.strptime(start, '%Y-%m-%d')).days + 1 
                         for start, end in zip(df['start_date'], df['end_date'])]
            df['total_hours'] = df['days'] * df['hours_per_day']
            
            # Select columns to display
            display_df = df[['team_member', 'project', 'phase', 'start_date', 'end_date', 
                            'hours_per_day', 'total_hours', 'status']]
            
            st.dataframe(display_df)
            
            # Summary statistics
            st.markdown("#### Allocation Summary")
            summary_data = []
            
            for member in team_members:
                member_entries = [e for e in filtered_entries if e['team_member'] == member]
                
                if member_entries:
                    # Calculate total allocated hours
                    total_allocated = sum(
                        (datetime.strptime(e['end_date'], '%Y-%m-%d') - 
                         datetime.strptime(e['start_date'], '%Y-%m-%d')).days + 1 
                        * e['hours_per_day'] for e in member_entries
                    )
                    
                    # Get weekly availability
                    weekly_availability = st.session_state.team_members[member]['availability_hours']
                    
                    # Calculate allocation by phase
                    phase_allocation = {}
                    for phase in audit_phases:
                        phase_entries = [e for e in member_entries if e['phase'] == phase]
                        phase_hours = sum(
                            (datetime.strptime(e['end_date'], '%Y-%m-%d') - 
                             datetime.strptime(e['start_date'], '%Y-%m-%d')).days + 1 
                            * e['hours_per_day'] for e in phase_entries
                        )
                        phase_allocation[phase] = phase_hours
                    
                    # Add to summary data
                    summary_data.append({
                        'Team Member': member,
                        'Weekly Availability': weekly_availability,
                        'Total Allocated Hours': total_allocated,
                        **{f"{phase} Hours": phase_allocation.get(phase, 0) for phase in audit_phases}
                    })
            
            if summary_data:
                summary_df = pd.DataFrame(summary_data)
                st.dataframe(summary_df)
            
            # Option to delete entries
            if st.button("Delete Selected Entries"):
                st.warning("This feature would allow deleting selected entries.")
        else:
            st.info("No schedule entries match the selected filters.")
    else:
        st.info("No schedule entries found. Create your first entry above.")

def manage_team_members():
    """Manages team members including their general availability."""
    st.markdown("### Team Members")
    
    # Add new team member
    with st.expander("Add New Team Member", expanded=False):
        with st.form("new_team_member"):
            name = st.text_input("Name")
            role = st.selectbox("Role", ["Partner", "Manager", "Qualified Assistant", "Senior Article", "Junior Article"])
            skills = st.multiselect("Skills", ["Audit", "Tax", "Advisory", "IT", "Forensic", "Valuation"])
            
            # Weekly availability
            availability_hours = st.number_input(
                "Weekly Availability (hours)", 
                min_value=0.0, 
                max_value=80.0, 
                value=40.0, 
                step=0.5,
                help="Total hours available per week across all projects and phases"
            )
            
            hourly_rate = st.number_input("Hourly Rate", min_value=0.0, value=100.0, step=10.0)
            
            submitted = st.form_submit_button("Add Team Member")
            
            if submitted and name:
                if name in st.session_state.team_members:
                    st.error(f"Team member '{name}' already exists.")
                else:
                    st.session_state.team_members[name] = {
                        'name': name,
                        'role': role,
                        'skills': skills,
                        'availability_hours': availability_hours,
                        'hourly_rate': hourly_rate
                    }
                    save_team_members_to_db()
                    st.success(f"Team member '{name}' added successfully.")
    
    # Display and edit team members
    if st.session_state.team_members:
        st.markdown("#### Current Team Members")
        
        # Convert to DataFrame for display
        team_df = pd.DataFrame([
            {
                'Name': name,
                'Role': member['role'],
                'Skills': ', '.join(member['skills']),
                'Weekly Availability (hours)': member['availability_hours'],
                'Hourly Rate': member['hourly_rate']
            }
            for name, member in st.session_state.team_members.items()
        ])
        
        st.dataframe(team_df)
        
        # Edit team member
        with st.expander("Edit Team Member", expanded=False):
            selected_member = st.selectbox("Select Team Member to Edit", list(st.session_state.team_members.keys()))
            
            if selected_member:
                member = st.session_state.team_members[selected_member]
                
                with st.form("edit_team_member"):
                    role = st.selectbox("Role", ["Partner", "Manager", "Qualified Assistant", "Senior Article", "Junior Article"], 
                                       index=["Partner", "Manager", "Qualified Assistant", "Senior Article", "Junior Article"].index(member['role']))
                    skills = st.multiselect("Skills", ["Audit", "Tax", "Advisory", "IT", "Forensic", "Valuation"], 
                                           default=member['skills'])
                    
                    # Weekly availability
                    availability_hours = st.number_input(
                        "Weekly Availability (hours)", 
                        min_value=0.0, 
                        max_value=80.0, 
                        value=member['availability_hours'], 
                        step=0.5,
                        help="Total hours available per week across all projects and phases"
                    )
                    
                    hourly_rate = st.number_input("Hourly Rate", min_value=0.0, value=member['hourly_rate'], step=10.0)
                    
                    update_submitted = st.form_submit_button("Update Team Member")
                    
                    if update_submitted:
                        st.session_state.team_members[selected_member].update({
                            'role': role,
                            'skills': skills,
                            'availability_hours': availability_hours,
                            'hourly_rate': hourly_rate
                        })
                        save_team_members_to_db()
                        st.success(f"Team member '{selected_member}' updated successfully.")
    else:
        st.info("No team members found. Add your first team member above.")

# The materiality calculator function is now imported from materiality_calculator.py