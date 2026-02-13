#!/usr/bin/env python3
"""
Incremental update of 6h timeseries data for all items

This script:
1. Checks existing timeseries files
2. Gets the last timestamp for each item
3. Downloads only NEW data since last update
4. Appends to existing files

Much faster than re-downloading everything!
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


class IncrementalUpdater:
    """Updates timeseries data incrementally"""
    
    # Use a highly liquid item as index to check for new data
    INDEX_ITEM_ID = 2  # Cannonball - always has recent data
    
    def __init__(self, timestep='6h'):
        self.api = OSRSWikiAPI()
        self.timestep = timestep
        self.timeseries_dir = Path(config.get('storage', 'raw_dir')) / f'timeseries_{timestep}'
        self.mapping_file = Path(config.get('storage', 'raw_dir')) / 'mapping.parquet'
        self.metadata_file = self.timeseries_dir / '_update_metadata.json'
        
        # Ensure directories exist
        self.timeseries_dir.mkdir(parents=True, exist_ok=True)
    
    def get_last_timestamp(self, item_id):
        """Get the last timestamp for an item"""
        file_path = self.timeseries_dir / f'item_{item_id}.parquet'
        
        if not file_path.exists():
            return None
        
        try:
            df = pd.read_parquet(file_path)
            if len(df) == 0:
                return None
            return df['datetime'].max()
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return None
    
    def load_metadata(self):
        """Load update metadata"""
        if self.metadata_file.exists():
            try:
                import json
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_metadata(self, metadata):
        """Save update metadata"""
        import json
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
    
    def check_for_new_data(self):
        """
        Check if there's new data available using index item
        Returns: (has_new_data, last_api_timestamp, last_local_timestamp)
        """
        logger.info(f"Checking for new data using index item {self.INDEX_ITEM_ID}...")
        
        # Get last local timestamp for index item
        last_local = self.get_last_timestamp(self.INDEX_ITEM_ID)
        
        if last_local is None:
            logger.info("Index item not found locally - full update needed")
            return True, None, None
        
        # Get latest data from API for index item
        try:
            df_api = self.api.get_timeseries(self.INDEX_ITEM_ID, self.timestep)
            
            if not df_api:
                logger.warning("No data from API for index item")
                return False, None, last_local
            
            df_api = pd.DataFrame(df_api)
            df_api['datetime'] = pd.to_datetime(df_api['timestamp'], unit='s')
            last_api = df_api['datetime'].max()
            
            # Compare
            if last_api > last_local:
                logger.info(f"New data available!")
                logger.info(f"  Local:  {last_local}")
                logger.info(f"  API:    {last_api}")
                logger.info(f"  Gap:    {(last_api - last_local).total_seconds() / 3600:.1f} hours")
                return True, last_api, last_local
            else:
                logger.info(f"Data is up to date (last: {last_local})")
                return False, last_api, last_local
                
        except Exception as e:
            logger.error(f"Error checking for new data: {e}")
            return False, None, last_local
    
    def update_item(self, item_id):
        """
        Update a single item's timeseries
        
        Returns:
            dict with update stats or None if failed
        """
        file_path = self.timeseries_dir / f'item_{item_id}.parquet'
        
        try:
            # Get new data
            df_new = self.api.get_timeseries(item_id, self.timestep)
            
            if not df_new:
                return {'status': 'no_data', 'new_records': 0}
            
            # Convert to DataFrame
            df_new = pd.DataFrame(df_new)
            df_new['item_id'] = item_id
            df_new['datetime'] = pd.to_datetime(df_new['timestamp'], unit='s')
            
            # Check if file exists
            if file_path.exists():
                # Load existing data
                df_existing = pd.read_parquet(file_path)
                
                # Get last timestamp
                last_timestamp = df_existing['datetime'].max()
                
                # Filter only NEW records
                df_new = df_new[df_new['datetime'] > last_timestamp]
                
                if len(df_new) == 0:
                    return {'status': 'up_to_date', 'new_records': 0}
                
                # Concatenate
                df_updated = pd.concat([df_existing, df_new], ignore_index=True)
                
                # Sort by timestamp
                df_updated = df_updated.sort_values('datetime')
                
                # Remove duplicates (safety check)
                df_updated = df_updated.drop_duplicates(subset=['timestamp'], keep='last')
                
            else:
                # New file - use all data
                df_updated = df_new
            
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
    
    def update_all(self, item_ids=None, force=False):
        """
        Update items (all or selective)
        
        Args:
            item_ids: Optional list of item IDs to update. If None, updates all items.
            force: If True, skip new data check and update anyway
        """
        logger.info("="*80)
        logger.info("STARTING INCREMENTAL UPDATE (6h data)")
        logger.info("="*80)
        
        # Determine which items to update
        if item_ids is None:
            # Load all items from mapping
            if not self.mapping_file.exists():
                logger.error(f"Mapping file not found: {self.mapping_file}")
                logger.error("Run bulk download first!")
                return
            
            df_mapping = pd.read_parquet(self.mapping_file)
            item_ids = df_mapping['id'].tolist()
            logger.info("Mode: Update ALL items")
        else:
            logger.info(f"Mode: Selective update ({len(item_ids)} items)")
        
        # Check for new data first (optimization!) - only if updating all
        if item_ids is not None or not force:
            # When doing selective update, always check if there's new data
            has_new_data, last_api, last_local = self.check_for_new_data()
            
            if not has_new_data and item_ids is None:
                # Only skip if updating ALL items and no new data
                logger.info("\n✅ No new data available - skipping update")
                logger.info("Use --force to update anyway")
                return {
                    'skipped': True,
                    'reason': 'no_new_data',
                    'last_check': datetime.now().isoformat()
                }
        else:
            logger.info("Forced update - skipping new data check")
        
        logger.info(f"\nTotal items to update: {len(item_ids)}")
        
        # Stats
        stats = {
            'total': len(item_ids),
            'updated': 0,
            'up_to_date': 0,
            'no_data': 0,
            'failed': 0,
            'new_files': 0,
            'total_new_records': 0,
            'start_time': datetime.now().isoformat(),
        }
        
        # Update each item with progress bar
        pbar = tqdm(item_ids, desc="Updating items")
        
        for item_id in pbar:
            result = self.update_item(item_id)
            
            if result:
                status = result['status']
                
                if status == 'updated':
                    stats['updated'] += 1
                    stats['total_new_records'] += result['new_records']
                    
                    # Check if this was a new file
                    if result.get('total_records') == result.get('new_records'):
                        stats['new_files'] += 1
                        
                elif status == 'up_to_date':
                    stats['up_to_date'] += 1
                elif status == 'no_data':
                    stats['no_data'] += 1
                elif status == 'failed':
                    stats['failed'] += 1
            
            # Update progress bar with live stats
            pbar.set_postfix({
                'Updated': stats['updated'],
                'Up-to-date': stats['up_to_date'],
                'New records': stats['total_new_records']
            })
        
        # Save metadata
        stats['end_time'] = datetime.now().isoformat()
        stats['skipped'] = False
        self.save_metadata(stats)
        
        # Summary
        logger.info("="*80)
        logger.info("UPDATE COMPLETED")
        logger.info("="*80)
        logger.info(f"Total items checked: {stats['total']}")
        logger.info(f"Items updated: {stats['updated']}")
        logger.info(f"Items already up-to-date: {stats['up_to_date']}")
        logger.info(f"Items with no data: {stats['no_data']}")
        logger.info(f"Failed updates: {stats['failed']}")
        logger.info(f"New files created: {stats['new_files']}")
        logger.info(f"Total new records added: {stats['total_new_records']:,}")
        
        return stats


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Incrementally update 6h timeseries data')
    parser.add_argument('--force', action='store_true',
                        help='Force update even if no new data detected')
    parser.add_argument('--selective', action='store_true',
                        help='Only update Level 2 items (fast mode)')
    
    args = parser.parse_args()
    
    updater = IncrementalUpdater(timestep='6h')
    
    # Determine which items to update
    item_ids = None
    if args.selective:
        # Load Level 2 items
        from pathlib import Path
        processed_dir = Path(config.get('storage', 'processed_dir'))
        level2_file = processed_dir / 'level2_filtered.parquet'
        
        if level2_file.exists():
            import pandas as pd
            df_level2 = pd.read_parquet(level2_file)
            item_ids = df_level2['item_id'].tolist()
            logger.info(f"Selective mode: Updating {len(item_ids)} Level 2 items")
        else:
            logger.warning("Level 2 file not found - updating ALL items instead")
            logger.warning("Run full re-analysis first: --mode full --reanalyze")
    
    stats = updater.update_all(item_ids=item_ids, force=args.force)
    
    if stats:
        if stats.get('skipped'):
            print("\n✅ Already up to date - no update needed")
            print("Run with --force to update anyway")
        else:
            print("\n✅ Incremental update completed!")
            print(f"📊 {stats['updated']} items updated with {stats['total_new_records']:,} new records")
    else:
        print("\n❌ Update failed!")
        sys.exit(1)
