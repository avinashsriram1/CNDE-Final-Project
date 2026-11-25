# Raw Data Profiling Report
Generated 2026-11-25 by `Scripts/profiling/profile_raw.py`. Raw files are profiled as they arrived, before any cleaning.

## Key findings (read this first)

**Snapshot:** run `2026-11-24` (manifest `20261124T231504Z`). All three sources downloaded successfully; file SHA-256 hashes are in the run manifest.

| Source | Rows | Duplicate keys | Main issues found | Decision (cleaning rule) |
|---|---|---|---|---|
| Stations (API) | 91,776 | 0 | 37 of 77 columns are 99%+ empty; port counts often empty; 26 Puerto Rico stations; some ZIPs lost their leading zero | Drop sparse columns; empty port count = 0 ports; keep 50 states + DC; pad ZIP to 5 digits |
| Prices (API) | 19,158 | 0 | 11 non-state codes (US total + 10 regions); 2 empty prices (AK, Aug–Sep 2016); prices arrive as text | Keep 51 states; flag and exclude empty prices (no imputation); convert to numbers |
| Registrations (web) | 520 | 0 | Includes a "United States" total row; wide format (one column per fuel); counting method changed in 2021 | Check that states sum to the total, then drop it; reshape to long; flag the 2021 break |

**1. Sparsity audit.** 37 station columns are at least 99% empty. Almost all belong to other fuels (CNG, LNG, propane, hydrogen, biodiesel, E85) or French-language copies (`*_fr`). They are empty because we request electric stations only, so they are dropped. `ev_level1_evse_num` (99.3% empty) is kept: Level 1 chargers are simply rare.

**2. Empty values that mean zero.** `ev_dc_fast_num` (81.6% empty) and `ev_level2_evse_num` (17.1% empty) are empty when a station has no ports of that type, not because data is missing. Only 6 stations have all three port counts empty; they are kept as stations but have no port rows.

**3. Empty values that stay empty.** `expected_date` (97.9% empty) is only filled for planned (P) and temporarily unavailable (T) stations. `owner_type_code` (75% empty) and `facility_type` (75.1% empty) are optional in the source; they are kept as NULL, not guessed.

**4. Keys and coordinates.** Station `id` is unique (91,776 distinct values). Latitude and longitude have no empty values. `state` has 52 values: 50 states, DC, and Puerto Rico.

**5. Grain and time coverage.** Stations are points, prices are monthly (2001-01 to the latest month), and registrations are yearly (2016–2025). The shared analysis window is 2016–2025 at state level.

**6. Known anomalies (flagged, not corrected).** In registrations, biodiesel jumps from 0 to 2.19 M and CNG falls from about 522,000 to 41,000 in 2021 (a method change); hybrids (HEV) jump 64% in 2025. EV and plug-in hybrid counts are consistent across all years, so the gap analysis uses those.

**7. Governance.** Phone numbers are removed before any file is saved. Raw files are never edited; every run writes a new dated folder with a manifest. Every row removed during cleaning is counted in `exclusion_log.csv`.

## Detailed profile by source

## Charging stations (NREL/NLR API)
- Rows: **91,776**  ·  Columns: **77**
- Key ['id']: **0** duplicate rows
- Sparse columns (>= 99% empty): 37 (funding_sources, plus4, bd_blends, cng_dispenser_num, cng_fill_type_code, cng_has_rng, cng_psi, cng_renewable_source, cng_total_compression, cng_total_storage, cng_vehicle_class, e85_blender_pump, e85_other_ethanol_blends, ev_level1_evse_num, ev_other_evse, ev_renewable_source, hy_is_retail, hy_pressures, hy_standards, hy_status_link, lng_has_rng, lng_renewable_source, lng_vehicle_class, lpg_nozzle_types, lpg_primary, ng_fill_type_code, ng_psi, ng_vehicle_class, rd_blended_with_biodiesel, rd_blends, rd_blends_fr, rd_max_biodiesel_level, nps_unit_name, access_days_time_fr, intersection_directions_fr, bd_blends_fr, ev_pricing_fr)

