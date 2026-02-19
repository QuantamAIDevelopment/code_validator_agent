"""Helper function for applying fixes in audit endpoints"""
import logging
from pathlib import Path
from src.agent import AutoFixAgent
from src.refactor_agent import RefactoringAgent
from src.test_generator import TestGenerator
from src.scanner import Scanner
from src.enhanced_fixer import EnhancedFixer

logger = logging.getLogger(__name__)

def apply_auto_fixes(extract_dir):
    """Apply auto-fixes using AutoFixAgent with RefactoringAgent and EnhancedFixer"""
    logger.info("Applying comprehensive auto-fixes...")
    
    # Step 1: Apply pattern-based fixes
    agent = AutoFixAgent(force_rescan=True)
    fix_result = agent.run(extract_dir, auto_fix=True)
    logger.info(f"Pattern fixes: {fix_result.get('files_fixed', 0)} files")
    
    # Step 2: Apply enhanced fixes (error handling, logging, comments)
    enhanced = EnhancedFixer()
    scanner = Scanner()
    files = scanner.scan(extract_dir)
    
    enhanced_count = 0
    for file_path in files:
        if file_path.suffix == '.py':
            if enhanced.fix_file(file_path):
                enhanced_count += 1
    logger.info(f"Enhanced fixes: {enhanced_count} files")
    
    # Step 3: Apply AI refactoring for long functions
    refactorer = RefactoringAgent()
    refactored_count = 0
    for file_path in files:
        if file_path.suffix == '.py':
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    original = f.read()
                
                refactored = refactorer.refactor_file(file_path, original)
                
                if refactored != original:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(refactored)
                    refactored_count += 1
                    logger.info(f"Refactored: {file_path.name}")
            except Exception as e:
                logger.error(f"Error refactoring {file_path.name}: {e}")
    
    logger.info(f"AI refactoring: {refactored_count} files")
    
    # Step 4: Generate tests
    test_gen = TestGenerator()
    tests_generated = test_gen.generate_tests(extract_dir)
    logger.info(f"Tests generated: {tests_generated} files")
    
    fix_result['files_fixed'] = fix_result.get('files_fixed', 0) + enhanced_count + refactored_count
    fix_result['tests_generated'] = tests_generated
    return fix_result
