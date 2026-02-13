#!/usr/bin/env python3
"""
Analyze all items and filter to find top candidates

This script:
1. Performs quick analysis on ALL items (4,400+)
2. Applies progressive filtering (L1 → L2 → L3)
3. Runs backtesting on candidates
4. Outputs top 50 candidates maximum

Uses user configuration for risk profile and filters.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from tqdm import tqdm
from datetime import datetime, timedelta
from src.utils.config import config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


# Load user configuration
import yaml

def load_user_config():
    """Load user configuration from config.yaml"""
    config_file = Path('config.yaml')
    
    if not config_file.exists():
        logger.error("config.yaml not found!")
        sys.exit(1)
    
    with open(config_file, 'r') as f:
        user_config = yaml.safe_load(f)
    
    return user_config


class CandidateAnalyzer:
    """Analyzes all items and filters candidates"""
    
    def __init__(self, user_config):
        self.user_config = user_config
        self.timeseries_dir = Path(config.get('storage', 'raw_dir')) / 'timeseries_6h'
        self.mapping_file = Path(config.get('storage', 'raw_dir')) / 'mapping.parquet'
        self.output_dir = Path(config.get('storage', 'processed_dir'))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get risk profile filters
        risk_profile = user_config.get('risk_profile', 'moderate')
        self.filters_l1 = user_config['risk_profiles'][risk_profile]['level1']
        self.filters_l2 = user_config['risk_profiles'][risk_profile]['level2']
        self.filters_l3 = user_config['risk_profiles'][risk_profile]['level3']
        
        logger.info(f"Using risk profile: {risk_profile}")
    
    def quick_analyze_item(self, item_id):
        """Quick analysis of an item (basic stats only)"""
        file_path = self.timeseries_dir / f'item_{item_id}.parquet'
        
        if not file_path.exists():
            return None
        
        try:
            df = pd.read_parquet(file_path)
            
            if len(df) == 0:
                return None
            
            # Basic metrics
            total_volume = df['highPriceVolume'].sum() + df['lowPriceVolume'].sum()
            avg_high = df['avgHighPrice'].mean()
            avg_low = df['avgLowPrice'].mean()
            last_timestamp = df['datetime'].max()
            
            return {
                'item_id': item_id,
                'records': len(df),
                'total_volume': total_volume,
                'avg_high_price': avg_high,
                'avg_low_price': avg_low,
                'avg_spread_gp': avg_high - avg_low,
                'avg_spread_pct': ((avg_high - avg_low) / avg_low * 100) if avg_low > 0 else 0,
                'last_timestamp': last_timestamp,
                'days_since_last_activity': (pd.Timestamp.now() - last_timestamp).days,
            }
        except Exception as e:
            logger.debug(f"Error analyzing item {item_id}: {e}")
            return None
    
    def detailed_analyze_item(self, item_id):
        """Detailed analysis (trading frequency, volatility)"""
        file_path = self.timeseries_dir / f'item_{item_id}.parquet'
        
        if not file_path.exists():
            return None
        
        try:
            df = pd.read_parquet(file_path)
            
            if len(df) == 0:
                return None
            
            days_range = (df['datetime'].max() - df['datetime'].min()).days
            avg_daily_volume = (df['highPriceVolume'].sum() + df['lowPriceVolume'].sum()) / max(1, days_range)
            
            # Trading frequency
            trading_frequency = ((df['highPriceVolume'] + df['lowPriceVolume']) > 0).mean()
            
            # Volatility
            df['spread_pct'] = ((df['avgHighPrice'] - df['avgLowPrice']) / df['avgLowPrice']) * 100
            spread_volatility = df['spread_pct'].std()
            price_volatility = df['avgHighPrice'].std() / df['avgHighPrice'].mean() if df['avgHighPrice'].mean() > 0 else 0
            
            return {
                'item_id': item_id,
                'avg_daily_volume': avg_daily_volume,
                'trading_frequency': trading_frequency,
                'spread_volatility': spread_volatility,
                'price_volatility': price_volatility,
            }
        except Exception as e:
            logger.debug(f"Error in detailed analysis for item {item_id}: {e}")
            return None
    
    def simulate_flipping(self, item_id, capital, ge_tax_rate=0.01):
        """Simulate conservative flipping strategy"""
        file_path = self.timeseries_dir / f'item_{item_id}.parquet'
        
        if not file_path.exists():
            return None
        
        try:
            df = pd.read_parquet(file_path).sort_values('datetime')
            
            if len(df) < 2:
                return None
            
            trades = []
            
            for i in range(len(df)):
                current = df.iloc[i]
                
                buy_price = current['avgLowPrice']
                sell_price = current['avgHighPrice']
                
                if buy_price <= 0 or sell_price <= 0:
                    continue
                
                quantity = int(capital / buy_price)
                
                if quantity == 0:
                    continue
                
                gross_profit = (sell_price - buy_price) * quantity
                tax = sell_price * quantity * ge_tax_rate
                net_profit = gross_profit - tax
                roi = (net_profit / (buy_price * quantity)) * 100
                
                trades.append({
                    'net_profit': net_profit,
                    'roi': roi,
                })
            
            if not trades:
                return None
            
            df_trades = pd.DataFrame(trades)
            
            return {
                'total_trades': len(df_trades),
                'profitable_trades': (df_trades['net_profit'] > 0).sum(),
                'win_rate': (df_trades['net_profit'] > 0).mean() * 100,
                'avg_roi': df_trades['roi'].mean(),
                'total_profit': df_trades['net_profit'].sum(),
                'sharpe_ratio': df_trades['roi'].mean() / df_trades['roi'].std() if df_trades['roi'].std() > 0 else 0,
            }
        except Exception as e:
            logger.debug(f"Error in simulation for item {item_id}: {e}")
            return None
    
    def run(self):
        """Execute full analysis pipeline"""
        logger.info("="*80)
        logger.info("STARTING CANDIDATE ANALYSIS")
        logger.info("="*80)
        
        # Load mapping
        df_mapping = pd.read_parquet(self.mapping_file)
        item_ids = df_mapping['id'].tolist()
        
        logger.info(f"Total items in mapping: {len(item_ids):,}")
        
        # PHASE 1: Quick analysis of ALL items
        logger.info("\n📊 Phase 1: Quick analysis of all items...")
        quick_stats = []
        
        for item_id in tqdm(item_ids, desc="Quick analysis"):
            stats = self.quick_analyze_item(item_id)
            if stats:
                quick_stats.append(stats)
        
        df_quick = pd.DataFrame(quick_stats)
        df_quick = df_quick.merge(
            df_mapping[['id', 'name', 'members', 'limit', 'highalch', 'lowalch']],
            left_on='item_id',
            right_on='id',
            how='left'
        )
        
        logger.info(f"Items with data: {len(df_quick):,}")
        
        # Save quick analysis
        df_quick.to_parquet(self.output_dir / 'all_items_quick_analysis.parquet')
        
        # PHASE 2: Level 1 filtering
        logger.info("\n🔍 Phase 2: Level 1 filtering (basic survival)...")
        
        df_level1 = df_quick[
            (df_quick['total_volume'] >= self.filters_l1['min_total_volume']) &
            (df_quick['records'] >= self.filters_l1['min_records']) &
            (df_quick['days_since_last_activity'] <= self.filters_l1['max_days_since_activity']) &
            (df_quick['limit'].notna()) &
            (df_quick['limit'] > 0)
        ].copy()
        
        logger.info(f"Level 1: {len(df_level1):,} items passed")
        
        # PHASE 3: Detailed analysis of Level 1
        logger.info("\n📊 Phase 3: Detailed analysis of Level 1 items...")
        
        detailed_stats = []
        for item_id in tqdm(df_level1['item_id'].tolist(), desc="Detailed analysis"):
            stats = self.detailed_analyze_item(item_id)
            if stats:
                detailed_stats.append(stats)
        
        df_detailed = pd.DataFrame(detailed_stats)
        df_level1 = df_level1.merge(df_detailed, on='item_id', how='left')
        
        # PHASE 4: Level 2 filtering
        logger.info("\n🔍 Phase 4: Level 2 filtering (quality)...")
        
        volume_threshold = df_level1['avg_daily_volume'].quantile(self.filters_l2['min_volume_percentile'] / 100)
        
        df_level2 = df_level1[
            (df_level1['avg_spread_pct'] >= self.filters_l2['min_spread_pct']) &
            (df_level1['avg_spread_pct'] <= self.filters_l2['max_spread_pct']) &
            (df_level1['avg_daily_volume'] >= volume_threshold) &
            (df_level1['trading_frequency'] >= self.filters_l2['min_trading_frequency']) &
            (df_level1['avg_high_price'] >= self.filters_l2['min_price']) &
            (df_level1['avg_high_price'] <= self.filters_l2['max_price'])
        ].copy()
        
        logger.info(f"Level 2: {len(df_level2):,} items passed")
        
        # PHASE 5: Backtesting
        logger.info("\n🎮 Phase 5: Backtesting Level 2 items...")
        
        capital = self.user_config.get('capital', 100000)
        ge_tax = self.user_config.get('ge_tax_rate', 0.01)
        
        backtest_results = []
        for item_id in tqdm(df_level2['item_id'].tolist(), desc="Backtesting"):
            metrics = self.simulate_flipping(item_id, capital, ge_tax)
            if metrics:
                backtest_results.append({
                    'item_id': item_id,
                    **metrics
                })
        
        df_backtest = pd.DataFrame(backtest_results)
        df_level2 = df_level2.merge(df_backtest, on='item_id', how='left')
        
        # PHASE 6: Level 3 filtering
        logger.info("\n🔍 Phase 6: Level 3 filtering (top performers)...")
        
        df_level3 = df_level2[
            (df_level2['win_rate'] >= self.filters_l3['min_win_rate']) &
            (df_level2['avg_roi'] >= self.filters_l3['min_avg_roi']) &
            (df_level2['sharpe_ratio'] >= self.filters_l3['min_sharpe_ratio'])
        ].copy()
        
        logger.info(f"Level 3: {len(df_level3):,} items passed")
        
        # PHASE 7: Calculate final score and limit to top 50
        logger.info("\n📊 Phase 7: Calculating final scores...")
        
        if len(df_level3) > 0:
            # Normalize metrics
            df_level3['norm_volume'] = df_level3['avg_daily_volume'] / df_level3['avg_daily_volume'].max()
            df_level3['norm_spread'] = df_level3['avg_spread_pct'] / 20
            df_level3['norm_win_rate'] = df_level3['win_rate'] / 100
            df_level3['norm_roi'] = df_level3['avg_roi'] / 20
            df_level3['norm_sharpe'] = df_level3['sharpe_ratio'] / df_level3['sharpe_ratio'].max()
            
            # Weighted score
            df_level3['final_score'] = (
                df_level3['norm_volume'] * 0.25 +
                df_level3['norm_spread'] * 0.15 +
                df_level3['norm_win_rate'] * 0.3 +
                df_level3['norm_roi'] * 0.2 +
                df_level3['norm_sharpe'] * 0.1
            )
            
            # Sort and limit to top 50
            df_level3 = df_level3.sort_values('final_score', ascending=False).head(50)
            
            logger.info(f"Final candidates (max 50): {len(df_level3):,}")
        
        # Save results
        logger.info("\n💾 Saving results...")
        
        df_level1.to_parquet(self.output_dir / 'level1_filtered.parquet')
        df_level2.to_parquet(self.output_dir / 'level2_filtered.parquet')
        
        if len(df_level3) > 0:
            risk_profile = self.user_config.get('risk_profile', 'moderate')
            df_level3.to_parquet(self.output_dir / f'final_candidates_{risk_profile}.parquet')
            
            # Also save as CSV for easy viewing
            df_level3[['name', 'avg_high_price', 'avg_spread_pct', 'win_rate', 
                       'avg_roi', 'sharpe_ratio', 'final_score']].to_csv(
                self.output_dir / f'final_candidates_{risk_profile}.csv',
                index=False
            )
        
        # Summary
        logger.info("="*80)
        logger.info("ANALYSIS COMPLETED")
        logger.info("="*80)
        logger.info(f"Pipeline: {len(item_ids):,} → {len(df_level1):,} → {len(df_level2):,} → {len(df_level3):,}")
        
        if len(df_level3) > 0:
            logger.info(f"\nTop 5 Candidates:")
            for i, row in df_level3.head(5).iterrows():
                logger.info(f"  {row['name']}: Spread {row['avg_spread_pct']:.1f}%, Win Rate {row['win_rate']:.0f}%, ROI {row['avg_roi']:.1f}%")
        else:
            logger.warning("No candidates found matching criteria!")
        
        return df_level3


if __name__ == "__main__":
    # Load user config
    user_config = load_user_config()
    
    # Run analysis
    analyzer = CandidateAnalyzer(user_config)
    df_candidates = analyzer.run()
    
    if len(df_candidates) > 0:
        print(f"\n✅ Analysis completed! {len(df_candidates)} candidates identified")
    else:
        print("\n⚠️  No candidates found. Try a less restrictive risk profile.")
        sys.exit(1)
