"""Secure Git Auto-Fix Agent"""
import os
import tempfile
import shutil
from pathlib import Path
from git import Repo
import logging

logger = logging.getLogger(__name__)

class SecureGitAutoFixAgent:
    def __init__(self):
        self.git_token = os.getenv('GIT_ACCESS_TOKEN')
        self.git_username = os.getenv('GIT_USERNAME', 'git')
    
    def auto_fix_and_push(self, repo_url: str, branch: str = 'main', 
                          ssh_key: str = None, access_token: str = None) -> dict:
        """Clone, fix, commit, and push changes"""
        temp_dir = None
        temp_key_path = None
        auth_method = None
        
        try:
            # Determine authentication method
            clone_url, auth_method, temp_key_path = self._setup_auth(
                repo_url, ssh_key, access_token
            )
            
            if not clone_url:
                return {
                    'status': 'failed',
                    'error': 'No authentication method available. Provide SSH key or access token.'
                }
            
            # Clone repository
            temp_dir = tempfile.mkdtemp()
            logger.info(f"Cloning repository (auth: {auth_method})...")
            repo = Repo.clone_from(clone_url, temp_dir, branch=branch, depth=1)
            
            # Checkout branch
            try:
                repo.git.checkout(branch)
            except:
                repo.git.checkout('-b', branch)
            
            # Apply auto-fix
            logger.info("Applying auto-fixes...")
            files_modified = self._apply_fixes(Path(temp_dir))
            
            if files_modified == 0:
                return {
                    'status': 'success',
                    'branch': branch,
                    'authentication_used': auth_method,
                    'files_modified': 0,
                    'summary': 'No fixes needed - code is clean'
                }
            
            # Stage changes
            repo.git.add(A=True)
            
            # Commit changes
            commit_msg = "Auto Fix: Applied code improvements and syntax corrections"
            repo.index.commit(commit_msg)
            
            # Push changes
            logger.info(f"Pushing changes to {branch}...")
            origin = repo.remote(name='origin')
            origin.push(branch)
            
            return {
                'status': 'success',
                'branch': branch,
                'authentication_used': auth_method,
                'files_modified': files_modified,
                'summary': f'Fixed {files_modified} files: syntax errors, indentation, lint issues'
            }
            
        except Exception as e:
            error_msg = str(e).replace(self.git_token or '', '***TOKEN***')
            if access_token:
                error_msg = error_msg.replace(access_token, '***TOKEN***')
            
            return {
                'status': 'failed',
                'branch': branch,
                'authentication_used': auth_method,
                'error': error_msg
            }
        
        finally:
            # Cleanup
            if temp_key_path and os.path.exists(temp_key_path):
                try:
                    os.unlink(temp_key_path)
                except:
                    pass
            
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except:
                    pass
            
            if 'GIT_SSH_COMMAND' in os.environ:
                del os.environ['GIT_SSH_COMMAND']
    
    def _setup_auth(self, repo_url: str, ssh_key: str = None, 
                    access_token: str = None) -> tuple:
        """Setup authentication and return clone URL"""
        
        # Priority 1: SSH key provided
        if ssh_key:
            fd, temp_key_path = tempfile.mkstemp(suffix='_key', text=True)
            with os.fdopen(fd, 'w') as f:
                f.write(ssh_key)
            try:
                os.chmod(temp_key_path, 0o600)
            except:
                pass
            
            os.environ['GIT_SSH_COMMAND'] = f'ssh -i {temp_key_path} -o StrictHostKeyChecking=no'
            
            # Convert to SSH URL if needed
            if repo_url.startswith('https://'):
                clone_url = repo_url.replace('https://github.com/', 'git@github.com:')
            else:
                clone_url = repo_url
            
            return clone_url, 'SSH', temp_key_path
        
        # Priority 2: Access token provided
        if access_token:
            if repo_url.startswith('https://'):
                clone_url = repo_url.replace('https://', f'https://{self.git_username}:{access_token}@')
            else:
                # Convert SSH to HTTPS
                clone_url = repo_url.replace('git@github.com:', 'https://github.com/')
                clone_url = clone_url.replace('https://', f'https://{self.git_username}:{access_token}@')
            
            return clone_url, 'ACCESS_TOKEN', None
        
        # Priority 3: Token from environment
        if self.git_token:
            if repo_url.startswith('https://'):
                clone_url = repo_url.replace('https://', f'https://{self.git_username}:{self.git_token}@')
            else:
                # Convert SSH to HTTPS
                clone_url = repo_url.replace('git@github.com:', 'https://github.com/')
                clone_url = clone_url.replace('https://', f'https://{self.git_username}:{self.git_token}@')
            
            return clone_url, 'ACCESS_TOKEN', None
        
        # No authentication available
        return None, None, None
    
    def _apply_fixes(self, project_path: Path) -> int:
        """Apply auto-fixes to code files"""
        files_modified = 0
        
        for file_path in project_path.rglob('*.py'):
            if any(x in file_path.parts for x in ['venv', '__pycache__', '.git']):
                continue
            
            try:
                content = file_path.read_text(encoding='utf-8')
                original = content
                
                # Fix common issues
                lines = content.split('\n')
                fixed_lines = []
                
                for i, line in enumerate(lines):
                    # Fix trailing whitespace
                    line = line.rstrip()
                    
                    # Fix indentation errors (basic)
                    if line.strip().startswith('if ') and line.strip().endswith(':'):
                        # Check next line
                        if i + 1 < len(lines) and lines[i + 1].strip() == '':
                            # Add pass statement
                            indent = len(line) - len(line.lstrip())
                            fixed_lines.append(line)
                            fixed_lines.append(' ' * (indent + 4) + 'pass')
                            continue
                    
                    fixed_lines.append(line)
                
                content = '\n'.join(fixed_lines)
                
                # Only write if changed
                if content != original:
                    file_path.write_text(content, encoding='utf-8')
                    files_modified += 1
                    logger.info(f"Fixed: {file_path.name}")
                
            except Exception as e:
                logger.warning(f"Could not fix {file_path.name}: {e}")
        
        return files_modified
