"""What-if scenario and carbon endpoints. Historical load; savings factors are assumptions."""
from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, HTTPException, Query

from optimizer.carbon import GRID_EMISSION_FACTOR_KG_PER_KWH
from optimizer.scenarios import SCENARIOS, SAVING_PER_C, run_scenario, summarize

router = APIRouter(tags=["what-if"])

NOTE = ("Simulation on historical (Arizona, BDG2) load. HVAC/lighting split and savings "
        "factors are assumptions. No real equipment is controlled.")


@lru_cache(maxsize=1)
def _inputs():
    from config.settings import BASE_DIR, get_settings
    from features.weather_client import load_site_weather
    from features.calendar_features import load_calendar
    from simulator.profile_loader import load_profiles
    from twin.entities import Campus

    campus = Campus.from_yaml(get_settings().campus_model_path)
    values, _ = load_profiles()
    weather = load_site_weather(BASE_DIR / "data" / "raw" / "weather.csv", "Fox")
    calendar = load_calendar(BASE_DIR / "data" / "academic_calendar.csv")
    return campus, values, weather, calendar


def compute(start: str, end: str, params: dict) -> list[dict]:
    from features.calendar_features import calendar_features

    campus, values, weather, calendar = _inputs()
    results = {}
    for b in campus.buildings:
        energy = values.loc[start:end, b.id]
        if energy.empty:
            raise HTTPException(status_code=404, detail="No data in that date range")
        feats = calendar_features(energy.index, calendar)
        temp = weather["air_temp_c"].reindex(energy.index)
        results[b.id] = run_scenario(b, energy, temp, feats, **params)
    return summarize(results).to_dict(orient="records")


@router.get("/carbon/factor")
def carbon_factor():
    return {
        "kg_co2_per_kwh": GRID_EMISSION_FACTOR_KG_PER_KWH,
        "source": "CEA CO2 Baseline Database v19.0, FY2022-23, all-India weighted average incl. renewables",
        "note": "National average, not measured for this campus.",
    }


@router.get("/whatif")
def whatif(
    start: str = Query("2017-07-01"),
    end: str = Query("2017-07-31"),
    scenario: str | None = Query(None, description="One of /whatif/scenarios"),
    setpoint_delta_c: float = Query(0.0, ge=0, le=6),
    hvac_empty_reduction: float = Query(0.0, ge=0, le=1),
    lighting_reduction: float = Query(0.0, ge=0, le=1),
):
    if scenario:
        if scenario not in SCENARIOS:
            raise HTTPException(status_code=404, detail=f"Unknown scenario. Choose from {list(SCENARIOS)}")
        params = SCENARIOS[scenario]
    else:
        params = dict(setpoint_delta_c=setpoint_delta_c, hvac_empty_reduction=hvac_empty_reduction,
                      lighting_reduction=lighting_reduction)
    return {"start": start, "end": end, "params": params,
            "saving_per_c_assumed": SAVING_PER_C, "note": NOTE,
            "results": compute(start, end, params)}


@router.get("/whatif/scenarios")
def list_scenarios():
    return {"scenarios": SCENARIOS, "note": NOTE}