"""
PH Price Index — Free Open Source API
Daily agricultural commodity prices from the Philippine Department of Agriculture.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional
from database import (
    get_prices_by_date, get_latest_prices, get_commodity_history,
    get_all_commodities, get_date_range, search_prices, get_stats
)

app = FastAPI(
    title="PH Price Index API",
    description="""
    🇵🇭 Free, open-source API for daily agricultural commodity prices in the Philippines.
    
    Data sourced from the Department of Agriculture's Daily Price Index.
    Covers rice, fish, meat, vegetables, fruits, and more — updated daily.
    
    **Source:** [da.gov.ph/price-monitoring](https://www.da.gov.ph/price-monitoring/)
    **GitHub:** [github.com/Manggigi/ph-price-index](https://github.com/Manggigi/ph-price-index)
    """,
    version="1.0.0",
    contact={"name": "PH Price Index", "url": "https://github.com/Manggigi/ph-price-index"},
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
)

# CORS — allow all origins for public API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """API info and links."""
    return {
        "name": "PH Price Index API",
        "version": "1.0.0",
        "description": "Free open-source API for Philippine daily agricultural commodity prices",
        "source": "Department of Agriculture - da.gov.ph",
        "endpoints": {
            "GET /api/prices/latest": "Latest available prices",
            "GET /api/prices/{date}": "Prices for a specific date (YYYY-MM-DD)",
            "GET /api/commodities": "List all tracked commodities",
            "GET /api/commodities/{name}/history": "Price history for a commodity",
            "GET /api/search?q=rice": "Search commodities",
            "GET /api/stats": "Database statistics",
            "GET /api/dates": "Available date range",
            "GET /docs": "Interactive API documentation",
        },
        "github": "https://github.com/Manggigi/ph-price-index",
    }


@app.get("/api/prices/latest")
def latest_prices():
    """Get the most recent available prices."""
    data = get_latest_prices()
    if not data["prices"]:
        raise HTTPException(status_code=404, detail="No price data available")
    return data


@app.get("/api/prices/{date}")
def prices_by_date(date: str):
    """Get all prices for a specific date (format: YYYY-MM-DD)."""
    # Validate date format
    import re
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
        raise HTTPException(status_code=400, detail="Date must be in YYYY-MM-DD format")
    
    prices = get_prices_by_date(date)
    if not prices:
        raise HTTPException(status_code=404, detail=f"No prices found for {date}")
    
    return {
        "date": date,
        "count": len(prices),
        "prices": prices,
    }


@app.get("/api/commodities")
def list_commodities(category: Optional[str] = Query(None, description="Filter by category")):
    """List all tracked commodities with their price count and date range."""
    commodities = get_all_commodities()
    
    if category:
        commodities = [c for c in commodities if c.get("category") and 
                       category.lower() in c["category"].lower()]
    
    # Group by category
    categories = {}
    for c in commodities:
        cat = c.get("category") or "UNCATEGORIZED"
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(c)
    
    return {
        "total": len(commodities),
        "categories": categories,
    }


@app.get("/api/commodities/{name}/history")
def commodity_history(
    name: str,
    days: int = Query(30, ge=1, le=365, description="Number of days of history"),
):
    """Get price history for a specific commodity."""
    history = get_commodity_history(name, days=days)
    if not history:
        raise HTTPException(status_code=404, detail=f"No history found for '{name}'")
    
    return {
        "commodity": name,
        "count": len(history),
        "history": history,
    }


@app.get("/api/search")
def search(
    q: str = Query(..., min_length=2, description="Search query"),
    date: Optional[str] = Query(None, description="Specific date (YYYY-MM-DD)"),
):
    """Search commodities by name or category."""
    results = search_prices(q, date=date)
    return {
        "query": q,
        "date": date,
        "count": len(results),
        "results": results,
    }


@app.get("/api/stats")
def stats():
    """Get database statistics."""
    return get_stats()


@app.get("/api/dates")
def dates():
    """Get available date range."""
    return get_date_range()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
