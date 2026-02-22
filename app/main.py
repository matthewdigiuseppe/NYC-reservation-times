"""
NYC Restaurant Reservation Times — FastAPI web application.

Serves a searchable/filterable HTML table of NYC restaurant reservation
release schedules, plus a JSON API and a manually-triggered update endpoint.
"""

import os
import csv
import subprocess
import logging
from pathlib import Path
from datetime import date
from typing import Optional

from fastapi import FastAPI, Query, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("uvicorn.error")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RESTAURANTS_CSV = DATA_DIR / "restaurants.csv"
MANUAL_CSV = DATA_DIR / "manual_review.csv"
TEMPLATES_DIR = BASE_DIR / "templates"

app = FastAPI(
    title="NYC Reservation Times",
    description="When do NYC restaurants release reservations?",
    version="1.0.0",
)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def load_restaurants() -> list[dict]:
    """Read restaurants.csv and return a list of dicts."""
    if not RESTAURANTS_CSV.exists():
        return []
    with open(RESTAURANTS_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def last_updated() -> str:
    """Return the most recent last_verified date from the CSV."""
    rows = load_restaurants()
    dates = [r.get("last_verified", "") for r in rows if r.get("last_verified")]
    return max(dates) if dates else "unknown"


def unique_values(rows: list[dict], key: str) -> list[str]:
    """Return sorted unique non-empty values for a CSV column."""
    return sorted({r[key] for r in rows if r.get(key)})


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    neighborhood: Optional[str] = Query(None),
    cuisine: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    q: Optional[str] = Query(None, description="Free-text search"),
):
    rows = load_restaurants()

    # Collect filter options before filtering
    neighborhoods = unique_values(rows, "neighborhood")
    cuisines = unique_values(rows, "cuisine")
    platforms = unique_values(rows, "booking_platform")

    # Apply filters
    if neighborhood:
        rows = [r for r in rows if r.get("neighborhood", "").lower() == neighborhood.lower()]
    if cuisine:
        rows = [r for r in rows if r.get("cuisine", "").lower() == cuisine.lower()]
    if platform:
        rows = [r for r in rows if r.get("booking_platform", "").lower() == platform.lower()]
    if q:
        q_lower = q.lower()
        rows = [
            r for r in rows
            if q_lower in r.get("restaurant_name", "").lower()
            or q_lower in r.get("neighborhood", "").lower()
            or q_lower in r.get("cuisine", "").lower()
            or q_lower in r.get("release_notes", "").lower()
        ]

    # Sort: known release_days_ahead first (ascending), then unknown
    def sort_key(r):
        try:
            return (0, int(r.get("release_days_ahead") or 9999))
        except (ValueError, TypeError):
            return (1, 9999)

    rows.sort(key=sort_key)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "rows": rows,
            "total": len(rows),
            "last_updated": last_updated(),
            "neighborhoods": neighborhoods,
            "cuisines": cuisines,
            "platforms": platforms,
            "filter_neighborhood": neighborhood or "",
            "filter_cuisine": cuisine or "",
            "filter_platform": platform or "",
            "filter_q": q or "",
        },
    )


@app.get("/data", response_class=JSONResponse)
async def get_data(
    neighborhood: Optional[str] = Query(None),
    cuisine: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
):
    """Return the full restaurant dataset as JSON."""
    rows = load_restaurants()
    if neighborhood:
        rows = [r for r in rows if r.get("neighborhood", "").lower() == neighborhood.lower()]
    if cuisine:
        rows = [r for r in rows if r.get("cuisine", "").lower() == cuisine.lower()]
    if platform:
        rows = [r for r in rows if r.get("booking_platform", "").lower() == platform.lower()]

    return {
        "count": len(rows),
        "last_updated": last_updated(),
        "restaurants": rows,
    }


@app.get("/data/manual", response_class=JSONResponse)
async def get_manual_review():
    """Return restaurants requiring manual review."""
    if not MANUAL_CSV.exists():
        return {"count": 0, "restaurants": []}
    with open(MANUAL_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {"count": len(rows), "restaurants": rows}


def _verify_update_key(request: Request):
    """Validate the UPDATE_API_KEY from header or query param."""
    expected = os.environ.get("UPDATE_API_KEY", "")
    if not expected:
        raise HTTPException(status_code=503, detail="UPDATE_API_KEY not configured on server.")

    # Accept key via Authorization bearer or ?api_key= query param
    auth_header = request.headers.get("Authorization", "")
    query_key = request.query_params.get("api_key", "")

    provided = ""
    if auth_header.lower().startswith("bearer "):
        provided = auth_header[7:].strip()
    elif query_key:
        provided = query_key

    if provided != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing UPDATE_API_KEY.")


@app.post("/update")
async def trigger_update(request: Request, _=Depends(_verify_update_key)):
    """
    Trigger scripts/update.py manually.
    Protected by UPDATE_API_KEY environment variable.

    Authenticate via:
      Authorization: Bearer <UPDATE_API_KEY>
    or:
      POST /update?api_key=<UPDATE_API_KEY>
    """
    script = BASE_DIR / "scripts" / "update.py"
    if not script.exists():
        raise HTTPException(status_code=500, detail="update.py not found.")

    try:
        result = subprocess.run(
            ["python", str(script)],
            capture_output=True,
            text=True,
            timeout=600,  # 10-minute timeout
        )
        return {
            "status": "completed" if result.returncode == 0 else "error",
            "returncode": result.returncode,
            "stdout": result.stdout[-3000:] if result.stdout else "",
            "stderr": result.stderr[-2000:] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Update script timed out.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Simple health check."""
    rows = load_restaurants()
    return {
        "status": "ok",
        "restaurant_count": len(rows),
        "last_updated": last_updated(),
        "csv_exists": RESTAURANTS_CSV.exists(),
    }
