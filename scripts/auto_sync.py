#!/usr/bin/env python3
"""
Auto-sync script - Backend automation

This script:
1. Checks for config changes in GitHub
2. Runs pipeline if needed
3. Uploads results back to GitHub

Run with cron every 3 days or manually
"""
import subprocess
import json
import yaml
from pathlib import Path
from datetime import datetime
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class AutoSync:
    """Automatic sync between local backend and GitHub"""
    
    def __init__(self):
        self.project_root = project_root
        self.config_file = self.project_root / 'config.yaml'
        self.metadata_file = self.project_root / 'data' / 'processed' / 'metadata.json'
        self.user_requests_file = self.project_root / '.streamlit' / 'user_requests.json'
    
    def git_pull(self):
        """Pull latest changes from GitHub"""
        logger.info("Pulling latest changes from GitHub...")
        
        try:
            result = subprocess.run(
                ['git', 'pull', 'origin', 'main'],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info("✅ Git pull successful")
                return True
            else:
                logger.error(f"❌ Git pull failed: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"❌ Git pull error: {e}")
            return False
    
    def git_push(self, message="Auto-update from backend"):
        """Push results to GitHub"""
        logger.info("Pushing results to GitHub...")
        
        try:
            # Add processed files
            subprocess.run(
                ['git', 'add', 'data/processed/*.parquet', 'data/processed/metadata.json'],
                cwd=self.project_root
            )
            
            # Commit
            result = subprocess.run(
                ['git', 'commit', '-m', message],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            # Push
            if result.returncode == 0:
                subprocess.run(
                    ['git', 'push', 'origin', 'main'],
                    cwd=self.project_root
                )
                logger.info("✅ Git push successful")
                return True
            else:
                logger.warning("⚠️  No changes to commit")
                return True  # Not an error
                
        except Exception as e:
            logger.error(f"❌ Git push error: {e}")
            return False
    
    def check_user_requests(self):
        """Check if user requested re-analysis from Streamlit"""
        if not self.user_requests_file.exists():
            return None
        
        try:
            with open(self.user_requests_file, 'r') as f:
                requests = json.load(f)
            
            # Check for pending requests
            pending = [r for r in requests if r.get('status') == 'pending']
            
            if pending:
                return pending[0]  # Return first pending request
            
        except Exception as e:
            logger.error(f"Error reading user requests: {e}")
        
        return None
    
    def mark_request_complete(self, request_id):
        """Mark user request as completed"""
        try:
            with open(self.user_requests_file, 'r') as f:
                requests = json.load(f)
            
            # Update request status
            for req in requests:
                if req.get('id') == request_id:
                    req['status'] = 'completed'
                    req['completed_at'] = datetime.now().isoformat()
            
            with open(self.user_requests_file, 'w') as f:
                json.dump(requests, f, indent=2)
            
            logger.info(f"✅ Marked request {request_id} as completed")
            
        except Exception as e:
            logger.error(f"Error updating request status: {e}")
    
    def run_pipeline(self, reanalyze=False):
        """Run the analysis pipeline"""
        logger.info(f"Running pipeline (reanalyze={reanalyze})...")
        
        cmd = [sys.executable, 'scripts/run_pipeline.py', '--mode', 'full']
        
        if reanalyze:
            cmd.append('--reanalyze')
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info("✅ Pipeline completed successfully")
                return True
            else:
                logger.error(f"❌ Pipeline failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Pipeline error: {e}")
            return False
    
    def create_metadata(self):
        """Create metadata file with update info"""
        metadata = {
            'last_update': datetime.now().isoformat(),
            'status': 'success',
            'backend': 'local',
        }
        
        # Add candidates info
        processed_dir = self.project_root / 'data' / 'processed'
        
        for risk_profile in ['conservative', 'moderate', 'aggressive']:
            file_path = processed_dir / f'final_candidates_{risk_profile}.parquet'
            
            if file_path.exists():
                import pandas as pd
                df = pd.read_parquet(file_path)
                
                metadata[f'{risk_profile}_candidates'] = len(df)
                metadata[f'{risk_profile}_avg_roi'] = float(df['avg_roi'].mean())
                metadata[f'{risk_profile}_avg_win_rate'] = float(df['win_rate'].mean())
        
        # Save
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info("✅ Metadata created")
    
    def run(self, force_reanalyze=False):
        """Main execution"""
        logger.info("="*80)
        logger.info("AUTO-SYNC STARTED")
        logger.info("="*80)
        
        # 1. Pull latest from GitHub
        if not self.git_pull():
            logger.error("❌ Failed to pull from GitHub")
            return False
        
        # 2. Check for user requests
        user_request = self.check_user_requests()
        
        if user_request:
            logger.info(f"📝 User request detected: {user_request}")
            force_reanalyze = user_request.get('reanalyze', False)
            request_id = user_request.get('id')
        else:
            request_id = None
        
        # 3. Run pipeline
        success = self.run_pipeline(reanalyze=force_reanalyze)
        
        if not success:
            logger.error("❌ Pipeline failed")
            return False
        
        # 4. Create metadata
        self.create_metadata()
        
        # 5. Push to GitHub
        commit_msg = f"Auto-update candidates - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        if user_request:
            commit_msg = f"Update from user request - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        if not self.git_push(commit_msg):
            logger.error("❌ Failed to push to GitHub")
            return False
        
        # 6. Mark request as complete
        if request_id:
            self.mark_request_complete(request_id)
        
        logger.info("="*80)
        logger.info("✅ AUTO-SYNC COMPLETED")
        logger.info("="*80)
        
        return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Auto-sync backend with GitHub')
    parser.add_argument('--reanalyze', action='store_true',
                        help='Force full re-analysis')
    
    args = parser.parse_args()
    
    syncer = AutoSync()
    success = syncer.run(force_reanalyze=args.reanalyze)
    
    sys.exit(0 if success else 1)
