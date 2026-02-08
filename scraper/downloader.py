"""
Download PDFs from DA website with rate limiting and resume support.
"""
import os
import time
import hashlib
import requests
from typing import List, Dict

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) PH-Price-Index-Bot/1.0"
}

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "pdfs")


def download_pdfs(links: List[Dict], pdf_type: str = "daily", delay: float = 0.5) -> List[Dict]:
    """Download PDFs, skipping already downloaded ones."""
    out_dir = os.path.join(DATA_DIR, pdf_type)
    os.makedirs(out_dir, exist_ok=True)
    
    results = []
    total = len(links)
    
    for i, link in enumerate(links):
        url = link["url"]
        filename = _url_to_filename(url, link)
        filepath = os.path.join(out_dir, filename)
        
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            results.append({**link, "filepath": filepath, "status": "cached"})
            continue
        
        print(f"[downloader] ({i+1}/{total}) Downloading {filename}...")
        
        try:
            resp = requests.get(url, headers=HEADERS, timeout=60)
            resp.raise_for_status()
            
            with open(filepath, "wb") as f:
                f.write(resp.content)
            
            results.append({**link, "filepath": filepath, "status": "downloaded"})
            time.sleep(delay)  # Be nice to the server
            
        except Exception as e:
            print(f"[downloader] FAILED {filename}: {e}")
            results.append({**link, "filepath": None, "status": "failed", "error": str(e)})
    
    downloaded = sum(1 for r in results if r["status"] == "downloaded")
    cached = sum(1 for r in results if r["status"] == "cached")
    failed = sum(1 for r in results if r["status"] == "failed")
    print(f"[downloader] Done: {downloaded} new, {cached} cached, {failed} failed")
    
    return results


def _url_to_filename(url: str, link: Dict) -> str:
    """Generate a clean filename from the URL and metadata."""
    # Use the date if available for daily
    if link.get("date"):
        return f"daily-{link['date']}.pdf"
    
    # Use the last part of the URL
    basename = url.split("/")[-1]
    # Clean up any weird characters
    basename = basename.replace("%20", "-").replace(" ", "-")
    return basename
