"""Production Refactoring Agent - Fixes quality issues"""
import ast
import logging
import os
from openai import OpenAI
from pathlib import Path

logger = logging.getLogger(__name__)

class RefactoringAgent:
    """Refactors code to fix quality issues"""
    
    def __init__(self):
        self.groq_key = os.getenv('GROQ_API_KEY')
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.groq_client = None
        self.openai_client = None
        
        if self.groq_key:
            self.groq_client = OpenAI(api_key=self.groq_key, base_url="https://api.groq.com/openai/v1")
        
        if self.openai_key:
            self.openai_client = OpenAI(api_key=self.openai_key)
    
    def refactor_project(self, source_path, target_path, organized_files):
        """Refactor entire project"""
        logger.info(f"Refactoring project: {target_path}")
        
        refactored = 0
        for file_path in Path(target_path).rglob('*.py'):
            if file_path.is_file():
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    new_content = self.refactor_file(file_path, content)
                    if new_content != content:
                        file_path.write_text(new_content, encoding='utf-8')
                        refactored += 1
                except Exception as e:
                    logger.error(f"Error refactoring {file_path}: {e}")
        
        return {
            'files_refactored': refactored,
            'python_imports_fixed': 0,
            'js_imports_fixed': 0,
            'config_files_updated': 0
        }
    
    def refactor_file(self, file_path, content):
        """Refactor a single file"""
        if file_path.suffix != '.py':
            return content
        
        logger.info(f"Refactoring {file_path.name}")
        
        # Check for long functions
        has_long_functions = self._has_long_functions(content)
        logger.info(f"{file_path.name}: has_long_functions={has_long_functions}")
        
        if has_long_functions and (self.groq_client or self.openai_client):
            logger.info(f"Attempting AI refactoring for {file_path.name}")
            refactored = self._ai_split_functions(content, file_path)
            if refactored != content:
                logger.info(f"AI refactored {file_path.name} successfully")
                content = refactored
            else:
                logger.warning(f"AI refactoring returned same content for {file_path.name}")
        elif has_long_functions:
            logger.warning(f"Long functions detected but no AI client available")
        
        # Add logging if missing
        content = self._add_logging(content)
        
        # Add error handling if missing
        content = self._add_error_handling(content)
        
        # Add docstrings
        content = self._add_docstrings(content, file_path)
        
        return content
    
    def _has_long_functions(self, content):
        """Check if file has functions > 50 lines"""
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if node.end_lineno - node.lineno > 50:
                        return True
        except:
            pass
        return False
    
    def _ai_split_functions(self, content, file_path):
        """Use AI to split long functions"""
        # Try Groq first
        if self.groq_client:
            try:
                logger.info(f"Calling Groq API for {file_path.name}")
                return self._call_ai(self.groq_client, 'llama-3.3-70b-versatile', content, file_path, 6000)
            except Exception as e:
                if 'rate_limit' in str(e).lower():
                    logger.warning(f"Groq rate limit, trying OpenAI for {file_path.name}")
                else:
                    logger.error(f"Groq failed: {e}")
        
        # Fallback to OpenAI
        if self.openai_client:
            try:
                logger.info(f"Calling OpenAI API for {file_path.name}")
                return self._call_ai(self.openai_client, 'gpt-4o-mini', content, file_path, 4000)
            except Exception as e:
                logger.error(f"OpenAI failed: {e}")
        
        return content
    
    def _call_ai(self, client, model, content, file_path, max_tokens):
        """Call AI API"""
        prompt = f"""Refactor this Python code by splitting long functions (>50 lines) into smaller helper functions.

Rules:
1. Split functions > 50 lines into multiple smaller functions
2. Keep all functionality identical
3. Return ONLY the refactored code

Code:
```python
{content[:6000]}
```

Refactored code:"""
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Refactor code by splitting long functions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=max_tokens
        )
        
        fixed_code = response.choices[0].message.content
        if '```' in fixed_code:
            lines = fixed_code.split('\n')
            start = next((i for i, l in enumerate(lines) if 'python' in l.lower() or l.strip() == '```'), 0)
            end = next((i for i, l in enumerate(lines[start+1:], start+1) if l.strip().startswith('```')), len(lines))
            fixed_code = '\n'.join(lines[start+1:end])
        
        return fixed_code.strip()
    
    def _add_logging(self, content):
        """Add logging import and logger"""
        if 'import logging' in content or 'from logging' in content:
            return content
        
        lines = content.split('\n')
        
        # Find first import
        import_idx = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                import_idx = i + 1
                break
        
        # Add logging
        lines.insert(import_idx, 'import logging')
        lines.insert(import_idx + 1, 'logger = logging.getLogger(__name__)')
        lines.insert(import_idx + 2, '')
        
        return '\n'.join(lines)
    
    def _add_error_handling(self, content):
        """Add try-except to main execution"""
        if 'try:' in content or 'if __name__' not in content:
            return content
        
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            if 'if __name__' in line:
                indent = len(line) - len(line.lstrip())
                # Find next non-empty line
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                
                if j < len(lines):
                    lines.insert(j, ' ' * (indent + 4) + 'try:')
                    
                    # Find end of block
                    k = j + 1
                    while k < len(lines) and (not lines[k].strip() or lines[k].startswith(' ' * (indent + 4))):
                        k += 1
                    
                    lines.insert(k, ' ' * (indent + 4) + 'except Exception as e:')
                    lines.insert(k + 1, ' ' * (indent + 8) + 'logger.error(f"Error: {e}")')
                    lines.insert(k + 2, ' ' * (indent + 8) + 'raise')
                break
        
        return '\n'.join(lines)
    
    def _add_docstrings(self, content, file_path):
        """Add missing docstrings"""
        lines = content.split('\n')
        
        # Add module docstring
        if not lines[0].strip().startswith('"""'):
            lines.insert(0, f'"""Module: {file_path.name}"""')
            lines.insert(1, '')
        
        # Add function docstrings
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            if stripped.startswith('def ') and ':' in line:
                if i + 1 < len(lines) and not lines[i + 1].strip().startswith('"""'):
                    indent = len(line) - len(line.lstrip()) + 4
                    func_name = stripped.split('(')[0].replace('def ', '')
                    lines.insert(i + 1, ' ' * indent + f'"""Function: {func_name}"""')
                    i += 1
            
            elif stripped.startswith('class ') and ':' in line:
                if i + 1 < len(lines) and not lines[i + 1].strip().startswith('"""'):
                    indent = len(line) - len(line.lstrip()) + 4
                    class_name = stripped.split('(')[0].split(':')[0].replace('class ', '')
                    lines.insert(i + 1, ' ' * indent + f'"""Class: {class_name}"""')
                    i += 1
            
            i += 1
        
        return '\n'.join(lines)
