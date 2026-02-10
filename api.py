"""Auto Fix Agent - API Server + CLI Tool"""
import os
import sys
import tempfile
import shutil
import zipfile
import traceback
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from pydantic import BaseModel

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from git import Repo
    GIT_AVAILABLE = True
    logger.info("GitPython available")
except ImportError as e:
    GIT_AVAILABLE = False
    Repo = None
    logger.warning(f"GitPython not available: {e}")

try:
    from src.agent import AutoFixAgent
    from src.organizer import CodeOrganizer
    logger.info("Agent modules loaded successfully")
except Exception as e:
    logger.error(f"Failed to import agent modules: {e}")
    raise

# FastAPI App
app = FastAPI(title="Auto Fix Agent API")

@app.on_event("startup")
async def startup_event():
    logger.info("Auto Fix Agent API starting...")
    logger.info(f"Git available: {GIT_AVAILABLE}")

class ScanRequest(BaseModel):
    source: str
    force_rescan: bool = True

class ApproveFixRequest(BaseModel):
    fix_id: str
    approved: bool = True

class FixPushRequest(BaseModel):
    source: str
    commit_message: str = "Auto-fix applied"

class OrganizeRequest(BaseModel):
    source: str
    target: str = None
    auto_fix_after_organize: bool = True

class RepoAutoFixRequest(BaseModel):
    repository_url: str
    force_rescan: bool = True

@app.post("/scan")
async def scan_and_fix(request: ScanRequest):
    """Scan and fix code from local path or GitHub URL"""
    source = request.source.strip()
    temp_dir = None
    
    try:
        if source.startswith(('http://', 'https://')) and 'github.com' in source:
            if not GIT_AVAILABLE:
                raise HTTPException(status_code=500, detail="Git is not installed")
            temp_dir = tempfile.mkdtemp()
            Repo.clone_from(source, temp_dir)
            target_path = temp_dir
        else:
            target_path = Path(source)
            if not target_path.exists():
                raise HTTPException(status_code=404, detail="Path not found")
        
        agent = AutoFixAgent(force_rescan=request.force_rescan)
        results = agent.run(target_path, auto_fix=False)
        
        total_issues = len(results.get("issues_found", []))
        
        scan_results = {
            "status": "success",
            "message": "Scanning completed - issues found need approval",
            "path": str(target_path),
            "force_rescan": request.force_rescan,
            "summary": {
                "files_scanned": results.get("scanned_files", 0),
                "issues_found": total_issues,
                "issues_fixed": 0,
                "needs_approval": total_issues
            },
            "files_with_issues": results.get("issues_found", []),
            "fixes_applied": []
        }
        
        return scan_results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

@app.post("/repo-auto-fix")
async def repo_auto_fix(request: RepoAutoFixRequest):
    """Clone repository and auto-fix all issues"""
    temp_dir = None
    
    try:
        if not GIT_AVAILABLE:
            raise HTTPException(status_code=500, detail="GitPython library not installed. Install with: pip install gitpython")
        
        # Normalize repository URL
        repo_url = request.repository_url
        if not repo_url.startswith(('http://', 'https://')):
            repo_url = f"https://github.com/{repo_url}"
        
        temp_dir = tempfile.mkdtemp()
        logger.info(f"Cloning {repo_url}...")
        
        # Clone with depth=1 for faster cloning
        Repo.clone_from(repo_url, temp_dir, depth=1)
        logger.info(f"Cloned to {temp_dir}")
        
        logger.info("Starting scan...")
        agent = AutoFixAgent(force_rescan=request.force_rescan)
        results = agent.run(temp_dir, auto_fix=True)
        logger.info(f"Scan complete: {results.get('files_fixed', 0)} files fixed")
        
        return {
            "status": "success",
            "message": f"Repository cloned and fixed - {results.get('files_fixed', 0)} files fixed",
            "repository": repo_url,
            "summary": {
                "files_scanned": results.get("scanned_files", 0),
                "issues_found": len(results.get("issues_found", [])),
                "files_fixed": results.get("files_fixed", 0)
            },
            "issues_found": results.get("issues_found", [])[:50],  # Limit to first 50
            "fixes_applied": results.get("fixes_applied", [])[:50]  # Limit to first 50
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_detail = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Error in repo_auto_fix: {error_detail}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_detail)
    
    finally:
        if temp_dir and os.path.exists(temp_dir):
            logger.info(f"Cleaning up {temp_dir}")
            shutil.rmtree(temp_dir, ignore_errors=True)

