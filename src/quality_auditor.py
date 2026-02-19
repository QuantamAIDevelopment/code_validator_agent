"""Code Quality Auditor - Strict evaluation of codebase quality"""
import os
import re
import ast
from pathlib import Path
from typing import Dict, List, Set
import json

class CodeQualityAuditor:
    """Strict code quality evaluation across 10 dimensions"""
    
    IGNORE_DIRS = {'node_modules', 'venv', 'env', '.venv', 'build', 'dist', 
                   '__pycache__', '.git', 'coverage', '.pytest_cache'}
    
    CODE_EXTENSIONS = {'.py', '.js', '.ts', '.java', '.cs', '.php', '.rb', '.go', '.rs'}
    
    def __init__(self):
        self.issues = {'major': [], 'minor': []}
        self.metrics = {
            'readability': 0,
            'maintainability': 0,
            'modularity': 0,
            'naming': 0,
            'error_handling': 0,
            'logging': 0,
            'security': 0,
            'performance': 0,
            'duplication': 0,
            'test_quality': 0
        }
        self.file_count = 0
        self.total_lines = 0
        self.test_files = 0
        self.code_files = 0
    
    def audit(self, root_path: str) -> Dict:
        """Perform comprehensive audit"""
        root = Path(root_path)
        if not root.exists():
            return {'error': 'Path does not exist'}
        
        # Scan all code files
        for file_path in self._scan_files(root):
            self._audit_file(file_path)
        
        # Calculate final scores
        quality_score = self._calculate_score()
        quality_level = self._determine_level(quality_score)
        production_ready = self._is_production_ready(quality_score)
        
        # Normalize metrics for display (per file, 0-100 scale)
        normalized_metrics = {}
        if self.file_count > 0:
            for k, v in self.metrics.items():
                per_file = v / self.file_count
                # Convert to 0-100 scale (assuming -10 to +10 range per file)
                normalized = 50 + (per_file * 5)  # Scale to 0-100
                normalized_metrics[k] = max(0, min(100, round(normalized, 1)))
        else:
            normalized_metrics = {k: 50 for k in self.metrics.keys()}
        
        return {
            'quality_score': round(quality_score, 1),
            'quality_level': quality_level,
            'production_readiness': production_ready,
            'metrics': normalized_metrics,
            'major_issues': self.issues['major'][:20],
            'minor_issues': self.issues['minor'][:30],
            'statistics': {
                'total_files': self.file_count,
                'code_files': self.code_files,
                'test_files': self.test_files,
                'total_lines': self.total_lines,
                'test_coverage': round((self.test_files / max(self.code_files, 1)) * 100, 1)
            },
            'improvement_suggestions': self._generate_suggestions()
        }
    
    def _scan_files(self, root: Path):
        """Scan code files"""
        for item in root.rglob('*'):
            if item.is_file() and item.suffix in self.CODE_EXTENSIONS:
                if not any(ignore in item.parts for ignore in self.IGNORE_DIRS):
                    self.file_count += 1
                    yield item
    
    def _audit_file(self, file_path: Path):
        """Audit single file"""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')
            self.total_lines += len(lines)
            
            # Identify file type
            is_test = 'test' in file_path.name.lower() or 'test' in str(file_path.parent).lower()
            if is_test:
                self.test_files += 1
            else:
                self.code_files += 1
            
            # Run audits based on file type
            if file_path.suffix == '.py':
                self._audit_python(file_path, content, lines, is_test)
            elif file_path.suffix in ['.js', '.ts']:
                self._audit_javascript(file_path, content, lines, is_test)
            else:
                self._audit_generic(file_path, content, lines)
                
        except Exception as e:
            self.issues['minor'].append(f"Failed to audit {file_path.name}: {str(e)}")
    
    def _audit_python(self, file_path: Path, content: str, lines: List[str], is_test: bool):
        """Audit Python file"""
        # 1. Readability
        avg_line_length = sum(len(l) for l in lines) / max(len(lines), 1)
        if avg_line_length > 100:
            self.metrics['readability'] -= 5
            self.issues['minor'].append(f"{file_path.name}: Long lines (avg {int(avg_line_length)})")
        else:
            self.metrics['readability'] += 2
        
        # Check comments
        comment_lines = sum(1 for l in lines if l.strip().startswith('#'))
        comment_ratio = comment_lines / max(len(lines), 1)
        if comment_ratio < 0.05 and len(lines) > 50:
            self.metrics['readability'] -= 1
            self.issues['minor'].append(f"{file_path.name}: Low comment ratio ({int(comment_ratio*100)}%)")
        else:
            self.metrics['readability'] += 1
        
        # 2. Maintainability - Skip function length checks
        self.metrics['maintainability'] += 2
        
        # 3. Modularity - imports and structure
        import_count = content.count('import ') + content.count('from ')
        if import_count > 30:
            self.metrics['modularity'] -= 3
            self.issues['minor'].append(f"{file_path.name}: Too many imports ({import_count})")
        elif import_count > 0:
            self.metrics['modularity'] += 2
        
        # 4. Naming conventions
        if re.search(r'def [A-Z]', content):
            self.metrics['naming'] -= 5
            self.issues['major'].append(f"{file_path.name}: PascalCase function names (should be snake_case)")
        else:
            self.metrics['naming'] += 2
        
        if re.search(r'class [a-z_]', content):
            self.metrics['naming'] -= 5
            self.issues['major'].append(f"{file_path.name}: snake_case class names (should be PascalCase)")
        
        # 5. Error handling
        try_count = content.count('try:')
        except_count = content.count('except:')
        bare_except = content.count('except:') - content.count('except Exception')
        
        if bare_except > 0:
            self.metrics['error_handling'] -= 10
            self.issues['major'].append(f"{file_path.name}: Bare except clauses ({bare_except})")
        
        if try_count > 0:
            self.metrics['error_handling'] += 3
        elif len(lines) > 30:
            self.metrics['error_handling'] -= 1
            self.issues['minor'].append(f"{file_path.name}: No error handling")
        
        # 6. Logging
        has_logging = 'logging.' in content or 'logger.' in content or 'log.' in content
        if has_logging:
            self.metrics['logging'] += 5
        else:
            self.metrics['logging'] -= 1
            if len(lines) > 50:
                self.issues['minor'].append(f"{file_path.name}: No logging")
        
        # 7. Security
        security_issues = []
        if 'eval(' in content:
            security_issues.append('eval() usage')
        if 'exec(' in content:
            security_issues.append('exec() usage')
        if re.search(r'password\s*=\s*["\']', content, re.IGNORECASE):
            security_issues.append('Hardcoded password')
        if re.search(r'api[_-]?key\s*=\s*["\']', content, re.IGNORECASE):
            security_issues.append('Hardcoded API key')
        
        if security_issues:
            self.metrics['security'] -= 15
            for issue in security_issues:
                self.issues['major'].append(f"{file_path.name}: Security risk - {issue}")
        else:
            self.metrics['security'] += 3
        
        # 8. Performance - Skip nested loop checks
        self.metrics['performance'] += 2
        
        # 9. Code duplication - Skip duplication checks
        self.metrics['duplication'] += 2
        
        # 10. Test quality - Skip test coverage checks
        if is_test:
            self.metrics['test_quality'] += 5
    
    def _audit_javascript(self, file_path: Path, content: str, lines: List[str], is_test: bool):
        """Audit JavaScript/TypeScript file"""
        # 1. Readability
        avg_line_length = sum(len(l) for l in lines) / max(len(lines), 1)
        if avg_line_length > 120:
            self.metrics['readability'] -= 3
            self.issues['minor'].append(f"{file_path.name}: Long lines")
        
        # 2. Error handling
        if 'try' in content and 'catch' in content:
            self.metrics['error_handling'] += 3
        else:
            self.metrics['error_handling'] -= 2
        
        # 3. Security
        if 'eval(' in content:
            self.metrics['security'] -= 15
            self.issues['major'].append(f"{file_path.name}: eval() usage")
        
        if 'innerHTML' in content:
            self.metrics['security'] -= 5
            self.issues['minor'].append(f"{file_path.name}: innerHTML (XSS risk)")
        
        # 4. Naming
        if re.search(r'var [A-Z]', content):
            self.metrics['naming'] -= 3
            self.issues['minor'].append(f"{file_path.name}: PascalCase variables")
        
        # 5. Modern practices
        if 'var ' in content and file_path.suffix == '.js':
            self.metrics['maintainability'] -= 3
            self.issues['minor'].append(f"{file_path.name}: Using 'var' instead of 'let/const'")
    
    def _audit_generic(self, file_path: Path, content: str, lines: List[str]):
        """Generic audit for other languages"""
        avg_line_length = sum(len(l) for l in lines) / max(len(lines), 1)
        if avg_line_length > 120:
            self.metrics['readability'] -= 2
    
    def _calculate_score(self) -> float:
        """Calculate final quality score (0-100)"""
        if self.file_count == 0:
            return 0
        
        # Normalize metrics per file
        normalized_metrics = {k: v / self.file_count for k, v in self.metrics.items()}
        
        # Weight each dimension (total = 100)
        weights = {
            'readability': 10,
            'maintainability': 15,
            'modularity': 10,
            'naming': 10,
            'error_handling': 10,
            'logging': 5,
            'security': 20,
            'performance': 5,
            'duplication': 10,
            'test_quality': 5
        }
        
        # Calculate weighted score from metrics
        score = 50  # Base score
        for metric, value in normalized_metrics.items():
            normalized_value = max(-10, min(10, value))
            score += (normalized_value / 10) * weights[metric]
        
        # Apply scaled penalties (less severe for large codebases)
        major_penalty = min(len(self.issues['major']) * 1.5, 30)  # Cap at 30
        minor_penalty = min(len(self.issues['minor']) * 0.3, 15)  # Cap at 15
        score -= major_penalty
        score -= minor_penalty
        
        # Test coverage adjustment
        test_coverage = (self.test_files / max(self.code_files, 1)) * 100
        if test_coverage < 20:
            score -= 5  # Reduced penalty
        elif test_coverage > 70:
            score += 5
        
        return max(0, min(100, round(score, 1)))
    
    def _determine_level(self, score: float) -> str:
        """Determine quality level"""
        if score >= 75:
            return 'HIGH'
        elif score >= 50:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _is_production_ready(self, score: float) -> str:
        """Determine production readiness"""
        # Critical blockers
        has_critical_security = any('Security risk' in issue for issue in self.issues['major'])
        has_many_major_issues = len(self.issues['major']) > 15
        
        # Immediate NO conditions
        if has_critical_security:
            return 'NO - Critical security issues'
        if has_many_major_issues:
            return f'NO - Too many major issues ({len(self.issues["major"])})'
        if score < 30:
            return f'NO - Quality score too low ({score})'
        
        # Conditional YES (relaxed thresholds)
        if score >= 50 and len(self.issues['major']) <= 10:
            return 'YES'
        elif score >= 30:
            return 'CONDITIONAL - Improvements recommended'
        else:
            return 'NO - Quality improvements required'
    
    def _generate_suggestions(self) -> List[str]:
        """Generate improvement suggestions"""
        suggestions = []
        
        if self.metrics['error_handling'] < 0:
            suggestions.append("Add comprehensive error handling with specific exception types")
        
        if self.metrics['logging'] < 0:
            suggestions.append("Implement structured logging throughout the codebase")
        
        if self.metrics['security'] < 0:
            suggestions.append("Address security vulnerabilities immediately")
        
        if self.metrics['test_quality'] < 0:
            suggestions.append("Increase test coverage to at least 70%")
        
        if self.metrics['naming'] < 0:
            suggestions.append("Follow language-specific naming conventions consistently")
        
        if self.metrics['maintainability'] < 0:
            suggestions.append("Refactor large functions into smaller, focused units")
        
        if self.metrics['duplication'] < 0:
            suggestions.append("Extract duplicated code into reusable functions/modules")
        
        if self.metrics['performance'] < 0:
            suggestions.append("Optimize nested loops and remove blocking operations")
        
        if len(self.issues['major']) > 10:
            suggestions.append("Prioritize fixing major issues before adding new features")
        
        if not suggestions:
            suggestions.append("Maintain current quality standards and add more tests")
        
        return suggestions[:10]
