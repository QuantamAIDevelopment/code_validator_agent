"""Bugs & issues detection"""
import ast
import os
import re
from pathlib import Path

class Analyzer:
    def __init__(self, force_rescan=True):
        self.force_rescan = force_rescan
    
    def analyze(self, file_path):
        """Detect bugs and issues"""
        issues = []
        
        try:
            # Always read fresh content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
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
        except IndentationError as e:
            issues.append({
                'type': 'IndentationError',
                'message': f'Indentation error: {e.msg}',
                'line': e.lineno or 0
            })
            return issues
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
            
            # Skip commented lines and TODO comments
            if stripped.startswith('#'):
                continue
            
            # Security issues
            if 'eval(' in line:
                issues.append({'type': 'SecurityIssue', 'message': 'Avoid using eval() - security risk', 'line': i})
            
            if 'exec(' in line:
                issues.append({'type': 'SecurityIssue', 'message': 'Avoid using exec() - security risk', 'line': i})
            
            if 'pickle.loads(' in line or 'pickle.load(' in line:
                issues.append({'type': 'SecurityIssue', 'message': 'Pickle can execute arbitrary code - use json instead', 'line': i})
            
            if 'shell=True' in line:
                issues.append({'type': 'SecurityIssue', 'message': 'shell=True is a security risk - avoid if possible', 'line': i})
            
            # Backend-specific issues
            if 'password' in line.lower() and ('print(' in line or 'log' in line.lower()):
                issues.append({'type': 'SecurityIssue', 'message': 'Potential password logging detected', 'line': i})
            
            if 'api_key' in line.lower() and ('=' in line and '"' in line):
                issues.append({'type': 'SecurityIssue', 'message': 'Hardcoded API key detected', 'line': i})
            
            if 'TODO' in line or 'FIXME' in line or 'HACK' in line:
                issues.append({'type': 'CodeQuality', 'message': 'TODO/FIXME comment found - needs implementation', 'line': i})
            
            if '.execute(' in line and 'f"' in line:
                issues.append({'type': 'SecurityIssue', 'message': 'SQL injection risk - use parameterized queries', 'line': i})
            
            if '.execute(' in line and '%' in line and 'format' not in line:
                issues.append({'type': 'SecurityIssue', 'message': 'SQL injection risk - use parameterized queries', 'line': i})
            
            if 'requests.get(' in line and 'verify=False' in line:
                issues.append({'type': 'SecurityIssue', 'message': 'SSL verification disabled - security risk', 'line': i})
            
            if 'sleep(' in line and not stripped.startswith('#'):
                issues.append({'type': 'PerformanceIssue', 'message': 'sleep() call may block - consider async approach', 'line': i})
            
            # Database issues
            if 'cursor.execute' in line and 'commit' not in content[max(0, content.find(line)):min(len(content), content.find(line)+500)]:
                issues.append({'type': 'DatabaseIssue', 'message': 'Missing commit() after execute() - transaction may not persist', 'line': i})
            
            if '.close()' not in content and ('connect(' in line or 'Connection(' in line):
                issues.append({'type': 'ResourceLeak', 'message': 'Database connection not closed - use context manager', 'line': i})
            
            if 'open(' in line and '.close()' not in content[max(0, content.find(line)):min(len(content), content.find(line)+300)]:
                issues.append({'type': 'ResourceLeak', 'message': 'File not closed - use "with" statement', 'line': i})
            
            # API issues
            if '@app.route' in line or '@router' in line:
                if 'methods=' not in line and 'get' not in line.lower() and 'post' not in line.lower():
                    issues.append({'type': 'APIIssue', 'message': 'HTTP method not specified for route', 'line': i})
            
            if 'return ' in stripped and 'jsonify' not in line and '@app' in content[:content.find(line)]:
                if 'dict' in line or '{' in line:
                    issues.append({'type': 'APIIssue', 'message': 'Return dict without jsonify() in Flask route', 'line': i})
            
            # Error handling
            if 'try:' in stripped:
                try_block = content[content.find(line):]
                if 'except Exception:' in try_block[:500] and 'pass' in try_block[:500]:
                    issues.append({'type': 'ErrorHandling', 'message': 'Empty exception handler - errors silently ignored', 'line': i})
            
            if 'raise Exception(' in line:
                issues.append({'type': 'ErrorHandling', 'message': 'Generic Exception raised - use specific exception type', 'line': i})
            
            # Code quality issues
            if '== None' in line and 'is None' not in line and '# ' not in stripped:
                issues.append({'type': 'ComparisonBug', 'message': "Use 'is None' instead of '== None'", 'line': i})
            
            if '!= None' in line and 'is not None' not in line and '# ' not in stripped:
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
            if re.search(r'\bif\s+\w+\s*=\s*[^=]', line) and ':=' not in line:
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
            
            # Skip commented lines
            if stripped.startswith('//'):
                continue
            
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
            stripped = line.strip()
            
            # Skip commented lines
            if stripped.startswith('<!--'):
                continue
            
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