@app.post("/zip-auto-fix")
async def zip_auto_fix(file: UploadFile = File(...)):
    """Upload ZIP file, extract, auto-fix all issues, and return fixed ZIP"""
    temp_dir = None
    
    try:
        if not file.filename.endswith('.zip'):
            raise HTTPException(status_code=400, detail="Only ZIP files are supported")
        
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, file.filename)
        
        with open(zip_path, 'wb') as f:
            content = await file.read()
            f.write(content)
        
        extract_dir = os.path.join(temp_dir, 'extracted')
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Fix all issues
        agent = AutoFixAgent(force_rescan=True)
        results = agent.run(extract_dir, auto_fix=True)
        
        # Create fixed ZIP
        output_dir = Path('fixed_outputs')
        output_dir.mkdir(exist_ok=True)
        
        import time
        output_filename = f"fixed_{int(time.time())}.zip"
        output_zip = output_dir / output_filename
        
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(extract_dir):
                for file_item in files:
                    file_path = os.path.join(root, file_item)
                    arcname = os.path.relpath(file_path, extract_dir)
                    zipf.write(file_path, arcname)
        
        from fastapi.responses import FileResponse
        return FileResponse(
            output_zip,
            media_type='application/zip',
            filename=f'fixed_{file.filename}',
            headers={
                "X-Files-Scanned": str(results.get("scanned_files", 0)),
                "X-Issues-Found": str(len(results.get("issues_found", []))),
                "X-Files-Fixed": str(results.get("files_fixed", 0))
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


@app.post("/approve-fix")
async def approve_fix(request: ApproveFixRequest):
    """Approve and apply fixes for specific issues"""
    try:
        # Here you would typically store approved fixes in database
        # For now, we'll return success response
        return {
            "status": "success", 
            "message": f"Fix {request.fix_id} approved and will be applied", 
            "approved": request.approved
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/fix-and-push")
async def fix_and_push(request: FixPushRequest):
    """Apply approved fixes and push to repository"""
    try:
        if not GIT_AVAILABLE:
            raise HTTPException(status_code=500, detail="Git is not installed")
        
        target_path = Path(request.source)
        if not target_path.exists():
            raise HTTPException(status_code=404, detail="Path not found")
        
        # Apply fixes after approval
        agent = AutoFixAgent(force_rescan=True)
        results = agent.run(target_path, auto_fix=True)  # Now apply fixes
        
        return {
            "status": "success", 
            "message": "Approved fixes applied and ready for push", 
            "commit_message": request.commit_message,
            "fixes_applied": results.get("fixes_applied", [])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/organize-code")
async def organize_code(request: OrganizeRequest):
    """Organize code into proper folder structure and optionally auto-fix"""
    try:
        source_path = Path(request.source)
        if not source_path.exists():
            raise HTTPException(status_code=404, detail="Source path not found")
        
        # Organize code structure
        organizer = CodeOrganizer()
        organize_results = organizer.organize_project(request.source, request.target)
        
        # Auto-fix organized code if requested
        fix_results = None
        if request.auto_fix_after_organize:
            organized_path = organize_results['organized_path']
            agent = AutoFixAgent(force_rescan=True)
            fix_results = agent.run(organized_path, auto_fix=True)
        
        return {
            "status": "success",
            "message": "Code organized and auto-fixed successfully",
            "organization": organize_results,
            "auto_fix": fix_results if fix_results else "Skipped"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/zip-organize")
async def zip_organize(file: UploadFile = File(...), request: Request = None):
    """Upload ZIP/7z file, extract and organize - returns JSON with download link"""
    temp_dir = None
    
    try:
        if not (file.filename.endswith('.zip') or file.filename.endswith('.7z')):
            raise HTTPException(status_code=400, detail="Only ZIP and 7z files are supported")
        
        temp_dir = tempfile.mkdtemp()
        archive_path = os.path.join(temp_dir, file.filename)
        
        with open(archive_path, 'wb') as f:
            content = await file.read()
            f.write(content)
        
        extract_dir = os.path.join(temp_dir, 'extracted')
        os.makedirs(extract_dir, exist_ok=True)
        
        # Extract
        if file.filename.endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
        elif file.filename.endswith('.7z'):
            try:
                import py7zr
                with py7zr.SevenZipFile(archive_path, mode='r') as z:
                    z.extractall(path=extract_dir)
            except ImportError:
                raise HTTPException(status_code=500, detail="py7zr not installed")
        
        organizer = CodeOrganizer()
        organize_results = organizer.organize_project(extract_dir)
        organized_path = organize_results['organized_path']
        
        # Save organized ZIP
        output_dir = Path('organized_outputs')
        output_dir.mkdir(exist_ok=True)
        
        import time
        output_filename = f"organized_{int(time.time())}.zip"
        output_zip = output_dir / output_filename
        
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(organized_path):
                for file_item in files:
                    file_path = os.path.join(root, file_item)
                    arcname = os.path.relpath(file_path, organized_path)
                    zipf.write(file_path, arcname)
        
        # Build download URL
        base_url = str(request.base_url).rstrip('/') if request else 'http://127.0.0.1:8000'
        download_url = f"{base_url}/download/{output_filename}"
        
        return {
            "status": "success",
            "message": f"Archive extracted and organized - {organize_results['files_organized']} files organized",
            "filename": file.filename,
            "download_url": download_url,
            "organization": organize_results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}")
    
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

