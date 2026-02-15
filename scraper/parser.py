"""
Parse DA price monitoring PDFs into structured data.

Strategy:
1. Try PyPDF2 text extraction first (fast, works for text-based PDFs)
2. If text extraction yields garbage/empty → try tabula-py for table extraction
3. If both fail → flag for OCR (handled separately)

The parser handles inconsistencies in formatting across different dates.
"""
import re
import os
import json
from typing import List, Dict, Optional, Tuple
from PyPDF2 import PdfReader

# Categories and their expected commodities (flexible — new ones auto-detected)
KNOWN_CATEGORIES = [
    "IMPORTED COMMERCIAL RICE",
    "LOCAL COMMERCIAL RICE",
    "CORN PRODUCTS",
    "LEGUMES",
    "FISH PRODUCTS",
    "BEEF MEAT PRODUCTS",
    "CARABEEF MEAT PRODUCTS",
    "PORK MEAT PRODUCTS",
    "CHICKEN MEAT PRODUCTS",
    "EGGS",
    "VEGETABLES",
    "FRUITS",
    "SPICES",
    "COOKING OIL",
    "SUGAR",
    "PROCESSED FOOD",
    "ROOT CROPS",
    "LOWLAND VEGETABLES",
    "HIGHLAND VEGETABLES",
    "LEAFY VEGETABLES",
    "FRUIT VEGETABLES",
]


def parse_daily_pdf(filepath: str, date: str = None) -> Dict:
    """Parse a daily price index PDF into structured data."""
    result = {
        "date": date,
        "source_file": os.path.basename(filepath),
        "parse_method": None,
        "commodities": [],
        "errors": [],
    }
    
    try:
        reader = PdfReader(filepath)
        all_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                all_text += text + "\n"
        
        if not all_text.strip():
            result["parse_method"] = "failed_empty"
            result["errors"].append("No text extracted — likely image-based PDF")
            return result
        
        # Check if text looks like actual data vs garbage
        if _is_garbage_text(all_text):
            result["parse_method"] = "failed_garbage"
            result["errors"].append("Extracted text appears to be garbage — likely image-based PDF")
            return result
        
        # Extract date from PDF if not provided
        if not date:
            date = _extract_date_from_text(all_text)
            result["date"] = date
        
        # Parse the structured price data
        commodities = _parse_price_text(all_text)
        result["commodities"] = commodities
        result["parse_method"] = "text"
        
    except Exception as e:
        result["parse_method"] = "failed_error"
        result["errors"].append(str(e))
    
    return result


def _is_garbage_text(text: str) -> bool:
    """Check if extracted text is garbage (image-based PDF artifact)."""
    if len(text.strip()) < 50:
        return True
    
    # Check ratio of readable vs non-readable characters
    readable = sum(1 for c in text if c.isalnum() or c.isspace() or c in ".,/()-₱")
    total = len(text)
    if total > 0 and readable / total < 0.4:
        return True
    
    # Check if we find at least some expected keywords
    keywords = ["rice", "price", "commodity", "peso", "pork", "chicken", "fish", "beef"]
    text_lower = text.lower()
    found = sum(1 for k in keywords if k in text_lower)
    if found < 2:
        return True
    
    return False


def _extract_date_from_text(text: str) -> Optional[str]:
    """Extract date from PDF text content."""
    months = {
        "january": "01", "february": "02", "march": "03", "april": "04",
        "may": "05", "june": "06", "july": "07", "august": "08",
        "september": "09", "october": "10", "november": "11", "december": "12",
    }
    
    for month_name, month_num in months.items():
        # Handle split text like "Febr uary" or "Janu ary"
        month_pattern = month_name[:4] + r'\s*' + month_name[4:]
        pattern = rf'{month_pattern}\s+(\d{{1,2}}),?\s*(\d{{4}})'
        match = re.search(pattern, text.lower())
        if match:
            day = int(match.group(1))
            year = int(match.group(2))
            return f"{year}-{month_num}-{day:02d}"
    
    return None


def _parse_price_text(text: str) -> List[Dict]:
    """Parse commodity prices from extracted text."""
    commodities = []
    current_category = None
    
    lines = text.split("\n")
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if not line or _is_header_line(line):
            i += 1
            continue
        
        # Check if this is a category header
        cat = _detect_category(line)
        if cat:
            current_category = cat
            i += 1
            continue
        
        # Skip known non-data lines
        if _is_skip_line(line):
            i += 1
            continue
        
        # Try to parse as a commodity line
        commodity = _parse_commodity_line(line, lines, i, current_category)
        if commodity:
            commodities.append(commodity)
        
        i += 1
    
    return commodities


def _is_header_line(line: str) -> bool:
    """Check if line is a page header/footer."""
    patterns = [
        r'^Page \d+ of \d+',
        r'^Department of Agriculture',
        r'^DAILY PRICE INDEX',
        r'^National Capital Region',
        r'^Prevailing Retail Price',
        r'^COMMODITY\s+SPECIFICATION',
        r'^PREVAILING',
        r'^RETAIL PRICE',
        r'^UNIT \(P/UNIT\)',
        r'^\(.*\d{4}\)',  # Date in parentheses
    ]
    for p in patterns:
        if re.match(p, line, re.IGNORECASE):
            return True
    return False


def _is_skip_line(line: str) -> bool:
    """Check if line should be skipped."""
    skip = [
        "source:", "note:", "disclaimer", "prepared by",
        "checked by", "approved by", "page", "p/unit",
    ]
    lower = line.lower().strip()
    return any(lower.startswith(s) for s in skip) or len(lower) < 3


