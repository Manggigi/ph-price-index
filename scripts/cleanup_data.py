#!/usr/bin/env python3
"""
PH Price Index — Data Cleanup Script
Removes junk commodities from PDF parsing errors, fixes names, merges duplicates.
Run: python scripts/cleanup_data.py
"""
import sqlite3
import re
import os
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "prices.db")

# === VALID CATEGORIES ===
# Only these are real DA categories
VALID_CATEGORIES = {
    'LOCAL COMMERCIAL RICE',
    'IMPORTED COMMERCIAL RICE', 
    'CORN PRODUCTS',
    'FISH PRODUCTS',
    'BEEF MEAT PRODUCTS',
    'PORK MEAT PRODUCTS',
    'OTHER LIVESTOCK MEAT',
    'FRESH WHOLE CHICKEN',
    'FRESH PORK PRODUCTS',
    'FROZEN PORK PRODUCTS',
    'VEGETABLES',
    'LEGUMES',
    'FRUITS',
    'SPICES',
    'SUGAR',
    'COOKING OIL',
    'COCONUT OIL',
}

# Normalize category names (map messy -> clean)
CATEGORY_NORMALIZE = {
    'BEEF  MEAT  PRODUCTS': 'BEEF MEAT PRODUCTS',
    'PORK  MEAT  PRODUCTS': 'PORK MEAT PRODUCTS',
    'OTHER  LIVESTOCK  MEAT': 'OTHER LIVESTOCK MEAT',
    'CORN  PRODUCTS': 'CORN PRODUCTS',
    'OMMERCIAL RICE': 'LOCAL COMMERCIAL RICE',
}

# === CANONICAL COMMODITIES ===
# Map of (clean_name, category, clean_specification) for known good commodities.
# We'll keep commodities that match these patterns.
# Format: { canonical_name: { 'category': ..., 'spec': ..., 'match_patterns': [...] } }

