"""
PH Price Index — Free Open Source API
Daily agricultural commodity prices from the Philippine Department of Agriculture.
"""
import os
import sys
import io
import csv
import time
import json as jsonlib
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, Query, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional
from database import (
    get_prices_by_date, get_latest_prices, get_commodity_history,
    get_all_commodities, get_date_range, search_prices, get_stats,
    get_categories, get_prices_range, export_all
)

# ============================================================
# Dashboard Cache — computed once, served to all users
# ============================================================
_dashboard_cache = {}
_dashboard_cache_ts = 0
DASHBOARD_CACHE_TTL = 3600  # 1 hour

API_VERSION = "2.0.0"

app = FastAPI(
    title="PH Price Index API",
    description="""
    🇵🇭 Free, open-source API for daily agricultural commodity prices in the Philippines.
    
    Data sourced from the Department of Agriculture's Daily Price Index.
    Covers rice, fish, meat, vegetables, fruits, spices, and more — updated daily.
    
    **Source:** [da.gov.ph/price-monitoring](https://www.da.gov.ph/price-monitoring/)  
    **GitHub:** [github.com/Manggigi/ph-price-index](https://github.com/Manggigi/ph-price-index)
    """,
    version=API_VERSION,
    contact={"name": "PH Price Index", "url": "https://github.com/Manggigi/ph-price-index"},
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
)

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
    stats = get_stats()
    return {
        "name": "PH Price Index API",
        "version": API_VERSION,
        "description": "Free open-source API for Philippine daily agricultural commodity prices",
        "source": "Department of Agriculture - da.gov.ph",
        "data": {
            "commodities": stats.get("total_commodities", 0),
            "prices": stats.get("total_prices", 0),
            "categories": stats.get("total_categories", 0),
            "date_range": f"{stats.get('first_date', '?')} to {stats.get('last_date', '?')}",
            "total_dates": stats.get("total_dates", 0),
        },
        "endpoints": {
            "GET /api/prices/latest": "Latest available prices",
            "GET /api/prices/{date}": "Prices for a specific date (YYYY-MM-DD)",
            "GET /api/prices/range?from=YYYY-MM-DD&to=YYYY-MM-DD": "Prices for a date range",
            "GET /api/commodities": "List all tracked commodities (paginated)",
            "GET /api/commodities/{name}/history": "Price history for a commodity",
            "GET /api/categories": "List all categories with commodity counts",
            "GET /api/search?q=rice": "Search commodities",
            "GET /api/export/csv": "Download entire database as CSV",
            "GET /api/export/json": "Download entire database as JSON",
            "GET /api/stats": "Database statistics",
            "GET /api/dates": "Available date range",
            "GET /docs": "Interactive API documentation (Swagger UI)",
        },
        "github": "https://github.com/Manggigi/ph-price-index",
    }


@app.get("/api/prices/latest")
def latest_prices(response: Response):
    """Get the most recent available prices."""
    data = get_latest_prices()
    if not data["prices"]:
        raise HTTPException(status_code=404, detail="No price data available")
    response.headers["Cache-Control"] = "public, max-age=3600"
    return data


@app.get("/api/prices/range")
def prices_range(
    date_from: str = Query(..., alias="from", description="Start date (YYYY-MM-DD)"),
    date_to: str = Query(..., alias="to", description="End date (YYYY-MM-DD)"),
    commodity: Optional[str] = Query(None, description="Filter by commodity name"),
):
    """Get prices for a date range, optionally filtered by commodity."""
    import re
    for d in [date_from, date_to]:
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', d):
            raise HTTPException(status_code=400, detail="Dates must be in YYYY-MM-DD format")
    
    results = get_prices_range(date_from, date_to, commodity)
    return {
        "from": date_from,
        "to": date_to,
        "commodity": commodity,
        "count": len(results),
        "prices": results,
    }


@app.get("/api/prices/{date}")
def prices_by_date(
    date: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=500, description="Results per page"),
):
    """Get all prices for a specific date (format: YYYY-MM-DD)."""
    import re
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
        raise HTTPException(status_code=400, detail="Date must be in YYYY-MM-DD format")
    
    data = get_prices_by_date(date, page=page, limit=limit)
    if not data["prices"]:
        raise HTTPException(status_code=404, detail=f"No prices found for {date}")
    
    return {
        "date": date,
        "count": len(data["prices"]),
        "prices": data["prices"],
        "meta": data["meta"],
    }


@app.get("/api/commodities")
def list_commodities(
    category: Optional[str] = Query(None, description="Filter by category"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=500, description="Results per page"),
):
    """List all tracked commodities with pagination."""
    data = get_all_commodities(page=page, limit=limit)
    commodities = data["commodities"]
    
    if category:
        commodities = [c for c in commodities if c.get("category") and 
                       category.lower() in c["category"].lower()]
    
    return {
        "total": len(commodities),
        "commodities": commodities,
        "meta": data["meta"],
    }


@app.get("/api/commodities/{name}/history")
def commodity_history(
    name: str,
    days: Optional[int] = Query(None, ge=1, description="Number of days of history"),
    date_from: Optional[str] = Query(None, alias="from", description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, alias="to", description="End date (YYYY-MM-DD)"),
):
    """Get price history for a specific commodity. Use from/to for date range, or days for recent history."""
    history = get_commodity_history(name, days=days, date_from=date_from, date_to=date_to)
    if not history:
        raise HTTPException(status_code=404, detail=f"No history found for '{name}'")
    
    return {
        "commodity": name,
        "count": len(history),
        "history": history,
    }


