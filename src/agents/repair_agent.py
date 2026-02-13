"""Repair Agent - Comprehensive codebase repair specialist"""
import os
import subprocess
from pathlib import Path
from typing import Dict, List

class RepairAgent:
    def __init__(self):
        self.repair_prompt = """You are a Senior Principal Software Engineer and Codebase Repair Specialist.

You are given a complete extracted project from a ZIP file or a private repository.

Your task is to fully repair the entire project.

STRICT RULES:
1. Do NOT explain anything.
2. Do NOT summarize.
3. Do NOT describe what you changed.
4. ONLY return the fully corrected code.
5. If multiple files exist, return them in this format:

### filename.ext
<code>

### folder/another_file.ext
<code>

6. Preserve original project structure.
7. Do NOT remove working functionality.
8. Fix ALL detected issues.

-----------------------------------

PROJECT STRUCTURE:
{project_tree}

-----------------------------------

PACKAGE / DEPENDENCY FILES:
{package_json_or_requirements}

-----------------------------------

DATABASE CONFIG (if any):
{db_config}

-----------------------------------

DETECTED ERRORS:
Lint Errors:
{lint_errors}

Dependency Errors:
{dependency_errors}

Import Errors:
{import_errors}

Build Errors:
{build_errors}

Runtime Errors:
{runtime_errors}

Database Errors:
{db_errors}

-----------------------------------

PROJECT CODE:
{full_project_code}

-----------------------------------

TASK:
1. Resolve all dependency issues.
2. Fix missing or incorrect imports.
3. Ensure successful build/compilation.
4. Fix runtime crashes.
5. Correct database configuration problems.
6. Ensure the project runs successfully.
7. Maintain clean, production-level structure.
8. If necessary, refactor code safely to eliminate systemic issues.

Before returning:
- Re-check syntax.
- Re-check imports.
- Re-check dependencies.
- Re-check runtime logic.
- Re-check database connectivity.
- Ensure no unresolved errors remain.

Return ONLY the corrected full project."""
    
    def analyze_and_repair(self, project_path: Path) -> Dict:
        """Analyze project and detect all errors"""
        
        # Collect project data
        project_tree = self._generate_tree(project_path)
        package_files = self._get_package_files(project_path)
        db_config = self._get_db_config(project_path)
        full_code = self._get_all_code(project_path)
        
        # Detect errors
        lint_errors = self._detect_lint_errors(project_path)
        dependency_errors = self._detect_dependency_errors(project_path)
        import_errors = self._detect_import_errors(project_path)
        build_errors = self._detect_build_errors(project_path)
        runtime_errors = self._detect_runtime_errors(project_path)
        db_errors = self._detect_db_errors(project_path)
        
        return {
            'project_tree': project_tree,
            'package_files': package_files,
            'db_config': db_config,
            'full_code': full_code,
            'errors': {
                'lint': lint_errors,
                'dependency': dependency_errors,
                'import': import_errors,
                'build': build_errors,
                'runtime': runtime_errors,
                'database': db_errors
            },
            'has_errors': any([lint_errors, dependency_errors, import_errors, 
                              build_errors, runtime_errors, db_errors])
        }
    
    def _generate_tree(self, path: Path, prefix: str = '', max_depth: int = 4, depth: int = 0) -> str:
        """Generate project tree"""
        if depth >= max_depth:
            return ''
        
        tree = []
        try:
            items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))[:50]
            for i, item in enumerate(items):
                if item.name.startswith('.') or item.name in ['node_modules', '__pycache__', 'venv']:
                    continue
                is_last = i == len(items) - 1
                tree.append(f"{prefix}{'`-- ' if is_last else '|-- '}{item.name}{'/' if item.is_dir() else ''}")
                if item.is_dir() and depth < max_depth - 1:
                    tree.append(self._generate_tree(item, prefix + ('    ' if is_last else '|   '), max_depth, depth + 1))
        except:
            pass
        return '\n'.join(filter(None, tree))
    
    def _get_package_files(self, path: Path) -> str:
        """Get package/dependency files"""
        files = []
        for name in ['requirements.txt', 'package.json', 'pom.xml', 'build.gradle', 'composer.json', 'Gemfile']:
            file_path = path / name
            if file_path.exists():
                try:
                    files.append(f"### {name}\n{file_path.read_text()}")
                except:
                    pass
        return '\n\n'.join(files) if files else 'None'
    
    def _get_db_config(self, path: Path) -> str:
        """Get database configuration"""
        configs = []
        for file_path in path.rglob('*'):
            if file_path.name in ['.env', 'database.py', 'db.py', 'config.py', 'settings.py']:
                try:
                    content = file_path.read_text()
                    if 'DATABASE' in content or 'DB_' in content or 'database' in content.lower():
                        configs.append(f"### {file_path.name}\n{content[:500]}")
                except:
                    pass
        return '\n\n'.join(configs) if configs else 'None'
    
    def _get_all_code(self, path: Path) -> str:
        """Get all project code"""
        code_files = []
        extensions = ['.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cs', '.php', '.rb', '.go']
        
        for file_path in path.rglob('*'):
            if file_path.suffix in extensions and file_path.is_file():
                if any(x in file_path.parts for x in ['node_modules', '__pycache__', 'venv', '.git']):
                    continue
                try:
                    relative = file_path.relative_to(path)
                    content = file_path.read_text()
                    code_files.append(f"### {relative}\n{content}")
                except:
                    pass
                if len(code_files) >= 50:  # Limit files
                    break
        
        return '\n\n'.join(code_files) if code_files else 'No code files found'
    
    def _detect_lint_errors(self, path: Path) -> str:
        """Detect linting errors"""
        errors = []
        for file_path in path.rglob('*.py'):
            try:
                result = subprocess.run(['python', '-m', 'py_compile', str(file_path)], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode != 0:
                    errors.append(f"{file_path.name}: {result.stderr[:200]}")
            except:
                pass
        return '\n'.join(errors[:10]) if errors else 'None detected'
    
    def _detect_dependency_errors(self, path: Path) -> str:
        """Detect dependency errors"""
        errors = []
        req_file = path / 'requirements.txt'
        if req_file.exists():
            try:
                content = req_file.read_text()
                if '==' not in content and '>=' not in content:
                    errors.append('requirements.txt: No version pinning')
            except:
                pass
        return '\n'.join(errors) if errors else 'None detected'
    
    def _detect_import_errors(self, path: Path) -> str:
        """Detect import errors"""
        errors = []
        for file_path in path.rglob('*.py'):
            try:
                content = file_path.read_text()
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if line.strip().startswith('from ') or line.strip().startswith('import '):
                        if 'ModuleNotFoundError' in line or 'ImportError' in line:
                            errors.append(f"{file_path.name}:{i}: {line.strip()}")
            except:
                pass
        return '\n'.join(errors[:10]) if errors else 'None detected'
    
    def _detect_build_errors(self, path: Path) -> str:
        """Detect build errors"""
        return 'Build check skipped (requires environment)'
    
    def _detect_runtime_errors(self, path: Path) -> str:
        """Detect runtime errors"""
        errors = []
        for file_path in path.rglob('*.py'):
            try:
                content = file_path.read_text()
                if 'DATABASE_URL = None' in content:
                    errors.append(f"{file_path.name}: DATABASE_URL is None")
                if 'raise HTTPException' in content and 'if' not in content[:content.find('raise HTTPException')]:
                    errors.append(f"{file_path.name}: Unindented raise statement")
            except:
                pass
        return '\n'.join(errors[:10]) if errors else 'None detected'
    
    def _detect_db_errors(self, path: Path) -> str:
        """Detect database errors"""
        errors = []
        for file_path in path.rglob('*.py'):
            try:
                content = file_path.read_text()
                if 'create_engine' in content and 'DATABASE_URL = None' in content:
                    errors.append(f"{file_path.name}: DATABASE_URL not configured")
            except:
                pass
        return '\n'.join(errors) if errors else 'None detected'
