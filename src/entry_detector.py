"""Entry Point Detection Agent - Identifies starting file in any codebase"""
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

class EntryPointDetector:
    """Detects the main entry point file in a codebase"""
    
    IGNORE_DIRS = {'node_modules', 'venv', 'env', '.venv', 'build', 'dist', '__pycache__', 
                   '.git', 'test', 'tests', '__tests__', 'coverage', '.pytest_cache'}
    
    ENTRY_PATTERNS = {
        'python': ['main.py', 'app.py', 'server.py', 'run.py', 'manage.py', 'wsgi.py', 'asgi.py', '__main__.py'],
        'javascript': ['index.js', 'main.js', 'app.js', 'server.js', 'index.ts', 'main.ts', 'app.ts', 'server.ts'],
        'java': ['Main.java', 'Application.java', 'App.java'],
        'go': ['main.go'],
        'rust': ['main.rs'],
        'csharp': ['Program.cs', 'Startup.cs'],
        'php': ['index.php', 'main.php', 'app.php'],
        'ruby': ['main.rb', 'app.rb', 'application.rb']
    }
    
    def detect(self, root_path: str) -> Dict:
        """Detect entry point in codebase"""
        root = Path(root_path)
        if not root.exists():
            return {'error': 'Path does not exist', 'entry_file': None}
        
        candidates = []
        
        # Scan for candidate files
        for file_path in self._scan_files(root):
            score = self._score_file(file_path, root)
            if score > 0:
                candidates.append((file_path, score))
        
        if not candidates:
            return {'error': 'No entry point found', 'entry_file': None, 'candidates': []}
        
        # Sort by score (highest first)
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        best_file, best_score = candidates[0]
        
        return {
            'entry_file': str(best_file),
            'confidence': self._confidence_level(best_score),
            'language': self._detect_language(best_file),
            'all_candidates': [str(f) for f, s in candidates[:5]]
        }
    
    def _scan_files(self, root: Path):
        """Recursively scan files, ignoring common build directories"""
        for item in root.rglob('*'):
            if item.is_file() and not any(ignore in item.parts for ignore in self.IGNORE_DIRS):
                yield item
    
    def _score_file(self, file_path: Path, root: Path) -> int:
        """Score a file based on entry point indicators"""
        score = 0
        filename = file_path.name.lower()
        rel_path = file_path.relative_to(root)
        
        # Check if filename matches entry patterns
        for lang, patterns in self.ENTRY_PATTERNS.items():
            if filename in [p.lower() for p in patterns]:
                score += 50
                break
        
        # Root level files get bonus
        if len(rel_path.parts) == 1:
            score += 30
        elif len(rel_path.parts) == 2 and rel_path.parts[0] in ['src', 'app', 'lib']:
            score += 20
        
        # Check file content for runtime indicators
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            score += self._score_content(content, file_path.suffix)
        except:
            pass
        
        return score
    
    def _score_content(self, content: str, ext: str) -> int:
        """Score file content for runtime indicators"""
        score = 0
        
        if ext == '.py':
            if 'if __name__ == "__main__"' in content or "if __name__ == '__main__'" in content:
                score += 40
            if re.search(r'(FastAPI|Flask|Django|uvicorn\.run|app\.run)', content):
                score += 30
            if 'def main(' in content:
                score += 20
        
        elif ext in ['.js', '.ts']:
            if re.search(r'(express\(\)|app\.listen|createServer)', content):
                score += 30
            if 'module.exports' in content or 'export default' in content:
                score += 10
        
        elif ext == '.java':
            if 'public static void main' in content:
                score += 40
            if '@SpringBootApplication' in content:
                score += 30
        
        elif ext == '.go':
            if 'func main()' in content:
                score += 40
        
        elif ext == '.rs':
            if 'fn main()' in content:
                score += 40
        
        elif ext == '.cs':
            if 'static void Main' in content:
                score += 40
        
        return score
    
    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension"""
        ext_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.go': 'Go',
            '.rs': 'Rust',
            '.cs': 'C#',
            '.php': 'PHP',
            '.rb': 'Ruby'
        }
        return ext_map.get(file_path.suffix, 'Unknown')
    
    def _confidence_level(self, score: int) -> str:
        """Convert score to confidence level"""
        if score >= 80:
            return 'High'
        elif score >= 50:
            return 'Medium'
        else:
            return 'Low'
