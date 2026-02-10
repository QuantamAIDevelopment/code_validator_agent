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
        """Fix detected issues using pattern-based fixes only (fast)"""
        if not issues:
            return content
        
        # Apply pattern fixes only - no AI to avoid delays
        return self._pattern_based_fix(content, issues)
    
    def _pattern_based_fix(self, content, issues):
        """Apply pattern-based fixes for ALL issue types"""
        lines = content.split('\n')
        modified = False
        
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
            
            elif issue_type == 'CodeQuality':
                if 'console.log(' in line:
                    line = ' ' * indent + '// ' + stripped
                elif '!important' in line:
                    line = line.replace('!important', '')
            
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
                match = re.search(r'if\s+(\w+)\s*=\s*([^=])', line)
                if match:
                    line = line.replace(f'{match.group(1)} =', f'{match.group(1)} ==', 1)
            
            elif issue_type == 'EmptyFunction':
                if 'pass' in line:
                    line = ' ' * indent + 'raise NotImplementedError()'
            
            elif issue_type == 'PerformanceIssue':
                line = ' ' * indent + '# ' + stripped + '  # TODO: Use join()'
            
            elif issue_type == 'DuplicateException':
                line = ' ' * indent + '# ' + stripped + '  # Duplicate'
            
            if line != original_line:
                lines[line_num - 1] = line
                modified = True
        
        return '\n'.join(lines)
    
    def _ai_fix_with_client(self, content, issues, client, model):
        """Fix using AI with specified client and model"""
        issues_text = "\n".join([f"- {issue['type']}: {issue['message']} (line {issue['line']})" for issue in issues[:20]])  # Limit to 20 issues
        
        prompt = f"""Fix these code issues:

{issues_text}

Code:
```
{content[:2000]}```

Return ONLY the fixed code, no explanations."""
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Fix code issues. Return only fixed code."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2000
        )
        
        fixed_code = response.choices[0].message.content
        if '```' in fixed_code:
            lines = fixed_code.split('\n')
            start = next((i for i, l in enumerate(lines) if l.strip().startswith('```')), 0)
            end = next((i for i, l in enumerate(lines[start+1:], start+1) if l.strip().startswith('```')), len(lines))
            fixed_code = '\n'.join(lines[start+1:end])
        
        return fixed_code.strip()