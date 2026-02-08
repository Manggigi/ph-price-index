"""
SQLite database for storing parsed price data.
Handles schema creation, upserts, and queries.
"""
import os
import sqlite3
import json
from typing import List, Dict, Optional
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "prices.db")


def get_db(db_path: str = None) -> sqlite3.Connection:
    """Get a database connection with row factory."""
    path = db_path or DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: str = None):
    """Initialize database schema."""
    conn = get_db(db_path)
    
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS commodities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            specification TEXT,
            unit TEXT DEFAULT 'PHP/kg',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(name, specification)
        );
        
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commodity_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            price REAL,
            source_type TEXT DEFAULT 'daily',
            source_file TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (commodity_id) REFERENCES commodities(id),
            UNIQUE(commodity_id, date, source_type)
        );
        
        CREATE TABLE IF NOT EXISTS scrape_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            source_type TEXT DEFAULT 'daily',
            source_url TEXT,
            source_file TEXT,
            parse_method TEXT,
            commodity_count INTEGER DEFAULT 0,
            errors TEXT,
            scraped_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, source_type)
        );
        
        CREATE INDEX IF NOT EXISTS idx_prices_date ON prices(date);
        CREATE INDEX IF NOT EXISTS idx_prices_commodity ON prices(commodity_id);
        CREATE INDEX IF NOT EXISTS idx_prices_date_type ON prices(date, source_type);
        CREATE INDEX IF NOT EXISTS idx_commodities_category ON commodities(category);
        CREATE INDEX IF NOT EXISTS idx_commodities_name ON commodities(name);
    """)
    
    conn.commit()
    conn.close()
    print(f"[db] Database initialized at {db_path or DB_PATH}")


def upsert_commodity(conn: sqlite3.Connection, name: str, category: str = None,
                     specification: str = None, unit: str = "PHP/kg") -> int:
    """Insert or get existing commodity, return its ID."""
    cursor = conn.execute(
        "SELECT id FROM commodities WHERE name = ? AND (specification = ? OR (specification IS NULL AND ? IS NULL))",
        (name, specification, specification)
    )
    row = cursor.fetchone()
    if row:
        # Update category if it was null
        if category:
            conn.execute(
                "UPDATE commodities SET category = ? WHERE id = ? AND category IS NULL",
                (category, row["id"])
            )
        return row["id"]
    
    cursor = conn.execute(
        "INSERT INTO commodities (name, category, specification, unit) VALUES (?, ?, ?, ?)",
        (name, category, specification, unit)
    )
    return cursor.lastrowid


def upsert_price(conn: sqlite3.Connection, commodity_id: int, date: str,
                 price: float, source_type: str = "daily", source_file: str = None):
    """Insert or update a price record."""
    conn.execute("""
        INSERT INTO prices (commodity_id, date, price, source_type, source_file)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(commodity_id, date, source_type)
        DO UPDATE SET price = excluded.price, source_file = excluded.source_file
    """, (commodity_id, date, price, source_type, source_file))


def log_scrape(conn: sqlite3.Connection, date: str, source_type: str,
               source_url: str = None, source_file: str = None,
               parse_method: str = None, commodity_count: int = 0,
               errors: List[str] = None):
    """Log a scrape attempt."""
    conn.execute("""
        INSERT INTO scrape_log (date, source_type, source_url, source_file, parse_method, commodity_count, errors)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(date, source_type) DO UPDATE SET
            parse_method = excluded.parse_method,
            commodity_count = excluded.commodity_count,
            errors = excluded.errors,
            scraped_at = CURRENT_TIMESTAMP
    """, (date, source_type, source_url, source_file, parse_method, commodity_count,
          json.dumps(errors) if errors else None))


def store_parsed_data(parsed_results: List[Dict], db_path: str = None):
    """Store parsed PDF data into the database."""
    conn = get_db(db_path)
    
    total_prices = 0
    total_commodities = 0
    
    for result in parsed_results:
        date = result.get("date")
        if not date:
            continue
        
        source_file = result.get("source_file", "")
        
        for commodity in result.get("commodities", []):
            commodity_id = upsert_commodity(
                conn,
                name=commodity["name"],
                category=commodity.get("category"),
                specification=commodity.get("specification"),
                unit=commodity.get("unit", "PHP/kg"),
            )
            total_commodities += 1
            
            if commodity.get("price") is not None:
                upsert_price(
                    conn,
                    commodity_id=commodity_id,
                    date=date,
                    price=commodity["price"],
                    source_type="daily",
                    source_file=source_file,
                )
                total_prices += 1
        
        log_scrape(
            conn,
            date=date,
            source_type="daily",
            source_file=source_file,
            parse_method=result.get("parse_method"),
            commodity_count=len(result.get("commodities", [])),
            errors=result.get("errors"),
        )
    
    conn.commit()
    conn.close()
    
    print(f"[db] Stored: {total_prices} prices, {total_commodities} commodity records")


# === Query functions ===

def get_prices_by_date(date: str, db_path: str = None) -> List[Dict]:
    """Get all prices for a specific date."""
    conn = get_db(db_path)
    cursor = conn.execute("""
        SELECT c.name, c.category, c.specification, c.unit, p.price, p.date
        FROM prices p
        JOIN commodities c ON p.commodity_id = c.id
        WHERE p.date = ?
        ORDER BY c.category, c.name
    """, (date,))
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_latest_prices(db_path: str = None) -> Dict:
    """Get the most recent prices."""
    conn = get_db(db_path)
    cursor = conn.execute("SELECT MAX(date) as latest FROM prices")
    row = cursor.fetchone()
    latest_date = row["latest"] if row else None
    conn.close()
    
    if latest_date:
        prices = get_prices_by_date(latest_date, db_path)
        return {"date": latest_date, "count": len(prices), "prices": prices}
    return {"date": None, "count": 0, "prices": []}


def get_commodity_history(commodity_name: str, days: int = 30, db_path: str = None) -> List[Dict]:
    """Get price history for a commodity."""
    conn = get_db(db_path)
    cursor = conn.execute("""
        SELECT c.name, c.category, c.specification, p.price, p.date
        FROM prices p
        JOIN commodities c ON p.commodity_id = c.id
        WHERE c.name LIKE ?
        ORDER BY p.date DESC
        LIMIT ?
    """, (f"%{commodity_name}%", days))
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_all_commodities(db_path: str = None) -> List[Dict]:
    """Get all unique commodities."""
    conn = get_db(db_path)
    cursor = conn.execute("""
        SELECT c.id, c.name, c.category, c.specification, c.unit,
               COUNT(p.id) as price_count,
               MIN(p.date) as first_date,
               MAX(p.date) as last_date
        FROM commodities c
        LEFT JOIN prices p ON c.id = p.commodity_id
        GROUP BY c.id
        ORDER BY c.category, c.name
    """)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_date_range(db_path: str = None) -> Dict:
    """Get available date range."""
    conn = get_db(db_path)
    cursor = conn.execute("""
        SELECT MIN(date) as first_date, MAX(date) as last_date, COUNT(DISTINCT date) as total_dates
        FROM prices
    """)
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {}


def search_prices(query: str, date: str = None, db_path: str = None) -> List[Dict]:
    """Search commodities by name."""
    conn = get_db(db_path)
    
    if date:
        cursor = conn.execute("""
            SELECT c.name, c.category, c.specification, c.unit, p.price, p.date
            FROM prices p
            JOIN commodities c ON p.commodity_id = c.id
            WHERE (c.name LIKE ? OR c.category LIKE ?) AND p.date = ?
            ORDER BY c.category, c.name
        """, (f"%{query}%", f"%{query}%", date))
    else:
        # Get latest price for matching commodities
        cursor = conn.execute("""
            SELECT c.name, c.category, c.specification, c.unit, p.price, p.date
            FROM prices p
            JOIN commodities c ON p.commodity_id = c.id
            WHERE (c.name LIKE ? OR c.category LIKE ?)
            AND p.date = (SELECT MAX(date) FROM prices)
            ORDER BY c.category, c.name
        """, (f"%{query}%", f"%{query}%"))
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_stats(db_path: str = None) -> Dict:
    """Get database statistics."""
    conn = get_db(db_path)
    
    stats = {}
    for query, key in [
        ("SELECT COUNT(*) as n FROM commodities", "total_commodities"),
        ("SELECT COUNT(*) as n FROM prices", "total_prices"),
        ("SELECT COUNT(DISTINCT date) as n FROM prices", "total_dates"),
        ("SELECT MIN(date) as n FROM prices", "first_date"),
        ("SELECT MAX(date) as n FROM prices", "last_date"),
        ("SELECT COUNT(DISTINCT category) as n FROM commodities WHERE category IS NOT NULL", "total_categories"),
    ]:
        row = conn.execute(query).fetchone()
        stats[key] = row["n"] if row else 0
    
    conn.close()
    return stats


if __name__ == "__main__":
    init_db()
    stats = get_stats()
    print(json.dumps(stats, indent=2))
