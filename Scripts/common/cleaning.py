"""Cleaning rules shared by Part B (PostgreSQL) and Part C (Databricks Silver).

Each function takes raw data and returns clean DataFrames that match the OLTP EER diagram.
Raw inputs are never modified. Every row that is removed is counted in the ExclusionLog.
"""

import pandas as pd

from Scripts.common import reference as ref

PORT_LEVELS = {code: col for code, (_, _, col) in ref.CHARGING_LEVELS.items()}


class ExclusionLog:
    """Counts every row removed by a cleaning rule, so nothing is dropped silently."""

    def __init__(self):
        self.rows = []

    def add(self, table, rule, count):
        self.rows.append({"table": table, "rule": rule, "rows_excluded": int(count)})

    def to_frame(self):
        return pd.DataFrame(self.rows, columns=["table", "rule", "rows_excluded"])


def pad_zip(value):
    """Restore leading zeros lost upstream, e.g. '5403' -> '05403'. Non-digits are kept as is."""
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text.zfill(5) if text.isdigit() and len(text) < 5 else text


# ---------- Stations ----------
STATION_COLUMNS = [
    "station_id", "station_name", "fuel_type_code", "status_code", "access_code",
    "owner_type_code", "network_id", "federal_agency_id", "state_code", "street_address",
    "city", "zip", "latitude", "longitude", "facility_type", "maximum_vehicle_class",
    "open_date", "expected_date", "date_last_confirmed", "updated_at", "unverified",
    "restricted_access", "ev_workplace_charging", "access_days_time", "ev_pricing",
    "loaded_run_id",
]  # fmt: skip


def clean_stations(records, log, run_id=None):
    """Return station, station_port, station_connector, station_relation, ev_network,
    federal_agency tables from the raw API records (list of dicts).

    run_id: the ingestion_run id these records came from (stored as loaded_run_id).
    """
    df = pd.DataFrame(records).drop(columns=ref.PII_FIELDS, errors="ignore")
    df["loaded_run_id"] = run_id
    df = df.rename(columns={"id": "station_id", "state": "state_code"})

    # Duplicates: keep the most recently confirmed record per station.
    before = len(df)
    df = df.sort_values(["date_last_confirmed", "updated_at"], na_position="first")
    df = df.drop_duplicates("station_id", keep="last")
    log.add("station", "duplicate station_id (kept latest confirmed)", before - len(df))

    # Only the 50 states + DC (removes PR and other territories).
    keep = df["state_code"].isin(ref.STATE_CODES.values())
    log.add("station", "state_code not in 50 states + DC", (~keep).sum())
    df = df[keep].copy()

    # expected_date is the opening date (P, planned) or reopening date (T, temporarily
    # unavailable). For available stations (E) it has no meaning: clear it and count it.
    stray = df["expected_date"].notna() & ~df["status_code"].isin(["P", "T"])
    log.add("station", "expected_date cleared for available (E) station", stray.sum())
    df.loc[stray, "expected_date"] = None

    df["zip"] = df["zip"].map(pad_zip)
    for col in ["open_date", "expected_date", "date_last_confirmed"]:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
    df["updated_at"] = pd.to_datetime(df["updated_at"], utc=True, errors="coerce")

    # Networks: lookup table with a surrogate key.
    networks = (
        df[["ev_network", "ev_network_web"]]
        .dropna(subset=["ev_network"])
        .drop_duplicates("ev_network")
        .sort_values("ev_network")
        .reset_index(drop=True)
    )
    networks.insert(0, "network_id", range(1, len(networks) + 1))
    networks = networks.rename(
        columns={"ev_network": "network_code", "ev_network_web": "network_web"}
    )
    df["network_id"] = df["ev_network"].map(
        dict(zip(networks.network_code, networks.network_id, strict=True))
    )

    # Federal agencies: nested object {id, code, name}.
    agencies = pd.DataFrame([a for a in df["federal_agency"].dropna() if isinstance(a, dict)])
    if agencies.empty:
        agencies = pd.DataFrame(columns=["agency_id", "agency_code", "agency_name"])
    else:
        agencies = agencies.drop_duplicates("id").rename(
            columns={"id": "agency_id", "code": "agency_code", "name": "agency_name"}
        )
    df["federal_agency_id"] = df["federal_agency"].map(
        lambda a: a.get("id") if isinstance(a, dict) else None
    )

    station = df[STATION_COLUMNS].reset_index(drop=True)
    station["network_id"] = station["network_id"].astype("Int64")
    station["federal_agency_id"] = station["federal_agency_id"].astype("Int64")
    station["loaded_run_id"] = station["loaded_run_id"].astype("Int64")

    # Ports: one row per station and level, only when the count is above 0.
    # An empty count in the source means the station has no ports of that level.
    ports = df[["station_id", *PORT_LEVELS.values()]].melt(
        id_vars="station_id", var_name="source_col", value_name="port_count"
    )
    ports["level_code"] = ports["source_col"].map({v: k for k, v in PORT_LEVELS.items()})
    ports = ports[ports["port_count"].fillna(0) > 0]
    station_port = (
        ports[["station_id", "level_code", "port_count"]]
        .astype({"port_count": int})
        .sort_values(["station_id", "level_code"])
        .reset_index(drop=True)
    )
    no_ports = ~df["station_id"].isin(station_port["station_id"])
    log.add("station_port", "station has no port counts (kept in station)", no_ports.sum())

    # Connectors: multi-valued list -> one row per station and connector.
    conn = df[["station_id", "ev_connector_types"]].explode("ev_connector_types").dropna()
    station_connector = (
        conn.rename(columns={"ev_connector_types": "connector_code"})
        .drop_duplicates()
        .sort_values(["station_id", "connector_code"])
        .reset_index(drop=True)
    )

    # Related stations: recursive M:N. Keep pairs whose both ends exist in station.
    pairs = [
        {"station_id": sid, "related_station_id": r.get("id")}
        for sid, rel in zip(df["station_id"], df["related_stations"], strict=True)
        if isinstance(rel, list)
        for r in rel
        if isinstance(r, dict) and r.get("id") != sid
    ]
    relation = pd.DataFrame(pairs, columns=["station_id", "related_station_id"]).drop_duplicates()
    valid = relation["related_station_id"].isin(station["station_id"])
    log.add("station_relation", "related station not in station table", (~valid).sum())
    station_relation = relation[valid].reset_index(drop=True)

    return {
        "station": station,
        "station_port": station_port,
        "station_connector": station_connector,
        "station_relation": station_relation,
        "ev_network": networks,
        "federal_agency": agencies[["agency_id", "agency_code", "agency_name"]],
    }


