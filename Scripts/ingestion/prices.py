"""Source 2: EIA API v2, electricity retail sales (average price by state and month)."""

import logging

from Scripts.ingestion import config
from Scripts.ingestion.http_client import get_with_retry, require_env

log = logging.getLogger(__name__)
SOURCE = "eia_prices"


def fetch_all(getter=get_with_retry):
    """Page through the API (5,000 rows per request) until every row is downloaded."""
    key = require_env("EIA_API_KEY")
    rows, offset = [], 0
    while True:
        params = {
            "api_key": key,
            "frequency": "monthly",
            "data[0]": "price",
            "facets[sectorid][]": config.EIA_SECTORS,
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "offset": offset,
            "length": config.EIA_PAGE_SIZE,
        }
        response = getter(config.EIA_BASE_URL, params).json()["response"]
        batch, total = response["data"], int(response["total"])
        rows.extend(batch)
        log.info("EIA offset=%d: %d rows (%d/%d)", offset, len(batch), len(rows), total)
        offset += config.EIA_PAGE_SIZE
        if not batch or len(rows) >= total:
            break
    if len(rows) != total:
        raise ValueError(f"EIA row count mismatch: got {len(rows)}, API reported {total}")
    return rows


def run(store, day):
    rows = fetch_all()
    if len(rows) < config.PRICES_MIN_ROWS:
        raise ValueError(f"Only {len(rows)} EIA rows; expected {config.PRICES_MIN_ROWS}+")
    path = store.write_json_gz(store.key(day, SOURCE, "retail_sales.json.gz"), rows)
    return {"source": SOURCE, "rows": len(rows), "files": [path]}
