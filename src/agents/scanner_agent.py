"""Scanner Agent - Scans files and extracts metadata"""
from pathlib import Path
from typing import List, Dict

class ScannerAgent:
    def __init__(self):
        self.ignore_patterns = {
            '__pycache__', '.git', 'node_modules', '.venv', 'venv',
            'env', 'dist', 'build', '.idea', '.vscode', '.backup_'
        }
    
    def scan(self, source_path: Path) -> Dict:
        """Scan directory and extract file metadata"""
        files = []
        extensions = []
        filenames = []
        
        for file_path in source_path.rglob('*'):
            if file_path.is_file() and not self._should_ignore(file_path):
                files.append(file_path)
                extensions.append(file_path.suffix.lower())
                filenames.append(file_path.name.lower())
        
        return {
            'files': files,
            'extensions': extensions,
            'filenames': filenames,
            'total_files': len(files)
        }
    
    def _should_ignore(self, file_path: Path) -> bool:
        return (any(pattern in file_path.parts for pattern in self.ignore_patterns) 
                or file_path.name.startswith('.'))