CANONICAL = [
    # Rice - Local
    {'name': 'Fancy', 'category': 'LOCAL COMMERCIAL RICE', 'spec': 'White Rice', 'patterns': ['Fancy', '5 Fancy']},
    {'name': 'Premium', 'category': 'LOCAL COMMERCIAL RICE', 'spec': '5% broken', 'patterns': ['6 Premium']},
    {'name': 'Well Milled', 'category': 'LOCAL COMMERCIAL RICE', 'spec': '1-19% bran streak', 'patterns': ['7 Well Milled']},
    {'name': 'Regular Milled', 'category': 'LOCAL COMMERCIAL RICE', 'spec': '20-40% bran streak', 'patterns': ['8 Regular Milled']},
    # Rice - Imported
    {'name': 'Fancy', 'category': 'IMPORTED COMMERCIAL RICE', 'spec': 'White Rice', 'patterns': ['1 Fancy', 'Fancy']},
    {'name': 'Premium', 'category': 'IMPORTED COMMERCIAL RICE', 'spec': '5% broken', 'patterns': ['2 Premium', 'Premium']},
    {'name': 'Well Milled', 'category': 'IMPORTED COMMERCIAL RICE', 'spec': '1-19% bran streak', 'patterns': ['3 Well Milled', 'Well Milled']},
    {'name': 'Regular Milled', 'category': 'IMPORTED COMMERCIAL RICE', 'spec': '20-40% bran streak', 'patterns': ['4 Regular Milled', 'Regular Milled']},
    {'name': 'Special Rice', 'category': 'IMPORTED COMMERCIAL RICE', 'spec': 'White Rice', 'patterns': ['Special Rice', 'Special', 'Other Special Rice', 'Special/Fancy']},
    {'name': 'Basmati Rice', 'category': 'IMPORTED COMMERCIAL RICE', 'spec': None, 'patterns': ['Basmati Rice']},
    {'name': 'Glutinous Rice', 'category': 'IMPORTED COMMERCIAL RICE', 'spec': None, 'patterns': ['Glutinous Rice']},
    {'name': 'Jasponica/Japonica Rice', 'category': 'IMPORTED COMMERCIAL RICE', 'spec': None, 'patterns': ['Jasponica', 'Japonica']},
    # Corn
    {'name': 'Corn (White)', 'category': 'CORN PRODUCTS', 'spec': 'Cob, Glutinous', 'patterns': ['9 Corn (White)', 'Corn (White)']},
    {'name': 'Corn (Yellow)', 'category': 'CORN PRODUCTS', 'spec': 'Cob, Sweet Corn', 'patterns': ['10 Corn (Yellow)', 'Corn (Yellow)']},
    {'name': 'Corn Grits (White, Food Grade)', 'category': 'CORN PRODUCTS', 'spec': None, 'patterns': ['11 Corn Grits (White']},
    {'name': 'Corn Grits (Yellow, Food Grade)', 'category': 'CORN PRODUCTS', 'spec': None, 'patterns': ['12 Corn Grits (Y']},
    {'name': 'Corn Cracked (Yellow, Feed Grade)', 'category': 'CORN PRODUCTS', 'spec': None, 'patterns': ['13 Corn Cracked']},
    {'name': 'Corn Grits (Feed Grade)', 'category': 'CORN PRODUCTS', 'spec': None, 'patterns': ['14 Corn Grits', 'Corn Grits (Feed']},
    # Fish
    {'name': 'Bangus (Large)', 'category': 'FISH PRODUCTS', 'spec': 'Large', 'patterns': ['15 Bangus', 'Bangus']},
    {'name': 'Bangus (Medium)', 'category': 'FISH PRODUCTS', 'spec': 'Medium (3-4 pcs/kg)', 'patterns': ['16 Bangus']},
    {'name': 'Tilapia', 'category': 'FISH PRODUCTS', 'spec': 'Medium (5-6 pcs/kg)', 'patterns': ['17 Tilapia', 'Tilapia']},
    {'name': 'Galunggong (Imported)', 'category': 'FISH PRODUCTS', 'spec': 'Medium', 'patterns': ['18 Galunggong', 'Galunggong']},
    {'name': 'Galunggong (Local)', 'category': 'FISH PRODUCTS', 'spec': 'Medium (12-14 pcs/kg)', 'patterns': ['19 Galunggong']},
    {'name': 'Alumahan', 'category': 'FISH PRODUCTS', 'spec': 'Medium (4-6 pcs/kg)', 'patterns': ['20 Alumahan', 'Alumahan']},
    {'name': 'Salmon Head (Local)', 'category': 'FISH PRODUCTS', 'spec': 'Local', 'patterns': ['21 Salmon Head']},
    {'name': 'Salmon Head (Imported)', 'category': 'FISH PRODUCTS', 'spec': 'Imported', 'patterns': ['22 Salmon Head']},
    {'name': 'Salmon Belly (Local)', 'category': 'FISH PRODUCTS', 'spec': 'Local', 'patterns': ['23 Salmon Belly']},
    {'name': 'Salmon Belly (Imported)', 'category': 'FISH PRODUCTS', 'spec': 'Imported', 'patterns': ['24 Salmon Belly']},
    {'name': 'Sardines (Tamban)', 'category': 'FISH PRODUCTS', 'spec': None, 'patterns': ['25 Sardin', 'Sardines (Tamban)']},
    {'name': 'Squid (Pusit Bisaya)', 'category': 'FISH PRODUCTS', 'spec': None, 'patterns': ['26 Squid (Pusit', 'Squid (Pusit']},
    {'name': 'Squid (Imported)', 'category': 'FISH PRODUCTS', 'spec': 'Imported', 'patterns': ['27 Squid']},
    {'name': 'Pompano (Local)', 'category': 'FISH PRODUCTS', 'spec': 'Local', 'patterns': ['28 Pomp']},
    {'name': 'Pompano (Imported)', 'category': 'FISH PRODUCTS', 'spec': 'Imported', 'patterns': ['29 Pompano']},
    {'name': 'Local Mackerel', 'category': 'FISH PRODUCTS', 'spec': 'Fresh', 'patterns': ['30 Local Mackerel']},
    {'name': 'Yellow-Fin Tuna (Tambakol)', 'category': 'FISH PRODUCTS', 'spec': 'Frozen', 'patterns': ['33 Yellow']},
    # Beef
    {'name': 'Beef Brisket', 'category': 'BEEF MEAT PRODUCTS', 'spec': 'Meat with Bones', 'patterns': ['Beef Brisket']},
    {'name': 'Beef Rump', 'category': 'BEEF MEAT PRODUCTS', 'spec': 'Lean Meat/Tapadera', 'patterns': ['Beef Rump']},
    # Pork
    {'name': 'Pork Kasim', 'category': 'PORK MEAT PRODUCTS', 'spec': None, 'patterns': ['Pork Kasim', 'Kasim']},
    {'name': 'Pork Liempo', 'category': 'PORK MEAT PRODUCTS', 'spec': None, 'patterns': ['Pork Liempo', 'Liempo']},
    {'name': 'Frozen Kasim', 'category': 'FROZEN PORK PRODUCTS', 'spec': None, 'patterns': ['Frozen Kasim']},
    {'name': 'Frozen Liempo', 'category': 'FROZEN PORK PRODUCTS', 'spec': None, 'patterns': ['Frozen Liempo']},
    # Other meat  
    {'name': 'Whole Chicken', 'category': 'OTHER LIVESTOCK MEAT', 'spec': None, 'patterns': ['Whole Chicken', 'Fresh Whole Chicken']},
    {'name': 'Chicken Egg (Medium)', 'category': 'OTHER LIVESTOCK MEAT', 'spec': 'Medium size (per piece)', 'patterns': ['Chicken Egg']},
    {'name': 'Chicken Egg (White, Small)', 'category': 'OTHER LIVESTOCK MEAT', 'spec': '51-55 grams/pc', 'patterns': ['Chicken Egg (White, Small)']},
    {'name': 'Chicken Egg (White, Medium)', 'category': 'OTHER LIVESTOCK MEAT', 'spec': '56-60 grams/pc', 'patterns': ['Chicken Egg (White, Medium)']},
    {'name': 'Chicken Egg (White, Large)', 'category': 'OTHER LIVESTOCK MEAT', 'spec': '61-65 grams/pc', 'patterns': ['Chicken Egg (White, Large)']},
    {'name': 'Chicken Egg (White, Extra Large)', 'category': 'OTHER LIVESTOCK MEAT', 'spec': '66-70 grams/pc', 'patterns': ['Chicken Egg (White, Extra Large)']},
    {'name': 'Chicken Egg (White, Jumbo)', 'category': 'OTHER LIVESTOCK MEAT', 'spec': '71+ grams/pc', 'patterns': ['Chicken Egg (White, Jumbo)']},
    {'name': 'Chicken Egg (Brown, Medium)', 'category': 'OTHER LIVESTOCK MEAT', 'spec': 'Medium', 'patterns': ['Chicken Egg (Brown, Medium)']},
    {'name': 'Chicken Egg (Brown, Large)', 'category': 'OTHER LIVESTOCK MEAT', 'spec': 'Large', 'patterns': ['Chicken Egg (Brown, Large)']},
    {'name': 'Chicken Egg (Brown, Extra Large)', 'category': 'OTHER LIVESTOCK MEAT', 'spec': 'Extra Large', 'patterns': ['Chicken Egg (Brown, Extra Large)']},
    # Vegetables
    {'name': 'Ampalaya', 'category': 'VEGETABLES', 'spec': '4-5 pcs/kg', 'patterns': ['Ampalaya']},
    {'name': 'Cabbage (Rare Ball)', 'category': 'VEGETABLES', 'spec': '510gm-1kg/head', 'patterns': ['Cabbage (Rare']},
    {'name': 'Cabbage (Wonder Ball)', 'category': 'VEGETABLES', 'spec': '510gm-1kg/head', 'patterns': ['Cabbage (Wonder']},
    {'name': 'Carrots', 'category': 'VEGETABLES', 'spec': None, 'patterns': ['Carrots', 'Carrot']},
    {'name': 'Chayote (Sayote)', 'category': 'VEGETABLES', 'spec': None, 'patterns': ['Sayote', 'Chayote']},
    {'name': 'Eggplant (Talong)', 'category': 'VEGETABLES', 'spec': None, 'patterns': ['Eggplant', 'Talong']},
    {'name': 'Habitchuelas', 'category': 'VEGETABLES', 'spec': None, 'patterns': ['Habitchuelas', 'Habichuelas']},
    {'name': 'Kalabasa', 'category': 'VEGETABLES', 'spec': None, 'patterns': ['Squash', 'Kalabasa']},
    {'name': 'Kangkong', 'category': 'VEGETABLES', 'spec': None, 'patterns': ['Kangkong']},
    {'name': 'Pechay Baguio', 'category': 'VEGETABLES', 'spec': None, 'patterns': ['Pechay Baguio']},
    {'name': 'Pechay Native', 'category': 'VEGETABLES', 'spec': None, 'patterns': ['Pechay Native', 'Pechay Tagalog']},
    {'name': 'Sitaw', 'category': 'VEGETABLES', 'spec': None, 'patterns': ['Sitaw']},
    {'name': 'Tomato', 'category': 'VEGETABLES', 'spec': '15-18 pcs/kg', 'patterns': ['Tomato']},
    {'name': 'Potato', 'category': 'VEGETABLES', 'spec': None, 'patterns': ['Potato']},
    # Legumes
    {'name': 'Munggo', 'category': 'LEGUMES', 'spec': None, 'patterns': ['Munggo', 'Mongo']},
    # Fruits
    {'name': 'Avocado', 'category': 'FRUITS', 'spec': None, 'patterns': ['Avocado']},
    {'name': 'Banana (Lakatan)', 'category': 'FRUITS', 'spec': '8-10 pcs/kg', 'patterns': ['Banana (Lakatan)', 'Banana ( Lakatan)']},
    {'name': 'Banana (Latundan)', 'category': 'FRUITS', 'spec': '10-12 pcs/kg', 'patterns': ['Banana (Latundan)', 'Banana ( Latundan)']},
    {'name': 'Banana (Saba)', 'category': 'FRUITS', 'spec': None, 'patterns': ['Banana (Saba)']},
    {'name': 'Calamansi', 'category': 'FRUITS', 'spec': None, 'patterns': ['Calamansi']},
    {'name': 'Mango (Carabao)', 'category': 'FRUITS', 'spec': 'Ripe, 3-4 pcs/kg', 'patterns': ['Mango (Carabao)', 'Mango']},
    {'name': 'Melon', 'category': 'FRUITS', 'spec': None, 'patterns': ['Melon']},
    {'name': 'Papaya', 'category': 'FRUITS', 'spec': 'Solo, Ripe, 2-3 pcs/kg', 'patterns': ['Papaya']},
    {'name': 'Pomelo', 'category': 'FRUITS', 'spec': None, 'patterns': ['Pomelo']},
    {'name': 'Watermelon', 'category': 'FRUITS', 'spec': None, 'patterns': ['Watermelon']},
    # Spices
    {'name': 'Garlic (Imported)', 'category': 'SPICES', 'spec': None, 'patterns': ['Garlic (Imported)']},
    {'name': 'Garlic (Local)', 'category': 'SPICES', 'spec': None, 'patterns': ['Garlic (Local)', 'Local Garlic']},
    {'name': 'Red Onion (Local)', 'category': 'SPICES', 'spec': 'Medium (150-300gm)', 'patterns': ['Red Onion (Local)', 'Sibuyas (Local)', 'Pulang Sibuyas']},
    {'name': 'Red Onion (Imported)', 'category': 'SPICES', 'spec': 'Medium (150-300gm)', 'patterns': ['Red Onion (Imported)', 'Sibuyas (Imported)']},
    {'name': 'White Onion (Imported)', 'category': 'SPICES', 'spec': None, 'patterns': ['White Onion']},
    {'name': 'Ginger', 'category': 'SPICES', 'spec': None, 'patterns': ['Ginger', 'Luya']},
    {'name': 'Chili (Labuyo)', 'category': 'SPICES', 'spec': None, 'patterns': ['Siling Labuyo', 'Chili']},
    # Sugar
    {'name': 'Brown Sugar', 'category': 'SUGAR', 'spec': None, 'patterns': ['Brown Sugar']},
    {'name': 'Refined Sugar', 'category': 'SUGAR', 'spec': None, 'patterns': ['Refined Sugar']},
    {'name': 'Washed Sugar', 'category': 'SUGAR', 'spec': None, 'patterns': ['Washed Sugar']},
    # Cooking Oil
    {'name': 'Coconut Oil (350ml)', 'category': 'COOKING OIL', 'spec': '350ml/bottle', 'patterns': ['Coconut']},
    {'name': 'Coconut Oil (1L)', 'category': 'COOKING OIL', 'spec': '1,000ml/bottle', 'patterns': []},
    {'name': 'Palm Oil (350ml)', 'category': 'COOKING OIL', 'spec': '350ml/bottle', 'patterns': ['Palm']},
    {'name': 'Palm Oil (1L)', 'category': 'COOKING OIL', 'spec': '1,000ml/bottle', 'patterns': []},
    # Salt (sometimes miscategorized under FRUITS)
    {'name': 'Salt (Iodized)', 'category': 'SPICES', 'spec': None, 'patterns': ['Salt (Iodized)']},
    {'name': 'Salt (Rock)', 'category': 'SPICES', 'spec': None, 'patterns': ['Salt (Rock)']},
]


