"""
eBay Debug Tool — run this FIRST to diagnose selector issues.
Saves the raw HTML eBay returns so we can inspect it.

Usage:
    python ebay_debug.py "mike trout rookie card"
"""

import sys
import time
from curl_cffi import requests as cf_requests

QUERY = sys.argv[1] if len(sys.argv) > 1 else "mike trout rookie card"

session = cf_requests.Session(impersonate="chrome124")

NAV_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "accept-language": "en-US,en;q=0.9",
    "accept-encoding": "gzip, deflate, br, zstd",
    "sec-ch-ua": '"Chromium";v="124","Google Chrome";v="124","Not-A.Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
}

print("Step 1: Fetching homepage...")
r = session.get("https://www.ebay.com/", headers=NAV_HEADERS, timeout=15)
print(f"  Status: {r.status_code}  Cookies: {len(session.cookies)}")
time.sleep(1.5)

print(f"\nStep 2: Fetching sold search for '{QUERY}'...")
r2 = session.get(
    "https://www.ebay.com/sch/i.html",
    params={"_nkw": QUERY, "LH_Sold": "1", "LH_Complete": "1", "_ipg": "60"},
    headers={**NAV_HEADERS, "sec-fetch-site": "same-origin", "referer": "https://www.ebay.com/"},
    timeout=20,
)
print(f"  Status: {r2.status_code}  Length: {len(r2.text)} chars")

html = r2.text
with open("ebay_debug_raw.html", "w", encoding="utf-8") as f:
    f.write(html)
print(f"\nRaw HTML saved to: ebay_debug_raw.html")

# --- Quick selector probe ---
from bs4 import BeautifulSoup
soup = BeautifulSoup(html, "lxml")

print("\n--- Selector probe ---")

# Try various item container selectors
for sel in ["li.s-item", "div.s-item", ".srp-results li", ".b-list__items li"]:
    found = soup.select(sel)
    print(f"  {sel!r:35s} → {len(found)} elements")

# Show first item's class tree
items = soup.select("li.s-item") or soup.select("div.s-item")
if items:
    first = items[0]
    print(f"\nFirst item tag: <{first.name} class='{' '.join(first.get('class', []))}'")
    for child in first.children:
        if hasattr(child, 'get'):
            classes = ' '.join(child.get('class', []))
            print(f"  <{child.name} class='{classes}'>  text={child.get_text(strip=True)[:60]!r}")

# Probe title selectors
print("\n--- Title selectors ---")
for sel in [".s-item__title", "h3.s-item__title", ".s-item__title span", "[class*='title']"]:
    els = soup.select(sel)
    if els:
        print(f"  {sel!r:35s} → {len(els)} found  first={els[0].get_text(strip=True)[:50]!r}")

# Probe price selectors
print("\n--- Price selectors ---")
for sel in [".s-item__price", ".notranslate", "[class*='price']", ".s-item__detail"]:
    els = soup.select(sel)
    if els:
        print(f"  {sel!r:35s} → {len(els)} found  first={els[0].get_text(strip=True)[:30]!r}")

# Probe date selectors
print("\n--- Date selectors ---")
for sel in [".s-item__ended-date", ".s-item__listingDate", "[class*='date']", "[class*='sold']", "[class*='end']"]:
    els = soup.select(sel)
    if els:
        print(f"  {sel!r:35s} → {len(els)} found  first={els[0].get_text(strip=True)[:30]!r}")

print("\nDone. Open ebay_debug_raw.html in a browser or text editor for full inspection.")