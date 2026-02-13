#!/usr/bin/env python3
"""
Master pipeline orchestrator

This script coordinates the full analysis pipeline:
- FULL mode: Complete re-analysis (every 3 days)
- DAILY mode: Only timing + recommendations (daily)

Usage:
    python scripts/run_pipeline.py --mode full    # Every 3 days
    python scripts/run_pipeline.py --mode daily   # Every day
"""
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class PipelineOrchestrator:
    """Orchestrates the full trading analysis pipeline"""
    
    def __init__(self):
        self.scripts_dir = Path(__file__).parent
        self.start_time = datetime.now()
    
    def run_script(self, script_name, args=None):
        """
        Run a Python script and handle errors
        
        Args:
            script_name: Name of script to run (e.g., 'update_6h_data.py')
            args: Optional list of command-line arguments
        
        Returns:
            bool: True if successful, False otherwise
        """
        script_path = self.scripts_dir / script_name
        
        if not script_path.exists():
            logger.error(f"Script not found: {script_path}")
            return False
        
        logger.info(f"\n{'='*80}")
        logger.info(f"Running: {script_name}")
        logger.info(f"{'='*80}")
        
        # Build command
        cmd = [sys.executable, str(script_path)]
        if args:
            cmd.extend(args)
        
        try:
            # Run script with real-time output
            result = subprocess.run(
                cmd,
                check=True,
                # Don't capture output - let it stream to console in real-time
                # capture_output=True,  # Removed
                text=True
            )
            
            logger.info(f"✅ {script_name} completed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ {script_name} failed!")
            logger.error(f"Exit code: {e.returncode}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error running {script_name}: {e}")
            return False
    
    def run_full_pipeline(self, reanalyze=False):
        """
        Run FULL pipeline
        
        Args:
            reanalyze: If True, re-analyze ALL items (slow). 
                      If False, only update Level 2 items (fast).
        
        Modes:
        - reanalyze=True: Complete re-analysis (every 1-2 weeks)
          1. Update 6h for ALL items (4,522) → 75 min
          2. Analyze all → Find new candidates
          3. Download 1h for candidates
          
        - reanalyze=False: Incremental update (every 3 days)
          1. Update 6h for Level 2 items only (~465) → 8 min
          2. Re-filter Level 2 → Level 3
          3. Update 1h for candidates → 2 min
        """
        logger.info("="*80)
        logger.info("🚀 STARTING FULL PIPELINE")
        logger.info("="*80)
        logger.info(f"Start time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Mode: {'COMPLETE RE-ANALYSIS' if reanalyze else 'INCREMENTAL UPDATE'}")
        
        if reanalyze:
            # Complete re-analysis: Update ALL items
            steps = [
                ("update_6h_data.py", None, "Update 6h data (ALL items)"),
                ("analyze_and_filter.py", None, "Analyze and filter candidates"),
                ("download_1h_candidates.py", ["--mode", "update"], "Download 1h data for candidates"),
            ]
        else:
            # Incremental: Only update Level 2 items
            steps = [
                ("update_6h_data.py", ["--selective"], "Update 6h data (Level 2 only)"),
                ("analyze_and_filter.py", ["--quick"], "Re-filter candidates"),
                ("download_1h_candidates.py", ["--mode", "update"], "Update 1h data for candidates"),
            ]
        
        for i, (script, args, description) in enumerate(steps, 1):
            logger.info(f"\n📍 Step {i}/{len(steps)}: {description}")
            
            success = self.run_script(script, args)
            
            if not success:
                logger.error(f"\n❌ Pipeline failed at step {i}: {description}")
                logger.error("Stopping pipeline execution")
                return False
        
        # Success
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        logger.info("\n" + "="*80)
        logger.info("✅ FULL PIPELINE COMPLETED SUCCESSFULLY")
        logger.info("="*80)
        logger.info(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        logger.info(f"Completed at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return True
    
    def run_daily_pipeline(self):
        """
        Run DAILY pipeline (every day):
        1. (Future) Analyze timing with latest 1h data
        2. (Future) Generate recommendations
        
        Note: Assumes 6h data and candidates are already current
        """
        logger.info("="*80)
        logger.info("📊 STARTING DAILY PIPELINE")
        logger.info("="*80)
        logger.info(f"Start time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # TODO: Implement when timing analysis and recommendations are ready
        logger.warning("Daily pipeline not yet implemented!")
        logger.warning("Run 'full' mode for now")
        
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Run OSRS trading analysis pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full pipeline (every 3 days)
  python scripts/run_pipeline.py --mode full
  
  # Run daily pipeline (timing + recommendations only)
  python scripts/run_pipeline.py --mode daily
  
  # Dry run (show what would be executed)
  python scripts/run_pipeline.py --mode full --dry-run
        """
    )
    
    parser.add_argument(
        '--mode',
        choices=['full', 'daily'],
        default='full',
        help='Pipeline mode: full (complete analysis) or daily (timing only)'
    )
    
    parser.add_argument(
        '--reanalyze',
        action='store_true',
        help='Re-analyze ALL items (slow, ~90min). Without this flag, only updates Level 2 items (fast, ~13min)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be executed without running'
    )
    
    args = parser.parse_args()
    
    # Create orchestrator
    orchestrator = PipelineOrchestrator()
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - Showing what would be executed:\n")
        
        if args.mode == 'full':
            print("FULL PIPELINE:")
            print("  1. update_6h_data.py")
            print("  2. analyze_and_filter.py")
            print("  3. download_1h_candidates.py --mode update")
            print("  4. (Future) analyze_timing.py")
            print("  5. (Future) generate_recommendations.py")
        else:
            print("DAILY PIPELINE:")
            print("  1. (Future) analyze_timing.py")
            print("  2. (Future) generate_recommendations.py")
        
        print("\n✅ Dry run completed")
        sys.exit(0)
    
    # Run pipeline
    if args.mode == 'full':
        success = orchestrator.run_full_pipeline(reanalyze=args.reanalyze)
    else:
        success = orchestrator.run_daily_pipeline()
    
    # Exit code
    sys.exit(0 if success else 1)