def is_junk_name(name):
    """Check if a commodity name is clearly garbage."""
    if not name or len(name.strip()) < 3:
        return True
    n = name.strip()
    # Pure numbers / price data
    if re.match(r'^[\d.,\s\-#/N A]+$', n):
        return True
    # Contains #N/A or #DIV
    if '#N/A' in n or '#DIV' in n:
        return True
    # Looks like price ranges (100.00 200.00 etc)
    if re.match(r'^[\d.]+\s+[\d.]+', n) and not any(c.isalpha() for c in n[:20]):
        return True
    # PDF headers/footers
    junk_phrases = [
        'National Capital Region', 'Daily Price Index', 'DPI', 'Price Monitoring',
        'Department of Agriculture', 'AGRIBUSINESS', 'Bantay Presyo',
        'Highest Price', 'Lowest Price', 'Prevailing', 'AVAILABLE',
        'available only in', 'Number of Stalls', 'Yesterday', 'Today Yesterday',
        'stews and ground', 'lumbar vertebrae', 'loc. 2165', '8926', '8920',
        'anterior portion', 'PRELIMINARY', '-8203', 'RETAIL PRICE RANGE',
    ]
    for phrase in junk_phrases:
        if phrase.lower() in n.lower():
            return True
    # Market names with numbers (from chicken stall data)
    if re.match(r'^\d+[A-Z][a-z]', n):  # e.g. "10Trabajo Market"
        return True
    # Specification data leaked into name (contains "kg" followed by numbers)
    if re.search(r'kg\s+[\d.]+\s+[\d.]+', n):
        return True
    # Contains "None" as data artifact
    if 'None' in n and re.search(r'None\s*None', n):
        return True
    return False


