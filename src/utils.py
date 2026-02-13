"""Backup, file ops"""
import shutil
from pathlib import Path
from datetime import datetime

def backup_file(file_path):
    """Create backup of file - avoid multiple backups"""
    file_path = Path(file_path)
    
    # Skip if already a backup file
    if '.backup_' in file_path.name:
        return file_path
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = file_path.with_name(f'{file_path.stem}.backup_{timestamp}{file_path.suffix}')
    
    try:
        shutil.copy2(file_path, backup_path)
        return backup_path
    except Exception as e:
        print(f"Backup failed: {e}")
        return file_path

def write_file(file_path, content):
    """Write content to file with immediate flush"""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
        f.flush()
        import os
        os.fsync(f.fileno())

def validate_fix(original_content, fixed_content):
    """Basic validation of fixed code"""
    if not fixed_content or not fixed_content.strip():
        return False
    
    # More lenient - allow changes as long as content exists
    if len(fixed_content) < len(original_content) * 0.2:
        return False
    
    return True