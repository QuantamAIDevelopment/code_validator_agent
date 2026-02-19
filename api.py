"""Auto Fix Agent - API Server + CLI Tool"""
import os
import sys
import tempfile
import shutil
import zipfile
import traceback
import logging
import asyncio
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from pydantic import BaseModel

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('auto_fix_agent.log')
    ]
)
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
    from src.git_agent import GitCodeAgent
    from src.s3_handler import S3Handler
    from src.entry_detector import EntryPointDetector
    from src.quality_auditor import CodeQualityAuditor
    from src.audit_helper import apply_auto_fixes
    from src.test_generator import TestGenerator
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
    branch: str = 'main'
    target_branch: str = None
    ssh_key: str = None
    access_token: str = None
    push_changes: bool = True
    force_rescan: bool = True

class GitRepoAnalyzeRequest(BaseModel):
    repository_url: str
    ssh_key_path: str = None
    auto_fix: bool = False
    branch: str = 'main'

class PrivateRepoSSHRequest(BaseModel):
    ssh_repo_url: str
    ssh_key_content: str = None
    access_token: str = None
    git_username: str = None
    auto_fix: bool = True
    push_changes: bool = True
    branch: str = 'main'

class CodeReviewRequest(BaseModel):
    source: str
    source_type: str  # "path" or "repository"

class S3ZipRequest(BaseModel):
    s3_key: str  # S3 object key (e.g., "uploads/code.zip")
    bucket_name: str = None  # Optional, uses env default

    class Config:
        schema_extra = {
            "example": {
                "s3_key": "uploads/code.zip"
            }
        }

class DetectEntryRequest(BaseModel):
    repository_url: str = None
    branch: str = 'main'
    access_token: str = None

@app.post("/repo-auto-fix")
async def repo_auto_fix(request: RepoAutoFixRequest, include_audit: bool = False):
    """Clone repository, auto-fix issues, and push to branch
    
    Parameters:
    - include_audit: If True, includes quality audit in response
    """
    temp_dir = None
    temp_key_path = None
    
    try:
        if not GIT_AVAILABLE:
            raise HTTPException(status_code=500, detail="GitPython library not installed. Install with: pip install gitpython")
        
        # Normalize repository URL
        repo_url = request.repository_url
        if not repo_url.startswith(('http://', 'https://')):
            repo_url = f"https://github.com/{repo_url}"
        
        temp_dir = tempfile.mkdtemp()
        temp_key_path = None
        
        # Setup authentication - Priority: access_token > ssh_key > env_token
        clone_url = repo_url
        auth_method = 'public'
        
        if request.access_token:
            git_username = os.getenv('GIT_USERNAME', 'git')
            clone_url = repo_url.replace('https://', f'https://{git_username}:{request.access_token}@')
            auth_method = 'access_token'
        elif request.ssh_key and request.ssh_key.strip():
            fd, temp_key_path = tempfile.mkstemp(suffix='_key', text=True)
            with os.fdopen(fd, 'w') as f:
                f.write(request.ssh_key)
            try:
                os.chmod(temp_key_path, 0o600)
            except:
                pass
            os.environ['GIT_SSH_COMMAND'] = f'ssh -i {temp_key_path} -o StrictHostKeyChecking=no'
            clone_url = repo_url.replace('https://github.com/', 'git@github.com:') if repo_url.startswith('https://') else repo_url
            auth_method = 'ssh_key'
            git_username = os.getenv('GIT_USERNAME', 'git')
            clone_url = repo_url.replace('https://', f'https://{git_username}:{request.access_token}@')
            auth_method = 'access_token'
        else:
            git_token = os.getenv('GIT_ACCESS_TOKEN')
            git_username = os.getenv('GIT_USERNAME', 'git')
            if git_token:
                if repo_url.startswith('https://'):
                    clone_url = repo_url.replace('https://', f'https://{git_username}:{git_token}@')
                else:
                    clone_url = repo_url.replace('git@github.com:', 'https://github.com/')
                    clone_url = clone_url.replace('https://', f'https://{git_username}:{git_token}@')
                auth_method = 'env_token'
        
        logger.info(f"Cloning {repo_url} from {request.branch} (auth: {auth_method})...")
        repo = Repo.clone_from(clone_url, temp_dir, branch=request.branch, depth=1)
        logger.info(f"Cloned to {temp_dir}")
        
        # Checkout target branch
        target_branch = request.target_branch or request.branch
        try:
            repo.git.checkout(target_branch)
        except:
            repo.git.checkout('-b', target_branch)
        
        logger.info("Starting auto-fix...")
        agent = AutoFixAgent(force_rescan=request.force_rescan)
        results = agent.run(temp_dir, auto_fix=True)
        logger.info(f"Auto-fix complete: {results.get('files_fixed', 0)} files fixed")
        
        # Push changes if requested
        pushed = False
        push_error = None
        if request.push_changes and results.get('files_fixed', 0) > 0:
            try:
                repo.git.add(A=True)
                commit_msg = f"Auto-fix: Fixed {results.get('files_fixed', 0)} files"
                repo.index.commit(commit_msg)
                
                # Update remote URL with credentials for push
                if auth_method == 'access_token':
                    git_username = os.getenv('GIT_USERNAME', 'git')
                    push_url = repo_url.replace('https://', f'https://{git_username}:{request.access_token}@')
                    repo.remote('origin').set_url(push_url)
                
                origin = repo.remote(name='origin')
                origin.push(target_branch)
                pushed = True
                logger.info(f"Changes pushed to {target_branch}")
            except Exception as e:
                push_error = str(e)
                logger.error(f"Failed to push: {e}")
                logger.error(traceback.format_exc())
        
        # Detect entry point
        detector = EntryPointDetector()
        entry_result = detector.detect(temp_dir)
        
        response_data = {
            "status": "success",
            "message": f"Repository fixed - {results.get('files_fixed', 0)} files" + (" and pushed" if pushed else ""),
            "repository": repo_url,
            "branch": request.branch,
            "target_branch": target_branch,
            "authentication_used": auth_method,
            "pushed": pushed,
            "push_error": push_error if push_error else None,
            "summary": {
                "files_scanned": results.get("scanned_files", 0),
                "issues_found": len(results.get("issues_found", [])),
                "files_fixed": results.get("files_fixed", 0)
            },
            "issues_found": results.get("issues_found", [])[:50],
            "fixes_applied": results.get("fixes_applied", [])[:50],
            "entry_point": entry_result if not entry_result.get('error') else None
        }
        
        # Add quality audit if requested
        if include_audit:
            logger.info("Performing quality audit...")
            auditor = CodeQualityAuditor()
            audit_result = auditor.audit(temp_dir)
            response_data['audit_summary'] = {
                'quality_score': audit_result['quality_score'],
                'quality_level': audit_result['quality_level'],
                'production_readiness': audit_result['production_readiness'],
                'major_issues': len(audit_result['major_issues']),
                'minor_issues': len(audit_result['minor_issues'])
            }
            response_data['full_audit'] = audit_result
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        error_detail = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Error in repo_auto_fix: {error_detail}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_detail)
    
    finally:
        if temp_key_path and os.path.exists(temp_key_path):
            try:
                os.unlink(temp_key_path)
            except:
                pass
        if temp_dir and os.path.exists(temp_dir):
            logger.info(f"Cleaning up {temp_dir}")
            shutil.rmtree(temp_dir, ignore_errors=True)
        if 'GIT_SSH_COMMAND' in os.environ:
            del os.environ['GIT_SSH_COMMAND']

