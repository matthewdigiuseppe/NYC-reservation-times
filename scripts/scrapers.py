"""
Scrapers for Resy, OpenTable, and Tock booking platforms.
Infers reservation release windows from available booking data.
"""

import os
import time
import random
import logging
import httpx
from datetime import datetime, date, timedelta
from typing import Optional
import anthropic

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


def jitter(lo: float = 1.0, hi: float = 3.5) -> None:
    """Sleep a random amount to avoid rate-limiting."""
    time.sleep(random.uniform(lo, hi))


def days_ahead(target_date_str: str) -> Optional[int]:
    """Return number of days from today to *target_date_str* (YYYY-MM-DD)."""
    try:
        target = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        delta = (target - date.today()).days
        return max(0, delta)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Anthropic-assisted parsing helper
# ---------------------------------------------------------------------------

def claude_infer(prompt: str) -> str:
    """Call Claude Haiku for lightweight text parsing / inference."""
    if not ANTHROPIC_API_KEY:
        return ""
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        logger.warning("Claude inference failed: %s", e)
        return ""


# ---------------------------------------------------------------------------
# Resy scraper
# ---------------------------------------------------------------------------

RESY_API = "https://api.resy.com/4"


def _resy_headers(api_key: str = "VbWk7s3L4KiK5fzlO7JD3Q5OUB39BoqNmEaTFx8T") -> dict:
    """Headers required by Resy public API."""
    return {
        **BROWSER_HEADERS,
        "Authorization": f'ResyAPI api_key="{api_key}"',
        "X-Origin": "https://resy.com",
        "Referer": "https://resy.com/",
        "Origin": "https://resy.com",
    }


def resy_get_venue_id(slug: str, city: str = "ny") -> Optional[str]:
    """Resolve Resy venue_id from a URL slug."""
    url = f"{RESY_API}/find"
    params = {"slug": slug, "city": city}
    try:
        with httpx.Client(headers=_resy_headers(), timeout=15) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            return str(data.get("id", ""))
    except Exception as e:
        logger.debug("resy_get_venue_id(%s) failed: %s", slug, e)
        return None


def resy_furthest_date(venue_id: str, party_size: int = 2) -> Optional[str]:
    """
    Query Resy calendar for up to 90 days out; return the furthest date
    that has at least one available slot.
    """
    url = f"{RESY_API}/venue/calendar"
    today = date.today()
    last_date = today + timedelta(days=90)
    params = {
        "venue_id": venue_id,
        "num_seats": party_size,
        "start_date": today.isoformat(),
        "end_date": last_date.isoformat(),
    }
    try:
        with httpx.Client(headers=_resy_headers(), timeout=15) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
        # scheduled array has {date, inventory:{reservation:'available'/'sold_out'}}
        scheduled = data.get("scheduled", [])
        available = [
            d["date"]
            for d in scheduled
            if d.get("inventory", {}).get("reservation") == "available"
        ]
        return max(available) if available else None
    except Exception as e:
        logger.debug("resy_furthest_date(%s) failed: %s", venue_id, e)
        return None


def scrape_resy(source_url: str) -> dict:
    """
    Main entry point for a Resy restaurant.
    Returns dict with keys: release_days_ahead, release_time_est, release_notes, error
    """
    result = {
        "release_days_ahead": None,
        "release_time_est": None,
        "release_notes": "",
        "error": "",
    }
    try:
        # Extract slug from URL like https://resy.com/cities/ny/venues/carbone
        parts = [p for p in source_url.rstrip("/").split("/") if p]
        slug = parts[-1]
        city = "ny"
        if "cities" in parts:
            idx = parts.index("cities")
            if idx + 1 < len(parts):
                city = parts[idx + 1]

        jitter(0.5, 1.5)
        # Try venue lookup via /find
        url = f"{RESY_API}/find"
        params = {"slug": slug, "city": city}
        with httpx.Client(headers=_resy_headers(), timeout=15) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            venue_data = r.json()

        venue_id = str(venue_data.get("id", ""))
        if not venue_id:
            result["error"] = "Could not resolve venue ID"
            return result

        jitter(1.0, 2.5)
        furthest = resy_furthest_date(venue_id)
        if not furthest:
            result["release_notes"] = "No availability found in next 90 days"
            return result

        result["release_days_ahead"] = days_ahead(furthest)

        # Common Resy release times
        result["release_time_est"] = "unknown"
        result["release_notes"] = f"Furthest available: {furthest}"
    except httpx.HTTPStatusError as e:
        result["error"] = f"HTTP {e.response.status_code}"
    except Exception as e:
        result["error"] = str(e)[:120]
    return result


