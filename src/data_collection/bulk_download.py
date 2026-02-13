"""
Bulk download of historical data
"""
import pandas as pd
from pathlib import Path
from tqdm import tqdm
from typing import List, Dict
from src.data_collection.api_client import OSRSWikiAPI
from src.utils.config import config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class BulkDownloader:
    """Download historical timeseries data for all items"""
    
    def __init__(self):
        self.api = OSRSWikiAPI()
        self.timestep = config.get('data_collection', 'bulk_download', 'timestep')
        self.chunk_size = config.get('data_collection', 'bulk_download', 'chunk_size')
        self.save_frequency = config.get('data_collection', 'bulk_download', 'save_frequency')
        
        # Setup paths
        self.raw_dir = Path(config.get('storage', 'raw_dir'))
        self.timeseries_dir = self.raw_dir / f"timeseries_{self.timestep}"
        self.timeseries_dir.mkdir(parents=True, exist_ok=True)
    
    def download_mapping(self) -> pd.DataFrame:
        """Download and save item mapping"""
        logger.info("Downloading item mapping...")
        
        mapping = self.api.get_mapping()
        df_mapping = pd.DataFrame(mapping)
        
        # Save
        output_path = self.raw_dir / "mapping.parquet"
        df_mapping.to_parquet(output_path, compression='snappy')
        logger.info(f"Saved mapping to {output_path}")
        
        return df_mapping
    
    def download_timeseries_all(self, item_ids: List[int]) -> Dict[str, any]:
        """
        Download timeseries for all items
        
        Args:
            item_ids: List of item IDs to download
        
        Returns:
            Dict with download statistics
        """
        logger.info(f"Starting bulk download for {len(item_ids)} items...")
        logger.info(f"Timestep: {self.timestep}")
        
        stats = {
            'total_items': len(item_ids),
            'successful': 0,
            'failed': 0,
            'empty': 0,
            'failed_ids': []
        }
        
        # Progress bar
        pbar = tqdm(item_ids, desc="Downloading timeseries")
        
        for i, item_id in enumerate(pbar):
            try:
                # Download
                data = self.api.get_timeseries(item_id, self.timestep)
                
                if not data:
                    stats['empty'] += 1
                    logger.debug(f"No data for item {item_id}")
                    continue
                
                # Convert to DataFrame
                df = pd.DataFrame(data)
                df['item_id'] = item_id
                
                # Add datetime
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
                
                # Save individual file
                output_path = self.timeseries_dir / f"item_{item_id}.parquet"
                df.to_parquet(output_path, compression='snappy')
                
                stats['successful'] += 1
                
                # Update progress bar
                pbar.set_postfix({
                    'Success': stats['successful'],
                    'Failed': stats['failed'],
                    'Empty': stats['empty']
                })
                
            except Exception as e:
                stats['failed'] += 1
                stats['failed_ids'].append(item_id)
                logger.error(f"Failed to download item {item_id}: {e}")
        
        # Summary
        logger.info("=" * 80)
        logger.info("BULK DOWNLOAD COMPLETED")
        logger.info("=" * 80)
        logger.info(f"Total items: {stats['total_items']}")
        logger.info(f"Successful: {stats['successful']}")
        logger.info(f"Failed: {stats['failed']}")
        logger.info(f"Empty (no data): {stats['empty']}")
        
        if stats['failed_ids']:
            logger.warning(f"Failed IDs: {stats['failed_ids'][:20]}...")  # Show first 20
        
        return stats
    
    def run(self):
        """Execute full bulk download pipeline"""
        logger.info("=" * 80)
        logger.info("STARTING BULK DOWNLOAD")
        logger.info("=" * 80)
        
        # Step 1: Download mapping
        df_mapping = self.download_mapping()
        
        # Step 2: Get all item IDs
        item_ids = df_mapping['id'].tolist()
        logger.info(f"Found {len(item_ids)} items to download")
        
        # Step 3: Download timeseries
        stats = self.download_timeseries_all(item_ids)
        
        return stats