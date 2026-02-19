"""Application scan logic"""
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class Scanner:
    def __init__(self):
        self.supported_extensions = [
            '.py', '.js', '.jsx', '.ts', '.tsx',
            '.html', '.css', '.scss', '.sass',
            '.java', '.cpp', '.c', '.h',
            '.php', '.rb', '.go', '.rs',
            '.json', '.xml', '.yaml', '.yml'
        ]
        self.ignore_dirs = {'node_modules', '.git', '__pycache__', 'venv', 'env', '.venv', 'dist', 'build'}
    
    def scan(self, path):
        """Scan application for files - fresh scan every time"""
        logger.info(f"Scanning path: {path}")
        target_path = Path(path)
        files = []
        
        if target_path.is_file():
            if target_path.suffix in self.supported_extensions and '.backup_' not in target_path.name:
                files.append(target_path)
        elif target_path.is_dir():
            for ext in self.supported_extensions:
                try:
                    for f in target_path.rglob(f'*{ext}'):
                        if '.backup_' not in f.name and not any(ignored in f.parts for ignored in self.ignore_dirs):
                            files.append(f)
                except PermissionError as e:
                    logger.warning(f"Permission denied accessing files: {e}")
        
        unique_files = list(set(files))
        logger.info(f"Found {len(unique_files)} files")
        return unique_files