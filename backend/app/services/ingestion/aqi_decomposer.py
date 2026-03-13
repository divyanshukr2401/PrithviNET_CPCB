"""
PRITHVINET AQI Decomposition Engine (shared module)
=====================================================
Core logic for decomposing composite CPCB AQI values into individual
pollutant concentrations using:
  - Official CPCB/NAQI breakpoint table
  - City-specific dominant-pollutant probability profiles
  - Seasonal and diurnal adjustments
  - Inter-pollutant correlations (PM2.5/PM10, NO2/CO)

Used by:
  - scripts/decompose_aqi_to_pollutants.py  (batch historical processing)
  - backend/app/services/ingestion/live_simulator.py  (real-time simulation)
"""

from __future__ import annotations

import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

POLLUTANTS = ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3", "NH3", "Pb"]

UNITS = {
    "PM2.5": "µg/m³",
    "PM10": "µg/m³",
    "NO2": "µg/m³",
    "SO2": "µg/m³",
    "CO": "mg/m³",
    "O3": "µg/m³",
    "NH3": "µg/m³",
    "Pb": "µg/m³",
}

# ---------------------------------------------------------------------------
# CPCB NAQI Breakpoint Table
# Each entry: (AQI_lo, AQI_hi, Conc_lo, Conc_hi)
# ---------------------------------------------------------------------------

BREAKPOINTS: dict[str, list[tuple[int, int, float, float]]] = {
    "PM2.5": [
        (0, 50, 0.0, 30.0),
        (51, 100, 31.0, 60.0),
        (101, 200, 61.0, 90.0),
        (201, 300, 91.0, 120.0),
        (301, 400, 121.0, 250.0),
        (401, 500, 250.0, 380.0),
    ],
    "PM10": [
        (0, 50, 0.0, 50.0),
        (51, 100, 51.0, 100.0),
        (101, 200, 101.0, 250.0),
        (201, 300, 251.0, 350.0),
        (301, 400, 351.0, 430.0),
        (401, 500, 430.0, 510.0),
    ],
    "NO2": [
        (0, 50, 0.0, 40.0),
        (51, 100, 41.0, 80.0),
        (101, 200, 81.0, 180.0),
        (201, 300, 181.0, 280.0),
        (301, 400, 281.0, 400.0),
        (401, 500, 400.0, 520.0),
    ],
    "SO2": [
        (0, 50, 0.0, 40.0),
        (51, 100, 41.0, 80.0),
        (101, 200, 81.0, 380.0),
        (201, 300, 381.0, 800.0),
        (301, 400, 801.0, 1600.0),
        (401, 500, 1600.0, 2400.0),
    ],
    "CO": [
        (0, 50, 0.0, 1.0),
        (51, 100, 1.1, 2.0),
        (101, 200, 2.1, 10.0),
        (201, 300, 10.1, 17.0),
        (301, 400, 17.0, 34.0),
        (401, 500, 34.0, 46.0),
    ],
    "O3": [
        (0, 50, 0.0, 50.0),
        (51, 100, 51.0, 100.0),
        (101, 200, 101.0, 168.0),
        (201, 300, 169.0, 208.0),
        (301, 400, 209.0, 748.0),
        (401, 500, 748.0, 960.0),
    ],
    "NH3": [
        (0, 50, 0.0, 200.0),
        (51, 100, 201.0, 400.0),
        (101, 200, 401.0, 800.0),
        (201, 300, 801.0, 1200.0),
        (301, 400, 1200.0, 1800.0),
        (401, 500, 1800.0, 2400.0),
    ],
    "Pb": [
        (0, 50, 0.0, 0.5),
        (51, 100, 0.5, 1.0),
        (101, 200, 1.1, 2.0),
        (201, 300, 2.1, 3.0),
        (301, 400, 3.1, 3.5),
        (401, 500, 3.5, 4.0),
    ],
}


def sub_index_to_concentration(sub_index: float, pollutant: str) -> float:
    """Reverse CPCB breakpoint: sub-index → concentration."""
    si = max(0.0, min(500.0, sub_index))
    bps = BREAKPOINTS[pollutant]
    for aqi_lo, aqi_hi, conc_lo, conc_hi in bps:
        if aqi_lo <= si <= aqi_hi:
            if aqi_hi == aqi_lo:
                return conc_lo
            frac = (si - aqi_lo) / (aqi_hi - aqi_lo)
            return conc_lo + frac * (conc_hi - conc_lo)
    aqi_lo, aqi_hi, conc_lo, conc_hi = bps[-1]
    frac = (si - aqi_lo) / (aqi_hi - aqi_lo) if aqi_hi != aqi_lo else 1.0
    return conc_lo + frac * (conc_hi - conc_lo)


