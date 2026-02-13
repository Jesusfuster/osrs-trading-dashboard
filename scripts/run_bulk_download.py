#!/usr/bin/env python3
"""
Run bulk historical data download

Usage:
    python scripts/run_bulk_download.py
"""
from src.data_collection.bulk_download import BulkDownloader

if __name__ == "__main__":
    downloader = BulkDownloader()
    stats = downloader.run()
    
    print("\n✅ Bulk download completed!")
    print(f"Check data/raw/timeseries_6h/ for downloaded files")