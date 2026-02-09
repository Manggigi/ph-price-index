# 🇵🇭 PH Price Index API

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![API Status](https://img.shields.io/badge/API-Live-brightgreen)](https://ph-price-index-production.up.railway.app)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

**Free, open-source REST API for daily agricultural commodity prices in the Philippines.**

Data sourced from the [Department of Agriculture's Daily Price Index](https://www.da.gov.ph/price-monitoring/) — covering rice, fish, meat, vegetables, fruits, spices, and more across NCR markets since 2018.

🔗 **Live API:** https://ph-price-index-production.up.railway.app  
📖 **Swagger Docs:** https://ph-price-index-production.up.railway.app/docs  
📊 **71 commodities** · **33,800+ price records** · **1,779 trading days** · **11 categories**

---

## ⚡ Quick Start

```bash
# Get latest prices
curl https://ph-price-index-production.up.railway.app/api/prices/latest

# Search for rice
curl "https://ph-price-index-production.up.railway.app/api/search?q=rice"

# Download everything as CSV
curl -O https://ph-price-index-production.up.railway.app/api/export/csv
```

---

## 📋 API Endpoints

Base URL: `https://ph-price-index-production.up.railway.app`

| Endpoint | Description |
|----------|-------------|
| `GET /` | API info, stats, and endpoint list |
| `GET /api/prices/latest` | Latest available prices |
| `GET /api/prices/{date}` | Prices for a specific date |
| `GET /api/prices/range` | Prices for a date range |
| `GET /api/commodities` | List all commodities (paginated) |
| `GET /api/commodities/{name}/history` | Price history for a commodity |
| `GET /api/categories` | All categories with counts |
| `GET /api/search?q=` | Search commodities |
| `GET /api/export/csv` | Full database as CSV download |
| `GET /api/export/json` | Full database as JSON download |
| `GET /api/stats` | Database statistics |
| `GET /api/dates` | Available date range |
| `GET /docs` | Interactive Swagger documentation |

---

## 📖 Endpoint Details & Examples

### `GET /api/prices/latest`

Returns the most recent available prices across all commodities.

```json
{
  "date": "2026-02-08",
  "count": 46,
  "prices": [
    {
      "name": "Beef Brisket",
      "category": "BEEF MEAT PRODUCTS",
      "specification": "Meat with Bones",
      "unit": "PHP/kg",
      "price": 440.0,
      "date": "2026-02-08"
    },
    {
      "name": "Well Milled",
      "category": "LOCAL COMMERCIAL RICE",
      "specification": "1-19% bran streak",
      "unit": "PHP/kg",
      "price": 47.0,
      "date": "2026-02-08"
    }
  ]
}
```

### `GET /api/prices/{date}?page=1&limit=50`

Get prices for a specific date. Supports pagination.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `limit` | int | 50 | Results per page (max 500) |

```bash
curl "https://ph-price-index-production.up.railway.app/api/prices/2025-01-15?page=1&limit=10"
```

### `GET /api/prices/range?from=YYYY-MM-DD&to=YYYY-MM-DD`

Get prices across a date range, optionally filtered by commodity.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `from` | string | ✅ | Start date (YYYY-MM-DD) |
| `to` | string | ✅ | End date (YYYY-MM-DD) |
| `commodity` | string | ❌ | Filter by commodity name |

```bash
# All prices in January 2025
curl "https://ph-price-index-production.up.railway.app/api/prices/range?from=2025-01-01&to=2025-01-31"

# Just rice prices
curl "https://ph-price-index-production.up.railway.app/api/prices/range?from=2025-01-01&to=2025-01-31&commodity=Premium"
```

### `GET /api/commodities?page=1&limit=50&category=`

List all tracked commodities with price counts and date ranges.

```json
{
  "total": 71,
  "commodities": [
    {
      "id": 1,
      "name": "Beef Brisket",
      "category": "BEEF MEAT PRODUCTS",
      "specification": "Meat with Bones",
      "unit": "PHP/kg",
      "price_count": 832,
      "first_date": "2018-02-01",
      "last_date": "2026-02-08"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 50,
    "total": 71,
    "has_more": true
  }
}
```

### `GET /api/commodities/{name}/history`

Get price history for a commodity. Supports date range or day limit.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `days` | int | 30 | Number of recent data points |
| `from` | string | — | Start date (YYYY-MM-DD) |
| `to` | string | — | End date (YYYY-MM-DD) |

```bash
# Last 30 days
curl "https://ph-price-index-production.up.railway.app/api/commodities/Tomato/history"

# Full year
curl "https://ph-price-index-production.up.railway.app/api/commodities/Tomato/history?from=2024-01-01&to=2024-12-31"
```

### `GET /api/categories`

```json
{
  "count": 11,
  "categories": [
    {
      "category": "VEGETABLES",
      "commodity_count": 11,
      "price_count": 8001,
      "first_date": "2018-02-01",
      "last_date": "2026-02-08"
    },
    {
      "category": "FRUITS",
      "commodity_count": 10,
      "price_count": 6022,
      "first_date": "2018-02-01",
      "last_date": "2026-02-08"
    }
  ]
}
```

### `GET /api/search?q=`

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `q` | string | — | Search query (min 2 chars) |
| `date` | string | latest | Specific date |
| `limit` | int | 50 | Max results |
| `offset` | int | 0 | Pagination offset |

```bash
curl "https://ph-price-index-production.up.railway.app/api/search?q=banana"
```

### `GET /api/export/csv`

Downloads the **entire database** as a CSV file. Perfect for researchers, students, and data analysts.

```bash
curl -O https://ph-price-index-production.up.railway.app/api/export/csv
```

CSV columns: `date`, `category`, `commodity`, `specification`, `unit`, `price`

### `GET /api/export/json`

Same as CSV but in JSON format.

---

## 📊 Data Dictionary

| Field | Type | Description |
|-------|------|-------------|
| `name` / `commodity` | string | Commodity name (e.g., "Beef Brisket", "Tomato") |
| `category` | string | Category grouping (e.g., "VEGETABLES", "FISH PRODUCTS") |
| `specification` | string | Size/type details (e.g., "Medium (5-6 pcs/kg)") |
| `unit` | string | Price unit, typically "PHP/kg" or "PHP/pc" |
| `price` | float | Price in Philippine Pesos (₱) |
| `date` | string | Date in YYYY-MM-DD format |

### Categories

| Category | Commodities | Description |
|----------|-------------|-------------|
| IMPORTED COMMERCIAL RICE | 8 | Imported rice varieties (Premium, Well Milled, etc.) |
| CORN PRODUCTS | 4 | Corn and corn derivatives |
| FISH PRODUCTS | 12 | Fresh fish and seafood (Galunggong, Bangus, Tilapia, etc.) |
| BEEF MEAT PRODUCTS | 2 | Beef cuts (Brisket, Rump) |
| PORK MEAT PRODUCTS | 1 | Fresh pork cuts |
| FROZEN PORK PRODUCTS | 2 | Frozen imported pork |
| OTHER LIVESTOCK MEAT | 10 | Chicken, eggs, and other meats |
| VEGETABLES | 11 | Common vegetables (Tomato, Onion, Eggplant, etc.) |
| FRUITS | 10 | Common fruits (Banana, Mango, Calamansi, etc.) |
| SPICES | 9 | Garlic, onion, ginger, salt, chili |
| COOKING OIL | 2 | Coconut and palm oil |

---

## 💡 Use Cases

### 🎓 Student Thesis: Analyzing Food Price Inflation

```python
import requests
import pandas as pd

# Download all data
url = "https://ph-price-index-production.up.railway.app/api/export/csv"
df = pd.read_csv(url)

# Analyze rice price trends
rice = df[df['category'].str.contains('RICE')]
monthly = rice.groupby([pd.to_datetime(rice['date']).dt.to_period('M'), 'commodity'])['price'].mean()
print(monthly.unstack().tail(12))
```

### 📱 App Builder: Price Comparison App

```javascript
// Fetch today's vegetable prices
const res = await fetch(
  "https://ph-price-index-production.up.railway.app/api/search?q=vegetables"
);
const data = await res.json();

data.results.forEach(item => {
  console.log(`${item.name}: ₱${item.price}/${item.unit}`);
});
```

### 📰 Journalist: Investigating Price Trends

```python
import requests

# Compare onion prices over time
url = "https://ph-price-index-production.up.railway.app/api/commodities/White Onion/history"
params = {"from": "2022-01-01", "to": "2023-12-31"}
data = requests.get(url, params=params).json()

for entry in data["history"][:5]:
    print(f"{entry['date']}: ₱{entry['price']}")
```

### 🔬 Researcher: Food Security Analysis

```python
import requests
import pandas as pd

# Get all price data
url = "https://ph-price-index-production.up.railway.app/api/export/csv"
df = pd.read_csv(url)

# Calculate price volatility by commodity
volatility = df.groupby('commodity')['price'].agg(['mean', 'std'])
volatility['cv'] = volatility['std'] / volatility['mean']  # coefficient of variation
print(volatility.sort_values('cv', ascending=False).head(10))
```

---

## 🐍 Code Examples

### Python: Fetch Today's Rice Prices

```python
import requests

response = requests.get(
    "https://ph-price-index-production.up.railway.app/api/search",
    params={"q": "rice"}
)
data = response.json()

for item in data["results"]:
    print(f"{item['category']} — {item['name']}: ₱{item['price']}")
```

### Python: Plot Price Trends

```python
import requests
import matplotlib.pyplot as plt

# Get 1-year history for tomatoes
response = requests.get(
    "https://ph-price-index-production.up.railway.app/api/commodities/Tomato/history",
    params={"from": "2025-01-01", "to": "2025-12-31"}
)
history = response.json()["history"]

dates = [h["date"] for h in history]
prices = [h["price"] for h in history]

plt.figure(figsize=(12, 4))
plt.plot(dates, prices)
plt.title("Tomato Prices in NCR (2025)")
plt.ylabel("Price (PHP/kg)")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("tomato_prices.png")
```

### JavaScript: Download CSV

```javascript
// Download full dataset
const response = await fetch(
  "https://ph-price-index-production.up.railway.app/api/export/csv"
);
const csv = await response.text();

// Save or process
const rows = csv.split('\n').map(row => row.split(','));
console.log(`Downloaded ${rows.length - 1} price records`);
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│  Department of Agriculture (da.gov.ph)      │
│  Daily Price Index PDFs                     │
└──────────────┬──────────────────────────────┘
               │ scraper (Python)
               ▼
┌─────────────────────────────────────────────┐
│  SQLite Database (prices.db)                │
│  71 commodities · 33,800+ prices            │
│  2018-02 to present                         │
└──────────────┬──────────────────────────────┘
               │ FastAPI
               ▼
┌─────────────────────────────────────────────┐
│  REST API (Railway)                         │
│  https://ph-price-index-production          │
│  .up.railway.app                            │
│                                             │
│  /api/prices/latest  /api/export/csv        │
│  /api/search         /api/categories        │
│  /api/commodities    /api/export/json       │
└─────────────────────────────────────────────┘
```

**Stack:** Python 3.9+ · FastAPI · SQLite · Railway

---

## 🛠️ Local Development

```bash
# Clone
git clone https://github.com/Manggigi/ph-price-index.git
cd ph-price-index

# Install dependencies
pip install -r requirements.txt

# Run API locally
uvicorn api.main:app --reload --port 8000

# Open http://localhost:8000/docs
```

---

## 🚦 Fair Use

This is a free, community API. Please be respectful:

- **No rate limit enforced** — but please don't hammer the server
- **Use `/api/export/csv`** for bulk data needs instead of scraping every endpoint
- **Cache responses** where possible — prices update once daily
- **Attribute the source** — Department of Agriculture, Philippines

For heavy usage, consider cloning the repo and running your own instance.

---

## 📄 Data Source & Disclaimer

- **Source:** [Department of Agriculture — Price Monitoring](https://www.da.gov.ph/price-monitoring/)
- **Coverage:** National Capital Region (NCR) markets
- **Frequency:** Daily (trading days)
- **Period:** February 2018 — present
- Prices are parsed from DA-published PDF reports. While we strive for accuracy, always verify critical data against the original source.

---

## 🤝 Contributing

Contributions welcome! Areas that need help:

- [ ] More commodity coverage (currently 71 tracked)
- [ ] Historical data backfill (pre-2018)
- [ ] Regional price data (currently NCR only)
- [ ] Better PDF parsing for edge cases
- [ ] Frontend dashboard

---

## 📜 License

MIT License — use it for anything. If it helps your research, thesis, or app, that makes us happy. 🇵🇭

---

**Built with ❤️ for the Filipino developer community.**
