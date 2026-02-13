"""Language Detector Agent - Identifies languages and frameworks"""
from collections import Counter
from typing import Dict, List

class LanguageDetectorAgent:
    def __init__(self):
        self.language_extensions = {
            'python': ['.py', '.pyx', '.pyd'],
            'javascript': ['.js', '.jsx', '.mjs'],
            'typescript': ['.ts', '.tsx'],
            'java': ['.java', '.class', '.jar'],
            'csharp': ['.cs', '.csx'],
            'cpp': ['.cpp', '.cc', '.cxx', '.h', '.hpp'],
            'go': ['.go'],
            'rust': ['.rs'],
            'php': ['.php'],
            'ruby': ['.rb'],
            'swift': ['.swift'],
            'kotlin': ['.kt', '.kts'],
            'scala': ['.scala'],
        }
        
        self.framework_indicators = {
            'django': ['manage.py', 'settings.py', 'wsgi.py'],
            'flask': ['app.py', 'application.py'],
            'fastapi': ['main.py', 'api.py'],
            'react': ['package.json', 'App.jsx', 'App.tsx'],
            'angular': ['angular.json'],
            'vue': ['vue.config.js', 'App.vue'],
            'spring': ['pom.xml', 'build.gradle'],
            'springboot': ['application.properties', 'application.yml'],
            'dotnet': ['.csproj', 'Program.cs'],
            'express': ['app.js', 'server.js'],
            'laravel': ['artisan', 'composer.json'],
        }
    
    def detect(self, scan_data: Dict) -> Dict:
        """Detect languages and frameworks from scan data"""
        extensions = scan_data['extensions']
        filenames = scan_data['filenames']
        
        # Detect languages
        lang_counts = Counter()
        for ext in extensions:
            for lang, exts in self.language_extensions.items():
                if ext in exts:
                    lang_counts[lang] += 1
        
        detected_languages = [lang for lang, _ in lang_counts.most_common()]
        
        # Detect frameworks
        detected_frameworks = []
        filenames_str = ' '.join(filenames)
        for framework, indicators in self.framework_indicators.items():
            if any(indicator.lower() in filenames_str for indicator in indicators):
                detected_frameworks.append(framework)
        
        return {
            'languages': detected_languages,
            'frameworks': detected_frameworks,
            'primary_language': detected_languages[0] if detected_languages else 'unknown'
        }
