"""AI-based auto fixer"""
import os
import re
import logging
from openai import OpenAI
from dotenv import load_dotenv

# Disable httpx and openai logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

load_dotenv()

class Fixer:
    def __init__(self):
        # Support both OpenAI and Groq with fallback
        self.groq_key = os.getenv('GROQ_API_KEY')
        self.openai_key = os.getenv('OPENAI_API_KEY')
        
        self.groq_client = None
        self.openai_client = None
        
        if self.groq_key:
            self.groq_client = OpenAI(api_key=self.groq_key, base_url="https://api.groq.com/openai/v1")
        
        if self.openai_key:
            self.openai_client = OpenAI(api_key=self.openai_key)
    
    def fix(self, file_path, content, issues):
        """Fix detected issues using pattern-based fixes and AI for complex issues"""
        if not issues:
            return content
        
        # Separate simple and complex issues
        simple_issues = [i for i in issues if i['type'] not in ['LongFunction', 'MissingLogging', 'MissingErrorHandling']]
        complex_issues = [i for i in issues if i['type'] in ['LongFunction', 'MissingLogging', 'MissingErrorHandling']]
        
        # Apply pattern fixes for simple issues
        fixed_content = self._pattern_based_fix(content, simple_issues)
        
        # Apply AI fixes for complex issues if available
        if complex_issues and (self.groq_client or self.openai_client):
            fixed_content = self._ai_refactor(file_path, fixed_content, complex_issues)
        else:
            # Fallback: Add basic improvements
            if str(file_path).endswith('.py'):
                fixed_content = self._add_quality_improvements(fixed_content, file_path)
        
        return fixed_content
    
    def _ai_refactor(self, file_path, content, issues):
        """Use AI to refactor complex issues"""
        try:
            # Use Groq (faster) or OpenAI
            if self.groq_client:
                return self._ai_fix_with_client(content, issues, self.groq_client, 'llama-3.3-70b-versatile')
            elif self.openai_client:
                return self._ai_fix_with_client(content, issues, self.openai_client, 'gpt-4o-mini')
        except Exception as e:
            logging.warning(f"AI refactoring failed: {e}")
            return content
        return content
    
    def _pattern_based_fix(self, content, issues):
        """Apply pattern-based fixes for ALL issue types"""
        lines = content.split('\n')
        modified = False
        
        # Add missing imports at top if needed
        needs_logging = any('logging' in i.get('message', '').lower() for i in issues)
        if needs_logging and 'import logging' not in content:
            lines.insert(0, 'import logging\n')
            modified = True
        
        for issue in issues:
            line_num = issue.get('line', 0)
            if line_num < 1 or line_num > len(lines):
                continue
            
            line = lines[line_num - 1]
            original_line = line
            issue_type = issue.get('type', '')
            indent = len(line) - len(line.lstrip())
            stripped = line.strip()
            
            # Fix comparison bugs
            if issue_type == 'ComparisonBug':
                if '== None' in line and 'is None' not in line:
                    line = line.replace('== None', 'is None')
                elif '!= None' in line and 'is not None' not in line:
                    line = line.replace('!= None', 'is not None')
                elif '== True' in line and 'is True' not in line:
                    line = line.replace('== True', 'is True')
                elif '== False' in line and 'is False' not in line:
                    line = line.replace('== False', 'is False')
                elif '==' in line and '===' not in line and 'is' not in line:
                    line = line.replace('==', '===', 1)
                elif '!=' in line and '!==' not in line and 'is not' not in line:
                    line = line.replace('!=', '!==', 1)
            
            elif issue_type == 'BareExcept':
                line = line.replace('except:', 'except Exception:')
            
            elif issue_type == 'MutableDefault':
                line = re.sub(r'=\s*\[\s*\]', '=None', line)
                line = re.sub(r'=\s*\{\s*\}', '=None', line)
            
            elif issue_type == 'TypeCheckBug':
                match = re.search(r'type\(([^)]+)\)\s*==\s*([\w.]+)', line)
                if match:
                    line = line.replace(match.group(0), f'isinstance({match.group(1)}, {match.group(2)})')
            
            elif issue_type == 'ImportIssue':
                if 'import *' in line:
                    # Try to replace with specific imports (common cases)
                    if 'from flask import *' in line:
                        line = ' ' * indent + 'from flask import Flask, request, jsonify, render_template'
                    elif 'from django' in line:
                        line = ' ' * indent + '# ' + stripped + '  # TODO: Import specific items'
                    else:
                        line = ' ' * indent + '# ' + stripped + '  # TODO: Replace wildcard import'
            
            elif issue_type == 'SecurityIssue':
                if 'eval(' in line:
                    line = ' ' * indent + '# ' + stripped + '  # SECURITY: Use ast.literal_eval()'
                elif 'exec(' in line:
                    line = ' ' * indent + '# ' + stripped + '  # SECURITY: Refactor'
                elif 'innerHTML' in line:
                    line = line.replace('innerHTML', 'textContent')
                elif 'shell=True' in line:
                    line = line.replace('shell=True', 'shell=False')
                elif 'pickle.load' in line:
                    line = ' ' * indent + '# ' + stripped + '  # SECURITY: Use json'
                elif 'verify=False' in line:
                    line = line.replace('verify=False', 'verify=True')
                elif 'SQL injection' in issue.get('message', ''):
                    line = ' ' * indent + '# ' + stripped + '  # SECURITY: Use parameterized queries'
                elif 'password' in line.lower() and 'log' in line.lower():
                    line = ' ' * indent + '# ' + stripped + '  # SECURITY: Remove password logging'
                elif 'api_key' in line.lower():
                    line = ' ' * indent + '# ' + stripped + '  # SECURITY: Move to environment variable'
            
            elif issue_type == 'CodeQuality':
                if 'console.log(' in line:
                    line = ' ' * indent + '// ' + stripped
                elif '!important' in line:
                    line = line.replace('!important', '')
                elif 'TODO' in line or 'FIXME' in line:
                    pass  # Keep TODO comments as-is
            
            elif issue_type == 'DeprecatedCode':
                if 'var ' in line:
                    line = line.replace('var ', 'let ')
                elif '<font' in line or '<center' in line:
                    line = '<!-- ' + stripped + ' -->'
            
            elif issue_type == 'Accessibility':
                if '<img' in line and 'alt=' not in line:
                    line = line.replace('<img', '<img alt=""')
            
            elif issue_type == 'StyleIssue':
                line = line.rstrip()
            
            elif issue_type == 'AssignmentInCondition':
                if ':=' not in line:
                    match = re.search(r'(if\s+\w+)\s*=\s*([^=])', line)
                    if match:
                        line = line.replace(f'{match.group(1)} =', f'{match.group(1)} ==', 1)
            
            elif issue_type == 'EmptyFunction':
                if 'pass' in line:
                    line = ' ' * indent + 'raise NotImplementedError()'
            
            elif issue_type == 'PerformanceIssue':
                if 'sleep(' in line:
                    line = ' ' * indent + '# ' + stripped + '  # TODO: Use async/await'
                else:
                    line = ' ' * indent + '# ' + stripped + '  # TODO: Use join()'
            
            elif issue_type == 'DuplicateException':
                line = ' ' * indent + '# ' + stripped + '  # Duplicate'
            
            elif issue_type == 'ResourceLeak':
                if 'open(' in line and 'with' not in line:
                    # Convert to with statement
                    match = re.search(r'(\w+)\s*=\s*open\(([^)]+)\)', line)
                    if match:
                        var_name = match.group(1)
                        file_args = match.group(2)
                        line = ' ' * indent + f'with open({file_args}) as {var_name}:'
                elif 'connect(' in line or 'Connection(' in line:
                    line = ' ' * indent + '# ' + stripped + '  # TODO: Use context manager or close()'
            
            elif issue_type == 'DatabaseIssue':
                if 'execute' in line:
                    # Add commit on next line
                    lines.insert(line_num, ' ' * indent + 'conn.commit()  # Auto-added')
                    modified = True
            
            elif issue_type == 'APIIssue':
                if 'methods=' not in line and '@app.route' in line:
                    # Add methods parameter to route
                    if '(' in line and ')' in line:
                        line = line.replace(')', ', methods=["GET", "POST"])')
                elif 'return ' in stripped and 'jsonify' not in line and 'dict' in issue.get('message', ''):
                    # Wrap return dict with jsonify
                    match = re.search(r'return\s+({[^}]+})', line)
                    if match:
                        line = line.replace(match.group(0), f'return jsonify({match.group(1)})')
                        # Add import if not present
                        if 'from flask import' not in content:
                            lines.insert(0, 'from flask import jsonify')
            
            elif issue_type == 'ErrorHandling':
                if 'raise Exception(' in line:
                    line = line.replace('raise Exception(', 'raise ValueError(')
                elif 'pass' in line:
                    line = ' ' * indent + 'logger.error("Error occurred")  # TODO: Handle error properly'
            
            elif issue_type == 'MissingLogging':
                # Add logger at start of file
                if 'import logging' not in '\n'.join(lines[:20]):
                    lines.insert(0, 'import logging\n')
                    lines.insert(1, 'logger = logging.getLogger(__name__)\n')
                    modified = True
            
            elif issue_type == 'MissingErrorHandling':
                # Add try-except wrapper hint
                lines.insert(line_num, ' ' * indent + '# TODO: Add try-except error handling')
                modified = True
            
            elif issue_type == 'LongFunction':
                # Add refactoring hint
                lines.insert(line_num, ' ' * indent + '# TODO: Refactor - function too long, split into smaller functions')
                modified = True
            
            if line != original_line:
                lines[line_num - 1] = line
                modified = True
        
        return '\n'.join(lines)
    
    def _add_quality_improvements(self, content, file_path):
        """Add quality improvements: logging, comments, error handling"""
        lines = content.split('\n')
        
        # 1. Add logging import if not present
        has_logging = 'import logging' in content or 'from logging import' in content
        if not has_logging and len(lines) > 10:
            import_idx = 0
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    import_idx = i + 1
                    break
            lines.insert(import_idx, 'import logging')
            lines.insert(import_idx + 1, '')
        
        # 2. Add file-level docstring if missing
        if len(lines) > 3 and not lines[0].strip().startswith('"""'):
            lines.insert(0, f'"""Module: {file_path.name} - Auto-generated documentation"""')
            lines.insert(1, '')
        
        # 3. Add function docstrings and inline comments
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Add docstring to functions
            if stripped.startswith('def ') and ':' in line:
                if i + 1 < len(lines) and not lines[i + 1].strip().startswith('"""'):
                    indent = len(line) - len(line.lstrip()) + 4
                    func_name = stripped.split('(')[0].replace('def ', '')
                    lines.insert(i + 1, ' ' * indent + f'"""Function: {func_name}"""')
                    i += 1
            
            # Add docstring to classes
            elif stripped.startswith('class ') and ':' in line:
                if i + 1 < len(lines) and not lines[i + 1].strip().startswith('"""'):
                    indent = len(line) - len(line.lstrip()) + 4
                    class_name = stripped.split('(')[0].split(':')[0].replace('class ', '')
                    lines.insert(i + 1, ' ' * indent + f'"""Class: {class_name}"""')
                    i += 1
            
            # Add inline comments for complex logic
            elif ('if ' in stripped or 'for ' in stripped or 'while ' in stripped) and not '#' in line:
                if len(stripped) > 30:  # Only for longer lines
                    lines[i] = line + '  # Logic check'
            
            i += 1
        
        # 4. Wrap main execution in try-except if not present
        has_try = 'try:' in content
        if not has_try and 'if __name__' in content:
            for i, line in enumerate(lines):
                if 'if __name__' in line:
                    # Find the block and wrap it
                    indent = len(line) - len(line.lstrip())
                    lines.insert(i + 1, ' ' * (indent + 4) + 'try:')
                    # Find end of block
                    j = i + 2
                    while j < len(lines) and (not lines[j].strip() or lines[j].startswith(' ' * (indent + 4))):
                        j += 1
                    lines.insert(j, ' ' * (indent + 4) + 'except Exception as e:')
                    lines.insert(j + 1, ' ' * (indent + 8) + 'logging.error(f"Error: {e}")')
                    break
        
        return '\n'.join(lines)
    
    def _ai_fix_with_client(self, content, issues, client, model):
        """Fix using AI with specified client and model"""
        issues_text = "\n".join([f"- {issue['type']}: {issue['message']} (line {issue.get('line', 0)})" for issue in issues[:10]])
        
        prompt = f"""Refactor this Python code to fix these issues:

{issues_text}

Rules:
1. Split long functions (>50 lines) into smaller helper functions
2. Add logging statements (import logging, use logger)
3. Add try-except error handling
4. Keep all functionality identical
5. Return ONLY the refactored code, no explanations

Code:
```python
{content[:4000]}
```

Refactored code:"""
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a senior software architect. Refactor code to improve quality while preserving functionality."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=4000
        )
        
        fixed_code = response.choices[0].message.content
        if '```' in fixed_code:
            lines = fixed_code.split('\n')
            start = next((i for i, l in enumerate(lines) if l.strip().startswith('```')), 0)
            end = next((i for i, l in enumerate(lines[start+1:], start+1) if l.strip().startswith('```')), len(lines))
            fixed_code = '\n'.join(lines[start+1:end])
        
        return fixed_code.strip()