"""
eBay Sold Listings Scraper
===========================
Uses Playwright (real Chromium browser) so eBay's bot challenge is bypassed.

Install:
    pip install playwright beautifulsoup4 lxml
    playwright install chromium

Usage from another script:
    from ebayscrape import EbaySoldScraper, save_csv, save_json
"""

import csv
import json
import re
import time
from dataclasses import dataclass, fields, asdict
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class SoldListing:
    title: str
    price: float
    currency: str
    sold_date: str
    condition: str
    shipping: str
    url: str
    image_url: str


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------

class EbaySoldScraper:
    BASE_URL = "https://www.ebay.com/sch/i.html"
    HOME_URL = "https://www.ebay.com/"

    def __init__(self, delay: float = 2.0, debug: bool = False, headless: bool = True):
        """
        Args:
            delay:    Seconds to wait between page requests.
            debug:    Print extra info and save HTML on 0 results.
            headless: False = show the browser window (useful for debugging).
        """
        self.delay      = delay
        self.debug      = debug
        self.headless   = headless
        self._pw        = None   # Playwright instance
        self._browser   = None
        self._page      = None
        self._warmed_up = False

    # ------------------------------------------------------------------
    # Browser lifecycle  (like a Java try-with-resources)
    # ------------------------------------------------------------------

    def _start(self) -> None:
        """Launch Chromium if not already running."""
        if self._browser:
            return
        self._pw      = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=self.headless)
        context       = self._browser.new_context(
            # Pretend to be a normal Windows Chrome user
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="en-US",
        )
        self._page = context.new_page()

    def close(self) -> None:
        """Shut down the browser. Call when you're done scraping."""
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()
        self._browser = None
        self._pw      = None
        self._page    = None

    def _warm_up_session(self) -> None:
        """Visit eBay homepage first to get cookies and look like a real user."""
        print("  Warming up session (opening eBay homepage)…")
        self._page.goto(self.HOME_URL, wait_until="domcontentloaded", timeout=20000)
        time.sleep(1.5)   # brief pause like a real person
        print("  Session ready.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(self, query: str, max_pages: int = 1) -> list[SoldListing]:
        """
        Scrape sold listings for *query* across up to *max_pages* pages.

        Args:
            query:     Plain text search — no quotes needed.
            max_pages: Each page has ~60 listings.

        Returns:
            List of SoldListing objects.
        """
        self._start()

        if not self._warmed_up:
            self._warm_up_session()
            self._warmed_up = True

        listings: list[SoldListing] = []

        for page in range(1, max_pages + 1):
            print(f"  Scraping page {page}/{max_pages}…")

            params = (
                f"?_nkw={query.replace(' ', '+')}"
                f"&LH_Sold=1&LH_Complete=1"
                f"&_pgn={page}&_ipg=60"
            )
            url = self.BASE_URL + params

            html = self._fetch_page(url)
            if html is None:
                break

            page_listings = self._parse_page(html)
            if not page_listings:
                print(f"  No listings parsed on page {page} — stopping.")
                if self.debug:
                    self._save_debug_html(html)
                break

            listings.extend(page_listings)
            print(f"  +{len(page_listings)} listings  (total: {len(listings)})")

            if page < max_pages:
                time.sleep(self.delay)

        return listings

    def filter_listings(self, listings: list, must_contain: list[str]) -> list:
        """
        Keeps only listings whose title contains ALL phrases in must_contain.
        Case-insensitive. Use this instead of quoted eBay search terms.

        Example:
            filter_listings(results, ["Aaron Judge", "Rookie", "Topps"])
        """
        def matches(listing) -> bool:
            title = listing.title.lower()
            return all(p.lower() in title for p in must_contain)
        return [l for l in listings if matches(l)]

    # ------------------------------------------------------------------
    # Page fetching
    # ------------------------------------------------------------------

    def _fetch_page(self, url: str) -> Optional[str]:
        """Navigate Playwright to a URL and return the fully rendered HTML."""
        try:
            if self.debug:
                print(f"  [debug] Navigating to: {url}")

            self._page.goto(url, wait_until="domcontentloaded", timeout=25000)

            current = self._page.url
            if self.debug:
                print(f"  [debug] Landed on: {current}")

            # Detect challenge redirect
            if "splashui/challenge" in current or "challenge" in current:
                print("  [!] eBay challenge page detected — waiting 5s and retrying…")
                time.sleep(5)
                self._page.reload(wait_until="domcontentloaded", timeout=25000)
                if "challenge" in self._page.url:
                    print("  [!] Still challenged. Your IP may be flagged. Try again later.")
                    return None

            # Wait for the results list to appear (up to 8s)
            try:
                self._page.wait_for_selector(".srp-results", timeout=8000)
            except PWTimeout:
                print("  [warn] .srp-results didn't appear — page may be empty or slow.")

            return self._page.content()   # fully rendered HTML including JS content

        except PWTimeout:
            print("  [!] Page timed out.")
            return None
        except Exception as exc:
            print(f"  [!] Error fetching page: {exc}")
            return None

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse_page(self, html: str) -> list[SoldListing]:
        soup  = BeautifulSoup(html, "lxml")
        items = soup.select("li.s-card[data-listingid]")

        if self.debug:
            print(f"  [debug] li.s-card[data-listingid] count: {len(items)}")
            if not items:
                for sel in ["li.s-card", ".srp-results li", ".s-item"]:
                    n = len(soup.select(sel))
                    if n:
                        print(f"  [debug] fallback selector {sel!r} → {n}")

        return [lst for item in items if (lst := self._parse_item(item))]

    def _parse_item(self, item) -> Optional[SoldListing]:
        title_el = item.select_one(".s-card__title")
        if not title_el:
            return None
        title = title_el.get_text(" ", strip=True)
        if not title or "Shop on eBay" in title:
            return None

        price_el  = item.select_one(".s-card__price")
        price_txt = price_el.get_text(" ", strip=True) if price_el else ""
        price, currency = self._parse_price(price_txt)

        sold_date = "N/A"
        for sel in (".s-card__caption", ".s-card__footer", ".s-card__attribute-row"):
            el = item.select_one(sel)
            if el:
                txt = el.get_text(" ", strip=True)
                if txt:
                    sold_date = txt
                    break

        cond_el   = item.select_one(".s-card__subtitle")
        condition = cond_el.get_text(" ", strip=True) if cond_el else "N/A"

        secondary_el = item.select_one(".su-card-container__attributes__secondary")
        shipping     = secondary_el.get_text(" ", strip=True) if secondary_el else "N/A"

        link_el = item.select_one("a.s-card__link")
        url     = link_el["href"].split("?")[0] if link_el and link_el.get("href") else "N/A"

        img_el    = item.select_one(".s-card__image img, .su-image img")
        image_url = ""
        if img_el:
            image_url = img_el.get("src") or img_el.get("data-src") or ""

        return SoldListing(
            title=title, price=price, currency=currency,
            sold_date=sold_date, condition=condition,
            shipping=shipping, url=url, image_url=image_url,
        )

    @staticmethod
    def _parse_price(text: str) -> tuple[float, str]:
        text = text.split(" to ")[0]
        currency_map = {"$": "USD", "£": "GBP", "€": "EUR", "C $": "CAD", "AU $": "AUD"}
        currency = "USD"
        for symbol, code in currency_map.items():
            if symbol in text:
                currency = code
                break
        numeric = re.sub(r"[^\d.]", "", text)
        try:
            return float(numeric), currency
        except ValueError:
            return 0.0, currency

    def _save_debug_html(self, html: str) -> None:
        path = "ebay_last_empty_response.html"
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  [debug] HTML saved to {path}")


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------

def save_csv(listings: list[SoldListing], path: str) -> None:
    if not listings:
        print("No listings to save.")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[fld.name for fld in fields(SoldListing)])
        writer.writeheader()
        writer.writerows(asdict(l) for l in listings)
    print(f"Saved {len(listings)} rows → {path}")


def save_json(listings: list[SoldListing], path: str) -> None:
    if not listings:
        print("No listings to save.")
        return
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(l) for l in listings], f, indent=2, ensure_ascii=False)
    print(f"Saved {len(listings)} records → {path}")


def print_summary(listings: list[SoldListing]) -> None:
    if not listings:
        print("\nNo listings found.")
        return
    prices = [l.price for l in listings if l.price > 0]
    print("\n" + "=" * 58)
    print(f"  Results      : {len(listings)} sold listings")
    if prices:
        print(f"  Price range  : ${min(prices):.2f} – ${max(prices):.2f}")
        print(f"  Average price: ${sum(prices) / len(prices):.2f}")
        print(f"  Median price : ${sorted(prices)[len(prices) // 2]:.2f}")
    print("=" * 58)
    print("\nTop 5 listings:")
    for i, l in enumerate(listings[:5], 1):
        print(f"  {i}. {l.title[:56]:<56}  {l.currency} {l.price:.2f}")
        print(f"     {l.sold_date}  |  {l.condition}  |  {l.shipping}")