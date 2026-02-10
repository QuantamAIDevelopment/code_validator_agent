"""Main agent runner (brain)"""
from .scanner import Scanner
from .analyzer import Analyzer
from .fixer import Fixer
from .utils import backup_file, write_file, validate_fix

class AutoFixAgent:
    def __init__(self, force_rescan=True):
        self.scanner = Scanner()
        self.analyzer = Analyzer(force_rescan=force_rescan)
        self.fixer = Fixer()
        self.force_rescan = force_rescan
        self._scan_cache = {}  # Clear cache on each instance
    
    def run(self, target_path, auto_fix=False):
        """Main execution logic - scan only by default, fix only if auto_fix=True"""
        # Clear all caches when force_rescan is enabled
        if self.force_rescan:
            self._scan_cache.clear()
            self.analyzer.clear_cache()
        
        # Fresh scan
        files = self.scanner.scan(target_path)
        results = {
            "scanned_files": len(files),
            "files_with_issues": 0,
            "files_fixed": 0,
            "files_list": [str(f) for f in files],
            "issues_found": [],
            "fixes_applied": []
        }
        
        for file_path in files:
            try:
                # Read with minimal buffering for fresh content
                with open(file_path, 'r', encoding='utf-8', buffering=1) as f:
                    original_content = f.read()
            except Exception as e:
                results["issues_found"].append({"file": str(file_path), "error": str(e)})
                continue
            
            issues = self.analyzer.analyze(file_path)
            if not issues:
                continue
            
            results["files_with_issues"] += 1
            results["issues_found"].extend([{"file": str(file_path), "issue": issue} for issue in issues])
            
            # Only fix if auto_fix is enabled
            if auto_fix:
                fixed_content = self.fixer.fix(file_path, original_content, issues)
                
                # Check if content actually changed
                if fixed_content != original_content:
                    if validate_fix(original_content, fixed_content):
                        backup_file(file_path)
                        write_file(file_path, fixed_content)
                        results["files_fixed"] += 1
                        results["fixes_applied"].append({"file": str(file_path), "status": "fixed", "issues": len(issues)})
        
        return results