def concentration_to_sub_index(conc: float, pollutant: str) -> float:
    """Forward CPCB breakpoint: concentration → sub-index."""
    bps = BREAKPOINTS[pollutant]
    for aqi_lo, aqi_hi, conc_lo, conc_hi in bps:
        if conc_lo <= conc <= conc_hi:
            if conc_hi == conc_lo:
                return float(aqi_lo)
            frac = (conc - conc_lo) / (conc_hi - conc_lo)
            return aqi_lo + frac * (aqi_hi - aqi_lo)
    aqi_lo, aqi_hi, conc_lo, conc_hi = bps[-1]
    if conc_hi == conc_lo:
        return float(aqi_hi)
    frac = (conc - conc_lo) / (conc_hi - conc_lo)
    return aqi_lo + frac * (aqi_hi - aqi_lo)


# ---------------------------------------------------------------------------
# Season helper
# ---------------------------------------------------------------------------


def _get_season(month: int) -> str:
    if month in (11, 12, 1, 2):
        return "winter"
    elif month in (6, 7, 8, 9):
        return "monsoon"
    elif month in (3, 4, 5):
        return "summer"
    else:
        return "post_monsoon"


# ---------------------------------------------------------------------------
# City-Specific Dominant Pollutant Profiles
# ---------------------------------------------------------------------------

CITY_PROFILES: dict[str, dict[str, dict[str, float]]] = {
    "Raipur": {
        "winter": {
            "PM2.5": 0.45,
            "PM10": 0.25,
            "NO2": 0.12,
            "SO2": 0.03,
            "CO": 0.06,
            "O3": 0.04,
            "NH3": 0.03,
            "Pb": 0.02,
        },
        "summer": {
            "PM2.5": 0.20,
            "PM10": 0.30,
            "NO2": 0.10,
            "SO2": 0.04,
            "CO": 0.05,
            "O3": 0.22,
            "NH3": 0.06,
            "Pb": 0.03,
        },
        "monsoon": {
            "PM2.5": 0.15,
            "PM10": 0.15,
            "NO2": 0.10,
            "SO2": 0.05,
            "CO": 0.05,
            "O3": 0.35,
            "NH3": 0.10,
            "Pb": 0.05,
        },
        "post_monsoon": {
            "PM2.5": 0.35,
            "PM10": 0.25,
            "NO2": 0.12,
            "SO2": 0.05,
            "CO": 0.08,
            "O3": 0.08,
            "NH3": 0.04,
            "Pb": 0.03,
        },
    },
    "Bhilai": {
        "winter": {
            "PM2.5": 0.20,
            "PM10": 0.30,
            "NO2": 0.08,
            "SO2": 0.22,
            "CO": 0.10,
            "O3": 0.03,
            "NH3": 0.04,
            "Pb": 0.03,
        },
        "summer": {
            "PM2.5": 0.15,
            "PM10": 0.30,
            "NO2": 0.07,
            "SO2": 0.20,
            "CO": 0.08,
            "O3": 0.12,
            "NH3": 0.05,
            "Pb": 0.03,
        },
        "monsoon": {
            "PM2.5": 0.10,
            "PM10": 0.20,
            "NO2": 0.08,
            "SO2": 0.25,
            "CO": 0.07,
            "O3": 0.18,
            "NH3": 0.07,
            "Pb": 0.05,
        },
        "post_monsoon": {
            "PM2.5": 0.20,
            "PM10": 0.28,
            "NO2": 0.08,
            "SO2": 0.22,
            "CO": 0.10,
            "O3": 0.05,
            "NH3": 0.04,
            "Pb": 0.03,
        },
    },
    "Korba": {
        "winter": {
            "PM2.5": 0.18,
            "PM10": 0.28,
            "NO2": 0.08,
            "SO2": 0.28,
            "CO": 0.06,
            "O3": 0.04,
            "NH3": 0.05,
            "Pb": 0.03,
        },
        "summer": {
            "PM2.5": 0.12,
            "PM10": 0.30,
            "NO2": 0.07,
            "SO2": 0.25,
            "CO": 0.05,
            "O3": 0.13,
            "NH3": 0.05,
            "Pb": 0.03,
        },
        "monsoon": {
            "PM2.5": 0.10,
            "PM10": 0.18,
            "NO2": 0.08,
            "SO2": 0.30,
            "CO": 0.05,
            "O3": 0.18,
            "NH3": 0.06,
            "Pb": 0.05,
        },
        "post_monsoon": {
            "PM2.5": 0.18,
            "PM10": 0.28,
            "NO2": 0.08,
            "SO2": 0.28,
            "CO": 0.06,
            "O3": 0.04,
            "NH3": 0.05,
            "Pb": 0.03,
        },
    },
    "Bilaspur": {
        "winter": {
            "PM2.5": 0.40,
            "PM10": 0.28,
            "NO2": 0.10,
            "SO2": 0.06,
            "CO": 0.06,
            "O3": 0.04,
            "NH3": 0.04,
            "Pb": 0.02,
        },
        "summer": {
            "PM2.5": 0.22,
            "PM10": 0.30,
            "NO2": 0.08,
            "SO2": 0.06,
            "CO": 0.05,
            "O3": 0.20,
            "NH3": 0.06,
            "Pb": 0.03,
        },
        "monsoon": {
            "PM2.5": 0.15,
            "PM10": 0.18,
            "NO2": 0.10,
            "SO2": 0.07,
            "CO": 0.05,
            "O3": 0.30,
            "NH3": 0.10,
            "Pb": 0.05,
        },
        "post_monsoon": {
            "PM2.5": 0.35,
            "PM10": 0.25,
            "NO2": 0.10,
            "SO2": 0.08,
            "CO": 0.07,
            "O3": 0.08,
            "NH3": 0.04,
            "Pb": 0.03,
        },
    },
    "mining_default": {
        "winter": {
            "PM2.5": 0.15,
            "PM10": 0.45,
            "NO2": 0.06,
            "SO2": 0.15,
            "CO": 0.05,
            "O3": 0.04,
            "NH3": 0.06,
            "Pb": 0.04,
        },
        "summer": {
            "PM2.5": 0.12,
            "PM10": 0.45,
            "NO2": 0.05,
            "SO2": 0.15,
            "CO": 0.04,
            "O3": 0.12,
            "NH3": 0.04,
            "Pb": 0.03,
        },
        "monsoon": {
            "PM2.5": 0.10,
            "PM10": 0.30,
            "NO2": 0.06,
            "SO2": 0.18,
            "CO": 0.04,
            "O3": 0.20,
            "NH3": 0.07,
            "Pb": 0.05,
        },
        "post_monsoon": {
            "PM2.5": 0.15,
            "PM10": 0.42,
            "NO2": 0.06,
            "SO2": 0.16,
            "CO": 0.05,
            "O3": 0.06,
            "NH3": 0.06,
            "Pb": 0.04,
        },
    },
}

