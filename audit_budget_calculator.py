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
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# Import the materiality calculator module
from materiality_calculator import create_materiality_calculator_dialog

# Define user credentials and roles
config = {
    'credentials': {
        'usernames': {
            'admin': {
                'name': 'Admin User',
                'password': 'hashed_password_for_admin',  # Use hashed passwords
                'role': 'admin'
            },
            'auditor': {
                'name': 'Auditor User',
                'password': 'hashed_password_for_auditor',  # Use hashed passwords
                'role': 'auditor'
            }
        }
    },
    'cookie': {
        'expiry_days': 30,
        'key': 'some_signature_key',
        'name': 'some_cookie_name'
    },
    'preauthorized': {
        'emails': []
    }
}

# Hash the passwords
# Retrieve hashed passwords from environment variables
admin_password = os.environ.get('ADMIN_PASSWORD_HASH', 'default_admin_hash')
auditor_password = os.environ.get('AUDITOR_PASSWORD_HASH', 'default_auditor_hash')

hashed_passwords = [admin_password, auditor_password]
config['credentials']['usernames']['admin']['password'] = hashed_passwords[0]
config['credentials']['usernames']['auditor']['password'] = hashed_passwords[1]

# Initialize the authenticator
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['preauthorized']
)

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
    BUCKET_NAME = os.environ.get('BUCKET_NAME', 'audit-app-storage')  # Replace with YOUR bucket name.
    cloud_storage = CloudStorageManager(BUCKET_NAME)
else:
    cloud_storage = None  # Initialize to None when not in the cloud

# Define industry sectors and time estimates
industry_sectors = {
    "MFG": {"name": "Manufacturing", "risk_factor": 1.0},
    "RET": {"name": "Retail", "risk_factor": 0.9},
    "TECH": {"name": "Technology", "risk_factor": 1.2},
    "FIN": {"name": "Financial Services", "risk_factor": 1.3},
    "HLTH": {"name": "Healthcare", "risk_factor": 1.1},
    "CONS": {"name": "Construction", "risk_factor": 1.0},
    "REAL": {"name": "Real Estate", "risk_factor": 0.9},
    "HOSP": {"name": "Hospitality", "risk_factor": 0.8},
    "TRAN": {"name": "Transportation", "risk_factor": 1.0},
    "ENER": {"name": "Energy", "risk_factor": 1.2},
    "TELE": {"name": "Telecommunications", "risk_factor": 1.1},
    "AGRI": {"name": "Agriculture", "risk_factor": 0.9},
    "PHAR": {"name": "Pharmaceuticals", "risk_factor": 1.3},
    "MEDIA": {"name": "Media & Entertainment", "risk_factor": 1.0},
    "EDU": {"name": "Education", "risk_factor": 0.8},
    "NPO": {"name": "Non-Profit", "risk_factor": 0.7}
}

# Define detailed time estimates by size and sector
detailed_time_estimates = {
    # Small Manufacturing
    "SMFG": {
        "planning": 40,
        "fieldwork": 120,
        "managerReview": 24,
        "partnerReview": 16,
        "total": 200
    },
    # Medium Manufacturing
    "MMFG": {
        "planning": 60,
        "fieldwork": 180,
        "managerReview": 36,
        "partnerReview": 24,
        "total": 300
    },
    # Large Manufacturing
    "LMFG": {
        "planning": 80,
        "fieldwork": 240,
        "managerReview": 48,
        "partnerReview": 32,
        "total": 400
    },
    # Very Large Manufacturing
    "VLMFG": {
        "planning": 120,
        "fieldwork": 360,
        "managerReview": 72,
        "partnerReview": 48,
        "total": 600
    }
}

