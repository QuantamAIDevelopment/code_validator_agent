# Auto Fix Agent

AI-powered code analysis, auto-fixing, and expert code organization tool.

## Features

### 🔧 Auto-Fix Agent
- Detects 100+ code issues (bugs, security, quality)
- Pattern-based fixes (instant, no AI delays)
- Supports Python, JavaScript, TypeScript, HTML, CSS, Java, C++, PHP

### 📁 Expert Code Organization Agent
- Automatically detects languages and frameworks
- Applies industry-standard folder structures
- Supports Django, Flask, FastAPI, React, Angular, Vue, Spring, .NET, Laravel
- Preserves all files and contents
- No code modification during organization

## Start Server

```bash
start_server.bat
```

Access Swagger UI: `http://localhost:8001/docs`

## API Endpoints

### Auto-Fix Endpoints

#### 1. `/scan` - Scan Code Only
Scan local path or repository without auto-fix.

```json
{
  "source": "/path/to/code",
  "force_rescan": true
}
```

#### 2. `/repo-auto-fix` - Repository Auto-Fix
Clone repository and automatically fix all issues.

```json
{
  "repository_url": "https://github.com/username/repo.git",
  "force_rescan": true
}
```

#### 3. `/zip-auto-fix` - ZIP File Auto-Fix
Upload ZIP file, extract and automatically fix all issues.

- Upload .zip file through Swagger UI
- Automatically extracts and scans
- Returns fixed code as downloadable ZIP

### Expert Organization Endpoints

#### 4. `/zip-organize` - Organize ZIP File ⭐ NEW
Upload ZIP file, detect languages/frameworks, apply industry standards.

**Features:**
- Detects: Python, JavaScript, TypeScript, Java, C#, PHP, etc.
- Recognizes: Django, Flask, React, Angular, Spring, .NET, Laravel
- Applies appropriate folder structure automatically
- Returns organized code as downloadable ZIP

**Response includes:**
- Detected languages and frameworks
- Visual folder tree
- Download link for organized code

#### 5. `/private-repo-organize` - Organize Private Repository ⭐ NEW
Access private Git repo via SSH, organize, and push changes.

```json
{
  "ssh_repo_url": "git@github.com:username/repo.git",
  "ssh_key_content": "-----BEGIN OPENSSH PRIVATE KEY-----\n...\n-----END OPENSSH PRIVATE KEY-----",
  "auto_fix": false,
  "push_changes": true,
  "branch": "organize-code"
}
```

**Features:**
- Secure SSH authentication
- Language and framework detection
- Industry-standard structure application
- Optional push to new branch
- No file deletion, only reorganization

### Other Endpoints

#### 6. `/approve-fix` - Approve Fix
#### 7. `/fix-and-push` - Fix and Push
#### 8. `/code-review` - Code Quality Review
#### 9. `/private-repo-ssh` - Private Repo Auto-Fix

## CLI Usage

```bash
python main.py <target_path>
```

## Documentation

- **Expert Organizer Guide**: See [EXPERT_ORGANIZER.md](EXPERT_ORGANIZER.md)
- **Error Fixes**: See [ERROR_FIXES.md](ERROR_FIXES.md)

## Supported Structures

### Python
- Django: project/, apps/, static/, templates/
- Flask/FastAPI: app/api, app/models, app/services
- Generic: src/, tests/, docs/

### JavaScript/TypeScript
- React: src/components, src/pages, src/hooks
- Angular: src/app, src/assets, src/environments
- Vue: src/components, src/views, src/store
- Express: src/controllers, src/routes, src/middleware

### Java
- Spring/Spring Boot: src/main/java/controller, service, repository, model, dto, config, exception, util
- Generic: src/main/java, src/test/java

### C#
- .NET: Controllers/, Models/, Services/, Views/

### PHP
- Laravel: app/Http/Controllers, app/Models, resources/

## Quick Examples

### Organize a ZIP file
```bash
curl -X POST http://localhost:8001/zip-organize \
  -F "file=@your-code.zip"
```

### Organize private repository
```bash
curl -X POST http://localhost:8001/private-repo-organize \
  -H "Content-Type: application/json" \
  -d '{
    "ssh_repo_url": "git@github.com:user/repo.git",
    "ssh_key_content": "YOUR_SSH_KEY",
    "push_changes": true,
    "branch": "organize"
  }'
```

### Auto-fix repository
```bash
curl -X POST http://localhost:8001/repo-auto-fix \
  -H "Content-Type: application/json" \
  -d '{"repository_url": "https://github.com/user/repo.git"}'
```

