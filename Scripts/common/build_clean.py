"""Build the clean tables from the raw zone and save them as CSV files.

Usage (from the repo root):
    # Whole raw folder (recommended): the newest file of each source is used,
    # and loaded_run_id / ingestion_run come from the run manifests.
    python -m Scripts.common.build_clean --raw-root raw --out-dir clean_out

    # Or individual files (no manifest, so loaded_run_id stays empty):
    python -m Scripts.common.build_clean --stations stations.json --prices prices.csv \
        --registrations registrations.csv --out-dir clean/test

Outputs: one CSV per table in the OLTP EER diagram, plus exclusion_log.csv.
"""

import argparse
import gzip
import json
import sys
from pathlib import Path

import pandas as pd

from Scripts.common import cleaning, lineage


def read_json(path):
    path = Path(path)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def find_one(folder, pattern):
    matches = sorted(Path(folder).glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No file matching {pattern} in {folder}")
    return matches[0]


def resolve_inputs(args):
    """Return {source: (path, ingestion_run row or None)} for the three sources."""
    given = {
        "afdc_stations": args.stations,
        "eia_prices": args.prices,
        "afdc_registrations": args.registrations,
    }
    inputs = {}
    for source in lineage.SOURCES:
        if given[source]:
            inputs[source] = (Path(given[source]), None)
        elif args.raw_root:
            path, day = lineage.latest_file(args.raw_root, source)
            inputs[source] = (path, lineage.ingestion_run_row(args.raw_root, source, day))
        else:
            raise SystemExit("Give --raw-root, or all of --stations, --prices, --registrations")
    return inputs


def read_prices(path):
    path = Path(path)
    return pd.read_csv(path) if path.suffix == ".csv" else pd.DataFrame(read_json(path))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Raw files -> clean tables (CSV).")
    parser.add_argument("--raw-root", help="The raw/ folder: <root>/YYYY-MM-DD/<source>/<files>")
    parser.add_argument("--stations", help="stations .json or .json.gz")
    parser.add_argument("--prices", help="EIA prices .json.gz or .csv")
    parser.add_argument("--registrations", help="registrations .csv")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)

    inputs = resolve_inputs(args)
    runs = {s: row for s, (_, row) in inputs.items() if row}
    run_id = {s: (row["run_id"] if row else None) for s, (_, row) in inputs.items()}
    for source, (path, _row) in inputs.items():
        print(f"{source:20s} {path}  (run {run_id[source] or 'not recorded'})")

    log = cleaning.ExclusionLog()
    tables = cleaning.lookup_tables()
    if runs:
        tables["ingestion_run"] = pd.DataFrame(runs.values())

    print("\nCleaning stations ...")
    raw = read_json(inputs["afdc_stations"][0])
    records = raw["fuel_stations"] if isinstance(raw, dict) else raw
    tables.update(cleaning.clean_stations(records, log, run_id["afdc_stations"]))

    print("Cleaning registrations ...")
    tables["vehicle_registration"] = cleaning.clean_registrations(
        pd.read_csv(inputs["afdc_registrations"][0]), log, run_id["afdc_registrations"]
    )

    print("Cleaning prices ...")
    tables["electricity_price"] = cleaning.clean_prices(
        read_prices(inputs["eia_prices"][0]), log, run_id["eia_prices"]
    )

    cleaning.check_keys(tables)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(out / f"{name}.csv", index=False)
    log.to_frame().to_csv(out / "exclusion_log.csv", index=False)

    print(f"\nSaved to {out}/")
    for name, df in tables.items():
        print(f"  {name:22s} {len(df):>8,} rows")
    print("\nRows excluded:")
    print(log.to_frame().to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
