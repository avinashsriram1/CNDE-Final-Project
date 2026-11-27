"""Find the newest raw file of each source and its ingestion run (for the ingestion_run table).

Raw layout: <raw_root>/YYYY-MM-DD/<source>/<file> and <raw_root>/YYYY-MM-DD/_manifest/<run_id>.json.
A weekly run may contain only stations, so each source is resolved on its own: the newest
dated folder that has that source wins.
"""

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

# source name -> (file pattern in its folder, position used in run ids)
SOURCES = {
    "afdc_stations": ("stations.json*", 1),
    "eia_prices": ("retail_sales.*", 2),
    "afdc_registrations": ("registrations.csv", 3),
}
DATE_DIR = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def date_dirs(raw_root):
    """Dated run folders, newest first."""
    root = Path(raw_root)
    return sorted(
        (p for p in root.iterdir() if p.is_dir() and DATE_DIR.match(p.name)), reverse=True
    )


def latest_file(raw_root, source):
    """Return (path, snapshot_date) of the newest file for a source."""
    pattern, _ = SOURCES[source]
    for day in date_dirs(raw_root):
        matches = sorted((day / source).glob(pattern))
        if matches:
            return matches[0], day.name
    raise FileNotFoundError(f"No {source} file under {raw_root}")


def run_key(run_id, source):
    """Stable BIGINT id per source and run: 20261124T231504Z + stations -> 202611242315041."""
    return int(re.sub(r"\D", "", run_id) + str(SOURCES[source][1]))


def ingestion_run_row(raw_root, source, snapshot_date):
    """Build the ingestion_run row for a source from its run manifest, or None if not found."""
    manifest_dir = Path(raw_root) / snapshot_date / "_manifest"
    for path in sorted(manifest_dir.glob("*.json"), reverse=True):  # newest run first
        manifest = json.loads(path.read_text())
        results = manifest.get("results", [])
        for i, result in enumerate(results):
            if result.get("source") != source or result.get("status") != "success":
                continue
            main = next(
                (f for f in result.get("files", []) if Path(f).match(SOURCES[source][0])), ""
            )
            file_hash = next(
                (f["sha256"] for f in manifest.get("files", []) if f.get("uri") == main), None
            )
            started = result.get("started_at")
            finished = result.get("finished_at")
            if not started:  # older manifests: sources ran one after another from the run start
                start = datetime.strptime(manifest["run_id"], "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
                offset = sum(r.get("seconds", 0) for r in results[:i])
                begin = start + timedelta(seconds=offset)
                started = begin.isoformat()
                finished = (begin + timedelta(seconds=result.get("seconds", 0))).isoformat()
            return {
                "run_id": run_key(manifest["run_id"], source),
                "source": source,
                "snapshot_date": snapshot_date,
                "file_uri": main,
                "file_hash": file_hash,
                "row_count": result.get("rows"),
                "started_at": started,
                "finished_at": finished,
                "status": "success",
            }
    return None
