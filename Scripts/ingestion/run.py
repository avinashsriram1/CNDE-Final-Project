"""Run the ingestion pipeline.

Usage (from the repo root):
    python -m Scripts.ingestion.run                         # all three sources
    python -m Scripts.ingestion.run --sources eia_prices    # one source

Each run writes a manifest (rows, files, status, seconds per source) to
raw/YYYY-MM-DD/_manifest/<run_id>.json and exits with code 1 if any source failed.
"""

import argparse
import json
import logging
import sys
import time
from datetime import UTC, datetime

from Scripts.ingestion import prices, registrations, stations
from Scripts.ingestion.storage import RawStore, run_date

SOURCES = {
    stations.SOURCE: stations.run,
    prices.SOURCE: prices.run,
    registrations.SOURCE: registrations.run,
}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Download raw data to the GCS raw zone.")
    parser.add_argument("--sources", nargs="+", choices=list(SOURCES), default=list(SOURCES))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("ingestion")

    store = RawStore()
    day = run_date()
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    log.info("Run %s (%s): %s", run_id, day, args.sources)

    results = []
    for name in args.sources:
        start = time.time()
        try:
            result = SOURCES[name](store, day)
            result["status"] = "success"
        except Exception as error:  # record the failure and continue with the next source
            log.error("%s FAILED: %s", name, error)
            result = {"source": name, "status": "failed", "error": str(error)}
        result["seconds"] = round(time.time() - start, 1)
        results.append(result)

    manifest = {"run_id": run_id, "run_date": day, "results": results, "files": store.written}
    store.write_text(
        store.key(day, "_manifest", f"{run_id}.json"),
        json.dumps(manifest, indent=2),
        "application/json",
    )
    for r in results:
        log.info("%-20s %-8s rows=%s", r["source"], r["status"], r.get("rows", "-"))
    return 0 if all(r["status"] == "success" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