CITY_PROFILE_MAP: dict[str, str] = {
    "Raipur": "Raipur",
    "Bhilai": "Bhilai",
    "Korba": "Korba",
    "Bilaspur": "Bilaspur",
    "Chhal": "mining_default",
    "Kunjemura": "mining_default",
    "Milupara": "mining_default",
    "Tumidih": "mining_default",
}

SUB_INDEX_RATIO: dict[str, dict[str, float]] = {
    "urban": {
        "PM2.5": 0.80,
        "PM10": 0.75,
        "NO2": 0.55,
        "SO2": 0.30,
        "CO": 0.40,
        "O3": 0.50,
        "NH3": 0.25,
        "Pb": 0.15,
    },
    "industrial_steel": {
        "PM2.5": 0.70,
        "PM10": 0.80,
        "NO2": 0.45,
        "SO2": 0.70,
        "CO": 0.50,
        "O3": 0.35,
        "NH3": 0.25,
        "Pb": 0.20,
    },
    "coal_power": {
        "PM2.5": 0.65,
        "PM10": 0.80,
        "NO2": 0.40,
        "SO2": 0.75,
        "CO": 0.35,
        "O3": 0.35,
        "NH3": 0.30,
        "Pb": 0.20,
    },
    "mining": {
        "PM2.5": 0.55,
        "PM10": 0.85,
        "NO2": 0.35,
        "SO2": 0.55,
        "CO": 0.30,
        "O3": 0.30,
        "NH3": 0.30,
        "Pb": 0.25,
    },
}

CITY_RATIO_MAP: dict[str, str] = {
    "Raipur": "urban",
    "Bilaspur": "urban",
    "Bhilai": "industrial_steel",
    "Korba": "coal_power",
    "Chhal": "mining",
    "Kunjemura": "mining",
    "Milupara": "mining",
    "Tumidih": "mining",
}


