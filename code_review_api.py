"""Code Review API - Returns evaluation scores without code"""
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from pathlib import Path
import tempfile
import shutil
import zipfile
import os
from typing import Optional
from src.analyzer import Analyzer
from src.scanner import Scanner

try:
    from git import Repo
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False
    Repo = None

app = FastAPI(title="Code Review API")

class PathReviewRequest(BaseModel):
    source: str
    source_type: str  # "path", "repository", or "zip"

class CodeReviewResponse(BaseModel):
    syntax_score: int
    code_quality_score: int
    reusability_score: int
    maintainability_score: int
    security_score: int
    final_score: float
    grade: str
    strengths: list[str]
    issues: list[str]
    improvements: list[str]

@app.post("/review", response_model=CodeReviewResponse)
async def review_code_unified(request: PathReviewRequest = None, file: UploadFile = File(None)):
    """Review code from path, repository, or ZIP file"""
    temp_dir = None
    target_path = None
    
    try:
        # Handle ZIP file upload
        if file:
            if not file.filename.endswith('.zip'):
                raise HTTPException(400, "Only ZIP files supported")
            
            temp_dir = tempfile.mkdtemp()
            zip_path = Path(temp_dir) / file.filename
            
            with open(zip_path, 'wb') as f:
                f.write(await file.read())
            
            target_path = Path(temp_dir) / 'code'
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(target_path)
        
        # Handle path or repository
        elif request:
            if request.source_type == "repository":
                if not GIT_AVAILABLE:
                    raise HTTPException(500, "GitPython not installed")
                
                temp_dir = tempfile.mkdtemp()
                Repo.clone_from(request.source, temp_dir, depth=1)
                target_path = Path(temp_dir)
            
            elif request.source_type == "path":
                target_path = Path(request.source)
                if not target_path.exists():
                    raise HTTPException(404, "Path not found")
            
            else:
                raise HTTPException(400, "Invalid source_type. Use: path, repository, or zip")
        
        else:
            raise HTTPException(400, "Provide either file upload or request body")
        
        # Scan and analyze
        scanner = Scanner()
        analyzer = Analyzer(force_rescan=True)
        files = scanner.scan(target_path)
        
        all_issues = []
        for file_path in files[:50]:
            issues = analyzer.analyze(file_path)
            all_issues.extend(issues)
        
        scores = _calculate_scores(all_issues, len(files))
        
        return CodeReviewResponse(
            syntax_score=scores['syntax'],
            code_quality_score=scores['quality'],
            reusability_score=scores['reusability'],
            maintainability_score=scores['maintainability'],
            security_score=scores['security'],
            final_score=scores['final'],
            grade=scores['grade'],
            strengths=_extract_strengths(all_issues, files),
            issues=_extract_issues(all_issues),
            improvements=_generate_improvements(all_issues)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)

def _calculate_scores(issues, file_count):
    """Calculate scores based on issues found"""
    syntax_issues = len([i for i in issues if i['type'] in ['SyntaxError', 'FileError']])
    quality_issues = len([i for i in issues if i['type'] in ['CodeQuality', 'StyleIssue', 'BareExcept']])
    security_issues = len([i for i in issues if i['type'] == 'SecurityIssue'])
    maintainability_issues = len([i for i in issues if i['type'] in ['EmptyFunction', 'PerformanceIssue']])
    reusability_issues = len([i for i in issues if i['type'] in ['ImportIssue', 'DuplicateException']])
    
    syntax = max(0, 100 - (syntax_issues * 10))
    quality = max(0, 100 - (quality_issues * 5))
    security = max(0, 100 - (security_issues * 15))
    maintainability = max(0, 100 - (maintainability_issues * 8))
    reusability = max(0, 100 - (reusability_issues * 7))
    
    final = (syntax * 0.20) + (quality * 0.25) + (reusability * 0.20) + (maintainability * 0.20) + (security * 0.15)
    
    if final >= 90: grade = "A+"
    elif final >= 80: grade = "A"
    elif final >= 70: grade = "B"
    elif final >= 60: grade = "C"
    else: grade = "D"
    
    return {
        'syntax': syntax,
        'quality': quality,
        'security': security,
        'maintainability': maintainability,
        'reusability': reusability,
        'final': round(final, 2),
        'grade': grade
    }

def _extract_strengths(issues, files):
    """Extract code strengths"""
    strengths = []
    if len(issues) < 10:
        strengths.append("Low issue count indicates good code quality")
    if not any(i['type'] == 'SecurityIssue' for i in issues):
        strengths.append("No security vulnerabilities detected")
    if not any(i['type'] == 'SyntaxError' for i in issues):
        strengths.append("All files have valid syntax")
    if len(files) > 5:
        strengths.append("Well-structured multi-file project")
    return strengths or ["Code is functional"]

def _extract_issues(issues):
    """Extract key issues"""
    return [f"{i['type']}: {i['message']} (line {i['line']})" for i in issues[:20]]

def _generate_improvements(issues):
    """Generate improvement suggestions"""
    improvements = []
    issue_types = set(i['type'] for i in issues)
    
    if 'SecurityIssue' in issue_types:
        improvements.append("Address security vulnerabilities immediately")
    if 'BareExcept' in issue_types:
        improvements.append("Specify exception types in except clauses")
    if 'StyleIssue' in issue_types:
        improvements.append("Run code formatter (black/prettier)")
    if 'ComparisonBug' in issue_types:
        improvements.append("Use proper comparison operators")
    
    return improvements or ["Continue following best practices"]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
