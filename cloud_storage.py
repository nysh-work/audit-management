# cloud_storage.py
"""Module for managing Google Cloud Storage operations."""
import os
import logging
from google.cloud import storage
from google.cloud.exceptions import NotFound, Conflict
import streamlit as st

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define tabs
tab_dashboard, tab_other = st.tabs(["Dashboard", "Other Tab"])

# Use the tab
with tab_dashboard:
    st.write("This is the dashboard tab.")

class CloudStorageManager:
    """Class to manage Google Cloud Storage operations."""
    def __init__(self, bucket_name):
        self.bucket_name = bucket_name
        self.client = storage.Client()
        
        # Get or create the bucket
        try:
            self.bucket = self.client.get_bucket(bucket_name)
            logger.info("Connected to bucket: %s", bucket_name)
        except NotFound:
            logger.info("Bucket %s not found, creating it.", bucket_name)
            try:
                self.bucket = self.client.create_bucket(bucket_name)
                logger.info("Bucket %s created.", bucket_name)
            except Conflict:
                logger.info("Bucket %s already exists and you own it.", bucket_name)
                self.bucket = self.client.get_bucket(bucket_name)
        except Exception as e:
            logger.error("Error accessing bucket %s: %s", bucket_name, str(e))
    
    def upload_file(self, source_file_name, destination_blob_name):
        """Uploads a file from the local filesystem to GCS."""
        try:
            blob = self.bucket.blob(destination_blob_name)
            blob.upload_from_filename(source_file_name)
            logger.info("Uploaded %s to %s", source_file_name, destination_blob_name)
            return True
        except Exception as e:
            logger.error("Error uploading file: %s", e)
            return False
    
    def download_file(self, source_blob_name, destination_file_name):
        """Downloads a file from GCS to the local filesystem."""
        try:
            blob = self.bucket.blob(source_blob_name)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(destination_file_name), exist_ok=True)
            
            # Download the file
            blob.download_to_filename(destination_file_name)
            logger.info("Downloaded %s to %s", source_blob_name, destination_file_name)
            return True
        except Exception as e:
            logger.error("Error downloading file: %s", e)
            return False
    
    def file_exists(self, blob_name):
        """Checks if a file exists in the bucket."""
        blob = self.bucket.blob(blob_name)
        return blob.exists()
    
    def list_files(self, prefix=None):
        """Lists all files in the bucket with the given prefix."""
        blobs = self.client.list_blobs(self.bucket_name, prefix=prefix)
        return [blob.name for blob in blobs]