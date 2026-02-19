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
        """Upload ZIP to S3 and return pre-signed URL"""
        try:
            logger.info(f"Uploading {local_path} to S3...")
            
            # Upload file
            self.s3_client.upload_file(local_path, self.bucket_name, s3_key)
            
            # Generate pre-signed URL (valid for 7 days)
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=604800  # 7 days
            )
            logger.info(f"Uploaded with pre-signed URL")
            return url
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            raise
