"""Main agent runner (brain)"""
import logging
from pathlib import Path
from .scanner import Scanner
from .analyzer import Analyzer
from .fixer import Fixer
from .refactor_agent import RefactoringAgent
from .utils import backup_file, write_file, validate_fix

logger = logging.getLogger(__name__)

class AutoFixAgent:
    def __init__(self, force_rescan=True):
        self.scanner = Scanner()
        self.analyzer = Analyzer(force_rescan=force_rescan)
        self.fixer = Fixer()
        self.refactorer = RefactoringAgent()
        self.force_rescan = force_rescan
    
    def run(self, target_path, auto_fix=False):
        """Main execution logic - scan first, then auto-fix if enabled"""
        logger.info(f"Starting agent run on {target_path}, auto_fix={auto_fix}")
        
        # Step 1: Scan for issues
        scan_results = self._scan_files(target_path)
        
        # Step 2: Auto-fix if enabled
        if auto_fix and scan_results["files_with_issues"] > 0:
            logger.info("Starting auto-fix...")
            fix_results = self._fix_files(target_path, scan_results)
            scan_results.update(fix_results)
        
        return scan_results
    
    def _scan_files(self, target_path):
        """Scan files for issues only"""
        logger.info("Scanning files...")
        files = self.scanner.scan(target_path)
        logger.info(f"Found {len(files)} files to analyze")
        
        MAX_FILES = 100
        if len(files) > MAX_FILES:
            logger.warning(f"Too many files ({len(files)}), limiting to {MAX_FILES}")
            files = files[:MAX_FILES]
        
        results = {
            "scanned_files": len(files),
            "files_with_issues": 0,
            "files_fixed": 0,
            "files_list": [str(f) for f in files],
            "issues_found": [],
            "fixes_applied": []
        }
        
        for idx, file_path in enumerate(files, 1):
            logger.info(f"Scanning {idx}/{len(files)}: {file_path.name}")
            
            if 'migration' in str(file_path).lower() or 'alembic' in str(file_path).lower():
                continue
            
            try:
                file_size = file_path.stat().st_size
                if file_size > 500_000:
                    logger.warning(f"Skipping large file: {file_path.name}")
                    continue
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                logger.warning(f"Error reading {file_path}: {e}")
                continue
            
            issues = self.analyzer.analyze(file_path)
            if issues:
                logger.info(f"Found {len(issues)} issues in {file_path.name}")
                results["files_with_issues"] += 1
                results["issues_found"].extend([{"file": str(file_path), "issue": issue} for issue in issues])
        
        logger.info(f"Scan complete: {results['files_with_issues']} files with issues")
        return results
    
    def _fix_files(self, target_path, scan_results):
        """Apply fixes to files with issues"""
        files_to_fix = list(set([item["file"] for item in scan_results["issues_found"]]))
        fix_results = {"files_fixed": 0, "fixes_applied": []}
        
        for file_str in files_to_fix:
            file_path = Path(file_str)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()
                
                file_issues = [item["issue"] for item in scan_results["issues_found"] if item["file"] == file_str]
                
                # Apply pattern-based fixes
                fixed_content = self.fixer.fix(file_path, original_content, file_issues)
                
                # Apply refactoring for quality issues
                quality_issues = [i for i in file_issues if i['type'] in ['MissingLogging', 'MissingErrorHandling', 'LongFunction']]
                if quality_issues:
                    fixed_content = self.refactorer.refactor_file(file_path, fixed_content)
                
                if fixed_content != original_content and validate_fix(original_content, fixed_content):
                    write_file(file_path, fixed_content)
                    fix_results["files_fixed"] += 1
                    fix_results["fixes_applied"].append({"file": file_str, "status": "fixed", "issues": len(file_issues)})
                    logger.info(f"Fixed {file_path.name}")
            except Exception as e:
                logger.error(f"Error fixing {file_path.name}: {e}")
        
        logger.info(f"Auto-fix complete: {fix_results['files_fixed']} files fixed")
        return fix_results