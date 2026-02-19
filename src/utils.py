"""Backup, file ops"""
import shutil
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

def backup_file(file_path):
    """Create backup of file - avoid multiple backups"""
    file_path = Path(file_path)
    
    if '.backup_' in file_path.name:
        return file_path
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = file_path.with_name(f'{file_path.stem}.backup_{timestamp}{file_path.suffix}')
    
    try:
        logger.info(f"Creating backup: {backup_path.name}")
        shutil.copy2(file_path, backup_path)
        return backup_path
    except (IOError, PermissionError) as e:
        logger.error(f"Backup failed: {e}")
        return file_path

def write_file(file_path, content):
    """Write content to file with immediate flush"""
    try:
        logger.debug(f"Writing file: {file_path}")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            f.flush()
            import os
            os.fsync(f.fileno())
        logger.debug(f"File written successfully: {file_path}")
    except (IOError, PermissionError) as e:
        logger.error(f"Failed to write file {file_path}: {e}")
        raise

def validate_fix(original_content, fixed_content):
    """Basic validation of fixed code"""
    if not fixed_content or not fixed_content.strip():
        logger.warning("Fixed content is empty")
        return False
    
    if len(fixed_content) < len(original_content) * 0.2:
        logger.warning("Fixed content too short")
        return False
    
    return True