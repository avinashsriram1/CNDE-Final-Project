"""Cleaning unit tests (Part A). Small hand-made inputs that cover each rule."""

import pandas as pd
import pytest

from Scripts.common import cleaning


def station(**overrides):
    base = {
        "id": 1,
        "station_name": "Test",
        "fuel_type_code": "ELEC",
        "status_code": "E",
        "access_code": "public",
        "owner_type_code": "P",
        "state": "IL",
        "street_address": "1 Main St",
        "city": "Chicago",
        "zip": "60601",
        "latitude": 41.9,
        "longitude": -87.6,
        "facility_type": None,
        "maximum_vehicle_class": None,
        "open_date": "2024-01-01",
        "expected_date": None,
        "date_last_confirmed": "2025-01-01",
        "updated_at": "2025-01-01T00:00:00Z",
        "unverified": False,
        "restricted_access": False,
        "ev_workplace_charging": False,
        "access_days_time": "24 hours daily",
        "ev_pricing": None,
        "ev_network": "ChargePoint Network",
        "ev_network_web": "https://example.com",
        "federal_agency": None,
        "related_stations": [],
        "ev_connector_types": ["J1772"],
        "ev_level1_evse_num": None,
        "ev_level2_evse_num": 2,
        "ev_dc_fast_num": None,
        "station_phone": "555-0100",
    }
    return {**base, **overrides}


def test_pad_zip_restores_leading_zero():
    assert cleaning.pad_zip("5403") == "05403"
    assert cleaning.pad_zip("60601") == "60601"
    assert cleaning.pad_zip(None) is None


def test_stations_rules():
    log = cleaning.ExclusionLog()
    records = [
        station(id=1),
        station(id=2, state="PR"),
        station(id=3, zip="5403", ev_dc_fast_num=4, ev_connector_types=["J1772", "CHADEMO"]),
    ]
    out = cleaning.clean_stations(records, log)
    st = out["station"]
    assert set(st["station_id"]) == {1, 3}  # Puerto Rico removed
    assert "station_phone" not in st.columns  # personal data removed
    assert st.set_index("station_id").loc[3, "zip"] == "05403"
    ports = out["station_port"]
    assert set(ports["level_code"]) == {"L2", "DCFC"}  # empty counts -> no row
    assert (ports["port_count"] > 0).all()
    assert len(out["station_connector"]) == 3
    excluded = log.to_frame().set_index("rule")["rows_excluded"]
    assert excluded["state_code not in 50 states + DC"] == 1


def test_duplicate_station_keeps_latest_confirmed():
    log = cleaning.ExclusionLog()
    records = [
        station(id=7, city="Old", date_last_confirmed="2024-01-01"),
        station(id=7, city="New", date_last_confirmed="2025-06-01"),
    ]
    st = cleaning.clean_stations(records, log)["station"]
    assert len(st) == 1 and st.loc[0, "city"] == "New"


def registrations_wide(us_ev=300):
    fuels = list(cleaning.ref.FUEL_TYPES)
    rows = []
    for name, ev in [("Illinois", 100), ("Ohio", 200), ("United States", us_ev)]:
        row = {"year": 2025, "State": name, **dict.fromkeys(fuels, 0)}
        row["Electric (EV)"] = ev
        rows.append(row)
    return pd.DataFrame(rows)


def test_registrations_wide_to_long_and_total_check():
    log = cleaning.ExclusionLog()
    long = cleaning.clean_registrations(registrations_wide(), log)
    assert len(long) == 2 * 12  # 2 states x 12 fuel types
    ev = long[(long.state_code == "IL") & (long.fuel_type_id == 1)]
    assert ev["vehicle_count"].item() == 100


def test_registrations_total_mismatch_fails():
    with pytest.raises(ValueError, match="United States"):
        cleaning.clean_registrations(registrations_wide(us_ev=999), cleaning.ExclusionLog())


def test_prices_rules():
    raw = pd.DataFrame(
        {
            "period": ["2025-01", "2025-01", "2025-01", "2025-02"],
            "stateid": ["IL", "US", "ENC", "AK"],
            "sectorid": ["RES"] * 4,
            "price": [15.2, 16.0, 15.0, None],
        }
    )
    log = cleaning.ExclusionLog()
    out = cleaning.clean_prices(raw, log)
    assert out["state_code"].tolist() == ["IL"]
    assert str(out.loc[0, "period_month"]) == "2025-01-01"


def test_lookup_tables_cover_51_states():
    tables = cleaning.lookup_tables()
    assert len(tables["state"]) == 51
    assert tables["state"]["division_code"].notna().all()


def test_expected_date_only_kept_for_planned_and_unavailable():
    log = cleaning.ExclusionLog()
    records = [
        station(id=1, status_code="E", expected_date="2026-12-01"),
        station(id=2, status_code="P", expected_date="2026-12-01"),
        station(id=3, status_code="T", expected_date="2026-12-01"),
    ]
    st = cleaning.clean_stations(records, log)["station"].set_index("station_id")
    assert st.loc[1, "expected_date"] is None or pd.isna(st.loc[1, "expected_date"])
    assert str(st.loc[2, "expected_date"]) == "2026-12-01"
    assert str(st.loc[3, "expected_date"]) == "2026-12-01"


def test_loaded_run_id_is_set_on_every_row():
    log = cleaning.ExclusionLog()
    st = cleaning.clean_stations([station(id=1)], log, run_id=202611242315041)["station"]
    assert st["loaded_run_id"].tolist() == [202611242315041]


def test_lineage_picks_newest_file_per_source_and_reads_manifest(tmp_path):
    import json

    from Scripts.common import lineage

    old = tmp_path / "2026-11-24"
    new = tmp_path / "2026-11-30"
    for day, sources in [(old, ["afdc_stations", "eia_prices"]), (new, ["afdc_stations"])]:
        for source in sources:
            (day / source).mkdir(parents=True)
            name = "stations.json.gz" if source == "afdc_stations" else "retail_sales.json.gz"
            (day / source / name).write_text("x")
    (old / "_manifest").mkdir()
    uri = "gs://b/raw/2026-11-24/eia_prices/retail_sales.json.gz"
    manifest = {
        "run_id": "20261124T231504Z",
        "results": [{"source": "eia_prices", "rows": 5, "files": [uri], "status": "success"}],
        "files": [{"uri": uri, "sha256": "abc"}],
    }
    (old / "_manifest" / "20261124T231504Z.json").write_text(json.dumps(manifest))

    assert lineage.latest_file(tmp_path, "afdc_stations")[1] == "2026-11-30"
    path, day = lineage.latest_file(tmp_path, "eia_prices")
    assert day == "2026-11-24"
    row = lineage.ingestion_run_row(tmp_path, "eia_prices", day)
    assert row["run_id"] == 202611242315042
    assert row["file_hash"] == "abc" and row["row_count"] == 5
