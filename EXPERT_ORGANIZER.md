# Expert Code Organization Agent

## Overview
AI-powered code organization agent that automatically detects programming languages, frameworks, and applies industry-standard folder structures.

## Features

### 🔍 Language Detection
Automatically detects:
- Python, JavaScript, TypeScript, Java, C#, C++, Go, Rust, PHP, Ruby, Swift, Kotlin, Scala
- HTML, CSS, SQL, Shell scripts

### 🎯 Framework Detection
Recognizes popular frameworks:
- **Python**: Django, Flask, FastAPI
- **JavaScript**: React, Angular, Vue, Express
- **Java**: Spring, Spring Boot
- **C#**: .NET
- **PHP**: Laravel

### 📁 Industry-Standard Structures

#### Python (Django)
```
project/
├── project/
│   ├── settings/
│   ├── urls/
│   └── wsgi/
├── apps/
│   ├── models/
│   ├── views/
│   ├── serializers/
│   └── migrations/
├── static/
├── templates/
├── tests/
└── docs/
```

#### Python (Flask/FastAPI)
```
app/
├── api/
├── models/
├── services/
├── schemas/
├── core/
└── utils/
tests/
static/
templates/
config/
docs/
requirements/
```

#### React
```
src/
├── components/
├── pages/
├── hooks/
├── services/
├── utils/
├── assets/
└── styles/
public/
tests/
docs/
```

#### Spring Boot (Java)
```
src/
├── main/
│   ├── java/
│   │   ├── controller/
│   │   ├── service/
│   │   ├── repository/
│   │   ├── model/
│   │   ├── dto/
│   │   ├── config/
│   │   ├── exception/
│   │   └── util/
│   └── resources/
│       ├── static/
│       ├── templates/
│       └── application.properties
└── test/
    └── java/
        ├── controller/
        ├── service/
        └── repository/
docs/
```

#### .NET (C#)
```
Controllers/
Models/
Services/
Data/
Views/
wwwroot/
├── css/
├── js/
└── images/
Tests/
Docs/
```

## API Endpoints

### 1. `/zip-organize` - Organize ZIP File

Upload a ZIP file containing source code. The agent will:
1. Extract and analyze the code
2. Detect all languages and frameworks
3. Apply appropriate industry-standard structure
4. Return organized code as downloadable ZIP

**Request:**
```bash
curl -X POST http://localhost:8001/zip-organize \
  -F "file=@your-code.zip"
```

**Response:**
```json
{
  "status": "success",
  "message": "Code organized using industry standards - 45 files organized",
  "filename": "your-code.zip",
  "download_url": "http://localhost:8001/download/organized_1234567890.zip",
  "detected_languages": ["python", "javascript", "html"],
  "detected_frameworks": ["fastapi", "react"],
  "folder_tree": "src/\n├── components/\n├── services/\n...",
  "summary": {
    "files_organized": 45,
    "languages": "python, javascript, html",
    "frameworks": "fastapi, react"
  }
}
```

### 2. `/private-repo-organize` - Organize Private Repository

Access a private Git repository via SSH, organize it, and optionally push changes back.

**Request:**
```bash
curl -X POST http://localhost:8001/private-repo-organize \
  -H "Content-Type: application/json" \
  -d '{
    "ssh_repo_url": "git@github.com:username/repo.git",
    "ssh_key_content": "-----BEGIN OPENSSH PRIVATE KEY-----\n...\n-----END OPENSSH PRIVATE KEY-----",
    "auto_fix": false,
    "push_changes": true,
    "branch": "organize-code"
  }'
```

**Response:**
```json
{
  "status": "success",
  "message": "Code organized using industry standards - 67 files organized and pushed",
  "detected_languages": ["java", "javascript"],
  "detected_frameworks": ["spring"],
  "folder_tree": "src/\n├── main/\n│   ├── java/\n...",
  "pushed": true,
  "branch": "organize-code",
  "summary": {
    "files_organized": 67,
    "primary_language": "java",
    "frameworks": "spring"
  }
}
```

## Rules & Guarantees

### ✅ What It Does
- Detects all programming languages in the project
- Identifies frameworks automatically
- Applies industry-standard folder structures
- Preserves all files (no deletion)
- Maintains file contents exactly (no code modification)
- Supports mixed-language repositories
- Creates appropriate package files (__init__.py, index.js)
- Generates visual folder tree

