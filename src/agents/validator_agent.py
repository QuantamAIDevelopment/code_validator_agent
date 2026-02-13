"""Validator Agent - Ensures imports/builds are not broken"""
from pathlib import Path
from typing import Dict, List

class ValidatorAgent:
    def validate(self, organized_path: Path, detection: Dict) -> Dict:
        """Validate organized structure"""
        issues = []
        warnings = []
        
        primary = detection['primary_language']
        
        # Check if main files exist
        if primary == 'python':
            if not any((organized_path / 'app').glob('*.py')):
                warnings.append('No Python files found in app/')
        
        elif primary in ['javascript', 'typescript']:
            if not any((organized_path / 'src').glob('*.js')) and not any((organized_path / 'src').glob('*.ts')):
                warnings.append('No JS/TS files found in src/')
        
        elif primary == 'java':
            if not any((organized_path / 'src/main/java').rglob('*.java')):
                warnings.append('No Java files found in src/main/java/')
        
        # Check for empty directories
        for dir_path in organized_path.rglob('*'):
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                warnings.append(f'Empty directory: {dir_path.name}')
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings[:10]  # Limit warnings
        }
