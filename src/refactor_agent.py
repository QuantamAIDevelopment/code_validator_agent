"""Intelligent Code Refactor Agent - Fixes imports after file reorganization"""
import ast
import re
import os
from pathlib import Path
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

class ImportFixer:
    """Fixes broken imports after file reorganization"""
    
    def __init__(self):
        self.file_moves = {}  # old_path -> new_path mapping
        self.import_fixes = []
    
    def register_move(self, old_path: str, new_path: str):
        """Register a file move for import fixing"""
        self.file_moves[old_path] = new_path
    
    def fix_python_imports(self, file_path: Path, old_location: Path, new_location: Path) -> bool:
        """Fix Python imports in a moved file"""
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)
            modified = False
            lines = content.split('\n')
            
            for node in ast.walk(tree):
                # Handle 'from X import Y'
                if isinstance(node, ast.ImportFrom):
                    if node.module:
                        old_import = node.module
                        new_import = self._calculate_new_import(old_import, old_location, new_location)
                        if new_import != old_import:
                            lines[node.lineno - 1] = lines[node.lineno - 1].replace(
                                f"from {old_import}", f"from {new_import}"
                            )
                            modified = True
                            self.import_fixes.append({
                                'file': str(file_path),
                                'line': node.lineno,
                                'old': old_import,
                                'new': new_import
                            })
            
            if modified:
                file_path.write_text('\n'.join(lines), encoding='utf-8')
                logger.info(f"Fixed imports in {file_path}")
                return True
            return False
            
        except Exception as e:
            logger.warning(f"Could not fix imports in {file_path}: {e}")
            return False
    
    def fix_js_imports(self, file_path: Path, old_location: Path, new_location: Path) -> bool:
        """Fix JavaScript/TypeScript imports"""
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            modified = False
            
            # Match: import X from 'path' or require('path')
            import_pattern = r"(import\s+.*?\s+from\s+['\"]|require\(['\"])([^'\"]+)(['\"])"
            
            for i, line in enumerate(lines):
                matches = re.finditer(import_pattern, line)
                for match in matches:
                    old_path = match.group(2)
                    if old_path.startswith('.'):  # Relative import
                        new_path = self._calculate_relative_path(old_path, old_location, new_location)
                        if new_path != old_path:
                            lines[i] = lines[i].replace(old_path, new_path)
                            modified = True
                            self.import_fixes.append({
                                'file': str(file_path),
                                'line': i + 1,
                                'old': old_path,
                                'new': new_path
                            })
            
            if modified:
                file_path.write_text('\n'.join(lines), encoding='utf-8')
                logger.info(f"Fixed imports in {file_path}")
                return True
            return False
            
        except Exception as e:
            logger.warning(f"Could not fix imports in {file_path}: {e}")
            return False
    
    def _calculate_new_import(self, old_import: str, old_loc: Path, new_loc: Path) -> str:
        """Calculate new import path for Python"""
        # Convert relative imports based on new location
        if old_import.startswith('.'):
            depth = len(old_import) - len(old_import.lstrip('.'))
            module = old_import.lstrip('.')
            
            # Calculate new relative path
            old_parts = old_loc.parts
            new_parts = new_loc.parts
            
            # Find common ancestor
            common = 0
            for i, (o, n) in enumerate(zip(old_parts, new_parts)):
                if o == n:
                    common = i + 1
                else:
                    break
            
            # Adjust depth based on new location
            new_depth = len(new_parts) - common
            return '.' * max(1, new_depth) + module
        
        return old_import
    
    def _calculate_relative_path(self, old_path: str, old_loc: Path, new_loc: Path) -> str:
        """Calculate new relative path for JS/TS"""
        if not old_path.startswith('.'):
            return old_path
        
        # Count '../' in old path
        up_count = old_path.count('../')
        remainder = old_path.replace('../', '').replace('./', '')
        
        # Calculate new depth
        old_depth = len(old_loc.parts)
        new_depth = len(new_loc.parts)
        depth_diff = new_depth - old_depth
        
        new_up_count = max(0, up_count + depth_diff)
        return '../' * new_up_count + remainder


class ConfigUpdater:
    """Updates config files after reorganization"""
    
    def __init__(self):
        self.updates = []
    
    def update_package_json(self, file_path: Path, moves: Dict[str, str]) -> bool:
        """Update paths in package.json"""
        try:
            import json
            content = json.loads(file_path.read_text())
            modified = False
            
            # Update main/entry points
            for key in ['main', 'module', 'types']:
                if key in content and content[key] in moves:
                    old_val = content[key]
                    content[key] = moves[old_val]
                    modified = True
                    self.updates.append(f"Updated {key}: {old_val} -> {content[key]}")
            
            if modified:
                file_path.write_text(json.dumps(content, indent=2))
                logger.info(f"Updated {file_path}")
            return modified
            
        except Exception as e:
            logger.warning(f"Could not update {file_path}: {e}")
            return False
    
    def update_setup_py(self, file_path: Path, moves: Dict[str, str]) -> bool:
        """Update paths in setup.py"""
        try:
            content = file_path.read_text()
            modified = False
            
            for old_path, new_path in moves.items():
                if old_path in content:
                    content = content.replace(old_path, new_path)
                    modified = True
                    self.updates.append(f"Updated setup.py: {old_path} -> {new_path}")
            
            if modified:
                file_path.write_text(content)
                logger.info(f"Updated {file_path}")
            return modified
            
        except Exception as e:
            logger.warning(f"Could not update {file_path}: {e}")
            return False


class RefactorAgent:
    """Main refactor agent coordinating all operations"""
    
    def __init__(self):
        self.import_fixer = ImportFixer()
        self.config_updater = ConfigUpdater()
        self.move_log = []
        self.warnings = []
    
    def refactor_project(self, source: Path, organized: Path, file_moves: List[Dict]) -> Dict:
        """Refactor project with import fixing"""
        logger.info("Starting intelligent refactoring...")
        
        # Register all moves
        for move in file_moves:
            self.import_fixer.register_move(move['original'], move['organized'])
            self.move_log.append(move)
        
        # Fix imports in moved files
        python_fixed = 0
        js_fixed = 0
        
        for move in file_moves:
            new_path = Path(move['organized'])
            if not new_path.exists():
                continue
            
            old_loc = Path(move['original']).parent
            new_loc = new_path.parent
            
            if new_path.suffix == '.py':
                if self.import_fixer.fix_python_imports(new_path, old_loc, new_loc):
                    python_fixed += 1
            elif new_path.suffix in ['.js', '.jsx', '.ts', '.tsx']:
                if self.import_fixer.fix_js_imports(new_path, old_loc, new_loc):
                    js_fixed += 1
        
        # Update config files
        config_updated = 0
        for config_file in organized.rglob('package.json'):
            if self.config_updater.update_package_json(config_file, 
                {m['original']: m['organized'] for m in file_moves}):
                config_updated += 1
        
        for config_file in organized.rglob('setup.py'):
            if self.config_updater.update_setup_py(config_file,
                {m['original']: m['organized'] for m in file_moves}):
                config_updated += 1
        
        return {
            'files_moved': len(file_moves),
            'python_imports_fixed': python_fixed,
            'js_imports_fixed': js_fixed,
            'config_files_updated': config_updated,
            'import_fixes': self.import_fixer.import_fixes[:50],
            'config_updates': self.config_updater.updates[:20],
            'warnings': self.warnings
        }