def is_junk_category(cat):
    """Check if a category is clearly garbage."""
    if not cat:
        return True
    # Normalize
    c = CATEGORY_NORMALIZE.get(cat, cat)
    if c in VALID_CATEGORIES:
        return False
    # Everything else is junk
    return True


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    print("=" * 60)
    print("PH Price Index — Data Cleanup")
    print("=" * 60)
    
    # Stats before
    before_commodities = conn.execute("SELECT COUNT(*) FROM commodities").fetchone()[0]
    before_prices = conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
    print(f"\nBEFORE: {before_commodities:,} commodities, {before_prices:,} prices")
    
    # === PHASE 1: Identify commodities to KEEP ===
    # Strategy: For each canonical commodity, find matching DB entries and merge their prices
    # into one clean canonical entry. Delete everything else.
    
    all_commodities = conn.execute(
        "SELECT id, name, category, specification FROM commodities"
    ).fetchall()
    
    # Build mapping: canonical_index -> list of commodity IDs to merge
    canonical_to_ids = {i: [] for i in range(len(CANONICAL))}
    matched_ids = set()
    
    for row in all_commodities:
        cid, name, cat, spec = row['id'], row['name'], row['category'], row['specification']
        name_clean = (name or '').strip().rstrip(',')
        
        for idx, canon in enumerate(CANONICAL):
            # Check if this commodity matches any pattern for this canonical
            for pattern in canon['patterns']:
                pat_lower = pattern.lower().strip()
                name_lower = name_clean.lower().strip()
                
                # Strip leading numbers for comparison (e.g. "171 Calamansi" -> "Calamansi")
                name_stripped = re.sub(r'^\d+\s+', '', name_lower).strip()
                pat_stripped = re.sub(r'^\d+\s+', '', pat_lower).strip()
                
                # Match: exact, starts-with on stripped, or pattern is substring
                if (name_lower == pat_lower or 
                    name_stripped == pat_stripped or
                    name_lower.startswith(pat_lower) or
                    name_stripped.startswith(pat_stripped)):
                    
                    # Additional check: category should be compatible (or we're merging across categories)
                    # Some commodities are miscategorized (e.g. fish under LOCAL COMMERCIAL RICE)
                    canonical_to_ids[idx].append(cid)
                    matched_ids.add(cid)
                    break
    
    # === PHASE 2: Create clean canonical commodities and remap prices ===
    print("\n--- Creating clean commodities ---")
    
    # First, delete ALL existing commodities and create fresh ones
    # But we need to preserve prices, so we'll remap
    
    new_id_map = {}  # old_commodity_id -> new_commodity_id
    
    # Use a temp table approach: create new commodities with IDs starting after max existing
    max_id = conn.execute("SELECT MAX(id) FROM commodities").fetchone()[0] or 0
    
    kept_count = 0
    for idx, canon in enumerate(CANONICAL):
        old_ids = canonical_to_ids[idx]
        if not old_ids:
            continue
        
        # Count total prices for this canonical
        placeholders = ','.join('?' * len(old_ids))
        price_count = conn.execute(
            f"SELECT COUNT(*) FROM prices WHERE commodity_id IN ({placeholders})",
            old_ids
        ).fetchone()[0]
        
        if price_count == 0:
            continue
        
        # Use a unique temp name to avoid conflicts, we'll fix later
        max_id += 1
        temp_name = f"__CANON_{max_id}__{canon['name']}"
        cursor = conn.execute(
            "INSERT INTO commodities (name, category, specification, unit) VALUES (?, ?, ?, 'PHP/kg')",
            (temp_name, canon['category'], canon['spec'])
        )
        new_id = cursor.lastrowid
        kept_count += 1
        
        for old_id in old_ids:
            new_id_map[old_id] = new_id
        
        print(f"  ✓ {canon['name']} ({canon['category']}) — {len(old_ids)} variants, {price_count} prices")
    
    print(f"\nCreated {kept_count} clean commodities from {len(matched_ids)} matched variants")
    
    # === PHASE 3: Remap prices to new commodity IDs ===
    print("\n--- Remapping prices ---")
    
    # For each old_id -> new_id, update prices
    # Handle conflicts (same commodity_id + date + source_type) by keeping the one with the price
    remapped = 0
    conflicts = 0
    
    for old_id, new_id in new_id_map.items():
        # Get all prices for old commodity
        prices = conn.execute(
            "SELECT id, date, price, source_type, source_file FROM prices WHERE commodity_id = ?",
            (old_id,)
        ).fetchall()
        
        for p in prices:
            try:
                conn.execute(
                    "UPDATE prices SET commodity_id = ? WHERE id = ?",
                    (new_id, p['id'])
                )
                remapped += 1
            except sqlite3.IntegrityError:
                # Conflict - same date/source_type for this new commodity already exists
                # Keep the existing one, delete this duplicate
                conn.execute("DELETE FROM prices WHERE id = ?", (p['id'],))
                conflicts += 1
    
    print(f"  Remapped: {remapped:,} prices")
    print(f"  Conflicts resolved (duplicates removed): {conflicts:,}")
    
    # === PHASE 4: Delete old commodities and orphaned prices ===
    print("\n--- Cleaning up ---")
    
    # Get all new commodity IDs
    new_ids = set(new_id_map.values())
    
    # Delete prices that weren't remapped (belong to junk commodities)
    orphan_prices = conn.execute(
        f"SELECT COUNT(*) FROM prices WHERE commodity_id NOT IN ({','.join('?' * len(new_ids))})",
        list(new_ids)
    ).fetchone()[0]
    
    conn.execute(
        f"DELETE FROM prices WHERE commodity_id NOT IN ({','.join('?' * len(new_ids))})",
        list(new_ids)
    )
    print(f"  Deleted {orphan_prices:,} orphaned prices")
    
    # Delete old commodities (ones not in our new set)
    old_commodities = conn.execute(
        f"SELECT COUNT(*) FROM commodities WHERE id NOT IN ({','.join('?' * len(new_ids))})",
        list(new_ids)
    ).fetchone()[0]
    
    conn.execute(
        f"DELETE FROM commodities WHERE id NOT IN ({','.join('?' * len(new_ids))})",
        list(new_ids)
    )
    print(f"  Deleted {old_commodities:,} junk commodities")
    
    # === PHASE 5: Fix names (remove temp prefix) ===
    print("\n--- Fixing names ---")
    rows = conn.execute("SELECT id, name FROM commodities WHERE name LIKE '__CANON_%'").fetchall()
    for r in rows:
        clean = re.sub(r'^__CANON_\d+__', '', r['name'])
        conn.execute("UPDATE commodities SET name = ? WHERE id = ?", (clean, r['id']))
    conn.execute("UPDATE commodities SET name = TRIM(name)")
    conn.execute("UPDATE commodities SET name = RTRIM(name, ',') WHERE name LIKE '%,'")
    conn.execute("UPDATE commodities SET specification = TRIM(specification) WHERE specification IS NOT NULL")
    
    # === PHASE 6: VACUUM ===
    conn.commit()
    
    # Stats after
    after_commodities = conn.execute("SELECT COUNT(*) FROM commodities").fetchone()[0]
    after_prices = conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
    
    print("\n" + "=" * 60)
    print(f"AFTER: {after_commodities:,} commodities, {after_prices:,} prices")
    print(f"Removed: {before_commodities - after_commodities:,} commodities, {before_prices - after_prices:,} prices")
    print("=" * 60)
    
    # Show final commodities
    print("\n--- Final commodity list ---")
    rows = conn.execute("""
        SELECT c.name, c.category, c.specification, COUNT(p.id) as cnt, 
               MIN(p.date) as first, MAX(p.date) as last
        FROM commodities c
        LEFT JOIN prices p ON c.id = p.commodity_id
        GROUP BY c.id
        ORDER BY c.category, c.name
    """).fetchall()
    
    current_cat = None
    for r in rows:
        if r['category'] != current_cat:
            current_cat = r['category']
            print(f"\n  [{current_cat}]")
        print(f"    {r['name']}: {r['cnt']} prices ({r['first']} to {r['last']})")
    
    conn.execute("VACUUM")
    conn.commit()
    conn.close()
    
    print(f"\n✅ Cleanup complete! Database: {DB_PATH}")


if __name__ == '__main__':
    main()
