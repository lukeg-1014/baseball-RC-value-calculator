import pybaseball
from pybaseball import batting_stats
from pybaseball import standings
from pybaseball import playerid_lookup
from pybaseball import cache
from pybaseball import pitching_stats
from pybaseball import batting_stats_bref
from ebayscrape import EbaySoldScraper, SoldListing, save_csv, save_json
import numpy as np
from pybaseball import playerid_lookup

# Look up the player by last and first name
player_info = playerid_lookup('judge', 'aaron')

# Extract their rookie year
rookie_year = player_info['mlb_played_first'].iloc[0]



cache.enable()
# gets all the stats from the year CALCULATE OUTLIER FORMULA
df = batting_stats_bref(2026)

class Player:
  #When bref pulls in data, it has trouble determining what is known as 'qualified plate appearances' when calculating OBP. 
  # Multiplying and dividing seems to resolve this issue
  leagueOBP = (df['OBP'] * df['PA']).sum() / df['PA'].sum()
  leagueSLG = (df['SLG'] * df['PA']).sum() / df['PA'].sum()
  leagueOPS = (df['OPS'] * df['PA']).sum() / df['PA'].sum()
  def __init__(self, first, last, rookie):
    #Only takes in the player name
    self.first = first
    self.last = last
    self.playerID = playerid_lookup(last, first)
    self.rookieYear = rookie
    #Creates an object from the player name
    playerObj = df[df['Name'] == first + " " + last]
    if playerObj.empty:
        raise ValueError(f"Player {first} {last} not found in dataset")
    #Kind of like an ArrayList
    self.team = playerObj["Tm"].iloc[0]
    self.playerOBP = playerObj['OBP'].iloc[0]
    self.playerSLG = playerObj['SLG'].iloc[0]
    self.playerOPS = playerObj['OPS'].iloc[0]
    self.playerOPSPlus = round(100 * ((self.playerOBP / self.leagueOBP) + (self.playerSLG / self.leagueSLG) - 1))
  # toString method
  def __str__(self):
    return f"Player Name: {self.first} {self.last} OPS+: {self.playerOPSPlus} Rookie Year: {self.rookieYear}"

#Object Creation


inputFirst = input("What is the Player's First Name: ")
inputLast = input("What is the Player's Last Name: ")
inputRookieYr = input("What is the Player's Rookie Year: ")
inputPlayer = Player(inputFirst, inputLast, inputRookieYr)

print(inputPlayer)

mainScrape = EbaySoldScraper(delay=2.0)
min_results = 5
listings = mainScrape.search(f"Topps {inputPlayer.first} {inputPlayer.last} Rookie Card {int(inputPlayer.rookieYear)} -bowman -ginter -psa -bgs -cgc -gypsy -now -lot -prizm -refractor -numbered -archives -heritage -graded", max_pages=1)

csvName = (inputPlayer.first + "_" + inputPlayer.last + "_eBay_sold_v2.csv")


# Filter in Python instead of using eBay quotes — same result, no challenge
listings = mainScrape.filter_listings(listings, [
    inputPlayer.first,
    inputPlayer.last,
    "Rookie",
    "Topps",
])

print(f"Total listings:   {len(listings)}")
save_csv(listings, csvName)

prices = [l.price for l in listings if l.price > 0]
if prices:
    print(f"Avg price: ${sum(prices)/len(prices):.2f}")
mainScrape.close()
