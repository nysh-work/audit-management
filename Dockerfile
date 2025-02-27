FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV STREAMLIT_SERVER_PORT=8080
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ENABLECORS=false
ENV CLOUD_RUN_SERVICE=true
ENV BUCKET_NAME=audit-app-storage

# Command to run the application
CMD ["streamlit", "run", "audit_budget_calculator.py", "--server.port=8080", "--server.address=0.0.0.0"]