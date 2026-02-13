"""
OSRS Wiki API Client
"""
import requests
import time
from typing import Dict, List, Optional, Any
from src.utils.config import config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class OSRSWikiAPI:
    """Client for OSRS Wiki Prices API"""
    
    def __init__(self):
        self.base_url = config.get('api', 'base_url')
        self.headers = {
            'User-Agent': config.get('api', 'user_agent')
        }
        self.rate_limit_delay = config.get('api', 'rate_limit_delay')
        self.max_retries = config.get('api', 'max_retries')
        self.timeout = config.get('api', 'timeout')
    
    def _request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make API request with retry logic
        
        Args:
            endpoint: API endpoint (e.g., 'mapping', 'latest')
            params: Query parameters
        
        Returns:
            JSON response as dict
        """
        url = f"{self.base_url}/{endpoint}"
        
        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                # Rate limiting
                time.sleep(self.rate_limit_delay)
                
                return response.json()
            
            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1}/{self.max_retries} failed: {e}")
                if attempt == self.max_retries - 1:
                    logger.error(f"Max retries reached for {url}")
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
    
    def get_mapping(self) -> List[Dict]:
        """Get item ID to name mapping"""
        logger.info("Fetching item mapping...")
        data = self._request('mapping')
        logger.info(f"Retrieved {len(data)} items")
        return data
    
    def get_latest_prices(self) -> Dict[str, Dict]:
        """Get latest prices for all items"""
        logger.info("Fetching latest prices...")
        data = self._request('latest')
        return data.get('data', {})
    
    def get_timeseries(
        self,
        item_id: int,
        timestep: str = '6h'
    ) -> List[Dict]:
        """
        Get historical timeseries for a specific item
        
        Args:
            item_id: Item ID
            timestep: Granularity ('5m', '1h', '6h')
        
        Returns:
            List of price records
        """
        params = {
            'id': item_id,
            'timestep': timestep
        }
        
        data = self._request('timeseries', params=params)
        return data.get('data', [])