@app.post("/zip-auto-fix")
async def zip_auto_fix(file: UploadFile = File(None), request: Request = None, s3_key: str = None, bucket_name: str = None, auto_approve: bool = True, include_audit: bool = False):
    """Auto-fix code from uploaded ZIP or S3, return fixed ZIP URL
    
    Parameters:
    - include_audit: If True, includes quality audit report in response and ZIP
    """
    temp_dir = None
    s3_handler = None
    
    try:
        temp_dir = tempfile.mkdtemp()
        
        # Handle S3 download
        if s3_key:
            logger.info(f"Downloading from S3: {s3_key}")
            s3_handler = S3Handler()
            if bucket_name:
                s3_handler.bucket_name = bucket_name
            
            zip_path = os.path.join(temp_dir, 'input.zip')
            s3_handler.download_zip(s3_key, zip_path)
            filename = s3_key.split('/')[-1]
        
        # Handle file upload
        elif file:
            logger.info(f"Received file: {file.filename}")
            if not file.filename.endswith('.zip'):
                raise HTTPException(status_code=400, detail="Only ZIP files are supported")
            
            zip_path = os.path.join(temp_dir, file.filename)
            content = await file.read()
            
            if len(content) > 500_000_000:
                raise HTTPException(status_code=400, detail="File too large (max 500MB)")
            
            with open(zip_path, 'wb') as f:
                f.write(content)
            filename = file.filename
        
        else:
            raise HTTPException(status_code=400, detail="Provide either file upload or s3_key parameter")
        
        logger.info("Extracting ZIP...")
        extract_dir = os.path.join(temp_dir, 'extracted')
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Handle nested folder structure (same as audit-zip)
        items = [i for i in os.listdir(extract_dir) if not i.startswith('.')]
        logger.info(f"Extracted items: {items}")
        
        # Store original extract_dir for ZIP creation later
        original_extract_dir = extract_dir
        
        if len(items) == 1 and os.path.isdir(os.path.join(extract_dir, items[0])):
            extract_dir = os.path.join(extract_dir, items[0])
            logger.info(f"Using nested folder for processing: {extract_dir}")
        
        logger.info("Starting scan...")
        agent = AutoFixAgent(force_rescan=True)
        
        try:
            # Step 1: Scan for issues
            logger.info("Step 1: Scanning for issues...")
            results = await asyncio.wait_for(
                asyncio.to_thread(agent.run, extract_dir, False),
                timeout=60
            )
            scan_issues = len(results.get('issues_found', []))
            logger.info(f"Scan complete: {scan_issues} issues found")
            
            # Step 2: Check if auto-approval is enabled
            if scan_issues > 0:
                if not auto_approve:
                    # Return issues for approval
                    return {
                        "status": "pending_approval",
                        "message": f"Found {scan_issues} issues. Set auto_approve=true to fix them.",
                        "filename": filename,
                        "summary": {
                            "files_scanned": results.get("scanned_files", 0),
                            "issues_found": scan_issues
                        },
                        "issues_found": results.get("issues_found", [])[:50],
                        "approval_required": True,
                        "next_step": "Call again with auto_approve=true to fix these issues"
                    }
                
                # Auto-approve enabled, apply fixes
                logger.info("Step 2: Applying auto-fix (approved)...")
                results = await asyncio.wait_for(
                    asyncio.to_thread(agent.run, extract_dir, True),
                    timeout=60
                )
                logger.info(f"Auto-fix complete: {results.get('files_fixed', 0)} files fixed")
        except asyncio.TimeoutError:
            raise HTTPException(status_code=408, detail="Processing timeout - file too complex")
        
        logger.info("Creating output ZIP...")
        output_dir = Path('fixed_outputs')
        output_dir.mkdir(exist_ok=True)
        
        import time
        output_filename = f"fixed_{int(time.time())}.zip"
        output_zip = output_dir / output_filename
        
        # Verify extract_dir has files before creating ZIP
        all_files_before_zip = list(Path(extract_dir).rglob('*'))
        code_files_before_zip = [f for f in all_files_before_zip if f.is_file() and f.suffix in ['.py', '.js', '.ts', '.java', '.cs', '.php', '.rb', '.go', '.rs']]
        logger.info(f"Files in extract_dir before ZIP: Total={len(all_files_before_zip)}, Code={len(code_files_before_zip)}")
        logger.info(f"Extract dir path: {extract_dir}")
        logger.info(f"Extract dir exists: {os.path.exists(extract_dir)}")
        
        if len(code_files_before_zip) == 0:
            raise HTTPException(status_code=500, detail="No code files found after processing")
        
        # Create ZIP from the processed directory (extract_dir has the fixed code)
        logger.info(f"Creating ZIP from: {extract_dir}")
        files_added = 0
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(extract_dir):
                # Skip .git directories
                if '.git' in root:
                    continue
                for file_item in files:
                    file_path = os.path.join(root, file_item)
                    arcname = os.path.relpath(file_path, extract_dir)
                    zipf.write(file_path, arcname)
                    files_added += 1
        
        logger.info(f"ZIP created with {files_added} files")
        
        # Always upload to S3
        if not s3_handler:
            s3_handler = S3Handler()
        
        s3_output_key = f"fixed/{output_filename}"
        download_url = s3_handler.upload_zip(str(output_zip), s3_output_key)
        logger.info(f"Uploaded to S3: {download_url}")
        
        logger.info(f"Fixed ZIP created: {output_zip}")
        return {
            "status": "success",
            "message": f"Auto-fix completed - {results.get('files_fixed', 0)} files fixed",
            "filename": filename,
            "download_url": download_url,
            "storage": "s3",
            "summary": {
                "files_scanned": results.get("scanned_files", 0),
                "issues_found": len(results.get("issues_found", [])),
                "files_fixed": results.get("files_fixed", 0)
            },
            "issues_found": results.get("issues_found", [])[:50],
            "fixes_applied": results.get("fixes_applied", [])[:50],
            "entry_point": None
        }
        
        # Detect entry point
        try:
            detector = EntryPointDetector()
            entry_result = detector.detect(extract_dir)
            return_data = {
                "status": "success",
                "message": f"Auto-fix completed - {results.get('files_fixed', 0)} files fixed",
                "filename": filename,
                "download_url": download_url,
                "storage": "s3",
                "summary": {
                    "files_scanned": results.get("scanned_files", 0),
                    "issues_found": len(results.get("issues_found", [])),
                    "files_fixed": results.get("files_fixed", 0)
                },
                "issues_found": results.get("issues_found", [])[:50],
                "fixes_applied": results.get("fixes_applied", [])[:50],
                "entry_point": entry_result if not entry_result.get('error') else None
            }
            
            # Add quality audit if requested
            if include_audit:
                logger.info("Performing quality audit...")
                auditor = CodeQualityAuditor()
                audit_result = auditor.audit(extract_dir)
                
                # Add audit report to ZIP
                report_path = os.path.join(extract_dir, 'QUALITY_AUDIT_REPORT.json')
                with open(report_path, 'w') as f:
                    import json
                    json.dump(audit_result, f, indent=2)
                
                # Recreate ZIP with audit report
                with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(extract_dir):
                        for file_item in files:
                            file_path = os.path.join(root, file_item)
                            arcname = os.path.relpath(file_path, extract_dir)
                            zipf.write(file_path, arcname)
                
                # Re-upload to S3
                download_url = s3_handler.upload_zip(str(output_zip), s3_output_key)
                
                return_data['audit_summary'] = {
                    'quality_score': audit_result['quality_score'],
                    'quality_level': audit_result['quality_level'],
                    'production_readiness': audit_result['production_readiness'],
                    'major_issues': len(audit_result['major_issues']),
                    'minor_issues': len(audit_result['minor_issues'])
                }
                return_data['full_audit'] = audit_result
                return_data['download_url'] = download_url
            
            return return_data
        except:
            pass
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in zip_auto_fix: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if temp_dir and os.path.exists(temp_dir):
            logger.info(f"Cleaning up temp dir: {temp_dir}")
            shutil.rmtree(temp_dir, ignore_errors=True)


