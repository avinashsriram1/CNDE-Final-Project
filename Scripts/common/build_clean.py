"""Build the clean tables from one ingestion run and save them as CSV files.

Usage (from the repo root), pointing at a downloaded raw run folder:
    python -m Scripts.common.build_clean --raw-dir raw/2026-11-24 --out-dir clean/2026-11-24

Or with individual files (for example the earlier Drive snapshot):
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

from Scripts.common import cleaning


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


def main(argv=None):
    parser = argparse.ArgumentParser(description="Raw files -> clean tables (CSV).")
    parser.add_argument("--raw-dir", help="Folder of one run: <dir>/<source>/<files>")
    parser.add_argument("--stations", help="stations .json or .json.gz")
    parser.add_argument("--prices", help="EIA prices .json.gz or .csv")
    parser.add_argument("--registrations", help="registrations .csv")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)

    if args.raw_dir:
        args.stations = args.stations or find_one(f"{args.raw_dir}/afdc_stations", "stations.json*")
        args.prices = args.prices or find_one(f"{args.raw_dir}/eia_prices", "retail_sales.*")
        args.registrations = args.registrations or find_one(
            f"{args.raw_dir}/afdc_registrations", "registrations.csv"
        )
    if not (args.stations and args.prices and args.registrations):
        parser.error("Give --raw-dir, or all of --stations, --prices, --registrations")

    log = cleaning.ExclusionLog()
    tables = cleaning.lookup_tables()

    print("Cleaning stations ...")
    raw_stations = read_json(args.stations)
    records = raw_stations["fuel_stations"] if isinstance(raw_stations, dict) else raw_stations
    tables.update(cleaning.clean_stations(records, log))

    print("Cleaning registrations ...")
    tables["vehicle_registration"] = cleaning.clean_registrations(
        pd.read_csv(args.registrations), log
    )

    print("Cleaning prices ...")
    prices_path = Path(args.prices)
    raw_prices = (
        pd.read_csv(prices_path)
        if prices_path.suffix == ".csv"
        else pd.DataFrame(read_json(prices_path))
    )
    tables["electricity_price"] = cleaning.clean_prices(raw_prices, log)

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
