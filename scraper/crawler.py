"""
Crawl da.gov.ph/price-monitoring to extract all PDF links.
Handles both Daily Price Index and Weekly Average Prices.
"""
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict

BASE_URL = "https://www.da.gov.ph/price-monitoring/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) PH-Price-Index-Bot/1.0"
}


def crawl_pdf_links() -> Dict[str, List[Dict]]:
    """Crawl the DA price monitoring page and extract all PDF links."""
    print("[crawler] Fetching DA price monitoring page...")
    resp = requests.get(BASE_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    
    soup = BeautifulSoup(resp.text, "html.parser")
    
    all_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.endswith(".pdf"):
            text = a.get_text(strip=True)
            all_links.append({"url": href, "text": text})
    
    daily = []
    weekly = []
    cigarette = []
    other = []
    
    for link in all_links:
        url_lower = link["url"].lower()
        text_lower = link["text"].lower()
        
        if "weekly" in url_lower or "weekly" in text_lower:
            link["type"] = "weekly"
            link["date_range"] = parse_weekly_date(link["text"])
            weekly.append(link)
        elif "cigarette" in url_lower or "cigarette" in text_lower:
            link["type"] = "cigarette"
            cigarette.append(link)
        elif "daily" in url_lower or "dpi" in url_lower or "price-monitoring" in url_lower:
            link["type"] = "daily"
            link["date"] = parse_daily_date(link["text"], link["url"])
            daily.append(link)
        else:
            # Try to detect daily by date pattern in text
            date = parse_daily_date(link["text"], link["url"])
            if date:
                link["type"] = "daily"
                link["date"] = date
                daily.append(link)
            else:
                link["type"] = "other"
                other.append(link)
    
    print(f"[crawler] Found: {len(daily)} daily, {len(weekly)} weekly, {len(cigarette)} cigarette, {len(other)} other")
    
    return {
        "daily": daily,
        "weekly": weekly,
        "cigarette": cigarette,
        "other": other,
    }


def parse_daily_date(text: str, url: str) -> str:
    """Try to extract a date from the link text or URL."""
    # Common formats in text: "February 8, 2026", "January 31, 2026"
    months = {
        "january": "01", "february": "02", "march": "03", "april": "04",
        "may": "05", "june": "06", "july": "07", "august": "08",
        "september": "09", "october": "10", "november": "11", "december": "12",
        "marhc": "03",  # they have typos!
    }
    
    # Try text first
    for month_name, month_num in months.items():
        pattern = rf'{month_name}\s+(\d{{1,2}}),?\s*(\d{{4}})'
        match = re.search(pattern, text.lower())
        if match:
            day = int(match.group(1))
            year = int(match.group(2))
            return f"{year}-{month_num}-{day:02d}"
    
    # Try URL patterns like MMDDYYYY
    match = re.search(r'(\d{2})(\d{2})(\d{4})-PRICE', url, re.IGNORECASE)
    if match:
        month, day, year = match.group(1), match.group(2), match.group(3)
        return f"{year}-{month}-{day}"
    
    # Try URL patterns like Month-Day-Year
    for month_name, month_num in months.items():
        pattern = rf'{month_name}-(\d{{1,2}})-(\d{{4}})'
        match = re.search(pattern, url.lower())
        if match:
            day = int(match.group(1))
            year = int(match.group(2))
            return f"{year}-{month_num}-{day:02d}"
    
    return None


def parse_weekly_date(text: str) -> Dict:
    """Parse weekly date range from text like 'January 26-31, 2026'."""
    # This is complex due to cross-month ranges
    # Return raw text for now, can be refined
    return {"raw": text}


if __name__ == "__main__":
    results = crawl_pdf_links()
    for dtype, links in results.items():
        print(f"\n=== {dtype.upper()} ({len(links)}) ===")
        for link in links[:3]:
            print(f"  {link.get('date', link.get('text', ''))}: {link['url'][:80]}...")
