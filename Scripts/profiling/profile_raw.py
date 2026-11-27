"""Profile the raw sources and write a Markdown report (Category 2: profiling).

For each source: row and column counts, a schema table (type, % empty, distinct values,
example), a sparsity audit (columns 99%+ empty), and duplicate-key checks.

Usage (from the repo root), same inputs as build_clean:
    python -m Scripts.profiling.profile_raw --raw-root raw --out Docs/profiling_report.md
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

from Scripts.common import lineage
from Scripts.common.build_clean import read_json

SPARSE_THRESHOLD = 99.0  # percent empty


def schema_table(df):
    rows = []
    for col in df.columns:
        series = df[col]
        hashable = series.map(lambda v: str(v) if isinstance(v, (list, dict)) else v)
        non_null = hashable.dropna()
        rows.append(
            {
                "column": col,
                "type": str(series.dtype),
                "% empty": round(series.isna().mean() * 100, 1),
                "distinct": int(non_null.nunique()),
                "example": str(non_null.iloc[0])[:40] if len(non_null) else "",
            }
        )
    return pd.DataFrame(rows)


def to_md(df):
    """Small Markdown table writer (avoids an extra dependency)."""
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, row in df.iterrows():
        cells = [str(row[c]).replace("|", "/").replace("\n", " ") for c in cols]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def profile_source(name, df, key):
    schema = schema_table(df)
    sparse = schema[schema["% empty"] >= SPARSE_THRESHOLD]["column"].tolist()
    dupes = int(df.duplicated(key).sum())
    parts = [
        f"## {name}",
        f"- Rows: **{len(df):,}**  ·  Columns: **{df.shape[1]}**",
        f"- Key {key}: **{dupes}** duplicate rows",
        f"- Sparse columns (>= {SPARSE_THRESHOLD:.0f}% empty): {len(sparse)}"
        + (f" ({', '.join(sparse)})" if sparse else ""),
        "",
        to_md(schema),
        "",
    ]
    return "\n".join(parts)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Profile raw sources into a Markdown report.")
    parser.add_argument(
        "--raw-root", help="The raw/ folder; the newest file of each source is used"
    )
    parser.add_argument("--stations")
    parser.add_argument("--prices")
    parser.add_argument("--registrations")
    parser.add_argument("--out", default="Docs/profiling_report.md")
    args = parser.parse_args(argv)
    if args.raw_root:
        args.stations = args.stations or lineage.latest_file(args.raw_root, "afdc_stations")[0]
        args.prices = args.prices or lineage.latest_file(args.raw_root, "eia_prices")[0]
        args.registrations = (
            args.registrations or lineage.latest_file(args.raw_root, "afdc_registrations")[0]
        )

    raw = read_json(args.stations)
    stations = pd.DataFrame(raw["fuel_stations"] if isinstance(raw, dict) else raw)
    prices_path = Path(args.prices)
    prices = (
        pd.read_csv(prices_path)
        if prices_path.suffix == ".csv"
        else pd.DataFrame(read_json(prices_path))
    )
    registrations = pd.read_csv(args.registrations)

    report = [
        "# Raw Data Profiling Report",
        f"Generated {date.today().isoformat()} by `Scripts/profiling/profile_raw.py`. "
        "Raw files are profiled as they arrived, before any cleaning.",
        "",
        profile_source("Charging stations (NREL/NLR API)", stations, ["id"]),
        profile_source("Electricity prices (EIA API)", prices, ["period", "stateid", "sectorid"]),
        profile_source("EV registrations (AFDC web tables)", registrations, ["year", "State"]),
    ]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(report), encoding="utf-8")
    print(f"Saved {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
