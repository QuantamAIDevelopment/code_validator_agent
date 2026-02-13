"""Organizer Agent - Moves files safely"""
import shutil
from pathlib import Path
from typing import Dict, List

class OrganizerAgent:
    def organize(self, scan_data: Dict, target: Path, detection: Dict) -> List[Dict]:
        """Organize files into target structure"""
        organized = []
        
        for file_path in scan_data['files']:
            new_location = self._categorize(file_path, target, detection)
            if new_location:
                new_location.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, new_location)
                organized.append({'original': str(file_path), 'organized': str(new_location)})
        
        return organized
    
    def _categorize(self, file_path: Path, target: Path, detection: Dict) -> Path:
        """Categorize file based on name and extension"""
        filename = file_path.name.lower()
        ext = file_path.suffix.lower()
        primary = detection['primary_language']
        
        # Config files
        if ext in ['.env', '.json', '.yaml', '.yml', '.properties']:
            if filename in ['application.properties', 'application.yml']:
                return target / 'src/main/resources' / file_path.name
            return target / 'config' / file_path.name
        
        # Docs
        if ext in ['.md', '.txt', '.rst']:
            return target / 'docs' / file_path.name
        
        # Tests
        if 'test' in filename:
            return target / 'tests' / file_path.name
        
        # Python
        if ext == '.py':
            if 'api' in filename or 'controller' in filename:
                return target / 'app' / 'api' / file_path.name
            elif 'model' in filename:
                return target / 'app' / 'models' / file_path.name
            elif 'service' in filename:
                return target / 'app' / 'services' / file_path.name
            return target / 'app' / 'core' / file_path.name
        
        # JavaScript/TypeScript
        elif ext in ['.js', '.jsx', '.ts', '.tsx']:
            if 'component' in filename:
                return target / 'src' / 'components' / file_path.name
            elif 'service' in filename:
                return target / 'src' / 'services' / file_path.name
            return target / 'src' / file_path.name
        
        # Java
        elif ext == '.java':
            if 'controller' in filename:
                return target / 'src/main/java' / 'controller' / file_path.name
            elif 'service' in filename:
                return target / 'src/main/java' / 'service' / file_path.name
            elif 'model' in filename:
                return target / 'src/main/java' / 'model' / file_path.name
            elif 'repository' in filename:
                return target / 'src/main/java' / 'repository' / file_path.name
            return target / 'src/main/java' / file_path.name
        
        # Default
        return target / 'src' / file_path.name
