"""Expert Code Organization Agent"""
import os
import shutil
from pathlib import Path
from typing import Dict, List, Set
from collections import Counter

class CodeOrganizer:
    def __init__(self):
        # Language detection patterns
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
            'html': ['.html', '.htm'],
            'css': ['.css', '.scss', '.sass', '.less'],
            'sql': ['.sql'],
            'shell': ['.sh', '.bash'],
        }
        
        # Framework detection patterns
        self.framework_indicators = {
            'django': ['manage.py', 'settings.py', 'wsgi.py'],
            'flask': ['app.py', 'application.py'],
            'fastapi': ['main.py', 'api.py'],
            'react': ['package.json', 'src/App.jsx', 'src/App.tsx'],
            'angular': ['angular.json', 'src/app'],
            'vue': ['vue.config.js', 'src/App.vue'],
            'spring': ['pom.xml', 'build.gradle', 'src/main/java'],
            'springboot': ['pom.xml', 'application.properties', 'application.yml', '@SpringBootApplication'],
            'dotnet': ['.csproj', 'Program.cs'],
            'express': ['package.json', 'app.js', 'server.js'],
            'laravel': ['artisan', 'composer.json', 'app/Http'],
        }
    
    def organize_project(self, source_path: str, target_path: str = None) -> Dict:
        """Expert Code Organization - Detect languages and apply industry standards"""
        source = Path(source_path)
        if not target_path:
            target_path = source.parent / f"{source.name}_organized"
        
        target = Path(target_path)
        target.mkdir(exist_ok=True)
        
        # Step 1: Detect languages and frameworks
        detection = self._detect_languages_and_frameworks(source)
        
        # Step 2: Generate appropriate structure
        structure = self._generate_structure(detection)
        
        # Step 3: Create directories
        self._create_directories(target, structure)
        
        # Step 4: Organize files
        organized_files = self._organize_files(source, target, detection)
        
        # Step 5: Create package files
        self._create_package_files(target, detection)
        
        # Step 6: Generate folder tree
        folder_tree = self._generate_tree(target)
        
        return {
            'source_path': str(source),
            'organized_path': str(target),
            'files_organized': len(organized_files),
            'detected_languages': detection['languages'],
            'detected_frameworks': detection['frameworks'],
            'structure_applied': structure,
            'folder_tree': folder_tree,
            'organized_files': organized_files[:100]  # Limit output
        }
    
    def _detect_languages_and_frameworks(self, source: Path) -> Dict:
        """Detect all languages and frameworks in the project"""
        extensions = []
        files = []
        
        for file_path in source.rglob('*'):
            if file_path.is_file() and not self._should_ignore(file_path):
                extensions.append(file_path.suffix.lower())
                files.append(file_path.name.lower())
        
        # Detect languages
        lang_counts = Counter()
        for ext in extensions:
            for lang, exts in self.language_extensions.items():
                if ext in exts:
                    lang_counts[lang] += 1
        
        detected_languages = [lang for lang, _ in lang_counts.most_common()]
        
        # Detect frameworks
        detected_frameworks = []
        for framework, indicators in self.framework_indicators.items():
            if any(indicator.lower() in ' '.join(files) for indicator in indicators):
                detected_frameworks.append(framework)
        
        return {
            'languages': detected_languages,
            'frameworks': detected_frameworks,
            'primary_language': detected_languages[0] if detected_languages else 'unknown'
        }
    
    def _generate_structure(self, detection: Dict) -> Dict:
        """Generate industry-standard structure based on detected languages/frameworks"""
        primary = detection['primary_language']
        frameworks = detection['frameworks']
        
        # Python structures
        if primary == 'python':
            if 'django' in frameworks:
                return self._django_structure()
            elif 'flask' in frameworks or 'fastapi' in frameworks:
                return self._flask_fastapi_structure()
            else:
                return self._python_generic_structure()
        
        # JavaScript/TypeScript structures
        elif primary in ['javascript', 'typescript']:
            if 'react' in frameworks:
                return self._react_structure()
            elif 'angular' in frameworks:
                return self._angular_structure()
            elif 'vue' in frameworks:
                return self._vue_structure()
            elif 'express' in frameworks:
                return self._express_structure()
            else:
                return self._js_generic_structure()
        
        # Java structures
        elif primary == 'java':
            if 'spring' in frameworks or 'springboot' in frameworks:
                return self._spring_structure()
            else:
                return self._java_generic_structure()
        
        # C# structures
        elif primary == 'csharp':
            return self._dotnet_structure()
        
        # PHP structures
        elif primary == 'php':
            if 'laravel' in frameworks:
                return self._laravel_structure()
            else:
                return self._php_generic_structure()
        
        # Generic structure for unknown languages
        else:
            return self._generic_structure()
    
    def _django_structure(self) -> Dict:
        return {
            'project': ['settings', 'urls', 'wsgi', 'asgi'],
            'apps': ['models', 'views', 'serializers', 'admin', 'migrations'],
            'static': ['css', 'js', 'images'],
            'templates': [],
            'tests': [],
            'docs': [],
            'requirements': []
        }
    
    def _flask_fastapi_structure(self) -> Dict:
        return {
            'app': ['api', 'models', 'services', 'schemas', 'core', 'utils'],
            'tests': [],
            'static': ['css', 'js', 'images'],
            'templates': [],
            'config': [],
            'docs': [],
            'requirements': []
        }
    
    def _python_generic_structure(self) -> Dict:
        return {
            'src': ['core', 'utils', 'services'],
            'tests': [],
            'docs': [],
            'config': [],
            'requirements': []
        }
    
    def _react_structure(self) -> Dict:
        return {
            'src': ['components', 'pages', 'hooks', 'services', 'utils', 'assets', 'styles'],
            'public': [],
            'tests': [],
            'docs': []
        }
    
    def _angular_structure(self) -> Dict:
        return {
            'src': ['app', 'assets', 'environments'],
            'app': ['components', 'services', 'models', 'guards', 'interceptors'],
            'tests': [],
            'docs': []
        }
    
    def _vue_structure(self) -> Dict:
        return {
            'src': ['components', 'views', 'router', 'store', 'assets', 'utils'],
            'public': [],
            'tests': [],
            'docs': []
        }
    
    def _express_structure(self) -> Dict:
        return {
            'src': ['controllers', 'models', 'routes', 'middleware', 'services', 'utils'],
            'public': ['css', 'js', 'images'],
            'views': [],
            'tests': [],
            'config': [],
            'docs': []
        }
    
    def _js_generic_structure(self) -> Dict:
        return {
            'src': ['components', 'utils', 'services'],
            'public': ['css', 'js', 'images'],
            'tests': [],
            'docs': []
        }
    
    def _spring_structure(self) -> Dict:
        """Spring Boot standard structure"""
        return {
            'src/main/java': ['controller', 'service', 'repository', 'model', 'dto', 'config', 'exception', 'util'],
            'src/main/resources': ['static', 'templates', 'application.properties'],
            'src/test/java': ['controller', 'service', 'repository'],
            'docs': []
        }
    
    def _java_generic_structure(self) -> Dict:
        return {
            'src/main/java': ['com/app'],
            'src/test/java': [],
            'resources': [],
            'docs': []
        }
    
    def _dotnet_structure(self) -> Dict:
        return {
            'Controllers': [],
            'Models': [],
            'Services': [],
            'Data': [],
            'Views': [],
            'wwwroot': ['css', 'js', 'images'],
            'Tests': [],
            'Docs': []
        }
    
    def _laravel_structure(self) -> Dict:
        return {
            'app': ['Http/Controllers', 'Models', 'Services'],
            'resources': ['views', 'css', 'js'],
            'routes': [],
            'database': ['migrations', 'seeders'],
            'tests': [],
            'public': [],
            'config': [],
            'docs': []
        }
    
    def _php_generic_structure(self) -> Dict:
        return {
            'src': ['Controllers', 'Models', 'Services'],
            'public': ['css', 'js', 'images'],
            'views': [],
            'tests': [],
            'config': [],
            'docs': []
        }
    
    def _generic_structure(self) -> Dict:
        return {
            'src': ['core', 'utils'],
            'assets': ['css', 'js', 'images'],
            'tests': [],
            'config': [],
            'docs': []
        }
    
    def _create_directories(self, target: Path, structure: Dict):
        """Create directory structure"""
        for main_dir, sub_dirs in structure.items():
            main_path = target / main_dir
            main_path.mkdir(parents=True, exist_ok=True)
            if isinstance(sub_dirs, list):
                for sub_dir in sub_dirs:
                    (target / main_dir / sub_dir).mkdir(parents=True, exist_ok=True)
    
    def _organize_files(self, source: Path, target: Path, detection: Dict) -> List[Dict]:
        """Organize files into appropriate folders"""
        organized_files = []
        for file_path in source.rglob('*'):
            if file_path.is_file() and not self._should_ignore(file_path):
                new_location = self._categorize_file(file_path, target, detection)
                if new_location:
                    new_location.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, new_location)
                    organized_files.append({
                        'original': str(file_path.relative_to(source)),
                        'organized': str(new_location),
                        'language': self._detect_file_language(file_path)
                    })
        return organized_files
    
    def _detect_file_language(self, file_path: Path) -> str:
        """Detect language of a single file"""
        ext = file_path.suffix.lower()
        for lang, exts in self.language_extensions.items():
            if ext in exts:
                return lang
        return 'unknown'
    
    def _should_ignore(self, file_path: Path) -> bool:
        """Check if file should be ignored"""
        ignore_patterns = {
            '__pycache__', '.git', 'node_modules', '.venv', 'venv', 
            'env', 'dist', 'build', '.idea', '.vscode', '.backup_'
        }
        return any(pattern in file_path.parts for pattern in ignore_patterns) or file_path.name.startswith('.')
    
    def _generate_tree(self, path: Path, prefix: str = '', max_depth: int = 4, current_depth: int = 0) -> str:
        """Generate folder tree visualization (Windows-safe)"""
        if current_depth >= max_depth:
            return ''
        
        tree = []
        items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
        
        for i, item in enumerate(items[:50]):  # Limit to 50 items
            is_last = i == len(items) - 1
            current_prefix = '`-- ' if is_last else '|-- '
            tree.append(f"{prefix}{current_prefix}{item.name}{'/' if item.is_dir() else ''}")
            
            if item.is_dir() and current_depth < max_depth - 1:
                extension = '    ' if is_last else '|   '
                tree.append(self._generate_tree(item, prefix + extension, max_depth, current_depth + 1))
        
        return '\n'.join(filter(None, tree))
    
    def _create_package_files(self, target: Path, detection: Dict):
        """Create package initialization files"""
        primary = detection['primary_language']
        
        if primary == 'python':
            self._create_init_files(target)
        elif primary in ['javascript', 'typescript']:
            self._create_index_files(target)
    
    def _create_index_files(self, target: Path):
        """Create index.js files for JavaScript/TypeScript"""
        for dir_path in target.rglob('*'):
            if dir_path.is_dir() and 'node_modules' not in str(dir_path):
                index_file = dir_path / 'index.js'
                if not index_file.exists() and any(dir_path.iterdir()):
                    index_file.write_text('// Auto-generated index file\n')
    
    def _categorize_file(self, file_path: Path, target: Path, detection: Dict = None) -> Path:
        """Categorize file based on name, extension, and detected language"""
        filename = file_path.name.lower()
        ext = file_path.suffix.lower()
        
        # Config files
        if ext in ['.env', '.json', '.yaml', '.yml', '.toml', '.ini', '.xml'] or 'config' in filename:
            # Spring Boot properties go to resources
            if filename in ['application.properties', 'application.yml', 'application.yaml']:
                return target / 'src/main/resources' / file_path.name
            return target / 'config' / file_path.name
        
        # Documentation
        if ext in ['.md', '.txt', '.rst', '.pdf'] or filename in ['readme.md', 'license', 'changelog.md']:
            return target / 'docs' / file_path.name
        
        # Requirements/Dependencies
        if 'requirements' in filename or filename in ['package.json', 'package-lock.json', 'yarn.lock', 'pom.xml', 'build.gradle', 'composer.json', 'Gemfile', 'Cargo.toml']:
            return target / 'requirements' / file_path.name
        
        # Test files
        if 'test' in filename or filename.startswith('test_') or ext == '.spec.js' or ext == '.test.js':
            return target / 'tests' / file_path.name
        
        # Python files
        if ext == '.py':
            if 'api' in filename or 'router' in filename or 'endpoint' in filename or 'controller' in filename:
                return target / 'app' / 'api' / file_path.name
            elif 'model' in filename or 'schema' in filename:
                return target / 'app' / 'models' / file_path.name
            elif 'service' in filename or 'agent' in filename:
                return target / 'app' / 'services' / file_path.name
            elif 'util' in filename or 'helper' in filename:
                return target / 'app' / 'utils' / file_path.name
            elif filename in ['main.py', 'app.py', 'run.py', 'manage.py']:
                return target / file_path.name
            else:
                return target / 'app' / 'core' / file_path.name
        
        # JavaScript/TypeScript files
        elif ext in ['.js', '.jsx', '.ts', '.tsx']:
            if 'component' in filename or filename.endswith('.component.js'):
                return target / 'src' / 'components' / file_path.name
            elif 'service' in filename:
                return target / 'src' / 'services' / file_path.name
            elif 'util' in filename or 'helper' in filename:
                return target / 'src' / 'utils' / file_path.name
            elif 'route' in filename or 'router' in filename:
                return target / 'src' / 'routes' / file_path.name
            elif filename in ['app.js', 'index.js', 'main.js', 'server.js']:
                return target / file_path.name
            else:
                return target / 'src' / file_path.name
        
        # HTML files
        elif ext in ['.html', '.htm']:
            if 'template' in str(file_path.parent).lower() or 'view' in str(file_path.parent).lower():
                return target / 'templates' / file_path.name
            else:
                return target / 'public' / file_path.name
        
        # CSS files
        elif ext in ['.css', '.scss', '.sass', '.less']:
            return target / 'static' / 'css' / file_path.name
        
        # Images
        elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp', '.bmp']:
            return target / 'static' / 'images' / file_path.name
        
        # Fonts
        elif ext in ['.woff', '.woff2', '.ttf', '.eot', '.otf']:
            return target / 'static' / 'fonts' / file_path.name
        
        # Java files
        elif ext in ['.java', '.class', '.jar']:
            if 'controller' in filename:
                return target / 'src/main/java' / 'controller' / file_path.name
            elif 'service' in filename:
                return target / 'src/main/java' / 'service' / file_path.name
            elif 'model' in filename or 'entity' in filename:
                return target / 'src/main/java' / 'model' / file_path.name
            elif 'repository' in filename or 'repo' in filename:
                return target / 'src/main/java' / 'repository' / file_path.name
            elif 'dto' in filename:
                return target / 'src/main/java' / 'dto' / file_path.name
            elif 'config' in filename:
                return target / 'src/main/java' / 'config' / file_path.name
            elif 'exception' in filename or 'error' in filename:
                return target / 'src/main/java' / 'exception' / file_path.name
            elif 'util' in filename or 'helper' in filename:
                return target / 'src/main/java' / 'util' / file_path.name
            else:
                return target / 'src/main/java' / file_path.name
        
        # C# files
        elif ext == '.cs':
            if 'controller' in filename:
                return target / 'Controllers' / file_path.name
            elif 'model' in filename:
                return target / 'Models' / file_path.name
            elif 'service' in filename:
                return target / 'Services' / file_path.name
            else:
                return target / 'src' / file_path.name
        
        # PHP files
        elif ext == '.php':
            if 'controller' in filename:
                return target / 'app' / 'Http/Controllers' / file_path.name
            elif 'model' in filename:
                return target / 'app' / 'Models' / file_path.name
            else:
                return target / 'src' / file_path.name
        
        # SQL files
        elif ext == '.sql':
            return target / 'database' / file_path.name
        
        # Default: place in src
        else:
            return target / 'src' / file_path.name
    
    def _create_init_files(self, target: Path):
        """Create __init__.py files for Python packages"""
        init_content = '"""Auto-generated package file"""'
        
        # Create __init__.py in all Python package directories
        python_dirs = [
            target / 'app',
            target / 'app' / 'api',
            target / 'app' / 'models', 
            target / 'app' / 'services',
            target / 'app' / 'core',
            target / 'app' / 'utils',
            target / 'tests'
        ]
        
        for dir_path in python_dirs:
            if dir_path.exists():
                init_file = dir_path / '__init__.py'
                if not init_file.exists():
                    init_file.write_text(init_content)