@app.post("/zip-organize")
async def zip_organize(file: UploadFile = File(None), request: Request = None, s3_key: str = None, bucket_name: str = None):
    """Multi-Agent Code Organization - from uploaded ZIP or S3"""
    temp_dir = None
    s3_handler = None
    
    try:
        temp_dir = tempfile.mkdtemp()
        
        # Handle S3 download
        if s3_key:
            logger.info(f"Downloading from S3: {s3_key}")
            s3_handler = S3Handler()
            if bucket_name:
                s3_handler.bucket_name = bucket_name
            
            archive_path = os.path.join(temp_dir, 'input.zip')
            s3_handler.download_zip(s3_key, archive_path)
            filename = s3_key.split('/')[-1]
        
        # Handle file upload
        elif file:
            if not file.filename.endswith('.zip'):
                raise HTTPException(status_code=400, detail="Only ZIP files are supported")
            
            archive_path = os.path.join(temp_dir, file.filename)
            logger.info(f"Received file: {file.filename}")
            
            with open(archive_path, 'wb') as f:
                content = await file.read()
                if len(content) > 500_000_000:
                    raise HTTPException(status_code=400, detail="File too large (max 500MB)")
                f.write(content)
            filename = file.filename
        
        else:
            raise HTTPException(status_code=400, detail="Provide either file upload or s3_key parameter")
        
        extract_dir = os.path.join(temp_dir, 'extracted')
        os.makedirs(extract_dir, exist_ok=True)
        
        logger.info("Extracting ZIP...")
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        logger.info("Orchestrating agents: Scanner → Detector → Structure → Organizer → Validator")
        from src.agents import CodeOrganizationOrchestrator
        orchestrator = CodeOrganizationOrchestrator()
        results = orchestrator.orchestrate(extract_dir)
        
        logger.info(f"Organization complete: {results['files_organized']} files organized")
        
        # Detect entry point
        detector = EntryPointDetector()
        entry_result = detector.detect(results['organized_path'])
        
        # Save organized ZIP
        output_dir = Path('organized_outputs')
        output_dir.mkdir(exist_ok=True)
        
        import time
        output_filename = f"organized_{int(time.time())}.zip"
        output_zip = output_dir / output_filename
        
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(results['organized_path']):
                for file_item in files:
                    file_path = os.path.join(root, file_item)
                    arcname = os.path.relpath(file_path, results['organized_path'])
                    zipf.write(file_path, arcname)
        
        # Always upload to S3
        if not s3_handler:
            s3_handler = S3Handler()
        
        s3_output_key = f"organized/{output_filename}"
        download_url = s3_handler.upload_zip(str(output_zip), s3_output_key)
        logger.info(f"Uploaded to S3: {download_url}")
        
        return {
            "status": "success",
            "message": f"Multi-agent organization complete - {results['files_organized']} files organized",
            "filename": filename,
            "download_url": download_url,
            "storage": "s3",
            "detected_languages": results['detected_languages'],
            "detected_frameworks": results['detected_frameworks'],
            "validation": results['validation'],
            "folder_tree": results['folder_tree'],
            "refactoring": results.get('refactoring', {}),
            "summary": {
                "files_organized": results['files_organized'],
                "languages": ', '.join(results['detected_languages'][:3]),
                "frameworks": ', '.join(results['detected_frameworks']) if results['detected_frameworks'] else 'None',
                "valid": results['validation']['valid'],
                "imports_fixed": results.get('refactoring', {}).get('python_imports_fixed', 0) + results.get('refactoring', {}).get('js_imports_fixed', 0)
            },
            "entry_point": entry_result if not entry_result.get('error') else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}")
    
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

@app.post("/private-repo-organize")
async def private_repo_organize(request: PrivateRepoSSHRequest):
    """Multi-Agent Organization - Access private repo, orchestrate agents, push changes"""
    temp_key_path = None
    temp_dir = None
    
    try:
        if not GIT_AVAILABLE:
            raise HTTPException(status_code=500, detail="GitPython not installed")
        
        logger.info(f"Accessing private repository: {request.ssh_repo_url}")
        
        # Handle SSH key authentication
        if request.ssh_key_content:
            import tempfile
            fd, temp_key_path = tempfile.mkstemp(suffix='_key', text=True)
            with os.fdopen(fd, 'w') as temp_key_file:
                temp_key_file.write(request.ssh_key_content)
            try:
                os.chmod(temp_key_path, 0o600)
            except:
                pass
            logger.info("Created temporary SSH key")
            ssh_cmd = f'ssh -i {temp_key_path} -o StrictHostKeyChecking=no'
            os.environ['GIT_SSH_COMMAND'] = ssh_cmd
            clone_url = request.ssh_repo_url
        
        # Handle access token authentication
        elif request.access_token:
            git_token = request.access_token
            git_username = request.git_username or 'git'
            if request.ssh_repo_url.startswith('https://'):
                clone_url = request.ssh_repo_url.replace('https://', f'https://{git_username}:{git_token}@')
            else:
                # Convert SSH URL to HTTPS with token
                clone_url = request.ssh_repo_url.replace('git@github.com:', 'https://github.com/').replace('.git', '')
                clone_url = clone_url.replace('https://', f'https://{git_username}:{git_token}@') + '.git'
        
        # Use token from .env as fallback
        else:
            git_token = os.getenv('GIT_ACCESS_TOKEN')
            git_username = os.getenv('GIT_USERNAME', 'git')
            if git_token and request.ssh_repo_url.startswith('https://'):
                clone_url = request.ssh_repo_url.replace('https://', f'https://{git_username}:{git_token}@')
            else:
                clone_url = request.ssh_repo_url
        
        # Clone repository
        try:
            repo = Repo.clone_from(clone_url, temp_dir)
            logger.info("Repository cloned successfully")
            
            # Handle branch
            try:
                remote_branches = [ref.name for ref in repo.remotes.origin.refs]
                branch_exists = f'origin/{request.branch}' in remote_branches
                
                if branch_exists:
                    repo.git.checkout(request.branch)
                else:
                    repo.git.checkout('-b', request.branch)
            except Exception as e:
                logger.warning(f"Branch operation failed: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to clone: {str(e)}")
        
        # Orchestrate agents
        logger.info("Orchestrating agents: Scanner → Detector → Structure → Organizer → Validator")
        from src.agents import CodeOrganizationOrchestrator
        orchestrator = CodeOrganizationOrchestrator()
        
        organized_temp = tempfile.mkdtemp()
        results = orchestrator.orchestrate(temp_dir, organized_temp)
        logger.info(f"Organization complete: {results['files_organized']} files")
        
        # Detect entry point
        detector = EntryPointDetector()
        entry_result = detector.detect(organized_temp)
        
        # Clear repo (except .git)
        for item in Path(temp_dir).iterdir():
            if item.name != '.git':
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
        
        # Move organized structure
        for item in Path(results['organized_path']).iterdir():
            dest = Path(temp_dir) / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
        
        shutil.rmtree(organized_temp)
        
        # Push changes
        pushed = False
        if request.push_changes:
            try:
                repo.git.add(A=True)
                commit_msg = f"Multi-agent code organization - {results['detected_languages'][0] if results['detected_languages'] else 'generic'} structure"
                repo.index.commit(commit_msg)
                repo.remote(name='origin').push(request.branch)
                pushed = True
                logger.info(f"Changes pushed to {request.branch}")
            except Exception as e:
                logger.warning(f"Failed to push: {e}")
        
        return {
            "status": "success",
            "message": f"Multi-agent organization complete - {results['files_organized']} files" + (" and pushed" if pushed else ""),
            "detected_languages": results['detected_languages'],
            "detected_frameworks": results['detected_frameworks'],
            "validation": results['validation'],
            "folder_tree": results['folder_tree'],
            "pushed": pushed,
            "branch": request.branch,
            "summary": {
                "files_organized": results['files_organized'],
                "primary_language": results['detected_languages'][0] if results['detected_languages'] else 'unknown',
                "valid": results['validation']['valid']
            },
            "entry_point": entry_result if not entry_result.get('error') else None
        }
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if temp_key_path and os.path.exists(temp_key_path):
            try:
                os.unlink(temp_key_path)
                logger.info("Cleaned up SSH key")
            except:
                pass
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.info("Cleaned up temp directory")
            except:
                pass
        if 'GIT_SSH_COMMAND' in os.environ:
            del os.environ['GIT_SSH_COMMAND']

