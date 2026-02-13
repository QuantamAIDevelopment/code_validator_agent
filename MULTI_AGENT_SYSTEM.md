# Multi-Agent Code Organization System

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR                            │
│  Coordinates workflow between specialized agents             │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Scanner    │───▶│   Detector   │───▶│  Structure   │
│    Agent     │    │    Agent     │    │  Generator   │
└──────────────┘    └──────────────┘    └──────────────┘
                                                │
                                                ▼
                                        ┌──────────────┐
                                        │  Organizer   │
                                        │    Agent     │
                                        └──────────────┘
                                                │
                                                ▼
                                        ┌──────────────┐
                                        │  Validator   │
                                        │    Agent     │
                                        └──────────────┘
```

## Agents

### 1. Scanner Agent
**Purpose**: Scans files and extracts metadata

**Responsibilities**:
- Traverse directory structure
- Collect file paths, extensions, names
- Filter ignored patterns (.git, node_modules, etc.)
- Return scan metadata

**Output**:
```python
{
    'files': [Path objects],
    'extensions': ['.py', '.js', ...],
    'filenames': ['app.py', 'index.js', ...],
    'total_files': 150
}
```

### 2. Language Detector Agent
**Purpose**: Identifies programming languages and frameworks

**Responsibilities**:
- Analyze file extensions
- Count language occurrences
- Detect framework indicators
- Determine primary language

**Output**:
```python
{
    'languages': ['python', 'javascript'],
    'frameworks': ['fastapi', 'react'],
    'primary_language': 'python'
}
```

### 3. Structure Generator Agent
**Purpose**: Selects best-practice folder templates

**Responsibilities**:
- Match language/framework to template
- Generate industry-standard structure
- Support multiple frameworks per language

**Output**:
```python
{
    'app': ['api', 'models', 'services'],
    'tests': [],
    'docs': []
}
```

### 4. Organizer Agent
**Purpose**: Moves files safely to new structure

**Responsibilities**:
- Categorize files by name/extension
- Copy files to appropriate folders
- Preserve file metadata
- Track all moves

**Output**:
```python
[
    {'original': '/old/path/file.py', 'organized': '/new/app/api/file.py'},
    ...
]
```

### 5. Validator Agent
**Purpose**: Ensures imports/builds are not broken

**Responsibilities**:
- Check for main files
- Detect empty directories
- Validate structure completeness
- Report issues and warnings

**Output**:
```python
{
    'valid': True,
    'issues': [],
    'warnings': ['Empty directory: utils/']
}
```

## Workflow

```
ZIP/Repo Input
      │
      ▼
┌─────────────┐
│   Scanner   │  Scans all files, extracts metadata
└─────────────┘
      │
      ▼
┌─────────────┐
│  Detector   │  Identifies languages: Python, Java, JS
└─────────────┘  Detects frameworks: FastAPI, Spring, React
      │
      ▼
┌─────────────┐
│  Structure  │  Selects template: FastAPI structure
└─────────────┘  Generates: app/, tests/, docs/
      │
      ▼
┌─────────────┐
│  Organizer  │  Moves files to correct folders
└─────────────┘  api.py → app/api/, model.py → app/models/
      │
      ▼
┌─────────────┐
│  Validator  │  Checks: All files moved? Imports valid?
└─────────────┘  Reports: warnings, issues
      │
      ▼
  Organized Output
```

## Security

### Environment Secrets
- SSH keys stored in environment variables
- Never logged or exposed in responses
- Temporary files auto-deleted

### Ephemeral Storage
- All operations in temp directories
- Automatic cleanup on completion
- No persistent storage of user code

### Credential Handling
```python
# ✅ Secure
ssh_key = os.getenv('SSH_KEY')
temp_key = tempfile.mkstemp()
# Use key
os.unlink(temp_key)  # Delete immediately

# ❌ Insecure
ssh_key = "hardcoded-key"  # Never do this
```

## API Usage

### Endpoint: `/zip-organize`
```bash
curl -X POST http://localhost:8001/zip-organize \
  -F "file=@code.zip"
```

**Response**:
```json
{
  "status": "success",
  "detected_languages": ["python", "javascript"],
  "detected_frameworks": ["fastapi"],
  "validation": {
    "valid": true,
    "issues": [],
    "warnings": []
  },
  "folder_tree": "app/\n|-- api/\n|-- models/\n...",
  "download_url": "http://localhost:8001/download/organized_123.zip"
}
```

### Endpoint: `/private-repo-organize`
```bash
curl -X POST http://localhost:8001/private-repo-organize \
  -H "Content-Type: application/json" \
  -d '{
    "ssh_repo_url": "git@github.com:user/repo.git",
    "ssh_key_content": "$SSH_KEY",
    "push_changes": true,
    "branch": "organize"
  }'
```

## Benefits

### Separation of Concerns
- Each agent has single responsibility
- Easy to test and maintain
- Can be replaced independently

### Scalability
- Agents can run in parallel (future)
- Easy to add new agents
- Modular architecture

### Reliability
- Validation ensures quality
- Clear error handling per agent
- Rollback capability

### Flexibility
- Support any language/framework
- Easy to add new templates
- Customizable per agent

## File Structure

```
src/agents/
├── __init__.py
├── orchestrator.py       # Coordinates all agents
├── scanner_agent.py      # Scans files
├── detector_agent.py     # Detects languages
├── structure_agent.py    # Generates templates
├── organizer_agent.py    # Moves files
└── validator_agent.py    # Validates output
```

## Future Enhancements

1. **Parallel Processing**: Run agents concurrently
2. **ML Detection**: Use ML for better framework detection
3. **Import Fixer**: Auto-fix broken imports
4. **Rollback**: Undo organization if validation fails
5. **Custom Templates**: User-defined structures
6. **Metrics**: Track organization quality scores
