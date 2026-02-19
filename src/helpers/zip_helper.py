"""ZIP File Operations Helper"""
import os
import zipfile
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ZipHelper:
    @staticmethod
    def extract_zip(zip_path, extract_dir):
        """Extract ZIP and handle nested folders"""
        logger.info(f"Extracting ZIP to {extract_dir}")
        os.makedirs(extract_dir, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        items = [i for i in os.listdir(extract_dir) if not i.startswith('.')]
        logger.info(f"Extracted items: {items}")
        
        if len(items) == 1 and os.path.isdir(os.path.join(extract_dir, items[0])):
            nested_dir = os.path.join(extract_dir, items[0])
            logger.info(f"Using nested folder: {nested_dir}")
            return nested_dir
        
        return extract_dir
    
    @staticmethod
    def create_zip(source_dir, output_path, exclude_git=True):
        """Create ZIP from directory"""
        logger.info(f"Creating ZIP from {source_dir}")
        files_added = 0
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_dir):
                if exclude_git and '.git' in root:
                    continue
                for file_item in files:
                    file_path = os.path.join(root, file_item)
                    arcname = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arcname)
                    files_added += 1
        
        logger.info(f"ZIP created with {files_added} files")
        return files_added
