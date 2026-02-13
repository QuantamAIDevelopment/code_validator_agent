"""Orchestrator - Coordinates multi-agent system"""
from pathlib import Path
from typing import Dict
from .scanner_agent import ScannerAgent
from .detector_agent import LanguageDetectorAgent
from .structure_agent import StructureGeneratorAgent
from .organizer_agent import OrganizerAgent
from .validator_agent import ValidatorAgent

class CodeOrganizationOrchestrator:
    def __init__(self):
        self.scanner = ScannerAgent()
        self.detector = LanguageDetectorAgent()
        self.structure_gen = StructureGeneratorAgent()
        self.organizer = OrganizerAgent()
        self.validator = ValidatorAgent()
    
    def orchestrate(self, source_path: str, target_path: str = None) -> Dict:
        """
        Orchestrate multi-agent workflow:
        ZIP/Repo → Scanner → Detector → Structure → Organizer → Validator → Output
        """
        source = Path(source_path)
        if not target_path:
            target_path = source.parent / f"{source.name}_organized"
        target = Path(target_path)
        target.mkdir(exist_ok=True)
        
        # Agent 1: Scanner - Scan files and metadata
        scan_data = self.scanner.scan(source)
        
        # Agent 2: Detector - Identify languages/frameworks
        detection = self.detector.detect(scan_data)
        
        # Agent 3: Structure Generator - Select best-practice templates
        structure = self.structure_gen.generate(detection)
        
        # Create directories
        self._create_dirs(target, structure)
        
        # Agent 4: Organizer - Move files safely
        organized_files = self.organizer.organize(scan_data, target, detection)
        
        # Agent 5: Validator - Ensure nothing is broken
        validation = self.validator.validate(target, detection)
        
        # Generate tree
        tree = self._generate_tree(target)
        
        return {
            'source_path': str(source),
            'organized_path': str(target),
            'files_organized': len(organized_files),
            'detected_languages': detection['languages'],
            'detected_frameworks': detection['frameworks'],
            'structure_applied': structure,
            'validation': validation,
            'folder_tree': tree,
            'organized_files': organized_files[:100]
        }
    
    def _create_dirs(self, target: Path, structure: Dict):
        """Create directory structure"""
        for main_dir, sub_dirs in structure.items():
            main_path = target / main_dir
            main_path.mkdir(parents=True, exist_ok=True)
            if isinstance(sub_dirs, list):
                for sub_dir in sub_dirs:
                    (target / main_dir / sub_dir).mkdir(parents=True, exist_ok=True)
    
    def _generate_tree(self, path: Path, prefix: str = '', max_depth: int = 3, depth: int = 0) -> str:
        """Generate folder tree"""
        if depth >= max_depth:
            return ''
        
        tree = []
        items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))[:30]
        
        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            tree.append(f"{prefix}{'`-- ' if is_last else '|-- '}{item.name}{'/' if item.is_dir() else ''}")
            
            if item.is_dir() and depth < max_depth - 1:
                tree.append(self._generate_tree(item, prefix + ('    ' if is_last else '|   '), max_depth, depth + 1))
        
        return '\n'.join(filter(None, tree))
