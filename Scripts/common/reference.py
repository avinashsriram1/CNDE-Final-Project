"""Reference (lookup) data for the clean tables. Values verified against the 2026-11-18 snapshot."""

STATE_CODES = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL",
    "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA",
    "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR",
    "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA",
    "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}  # fmt: skip
US_TOTAL_NAME = "United States"

# Census divisions as EIA reports them (Pacific is split into contiguous / noncontiguous).
DIVISIONS = {
    "NEW": ("New England", ["CT", "ME", "MA", "NH", "RI", "VT"]),
    "MAT": ("Middle Atlantic", ["NJ", "NY", "PA"]),
    "ENC": ("East North Central", ["IL", "IN", "MI", "OH", "WI"]),
    "WNC": ("West North Central", ["IA", "KS", "MN", "MO", "NE", "ND", "SD"]),
    "SAT": ("South Atlantic", ["DE", "DC", "FL", "GA", "MD", "NC", "SC", "VA", "WV"]),
    "ESC": ("East South Central", ["AL", "KY", "MS", "TN"]),
    "WSC": ("West South Central", ["AR", "LA", "OK", "TX"]),
    "MTN": ("Mountain", ["AZ", "CO", "ID", "MT", "NV", "NM", "UT", "WY"]),
    "PACC": ("Pacific Contiguous", ["CA", "OR", "WA"]),
    "PACN": ("Pacific Noncontiguous", ["AK", "HI"]),
}
EIA_NON_STATE_CODES = {"US", *DIVISIONS}

STATION_STATUS = {"E": "Available", "P": "Planned", "T": "Temporarily unavailable"}
ACCESS_TYPES = {"public": "Open to the public", "private": "Private or restricted"}
OWNER_TYPES = {
    "P": "Privately owned",
    "T": "Utility owned",
    "FG": "Federal government owned",
    "SG": "State government owned",
    "LG": "Local government owned",
    "J": "Jointly owned",
}
# level_code: (description, counts_as_public_supply, source column)
CHARGING_LEVELS = {
    "L1": ("Level 1", False, "ev_level1_evse_num"),
    "L2": ("Level 2", True, "ev_level2_evse_num"),
    "DCFC": ("DC fast", True, "ev_dc_fast_num"),
}
CONNECTOR_TYPES = {
    "J1772": "SAE J1772 (Level 2)",
    "J1772COMBO": "CCS / SAE J1772 Combo (DC fast)",
    "TESLA": "Tesla / NACS",
    "CHADEMO": "CHAdeMO (DC fast)",
    "NEMA1450": "NEMA 14-50 outlet",
    "NEMA515": "NEMA 5-15 outlet",
    "NEMA520": "NEMA 5-20 outlet",
    "J3271": "SAE J3271 (megawatt charging)",
}
# Registration column header -> (fuel_type_id, fuel_name, is_plug_in)
FUEL_TYPES = {
    "Electric (EV)": (1, "Electric (EV)", True),
    "Plug-In Hybrid Electric (PHEV)": (2, "Plug-in hybrid (PHEV)", True),
    "Hybrid Electric (HEV)": (3, "Hybrid (HEV)", False),
    "Biodiesel": (4, "Biodiesel", False),
    "Ethanol/Flex (E85)": (5, "Ethanol/Flex (E85)", False),
    "Compressed Natural Gas (CNG)": (6, "Compressed natural gas (CNG)", False),
    "Propane": (7, "Propane", False),
    "Hydrogen": (8, "Hydrogen", False),
    "Methanol": (9, "Methanol", False),
    "Gasoline": (10, "Gasoline", False),
    "Diesel": (11, "Diesel", False),
    "Unknown Fuel": (12, "Unknown", False),
}
ENERGY_SECTORS = {"RES": "residential", "COM": "commercial", "ALL": "all sectors"}

PII_FIELDS = ["station_phone"]
