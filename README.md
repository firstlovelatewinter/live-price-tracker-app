# Uniqlo Price Monitor

A local dashboard to track Uniqlo product prices and get notified when they drop.

## Features

- **Track multiple products** - Add any Uniqlo product URLs
- **Price history** - Stores all price checks in a local SQLite database
- **Visual dashboard** - Web interface showing current prices and price changes
- **Automatic monitoring** - Background process that checks prices on a schedule
- **Sale detection** - Highlights when items go on sale
- **Price change indicators** - Shows if price went up, down, or stayed same

## Setup

### 1. Install dependencies

```bash
cd /Users/LeAnnLo/uniqlo-price-monitor
pip3 install -r requirements.txt
```

### 2. Initialize the database

```bash
python3 database.py
```

## Usage

### Option 1: Web Dashboard (Recommended)

Start the dashboard server:

```bash
python3 dashboard.py
```

Then open http://localhost:5000 in your browser.

From the dashboard you can:
- Add new products by pasting Uniqlo URLs
- See all tracked products with current prices
- View price change indicators (↓ dropped, ↑ increased, → same)
- Manually check prices
- Remove products you no longer want to track

### Option 2: Background Monitor

Run the monitor in the background to check prices automatically:

```bash
# Check every 6 hours (default)
python3 monitor.py

# Check every 2 hours
python3 monitor.py --interval 2

# Run once and exit
python3 monitor.py --once
```

### Option 3: CLI Management

Use the CLI script to manage products:

```bash
# List all products
python3 cli.py list

# Add a product
python3 cli.py add "https://www.uniqlo.com/..." "Optional Name"

# Check all prices now
python3 cli.py check

# Remove a product
python3 cli.py remove <product_id>

# View price history for a product
python3 cli.py history <product_id>
```

## How to find Uniqlo product URLs

1. Go to uniqlo.com and find a product
2. Copy the URL from your browser
3. Paste it into the dashboard or CLI

Example URLs:
- `https://www.uniqlo.com/us/en/products/E460691-000/00`
- `https://www.uniqlo.com/us/en/products/E460695-000/00?colorCode=COL09`

## Files

- `dashboard.py` - Flask web server for the UI
- `monitor.py` - Background price checker
- `scraper.py` - Uniqlo website scraper
- `database.py` - SQLite database operations
- `cli.py` - Command-line interface
- `prices.db` - SQLite database (created automatically)
- `templates/index.html` - Dashboard HTML template

## Notes

- The scraper respects Uniqlo's website by using reasonable request rates
- All data is stored locally in `prices.db`
- The dashboard is only accessible from your computer (localhost)
- Price checks include a random delay to avoid being blocked