@app.post("/private-repo-ssh")
async def private_repo_ssh(request: PrivateRepoSSHRequest, include_audit: bool = False):
    """Codebase Repair Specialist - Access private repo, analyze, repair all issues, push
    
    Parameters:
    - include_audit: If True, includes quality audit in response
    """
    temp_key_path = None
    temp_dir = None
    
    try:
        if not GIT_AVAILABLE:
            raise HTTPException(status_code=500, detail="GitPython not installed")
        
        logger.info(f"Accessing private repository: {request.ssh_repo_url}")
        
        # Create temp directory for cloning
        temp_dir = tempfile.mkdtemp()
        
        # Handle SSH key authentication
        if request.ssh_key_content:
            fd, temp_key_path = tempfile.mkstemp(suffix='_key', text=True)
            with os.fdopen(fd, 'w') as temp_key_file:
                temp_key_file.write(request.ssh_key_content)
            try:
                os.chmod(temp_key_path, 0o600)
            except:
                pass
            logger.info("Created temporary SSH key")
            ssh_cmd = f'ssh -i {temp_key_path} -o StrictHostKeyChecking=no'
            os.environ['GIT_SSH_COMMAND'] = ssh_cmd
            clone_url = request.ssh_repo_url
        
        # Handle access token authentication
        elif request.access_token:
            git_token = request.access_token
            git_username = request.git_username or 'git'
            if request.ssh_repo_url.startswith('https://'):
                clone_url = request.ssh_repo_url.replace('https://', f'https://{git_username}:{git_token}@')
            else:
                # Convert SSH URL to HTTPS with token
                clone_url = request.ssh_repo_url.replace('git@github.com:', 'https://github.com/').replace('.git', '')
                clone_url = clone_url.replace('https://', f'https://{git_username}:{git_token}@') + '.git'
        
        # Use token from .env as fallback
        else:
            git_token = os.getenv('GIT_ACCESS_TOKEN')
            git_username = os.getenv('GIT_USERNAME', 'git')
            if git_token and request.ssh_repo_url.startswith('https://'):
                clone_url = request.ssh_repo_url.replace('https://', f'https://{git_username}:{git_token}@')
            else:
                clone_url = request.ssh_repo_url
        
        try:
            repo = Repo.clone_from(clone_url, temp_dir)
            logger.info("Repository cloned successfully")
            
            try:
                remote_branches = [ref.name for ref in repo.remotes.origin.refs]
                branch_exists = f'origin/{request.branch}' in remote_branches
                if branch_exists:
                    repo.git.checkout(request.branch)
                else:
                    repo.git.checkout('-b', request.branch)
            except Exception as e:
                logger.warning(f"Branch operation failed: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to clone: {str(e)}")
        
        # Apply auto-fix if requested
        fix_results = {'files_fixed': 0, 'fixes_applied': []}
        pushed = False
        
        if request.auto_fix:
            logger.info("Applying auto-fix...")
            agent = AutoFixAgent(force_rescan=True)
            fix_results = agent.run(temp_dir, auto_fix=True)
            logger.info(f"Auto-fix complete: {fix_results.get('files_fixed', 0)} files fixed")
            
            # Push changes if requested
            if request.push_changes and fix_results.get('files_fixed', 0) > 0:
                try:
                    repo.git.add(A=True)
                    commit_msg = f"Auto-fix: Fixed {fix_results.get('files_fixed', 0)} files"
                    repo.index.commit(commit_msg)
                    repo.remote(name='origin').push(request.branch)
                    pushed = True
                    logger.info(f"Changes pushed to {request.branch}")
                except Exception as e:
                    logger.warning(f"Failed to push: {e}")
        
        # Detect entry point
        detector = EntryPointDetector()
        entry_result = detector.detect(Path(temp_dir))
        
        response_data = {
            "status": "success",
            "message": f"Repository analyzed - {fix_results.get('files_fixed', 0)} files fixed" + (" and pushed" if pushed else ""),
            "repair": {
                "files_fixed": fix_results.get('files_fixed', 0),
                "fixes_applied": fix_results.get('fixes_applied', [])[:20]
            },
            "pushed": pushed,
            "branch": request.branch,
            "entry_point": entry_result if not entry_result.get('error') else None
        }
        
        # Add quality audit if requested
        if include_audit:
            logger.info("Performing quality audit...")
            auditor = CodeQualityAuditor()
            audit_result = auditor.audit(Path(temp_dir))
            response_data['audit_summary'] = {
                'quality_score': audit_result['quality_score'],
                'quality_level': audit_result['quality_level'],
                'production_readiness': audit_result['production_readiness'],
                'major_issues': len(audit_result['major_issues']),
                'minor_issues': len(audit_result['minor_issues'])
            }
            response_data['full_audit'] = audit_result
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if temp_key_path and os.path.exists(temp_key_path):
            try:
                os.unlink(temp_key_path)
                logger.info("Cleaned up temporary SSH key")
            except:
                pass
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.info("Cleaned up temp directory")
            except:
                pass
        if 'GIT_SSH_COMMAND' in os.environ:
            del os.environ['GIT_SSH_COMMAND']