# ---------------------------------------------------------------------------
# OpenTable scraper
# ---------------------------------------------------------------------------

OT_GRAPHQL = "https://www.opentable.com/dapi/fe/gql"

OT_HEADERS = {
    **BROWSER_HEADERS,
    "Content-Type": "application/json",
    "Referer": "https://www.opentable.com/",
    "Origin": "https://www.opentable.com",
    "x-csrf-token": "",
}


def _ot_restaurant_id(source_url: str) -> Optional[str]:
    """Extract OpenTable restaurant ID from a URL like /r/carbone-new-york or ?rid=12345."""
    import re
    m = re.search(r"rid=(\d+)", source_url)
    if m:
        return m.group(1)
    # Slug-based: hit the page and find the rid
    try:
        with httpx.Client(headers=BROWSER_HEADERS, timeout=15, follow_redirects=True) as c:
            r = c.get(source_url)
            m2 = re.search(r'"restaurantId":(\d+)', r.text)
            if m2:
                return m2.group(1)
            m3 = re.search(r'"rid":(\d+)', r.text)
            if m3:
                return m3.group(1)
    except Exception as e:
        logger.debug("_ot_restaurant_id failed: %s", e)
    return None


def scrape_opentable(source_url: str) -> dict:
    """
    Query OpenTable availability API for the furthest available date.
    """
    result = {
        "release_days_ahead": None,
        "release_time_est": None,
        "release_notes": "",
        "error": "",
    }
    try:
        rid = _ot_restaurant_id(source_url)
        if not rid:
            result["error"] = "Could not determine restaurant ID"
            return result

        jitter(1.0, 2.5)
        today = date.today()
        # OpenTable availability endpoint
        url = "https://www.opentable.com/dapi/booking/availability/range"
        params = {
            "restaurantId": rid,
            "startDate": today.isoformat(),
            "endDate": (today + timedelta(days=90)).isoformat(),
            "partySize": 2,
            "covers": 2,
        }
        headers = {
            **BROWSER_HEADERS,
            "Referer": source_url,
            "x-requested-with": "XMLHttpRequest",
        }
        with httpx.Client(headers=headers, timeout=20, follow_redirects=True) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            data = r.json()

        # Response has a list of date objects
        available_dates = []
        for item in data.get("availability", []):
            if item.get("available") or item.get("timeSlots"):
                available_dates.append(item.get("date", item.get("dateString", "")))

        if not available_dates:
            result["release_notes"] = "No availability found in 90-day window"
            return result

        furthest = max(d for d in available_dates if d)
        result["release_days_ahead"] = days_ahead(furthest[:10])
        result["release_time_est"] = "unknown"
        result["release_notes"] = f"Furthest available: {furthest[:10]}"

    except httpx.HTTPStatusError as e:
        result["error"] = f"HTTP {e.response.status_code}"
    except Exception as e:
        result["error"] = str(e)[:120]
    return result


# ---------------------------------------------------------------------------
# Tock scraper
# ---------------------------------------------------------------------------

TOCK_API = "https://www.exploretock.com/api"


