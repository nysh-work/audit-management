from google.cloud import storage
import os
import tempfile
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CloudStorageManager:
    def __init__(self, bucket_name):
        self.bucket_name = bucket_name
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)
        
        # Create bucket if it doesn't exist
        if not self.bucket.exists():
            logger.info(f"Creating bucket {bucket_name}")
            self.bucket = self.client.create_bucket(bucket_name)
    
    def download_file(self, source_blob_name, destination_file_name):
        """Downloads a file from GCS to the local filesystem."""
        try:
            blob = self.bucket.blob(source_blob_name)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(destination_file_name), exist_ok=True)
            
            # Download the file
            blob.download_to_filename(destination_file_name)
            logger.info(f"Downloaded {source_blob_name} to {destination_file_name}")
            return True
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return False
    
    def upload_file(self, source_file_name, destination_blob_name):
        """Uploads a file from the local filesystem to GCS."""
        try:
            blob = self.bucket.blob(destination_blob_name)
            blob.upload_from_filename(source_file_name)
            logger.info(f"Uploaded {source_file_name} to {destination_blob_name}")
            return True
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return False
    
    def list_files(self, prefix=None):
        """Lists all files in the bucket with the given prefix."""
        blobs = self.client.list_blobs(self.bucket_name, prefix=prefix)
        return [blob.name for blob in blobs]
    
    def file_exists(self, blob_name):
        """Checks if a file exists in the bucket."""
        blob = self.bucket.blob(blob_name)
        return blob.exists()