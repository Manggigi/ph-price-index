# 🇵🇭 PH Price Index API

**Free, open-source API for daily agricultural commodity prices in the Philippines.**

No more reading PDFs. Get structured, machine-readable price data for rice, fish, meat, vegetables, fruits, and 180+ commodities — updated daily from the Department of Agriculture.

## 🌐 Live API

> **Base URL:** `https://ph-price-index.vercel.app`

## 📡 Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/prices/latest` | Latest available prices |
| GET | `/api/prices/{date}` | Prices for a specific date (YYYY-MM-DD) |
| GET | `/api/commodities` | List all tracked commodities |
| GET | `/api/commodities/{name}/history` | Price history for a commodity |
| GET | `/api/search?q=rice` | Search commodities by name |
| GET | `/api/stats` | Database statistics |
| GET | `/api/dates` | Available date range |
| GET | `/docs` | Interactive Swagger documentation |

## 🔧 Quick Start

```bash
# Get today's rice prices
curl "https://ph-price-index.vercel.app/api/search?q=rice"

# Get all prices for a specific date
curl "https://ph-price-index.vercel.app/api/prices/2026-02-08"

# Get price history for Galunggong
curl "https://ph-price-index.vercel.app/api/commodities/Galunggong/history?days=30"
```

## 📊 What's Included

- **180+ commodities** tracked daily
- **Categories:** Rice, Corn, Fish, Beef, Pork, Chicken, Eggs, Vegetables, Fruits, Spices, Cooking Oil, Sugar
- **Source:** [DA Price Monitoring](https://www.da.gov.ph/price-monitoring/) (NCR wet market prices)
- **History:** Daily data going back to March 2025+
- **Updates:** Automated daily scraping

## 🏗️ Architecture

```
da.gov.ph (PDFs) → Scraper (Python) → SQLite DB → FastAPI → Public REST API
```

1. **Crawler** — Scrapes DA website for new PDF links
2. **Downloader** — Downloads PDFs with caching
3. **Parser** — Extracts structured data from PDF tables (handles text + image PDFs)
4. **Database** — SQLite with full history
5. **API** — FastAPI with auto-generated Swagger docs

## 🛠️ Run Locally

```bash
# Clone
git clone https://github.com/Manggigi/ph-price-index.git
cd ph-price-index

# Install dependencies
pip install -r requirements.txt

# Run the scraper (downloads & parses all PDFs)
python run_scraper.py

# Test with 5 PDFs first
python run_scraper.py --test

# Start the API
python api/main.py
# → http://localhost:8000
# → http://localhost:8000/docs (Swagger UI)
```

## 🤝 Contributing

This is an open-source project. Contributions welcome!

- **Found a parsing issue?** Open an issue with the date and commodity name
- **Want to add weekly data?** PRs welcome
- **Building something cool?** Let us know!

## 📋 Data Notes

- Prices are **prevailing retail prices** from selected NCR wet markets
- Some dates may have `null` prices (commodity not available that day)
- PDF formats are inconsistent across dates — parser handles multiple formats
- Some older PDFs are image-based and may need OCR (flagged in scrape log)

## 📜 License

MIT — Free to use for any purpose.

## 🙏 Credits

- **Data Source:** [Department of Agriculture, Philippines](https://www.da.gov.ph)
- **Built by:** [@Manggigi](https://github.com/Manggigi)

---

*Making Philippine agricultural data accessible to everyone — students, researchers, journalists, and developers.* 🇵🇭
