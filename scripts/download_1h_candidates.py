#!/usr/bin/env python3
"""
Download 1h timeseries data ONLY for final candidates

This script:
1. Reads final_candidates.parquet
2. Downloads 1h granularity data for those items only
3. Keeps only last 15 days of data (configurable)
4. Much faster than downloading all items

Run after analyze_and_filter.py
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from tqdm import tqdm
from datetime import datetime, timedelta
from src.data_collection.api_client import OSRSWikiAPI
from src.utils.config import config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class CandidatesDownloader:
    """Downloads 1h data for candidate items"""
    
    def __init__(self, timestep='1h', days_to_keep=15):
        self.api = OSRSWikiAPI()
        self.timestep = timestep
        self.days_to_keep = days_to_keep
        self.timeseries_dir = Path(config.get('storage', 'raw_dir')) / f'timeseries_{timestep}'
        self.processed_dir = Path(config.get('storage', 'processed_dir'))
        
        # Ensure directory exists
        self.timeseries_dir.mkdir(parents=True, exist_ok=True)
    
    def download_item(self, item_id):
        """Download 1h data for a single item"""
        try:
            # Download
            data = self.api.get_timeseries(item_id, self.timestep)
            
            if not data:
                return {'status': 'no_data', 'records': 0}
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            df['item_id'] = item_id
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
            
            # Keep only last N days
            cutoff_date = pd.Timestamp.now() - timedelta(days=self.days_to_keep)
            df = df[df['datetime'] >= cutoff_date]
            
            if len(df) == 0:
                return {'status': 'no_recent_data', 'records': 0}
            
            # Save
            output_path = self.timeseries_dir / f'item_{item_id}.parquet'
            df.to_parquet(output_path, compression='snappy')
            
            return {'status': 'success', 'records': len(df)}
            
        except Exception as e:
            logger.error(f"Failed to download item {item_id}: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    def update_item(self, item_id):
        """
        Update existing 1h data or download if not exists
        Similar to incremental update but for 1h data
        """
        file_path = self.timeseries_dir / f'item_{item_id}.parquet'
        
        try:
            # Download new data
            df_new = self.api.get_timeseries(item_id, self.timestep)
            
            if not df_new:
                return {'status': 'no_data', 'new_records': 0}
            
            df_new = pd.DataFrame(df_new)
            df_new['item_id'] = item_id
            df_new['datetime'] = pd.to_datetime(df_new['timestamp'], unit='s')
            
            # If file exists, append only new data
            if file_path.exists():
                df_existing = pd.read_parquet(file_path)
                last_timestamp = df_existing['datetime'].max()
                
                # Filter only new records
                df_new = df_new[df_new['datetime'] > last_timestamp]
                
                if len(df_new) == 0:
                    # No new data, but trim old data
                    cutoff_date = pd.Timestamp.now() - timedelta(days=self.days_to_keep)
                    df_existing = df_existing[df_existing['datetime'] >= cutoff_date]
                    df_existing.to_parquet(file_path, compression='snappy')
                    return {'status': 'trimmed', 'new_records': 0, 'total_records': len(df_existing)}
                
                # Concatenate
                df_updated = pd.concat([df_existing, df_new], ignore_index=True)
            else:
                # New file
                df_updated = df_new
            
            # Keep only last N days
            cutoff_date = pd.Timestamp.now() - timedelta(days=self.days_to_keep)
            df_updated = df_updated[df_updated['datetime'] >= cutoff_date]
            
            # Sort and remove duplicates
            df_updated = df_updated.sort_values('datetime')
            df_updated = df_updated.drop_duplicates(subset=['timestamp'], keep='last')
            
            # Save
            df_updated.to_parquet(file_path, compression='snappy')
            
            return {
                'status': 'updated',
                'new_records': len(df_new),
                'total_records': len(df_updated)
            }
            
        except Exception as e:
            logger.error(f"Failed to update item {item_id}: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    def run(self, mode='update'):
        """
        Download/update 1h data for all candidates
        
        Args:
            mode: 'download' for fresh download, 'update' for incremental
        """
        logger.info("="*80)
        logger.info(f"DOWNLOADING 1H DATA FOR CANDIDATES (mode: {mode})")
        logger.info("="*80)
        
        # Find candidates file (try all risk profiles)
        candidates_file = None
        for risk_profile in ['conservative', 'moderate', 'aggressive']:
            candidate_path = self.processed_dir / f'final_candidates_{risk_profile}.parquet'
            if candidate_path.exists():
                candidates_file = candidate_path
                logger.info(f"Found candidates file: {candidate_path.name}")
                break
        
        if not candidates_file:
            logger.error("No candidates file found!")
            logger.error("Run analyze_and_filter.py first")
            return None
        
        # Load candidates
        df_candidates = pd.read_parquet(candidates_file)
        item_ids = df_candidates['item_id'].tolist()
        
        logger.info(f"Candidates to download: {len(item_ids)}")
        logger.info(f"Timestep: {self.timestep}")
        logger.info(f"Keeping last {self.days_to_keep} days of data")
        
        # Stats
        stats = {
            'total': len(item_ids),
            'success': 0,
            'updated': 0,
            'trimmed': 0,
            'no_data': 0,
            'failed': 0,
            'total_records': 0,
        }
        
        # Download/update each item
        for item_id in tqdm(item_ids, desc=f"{mode.capitalize()}ing 1h data"):
            if mode == 'download':
                result = self.download_item(item_id)
            else:  # update
                result = self.update_item(item_id)
            
            if result:
                status = result['status']
                
                if status == 'success':
                    stats['success'] += 1
                    stats['total_records'] += result['records']
                elif status == 'updated':
                    stats['updated'] += 1
                    stats['total_records'] += result.get('total_records', 0)
                elif status == 'trimmed':
                    stats['trimmed'] += 1
                    stats['total_records'] += result.get('total_records', 0)
                elif status in ['no_data', 'no_recent_data']:
                    stats['no_data'] += 1
                elif status == 'failed':
                    stats['failed'] += 1
        
        # Summary
        logger.info("="*80)
        logger.info("DOWNLOAD COMPLETED")
        logger.info("="*80)
        logger.info(f"Total items: {stats['total']}")
        
        if mode == 'download':
            logger.info(f"Successfully downloaded: {stats['success']}")
        else:
            logger.info(f"Successfully updated: {stats['updated']}")
            logger.info(f"Trimmed (no new data): {stats['trimmed']}")
        
        logger.info(f"No data: {stats['no_data']}")
        logger.info(f"Failed: {stats['failed']}")
        logger.info(f"Total records: {stats['total_records']:,}")
        
        return stats


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Download 1h data for candidate items')
    parser.add_argument('--mode', choices=['download', 'update'], default='update',
                        help='download: fresh download, update: incremental update')
    parser.add_argument('--days', type=int, default=15,
                        help='Number of days to keep (default: 15)')
    
    args = parser.parse_args()
    
    downloader = CandidatesDownloader(timestep='1h', days_to_keep=args.days)
    stats = downloader.run(mode=args.mode)
    
    if stats and (stats['success'] > 0 or stats['updated'] > 0):
        print(f"\n✅ {args.mode.capitalize()} completed successfully!")
    else:
        print(f"\n❌ {args.mode.capitalize()} failed!")
        sys.exit(1)