# Default time estimate (fallback)
default_time_estimate = {
    "planning": 40,
    "fieldwork": 120,
    "managerReview": 24,
    "partnerReview": 16,
    "total": 200
}

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
        logging.info("Initializing database at %s", db_path)

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
        error_msg = "Database initialization error: %s" % str(e)
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
            logging.error("Error saving data to cloud storage: %s", e)
            st.error("Error saving data to files: %s", e)

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
        st.error("Error saving data to files: %s", e)

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
        logging.info("Data loaded successfully. Projects: %s, Time entries: %s, Team members: %s, Schedule entries: %s",
                    len(st.session_state.projects), len(st.session_state.time_entries),
                    len(st.session_state.team_members), len(st.session_state.schedule_entries))

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
            return False, "Cloud backup failed: %s" % str(e)

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
        return False, "Local backup failed: %s" % str(e)

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
                try:
                    cloud_storage.bucket.copy_blob(
                        projects_backup,
                        cloud_storage.bucket,
                        'data/projects.json'
                    )
                except Exception as e:
                    logging.error(f"Error restoring projects.json: {e}")

            entries_backup = cloud_storage.bucket.blob(f"backups/time_entries_{timestamp}.csv")
            if entries_backup.exists():
                try:
                    cloud_storage.bucket.copy_blob(
                        entries_backup,
                        cloud_storage.bucket,
                        'data/time_entries.csv'
                    )
                except Exception as e:
                    logging.error(f"Error restoring time_entries.csv: {e}")


            # Force a reload of the database
            db_path = get_db_path()
            cloud_storage.download_file('data/audit_management.db', db_path)

            return True, "Database restored successfully from cloud backup. Please refresh the page."
        except Exception as e:
                    return False, "Cloud restore failed: %s" % str(e)

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
        return False, "Local restore failed: %s" % str(e)

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
            logging.error("Error listing cloud backups: %s", e)
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

