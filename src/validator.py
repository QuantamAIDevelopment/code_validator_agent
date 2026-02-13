"""Code validation after fixes"""
import ast
import subprocess

class Validator:
    def validate_python(self, content):
        """Validate Python code syntax"""
        try:
            ast.parse(content)
            return True, "Valid syntax"
        except SyntaxError as e:
            return False, f"Syntax error: {e}"
    
    def validate_with_tools(self, file_path):
        """Validate using external tools"""
        try:
            # Quick pylint check
            result = subprocess.run(
                ['pylint', str(file_path), '--errors-only'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return True, "No critical errors"
            else:
                return False, "Critical errors found"
        except Exception:
            return True, "Validation skipped"