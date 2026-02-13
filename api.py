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
    from src.git_agent import GitCodeAgent
    from src.s3_handler import S3Handler
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

class GitRepoAnalyzeRequest(BaseModel):
    repository_url: str
    ssh_key_path: str = None
    auto_fix: bool = False
    branch: str = 'main'

class PrivateRepoSSHRequest(BaseModel):
    ssh_repo_url: str
    ssh_key_content: str
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
async def zip_auto_fix(file: UploadFile = File(None), request: Request = None, s3_key: str = None, bucket_name: str = None, auto_approve: bool = False):
    """Auto-fix code from uploaded ZIP or S3, return fixed ZIP URL"""
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
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
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
        
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(extract_dir):
                for file_item in files:
                    file_path = os.path.join(root, file_item)
                    arcname = os.path.relpath(file_path, extract_dir)
                    zipf.write(file_path, arcname)
        
        # Upload to S3 if request came from S3
        if s3_key and s3_handler:
            s3_output_key = f"fixed/{output_filename}"
            download_url = s3_handler.upload_zip(str(output_zip), s3_output_key)
            logger.info(f"Uploaded to S3: {download_url}")
        else:
            base_url = str(request.base_url).rstrip('/') if request else 'http://127.0.0.1:8000'
            download_url = f"{base_url}/download/{output_filename}"
        
        logger.info(f"Fixed ZIP created: {output_zip}")
        return {
            "status": "success",
            "message": f"Auto-fix completed - {results.get('files_fixed', 0)} files fixed",
            "filename": filename,
            "download_url": download_url,
            "storage": "s3" if s3_key else "local",
            "summary": {
                "files_scanned": results.get("scanned_files", 0),
                "issues_found": len(results.get("issues_found", [])),
                "files_fixed": results.get("files_fixed", 0)
            },
            "issues_found": results.get("issues_found", [])[:50],
            "fixes_applied": results.get("fixes_applied", [])[:50]
        }
        
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
        
        # Upload to S3 if request came from S3
        if s3_key and s3_handler:
            s3_output_key = f"organized/{output_filename}"
            download_url = s3_handler.upload_zip(str(output_zip), s3_output_key)
            logger.info(f"Uploaded to S3: {download_url}")
        else:
            base_url = str(request.base_url).rstrip('/') if request else 'http://127.0.0.1:8000'
            download_url = f"{base_url}/download/{output_filename}"
        
        return {
            "status": "success",
            "message": f"Multi-agent organization complete - {results['files_organized']} files organized",
            "filename": filename,
            "download_url": download_url,
            "storage": "s3" if s3_key else "local",
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
            }
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
        
        # Create temporary SSH key
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
        
        temp_dir = tempfile.mkdtemp()
        logger.info(f"Cloning repository to {temp_dir}...")
        
        # Setup SSH command
        if temp_key_path:
            ssh_cmd = f'ssh -i {temp_key_path} -o StrictHostKeyChecking=no'
            os.environ['GIT_SSH_COMMAND'] = ssh_cmd
        
        # Clone repository
        try:
            repo = Repo.clone_from(request.ssh_repo_url, temp_dir)
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
            }
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
async def private_repo_ssh(request: PrivateRepoSSHRequest):
    """Codebase Repair Specialist - Access private repo, analyze, repair all issues, push"""
    temp_key_path = None
    temp_dir = None
    
    try:
        logger.info(f"Accessing private repository: {request.ssh_repo_url}")
        
        if request.ssh_key_content:
            import tempfile
            fd, temp_key_path = tempfile.mkstemp(suffix='_key', text=True)
            with os.fdopen(fd, 'w') as temp_key_file:
                temp_key_file.write(request.ssh_key_content)
            try:
                os.chmod(temp_key_path, 0o600)
            except:
                pass
            ssh_key = temp_key_path
            logger.info(f"Created temporary SSH key")
        else:
            ssh_key = None
        
        if not GIT_AVAILABLE:
            raise HTTPException(status_code=500, detail="GitPython not installed")
        
        temp_dir = tempfile.mkdtemp()
        logger.info(f"Cloning repository to {temp_dir}...")
        
        if temp_key_path:
            ssh_cmd = f'ssh -i {temp_key_path} -o StrictHostKeyChecking=no'
            os.environ['GIT_SSH_COMMAND'] = ssh_cmd
        
        try:
            repo = Repo.clone_from(request.ssh_repo_url, temp_dir)
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
        
        # Analyze and detect errors
        logger.info("Analyzing codebase for errors...")
        from src.agents.repair_agent import RepairAgent
        repair_agent = RepairAgent()
        analysis = repair_agent.analyze_and_repair(Path(temp_dir))
        
        logger.info(f"Analysis complete. Errors detected: {analysis['has_errors']}")
        
        # Auto-fix if requested
        if request.auto_fix and analysis['has_errors']:
            logger.info("Applying auto-fix...")
            agent = AutoFixAgent(force_rescan=True)
            fix_results = agent.run(temp_dir, auto_fix=True)
            logger.info(f"Auto-fix complete: {fix_results.get('files_fixed', 0)} files fixed")
        else:
            fix_results = {'files_fixed': 0, 'fixes_applied': []}
        
        # Push changes if requested
        pushed = False
        if request.push_changes and (request.auto_fix or analysis['has_errors']):
            try:
                repo.git.add(A=True)
                repo.index.commit(f"Codebase repair - Fixed {fix_results.get('files_fixed', 0)} files")
                origin = repo.remote(name='origin')
                origin.push(request.branch)
                pushed = True
                logger.info(f"Changes pushed to {request.branch}")
            except Exception as e:
                logger.warning(f"Failed to push: {e}")
        
        return {
            "status": "success",
            "message": f"Codebase repair complete - {fix_results.get('files_fixed', 0)} files fixed" + (" and pushed" if pushed else ""),
            "analysis": {
                "has_errors": analysis['has_errors'],
                "lint_errors": analysis['errors']['lint'][:200],
                "dependency_errors": analysis['errors']['dependency'][:200],
                "import_errors": analysis['errors']['import'][:200],
                "runtime_errors": analysis['errors']['runtime'][:200]
            },
            "repair": {
                "files_fixed": fix_results.get('files_fixed', 0),
                "fixes_applied": fix_results.get('fixes_applied', [])[:20]
            },
            "pushed": pushed,
            "branch": request.branch
        }
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Clean up temporary key file
        if temp_key_path and os.path.exists(temp_key_path):
            try:
                os.unlink(temp_key_path)
                logger.info("Cleaned up temporary SSH key")
            except:
                pass

