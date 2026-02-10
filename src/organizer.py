"""Code Organization Service"""
import os
import shutil
from pathlib import Path
from typing import Dict, List

class CodeOrganizer:
    def __init__(self):
        self.file_categories = {
            'api': ['.py'],  # API related files
            'models': ['.py'],  # Data models
            'services': ['.py'],  # Business logic
            'utils': ['.py'],  # Utility functions
            'tests': ['.py'],  # Test files
            'config': ['.env', '.json', '.yaml', '.yml'],  # Configuration
            'docs': ['.md', '.txt', '.rst'],  # Documentation
            'static': ['.css', '.js', '.html'],  # Static files
            'requirements': ['.txt']  # Dependencies
        }
    
    def organize_project(self, source_path: str, target_path: str = None) -> Dict:
        """Organize code into proper folder structure"""
        source = Path(source_path)
        if not target_path:
            target_path = source.parent / f"{source.name}_organized"
        
        target = Path(target_path)
        target.mkdir(exist_ok=True)
        
        # Create organized structure
        structure = {
            'app': ['api', 'models', 'services', 'core', 'utils'],
            'static': ['html', 'css', 'js', 'images', 'fonts'],
            'tests': [],
            'config': [],
            'docs': [],
            'requirements': []
        }
        
        # Create directories
        for main_dir, sub_dirs in structure.items():
            main_path = target / main_dir
            main_path.mkdir(exist_ok=True)
            for sub_dir in sub_dirs:
                (main_path / sub_dir).mkdir(exist_ok=True)
        
        # Organize files
        organized_files = []
        for file_path in source.rglob('*'):
            if file_path.is_file() and not file_path.name.startswith('.'):
                new_location = self._categorize_file(file_path, target)
                if new_location:
                    shutil.copy2(file_path, new_location)
                    organized_files.append({
                        'original': str(file_path),
                        'organized': str(new_location)
                    })
        
        # Create __init__.py files
        self._create_init_files(target)
        
        return {
            'source_path': str(source),
            'organized_path': str(target),
            'files_organized': len(organized_files),
            'structure_created': list(structure.keys()),
            'organized_files': organized_files
        }
    
    def _categorize_file(self, file_path: Path, target: Path) -> Path:
        """Categorize file based on name and content"""
        filename = file_path.name.lower()
        ext = file_path.suffix.lower()
        
        # Skip hidden files and common ignore patterns
        if filename.startswith('.') or '__pycache__' in str(file_path):
            return None
        
        # HTML files
        if ext in ['.html', '.htm']:
            return target / 'static' / 'html' / file_path.name
        
        # CSS files
        elif ext in ['.css', '.scss', '.sass']:
            return target / 'static' / 'css' / file_path.name
        
        # JavaScript files
        elif ext in ['.js', '.jsx', '.ts', '.tsx']:
            return target / 'static' / 'js' / file_path.name
        
        # Images
        elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp']:
            return target / 'static' / 'images' / file_path.name
        
        # Fonts
        elif ext in ['.woff', '.woff2', '.ttf', '.eot', '.otf']:
            return target / 'static' / 'fonts' / file_path.name
        
        # Python files
        elif ext == '.py':
            # API files
            if 'api' in filename or 'router' in filename or 'endpoint' in filename:
                return target / 'app' / 'api' / file_path.name
            # Model files
            elif 'model' in filename or 'schema' in filename:
                return target / 'app' / 'models' / file_path.name
            # Service files
            elif 'service' in filename or 'agent' in filename or 'scanner' in filename or 'analyzer' in filename or 'fixer' in filename:
                return target / 'app' / 'services' / file_path.name
            # Utility files
            elif 'util' in filename or 'helper' in filename:
                return target / 'app' / 'utils' / file_path.name
            # Test files
            elif 'test' in filename or filename.startswith('test_'):
                return target / 'tests' / file_path.name
            # Main files
            elif filename in ['main.py', 'app.py', 'run.py']:
                return target / file_path.name
            # Default to core
            else:
                return target / 'app' / 'core' / file_path.name
        
        # Config files
        elif ext in ['.env', '.json', '.yaml', '.yml', '.toml', '.ini'] or 'config' in filename:
            return target / 'config' / file_path.name
        
        # Requirements
        elif 'requirements' in filename or 'package.json' in filename:
            return target / 'requirements' / file_path.name
        
        # Documentation
        elif ext in ['.md', '.txt', '.rst']:
            return target / 'docs' / file_path.name
        
        return None
    
    def _create_init_files(self, target: Path):
        """Create __init__.py files for Python packages"""
        init_content = '"""Auto-generated package file"""'
        
        # Create __init__.py in all Python package directories
        python_dirs = [
            target / 'app',
            target / 'app' / 'api',
            target / 'app' / 'models', 
            target / 'app' / 'services',
            target / 'app' / 'core',
            target / 'app' / 'utils',
            target / 'tests'
        ]
        
        for dir_path in python_dirs:
            if dir_path.exists():
                init_file = dir_path / '__init__.py'
                if not init_file.exists():
                    init_file.write_text(init_content)