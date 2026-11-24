"""Ingestion settings in one place.

Every value can be overridden by an environment variable (see Docker/.env.example),
so URLs and limits are never hard-coded in the source modules.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / "Docker" / ".env")  # local runs; GitHub Actions uses Secrets

TIMEZONE = "America/Chicago"

# Storage: GCS when GCS_BUCKET is set, otherwise a local folder (ignored by git).
GCS_BUCKET = os.getenv("GCS_BUCKET", "")
GCS_RAW_PREFIX = os.getenv("GCS_RAW_PREFIX", "raw")
LOCAL_OUT_DIR = Path(os.getenv("LOCAL_OUT_DIR", REPO_ROOT / "data"))

# HTTP behavior
TIMEOUT_SECONDS = 120
MAX_RETRIES = 4
BACKOFF_SECONDS = 5  # waits 5, 10, 20 seconds between attempts

# Source 1: NREL/NLR Alternative Fuel Stations API. The lab was renamed NREL -> NLR,
# so the old domain is kept as a fallback.
NREL_BASE_URLS = [
    os.getenv("NREL_BASE_URL") or "https://developer.nlr.gov/api/alt-fuel-stations/v1.json",
    "https://developer.nrel.gov/api/alt-fuel-stations/v1.json",
]
STATIONS_PARAMS = {"fuel_type": "ELEC", "status": "all", "country": "US", "limit": "all"}
STATIONS_PII_FIELDS = ["station_phone"]  # removed before anything is saved (GOV-01)
STATIONS_MIN_ROWS = 50_000

# Source 2: EIA API v2, electricity retail sales (price by state and month)
EIA_BASE_URL = os.getenv("EIA_BASE_URL") or "https://api.eia.gov/v2/electricity/retail-sales/data/"
EIA_PAGE_SIZE = 5_000  # API maximum per request
EIA_SECTORS = ["RES"]  # residential; add "COM" for the commercial stretch goal
PRICES_MIN_ROWS = 15_000

# Source 3: AFDC vehicle registration counts (HTML tables, one page per year).
# afdc.energy.gov/robots.txt has no Disallow rules (checked 2026-11-20).
REGISTRATIONS_URL = "https://afdc.energy.gov/vehicle-registration"
REGISTRATIONS_FIRST_YEAR = 2016
REGISTRATIONS_MIN_ROWS = 400
SCRAPE_DELAY_SECONDS = 1  # be polite: one page per second
