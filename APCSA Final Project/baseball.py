import pybaseball
from pybaseball import batting_stats
from pybaseball import playerid_lookup
from pybaseball import cache
from pybaseball import batting_stats_bref
from ebayscrape import EbaySoldScraper, SoldListing, save_csv
import numpy as np
from pybaseball import playerid_lookup
from datetime import datetime
import time

currentYear = datetime.now().year

cache.enable()
# gets all the stats from the year
df = batting_stats_bref(2026)

class Player:
  #When bref pulls in data, it has trouble determining what is known as 'qualified plate appearances' when calculating OBP. 
  # Multiplying and dividing seems to resolve this issue
  leagueOBP = (df['OBP'] * df['PA']).sum() / df['PA'].sum()
  leagueSLG = (df['SLG'] * df['PA']).sum() / df['PA'].sum()
  leagueOPS = (df['OPS'] * df['PA']).sum() / df['PA'].sum()
  def __init__(self, first, last):
    #Only takes in the player name
    self.first = first
    self.last = last
    self.playerID = playerid_lookup(last, first)
    self.avgCardPrice = None
    #Creates an object from the player name
    playerObj = df[df['Name'] == first + " " + last]
    if playerObj.empty:
        raise ValueError(f"Player {first} {last} not found in dataset")
    #Kind of like an ArrayList
    self.team = playerObj["Tm"].iloc[0]
    self.rookieYear = int(self.playerID["mlb_played_first"].iloc[0])
    self.yearsSinceRookie = currentYear - self.rookieYear
    self.vintageMultiplier = (1 + 0.062) ** self.yearsSinceRookie
    self.playerOBP = playerObj['OBP'].iloc[0]
    self.playerSLG = playerObj['SLG'].iloc[0]
    self.playerOPS = playerObj['OPS'].iloc[0]
    self.playerOPSPlus = round(100 * ((self.playerOBP / self.leagueOBP) + (self.playerSLG / self.leagueSLG) - 1))
  # toString method
  def __str__(self):
    return f"Player Name: {self.first} {self.last}\nOPS+: {self.playerOPSPlus}\nRookie Year: {self.rookieYear}"


def cardValueScore(player: Player, avgPrice: float):
   baseValue: float = 4.00
   fairValue = baseValue * (player.playerOPSPlus / 100) * player.vintageMultiplier
   #OPS multiplier. Basicially a base card isn't really worth $4 so this adds (or subtracts) onto the already existing base
   if player.playerOPSPlus < 50:
      fairValue *= .22
   elif player.playerOPSPlus < 75:
      fairValue *= .45
   elif player.playerOPSPlus <= 90:
      fairValue *= .66
   elif player.playerOPSPlus < 100:
      fairValue *= .76
   elif player.playerOPSPlus <= 110:
      fairValue *= 1.05
   elif player.playerOPSPlus <= 120:
      fairValue *= 1.16
   elif player.playerOPSPlus <= 140:
      fairValue *= 1.29
   elif player.playerOPSPlus <= 155:
      fairValue *= 1.36
   elif player.playerOPSPlus <= 170:
      fairValue *= 1.42
   elif player.playerOPSPlus <= 180:
      fairValue *= 1.48
   elif player.playerOPSPlus <= 195:
      fairValue *= 1.54
   else:
      fairValue *= 1.6



   premium = fairValue - avgPrice
   percentDiff = (premium / avgPrice) * 100
   if premium > avgPrice * 0.10:
      recommendation = f"BUY    — {percentDiff:.1f}% underpriced vs fair value"
   elif premium >= -avgPrice * 0.10:
      recommendation = f"NEUTRAL — within 10% of fair value"
   else:
      recommendation = f"PASS   — {abs(percentDiff):.1f}% overpriced vs fair value"
   return {
      "ops_plus":           player.playerOPSPlus,
      "years_since_rookie": player.yearsSinceRookie,
      "performance_mult":   round(player.playerOPSPlus/100, 3),
      "vintage_mult":       round(player.vintageMultiplier, 3),
      "fair_value":         f"${fairValue:.2f}",
      "avg_sold_price":     f"${avgPrice:.2f}",
      "premium":            f"${premium:.2f}",
      "recommendation":     recommendation
    }

def filter_base_cards(listings: list, must_contain: list[str]) -> list:
    """
    Filters to likely base cards by:
    1. Title keyword matching
    2. Removing price outliers above the IQR upper fence
    """
    # Step 1 — keyword filter first
    keyword_filtered = [
        l for l in listings
        if all(p.lower() in l.title.lower() for p in must_contain)
        and l.price > 0.50
    ]

    if not keyword_filtered:
        return []

    # Step 2 — find the IQR price ceiling
    prices = [l.price for l in keyword_filtered]
    q1     = np.percentile(prices, 25)
    q3     = np.percentile(prices, 75)
    iqr    = q3 - q1
    ceiling = q3 + (1.5 * iqr)   # standard outlier formula

    print(f"  Price range before filter: ${min(prices):.2f} – ${max(prices):.2f}")
    print(f"  IQR ceiling (base card cutoff): ${ceiling:.2f}")

    # Step 3 — drop anything above the ceiling
    return [l for l in keyword_filtered if l.price <= ceiling]


#Object Creation


inputFirst = input("What is the Player's First Name: ")
inputLast = input("What is the Player's Last Name: ")
inputPlayer = Player(inputFirst, inputLast)
print(f"The recorded player's rookie year is: {inputPlayer.rookieYear}")
time.sleep(.5)
changeRookieYearQ = input("This may or may not be the year the player has a rookie card. \nWould you like to enter a new year? (Y/N): ").upper()
if changeRookieYearQ == "Y":
   changeRY = input("What year do you want to change it to? ")
   while True:
      try:
         changeRY = int(changeRY)
         break
      except ValueError:
         print("Invalid input! Please enter a valid integer! ")
   inputPlayer.rookieYear = changeRY
else:
   print("No Change Detected")
time.sleep(.1)
print("--------------------------")
print(inputPlayer)
time.sleep(.4)
print("--------------------------")

mainScrape = EbaySoldScraper(delay=2.0)


# Filter in Python instead of using eBay quotes — same result, no challenge
listings = mainScrape.search(
    f"Topps {inputPlayer.first} {inputPlayer.last} Rookie Card {inputPlayer.rookieYear}"
    " -psa -bgs -cgc -sgc -graded -grade"
    " -/25 -/50 -/75 -/99 -/100 -/150 -/199 -/249 -/299 -/499 -/999 -numbered"
    " -refractor -prizm -chrome -gold -rainbow -superfractor"
    " -auto -autograph -patch -short -sp -ssp -variation"
    " -lot -bundle -reprint -custom -bowman -heritage -archives -gypsy -ginter",
    max_pages=2   # grab more raw results so the filter has more to work with
)

listings = filter_base_cards(listings, [
    inputPlayer.first,
    inputPlayer.last,
    "Rookie",
    "Topps",
])
save_csv(listings, f"{inputPlayer.first}_{inputPlayer.last}_eBay_sold_v3.csv")
mainScrape.close()
print(f"Listings after filter: {len(listings)}")

priceArr = [l.price for l in listings if l.price > 0]
if priceArr:
    avg_price = sum(priceArr) / len(priceArr)
    print(f"Avg sold price: ${avg_price:.2f}")

    result = cardValueScore(inputPlayer, avg_price)
    print("\n--- Card Value Analysis ---")
    for k, v in result.items():
        print(f"  {k:<22} {v}")