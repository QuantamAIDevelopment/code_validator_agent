"""Git Repository Code Agent - Clone, Analyze, Fix"""
import os
import tempfile
import logging
from pathlib import Path
from git import Repo
from .agent import AutoFixAgent

logger = logging.getLogger(__name__)

class GitCodeAgent:
    def __init__(self, ssh_key_path=None):
        self.ssh_key_path = ssh_key_path
        self.git_ssh_cmd = f'ssh -i {ssh_key_path}' if ssh_key_path else None
    
    def analyze_repository(self, repo_url, auto_fix=False, branch='main', push_changes=False):
        """Clone and analyze Git repository"""
        temp_dir = None
        
        try:
            # Convert HTTPS to SSH if needed
            if repo_url.startswith('https://github.com/'):
                repo_url = repo_url.replace('https://github.com/', 'git@github.com:')
                if not repo_url.endswith('.git'):
                    repo_url += '.git'
                logger.info(f"Converted to SSH URL: {repo_url}")
            
            temp_dir = tempfile.mkdtemp()
            logger.info(f"Cloning {repo_url} to {temp_dir}")
            
            # Clone with SSH (clone default branch first)
            env = {'GIT_SSH_COMMAND': self.git_ssh_cmd} if self.git_ssh_cmd else None
            repo = Repo.clone_from(repo_url, temp_dir, env=env)
            
            # Check if branch exists, if not create it
            try:
                repo.git.checkout(branch)
                logger.info(f"Checked out existing branch: {branch}")
            except:
                logger.info(f"Branch {branch} doesn't exist, creating new branch")
                repo.git.checkout('-b', branch)
            
            logger.info(f"Repository cloned successfully")
            
            # Run analysis
            agent = AutoFixAgent(force_rescan=True)
            results = agent.run(temp_dir, auto_fix=False)
            
            # Generate report
            report = self._generate_report(results, repo_url, branch)
            
            # Apply fixes and push if enabled
            if auto_fix and results.get('files_with_issues', 0) > 0:
                logger.info(f"Applying fixes to branch: {branch}")
                
                # Apply fixes
                fix_results = agent.run(temp_dir, auto_fix=True)
                
                # Commit and push changes
                if fix_results.get('files_fixed', 0) > 0:
                    repo.git.add(A=True)
                    commit_msg = f"Auto-fix: {fix_results['files_fixed']} files fixed\n\nIssues resolved: {len(fix_results.get('fixes_applied', []))}"
                    repo.git.commit('-m', commit_msg)
                    logger.info(f"Changes committed: {fix_results['files_fixed']} files fixed")
                    
                    if push_changes:
                        logger.info(f"Pushing changes to {branch}")
                        origin = repo.remote(name='origin')
                        origin.push(branch)
                        logger.info(f"Changes pushed successfully")
                        report['pushed'] = True
                    else:
                        report['pushed'] = False
                        report['message'] = 'Changes committed locally but not pushed'
                    
                    report['fixes_applied'] = fix_results.get('fixes_applied', [])
                    report['files_fixed'] = fix_results.get('files_fixed', 0)
            
            return report
            
        except Exception as e:
            logger.error(f"Error analyzing repository: {e}")
            raise
        finally:
            if temp_dir and os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _generate_report(self, results, repo_url, branch):
        """Generate analysis report"""
        issues_by_risk = {'low': [], 'medium': [], 'high': []}
        
        for issue_data in results.get('issues_found', []):
            issue = issue_data.get('issue', {})
            risk = self._assess_risk(issue.get('type', ''))
            issues_by_risk[risk].append(issue_data)
        
        return {
            'repository': repo_url,
            'branch': branch,
            'summary': {
                'files_scanned': results.get('scanned_files', 0),
                'files_with_issues': results.get('files_with_issues', 0),
                'total_issues': len(results.get('issues_found', [])),
                'high_risk': len(issues_by_risk['high']),
                'medium_risk': len(issues_by_risk['medium']),
                'low_risk': len(issues_by_risk['low'])
            },
            'issues_by_risk': issues_by_risk,
            'files_scanned': results.get('files_list', [])
        }
    
    def _assess_risk(self, issue_type):
        """Assess risk level of issue"""
        high_risk = ['SecurityIssue', 'SyntaxError']
        medium_risk = ['ComparisonBug', 'AssignmentInCondition', 'BareExcept', 'TypeCheckBug']
        
        if issue_type in high_risk:
            return 'high'
        elif issue_type in medium_risk:
            return 'medium'
        return 'low'
