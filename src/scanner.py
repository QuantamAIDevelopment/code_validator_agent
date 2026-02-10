"""Application scan logic"""
import os
from pathlib import Path

class Scanner:
    def __init__(self):
        self.supported_extensions = [
            '.py', '.js', '.jsx', '.ts', '.tsx',  # Python & JavaScript
            '.html', '.css', '.scss', '.sass',     # Web
            '.java', '.cpp', '.c', '.h',           # Java & C/C++
            '.php', '.rb', '.go', '.rs',           # Other languages
            '.json', '.xml', '.yaml', '.yml'       # Config files
        ]
    
    def scan(self, path):
        """Scan application for files - fresh scan every time"""
        target_path = Path(path)
        files = []
        
        if target_path.is_file():
            if target_path.suffix in self.supported_extensions and '.backup_' not in target_path.name:
                files.append(target_path)
        elif target_path.is_dir():
            # Fresh scan every time - no caching, skip backup files and common ignore dirs
            ignore_dirs = {'node_modules', '.git', '__pycache__', 'venv', 'env', '.venv', 'dist', 'build'}
            for ext in self.supported_extensions:
                for f in target_path.rglob(f'*{ext}'):
                    # Skip if in ignored directory or is backup file
                    if '.backup_' not in f.name and not any(ignored in f.parts for ignored in ignore_dirs):
                        files.append(f)
        
        # Remove duplicates and return fresh list
        return list(set(files))