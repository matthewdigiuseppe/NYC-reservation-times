# NYC Reservation Times

A continuously updated database of NYC restaurant reservation release schedules — tracking which restaurants use which booking platforms, how far in advance reservations are released, and at what time of day slots appear.

**Live app:** Deploy to Render with one click using `render.yaml`.

---

## What it tracks

| Column | Description |
|--------|-------------|
| `restaurant_name` | Full name of the restaurant |
| `neighborhood` | NYC neighborhood |
| `cuisine` | Cuisine type |
| `booking_platform` | Resy / OpenTable / Tock / Phone / Walk-in / Other |
| `release_days_ahead` | How many days in advance reservations are released |
| `release_time_est` | Time of day slots appear (EST) |
| `release_notes` | Platform quirks, walk-in notes, email-list caveats |
| `last_verified` | ISO date when this row was last checked |
| `source_url` | Direct link to the booking page |

---

## Quick start (local)

```bash
# 1. Clone and enter repo
git clone <repo-url>
cd NYC-reservation-times

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables
cp .env.example .env
# Edit .env and fill in your ANTHROPIC_API_KEY and UPDATE_API_KEY

# 4. (Optional) Re-generate seed data from scratch
python scripts/generate_seed_csv.py

# 5. Start the web app
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Visit http://localhost:8000
```

---

## Project structure

```
NYC-reservation-times/
├── app/
│   └── main.py              # FastAPI application
├── data/
│   ├── restaurants.csv      # Main database
│   └── manual_review.csv    # Restaurants needing manual verification
├── logs/
│   └── update.log           # Update run logs
├── scripts/
│   ├── scrapers.py          # Resy / OpenTable / Tock / Claude-assisted scrapers
│   ├── seed.py              # Live-scrape seed script (runs on Render)
│   ├── generate_seed_csv.py # Research-based seed (no network required)
│   └── update.py            # Weekly update runner
├── templates/
│   └── index.html           # Jinja2 HTML template
├── .env.example             # Environment variable template
├── render.yaml              # Render deployment config
└── requirements.txt
```

---

## Web app endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Searchable/filterable HTML table |
| `GET` | `/data` | Full dataset as JSON (supports `?neighborhood=`, `?cuisine=`, `?platform=`) |
| `GET` | `/data/manual` | Restaurants in manual review queue as JSON |
| `GET` | `/health` | Health check — returns restaurant count and last update date |
| `POST` | `/update` | Trigger `scripts/update.py` manually (requires `UPDATE_API_KEY`) |

### Filtering examples

```
GET /?platform=Resy&neighborhood=West Village
GET /data?platform=Tock
GET /data?cuisine=Japanese+Omakase
```

### Triggering a manual update

```bash
curl -X POST https://your-app.onrender.com/update \
  -H "Authorization: Bearer YOUR_UPDATE_API_KEY"
```

---

## Scraper architecture

`scripts/scrapers.py` provides platform-specific scrapers:

- **Resy** — Queries `api.resy.com/4/venue/calendar` with public API key; finds furthest available date in 90-day window
- **OpenTable** — Queries OpenTable's availability range API; extracts furthest available date
- **Tock** — Queries `exploretock.com/api/experience/search/{slug}/availability`
- **Claude fallback** — For unknown platforms, fetches the booking page and asks Claude to infer release schedule from page content
- **Phone / Walk-in / Email** — Flagged to `manual_review.csv` automatically; never scraped

The scraper uses realistic browser headers and randomized delays (1.5–4s) between requests to avoid bot detection.

---

## Deploying to Render

### Step 1: Create a Render account

Sign up at [render.com](https://render.com).

### Step 2: Connect your GitHub repository

In the Render dashboard, click **New > Blueprint** and select this repository. Render will read `render.yaml` and create:
- A **web service** running the FastAPI app
- A **cron job** that runs `scripts/update.py` every Sunday at 3am EST (8am UTC)

### Step 3: Set environment variables

In the Render dashboard, set these environment variables for both services:

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key from [console.anthropic.com](https://console.anthropic.com) |
| `UPDATE_API_KEY` | A secret string to protect the `/update` endpoint |

### Step 4: Deploy

Click **Apply** in the Render dashboard. The first deploy will install dependencies and start the web server. The cron job will run on its schedule.

---

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes (for live scraping) | Used by Claude-assisted fallback scraper for ambiguous booking pages |
| `UPDATE_API_KEY` | Yes | Protects the `POST /update` endpoint from unauthorized access |

Set these in a `.env` file locally (see `.env.example`), or in the Render dashboard for production.

---

## Data files

### `data/restaurants.csv`

The main database. Updated weekly by the cron job. Contains 89+ of the most competitive NYC restaurants.

### `data/manual_review.csv`

Restaurants where the release schedule cannot be automatically determined. Includes:
- Phone-only restaurants (Rao's)
- Walk-in only (Lucali)
- Email-list only restaurants
- Any restaurant where live scraping fails

---

## Running the update script manually

```bash
# Update all restaurants (requires network access to booking platforms)
python scripts/update.py

# View the update log
cat logs/update.log
```

---

## Development notes

### Resy bot detection

Resy has active bot detection. The scraper uses:
- Realistic Chrome browser User-Agent headers
- `X-Origin`, `Referer`, and `Origin` headers matching resy.com
- Public Resy API key (same key used by the Resy web app)
- Randomized delays between requests

If Resy blocks requests, increase delays in `scrapers.py` or add restaurant data manually to `restaurants.csv`.

### Adding a new restaurant

Add a row to `data/restaurants.csv` with the correct booking platform and source URL. On the next weekly update run, the scraper will attempt to fill in `release_days_ahead` and `release_time_est`.

### Claude-assisted parsing

When `ANTHROPIC_API_KEY` is set and a restaurant uses an unknown platform, the scraper fetches the booking page and asks Claude to extract release schedule information. This is used as a fallback for restaurants that don't use Resy/OpenTable/Tock.

---

## License

MIT
