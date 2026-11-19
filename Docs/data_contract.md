# Data Contract v0 (K3)

**Owner:** Part A. **Status:** DRAFT template, due Thu 11/19, approved by all four before merge.
**Why it matters:** Parts B, C, and D build against this file and the K4 fixtures instead of waiting for ingestion. After merge, change it only by PR with all owners tagged.

Pre-filled items come from our first look at the 2026-11-18 Drive snapshot. Every `verify` must be checked against the actual files before approval. Do not add columns from API docs that are not in the files.

## Conventions (all Silver tables)
- Column names: `snake_case`, whitespace stripped.
- State key: `state_code`, 2-letter USPS code, 50 states + DC = 51 values. No `US` total, no EIA regional codes.
- Exclusions are never silent: each filter writes a count to the exclusion log.
- Imputation policy: none. Flag and exclude with a logged count unless a value is derivable.

## 1. Stations: `silver_stations`
Source: NREL/AFDC stations API (`afdc_stations.json` raw; CSV for reference).
Grain / key: one row per station, PK `station_id` (from `id`; dedupe on it).

| Silver column | Type | Source column | Rule |
|---|---|---|---|
| station_id | BIGINT | id | dedupe, keep latest `date_last_confirmed` (verify rule) |
| fuel_type_code | STRING | fuel_type_code | keep all; gap universe = `ELEC` |
| status_code | STRING | status_code | E / P / T; gap universe = `E` |
| access_code | STRING | access_code | gap universe = public (verify values) |
| state_code | STRING | state | must be in the 51-state list |
| zip | STRING | zip | keep as string (leading zeros) |
| latitude, longitude | DOUBLE | latitude, longitude | null → flag, not imputed |
| ev_network | STRING | ev_network | |
| ev_level1_evse_num | INT | ev_level1_evse_num | null → 0? (decide, verify) |
| ev_level2_evse_num | INT | ev_level2_evse_num | null → 0? (decide, verify) |
| ev_dc_fast_num | INT | ev_dc_fast_num | null → 0? (decide, verify) |
| ev_connector_types | ARRAY/STRING | ev_connector_types | multi-valued; bridge table in OLTP |
| open_date | DATE | open_date | cast; null allowed |
| date_last_confirmed | DATE | date_last_confirmed | cast |
| _todo_ | | unverified flag | verify exact column name |

Dropped at Silver (documented, GOV-01): nested `related_stations`, `ev_network_ids.*`, `federal_agency.*`, and any contact fields (verify which exist).

## 2. Registrations: `silver_registrations_long`
Source: `afdc_registrations.csv` (wide; ~2016–2025 × 51 + `United States` total per year).
Grain / key: (`state_code`, `year`, `fuel_type`).

| Silver column | Type | Rule |
|---|---|---|
| state_code | STRING | map state name → code; drop `United States` total row (log count) |
| year | INT | |
| fuel_type | STRING | from header after whitespace normalization (verify list) |
| vehicle_count | INT | values rounded to nearest 100 in source; flag low-confidence states |

Known anomalies: trailing whitespace in headers; 2021 series break for some fuels (Biodiesel appears, CNG drops); EV and PHEV look consistent (verify).

## 3. Prices: `silver_prices_state_monthly`
Source: `eia_residential_prices.csv` (columns: `period`, `stateid`, `stateDescription`, `sectorid`, `sectorName`, `price`, `price-units`).
Grain / key: (`state_code`, `period`, `sector_id`).

| Silver column | Type | Source column | Rule |
|---|---|---|---|
| state_code | STRING | stateid | keep 51 states only; drop regional codes (ENC, ESC, …) and US total (log counts) |
| period | DATE | period (YYYY-MM) | first of month |
| sector_id | STRING | sectorid | residential now (verify code); commercial = PRO-07 stretch |
| price_cents_kwh | DOUBLE | price | > 0; sanity range TBD |

## Fixtures (K4)
A few hundred real rows per source in `Scripts/tests/fixtures/`, including: US total row, EIA regional codes, a duplicate station id, missing coordinates, a header with trailing whitespace.

## Approval
- [ ] Part A  - [ ] Part B  - [ ] Part C  - [ ] Part D
