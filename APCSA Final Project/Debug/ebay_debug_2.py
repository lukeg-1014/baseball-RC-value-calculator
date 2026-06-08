"""
Deep-probe the .srp-results li elements eBay is now returning.
Run:  python ebay_probe2.py
(Reads the ebay_debug_raw.html you already saved — no extra requests needed)
"""
from bs4 import BeautifulSoup

with open("ebay_debug_raw.html", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "lxml")

items = soup.select(".srp-results li")
print(f"Total .srp-results li: {len(items)}\n")

# Print the raw HTML of the first real-looking item
# (skip the first couple which are often header/ad injections)
for i, item in enumerate(items[:6]):
    text = item.get_text(" ", strip=True)
    if len(text) < 20:
        continue
    print(f"=== Item {i} (first {600} chars of inner HTML) ===")
    print(str(item)[:600])
    print()
    break  # just show the first meaty one

# Now dump ALL class names that appear inside .srp-results li
print("\n=== All unique class names inside .srp-results li ===")
seen = set()
for item in items:
    for tag in item.find_all(True):
        for cls in tag.get("class", []):
            seen.add(cls)
for cls in sorted(seen):
    print(" ", cls)