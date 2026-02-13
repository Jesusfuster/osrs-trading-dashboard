"""
Data loading utilities for Streamlit dashboard
"""
import pandas as pd
import yaml
from pathlib import Path
from typing import Optional, Tuple

def load_config() -> dict:
    """Load config.yaml"""
    config_file = Path('config.yaml')
    
    if not config_file.exists():
        raise FileNotFoundError("config.yaml not found!")
    
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)


def load_candidates(risk_profile: Optional[str] = None) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Load final candidates parquet file
    
    Args:
        risk_profile: Specific profile to load, or None to auto-detect
    
    Returns:
        (dataframe, risk_profile_used) or (None, None) if not found
    """
    config = load_config()
    processed_dir = Path(config['storage']['processed_dir'])
    
    # List of profiles to try
    if risk_profile:
        profiles_to_try = [risk_profile]
    else:
        profiles_to_try = ['moderate', 'conservative', 'aggressive']
    
    for profile in profiles_to_try:
        file_path = processed_dir / f'final_candidates_{profile}.parquet'
        
        if file_path.exists():
            df = pd.read_parquet(file_path)
            return df, profile
    
    return None, None


def load_timeseries(item_id: int, timestep: str = '6h') -> Optional[pd.DataFrame]:
    """
    Load timeseries data for a specific item
    
    Args:
        item_id: Item ID
        timestep: '6h' or '1h'
    
    Returns:
        DataFrame with timeseries data or None if not found
    """
    config = load_config()
    raw_dir = Path(config['storage']['raw_dir'])
    
    ts_file = raw_dir / f'timeseries_{timestep}' / f'item_{item_id}.parquet'
    
    if ts_file.exists():
        df = pd.read_parquet(ts_file)
        return df.sort_values('datetime')
    
    return None


def load_all_candidates_history() -> pd.DataFrame:
    """
    Load all historical candidate files to show evolution over time
    
    Returns:
        DataFrame with historical candidates or empty DataFrame
    """
    # TODO: Implement if we save historical snapshots
    return pd.DataFrame()


def get_update_metadata() -> Optional[dict]:
    """
    Load update metadata from last pipeline run
    
    Returns:
        Metadata dict or None if not found
    """
    import json
    
    metadata_file = Path('data/raw/timeseries_6h/_update_metadata.json')
    
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            return json.load(f)
    
    return None