| column | type | % empty | distinct | example |
|---|---|---|---|---|
| access_code | object | 0.0 | 2 | private |
| access_days_time | object | 6.7 | 1767 | For fleet use only |
| access_detail_code | object | 93.9 | 7 | GOVERNMENT |
| cards_accepted | object | 88.5 | 115 | CREDIT |
| date_last_confirmed | object | 0.5 | 77 | 2025-11-13 |
| expected_date | object | 97.9 | 317 | 2026-03-09 |
| fuel_type_code | object | 0.0 | 1 | ELEC |
| groups_with_access_code | object | 0.0 | 24 | Private |
| id | int64 | 0.0 | 91776 | 1517 |
| maximum_vehicle_class | object | 82.0 | 3 | MD |
| open_date | object | 0.3 | 4573 | 1999-10-15 |
| owner_type_code | object | 75.0 | 6 | LG |
| related_stations | object | 0.0 | 1027 | [{'id': 440988, 'access_code': 'private' |
| restricted_access | object | 5.9 | 2 | False |
| status_code | object | 0.0 | 3 | E |
| funding_sources | object | 99.6 | 4 | ['NEVI'] |
| unverified | bool | 0.0 | 1 | False |
| facility_type | object | 75.1 | 62 | UTILITY |
| station_name | object | 0.0 | 89325 | LADWP - Truesdale Center |
| updated_at | object | 0.0 | 16008 | 2026-08-07T18:57:47Z |
| geocode_status | object | 0.0 | 5 | GPS |
| latitude | float64 | 0.0 | 87917 | 34.2483191527193 |
| longitude | float64 | 0.0 | 88288 | -118.387971374343 |
| city | object | 0.0 | 7542 | Sun Valley |
| country | object | 0.0 | 1 | US |
| intersection_directions | object | 70.5 | 15170 | West hall and South hall |
| plus4 | object | 100.0 | 0 |  |
| state | object | 0.0 | 52 | CA |
| street_address | object | 0.0 | 61578 | 11797 Truesdale St |
| zip | object | 0.0 | 12770 | 91352 |
| bd_blends | object | 100.0 | 0 |  |
| cng_dispenser_num | object | 100.0 | 0 |  |
| cng_fill_type_code | object | 100.0 | 0 |  |
| cng_has_rng | object | 100.0 | 0 |  |
| cng_psi | object | 100.0 | 0 |  |
| cng_renewable_source | object | 100.0 | 0 |  |
| cng_total_compression | object | 100.0 | 0 |  |
| cng_total_storage | object | 100.0 | 0 |  |
| cng_vehicle_class | object | 100.0 | 0 |  |
| e85_blender_pump | object | 100.0 | 0 |  |
| e85_other_ethanol_blends | object | 100.0 | 0 |  |
| ev_connector_types | object | 0.0 | 30 | ['CHADEMO', 'J1772', 'J1772COMBO'] |
| ev_dc_fast_num | float64 | 81.6 | 61 | 2.0 |
| ev_level1_evse_num | float64 | 99.3 | 36 | 1.0 |
| ev_level2_evse_num | float64 | 17.1 | 113 | 57.0 |
| ev_network | object | 0.0 | 99 | SHELL_RECHARGE |
| ev_network_web | object | 9.4 | 97 | https://www.shell.us/electric-vehicle-ch |
| ev_other_evse | object | 100.0 | 5 | 1 LP Inductive |
| ev_power_sharing | object | 91.6 | 2 | False |
| ev_pricing | object | 85.2 | 923 | Free |
| ev_renewable_source | object | 99.5 | 5 | SOLAR |
| ev_workplace_charging | object | 0.0 | 2 | True |
| hy_is_retail | object | 100.0 | 0 |  |
| hy_pressures | object | 100.0 | 0 |  |
| hy_standards | object | 100.0 | 0 |  |
| hy_status_link | object | 100.0 | 0 |  |
| lng_has_rng | object | 100.0 | 0 |  |
| lng_renewable_source | object | 100.0 | 0 |  |
| lng_vehicle_class | object | 100.0 | 0 |  |
| lpg_nozzle_types | object | 100.0 | 0 |  |
| lpg_primary | object | 100.0 | 0 |  |
| ng_fill_type_code | object | 100.0 | 0 |  |
| ng_psi | object | 100.0 | 0 |  |
| ng_vehicle_class | object | 100.0 | 0 |  |
| rd_blended_with_biodiesel | object | 100.0 | 0 |  |
| rd_blends | object | 100.0 | 0 |  |
| rd_blends_fr | object | 100.0 | 0 |  |
| rd_max_biodiesel_level | object | 100.0 | 0 |  |
| nps_unit_name | object | 99.8 | 78 | Santa Monica Mountains National Recreati |
| access_days_time_fr | object | 100.0 | 1 | 24 hours daily; for guest use only |
| intersection_directions_fr | object | 100.0 | 0 |  |
| bd_blends_fr | object | 100.0 | 0 |  |
| groups_with_access_code_fr | object | 0.0 | 24 | Privé |
| ev_pricing_fr | object | 100.0 | 0 |  |
| ev_charging_units | object | 0.0 | 7905 | [{'network': 'SHELL_RECHARGE', 'connecto |
| ev_network_ids | object | 24.9 | 68878 | {'station': ['USCPIL226108'], 'posts': [ |
| federal_agency | object | 98.0 | 29 | {'id': 23, 'code': 'SI', 'name': 'Smiths |

## Electricity prices (EIA API)
- Rows: **19,158**  ·  Columns: **7**
- Key ['period', 'stateid', 'sectorid']: **0** duplicate rows
- Sparse columns (>= 99% empty): 0

| column | type | % empty | distinct | example |
|---|---|---|---|---|
| period | object | 0.0 | 309 | 2001-01 |
| stateid | object | 0.0 | 62 | AK |
| stateDescription | object | 0.0 | 62 | Alaska |
| sectorid | object | 0.0 | 1 | RES |
| sectorName | object | 0.0 | 1 | residential |
| price | object | 0.0 | 2439 | 11.22 |
| price-units | object | 0.0 | 1 | cents per kilowatt-hour |

## EV registrations (AFDC web tables)
- Rows: **520**  ·  Columns: **14**
- Key ['year', 'State']: **0** duplicate rows
- Sparse columns (>= 99% empty): 0

| column | type | % empty | distinct | example |
|---|---|---|---|---|
| year | int64 | 0.0 | 10 | 2016 |
| State | object | 0.0 | 52 | Alabama |
| Electric (EV) | int64 | 0.0 | 301 | 500 |
| Plug-In Hybrid Electric (PHEV) | int64 | 0.0 | 239 | 900 |
| Hybrid Electric (HEV) | int64 | 0.0 | 465 | 29100 |
| Biodiesel | int64 | 0.0 | 233 | 0 |
| Ethanol/Flex (E85) | int64 | 0.0 | 503 | 428300 |
| Compressed Natural Gas (CNG) | int64 | 0.0 | 180 | 20100 |
| Propane | int64 | 0.0 | 20 | 0 |
| Hydrogen | int64 | 0.0 | 13 | 0 |
| Methanol | int64 | 0.0 | 5 | 0 |
| Gasoline | int64 | 0.0 | 515 | 3777300 |
| Diesel | int64 | 0.0 | 474 | 126500 |
| Unknown Fuel | int64 | 0.0 | 407 | 53900 |