@app.post("/audit-zip")
async def audit_zip(
    file: UploadFile = File(...),
    return_zip: bool = False,
    apply_fixes: bool = False
):
    """Audit code quality from ZIP file upload"""
    temp_dir = None
    
    try:
        temp_dir = tempfile.mkdtemp()
        
        if not file.filename.endswith('.zip'):
            raise HTTPException(status_code=400, detail="Only ZIP files supported")
        
        zip_path = os.path.join(temp_dir, file.filename)
        content = await file.read()
        if len(content) > 500_000_000:
            raise HTTPException(status_code=400, detail="File too large (max 500MB)")
        
        with open(zip_path, 'wb') as f:
            f.write(content)
        
        extract_dir = os.path.join(temp_dir, 'code')
        os.makedirs(extract_dir, exist_ok=True)
        
        logger.info(f"Extracting ZIP to {extract_dir}")
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(extract_dir)
        
        # Handle nested folder structure
        items = [i for i in os.listdir(extract_dir) if not i.startswith('.')]
        logger.info(f"Extracted items: {items}")
        
        if len(items) == 1 and os.path.isdir(os.path.join(extract_dir, items[0])):
            extract_dir = os.path.join(extract_dir, items[0])
            logger.info(f"Using nested folder: {extract_dir}")
        
        # Verify directory has files
        all_files = list(Path(extract_dir).rglob('*'))
        code_files = [f for f in all_files if f.is_file() and f.suffix in ['.py', '.js', '.ts', '.java', '.cs', '.php', '.rb', '.go', '.rs']]
        logger.info(f"Total files: {len(all_files)}, Code files: {len(code_files)}")
        
        if len(code_files) == 0:
            logger.error(f"No code files found in {extract_dir}")
            logger.error(f"All files: {[str(f) for f in all_files if f.is_file()]}")
            # Don't raise error, just return empty audit
        
        source_name = file.filename.replace('.zip', '')
        
        # Perform quality audit
        logger.info(f"Starting quality audit on {len(code_files)} code files...")
        auditor = CodeQualityAuditor()
        audit_result = auditor.audit(extract_dir)
        
        # Detect entry point
        detector = EntryPointDetector()
        entry_result = detector.detect(extract_dir)
        audit_result['entry_point'] = entry_result if not entry_result.get('error') else None
        
        # Apply fixes if requested
        if apply_fixes:
            logger.info("Applying auto-fixes...")
            from src.scanner import Scanner
            from src.analyzer import Analyzer
            from src.fixer import Fixer
            
            scanner = Scanner()
            analyzer = Analyzer(force_rescan=True)
            fixer = Fixer()
            
            files = scanner.scan(extract_dir)
            for file_path in files:
                issues = analyzer.analyze(file_path)
                if issues:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        fixed_content = fixer.fix(file_path, content, issues)
                        if fixed_content != content:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(fixed_content)
                    except Exception as e:
                        logger.error(f"Error fixing {file_path}: {e}")
            
            # Re-audit
            auditor_after = CodeQualityAuditor()
            audit_after = auditor_after.audit(extract_dir)
            audit_result['quality_score_after_fix'] = audit_after['quality_score']
            audit_result['quality_level_after_fix'] = audit_after['quality_level']
            audit_result['production_readiness_after_fix'] = audit_after['production_readiness']
            audit_result['improvement'] = round(audit_after['quality_score'] - audit_result['quality_score'], 1)
        
        # Return ZIP if requested
        if return_zip:
            output_dir = Path('fixed_outputs')
            output_dir.mkdir(exist_ok=True)
            
            import time
            output_filename = f"audited_{source_name}_{int(time.time())}.zip"
            output_zip = output_dir / output_filename
            
            report_path = os.path.join(extract_dir, 'QUALITY_AUDIT_REPORT.json')
            with open(report_path, 'w') as f:
                import json
                json.dump(audit_result, f, indent=2)
            
            with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(extract_dir):
                    for file_item in files:
                        file_path = os.path.join(root, file_item)
                        arcname = os.path.relpath(file_path, extract_dir)
                        zipf.write(file_path, arcname)
            
            s3_handler = S3Handler()
            s3_output_key = f"audited/{output_filename}"
            download_url = s3_handler.upload_zip(str(output_zip), s3_output_key)
            
            return {
                "status": "success",
                "source": "zip_upload",
                "download_url": download_url,
                "filename": output_filename,
                "audit_summary": {
                    "quality_score": audit_result['quality_score'],
                    "quality_level": audit_result['quality_level'],
                    "production_readiness": audit_result['production_readiness'],
                    "major_issues": len(audit_result['major_issues']),
                    "minor_issues": len(audit_result['minor_issues'])
                },
                "full_audit": audit_result
            }
        
        audit_result['source'] = 'zip_upload'
        return audit_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

@app.post("/audit-public-repo")
async def audit_public_repo(
    repo_url: str,
    branch: str = "main",
    return_zip: bool = False,
    apply_fixes: bool = False
):
    """Audit code quality from public GitHub repository"""
    temp_dir = None
    
    try:
        if not GIT_AVAILABLE:
            raise HTTPException(status_code=500, detail="GitPython not installed")
        
        temp_dir = tempfile.mkdtemp()
        
        logger.info(f"Cloning public repo: {repo_url}")
        extract_dir = os.path.join(temp_dir, 'repo')
        Repo.clone_from(repo_url, extract_dir, branch=branch, depth=1)
        source_name = repo_url.split('/')[-1].replace('.git', '')
        
        # Perform quality audit
        logger.info("Starting quality audit...")
        auditor = CodeQualityAuditor()
        audit_result = auditor.audit(extract_dir)
        
        # Detect entry point
        detector = EntryPointDetector()
        entry_result = detector.detect(extract_dir)
        audit_result['entry_point'] = entry_result if not entry_result.get('error') else None
        
        # Apply fixes if requested
        if apply_fixes:
            logger.info("Applying auto-fixes...")
            from src.scanner import Scanner
            from src.analyzer import Analyzer
            from src.fixer import Fixer
            
            scanner = Scanner()
            analyzer = Analyzer(force_rescan=True)
            fixer = Fixer()
            
            files = scanner.scan(extract_dir)
            for file_path in files:
                issues = analyzer.analyze(file_path)
                if issues:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        fixed_content = fixer.fix(file_path, content, issues)
                        if fixed_content != content:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(fixed_content)
                    except Exception as e:
                        logger.error(f"Error fixing {file_path}: {e}")
            
            # Re-audit
            auditor_after = CodeQualityAuditor()
            audit_after = auditor_after.audit(extract_dir)
            audit_result['quality_score_after_fix'] = audit_after['quality_score']
            audit_result['quality_level_after_fix'] = audit_after['quality_level']
            audit_result['production_readiness_after_fix'] = audit_after['production_readiness']
            audit_result['improvement'] = round(audit_after['quality_score'] - audit_result['quality_score'], 1)
        
        # Return ZIP if requested
        if return_zip:
            output_dir = Path('fixed_outputs')
            output_dir.mkdir(exist_ok=True)
            
            import time
            output_filename = f"audited_{source_name}_{int(time.time())}.zip"
            output_zip = output_dir / output_filename
            
            report_path = os.path.join(extract_dir, 'QUALITY_AUDIT_REPORT.json')
            with open(report_path, 'w') as f:
                import json
                json.dump(audit_result, f, indent=2)
            
            with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(extract_dir):
                    if '.git' in root:
                        continue
                    for file_item in files:
                        file_path = os.path.join(root, file_item)
                        arcname = os.path.relpath(file_path, extract_dir)
                        zipf.write(file_path, arcname)
            
            s3_handler = S3Handler()
            s3_output_key = f"audited/{output_filename}"
            download_url = s3_handler.upload_zip(str(output_zip), s3_output_key)
            
            return {
                "status": "success",
                "source": "public_repo",
                "repository": repo_url,
                "branch": branch,
                "download_url": download_url,
                "filename": output_filename,
                "audit_summary": {
                    "quality_score": audit_result['quality_score'],
                    "quality_level": audit_result['quality_level'],
                    "production_readiness": audit_result['production_readiness'],
                    "major_issues": len(audit_result['major_issues']),
                    "minor_issues": len(audit_result['minor_issues'])
                },
                "full_audit": audit_result
            }
        
        audit_result['source'] = 'public_repo'
        audit_result['repository'] = repo_url
        audit_result['branch'] = branch
        return audit_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

