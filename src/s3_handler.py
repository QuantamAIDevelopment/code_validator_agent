"""AWS S3 Handler for ZIP file operations"""
import os
import boto3
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class S3Handler:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'ap-south-1')
        )
        self.bucket_name = os.getenv('S3_BUCKET_NAME', 'code-agent-bucket')
    
    def download_zip(self, s3_key: str, local_path: str) -> bool:
        """Download ZIP from S3"""
        try:
            logger.info(f"Downloading {s3_key} from S3...")
            self.s3_client.download_file(self.bucket_name, s3_key, local_path)
            logger.info(f"Downloaded to {local_path}")
            return True
        except Exception as e:
            logger.error(f"S3 download failed: {e}")
            raise
    
    def upload_zip(self, local_path: str, s3_key: str) -> str:
        """Upload ZIP to S3 and return public URL"""
        try:
            logger.info(f"Uploading {local_path} to S3...")
            self.s3_client.upload_file(local_path, self.bucket_name, s3_key)
            url = f"https://{self.bucket_name}.s3.{os.getenv('AWS_REGION', 'ap-south-1')}.amazonaws.com/{s3_key}"
            logger.info(f"Uploaded: {url}")
            return url
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            raise
