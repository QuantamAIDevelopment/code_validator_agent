"""Structure Generator Agent - Selects best-practice folder templates"""
from typing import Dict

class StructureGeneratorAgent:
    def generate(self, detection: Dict) -> Dict:
        """Generate industry-standard structure based on detection"""
        primary = detection['primary_language']
        frameworks = detection['frameworks']
        
        if primary == 'python':
            if 'django' in frameworks:
                return {'project': ['settings', 'urls', 'wsgi'], 'apps': ['models', 'views'], 'static': [], 'tests': [], 'docs': []}
            elif 'flask' in frameworks or 'fastapi' in frameworks:
                return {'app': ['api', 'models', 'services', 'core'], 'tests': [], 'static': [], 'config': [], 'docs': []}
            return {'src': ['core', 'utils'], 'tests': [], 'docs': [], 'config': []}
        
        elif primary in ['javascript', 'typescript']:
            if 'react' in frameworks:
                return {'src': ['components', 'pages', 'hooks', 'services', 'utils'], 'public': [], 'tests': []}
            elif 'angular' in frameworks:
                return {'src': ['app', 'assets'], 'tests': []}
            elif 'vue' in frameworks:
                return {'src': ['components', 'views', 'router', 'store'], 'public': [], 'tests': []}
            elif 'express' in frameworks:
                return {'src': ['controllers', 'models', 'routes', 'services'], 'public': [], 'tests': []}
            return {'src': ['components', 'utils'], 'public': [], 'tests': []}
        
        elif primary == 'java':
            if 'spring' in frameworks or 'springboot' in frameworks:
                return {'src/main/java': ['controller', 'service', 'repository', 'model', 'dto', 'config'], 
                        'src/main/resources': ['static'], 'src/test/java': [], 'docs': []}
            return {'src/main/java': [], 'src/test/java': [], 'docs': []}
        
        elif primary == 'csharp':
            return {'Controllers': [], 'Models': [], 'Services': [], 'Views': [], 'wwwroot': [], 'Tests': []}
        
        elif primary == 'php':
            if 'laravel' in frameworks:
                return {'app': ['Http/Controllers', 'Models'], 'resources': [], 'routes': [], 'tests': []}
            return {'src': ['Controllers', 'Models'], 'public': [], 'tests': []}
        
        return {'src': ['core'], 'tests': [], 'docs': []}
