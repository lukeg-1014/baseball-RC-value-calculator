# ⚾ Baseball Rookie Card Value Calculator

A Python tool that cross-references MLB player statistics with eBay sold listings to determine whether a baseball rookie card is worth buying.

---

## What it does

1. Looks up a player's stats from Baseball Reference via `pybaseball`
2. Calculates their **OPS+** (a park/era-adjusted measure of offensive performance where 100 = league average)
3. Scrapes recent **eBay sold listings** for their Topps base rookie card using a real Chromium browser (via Playwright) to bypass bot detection
4. Filters out graded, numbered, and variant cards to isolate base card prices
5. Calculates a **fair value** based on the player's performance and how long ago they debuted
6. Returns a **BUY / NEUTRAL / PASS** recommendation

---

## How the formula works

```
Fair Value = Base Value × (OPS+ / 100) × (1.06 ^ Years Since Rookie)
```

- **Base Value** — what a brand-new average player's rookie card costs (~$4)
- **OPS+ / 100** — performance multiplier. A 166 OPS+ player gets a 1.66x multiplier
- **Vintage multiplier** — compound appreciation for age. Cards from 10 years ago are worth more than brand new ones
- **Premium** = Fair Value − Avg Sold Price
  - Positive → card is underpriced → **BUY**
  - Near zero → fairly priced → **NEUTRAL**
  - Negative → card is overpriced → **PASS**

---

## Installation

**1. Clone the repo**
```bash
git clone https://github.com/lukeg-1014/baseball-RC-value-calculator
cd baseball-RC-value-calculator
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Install Chromium (required for eBay scraping)**
```bash
playwright install chromium
```

---

## Usage

```bash
python main.py
```

You'll be prompted for the player's first and last name:

```
What is the Player's First Name: Aaron
What is the Player's Last Name: Judge
```

The tool will then scrape eBay and output something like:

```
Player Name: Aaron Judge
OPS+: 166
Rookie Year: 2016
--------------------------
  Price range before filter: $0.99 – $312.00
  IQR ceiling (base card cutoff): $18.43
  Listings after filter: 31

--- Card Value Analysis ---
  ops_plus               166
  years_since_rookie     10
  performance_mult       1.66
  vintage_mult           1.791
  fair_value             $11.90
  avg_sold_price         $8.43
  premium                $3.47
  recommendation         BUY — 41.2% underpriced vs fair value
```

A CSV of the raw eBay listings is also saved to the project folder.

---

## Project structure

```
baseball-RC-value-calculator/
│
├── main.py          # Player class, value formula, main script
├── ebayscrape.py    # EbaySoldScraper class (Playwright-based)
├── requirements.txt # Python dependencies
└── README.md
```

---

## Dependencies

| Library | Purpose |
|---|---|
| `pybaseball` | Pull MLB stats from Baseball Reference |
| `playwright` | Real Chromium browser to bypass eBay bot detection |
| `beautifulsoup4` + `lxml` | Parse eBay HTML |
| `numpy` | IQR outlier filtering |
| `pandas` | DataFrame handling for stats table |
| `flask` | (Optional) web server for browser UI |

---

## Notes

- The scraper targets **Topps base rookie cards only** — graded, numbered, refractor, and parallel cards are filtered out
- eBay scraping takes 20–40 seconds per search since it runs a real browser
- Player must have played in the **current season** to appear in the stats table
- OPS+ is calculated from the current season's stats, not career stats

---

## Built with

- Python 3.14
- [pybaseball](https://github.com/jldbc/pybaseball)
- [Playwright](https://playwright.dev/python/)
- [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/)