@app.get("/api/categories")
def categories():
    """List all categories with commodity and price counts."""
    cats = get_categories()
    return {
        "count": len(cats),
        "categories": cats,
    }


@app.get("/api/search")
def search(
    q: str = Query(..., min_length=2, description="Search query"),
    date: Optional[str] = Query(None, description="Specific date (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=500, description="Results per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """Search commodities by name or category."""
    data = search_prices(q, date=date, limit=limit, offset=offset)
    return {
        "query": q,
        "date": date,
        "count": len(data["results"]),
        "results": data["results"],
        "meta": data["meta"],
    }


@app.get("/api/export/csv")
def export_csv():
    """Download the entire database as a CSV file."""
    def generate():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["date", "category", "commodity", "specification", "unit", "price"])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)
        
        for row in export_all():
            writer.writerow([
                row["date"], row["category"], row["commodity"],
                row["specification"], row["unit"], row["price"]
            ])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)
    
    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ph-price-index.csv"}
    )


@app.get("/api/export/json")
def export_json():
    """Download the entire database as a JSON file."""
    import json
    
    def generate():
        yield '{"prices":['
        first = True
        for row in export_all():
            if not first:
                yield ','
            yield json.dumps(row)
            first = False
        yield ']}'
    
    return StreamingResponse(
        generate(),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=ph-price-index.json"}
    )


@app.get("/api/stats")
def stats():
    """Get database statistics."""
    return get_stats()


@app.get("/api/dates")
def dates():
    """Get available date range."""
    return get_date_range()


# ============================================================
# DASHBOARD — Pre-computed, cached, single-call endpoint
# ============================================================

def _build_dashboard():
    """Pre-compute the entire AnoMura dashboard payload."""
    stats_data = get_stats()
    latest_data = get_latest_prices()
    latest_prices = latest_data.get("prices", [])
    latest_date = latest_data.get("date", "")

    # Pre-compute for all 3 time ranges
    periods = {}
    for label, days in [("30d", 30), ("90d", 90), ("1y", 365)]:
        to_date = latest_date
        from_dt = datetime.strptime(latest_date, "%Y-%m-%d") - timedelta(days=days)
        from_date = from_dt.strftime("%Y-%m-%d")
        range_prices = get_prices_range(from_date, to_date)

        # Group history by name+spec (the key fix for zigzag)
        hist_map = {}
        for p in range_prices:
            key = f"{p['name']}||{p.get('specification', '')}"
            if key not in hist_map:
                hist_map[key] = []
            hist_map[key].append(p["price"])

        # Build per-commodity signals
        items = []
        for item in latest_prices:
            key = f"{item['name']}||{item.get('specification', '')}"
            prices = hist_map.get(key, [])
            avg = sum(prices) / len(prices) if prices else item["price"]
            change_pct = ((item["price"] - avg) / avg) * 100 if avg else 0

            signal = "STABLE"
            if change_pct < -5:
                signal = "MURA"
            elif change_pct > 10:
                signal = "MAHAL"

            # Clean display name
            clean_name = item["name"].rstrip(", ")
            spec = item.get("specification", "")
            display_name = f"{clean_name} ({spec})" if spec and spec != clean_name else clean_name

            # Compact sparkline: downsample to max 30 points
            sparkline = prices
            if len(sparkline) > 30:
                step = len(sparkline) / 30
                sparkline = [sparkline[int(i * step)] for i in range(30)]

            items.append({
                "name": item["name"],
                "displayName": display_name,
                "category": item.get("category", ""),
                "specification": spec,
                "unit": item.get("unit", "PHP/kg"),
                "price": item["price"],
                "avg": round(avg, 2),
                "changePct": round(change_pct, 2),
                "signal": signal,
                "sparkline": [round(p, 2) for p in sparkline],
            })

        items.sort(key=lambda x: x["changePct"])

        best_deals = [i for i in items if i["signal"] == "MURA"][:5]
        getting_expensive = sorted(
            [i for i in items if i["signal"] == "MAHAL"],
            key=lambda x: -x["changePct"]
        )[:5]

        periods[label] = {
            "items": items,
            "bestDeals": best_deals,
            "gettingExpensive": getting_expensive,
        }

    return {
        "stats": stats_data,
        "latestDate": latest_date,
        "priceCount": len(latest_prices),
        "periods": periods,
        "generatedAt": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/api/dashboard")
def dashboard(response: Response):
    """
    Pre-computed dashboard for AnoMura.
    Returns stats, latest prices with signals, best deals, getting expensive,
    and sparkline data for 30D/90D/1Y — all in one call.
    Cached server-side for 1 hour.
    """
    global _dashboard_cache, _dashboard_cache_ts

    now = time.time()
    if not _dashboard_cache or (now - _dashboard_cache_ts) > DASHBOARD_CACHE_TTL:
        _dashboard_cache = _build_dashboard()
        _dashboard_cache_ts = now

    # Tell browsers + CDN to cache for 1 hour
    response.headers["Cache-Control"] = "public, max-age=3600, s-maxage=3600"
    return _dashboard_cache


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
