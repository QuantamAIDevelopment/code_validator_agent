"""Git Authentication Helper"""
import os
import tempfile
import logging

logger = logging.getLogger(__name__)

class GitAuthHelper:
    def __init__(self):
        self.temp_key_path = None
        self.original_ssh_cmd = os.environ.get('GIT_SSH_COMMAND')
    
    def setup_auth(self, repo_url, access_token=None, ssh_key=None):
        """Setup git authentication and return clone URL"""
        logger.info("Setting up git authentication")
        
        if access_token:
            git_username = os.getenv('GIT_USERNAME', 'git')
            clone_url = repo_url.replace('https://', f'https://{git_username}:{access_token}@')
            logger.info("Using access token authentication")
            return clone_url, 'access_token'
        
        elif ssh_key and ssh_key.strip():
            fd, self.temp_key_path = tempfile.mkstemp(suffix='_key', text=True)
            with os.fdopen(fd, 'w') as f:
                f.write(ssh_key)
            try:
                os.chmod(self.temp_key_path, 0o600)
            except:
                pass
            os.environ['GIT_SSH_COMMAND'] = f'ssh -i {self.temp_key_path} -o StrictHostKeyChecking=no'
            clone_url = repo_url if repo_url.startswith('git@') else repo_url.replace('https://github.com/', 'git@github.com:')
            logger.info("Using SSH key authentication")
            return clone_url, 'ssh_key'
        
        else:
            git_token = os.getenv('GIT_ACCESS_TOKEN')
            git_username = os.getenv('GIT_USERNAME', 'git')
            if git_token:
                clone_url = repo_url.replace('https://', f'https://{git_username}:{git_token}@')
                logger.info("Using environment token authentication")
                return clone_url, 'env_token'
            logger.info("Using public access")
            return repo_url, 'public'
    
    def cleanup(self):
        """Cleanup authentication resources"""
        if self.temp_key_path and os.path.exists(self.temp_key_path):
            try:
                os.unlink(self.temp_key_path)
                logger.info("Cleaned up SSH key")
            except:
                pass
        if 'GIT_SSH_COMMAND' in os.environ and self.original_ssh_cmd is None:
            del os.environ['GIT_SSH_COMMAND']
