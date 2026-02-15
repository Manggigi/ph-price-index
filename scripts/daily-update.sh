#!/bin/bash
# PH Price Index — Daily auto-update script
# Runs the scraper for latest 5 PDFs, commits, and deploys to Railway

set -e

cd /Users/gian/.openclaw/workspace/apps/ph-price-index

echo "🇵🇭 PH Price Index — Daily Update"
echo "=================================="

# 1. Run scraper (latest 5 PDFs covers ~5 days)
echo "[1/3] Running scraper..."
python3 run_scraper.py --max 5

# 2. Check if DB changed
if git diff --quiet data/prices.db; then
  echo "✅ No new data — DB unchanged. Skipping deploy."
  exit 0
fi

# 3. Commit and push
echo "[2/3] Committing updated data..."
git add data/prices.db
DATE=$(date +%Y-%m-%d)
git commit -m "Auto-update price data ${DATE}"
git push origin main

# 4. Deploy to Railway
echo "[3/3] Deploying to Railway..."
railway up --service ph-price-index

echo "✅ Done! Fresh prices deployed."
