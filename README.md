# Auto Fix Agent

AI-powered code analysis and auto-fixing tool.

## Start Server

```bash
start_server.bat
```

Access Swagger UI: `http://localhost:8000/docs`

## API Endpoints

### 1. `/scan` - Scan Code (Original)
Scan local path or repository without auto-fix.

```json
{
  "source": "/path/to/code",
  "force_rescan": true
}
```

### 2. `/repo-auto-fix` - Repository Auto-Fix (New)
Clone repository and automatically fix all issues.

```json
{
  "repository_url": "https://github.com/username/repo.git",
  "force_rescan": true
}
```

### 3. `/zip-auto-fix` - ZIP File Auto-Fix (New)
Upload ZIP file, extract and automatically fix all issues.

- Upload .zip file through Swagger UI
- Automatically extracts and scans
- Returns fixed code results

### 4. `/approve-fix` - Approve Fix
### 5. `/fix-and-push` - Fix and Push
### 6. `/organize-code` - Organize Code

## CLI Usage

```bash
python main.py <target_path>
```