@app.post("/code-review")
async def code_review(request: CodeReviewRequest):
    """Review code from path or repository - returns evaluation scores only"""
    temp_dir = None
    
    try:
        if request.source_type == "repository":
            if not GIT_AVAILABLE:
                raise HTTPException(status_code=500, detail="GitPython not installed")
            temp_dir = tempfile.mkdtemp()
            Repo.clone_from(request.source, temp_dir, depth=1)
            target_path = temp_dir
        elif request.source_type == "path":
            target_path = Path(request.source)
            if not target_path.exists():
                raise HTTPException(status_code=404, detail="Path not found")
        else:
            raise HTTPException(status_code=400, detail="Invalid source_type. Use 'path' or 'repository'")
        
        from src.scanner import Scanner
        from src.analyzer import Analyzer
        scanner = Scanner()
        analyzer = Analyzer(force_rescan=True)
        files = scanner.scan(target_path)
        all_issues = []
        for file_path in files[:50]:
            all_issues.extend(analyzer.analyze(file_path))
        
        syntax_issues = len([i for i in all_issues if i['type'] in ['SyntaxError', 'FileError']])
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
        if not any(i['type'] == 'SyntaxError' for i in all_issues):
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
            "improvements": improvements
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

@app.post("/code-review-zip")
async def code_review_zip(file: UploadFile = File(...)):
    """Review code from ZIP file - returns evaluation scores only"""
    temp_dir = None
    
    try:
        if not file.filename.endswith('.zip'):
            raise HTTPException(status_code=400, detail="Only ZIP files supported")
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, file.filename)
        
        content = await file.read()
        if len(content) > 500_000_000:  # 500MB limit
            raise HTTPException(status_code=400, detail="File too large (max 500MB)")
        
        with open(zip_path, 'wb') as f:
            f.write(content)
        target_path = os.path.join(temp_dir, 'code')
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(target_path)
        
        from src.scanner import Scanner
        from src.analyzer import Analyzer
        scanner = Scanner()
        analyzer = Analyzer(force_rescan=True)
        files = scanner.scan(target_path)
        all_issues = []
        for file_path in files[:50]:
            all_issues.extend(analyzer.analyze(file_path))
        
        syntax_issues = len([i for i in all_issues if i['type'] in ['SyntaxError', 'FileError']])
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
        if not any(i['type'] == 'SyntaxError' for i in all_issues):
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
            "improvements": improvements
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
    print(f"  Server: http://localhost:8001")
    print(f"  Docs: http://localhost:8001/docs")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
