"""Carbon accounting for energy savings: one simple, editable factor."""

# All-India weighted average grid emission factor, CEA CO2 Baseline Database v19.0,
# FY 2022-23, including renewables: 0.716 tCO2/MWh = 0.716 kgCO2/kWh.
# A newer CEA version (22.0) exists: update this value once you have read it.
# This is a national average, not a measurement for this campus.
GRID_EMISSION_FACTOR_KG_PER_KWH = 0.716


def co2_kg(kwh: float, factor: float = GRID_EMISSION_FACTOR_KG_PER_KWH) -> float:
    return kwh * factor