#!/usr/bin/env python3
"""
Main scraper script. Run this to:
1. Crawl DA website for PDF links
2. Download all PDFs
3. Parse them into structured data
4. Store in SQLite database
"""
import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from scraper.crawler import crawl_pdf_links
from scraper.downloader import download_pdfs
from scraper.parser import parse_pdf_batch
from database import init_db, store_parsed_data, get_stats


def main(max_pdfs: int = None, daily_only: bool = True):
    """Run the full scrape pipeline."""
    print("=" * 60)
    print("🇵🇭 PH Price Index — Scraper")
    print("=" * 60)
    
    # 1. Initialize database
    print("\n[1/4] Initializing database...")
    init_db()
    
    # 2. Crawl for PDF links
    print("\n[2/4] Crawling DA website...")
    links = crawl_pdf_links()
    
    # 3. Download PDFs
    print("\n[3/4] Downloading PDFs...")
    daily_links = links["daily"]
    
    if max_pdfs:
        daily_links = daily_links[:max_pdfs]
    
    downloaded = download_pdfs(daily_links, pdf_type="daily", delay=0.3)
    
    # 4. Parse and store
    print("\n[4/4] Parsing PDFs and storing data...")
    parsed = parse_pdf_batch(downloaded)
    store_parsed_data(parsed)
    
    # Summary
    stats = get_stats()
    print("\n" + "=" * 60)
    print("✅ Scrape complete!")
    print(f"   Commodities: {stats.get('total_commodities', 0)}")
    print(f"   Prices:      {stats.get('total_prices', 0)}")
    print(f"   Dates:       {stats.get('total_dates', 0)}")
    print(f"   Range:       {stats.get('first_date', 'N/A')} → {stats.get('last_date', 'N/A')}")
    print("=" * 60)
    
    return stats


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="PH Price Index Scraper")
    parser.add_argument("--max", type=int, help="Max PDFs to download", default=None)
    parser.add_argument("--test", action="store_true", help="Test mode (5 PDFs)")
    args = parser.parse_args()
    
    max_pdfs = 5 if args.test else args.max
    main(max_pdfs=max_pdfs)