# ---------- Registrations ----------
def clean_registrations(wide, log, run_id=None):
    """Wide AFDC table (one column per fuel) -> long vehicle_registration table.

    Validation: the 51 state rows must add up exactly to the 'United States' row.
    """
    wide = wide.rename(columns=lambda c: str(c).strip())
    fuel_cols = [c for c in wide.columns if c in ref.FUEL_TYPES]
    missing = set(ref.FUEL_TYPES) - set(fuel_cols)
    if missing:
        raise ValueError(f"Registration columns missing: {sorted(missing)}")
    for col in fuel_cols:
        wide[col] = pd.to_numeric(wide[col].astype(str).str.replace(",", ""), errors="raise")

    total = wide[wide["State"] == ref.US_TOTAL_NAME].set_index("year")[fuel_cols]
    states = wide[wide["State"] != ref.US_TOTAL_NAME].copy()
    sums = states.groupby("year")[fuel_cols].sum()
    if not total.empty and not sums.loc[total.index].equals(total):
        raise ValueError("Validation failed: state rows do not add up to the United States total")
    log.add("vehicle_registration", "'United States' total row", len(wide) - len(states))

    states["state_code"] = states["State"].map(ref.STATE_CODES)
    unknown = states["state_code"].isna()
    log.add("vehicle_registration", "state name not in 50 states + DC", unknown.sum())
    states = states[~unknown]

    long = states.melt(id_vars=["state_code", "year"], value_vars=fuel_cols, var_name="fuel")
    long["fuel_type_id"] = long["fuel"].map(lambda f: ref.FUEL_TYPES[f][0])
    long["loaded_run_id"] = pd.array([run_id] * len(long), dtype="Int64")
    return (
        long.rename(columns={"value": "vehicle_count"})[
            ["state_code", "year", "fuel_type_id", "vehicle_count", "loaded_run_id"]
        ]
        .astype({"year": int, "fuel_type_id": int, "vehicle_count": int})
        .sort_values(["state_code", "year", "fuel_type_id"])
        .reset_index(drop=True)
    )


