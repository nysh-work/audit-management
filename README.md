# Statutory Audit Budget Calculator & Time Tracker

## Overview

This application is a comprehensive tool for chartered accountancy firms to manage statutory audit engagements. It offers budget calculation, time tracking, and reporting capabilities to streamline audit planning and execution.

The Audit Budget Calculator provides automated budget recommendations based on client characteristics and risk factors. The integrated Time Tracking system allows team members to log hours against specific projects and audit phases. Detailed reports help manage resources effectively and monitor audit progress.

## Features

- **Audit Budget Calculator**: Generate detailed audit budgets based on company size, industry sector, and risk factors
- **Staff Allocation Planning**: Automatically calculate optimal staffing based on audit complexity 
- **Time Tracking**: Log and monitor hours spent by team members across audit phases
- **Project Reports**: View comprehensive project progress metrics and visualizations
- **Team Reports**: Analyze team utilization across multiple projects
- **Data Export**: Generate Excel reports for further analysis
- **Dark/Light Mode**: Toggle between appearance themes based on preference
- **Secure Database Management**: Password-protected backup and restore functionality
- **Cloud Storage**: Google Cloud Storage integration for data persistence when deployed on GCP

## Installation & Setup

### Local Development

1. Clone the repository:
   ```
   git clone <repository-url>
   cd audit-budget-calculator
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   streamlit run audit_budget_calculator.py
   ```

### Cloud Deployment (Google Cloud Platform)

1. Ensure you have [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) installed

2. Create a Google Cloud Storage bucket:
   ```
   gsutil mb gs://audit-app-storage
   ```

3. Build and deploy to Cloud Run:
   ```
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/audit-app
   
   gcloud run deploy audit-budget-app \
     --image gcr.io/YOUR_PROJECT_ID/audit-app \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars="BUCKET_NAME=audit-app-storage,CLOUD_RUN_SERVICE=true"
   ```

## Usage Guide

### Budget Calculator

1. Navigate to the "Budget Calculator" tab
2. Enter company details including name, turnover, industry sector
3. Set risk factors (controls risk, inherent risk, complexity, information delay)
4. Assign team members
5. Click "Calculate and Save Project"

### Time Tracking

1. Navigate to the "Time Tracking" tab
2. Select a project from the dropdown
3. Choose the team member, audit phase, and date
4. Enter hours spent and description
5. Click "Add Time Entry"

### Reports

- **Project Reports**: Analyze individual project progress, resource allocation, and timeline
- **Team Reports**: View team member utilization across projects and audit phases

### Database Management

Access the Database Management section in the sidebar:
1. Click "Unlock Admin Features"
2. Enter the admin password (default: "audit2025")
3. Use "Create Database Backup" to create backups
4. Use "Restore from Backup" to restore from a previous backup

## Technical Details

### Main Components

- **Frontend**: Streamlit framework with custom CSS styling
- **Data Storage**: SQLite database for local development, Google Cloud Storage for cloud deployment
- **Visualization**: Plotly for interactive charts and graphs
- **Export**: Pandas and XlsxWriter for Excel report generation

### File Structure

- `audit_budget_calculator.py`: Main application file
- `cloud_storage.py`: Google Cloud Storage integration
- `requirements.txt`: Python dependencies
- `Dockerfile`: Container configuration for deployment
- `.devcontainer/`: Development container configuration

## Administration

### Security

- Admin functions are protected with a password
- When deployed to Cloud Run, Google Cloud IAM provides additional security
- Database backups are maintained for disaster recovery

### Backup and Restore

- Manual backup creation via the sidebar
- Automatic cloud backups when deployed on GCP
- Restore functionality to roll back to previous database versions

## Customization

The application includes several industry sectors and baseline audit hours for different company sizes. To add or modify these:

1. Update the `industry_sectors` dictionary 
2. Modify the `detailed_time_estimates` dictionary for different company sizes

## Credits

Developed by Nishanth under MIT License.

## Support

For issues, feature requests, or questions, please submit an issue on the GitHub repository or contact the development team.