def scrape_tock(source_url: str) -> dict:
    """
    Query Tock availability for the furthest available date.
    """
    result = {
        "release_days_ahead": None,
        "release_time_est": None,
        "release_notes": "",
        "error": "",
    }
    try:
        import re
        # Extract slug from https://www.exploretock.com/someslug
        m = re.search(r"exploretock\.com/([^/?#]+)", source_url)
        if not m:
            result["error"] = "Could not extract Tock slug"
            return result
        slug = m.group(1)

        jitter(0.8, 2.0)
        today = date.today()
        end = today + timedelta(days=90)
        url = f"https://www.exploretock.com/api/experience/search/{slug}/availability"
        params = {
            "date": today.isoformat(),
            "endDate": end.isoformat(),
            "partySize": 2,
        }
        with httpx.Client(headers={**BROWSER_HEADERS, "Referer": source_url}, timeout=20) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            data = r.json()

        available_dates = []
        for item in data.get("availability", data.get("results", [])):
            d = item.get("date") or item.get("localDate") or item.get("startDate", "")
            if d and item.get("available", True):
                available_dates.append(str(d)[:10])

        if not available_dates:
            result["release_notes"] = "No availability found via Tock API"
            return result

        furthest = max(available_dates)
        result["release_days_ahead"] = days_ahead(furthest)
        result["release_time_est"] = "unknown"
        result["release_notes"] = f"Furthest available: {furthest}"

    except httpx.HTTPStatusError as e:
        result["error"] = f"HTTP {e.response.status_code}"
    except Exception as e:
        result["error"] = str(e)[:120]
    return result


# ---------------------------------------------------------------------------
# Claude-assisted fallback for unknown platforms
# ---------------------------------------------------------------------------

def scrape_generic(source_url: str) -> dict:
    """
    Fetch the booking page and ask Claude to infer the release schedule.
    """
    result = {
        "release_days_ahead": None,
        "release_time_est": None,
        "release_notes": "",
        "error": "",
    }
    try:
        jitter(1.0, 2.5)
        with httpx.Client(headers=BROWSER_HEADERS, timeout=20, follow_redirects=True) as client:
            r = client.get(source_url)
            r.raise_for_status()
            text = r.text[:6000]

        prompt = f"""You are analyzing a restaurant booking page to determine its reservation release schedule.

Page URL: {source_url}
Page content (truncated):
{text}

Please answer:
1. What booking platform does this restaurant use? (Resy / OpenTable / Tock / Phone / Email / Walk-in / Other)
2. How many days in advance are reservations released? (give a number, or "unknown")
3. What time of day do new reservations appear? (EST, or "unknown")
4. Any important notes (e.g., "email list only", "phone only", "walk-in only")

Respond in this exact JSON format:
{{"platform": "...", "days_ahead": <number or null>, "release_time": "...", "notes": "..."}}"""

        response = claude_infer(prompt)
        if response:
            import json
            try:
                parsed = json.loads(response)
                result["release_days_ahead"] = parsed.get("days_ahead")
                result["release_time_est"] = parsed.get("release_time", "unknown")
                result["release_notes"] = parsed.get("notes", "")
            except json.JSONDecodeError:
                result["release_notes"] = f"Claude response: {response[:200]}"
    except httpx.HTTPStatusError as e:
        result["error"] = f"HTTP {e.response.status_code}"
    except Exception as e:
        result["error"] = str(e)[:120]
    return result


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def scrape_restaurant(booking_platform: str, source_url: str) -> dict:
    """
    Route to the correct scraper based on platform.
    Returns standardised result dict.
    """
    platform = booking_platform.lower().strip()
    logger.info("Scraping %s via %s", source_url, platform)

    if "resy" in platform or "resy.com" in source_url:
        return scrape_resy(source_url)
    elif "opentable" in platform or "opentable.com" in source_url:
        return scrape_opentable(source_url)
    elif "tock" in platform or "exploretock.com" in source_url:
        return scrape_tock(source_url)
    elif platform in ("phone", "walk-in", "walkin", "email"):
        return {
            "release_days_ahead": None,
            "release_time_est": None,
            "release_notes": f"Reservations via {booking_platform} — manual verification required",
            "error": "",
        }
    else:
        return scrape_generic(source_url)