@app.post("/audit-private-repo")
async def audit_private_repo(
    repo_url: str,
    branch: str = "main",
    access_token: str = None,
    ssh_key: str = None,
    return_zip: bool = False,
    apply_fixes: bool = False
):
    """Audit code quality from private GitHub repository"""
    temp_dir = None
    temp_key_path = None
    
    try:
        if not GIT_AVAILABLE:
            raise HTTPException(status_code=500, detail="GitPython not installed")
        
        temp_dir = tempfile.mkdtemp()
        
        # Setup authentication
        if access_token:
            logger.info("Using access token authentication")
            git_username = os.getenv('GIT_USERNAME', 'git')
            clone_url = repo_url.replace('https://', f'https://{git_username}:{access_token}@') if repo_url.startswith('https://') else repo_url
            auth_method = 'access_token'
        elif ssh_key and ssh_key.strip():
            logger.info("Using SSH key authentication")
            fd, temp_key_path = tempfile.mkstemp(suffix='_key', text=True)
            with os.fdopen(fd, 'w') as f:
                f.write(ssh_key)
            try:
                os.chmod(temp_key_path, 0o600)
            except:
                pass
            os.environ['GIT_SSH_COMMAND'] = f'ssh -i {temp_key_path} -o StrictHostKeyChecking=no'
            clone_url = repo_url if repo_url.startswith('git@') else repo_url.replace('https://github.com/', 'git@github.com:')
            auth_method = 'ssh_key'
        else:
            raise HTTPException(status_code=400, detail="Provide access_token or ssh_key for private repo")
        
        logger.info(f"Cloning private repo: {repo_url}")
        extract_dir = os.path.join(temp_dir, 'repo')
        Repo.clone_from(clone_url, extract_dir, branch=branch, depth=1)
        source_name = repo_url.split('/')[-1].replace('.git', '')
        
        # Perform quality audit
        logger.info("Starting quality audit...")
        auditor = CodeQualityAuditor()
        audit_result = auditor.audit(extract_dir)
        
        # Detect entry point
        detector = EntryPointDetector()
        entry_result = detector.detect(extract_dir)
        audit_result['entry_point'] = entry_result if not entry_result.get('error') else None
        
        # Apply fixes if requested
        if apply_fixes:
            logger.info("Applying auto-fixes...")
            from src.scanner import Scanner
            from src.analyzer import Analyzer
            from src.fixer import Fixer
            
            scanner = Scanner()
            analyzer = Analyzer(force_rescan=True)
            fixer = Fixer()
            
            files = scanner.scan(extract_dir)
            for file_path in files:
                issues = analyzer.analyze(file_path)
                if issues:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        fixed_content = fixer.fix(file_path, content, issues)
                        if fixed_content != content:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(fixed_content)
                    except Exception as e:
                        logger.error(f"Error fixing {file_path}: {e}")
            
            # Re-audit
            auditor_after = CodeQualityAuditor()
            audit_after = auditor_after.audit(extract_dir)
            audit_result['quality_score_after_fix'] = audit_after['quality_score']
            audit_result['quality_level_after_fix'] = audit_after['quality_level']
            audit_result['production_readiness_after_fix'] = audit_after['production_readiness']
            audit_result['improvement'] = round(audit_after['quality_score'] - audit_result['quality_score'], 1)
        
        # Return ZIP if requested
        if return_zip:
            output_dir = Path('fixed_outputs')
            output_dir.mkdir(exist_ok=True)
            
            import time
            output_filename = f"audited_{source_name}_{int(time.time())}.zip"
            output_zip = output_dir / output_filename
            
            report_path = os.path.join(extract_dir, 'QUALITY_AUDIT_REPORT.json')
            with open(report_path, 'w') as f:
                import json
                json.dump(audit_result, f, indent=2)
            
            with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(extract_dir):
                    if '.git' in root:
                        continue
                    for file_item in files:
                        file_path = os.path.join(root, file_item)
                        arcname = os.path.relpath(file_path, extract_dir)
                        zipf.write(file_path, arcname)
            
            s3_handler = S3Handler()
            s3_output_key = f"audited/{output_filename}"
            download_url = s3_handler.upload_zip(str(output_zip), s3_output_key)
            
            return {
                "status": "success",
                "source": "private_repo",
                "repository": repo_url,
                "branch": branch,
                "authentication": auth_method,
                "download_url": download_url,
                "filename": output_filename,
                "audit_summary": {
                    "quality_score": audit_result['quality_score'],
                    "quality_level": audit_result['quality_level'],
                    "production_readiness": audit_result['production_readiness'],
                    "major_issues": len(audit_result['major_issues']),
                    "minor_issues": len(audit_result['minor_issues'])
                },
                "full_audit": audit_result
            }
        
        audit_result['source'] = 'private_repo'
        audit_result['repository'] = repo_url
        audit_result['branch'] = branch
        audit_result['authentication'] = auth_method
        return audit_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_key_path and os.path.exists(temp_key_path):
            try:
                os.unlink(temp_key_path)
            except:
                pass
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        if 'GIT_SSH_COMMAND' in os.environ:
            del os.environ['GIT_SSH_COMMAND']