def get_dominant_weights(city: str, month: int, hour: int) -> dict[str, float]:
    """Get pollutant dominance weights for a given city, month, and hour."""
    profile_key = CITY_PROFILE_MAP.get(city, "Raipur")
    season = _get_season(month)
    base = CITY_PROFILES[profile_key][season].copy()

    if 7 <= hour <= 10:
        base["NO2"] *= 1.5
        base["CO"] *= 1.4
    elif 12 <= hour <= 16:
        base["O3"] *= 1.8
        base["NO2"] *= 0.8
    elif 17 <= hour <= 20:
        base["NO2"] *= 1.4
        base["CO"] *= 1.3
    elif hour >= 22 or hour <= 5:
        base["PM2.5"] *= 1.3
        base["PM10"] *= 1.1

    total = sum(base.values())
    return {k: v / total for k, v in base.items()}


# ---------------------------------------------------------------------------
# Main decompose function
# ---------------------------------------------------------------------------


def decompose_aqi(
    aqi: int,
    city: str,
    month: int,
    hour: int,
    rng: np.random.Generator,
) -> list[dict]:
    """
    Decompose a composite AQI into 8 pollutant readings.

    Returns list of 8 dicts with keys: parameter, value, unit, aqi (sub-index)
    """
    if aqi <= 0:
        return [
            {"parameter": p, "value": 0.0, "unit": UNITS[p], "aqi": 0}
            for p in POLLUTANTS
        ]

    aqi = min(500, max(1, aqi))

    # Pick dominant pollutant
    weights = get_dominant_weights(city, month, hour)
    pollutant_names = list(weights.keys())
    pollutant_probs = np.array([weights[p] for p in pollutant_names])
    pollutant_probs /= pollutant_probs.sum()
    dominant = rng.choice(pollutant_names, p=pollutant_probs)

    # Generate sub-indices
    ratio_key = CITY_RATIO_MAP.get(city, "urban")
    ratio_profile = SUB_INDEX_RATIO[ratio_key]
    sub_indices: dict[str, float] = {}

    for p in POLLUTANTS:
        if p == dominant:
            sub_indices[p] = float(aqi)
        else:
            mean_ratio = max(0.05, min(0.95, ratio_profile[p]))
            kappa = 12.0
            alpha = mean_ratio * kappa
            beta_param = (1 - mean_ratio) * kappa
            ratio = rng.beta(alpha, beta_param)
            raw_si = ratio * aqi
            raw_si = min(raw_si, aqi - 1.0) if aqi > 1 else 0.0
            sub_indices[p] = max(0.0, raw_si)

    # PM2.5/PM10 consistency
    pm25_conc = sub_index_to_concentration(sub_indices["PM2.5"], "PM2.5")
    pm10_conc = sub_index_to_concentration(sub_indices["PM10"], "PM10")
    if pm10_conc > 0 and pm25_conc > pm10_conc:
        target = pm10_conc * rng.uniform(0.40, 0.70)
        new_si = concentration_to_sub_index(target, "PM2.5")
        if dominant == "PM2.5":
            sub_indices["PM10"] = float(aqi)
            sub_indices["PM2.5"] = min(new_si, aqi - 1.0)
            dominant = "PM10"
        else:
            sub_indices["PM2.5"] = min(new_si, aqi - 1.0)

    # NO2/CO correlation
    no2_si = sub_indices["NO2"]
    co_si = sub_indices["CO"]
    if no2_si > 0 and co_si > 0 and aqi > 0:
        corr = 0.4
        blended = (co_si / aqi) * (1 - corr) + (no2_si / aqi) * corr
        blended_si = blended * aqi
        if dominant != "CO":
            blended_si = min(blended_si, aqi - 1.0)
        sub_indices["CO"] = max(0.0, blended_si)

    # Convert to concentrations
    results: list[dict] = []
    for p in POLLUTANTS:
        conc = sub_index_to_concentration(sub_indices[p], p)
        if p != dominant:
            conc = max(0.0, conc * (1 + rng.uniform(-0.05, 0.05)))
        conc = max(0.0, conc)

        if p == "CO":
            conc = round(conc, 2)
        elif p == "Pb":
            conc = round(conc, 3)
        else:
            conc = round(conc, 1)

        final_si = int(round(concentration_to_sub_index(conc, p)))
        final_si = max(0, min(500, final_si))
        if p == dominant:
            final_si = aqi
        else:
            final_si = min(final_si, aqi)

        results.append(
            {
                "parameter": p,
                "value": conc,
                "unit": UNITS[p],
                "aqi": final_si,
            }
        )

    return results
