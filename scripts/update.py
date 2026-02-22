"""
update.py — Re-scrape all restaurants and update restaurants.csv.

- Re-queries each restaurant for its current furthest available date
- Updates release_days_ahead, release_time_est, and last_verified if changed
- Appends newly unresolvable entries to manual_review.csv
- Logs all activity to logs/update.log

Run: python scripts/update.py
"""

import csv
import logging
import sys
import time
import random
import os
from datetime import date
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.scrapers import scrape_restaurant

# ---------------------------------------------------------------------------
# Paths & logging
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "update.log"),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------

def load_csv(path: Path, fieldnames: list) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def write_csv(rows: list[dict], path: Path, fieldnames: list):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def append_csv(rows: list[dict], path: Path, fieldnames: list):
    """Append rows to CSV, creating it with header if it doesn't exist."""
    file_exists = path.exists() and path.stat().st_size > 0
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)

# ---------------------------------------------------------------------------
# Update logic
# ---------------------------------------------------------------------------

def _skip_platform(platform: str) -> bool:
    """Some platforms/restaurants should not be re-scraped automatically."""
    return platform.lower() in ("phone", "walk-in", "walkin", "email")


def run_update():
    logger.info("=== Starting NYC Reservation Times update ===")

    rows = load_csv(RESTAURANTS_CSV, FIELDNAMES)
    if not rows:
        logger.error("restaurants.csv is empty or missing — run generate_seed_csv.py first.")
        sys.exit(1)

    today = date.today().isoformat()
    updated = 0
    unchanged = 0
    skipped = 0
    errors = 0
    new_manual = []

    for i, row in enumerate(rows):
        name = row.get("restaurant_name", "")
        platform = row.get("booking_platform", "")
        source_url = row.get("source_url", "")

        if _skip_platform(platform):
            logger.info("[%d/%d] SKIP %s (%s) — manual platform", i + 1, len(rows), name, platform)
            skipped += 1
            continue

        logger.info("[%d/%d] Updating %s (%s)", i + 1, len(rows), name, platform)

        try:
            scraped = scrape_restaurant(platform, source_url)
        except Exception as e:
            logger.warning("Unexpected error scraping %s: %s", name, e)
            scraped = {"error": str(e)[:200]}

        error = scraped.get("error", "")
        new_days = scraped.get("release_days_ahead")
        new_time = scraped.get("release_time_est")
        new_notes = scraped.get("release_notes", "")

        if error or new_days is None:
            reason = error or "Scrape returned no availability data"
            logger.warning("  -> Could not determine release window: %s", reason)
            errors += 1
            new_manual.append({**row, "reason": reason})
            continue

        # Check whether anything changed
        old_days = row.get("release_days_ahead", "")
        old_time = row.get("release_time_est", "")

        changed = str(new_days) != str(old_days) or str(new_time) != str(old_time)

        if changed:
            logger.info(
                "  -> Updated: days_ahead %s -> %s, release_time %s -> %s",
                old_days, new_days, old_time, new_time,
            )
            row["release_days_ahead"] = new_days
            row["release_time_est"] = new_time or ""
            if new_notes:
                row["release_notes"] = new_notes
            row["last_verified"] = today
            updated += 1
        else:
            # Still update last_verified to record we checked today
            row["last_verified"] = today
            unchanged += 1

        # Polite pause between requests
        if i < len(rows) - 1:
            time.sleep(random.uniform(1.5, 4.0))

    # Persist changes
    write_csv(rows, RESTAURANTS_CSV, FIELDNAMES)
    logger.info("Wrote %d rows to %s", len(rows), RESTAURANTS_CSV)

    # Merge new_manual entries with existing manual_review.csv
    if new_manual:
        existing_manual = load_csv(MANUAL_CSV, MANUAL_FIELDNAMES)
        existing_names = {r.get("restaurant_name") for r in existing_manual}
        truly_new = [r for r in new_manual if r.get("restaurant_name") not in existing_names]
        if truly_new:
            append_csv(truly_new, MANUAL_CSV, MANUAL_FIELDNAMES)
            logger.info("Appended %d new entries to %s", len(truly_new), MANUAL_CSV)

    logger.info(
        "=== Update complete: %d updated, %d unchanged, %d skipped, %d errors ===",
        updated, unchanged, skipped, errors,
    )
    return {"updated": updated, "unchanged": unchanged, "skipped": skipped, "errors": errors}


if __name__ == "__main__":
    run_update()