@app.post("/audit-quality")
async def audit_quality(
    file: UploadFile = File(None),
    repo_url: str = None,
    branch: str = "main",
    access_token: str = None,
    ssh_key: str = None,
    s3_key: str = None,
    bucket_name: str = None,
    return_zip: bool = False,
    apply_fixes: bool = False
):
    """Comprehensive code quality audit
    
    Parameters:
    - return_zip: If True, creates ZIP with audit report and returns download URL
    - apply_fixes: If True, applies auto-fixes before audit
    
    Supports: ZIP upload, S3, Git (public/private with token or SSH)
    """
    temp_dir = None
    s3_handler = None
    temp_key_path = None
    
    try:
        temp_dir = tempfile.mkdtemp()
        
        # Handle ZIP file upload
        if file:
            if not file.filename.endswith('.zip'):
                raise HTTPException(status_code=400, detail="Only ZIP files supported")
            zip_path = os.path.join(temp_dir, file.filename)
            content = await file.read()
            if len(content) > 500_000_000:
                raise HTTPException(status_code=400, detail="File too large (max 500MB)")
            with open(zip_path, 'wb') as f:
                f.write(content)
            extract_dir = os.path.join(temp_dir, 'code')
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(extract_dir)
            
            # Handle nested folder structure
            items = os.listdir(extract_dir)
            if len(items) == 1 and os.path.isdir(os.path.join(extract_dir, items[0])):
                extract_dir = os.path.join(extract_dir, items[0])
            
            source_name = file.filename.replace('.zip', '')
            auth_method = 'none'
        
        # Handle S3 download
        elif s3_key:
            logger.info(f"Downloading from S3: {s3_key}")
            s3_handler = S3Handler()
            if bucket_name:
                s3_handler.bucket_name = bucket_name
            zip_path = os.path.join(temp_dir, 'input.zip')
            s3_handler.download_zip(s3_key, zip_path)
            extract_dir = os.path.join(temp_dir, 'code')
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(extract_dir)
            
            # Handle nested folder structure
            items = os.listdir(extract_dir)
            if len(items) == 1 and os.path.isdir(os.path.join(extract_dir, items[0])):
                extract_dir = os.path.join(extract_dir, items[0])
            
            source_name = s3_key.split('/')[-1].replace('.zip', '')
            auth_method = 'none'
        
        # Handle Git repository
        elif repo_url:
            if not GIT_AVAILABLE:
                raise HTTPException(status_code=500, detail="GitPython not installed")
            
            # SSH Key authentication
            if ssh_key:
                logger.info("Using SSH key authentication")
                fd, temp_key_path = tempfile.mkstemp(suffix='_key', text=True)
                with os.fdopen(fd, 'w') as f:
                    f.write(ssh_key)
                try:
                    os.chmod(temp_key_path, 0o600)
                except:
                    pass
                os.environ['GIT_SSH_COMMAND'] = f'ssh -i {temp_key_path} -o StrictHostKeyChecking=no'
                clone_url = repo_url if repo_url.startswith('git@') else repo_url.replace('https://github.com/', 'git@github.com:')
                auth_method = 'ssh_key'
            
            # Access Token authentication
            elif access_token:
                logger.info("Using access token authentication")
                git_username = os.getenv('GIT_USERNAME', 'git')
                clone_url = repo_url.replace('https://', f'https://{git_username}:{access_token}@') if repo_url.startswith('https://') else repo_url
                auth_method = 'access_token'
            
            # Public repository
            else:
                logger.info("Attempting public repository access")
                clone_url = repo_url
                auth_method = 'public'
            
            logger.info(f"Cloning {repo_url}")
            extract_dir = os.path.join(temp_dir, 'repo')
            Repo.clone_from(clone_url, extract_dir, branch=branch, depth=1)
            source_name = repo_url.split('/')[-1].replace('.git', '')
        
        else:
            raise HTTPException(status_code=400, detail="Provide file, repo_url, or s3_key")
        
        # Perform quality audit
        logger.info("Starting quality audit...")
        logger.info(f"Extract directory: {extract_dir}")
        logger.info(f"Directory exists: {os.path.exists(extract_dir)}")
        if os.path.exists(extract_dir):
            logger.info(f"Files in directory: {os.listdir(extract_dir)}")
        
        auditor = CodeQualityAuditor()
        audit_result = auditor.audit(extract_dir)
        
        # Detect entry point
        detector = EntryPointDetector()
        entry_result = detector.detect(extract_dir)
        audit_result['entry_point'] = entry_result if not entry_result.get('error') else None
        
        # Apply fixes if requested
        if apply_fixes:
            fix_result = apply_auto_fixes(extract_dir)
            
            # Re-audit
            auditor_after = CodeQualityAuditor()
            audit_after = auditor_after.audit(extract_dir)
            audit_result['quality_score_after_fix'] = audit_after['quality_score']
            audit_result['quality_level_after_fix'] = audit_after['quality_level']
            audit_result['production_readiness_after_fix'] = audit_after['production_readiness']
            audit_result['improvement'] = round(audit_after['quality_score'] - audit_result['quality_score'], 1)
            audit_result['files_fixed'] = fix_result.get('files_fixed', 0)
        
        # Return ZIP if requested
        if return_zip:
            output_dir = Path('fixed_outputs')
            output_dir.mkdir(exist_ok=True)
            
            import time
            output_filename = f"audited_{source_name}_{int(time.time())}.zip"
            output_zip = output_dir / output_filename
            
            # Add audit report to ZIP
            report_path = os.path.join(extract_dir, 'QUALITY_AUDIT_REPORT.json')
            with open(report_path, 'w') as f:
                import json
                json.dump(audit_result, f, indent=2)
            
            # Create ZIP
            with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(extract_dir):
                    if '.git' in root:
                        continue
                    for file_item in files:
                        file_path = os.path.join(root, file_item)
                        arcname = os.path.relpath(file_path, extract_dir)
                        zipf.write(file_path, arcname)
            
            # Upload to S3
            if not s3_handler:
                s3_handler = S3Handler()
            
            s3_output_key = f"audited/{output_filename}"
            download_url = s3_handler.upload_zip(str(output_zip), s3_output_key)
            
            return {
                "status": "success",
                "download_url": download_url,
                "filename": output_filename,
                "authentication_method": auth_method,
                "audit_summary": {
                    "quality_score": audit_result['quality_score'],
                    "quality_level": audit_result['quality_level'],
                    "production_readiness": audit_result['production_readiness'],
                    "major_issues": len(audit_result['major_issues']),
                    "minor_issues": len(audit_result['minor_issues']),
                    "fixes_applied": audit_result.get('fixes_applied', 0)
                },
                "full_audit": audit_result
            }
        
        # Return JSON only
        audit_result['source_type'] = auth_method
        return audit_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_key_path and os.path.exists(temp_key_path):
            try:
                os.unlink(temp_key_path)
            except:
                pass
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        if 'GIT_SSH_COMMAND' in os.environ:
            del os.environ['GIT_SSH_COMMAND']