def _detect_category(line: str) -> Optional[str]:
    """Detect if a line is a category header."""
    upper = line.upper().strip()
    
    for cat in KNOWN_CATEGORIES:
        if cat in upper:
            return cat
    
    # Detect category-like patterns (ALL CAPS with key words)
    if re.match(r'^[A-Z\s]{10,}$', upper) and any(w in upper for w in 
        ["RICE", "CORN", "FISH", "MEAT", "CHICKEN", "PORK", "BEEF", "VEGETABLE",
         "FRUIT", "SPICE", "OIL", "SUGAR", "EGG", "LEGUME", "PROCESSED", "ROOT",
         "CARABEEF", "LOWLAND", "HIGHLAND", "LEAFY"]):
        return upper.strip()
    
    return None


def _parse_commodity_line(line: str, lines: List[str], idx: int, category: str) -> Optional[Dict]:
    """Parse a single commodity line into structured data."""
    # Price pattern: number with optional decimal, or "n/a"
    price_pattern = r'(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)\s*$'
    na_pattern = r'n/a\s*$'
    
    # Check if this line is a continuation of a wrapped specification from the previous line.
    # DA PDFs often wrap long specs like:
    #   "Broccoli, Local  Medium (8 -10 cm"
    #   "diameter/bunch hd)  160.00"
    # The second line starts with a lowercase word or spec fragment and has a price at the end.
    if idx > 0:
        prev_line = lines[idx - 1].strip() if idx - 1 < len(lines) else ""
        # Detect continuation: line starts lowercase/paren/digit and previous line has NO price
        starts_like_continuation = bool(re.match(r'^[a-z()\d]', line))
        prev_has_no_price = not re.search(price_pattern, prev_line) and not re.search(na_pattern, prev_line, re.IGNORECASE)
        prev_has_text = len(prev_line) > 5 and not _is_header_line(prev_line) and not _is_skip_line(prev_line)
        
        if starts_like_continuation and prev_has_no_price and prev_has_text:
            # This is a wrapped line — merge with previous and parse the combined result
            combined = prev_line + " " + line
            price_match_c = re.search(price_pattern, combined)
            na_match_c = re.search(na_pattern, combined, re.IGNORECASE)
            
            if price_match_c:
                price_str = price_match_c.group(1).replace(",", "")
                price = float(price_str)
                text_part = combined[:price_match_c.start()].strip()
            elif na_match_c:
                price = None
                text_part = combined[:na_match_c.start()].strip()
            else:
                return None
            
            if not text_part or len(text_part) < 2:
                return None
            
            name, spec = _split_name_spec(text_part)
            if not name or len(name) < 2:
                return None
            if name.upper() == name and len(name) > 30:
                return None
            
            return {
                "category": category,
                "name": name.strip(),
                "specification": spec.strip() if spec else None,
                "price": price,
                "unit": "PHP/kg",
            }

    # Try to find price at end of line
    price_match = re.search(price_pattern, line)
    na_match = re.search(na_pattern, line, re.IGNORECASE)
    
    if price_match:
        price_str = price_match.group(1).replace(",", "")
        price = float(price_str)
        text_part = line[:price_match.start()].strip()
    elif na_match:
        price = None
        text_part = line[:na_match.start()].strip()
    else:
        return None
    
    if not text_part:
        return None
    
    # Split text into commodity name and specification
    name, spec = _split_name_spec(text_part)
    
    if not name or len(name) < 2:
        return None
    
    # Skip if it looks like a header
    if name.upper() == name and len(name) > 30:
        return None
    
    return {
        "category": category,
        "name": name.strip(),
        "specification": spec.strip() if spec else None,
        "price": price,
        "unit": "PHP/kg",  # Default, most are per kg or per unit
    }


def _split_name_spec(text: str) -> Tuple[str, str]:
    """Split commodity text into name and specification."""
    # Common spec patterns
    spec_patterns = [
        r'(.*?)\s{2,}(.*)',  # Two or more spaces separate name from spec
        r'(.*?),\s*(.*)',     # Comma separator
    ]
    
    # Try double-space split first
    match = re.match(r'(.*?)\s{2,}(.*)', text)
    if match:
        return match.group(1), match.group(2)
    
    # Check for known spec keywords
    spec_keywords = [
        r'(.*?)\s+((?:Medium|Large|Small|Fresh|Frozen|Whole|Cob|Male|Female|Local|Imported).*)',
        r'(.*?)\s+(\d+%?\s*broken.*)',
        r'(.*?)\s+(Meat\s+with.*)',
        r'(.*?)\s+(White\s+Rice)',
    ]
    for pattern in spec_keywords:
        match = re.match(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1), match.group(2)
    
    return text, None


def parse_pdf_batch(pdf_results: List[Dict]) -> List[Dict]:
    """Parse a batch of downloaded PDFs."""
    parsed = []
    total = len(pdf_results)
    success = 0
    failed = 0
    
    for i, pdf in enumerate(pdf_results):
        if not pdf.get("filepath") or pdf.get("status") == "failed":
            continue
        
        date = pdf.get("date")
        filepath = pdf["filepath"]
        
        print(f"[parser] ({i+1}/{total}) Parsing {os.path.basename(filepath)}...")
        
        result = parse_daily_pdf(filepath, date)
        
        if result["commodities"]:
            success += 1
            print(f"  → {len(result['commodities'])} commodities extracted")
        else:
            failed += 1
            print(f"  → FAILED: {result.get('errors', ['unknown'])}")
        
        parsed.append(result)
    
    print(f"\n[parser] Done: {success} success, {failed} failed out of {total}")
    return parsed


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        result = parse_daily_pdf(sys.argv[1])
        print(json.dumps(result, indent=2))
