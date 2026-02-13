"""Multi-Agent Code Organization Orchestrator"""
import os
from pathlib import Path
from typing import Dict
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from scanner import Scanner
from analyzer import Analyzer
from organizer import CodeOrganizer
from refactor_agent import RefactorAgent
import logging

logger = logging.getLogger(__name__)

class CodeOrganizationOrchestrator:
    """Orchestrates multiple agents for code organization"""
    
    def __init__(self):
        self.scanner = Scanner()
        self.analyzer = Analyzer(force_rescan=True)
        self.organizer = CodeOrganizer()
        self.refactor_agent = RefactorAgent()
    
    def orchestrate(self, source_path: str, target_path: str = None) -> Dict:
        """
        Orchestrate agents: Scanner → Detector → Structure → Organizer → Refactor → Validator
        """
        logger.info("Starting multi-agent orchestration...")
        
        # Step 1: Organize code structure
        logger.info("Agent 1: Organizing code structure...")
        organize_results = self.organizer.organize_project(source_path, target_path)
        
        # Step 2: Fix imports and update configs
        logger.info("Agent 2: Fixing imports and updating configs...")
        refactor_results = self.refactor_agent.refactor_project(
            Path(source_path),
            Path(organize_results['organized_path']),
            organize_results['organized_files']
        )
        
        # Step 3: Validate organized structure
        logger.info("Agent 3: Validating organized structure...")
        validation = self._validate_structure(organize_results['organized_path'])
        
        return {
            'organized_path': organize_results['organized_path'],
            'files_organized': organize_results['files_organized'],
            'detected_languages': organize_results['detected_languages'],
            'detected_frameworks': organize_results['detected_frameworks'],
            'folder_tree': organize_results['folder_tree'],
            'refactoring': refactor_results,
            'validation': validation
        }
    
    def _validate_structure(self, path: str) -> Dict:
        """Validate the organized structure"""
        path_obj = Path(path)
        
        has_src = (path_obj / 'src').exists() or (path_obj / 'app').exists()
        has_tests = (path_obj / 'tests').exists()
        has_docs = (path_obj / 'docs').exists()
        has_config = (path_obj / 'config').exists()
        
        file_count = sum(1 for _ in path_obj.rglob('*') if _.is_file())
        
        return {
            'valid': has_src and file_count > 0,
            'has_source_folder': has_src,
            'has_tests': has_tests,
            'has_docs': has_docs,
            'has_config': has_config,
            'total_files': file_count
        }