### ❌ What It Doesn't Do
- Modify code contents
- Delete any files
- Change file names
- Expose secrets or credentials
- Break relative imports (best effort to maintain)

## File Categorization Logic

### By Purpose
- **Controllers/API**: Files with 'controller', 'api', 'router', 'endpoint' in name
- **Models/Entities**: Files with 'model', 'schema', 'entity' in name
- **Services**: Files with 'service', 'agent' in name
- **Repositories**: Files with 'repository', 'repo' in name
- **DTOs**: Files with 'dto' in name (Data Transfer Objects)
- **Utils**: Files with 'util', 'helper' in name
- **Exceptions**: Files with 'exception', 'error' in name
- **Config**: Files with 'config' in name or .properties, .yml extensions
- **Tests**: Files with 'test' in name or .spec/.test extensions
- **Docs**: .md, .txt, .rst, .pdf files
- **Assets**: Images, fonts, CSS files

### By Extension
- **Python (.py)**: Organized into app/api, app/models, app/services, etc.
- **JavaScript (.js, .jsx)**: Organized into src/components, src/services, etc.
- **TypeScript (.ts, .tsx)**: Same as JavaScript
- **Java (.java)**: Organized into src/main/java/controller, service, repository, model, dto, config, exception, util
- **C# (.cs)**: Organized into Controllers, Models, Services, etc.
- **HTML (.html)**: Placed in templates/ or public/
- **CSS (.css, .scss)**: Placed in static/css/
- **SQL (.sql)**: Placed in database/
- **Properties (.properties, .yml)**: Spring Boot configs go to src/main/resources/

## Mixed-Language Projects

For projects with multiple languages, the agent:
1. Detects the primary language (most files)
2. Applies the primary language's structure
3. Places secondary language files in appropriate folders
4. Maintains logical separation

Example: Python backend + React frontend
```
app/              # Python backend
├── api/
├── models/
└── services/
src/              # React frontend
├── components/
├── pages/
└── hooks/
static/           # Shared assets
tests/            # All tests
docs/             # All documentation
```

## Security

- SSH keys are stored temporarily and deleted immediately after use
- No credentials are logged or exposed
- Temporary directories are cleaned up automatically
- File permissions are preserved
- No external network calls except Git operations

## Best Practices

1. **Before organizing**: Commit your current code to Git
2. **Review changes**: Check the folder_tree in the response
3. **Test imports**: Verify relative imports still work
4. **Update configs**: Update paths in configuration files if needed
5. **Run tests**: Ensure tests pass after reorganization

## Limitations

- Maximum file size: 500MB
- Timeout: 120 seconds for large projects
- Ignores: node_modules, .git, __pycache__, venv, dist, build
- Best for: Projects with < 1000 files

## Examples

### Organize a Python Flask Project
```bash
curl -X POST http://localhost:8001/zip-organize \
  -F "file=@flask-app.zip"
```

Result: Flask structure with app/api, app/models, app/services

### Organize a React Project
```bash
curl -X POST http://localhost:8001/zip-organize \
  -F "file=@react-app.zip"
```

Result: React structure with src/components, src/pages, src/hooks

### Organize and Push to GitHub
```bash
curl -X POST http://localhost:8001/private-repo-organize \
  -H "Content-Type: application/json" \
  -d '{
    "ssh_repo_url": "git@github.com:user/repo.git",
    "ssh_key_content": "YOUR_SSH_KEY",
    "push_changes": true,
    "branch": "refactor/organize-structure"
  }'
```

Result: Organized code pushed to new branch

## Troubleshooting

### Issue: Wrong structure applied
**Solution**: The agent uses the primary language. If detection is wrong, manually specify structure.

### Issue: Imports broken after organization
**Solution**: Update relative import paths in your code.

### Issue: SSH authentication failed
**Solution**: Ensure SSH key format is correct and has repository access.

### Issue: Files missing after organization
**Solution**: Check if files were in ignored directories (node_modules, .git, etc.)

## Support

For issues or questions:
1. Check server logs for detailed error messages
2. Verify file formats and sizes
3. Test with a small project first
4. Review the folder_tree output
