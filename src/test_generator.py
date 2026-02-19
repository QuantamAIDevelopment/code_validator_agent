"""Test Generator Agent - Generates pytest tests"""
import os
import logging
from pathlib import Path
from openai import OpenAI

logger = logging.getLogger(__name__)

class TestGenerator:
    def __init__(self):
        self.groq_key = os.getenv('GROQ_API_KEY')
        self.groq_client = None
        if self.groq_key:
            self.groq_client = OpenAI(api_key=self.groq_key, base_url="https://api.groq.com/openai/v1")
    
    def generate_tests(self, source_dir):
        """Generate test files for Python modules"""
        if not self.groq_client:
            logger.warning("No Groq client - skipping test generation")
            return 0
        
        source_path = Path(source_dir)
        tests_dir = source_path / 'tests'
        tests_dir.mkdir(exist_ok=True)
        
        # Create __init__.py
        (tests_dir / '__init__.py').write_text('"""Tests"""')
        
        # Find main modules
        py_files = list(source_path.rglob('*.py'))
        py_files = [f for f in py_files if 'test' not in f.name and '__pycache__' not in str(f)]
        
        generated = 0
        for py_file in py_files[:5]:  # Limit to 5 files
            try:
                test_content = self._generate_test_for_file(py_file)
                if test_content:
                    test_file = tests_dir / f'test_{py_file.name}'
                    test_file.write_text(test_content)
                    generated += 1
                    logger.info(f"Generated test: {test_file.name}")
            except Exception as e:
                logger.error(f"Failed to generate test for {py_file.name}: {e}")
        
        return generated
    
    def _generate_test_for_file(self, py_file):
        """Generate test content using AI"""
        try:
            content = py_file.read_text(encoding='utf-8', errors='ignore')
            
            prompt = f"""Generate pytest tests for this Python module.

Rules:
1. Use pytest framework
2. Mock external dependencies
3. Test main functions and classes
4. Include edge cases
5. Return ONLY the test code

Code:
```python
{content[:3000]}
```

Test code:"""
            
            response = self.groq_client.chat.completions.create(
                model='llama-3.3-70b-versatile',
                messages=[
                    {"role": "system", "content": "Generate pytest tests. Return only test code."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            test_code = response.choices[0].message.content
            if '```' in test_code:
                lines = test_code.split('\n')
                start = next((i for i, l in enumerate(lines) if 'python' in l.lower() or l.strip() == '```'), 0)
                end = next((i for i, l in enumerate(lines[start+1:], start+1) if l.strip().startswith('```')), len(lines))
                test_code = '\n'.join(lines[start+1:end])
            
            return test_code.strip()
        except Exception as e:
            logger.error(f"AI test generation failed: {e}")
            return None
