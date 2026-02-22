"""
seed.py — Build the initial restaurants.csv from a hardcoded list + live scraping.
Run: python scripts/seed.py
"""

import os
import csv
import time
import random
import logging
import sys
from datetime import date
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.scrapers import scrape_restaurant

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/seed.log"),
    ],
)
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

RESTAURANTS_CSV = DATA_DIR / "restaurants.csv"
MANUAL_CSV = DATA_DIR / "manual_review.csv"

FIELDNAMES = [
    "restaurant_name",
    "neighborhood",
    "cuisine",
    "booking_platform",
    "release_days_ahead",
    "release_time_est",
    "release_notes",
    "last_verified",
    "source_url",
]

MANUAL_FIELDNAMES = FIELDNAMES + ["reason"]

# ---------------------------------------------------------------------------
# Master restaurant list
# ---------------------------------------------------------------------------

RESTAURANTS = [
    # ---- Resy restaurants ----
    {"restaurant_name": "Carbone", "neighborhood": "Greenwich Village", "cuisine": "Italian-American", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/carbone"},
    {"restaurant_name": "Via Carota", "neighborhood": "West Village", "cuisine": "Italian", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/via-carota"},
    {"restaurant_name": "Don Angie", "neighborhood": "West Village", "cuisine": "Italian-American", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/don-angie"},
    {"restaurant_name": "Lilia", "neighborhood": "Williamsburg", "cuisine": "Italian", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/lilia"},
    {"restaurant_name": "Tatiana", "neighborhood": "Upper West Side", "cuisine": "American", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/tatiana-by-kwame-onwuachi"},
    {"restaurant_name": "Frenchette", "neighborhood": "Tribeca", "cuisine": "French", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/frenchette"},
    {"restaurant_name": "Estela", "neighborhood": "Nolita", "cuisine": "Mediterranean", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/estela"},
    {"restaurant_name": "L'Artusi", "neighborhood": "West Village", "cuisine": "Italian", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/l-artusi"},
    {"restaurant_name": "Torrisi", "neighborhood": "Nolita", "cuisine": "Italian-American", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/torrisi-bar-and-restaurant"},
    {"restaurant_name": "4 Charles Prime Rib", "neighborhood": "West Village", "cuisine": "Steakhouse", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/4-charles-prime-rib"},
    {"restaurant_name": "Crown Shy", "neighborhood": "Financial District", "cuisine": "American", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/crown-shy"},
    {"restaurant_name": "Gramercy Tavern", "neighborhood": "Gramercy", "cuisine": "American", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/gramercy-tavern"},
    {"restaurant_name": "The Modern", "neighborhood": "Midtown", "cuisine": "American-French", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/the-modern"},
    {"restaurant_name": "Aquavit", "neighborhood": "Midtown", "cuisine": "Scandinavian", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/aquavit"},
    {"restaurant_name": "Semma", "neighborhood": "Greenwich Village", "cuisine": "South Indian", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/semma"},
    {"restaurant_name": "Rezdôra", "neighborhood": "Flatiron", "cuisine": "Italian", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/rezdora"},
    {"restaurant_name": "Jua", "neighborhood": "Flatiron", "cuisine": "Korean", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/jua"},
    {"restaurant_name": "Le Bernardin", "neighborhood": "Midtown", "cuisine": "French Seafood", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/le-bernardin"},
    {"restaurant_name": "Daniel", "neighborhood": "Upper East Side", "cuisine": "French", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/daniel"},
    {"restaurant_name": "Jean-Georges", "neighborhood": "Upper West Side", "cuisine": "French-American", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/jean-georges"},
    {"restaurant_name": "Eleven Madison Park", "neighborhood": "Flatiron", "cuisine": "Plant-based Tasting Menu", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/eleven-madison-park"},
    {"restaurant_name": "Atomix", "neighborhood": "Midtown", "cuisine": "Korean Tasting Menu", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/atomix"},
    {"restaurant_name": "Atera", "neighborhood": "Tribeca", "cuisine": "New Nordic Tasting Menu", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/atera"},
    {"restaurant_name": "Aska", "neighborhood": "Williamsburg", "cuisine": "Scandinavian Tasting Menu", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/aska"},
    {"restaurant_name": "Blanca", "neighborhood": "Bushwick", "cuisine": "Italian Tasting Menu", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/blanca"},
    {"restaurant_name": "Buvette", "neighborhood": "West Village", "cuisine": "French", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/buvette"},
    {"restaurant_name": "Bar Goto Niban", "neighborhood": "Williamsburg", "cuisine": "Japanese Bar", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/bar-goto-niban"},
    {"restaurant_name": "Balthazar", "neighborhood": "SoHo", "cuisine": "French Brasserie", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/balthazar"},
    {"restaurant_name": "Sadelle's", "neighborhood": "SoHo", "cuisine": "Jewish-American", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/sadelles"},
    {"restaurant_name": "Nobu Downtown", "neighborhood": "Tribeca", "cuisine": "Japanese-Peruvian", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/nobu-downtown"},
    {"restaurant_name": "Nobu 57", "neighborhood": "Midtown", "cuisine": "Japanese-Peruvian", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/nobu-57"},
    {"restaurant_name": "Cote", "neighborhood": "Flatiron", "cuisine": "Korean Steakhouse", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/cote-korean-steakhouse"},
    {"restaurant_name": "Nomo SoHo", "neighborhood": "SoHo", "cuisine": "American", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/nomo-soho"},
    {"restaurant_name": "Lure Fishbar", "neighborhood": "SoHo", "cuisine": "Seafood", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/lure-fishbar"},
    {"restaurant_name": "Frankies 457 Spuntino", "neighborhood": "Carroll Gardens", "cuisine": "Italian", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/frankies-457-spuntino"},
    {"restaurant_name": "Dhamaka", "neighborhood": "Lower East Side", "cuisine": "South Asian", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/dhamaka"},
    {"restaurant_name": "Oxomoco", "neighborhood": "Greenpoint", "cuisine": "Mexican", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/oxomoco"},
    {"restaurant_name": "Lighthouse", "neighborhood": "Williamsburg", "cuisine": "American", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/lighthouse-bk"},
    {"restaurant_name": "Sunday in Brooklyn", "neighborhood": "Williamsburg", "cuisine": "American", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/sunday-in-brooklyn"},
    {"restaurant_name": "Olmsted", "neighborhood": "Prospect Heights", "cuisine": "American", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/olmsted"},
    {"restaurant_name": "Maison Premiere", "neighborhood": "Williamsburg", "cuisine": "Oyster Bar", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/maison-premiere"},
    {"restaurant_name": "Oiji Mi", "neighborhood": "Flatiron", "cuisine": "Modern Korean", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/oiji-mi"},
    {"restaurant_name": "The Musket Room", "neighborhood": "Nolita", "cuisine": "New Zealand-inspired", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/the-musket-room"},
    {"restaurant_name": "King", "neighborhood": "SoHo", "cuisine": "French-Italian", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/king-restaurant"},
    {"restaurant_name": "Bar Primi", "neighborhood": "East Village", "cuisine": "Italian", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/bar-primi"},
    {"restaurant_name": "Loring Place", "neighborhood": "Greenwich Village", "cuisine": "American", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/loring-place"},
    {"restaurant_name": "Flora Bar", "neighborhood": "Upper East Side", "cuisine": "American", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/flora-bar"},
    {"restaurant_name": "Forsythia", "neighborhood": "Lower East Side", "cuisine": "American", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/forsythia"},
    {"restaurant_name": "Fausto", "neighborhood": "Park Slope", "cuisine": "Italian-American", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/fausto"},
    {"restaurant_name": "Shukette", "neighborhood": "Chelsea", "cuisine": "Israeli", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/shukette"},
    {"restaurant_name": "Superiority Burger", "neighborhood": "East Village", "cuisine": "Vegetarian", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/superiority-burger"},
    {"restaurant_name": "Claro", "neighborhood": "Gowanus", "cuisine": "Oaxacan", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/claro"},
    {"restaurant_name": "Ci Siamo", "neighborhood": "Hudson Yards", "cuisine": "Italian", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/ci-siamo"},
    {"restaurant_name": "One White Street", "neighborhood": "Tribeca", "cuisine": "American", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/one-white-street"},
    {"restaurant_name": "Cookshop", "neighborhood": "Chelsea", "cuisine": "American", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/cookshop"},
    {"restaurant_name": "Penny", "neighborhood": "West Village", "cuisine": "American", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/penny-restaurant"},
    {"restaurant_name": "Carne Mare", "neighborhood": "Financial District", "cuisine": "Steakhouse", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/carne-mare"},
    {"restaurant_name": "Joe's Pizza", "neighborhood": "West Village", "cuisine": "Pizza", "booking_platform": "Walk-in", "source_url": "https://joespizzanyc.com"},
    # ---- OpenTable restaurants ----
    {"restaurant_name": "Per Se", "neighborhood": "Columbus Circle", "cuisine": "French-American Tasting Menu", "booking_platform": "OpenTable", "source_url": "https://www.opentable.com/per-se"},
    {"restaurant_name": "Masa", "neighborhood": "Columbus Circle", "cuisine": "Japanese Tasting Menu", "booking_platform": "OpenTable", "source_url": "https://www.opentable.com/masa-new-york"},
    {"restaurant_name": "Gabriel Kreuther", "neighborhood": "Midtown", "cuisine": "Alsatian-American", "booking_platform": "OpenTable", "source_url": "https://www.opentable.com/gabriel-kreuther"},
    {"restaurant_name": "Sushi Yasuda", "neighborhood": "Midtown", "cuisine": "Japanese Sushi", "booking_platform": "OpenTable", "source_url": "https://www.opentable.com/sushi-yasuda"},
    {"restaurant_name": "Smith & Wollensky", "neighborhood": "Midtown", "cuisine": "Steakhouse", "booking_platform": "OpenTable", "source_url": "https://www.opentable.com/smith-and-wollensky-new-york"},
    {"restaurant_name": "Peter Luger Steak House", "neighborhood": "Williamsburg", "cuisine": "Steakhouse", "booking_platform": "OpenTable", "source_url": "https://www.opentable.com/peter-luger-steak-house"},
    {"restaurant_name": "The River Cafe", "neighborhood": "DUMBO", "cuisine": "American", "booking_platform": "OpenTable", "source_url": "https://www.opentable.com/the-river-cafe"},
    {"restaurant_name": "Ai Fiori", "neighborhood": "Midtown", "cuisine": "Italian-French", "booking_platform": "OpenTable", "source_url": "https://www.opentable.com/ai-fiori"},
    {"restaurant_name": "Aureole", "neighborhood": "Midtown", "cuisine": "American", "booking_platform": "OpenTable", "source_url": "https://www.opentable.com/aureole-new-york"},
    {"restaurant_name": "Gotham", "neighborhood": "Greenwich Village", "cuisine": "American", "booking_platform": "OpenTable", "source_url": "https://www.opentable.com/gotham-restaurant"},
    {"restaurant_name": "The Pool", "neighborhood": "Midtown", "cuisine": "American", "booking_platform": "OpenTable", "source_url": "https://www.opentable.com/the-pool-restaurant-new-york"},
    {"restaurant_name": "Betony", "neighborhood": "Midtown", "cuisine": "American", "booking_platform": "OpenTable", "source_url": "https://www.opentable.com/betony"},
    {"restaurant_name": "Minetta Tavern", "neighborhood": "Greenwich Village", "cuisine": "French", "booking_platform": "OpenTable", "source_url": "https://www.opentable.com/minetta-tavern"},
    {"restaurant_name": "Il Mulino", "neighborhood": "West Village", "cuisine": "Italian", "booking_platform": "OpenTable", "source_url": "https://www.opentable.com/il-mulino-new-york-downtown"},
    {"restaurant_name": "Keens Steakhouse", "neighborhood": "Midtown", "cuisine": "Steakhouse", "booking_platform": "OpenTable", "source_url": "https://www.opentable.com/keens-steakhouse"},
    # ---- Tock restaurants ----
    {"restaurant_name": "Ko (Momofuku Ko)", "neighborhood": "East Village", "cuisine": "American Tasting Menu", "booking_platform": "Tock", "source_url": "https://www.exploretock.com/momofukuko"},
    {"restaurant_name": "Chef's Table at Brooklyn Fare", "neighborhood": "Downtown Brooklyn", "cuisine": "French Tasting Menu", "booking_platform": "Tock", "source_url": "https://www.exploretock.com/brooklynfare"},
    {"restaurant_name": "Shoji at 69 Leonard", "neighborhood": "Tribeca", "cuisine": "Japanese Omakase", "booking_platform": "Tock", "source_url": "https://www.exploretock.com/shoji"},
    {"restaurant_name": "Sushi Noz", "neighborhood": "Upper East Side", "cuisine": "Japanese Omakase", "booking_platform": "Tock", "source_url": "https://www.exploretock.com/sushinoz"},
    {"restaurant_name": "Noda", "neighborhood": "Midtown", "cuisine": "Japanese Omakase", "booking_platform": "Tock", "source_url": "https://www.exploretock.com/nodalcnyc"},
    {"restaurant_name": "Sushi by Bou", "neighborhood": "Midtown", "cuisine": "Japanese Omakase", "booking_platform": "Tock", "source_url": "https://www.exploretock.com/sushibybou"},
    {"restaurant_name": "Sushi Nakazawa", "neighborhood": "West Village", "cuisine": "Japanese Omakase", "booking_platform": "Tock", "source_url": "https://www.exploretock.com/sushinakazawa"},
    {"restaurant_name": "Sushi Seki", "neighborhood": "Upper East Side", "cuisine": "Japanese Sushi", "booking_platform": "Tock", "source_url": "https://www.exploretock.com/sushisekinyc"},
    {"restaurant_name": "Ugly Baby", "neighborhood": "Carroll Gardens", "cuisine": "Thai", "booking_platform": "Tock", "source_url": "https://www.exploretock.com/uglybaby"},
    {"restaurant_name": "Nari", "neighborhood": "Midtown", "cuisine": "Thai", "booking_platform": "Tock", "source_url": "https://www.exploretock.com/nari-nyc"},
    # ---- Phone / Special ----
    {"restaurant_name": "Lucali", "neighborhood": "Carroll Gardens", "cuisine": "Pizza", "booking_platform": "Phone", "source_url": "https://www.lucali.com"},
    {"restaurant_name": "Rao's", "neighborhood": "East Harlem", "cuisine": "Italian-American", "booking_platform": "Phone", "source_url": "https://www.raos.com/reservations"},
    {"restaurant_name": "Sushi Saito NYC", "neighborhood": "Tribeca", "cuisine": "Japanese Omakase", "booking_platform": "Email", "source_url": "https://sushisaito.com"},
    {"restaurant_name": "Casa Lever", "neighborhood": "Midtown", "cuisine": "Italian", "booking_platform": "OpenTable", "source_url": "https://www.opentable.com/casa-lever"},
    {"restaurant_name": "Manhatta", "neighborhood": "Financial District", "cuisine": "American", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/manhatta"},
    {"restaurant_name": "Oxalis", "neighborhood": "Prospect Heights", "cuisine": "French-American", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/oxalis"},
    {"restaurant_name": "Laser Wolf", "neighborhood": "Williamsburg", "cuisine": "Israeli", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/laser-wolf-brooklyn"},
    {"restaurant_name": "Cadence", "neighborhood": "East Village", "cuisine": "Soul Food Vegan", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/cadence"},
    {"restaurant_name": "Tatiana by Kwame Onwuachi", "neighborhood": "Upper West Side", "cuisine": "Afro-Caribbean", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/tatiana-by-kwame-onwuachi"},
    {"restaurant_name": "Indian Accent", "neighborhood": "Midtown", "cuisine": "Modern Indian", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/indian-accent-new-york"},
    {"restaurant_name": "Saga", "neighborhood": "Financial District", "cuisine": "American Tasting Menu", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/saga"},
    {"restaurant_name": "Nix", "neighborhood": "Greenwich Village", "cuisine": "Vegetarian", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/nix"},
    {"restaurant_name": "Momofuku Noodle Bar", "neighborhood": "East Village", "cuisine": "Japanese-American", "booking_platform": "Tock", "source_url": "https://www.exploretock.com/momofukunoodlebar"},
    {"restaurant_name": "Sushi Amane", "neighborhood": "Midtown", "cuisine": "Japanese Omakase", "booking_platform": "Tock", "source_url": "https://www.exploretock.com/sushiamane"},
    {"restaurant_name": "Torien", "neighborhood": "SoHo", "cuisine": "Japanese Yakitori", "booking_platform": "Tock", "source_url": "https://www.exploretock.com/torien-nyc"},
    {"restaurant_name": "Dirt Candy", "neighborhood": "Lower East Side", "cuisine": "Vegetarian", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/dirt-candy"},
    {"restaurant_name": "Llama Inn", "neighborhood": "Williamsburg", "cuisine": "Peruvian", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/llama-inn"},
    {"restaurant_name": "Quality Eats", "neighborhood": "West Village", "cuisine": "Steakhouse", "booking_platform": "OpenTable", "source_url": "https://www.opentable.com/quality-eats-west-village"},
    {"restaurant_name": "Sartiano's", "neighborhood": "SoHo", "cuisine": "Italian", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/sartianos"},
    {"restaurant_name": "Charlie Bird", "neighborhood": "SoHo", "cuisine": "Italian-American", "booking_platform": "Resy", "source_url": "https://resy.com/cities/ny/venues/charlie-bird"},
]


def write_csv(rows: list, filepath: Path, fieldnames: list):
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    logger.info("Wrote %d rows to %s", len(rows), filepath)


def seed(pilot_only: bool = False, pilot_names: list = None):
    restaurants = RESTAURANTS
    if pilot_only and pilot_names:
        restaurants = [r for r in restaurants if r["restaurant_name"] in pilot_names]

    results = []
    manual = []
    today = date.today().isoformat()

    for i, r in enumerate(restaurants):
        logger.info("[%d/%d] Scraping %s (%s)", i + 1, len(restaurants), r["restaurant_name"], r["booking_platform"])

        scraped = scrape_restaurant(r["booking_platform"], r["source_url"])

        row = {
            "restaurant_name": r["restaurant_name"],
            "neighborhood": r["neighborhood"],
            "cuisine": r["cuisine"],
            "booking_platform": r["booking_platform"],
            "release_days_ahead": scraped.get("release_days_ahead", ""),
            "release_time_est": scraped.get("release_time_est", ""),
            "release_notes": scraped.get("release_notes", ""),
            "last_verified": today,
            "source_url": r["source_url"],
        }

        error = scraped.get("error", "")
        if error or row["release_days_ahead"] in (None, ""):
            manual_row = {**row, "reason": error or "Could not determine release window automatically"}
            manual.append(manual_row)
            # Still keep in main CSV with blank release_days_ahead
            results.append(row)
        else:
            results.append(row)

        # Brief pause between restaurants
        if i < len(restaurants) - 1:
            time.sleep(random.uniform(1.5, 3.5))

    write_csv(results, RESTAURANTS_CSV, FIELDNAMES)
    write_csv(manual, MANUAL_CSV, MANUAL_FIELDNAMES)
    logger.info("Done. %d restaurants total, %d flagged for manual review.", len(results), len(manual))
    return results, manual


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Seed NYC restaurant reservation database")
    parser.add_argument("--pilot", action="store_true", help="Run pilot mode on 5 test restaurants only")
    args = parser.parse_args()

    PILOT = ["Carbone", "Via Carota", "Don Angie", "Lilia", "Tatiana by Kwame Onwuachi"]
    seed(pilot_only=args.pilot, pilot_names=PILOT)
