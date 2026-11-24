"""Source 3: AFDC Vehicle Registration Counts by State (web scrape).

The page has no download file; each year's table is plain HTML at ?year=YYYY.
The raw HTML is saved unchanged. A combined CSV is also saved for convenience;
cleaning (commas, US total row, state codes) happens later, not here.
"""

import io
import logging
import time
from datetime import date

import pandas as pd

from Scripts.ingestion import config
from Scripts.ingestion.http_client import get_with_retry

log = logging.getLogger(__name__)
SOURCE = "afdc_registrations"


def parse_year(html, year):
    """Read the year's HTML table into a DataFrame and check it has a State column."""
    tables = pd.read_html(io.StringIO(html))
    if not tables or "State" not in tables[0].columns:
        raise ValueError(f"Unexpected page layout for {year}")
    df = tables[0]
    df.insert(0, "year", year)
    return df


def run(store, day, last_year=None, sleep=time.sleep):
    last_year = last_year or date.today().year - 1
    frames, files, skipped = [], [], []
    for year in range(config.REGISTRATIONS_FIRST_YEAR, last_year + 1):
        try:
            html = get_with_retry(config.REGISTRATIONS_URL, {"year": year}).text
            files.append(
                store.write_text(store.key(day, SOURCE, f"{year}.html"), html, "text/html")
            )
            frames.append(parse_year(html, year))
        except Exception as error:  # one bad year should not stop the others
            log.error("Registrations %d skipped: %s", year, error)
            skipped.append(year)
        sleep(config.SCRAPE_DELAY_SECONDS)
    if not frames:
        raise RuntimeError("No registration years could be scraped")
    df = pd.concat(frames, ignore_index=True)
    if len(df) < config.REGISTRATIONS_MIN_ROWS:
        raise ValueError(f"Only {len(df)} registration rows; expected more")
    files.append(store.write_csv(store.key(day, SOURCE, "registrations.csv"), df))
    return {"source": SOURCE, "rows": len(df), "files": files, "skipped_years": skipped}
