"""Bugs & issues detection"""
import ast
import os
import re
from pathlib import Path

class Analyzer:
    def __init__(self, force_rescan=True):
        self.force_rescan = force_rescan
        self._file_cache = {}  # Track file mtimes
    
    def clear_cache(self):
        """Clear file modification time cache"""
        self._file_cache.clear()
    
    def analyze(self, file_path):
        """Detect bugs and issues"""
        issues = []
        
        try:
            # Always read fresh content when force_rescan is True
            if self.force_rescan:
                # Clear cache entry for this file to force fresh read
                self._file_cache.pop(str(file_path), None)
                
            # Check modification time for cache invalidation
            current_mtime = os.path.getmtime(file_path)
            cached_mtime = self._file_cache.get(str(file_path))
            
            # Force re-analysis if file was modified or force_rescan is True
            if self.force_rescan or cached_mtime is None or cached_mtime != current_mtime:
                self._file_cache[str(file_path)] = current_mtime
                
                # Read with minimal buffering for fresh content
                with open(file_path, 'r', encoding='utf-8', errors='ignore', buffering=1) as f:
                    content = f.read()
            else:
                # Use cached result (for production optimization)
                return []
                
        except Exception as e:
            return [{'type': 'FileError', 'message': str(e), 'line': 0}]
        
        # Analyze based on file type
        try:
            if file_path.suffix == '.py':
                issues.extend(self._analyze_python(file_path, content))
            elif file_path.suffix in ['.js', '.jsx', '.ts', '.tsx']:
                issues.extend(self._analyze_javascript(file_path, content))
            elif file_path.suffix in ['.html', '.htm']:
                issues.extend(self._analyze_html(file_path, content))
            elif file_path.suffix in ['.css', '.scss', '.sass']:
                issues.extend(self._analyze_css(file_path, content))
        except Exception as e:
            issues.append({'type': 'AnalysisError', 'message': f'Failed to analyze: {str(e)}', 'line': 0})
        
        return issues
    
    def _analyze_python(self, file_path, content):
        """Analyze Python code for common bugs and issues"""
        issues = []
        lines = content.split('\n')
        
        # Syntax check
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            issues.append({
                'type': 'SyntaxError',
                'message': str(e),
                'line': e.lineno or 0
            })
            return issues
        
        # AST-based analysis
        issues.extend(self._analyze_ast(tree))
        
        # Pattern-based detection
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Security issues
            if 'eval(' in line:
                issues.append({'type': 'SecurityIssue', 'message': 'Avoid using eval() - security risk', 'line': i})
            
            if 'exec(' in line:
                issues.append({'type': 'SecurityIssue', 'message': 'Avoid using exec() - security risk', 'line': i})
            
            if 'pickle.loads(' in line or 'pickle.load(' in line:
                issues.append({'type': 'SecurityIssue', 'message': 'Pickle can execute arbitrary code - use json instead', 'line': i})
            
            if 'shell=True' in line:
                issues.append({'type': 'SecurityIssue', 'message': 'shell=True is a security risk - avoid if possible', 'line': i})
            
            # Code quality issues
            if '== None' in line and 'is None' not in line:
                issues.append({'type': 'ComparisonBug', 'message': "Use 'is None' instead of '== None'", 'line': i})
            
            if '!= None' in line and 'is not None' not in line:
                issues.append({'type': 'ComparisonBug', 'message': "Use 'is not None' instead of '!= None'", 'line': i})
            
            if stripped == 'except:':
                issues.append({'type': 'BareExcept', 'message': 'Bare except clause - specify exception type', 'line': i})
            
            if 'def ' in stripped and '=[]' in line.replace(' ', ''):
                issues.append({'type': 'MutableDefault', 'message': 'Mutable default argument [] - use None instead', 'line': i})
            
            if 'def ' in stripped and '={}' in line.replace(' ', ''):
                issues.append({'type': 'MutableDefault', 'message': 'Mutable default argument {} - use None instead', 'line': i})
            
            if 'type(' in line and ') ==' in line and 'isinstance' not in line:
                issues.append({'type': 'TypeCheckBug', 'message': 'Use isinstance() instead of type() ==', 'line': i})
            
            # Common bugs
            if re.search(r'\bif\s+\w+\s*=\s*', line):
                issues.append({'type': 'AssignmentInCondition', 'message': 'Assignment in condition - did you mean == ?', 'line': i})
            
            if 'import *' in line:
                issues.append({'type': 'ImportIssue', 'message': 'Avoid wildcard imports - import specific names', 'line': i})
            
            # Performance issues
            if '+=' in line and 'str' in line.lower() and 'for ' in content[max(0, content.find(line)-100):content.find(line)]:
                issues.append({'type': 'PerformanceIssue', 'message': 'String concatenation in loop - use join() instead', 'line': i})
            
            # Trailing whitespace
            if line and (line.endswith(' ') or line.endswith('\t')):
                issues.append({'type': 'StyleIssue', 'message': 'Trailing whitespace', 'line': i})
        
        return issues
    
    def _analyze_ast(self, tree):
        """AST-based analysis for deeper code inspection"""
        issues = []
        
        for node in ast.walk(tree):
            # Detect unused variables
            if isinstance(node, ast.FunctionDef):
                # Check for empty functions
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    issues.append({
                        'type': 'EmptyFunction',
                        'message': f'Empty function: {node.name}',
                        'line': node.lineno
                    })
            
            # Detect duplicate exception handlers
            if isinstance(node, ast.Try):
                exception_types = []
                for handler in node.handlers:
                    if handler.type:
                        exc_name = ast.unparse(handler.type) if hasattr(ast, 'unparse') else str(handler.type)
                        if exc_name in exception_types:
                            issues.append({
                                'type': 'DuplicateException',
                                'message': f'Duplicate exception handler: {exc_name}',
                                'line': handler.lineno
                            })
                        exception_types.append(exc_name)
            
            # Detect comparison with True/False
            if isinstance(node, ast.Compare):
                for op, comparator in zip(node.ops, node.comparators):
                    if isinstance(op, ast.Eq) and isinstance(comparator, ast.Constant):
                        if comparator.value is True or comparator.value is False:
                            issues.append({
                                'type': 'ComparisonBug',
                                'message': f'Comparing with {comparator.value} - use "is" instead',
                                'line': node.lineno
                            })
        
        return issues
    
    def _analyze_javascript(self, file_path, content):
        """Analyze JavaScript/TypeScript code"""
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Security issues
            if 'eval(' in line:
                issues.append({'type': 'SecurityIssue', 'message': 'Avoid eval() - security risk', 'line': i})
            
            if 'innerHTML' in line and '=' in line:
                issues.append({'type': 'SecurityIssue', 'message': 'innerHTML can cause XSS - use textContent', 'line': i})
            
            # Common bugs
            if '==' in line and '===' not in line and '!=' not in line:
                issues.append({'type': 'ComparisonBug', 'message': 'Use === instead of ==', 'line': i})
            
            if '!=' in line and '!==' not in line:
                issues.append({'type': 'ComparisonBug', 'message': 'Use !== instead of !=', 'line': i})
            
            if 'var ' in line:
                issues.append({'type': 'StyleIssue', 'message': 'Use let or const instead of var', 'line': i})
            
            # Console statements
            if 'console.log(' in line:
                issues.append({'type': 'CodeQuality', 'message': 'Remove console.log in production', 'line': i})
            
            if line and (line.endswith(' ') or line.endswith('\t')):
                issues.append({'type': 'StyleIssue', 'message': 'Trailing whitespace', 'line': i})
        
        return issues
    
    def _analyze_html(self, file_path, content):
        """Analyze HTML code"""
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Missing alt attributes
            if '<img' in line and 'alt=' not in line:
                issues.append({'type': 'Accessibility', 'message': 'Image missing alt attribute', 'line': i})
            
            # Inline styles
            if 'style=' in line and '<style' not in line:
                issues.append({'type': 'CodeQuality', 'message': 'Avoid inline styles - use CSS', 'line': i})
            
            # Deprecated tags
            if '<font' in line or '<center' in line:
                issues.append({'type': 'DeprecatedCode', 'message': 'Deprecated HTML tag - use CSS', 'line': i})
            
            if line and (line.endswith(' ') or line.endswith('\t')):
                issues.append({'type': 'StyleIssue', 'message': 'Trailing whitespace', 'line': i})
        
        return issues
    
    def _analyze_css(self, file_path, content):
        """Analyze CSS code"""
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # !important overuse
            if '!important' in line:
                issues.append({'type': 'CodeQuality', 'message': 'Avoid !important - refactor specificity', 'line': i})
            
            # Color format consistency
            if re.search(r'#[0-9a-fA-F]{3}\b', line):
                issues.append({'type': 'StyleIssue', 'message': 'Use 6-digit hex colors for consistency', 'line': i})
            
            if line and (line.endswith(' ') or line.endswith('\t')):
                issues.append({'type': 'StyleIssue', 'message': 'Trailing whitespace', 'line': i})
        
        return issues