# --- VISUAL ENHANCEMENTS ---

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

    # Add Google Fonts for better typography
    st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    """, unsafe_allow_html=True)

# Function to create a professional header
def create_header():
    """Create a professional header for the application"""
    col1, col2 = st.columns([1, 5])

    with col1:
        # Display a default placeholder logo using CSS
        st.markdown("""
        <div style="background-color:#4F8DF5; width:60px; height:60px; border-radius:50%; display:flex;
        justify-content:center; align-items:center; color:white; font-weight:bold; font-size:28px;">
        V
        </div>
        """, unsafe_allow_html=True)

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
if 'team_members' not in st.session_state:
    st.session_state.team_members = {}
if 'schedule_entries' not in st.session_state:
    st.session_state.schedule_entries = []
if 'sidebar_authenticated' not in st.session_state:
    st.session_state.sidebar_authenticated = False
if 'sidebar_password_attempt' not in st.session_state:
    st.session_state.sidebar_password_attempt = False
if 'show_materiality_calculator' not in st.session_state:
    st.session_state.show_materiality_calculator = False

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

    st.divider()
    
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


# --- Project Management ---
section_header("Project Management", "💼")

with st.expander("Add New Project", expanded=False):
    with st.form(key='new_project_form'):
        project_name = st.text_input("Project Name", key='new_project_name')
        client_name = st.text_input("Client Name")
        industry_sector = st.selectbox("Industry Sector", options=list(industry_sectors.keys()), format_func=lambda x: industry_sectors[x]['name'])
        project_size = st.selectbox("Project Size", options=["Small", "Medium", "Large", "Very Large"])
        start_date = st.date_input("Start Date")
        end_date = st.date_input("End Date")
        total_budget = st.number_input("Total Budget", min_value=0.0)
        
        # Additional fields using a dictionary
        additional_fields = {}
        additional_fields['engagement_letter_signed'] = st.checkbox("Engagement Letter Signed")
        additional_fields['internal_approval'] = st.selectbox("Internal Approval Status", ["Pending", "Approved", "Rejected"])
        additional_fields['notes'] = st.text_area("Additional Notes")

        submit_button = st.form_submit_button("Add Project")

        if submit_button:
            if project_name:
                # Combine core project data and additional fields
                project_data = {
                    'client_name': client_name,
                    'industry_sector': industry_sector,
                    'project_size': project_size,
                    'start_date': start_date.strftime("%Y-%m-%d") if start_date else None,
                    'end_date': end_date.strftime("%Y-%m-%d") if end_date else None,
                    'total_budget': total_budget,
                    'creation_date': datetime.now().strftime("%Y-%m-%d"),  # Capture creation date
                    **additional_fields  # Add the additional fields
                }

                st.session_state.projects[project_name] = project_data
                save_data()  # Save immediately
                st.success(f"Project '{project_name}' added successfully!")
                st.rerun()
            else:
                st.error("Project name is required.")

# --- Project List and Editing ---
if st.session_state.projects:
    st.subheader("Existing Projects")

    # Create a list for the table, including the creation date
    project_list = []
    for name, data in st.session_state.projects.items():
        # Ensure dates are strings (for display and sorting)
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        creation_date_str = data.get('creation_date', '')  # Default to empty string if not found

        project_list.append({
            "Project Name": name,
            "Client": data.get('client_name', ''),
            "Industry": industry_sectors.get(data.get('industry_sector'), {}).get('name', 'N/A'),
            "Size": data.get('project_size', ''),
            "Start Date": start_date_str,
            "End Date": end_date_str,
            "Budget": data.get('total_budget', 0),
            "Creation Date": creation_date_str
        })

    df = pd.DataFrame(project_list)
    if not df.empty:
      df = df.sort_values(by="Creation Date", ascending=False) # Sort by creation date.
      st.dataframe(df, hide_index=True) #hiding the index makes it look nicer
    else:
      st.info("No projects found.")


    # Project editing and deletion
    selected_project = st.selectbox("Select Project to Edit/Delete", list(st.session_state.projects.keys()))

    col1, col2 = st.columns(2)
    with col1:
      if st.button("Edit Project"):
          st.session_state.edit_project = selected_project
    with col2:
      if st.button("Delete Project"):
          st.session_state.delete_project = selected_project

    # Project deletion
    if 'delete_project' in st.session_state:
        project_to_delete = st.session_state.delete_project
        del st.session_state.projects[project_to_delete]

        # Delete related time entries
        st.session_state.time_entries = [entry for entry in st.session_state.time_entries if entry['project'] != project_to_delete]

        # Delete related schedule entries
        st.session_state.schedule_entries = [entry for entry in st.session_state.schedule_entries if entry['project'] != project_to_delete]

        save_data()
        del st.session_state.delete_project
        st.success(f"Project '{project_to_delete}' and related entries deleted!")
        st.rerun()
    # Project editing form.  This is *outside* the if st.button block
    if 'edit_project' in st.session_state:
        project_to_edit = st.session_state.edit_project
        project_data = st.session_state.projects[project_to_edit]

        with st.form(key='edit_project_form'):
            st.subheader(f"Editing Project: {project_to_edit}")
            new_project_name = st.text_input("Project Name", value=project_to_edit, key='edit_project_name')
            client_name = st.text_input("Client Name", value=project_data.get('client_name', ''))
            industry_sector = st.selectbox("Industry Sector", options=list(industry_sectors.keys()), format_func=lambda x: industry_sectors[x]['name'], index=list(industry_sectors.keys()).index(project_data.get('industry_sector')) if project_data.get('industry_sector') in industry_sectors else 0)
            project_size = st.selectbox("Project Size", options=["Small", "Medium", "Large", "Very Large"], index=["Small", "Medium", "Large", "Very Large"].index(project_data.get('project_size')) if project_data.get('project_size') in ["Small", "Medium", "Large", "Very Large"] else 0)
            start_date = st.date_input("Start Date", value=datetime.strptime(project_data.get('start_date'), "%Y-%m-%d") if project_data.get('start_date') else None)
            end_date = st.date_input("End Date", value=datetime.strptime(project_data.get('end_date'), "%Y-%m-%d") if project_data.get('end_date') else None)
            total_budget = st.number_input("Total Budget", min_value=0.0, value=project_data.get('total_budget', 0.0))

            # Edit additional fields
            additional_fields = {}
            additional_fields['engagement_letter_signed'] = st.checkbox("Engagement Letter Signed", value=project_data.get('engagement_letter_signed', False))
            additional_fields['internal_approval'] = st.selectbox("Internal Approval Status", ["Pending", "Approved", "Rejected"], index=["Pending", "Approved", "Rejected"].index(project_data.get('internal_approval')) if project_data.get('internal_approval') in ["Pending", "Approved", "Rejected"] else 0)
            additional_fields['notes'] = st.text_area("Additional Notes", value=project_data.get('notes', ''))


            update_button = st.form_submit_button("Update Project")

            if update_button:
                # Remove the old project entry if the name has changed
                if new_project_name != project_to_edit:
                    del st.session_state.projects[project_to_edit]
                    # Update time entries and schedule entries to the new project name
                    for entry in st.session_state.time_entries:
                        if entry['project'] == project_to_edit:
                            entry['project'] = new_project_name
                    for entry in st.session_state.schedule_entries:
                         if entry['project'] == project_to_edit:
                            entry['project'] = new_project_name


                # Update the project data
                updated_project_data = {
                    'client_name': client_name,
                    'industry_sector': industry_sector,
                    'project_size': project_size,
                    'start_date': start_date.strftime("%Y-%m-%d") if start_date else None,
                    'end_date': end_date.strftime("%Y-%m-%d") if end_date else None,
                    'total_budget': total_budget,
                    'creation_date': project_data.get('creation_date', datetime.now().strftime("%Y-%m-%d")), #keep the original creation date
                    **additional_fields  # Include the updated additional fields
                }
                st.session_state.projects[new_project_name] = updated_project_data
                save_data()
                del st.session_state.edit_project  # Clear the edit state
                st.success(f"Project '{new_project_name}' updated successfully!")
                st.rerun()


# --- Time Tracking ---

section_header("Time Tracking", "⏱️")

with st.expander("Add New Time Entry", expanded=False):
    with st.form(key='new_time_entry_form'):
        project = st.selectbox("Project", options=list(st.session_state.projects.keys()))
        resource = st.text_input("Resource")
        phase = st.selectbox("Phase", options=["planning", "fieldwork", "managerReview", "partnerReview"])
        date_worked = st.date_input("Date")
        hours = st.number_input("Hours", min_value=0.0, format="%.2f")
        description = st.text_area("Description")
        submit_button = st.form_submit_button("Add Time Entry")

        if submit_button:
            # Validate that a project is selected
            if not project:
                st.error("Please select a project.")
            else:
                new_entry = {
                    'project': project,
                    'resource': resource,
                    'phase': phase,
                    'date': date_worked.strftime("%Y-%m-%d") if date_worked else None,  # Ensure date is stored as string
                    'hours': hours,
                    'description': description,
                    'entry_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                st.session_state.time_entries.append(new_entry)
                save_data()
                st.success("Time entry added!")
                st.rerun()

# Time Entry List, Editing, and Deletion
if st.session_state.time_entries:
    st.subheader("Existing Time Entries")
    
    # Convert dates to strings for display, and handle potential None values
    time_entry_list = []
    for entry in st.session_state.time_entries:
        entry_copy = entry.copy()  # Work with a copy to avoid modifying the original
        entry_copy['date'] = entry_copy.get('date', '')  # Default to empty string if None
        entry_copy['entry_time'] = entry_copy.get('entry_time', '')  # Same for entry_time
        time_entry_list.append(entry_copy)
    
    df = pd.DataFrame(time_entry_list)
    
    if not df.empty:
        # Display the DataFrame
        st.dataframe(df, hide_index=True)

        # Edit and Delete Time Entries
        selected_entry_index = st.selectbox("Select Time Entry to Edit/Delete", options=range(len(st.session_state.time_entries)), format_func=lambda x: st.session_state.time_entries[x]['entry_time'])

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Edit Time Entry"):
                st.session_state.edit_time_entry = selected_entry_index
        with col2:
            if st.button("Delete Time Entry"):
                st.session_state.delete_time_entry = selected_entry_index

    # Handle time entry deletion
    if 'delete_time_entry' in st.session_state:
        del st.session_state.time_entries[st.session_state.delete_time_entry]
        save_data()
        del st.session_state.delete_time_entry
        st.success("Time entry deleted!")
        st.rerun()  # Refresh the page

    # Handle time entry editing
    if 'edit_time_entry' in st.session_state:
        entry_to_edit = st.session_state.time_entries[st.session_state.edit_time_entry]
        with st.form(key='edit_time_entry_form'):
            st.subheader("Edit Time Entry")
            project = st.selectbox("Project", options=list(st.session_state.projects.keys()), index=list(st.session_state.projects.keys()).index(entry_to_edit['project']) if entry_to_edit['project'] in st.session_state.projects else 0 )
            resource = st.text_input("Resource", value=entry_to_edit['resource'])
            phase = st.selectbox("Phase", options=["planning", "fieldwork", "managerReview", "partnerReview"], index=["planning", "fieldwork", "managerReview", "partnerReview"].index(entry_to_edit['phase']) if entry_to_edit['phase'] in ["planning", "fieldwork", "managerReview", "partnerReview"] else 0)
            date_worked = st.date_input("Date", value=datetime.strptime(entry_to_edit['date'], "%Y-%m-%d") if entry_to_edit['date'] else None)
            hours = st.number_input("Hours", min_value=0.0, value=entry_to_edit['hours'], format="%.2f")
            description = st.text_area("Description", value=entry_to_edit['description'])
            submit_button = st.form_submit_button("Update Time Entry")

            if submit_button:
                entry_to_edit['project'] = project
                entry_to_edit['resource'] = resource
                entry_to_edit['phase'] = phase
                entry_to_edit['date'] = date_worked.strftime("%Y-%m-%d") if date_worked else None
                entry_to_edit['hours'] = hours
                entry_to_edit['description'] = description
                entry_to_edit['entry_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Update entry time
                save_data()
                del st.session_state.edit_time_entry
                st.success("Time entry updated!")
                st.rerun()

# --- Team Management ---
section_header("Team Management", "👥")

with st.expander("Add New Team Member", expanded=False):
    with st.form(key='new_team_member_form'):
        member_name = st.text_input("Team Member Name", key='new_team_member_name')
        role = st.selectbox("Role", options=["Staff", "Senior", "Manager", "Partner"])
        skills = st.multiselect("Skills", options=["Audit", "Tax", "Advisory", "Technical Accounting"])
        availability = st.number_input("Availability (hours/week)", min_value=0.0, max_value=168.0, step=0.5, value=40.0)
        hourly_rate = st.number_input("Hourly Rate", min_value=0.0, step=0.5, value=0.0)
        
        # Additional team member fields as a dictionary
        additional_info = {}
        additional_info['start_date'] = st.date_input("Start Date")
        additional_info['end_date'] = st.date_input("End Date", value=None)  # Allow None for ongoing
        additional_info['notes'] = st.text_area("Notes")
        
        submit_button = st.form_submit_button("Add Team Member")

        if submit_button:
            if member_name:
                 # Combine core and additional fields
                team_member_data = {
                    'role': role,
                    'skills': skills,
                    'availability_hours': availability,
                    'hourly_rate': hourly_rate,
                    **additional_info # Add the additional fields
                }
                st.session_state.team_members[member_name] = team_member_data
                save_data()
                st.success(f"Team member '{member_name}' added.")
                st.rerun()
            else:
                st.error("Team member name is required.")
# Team Member Listing, Editing, Deletion

if st.session_state.team_members:
    st.subheader("Team Members")
    team_member_list = []
    for name, data in st.session_state.team_members.items():
        team_member_list.append({
            "Name": name,
            "Role": data.get('role', ''),
            "Skills": ', '.join(data.get('skills', [])),
            "Availability (hrs/week)": data.get('availability_hours', 40.0),
            "Hourly Rate": data.get('hourly_rate', 0.0)
        })

    df_team = pd.DataFrame(team_member_list)
    if not df_team.empty:
        st.dataframe(df_team, hide_index = True)
    else:
        st.info("No team members found.")


    selected_member = st.selectbox("Select Team Member to Edit/Delete", list(st.session_state.team_members.keys()))
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Edit Team Member"):
            st.session_state.edit_team_member = selected_member
    with col2:
        if st.button("Delete Team Member"):
            st.session_state.delete_team_member = selected_member


    # Team member deletion
    if 'delete_team_member' in st.session_state:
        member_to_delete = st.session_state.delete_team_member
        del st.session_state.team_members[member_to_delete]

        # Delete related schedule entries
        st.session_state.schedule_entries = [entry for entry in st.session_state.schedule_entries if entry['team_member'] != member_to_delete]

        save_data()
        del st.session_state.delete_team_member
        st.success(f"Team member '{member_to_delete}' and related schedule entries deleted!")
        st.rerun()


    # Team member editing
    if 'edit_team_member' in st.session_state:
        member_to_edit = st.session_state.edit_team_member
        member_data = st.session_state.team_members[member_to_edit]
        with st.form(key='edit_team_member_form'):
            st.subheader(f"Editing Team Member: {member_to_edit}")
            new_member_name = st.text_input("Team Member Name", value=member_to_edit, key='edit_team_member_name')
            role = st.selectbox("Role", options=["Staff", "Senior", "Manager", "Partner"], index=["Staff", "Senior", "Manager", "Partner"].index(member_data.get('role')) if member_data.get('role') in ["Staff", "Senior", "Manager", "Partner"] else 0 )
            skills = st.multiselect("Skills", options=["Audit", "Tax", "Advisory", "Technical Accounting"], default=member_data.get('skills', []))
            availability = st.number_input("Availability (hours/week)", min_value=0.0, max_value=168.0, step=0.5, value=member_data.get('availability_hours', 40.0))
            hourly_rate = st.number_input("Hourly Rate", min_value=0.0, step=0.5, value=member_data.get('hourly_rate', 0.0))

            # Edit additional info
            additional_info = {}
            additional_info['start_date'] = st.date_input("Start Date", value=member_data.get('start_date'))
            additional_info['end_date'] = st.date_input("End Date", value=member_data.get('end_date'))  # Allow None
            additional_info['notes'] = st.text_area("Notes", value=member_data.get('notes', ''))

            update_button = st.form_submit_button("Update Team Member")

            if update_button:
                if new_member_name != member_to_edit:
                    del st.session_state.team_members[member_to_edit]

                    # Update schedule entries to the new name
                    for entry in st.session_state.schedule_entries:
                        if entry['team_member'] == member_to_edit:
                            entry['team_member'] = new_member_name
                updated_member_data = {
                    'role': role,
                    'skills': skills,
                    'availability_hours': availability,
                    'hourly_rate': hourly_rate,
                    **additional_info
                }

                st.session_state.team_members[new_member_name] = updated_member_data
                save_data()
                del st.session_state.edit_team_member
                st.success(f"Team member '{new_member_name}' updated.")
                st.rerun()
# --- Scheduling ---
section_header("Scheduling", "📅")

with st.expander("Add New Schedule Entry", expanded=False):
    with st.form(key='new_schedule_entry_form'):
        team_member = st.selectbox("Team Member", options=list(st.session_state.team_members.keys()))
        project = st.selectbox("Project", options=list(st.session_state.projects.keys()))
        start_date = st.date_input("Start Date")
        end_date = st.date_input("End Date")
        hours_per_day = st.number_input("Hours per Day", min_value=0.0, max_value=24.0, step=0.5, value=8.0)
        phase = st.selectbox("Phase", options=["planning", "fieldwork", "managerReview", "partnerReview"])
        status = st.selectbox("Status", options=["scheduled", "in progress", "completed"])
        notes = st.text_area("Notes")

        submit_button = st.form_submit_button("Add Schedule Entry")
        if submit_button:
            if not team_member or not project:
                st.error("Team member and project are required.")
            elif start_date > end_date:
                st.error("Start date must be before end date.")
            else:
                new_schedule_entry = {
                    'team_member': team_member,
                    'project': project,
                    'start_date': start_date.strftime("%Y-%m-%d") if start_date else None,  # String format
                    'end_date': end_date.strftime("%Y-%m-%d") if end_date else None,      # String format
                    'hours_per_day': hours_per_day,
                    'phase': phase,
                    'status': status,
                    'notes': notes,
                    'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'updated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                st.session_state.schedule_entries.append(new_schedule_entry)
                save_data()
                st.success("Schedule entry added!")
                st.rerun()

# Schedule Entry List, Editing, and Deletion
if st.session_state.schedule_entries:
    st.subheader("Scheduled Entries")
      # Convert date fields to strings for display, handle None
    schedule_entry_list = []
    for entry in st.session_state.schedule_entries:
        entry_copy = entry.copy()
        entry_copy['start_date'] = entry_copy.get('start_date', '')
        entry_copy['end_date'] = entry_copy.get('end_date', '')
        entry_copy['created_at'] = entry_copy.get('created_at', '')
        entry_copy['updated_at'] = entry_copy.get('updated_at', '')
        schedule_entry_list.append(entry_copy)

    df_schedule = pd.DataFrame(schedule_entry_list)

    if not df_schedule.empty:
        # Display the DataFrame
        st.dataframe(df_schedule, hide_index = True)
        selected_entry_index = st.selectbox("Select Schedule Entry to Edit/Delete", options=range(len(st.session_state.schedule_entries)), format_func=lambda x: f"{st.session_state.schedule_entries[x]['team_member']} - {st.session_state.schedule_entries[x]['project']} ({st.session_state.schedule_entries[x]['start_date']} to {st.session_state.schedule_entries[x]['end_date']})")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Edit Schedule Entry"):
                st.session_state.edit_schedule_entry = selected_entry_index
        with col2:
            if st.button("Delete Schedule Entry"):
                st.session_state.delete_schedule_entry = selected_entry_index
    else:
        st.info("No schedule entries found.")

     # Handle schedule entry deletion
    if 'delete_schedule_entry' in st.session_state:
        del st.session_state.schedule_entries[st.session_state.delete_schedule_entry]
        save_data()
        del st.session_state.delete_schedule_entry
        st.success("Schedule entry deleted!")
        st.rerun()

    # Handle schedule entry editing
    if 'edit_schedule_entry' in st.session_state:
        entry_to_edit = st.session_state.schedule_entries[st.session_state.edit_schedule_entry]
        with st.form(key='edit_schedule_entry_form'):
            st.subheader("Edit Schedule Entry")
            team_member = st.selectbox("Team Member", options=list(st.session_state.team_members.keys()), index=list(st.session_state.team_members.keys()).index(entry_to_edit['team_member']) if entry_to_edit['team_member'] in st.session_state.team_members else 0)
            project = st.selectbox("Project", options=list(st.session_state.projects.keys()), index=list(st.session_state.projects.keys()).index(entry_to_edit['project']) if entry_to_edit['project'] in st.session_state.projects else 0)
            start_date = st.date_input("Start Date", value=datetime.strptime(entry_to_edit['start_date'], "%Y-%m-%d") if entry_to_edit['start_date'] else None)
            end_date = st.date_input("End Date", value=datetime.strptime(entry_to_edit['end_date'], "%Y-%m-%d") if entry_to_edit['end_date'] else None)
            hours_per_day = st.number_input("Hours per Day", min_value=0.0, max_value=24.0, step=0.5, value=entry_to_edit['hours_per_day'])
            phase = st.selectbox("Phase", options=["planning", "fieldwork", "managerReview", "partnerReview"], index=["planning", "fieldwork", "managerReview", "partnerReview"].index(entry_to_edit['phase']) if entry_to_edit['phase'] in ["planning", "fieldwork", "managerReview", "partnerReview"] else 0)
            status = st.selectbox("Status", options=["scheduled", "in progress", "completed"], index=["scheduled", "in progress", "completed"].index(entry_to_edit['status']) if entry_to_edit['status'] in ["scheduled", "in progress", "completed"] else 0)
            notes = st.text_area("Notes", value=entry_to_edit['notes'])
            submit_button = st.form_submit_button("Update Schedule Entry")

            if submit_button:
                if start_date > end_date:
                    st.error("Start date must be before end date.")
                else:
                    entry_to_edit['team_member'] = team_member
                    entry_to_edit['project'] = project
                    entry_to_edit['start_date'] = start_date.strftime("%Y-%m-%d") if start_date else None
                    entry_to_edit['end_date'] = end_date.strftime("%Y-%m-%d") if end_date else None
                    entry_to_edit['hours_per_day'] = hours_per_day
                    entry_to_edit['phase'] = phase
                    entry_to_edit['status'] = status
                    entry_to_edit['notes'] = notes
                    entry_to_edit['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Update 'updated_at'
                    save_data()
                    del st.session_state.edit_schedule_entry
                    st.success("Schedule entry updated!")
                    st.rerun()

# --- Reporting ---
section_header("Reporting", "📊")

# Budget vs. Actual
st.subheader("Budget vs. Actual")

# Aggregate time entries by project and phase
project_phase_summary = {}
for entry in st.session_state.time_entries:
    project = entry['project']
    phase = entry['phase']
    hours = entry['hours']
    if project not in project_phase_summary:
        project_phase_summary[project] = {}
    if phase not in project_phase_summary[project]:
        project_phase_summary[project][phase] = 0
    project_phase_summary[project][phase] += hours

# Prepare data for budget vs. actual chart
budget_data = []
for project, project_data in st.session_state.projects.items():
    total_budget = project_data.get('total_budget', 0)
    actual_hours = sum(project_phase_summary.get(project, {}).values())

    # Get hourly rates for team members involved in the project
    team_member_rates = {}
    for entry in st.session_state.time_entries:
        if entry['project'] == project:
            member = entry['resource']
            if member not in team_member_rates:
                # Find the team member in the team_members dictionary
                for name, member_data in st.session_state.team_members.items():
                     if name == member: #If the team member's name matches
                        team_member_rates[member] = member_data.get('hourly_rate', 0)  # Get hourly rate or default to 0
                        break  # Exit inner loop once found


    # Calculate actual cost based on hours and hourly rates
    actual_cost = 0
    for entry in st.session_state.time_entries:
      if entry['project'] == project:
        member = entry['resource']
        hourly_rate = team_member_rates.get(member, 0)
        actual_cost += entry['hours'] * hourly_rate


    budget_data.append({
        "Project": project,
        "Type": "Budget",
        "Value": total_budget
    })
    budget_data.append({
        "Project": project,
        "Type": "Actual",
        "Value": actual_cost
    })

budget_df = pd.DataFrame(budget_data)

if not budget_df.empty:
    fig_budget = px.bar(budget_df, x="Project", y="Value", color="Type", barmode="group",
                        color_discrete_map={"Budget": COLOR_PRIMARY, "Actual": COLOR_SECONDARY})
    fig_budget = style_plotly_chart(fig_budget, "Project Budget vs. Actual Cost")  # Apply consistent styling
    st.plotly_chart(fig_budget, use_container_width=True)
else:
    st.info("No data available for budget vs. actual comparison.")



# Time by Phase
st.subheader("Time by Phase")

# Prepare data for time by phase chart
phase_data = []
for project, phases in project_phase_summary.items():
    for phase, hours in phases.items():
        phase_data.append({
            "Project": project,
            "Phase": phase,
            "Hours": hours
        })

phase_df = pd.DataFrame(phase_data)

if not phase_df.empty:
    fig_phase = px.bar(phase_df, x="Project", y="Hours", color="Phase",
                       color_discrete_sequence=px.colors.qualitative.Pastel) #Using a nice color palette
    fig_phase = style_plotly_chart(fig_phase, "Time Spent per Phase")  # Consistent styling
    st.plotly_chart(fig_phase, use_container_width=True)
else:
    st.info("No data available for time by phase breakdown.")



# Time by Resource (Team Member)
st.subheader("Time by Resource")
resource_data = []
for entry in st.session_state.time_entries:
    resource_data.append({
        "Resource": entry['resource'],
        "Project": entry['project'],
        "Hours": entry['hours']
    })
resource_df = pd.DataFrame(resource_data)

if not resource_df.empty:
    resource_summary = resource_df.groupby(['Resource', 'Project'])['Hours'].sum().reset_index()
    fig_resource = px.bar(resource_summary, x="Resource", y="Hours", color="Project",
                          color_discrete_sequence=px.colors.qualitative.Prism)  # Another nice palette
    fig_resource = style_plotly_chart(fig_resource, "Time Spent by Resource")
    st.plotly_chart(fig_resource, use_container_width=True)
else:
    st.info("No data available for time by resource breakdown.")
