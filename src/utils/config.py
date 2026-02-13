"""
Configuration management
"""
import yaml
from pathlib import Path
from typing import Dict, Any

class Config:
    """Global configuration manager"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._config = self._load_config()
        self._ensure_directories()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _ensure_directories(self):
        """Create necessary directories if they don't exist"""
        for dir_key in ['data_dir', 'raw_dir', 'processed_dir', 'logs_dir']:
            dir_path = Path(self._config['storage'][dir_key])
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def get(self, *keys, default=None):
        """
        Get nested config value
        Example: config.get('api', 'base_url')
        """
        value = self._config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key, default)
            else:
                return default
        return value
    
    @property
    def api(self):
        return self._config['api']
    
    @property
    def storage(self):
        return self._config['storage']
    
    @property
    def data_collection(self):
        return self._config['data_collection']

# Global config instance
config = Config()