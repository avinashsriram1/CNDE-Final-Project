"""Source 1: NREL/NLR Alternative Fuel Stations API (EV charging stations)."""

import logging

from Scripts.ingestion import config
from Scripts.ingestion.http_client import get_with_retry, require_env

log = logging.getLogger(__name__)
SOURCE = "afdc_stations"


def remove_pii(stations, fields=config.STATIONS_PII_FIELDS):
    """Drop personal fields (phone numbers) from every record before saving."""
    return [{k: v for k, v in s.items() if k not in fields} for s in stations]


def fetch():
    """Return the full API response, trying the new domain first, then the old one."""
    params = {**config.STATIONS_PARAMS, "api_key": require_env("NREL_API_KEY")}
    last_error = None
    for url in config.NREL_BASE_URLS:
        try:
            log.info("Requesting %s", url)
            return get_with_retry(url, params).json()
        except Exception as error:  # try the fallback domain
            last_error = error
            log.warning("Endpoint failed, trying next: %s", error)
    raise RuntimeError(f"All stations endpoints failed: {last_error}")


def run(store, day):
    data = fetch()
    stations = remove_pii(data.get("fuel_stations", []))
    if len(stations) < config.STATIONS_MIN_ROWS:
        raise ValueError(f"Only {len(stations)} stations; expected {config.STATIONS_MIN_ROWS}+")
    data["fuel_stations"] = stations
    path = store.write_json_gz(store.key(day, SOURCE, "stations.json.gz"), data)
    return {"source": SOURCE, "rows": len(stations), "files": [path]}