@app.post("/generate-tests")
async def generate_tests(file: UploadFile = File(None), s3_key: str = None, bucket_name: str = None):
    """Generate unit tests for code from ZIP or S3"""
    temp_dir = None
    s3_handler = None
    
    try:
        temp_dir = tempfile.mkdtemp()
        
        # Handle S3 download
        if s3_key:
            logger.info(f"Downloading from S3: {s3_key}")
            s3_handler = S3Handler()
            if bucket_name:
                s3_handler.bucket_name = bucket_name
            zip_path = os.path.join(temp_dir, 'input.zip')
            s3_handler.download_zip(s3_key, zip_path)
            filename = s3_key.split('/')[-1]
        
        # Handle file upload
        elif file:
            if not file.filename.endswith('.zip'):
                raise HTTPException(status_code=400, detail="Only ZIP files supported")
            zip_path = os.path.join(temp_dir, file.filename)
            content = await file.read()
            if len(content) > 500_000_000:
                raise HTTPException(status_code=400, detail="File too large (max 500MB)")
            with open(zip_path, 'wb') as f:
                f.write(content)
            filename = file.filename
        else:
            raise HTTPException(status_code=400, detail="Provide file or s3_key")
        
        # Extract ZIP
        extract_dir = os.path.join(temp_dir, 'code')
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(extract_dir)
        
        # Handle nested folder
        items = [i for i in os.listdir(extract_dir) if not i.startswith('.')]
        if len(items) == 1 and os.path.isdir(os.path.join(extract_dir, items[0])):
            extract_dir = os.path.join(extract_dir, items[0])
        
        # Generate tests
        logger.info("Generating tests...")
        generator = TestGenerator()
        tests_generated = generator.generate_tests(extract_dir)
        logger.info(f"Generated {tests_generated} test files")
        
        # Create output ZIP
        output_dir = Path('fixed_outputs')
        output_dir.mkdir(exist_ok=True)
        
        import time
        output_filename = f"with_tests_{int(time.time())}.zip"
        output_zip = output_dir / output_filename
        
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(extract_dir):
                for file_item in files:
                    file_path = os.path.join(root, file_item)
                    arcname = os.path.relpath(file_path, extract_dir)
                    zipf.write(file_path, arcname)
        
        # Upload to S3
        if not s3_handler:
            s3_handler = S3Handler()
        s3_output_key = f"with_tests/{output_filename}"
        download_url = s3_handler.upload_zip(str(output_zip), s3_output_key)
        
        return {
            "status": "success",
            "message": f"Generated {tests_generated} test files",
            "filename": filename,
            "download_url": download_url,
            "storage": "s3",
            "tests_generated": tests_generated
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

@app.post("/code-review")
async def code_review(file: UploadFile = File(None), repo_url: str = None, branch: str = "main", ssh_key: str = None, access_token: str = None, s3_key: str = None):
    """Review code from ZIP, public repo, private repo, or S3"""
    temp_dir = None
    
    try:
        temp_dir = tempfile.mkdtemp()
        
        # Handle ZIP file upload
        if file:
            if not file.filename.endswith('.zip'):
                raise HTTPException(status_code=400, detail="Only ZIP files supported")
            zip_path = os.path.join(temp_dir, file.filename)
            content = await file.read()
            if len(content) > 500_000_000:
                raise HTTPException(status_code=400, detail="File too large (max 500MB)")
            with open(zip_path, 'wb') as f:
                f.write(content)
            target_path = os.path.join(temp_dir, 'code')
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(target_path)
        
        # Handle S3 download
        elif s3_key:
            from src.s3_handler import S3Handler
            s3_handler = S3Handler()
            zip_path = os.path.join(temp_dir, 'input.zip')
            s3_handler.download_zip(s3_key, zip_path)
            target_path = os.path.join(temp_dir, 'code')
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(target_path)
        
        # Handle repository (public or private)
        elif repo_url:
            if not GIT_AVAILABLE:
                raise HTTPException(status_code=500, detail="GitPython not installed")
            
            # Handle private repo with SSH key or access token
            if ssh_key:
                import tempfile as tmp
                fd, key_path = tmp.mkstemp(suffix='_key', text=True)
                with os.fdopen(fd, 'w') as f:
                    f.write(ssh_key)
                try:
                    os.chmod(key_path, 0o600)
                except:
                    pass
                os.environ['GIT_SSH_COMMAND'] = f'ssh -i {key_path} -o StrictHostKeyChecking=no'
                clone_url = repo_url
            else:
                # Use provided access token or get from .env
                if access_token:
                    git_token = access_token
                    git_username = 'git'
                else:
                    git_token = os.getenv('GIT_ACCESS_TOKEN')
                    git_username = os.getenv('GIT_USERNAME', 'git')
                
                if git_token and repo_url.startswith('https://'):
                    # Inject token into URL: https://token@github.com/user/repo.git
                    clone_url = repo_url.replace('https://', f'https://{git_username}:{git_token}@')
                else:
                    clone_url = repo_url
            
            # Clone specific branch
            logger.info(f"Cloning {repo_url} branch: {branch}")
            Repo.clone_from(clone_url, temp_dir, branch=branch, depth=1)
            target_path = temp_dir
            
            # Cleanup SSH key
            if ssh_key and 'GIT_SSH_COMMAND' in os.environ:
                del os.environ['GIT_SSH_COMMAND']
                if 'key_path' in locals():
                    try:
                        os.unlink(key_path)
                    except:
                        pass
        
        else:
            raise HTTPException(status_code=400, detail="Provide file, repo_url, or s3_key")
        
        # Detect entry point
        detector = EntryPointDetector()
        entry_result = detector.detect(target_path)
        
        # Analyze code
        from src.scanner import Scanner
        from src.analyzer import Analyzer
        scanner = Scanner()
        analyzer = Analyzer(force_rescan=True)
        files = scanner.scan(target_path)
        all_issues = []
        for file_path in files:
            all_issues.extend(analyzer.analyze(file_path))
        
        # Calculate scores
        syntax_issues = len([i for i in all_issues if i['type'] in ['SyntaxError', 'IndentationError', 'FileError']])
        quality_issues = len([i for i in all_issues if i['type'] in ['CodeQuality', 'StyleIssue', 'BareExcept']])
        security_issues = len([i for i in all_issues if i['type'] == 'SecurityIssue'])
        maintainability_issues = len([i for i in all_issues if i['type'] in ['EmptyFunction', 'PerformanceIssue']])
        reusability_issues = len([i for i in all_issues if i['type'] in ['ImportIssue', 'DuplicateException']])
        
        syntax_score = max(0, 100 - (syntax_issues * 10))
        quality_score = max(0, 100 - (quality_issues * 5))
        security_score = max(0, 100 - (security_issues * 15))
        maintainability_score = max(0, 100 - (maintainability_issues * 8))
        reusability_score = max(0, 100 - (reusability_issues * 7))
        final_score = (syntax_score * 0.20) + (quality_score * 0.25) + (reusability_score * 0.20) + (maintainability_score * 0.20) + (security_score * 0.15)
        
        grade = "A+" if final_score >= 90 else "A" if final_score >= 80 else "B" if final_score >= 70 else "C" if final_score >= 60 else "D"
        
        strengths = []
        if len(all_issues) < 10:
            strengths.append("Low issue count")
        if not any(i['type'] == 'SecurityIssue' for i in all_issues):
            strengths.append("No security vulnerabilities")
        if not any(i['type'] in ['SyntaxError', 'IndentationError'] for i in all_issues):
            strengths.append("Valid syntax")
        if not strengths:
            strengths.append("Code is functional")
        
        issues_list = [f"{i['type']}: {i['message']} (line {i['line']})" for i in all_issues[:20]]
        
        improvements = []
        issue_types = set(i['type'] for i in all_issues)
        if 'SecurityIssue' in issue_types:
            improvements.append("Fix security vulnerabilities")
        if 'BareExcept' in issue_types:
            improvements.append("Specify exception types")
        if 'StyleIssue' in issue_types:
            improvements.append("Run code formatter")
        if not improvements:
            improvements.append("Continue best practices")
        
        return {
            "syntax_score": syntax_score,
            "code_quality_score": quality_score,
            "reusability_score": reusability_score,
            "maintainability_score": maintainability_score,
            "security_score": security_score,
            "final_score": round(final_score, 2),
            "grade": grade,
            "strengths": strengths,
            "issues": issues_list,
            "improvements": improvements,
            "entry_point": entry_result if not entry_result.get('error') else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    import uvicorn
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    print("=" * 60)
    print("  Senior Software Architecture Agent API")
    print("  Auto-Fix & Organization Service")
    print("=" * 60)
    print(f"  Server: http://localhost:8080")
    print(f"  Docs: http://localhost:8080/docs")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