# ---------- Prices ----------
def clean_prices(raw, log, run_id=None):
    """EIA retail-sales rows -> electricity_price (51 states, one row per state, month, sector)."""
    df = raw.rename(
        columns={"stateid": "state_code", "sectorid": "sector_id", "price": "price_cents_kwh"}
    )
    non_state = df["state_code"].isin(ref.EIA_NON_STATE_CODES)
    log.add("electricity_price", "US total and EIA regional codes", non_state.sum())
    df = df[~non_state].copy()

    df["price_cents_kwh"] = pd.to_numeric(df["price_cents_kwh"], errors="coerce")
    missing = df["price_cents_kwh"].isna()
    log.add("electricity_price", "price is empty (flagged, not imputed)", missing.sum())
    df = df[~missing]
    bad = (df["price_cents_kwh"] <= 0) | (df["price_cents_kwh"] > 100)
    log.add("electricity_price", "price outside 0-100 cents/kWh", bad.sum())
    df = df[~bad]

    df["period_month"] = pd.to_datetime(df["period"], format="%Y-%m").dt.date
    df["loaded_run_id"] = pd.array([run_id] * len(df), dtype="Int64")
    out = df[["state_code", "period_month", "sector_id", "price_cents_kwh", "loaded_run_id"]]
    before = len(out)
    out = out.drop_duplicates(["state_code", "period_month", "sector_id"])
    log.add("electricity_price", "duplicate state + month + sector", before - len(out))
    return out.sort_values(["state_code", "period_month"]).reset_index(drop=True)


# ---------- Lookup tables ----------
def lookup_tables():
    divisions = pd.DataFrame(
        [(code, name) for code, (name, _) in ref.DIVISIONS.items()],
        columns=["division_code", "division_name"],
    )
    division_of = {s: code for code, (_, members) in ref.DIVISIONS.items() for s in members}
    state = pd.DataFrame(
        [(code, name, division_of[code]) for name, code in ref.STATE_CODES.items()],
        columns=["state_code", "state_name", "division_code"],
    ).sort_values("state_code")
    return {
        "state": state.reset_index(drop=True),
        "census_division": divisions,
        "station_status": pd.DataFrame(
            ref.STATION_STATUS.items(), columns=["status_code", "description"]
        ),
        "access_type": pd.DataFrame(
            ref.ACCESS_TYPES.items(), columns=["access_code", "description"]
        ),
        "owner_type": pd.DataFrame(
            ref.OWNER_TYPES.items(), columns=["owner_type_code", "description"]
        ),
        "charging_level": pd.DataFrame(
            [(c, d, p) for c, (d, p, _) in ref.CHARGING_LEVELS.items()],
            columns=["level_code", "description", "counts_as_public_supply"],
        ),
        "connector_type": pd.DataFrame(
            ref.CONNECTOR_TYPES.items(), columns=["connector_code", "description"]
        ),
        "vehicle_fuel_type": pd.DataFrame(
            ref.FUEL_TYPES.values(), columns=["fuel_type_id", "fuel_name", "is_plug_in"]
        ),
        "energy_sector": pd.DataFrame(
            ref.ENERGY_SECTORS.items(), columns=["sector_id", "sector_name"]
        ),
    }


def check_keys(tables):
    """Fail loudly if a primary key is duplicated or a foreign key points nowhere."""
    pks = {
        "state": ["state_code"],
        "station": ["station_id"],
        "station_port": ["station_id", "level_code"],
        "station_connector": ["station_id", "connector_code"],
        "vehicle_registration": ["state_code", "year", "fuel_type_id"],
        "electricity_price": ["state_code", "period_month", "sector_id"],
    }
    problems = []
    for table, key in pks.items():
        if table in tables and tables[table].duplicated(key).any():
            problems.append(f"{table}: duplicate primary key {key}")
    states = set(tables["state"]["state_code"])
    for table in ["station", "vehicle_registration", "electricity_price"]:
        if table in tables and not set(tables[table]["state_code"]) <= states:
            problems.append(f"{table}: state_code not in state table")
    for table, col, parent, pcol in [
        ("station_port", "level_code", "charging_level", "level_code"),
        ("station_connector", "connector_code", "connector_type", "connector_code"),
        ("station", "status_code", "station_status", "status_code"),
        ("station", "access_code", "access_type", "access_code"),
    ]:
        if table in tables:
            extra = set(tables[table][col].dropna()) - set(tables[parent][pcol])
            if extra:
                problems.append(f"{table}.{col} has unknown values: {sorted(extra)}")
    if "ingestion_run" in tables:
        runs = set(tables["ingestion_run"]["run_id"])
        for table in ["station", "vehicle_registration", "electricity_price"]:
            if table in tables:
                ids = set(tables[table]["loaded_run_id"].dropna())
                if not ids <= runs:
                    problems.append(f"{table}.loaded_run_id not in ingestion_run")
    if problems:
        raise ValueError("Key checks failed:\n" + "\n".join(problems))
