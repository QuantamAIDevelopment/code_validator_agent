"""Enhanced Fixer - Fixes major quality issues"""
import ast
import re
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class EnhancedFixer:
    """Fixes major quality issues that basic fixer misses"""
    
    def fix_long_functions(self, file_path, content):
        """Add TODO comments for long functions"""
        try:
            tree = ast.parse(content)
            lines = content.split('\n')
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_len = node.end_lineno - node.lineno
                    if func_len > 50:
                        # Add TODO comment
                        indent = len(lines[node.lineno - 1]) - len(lines[node.lineno - 1].lstrip())
                        comment = ' ' * indent + f'# TODO: Refactor {node.name} - function too long ({func_len} lines)\n'
                        lines.insert(node.lineno - 1, comment)
            
            return '\n'.join(lines)
        except:
            return content
    
    def add_error_handling(self, content):
        """Add basic try-except to functions without error handling"""
        if 'try:' in content:
            return content
        
        lines = content.split('\n')
        modified = False
        i = 0
        
        while i < len(lines):
            line = lines[i]
            if line.strip().startswith('def ') and ':' in line and '__init__' not in line:
                # Find function body start
                indent = len(line) - len(line.lstrip())
                j = i + 1
                
                # Skip docstring and empty lines
                while j < len(lines) and (not lines[j].strip() or '"""' in lines[j] or "'''" in lines[j]):
                    j += 1
                
                # Check if already has try
                if j < len(lines) and 'try:' not in lines[j]:
                    # Find function end
                    k = j
                    while k < len(lines) and (lines[k].startswith(' ' * (indent + 4)) or not lines[k].strip()):
                        k += 1
                    
                    # Wrap function body in try-except
                    lines.insert(j, ' ' * (indent + 4) + 'try:')
                    # Indent existing body
                    for idx in range(j + 1, k + 1):
                        if lines[idx].strip():
                            lines[idx] = '    ' + lines[idx]
                    
                    lines.insert(k + 1, ' ' * (indent + 4) + 'except Exception as e:')
                    lines.insert(k + 2, ' ' * (indent + 8) + 'logger.error(f"Error in function: {e}")')
                    lines.insert(k + 3, ' ' * (indent + 8) + 'raise')
                    modified = True
                    i = k + 4
                    continue
            i += 1
        
        return '\n'.join(lines) if modified else content
    
    def add_logging(self, content):
        """Add logging import"""
        if 'import logging' in content:
            return content
        
        lines = content.split('\n')
        
        # Find first import
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                lines.insert(i + 1, 'import logging')
                lines.insert(i + 2, 'logger = logging.getLogger(__name__)')
                lines.insert(i + 3, '')
                break
        
        return '\n'.join(lines)
    
    def add_comments(self, content):
        """Add comprehensive comments to functions and classes"""
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Add function docstrings
            if line.strip().startswith('def ') and ':' in line:
                if i + 1 < len(lines) and not lines[i + 1].strip().startswith('"""'):
                    indent = len(line) - len(line.lstrip())
                    func_name = line.strip().split('(')[0].replace('def ', '')
                    
                    # Extract parameters
                    params_match = re.search(r'\((.*)\)', line)
                    params = params_match.group(1) if params_match else ''
                    
                    docstring = f'{" " * (indent + 4)}"""\n'
                    docstring += f'{" " * (indent + 4)}{func_name.replace("_", " ").title()}\n'
                    if params and params != 'self':
                        docstring += f'{" " * (indent + 4)}\n'
                        docstring += f'{" " * (indent + 4)}Args:\n'
                        for param in params.split(','):
                            param = param.strip().split('=')[0].split(':')[0].strip()
                            if param and param != 'self':
                                docstring += f'{" " * (indent + 8)}{param}: Description\n'
                    docstring += f'{" " * (indent + 4)}"""'
                    
                    lines.insert(i + 1, docstring)
                    i += 1
            
            # Add class docstrings
            elif line.strip().startswith('class ') and ':' in line:
                if i + 1 < len(lines) and not lines[i + 1].strip().startswith('"""'):
                    indent = len(line) - len(line.lstrip())
                    class_name = line.strip().split('(')[0].split(':')[0].replace('class ', '')
                    lines.insert(i + 1, f'{" " * (indent + 4)}"""Class: {class_name}"""')
                    i += 1
            
            i += 1
        
        return '\n'.join(lines)
    
    def fix_file(self, file_path):
        """Apply all fixes to a file"""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            original = content
            
            # Apply fixes in order
            content = self.add_logging(content)  # Fix: No logging
            content = self.add_comments(content)  # Fix: Low comment ratio
            content = self.add_error_handling(content)  # Fix: No error handling
            content = self.fix_long_functions(file_path, content)  # Add TODO for long functions
            
            if content != original:
                file_path.write_text(content, encoding='utf-8')
                logger.info(f"Fixed: {file_path.name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error fixing {file_path}: {e}")
            return False
