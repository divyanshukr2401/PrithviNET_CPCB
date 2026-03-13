"""
PRITHVINET AQI-to-Individual-Pollutant Decomposition Engine
============================================================

The CPCB historical XLSX files provide only composite AQI values, NOT
individual pollutant concentrations.  This script reverse-engineers those
composite AQI values into realistic per-pollutant readings (PM2.5, PM10,
NO2, SO2, CO, O3, NH3, Pb) using:

  1. The official CPCB/NAQI breakpoint table (sub-index ↔ concentration)
  2. City-specific dominant-pollutant probability profiles (e.g., Bhilai →
     higher SO2/PM10 from steel plant; Korba → higher SO2 from coal power)
  3. Seasonal (month) and diurnal (hour-of-day) adjustments
  4. Inter-pollutant correlations (PM2.5/PM10 co-vary, NO2/CO traffic link)
  5. Controlled random variation via Beta distributions

Algorithm per AQI row:
  a) Pick a *dominant pollutant* (weighted random based on city/season/hour)
  b) Set dominant pollutant's sub-index = AQI value
  c) For each remaining pollutant, sample sub-index from Beta(α, β) scaled to
     [0, AQI], with α/β chosen so the expected ratio to AQI is city-realistic
  d) Apply correlation adjustments (PM2.5 and PM10 track together, etc.)
  e) Reverse-lookup each sub-index → concentration via CPCB breakpoints
  f) Insert 8 new rows per original AQI row into ClickHouse

Output:
  ~180K × 8 = ~1.45M new rows in air_quality_raw with parameter ∈
  {PM2.5, PM10, NO2, SO2, CO, O3, NH3, Pb}, value = concentration,
  aqi = sub-index for that pollutant.

Usage:
  python scripts/decompose_aqi_to_pollutants.py                  # process all
  python scripts/decompose_aqi_to_pollutants.py --dry-run        # count only
  python scripts/decompose_aqi_to_pollutants.py --station site_5652  # one station
  python scripts/decompose_aqi_to_pollutants.py --verify         # run stats check after
"""

from __future__ import annotations

import argparse
import math
import random
import sys
import time
from datetime import datetime
from typing import Optional

import numpy as np

# ---------------------------------------------------------------------------
# CPCB NAQI Breakpoint Table (official)
# Each entry: (AQI_lo, AQI_hi, Conc_lo, Conc_hi)
# For AQI 401-500 (Hazardous), we define upper bounds for interpolation.
# ---------------------------------------------------------------------------

POLLUTANTS = ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3", "NH3", "Pb"]

# Units per pollutant
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

# Breakpoints: list of (AQI_lo, AQI_hi, Conc_lo, Conc_hi) per pollutant
# Source: CPCB National Air Quality Index (NAQI) standard
BREAKPOINTS: dict[str, list[tuple[int, int, float, float]]] = {
    "PM2.5": [
        (0, 50, 0.0, 30.0),
        (51, 100, 31.0, 60.0),
        (101, 200, 61.0, 90.0),
        (201, 300, 91.0, 120.0),
        (301, 400, 121.0, 250.0),
        (401, 500, 250.0, 380.0),  # extrapolated upper bound
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
    """
    Reverse CPCB breakpoint lookup: given a sub-index value (0-500),
    return the corresponding pollutant concentration.

    Formula:
      Conc = ((SI - AQI_lo) / (AQI_hi - AQI_lo)) * (Conc_hi - Conc_lo) + Conc_lo
    """
    si = max(0.0, min(500.0, sub_index))
    bps = BREAKPOINTS[pollutant]

    # Find the matching breakpoint range
    for aqi_lo, aqi_hi, conc_lo, conc_hi in bps:
        if aqi_lo <= si <= aqi_hi:
            if aqi_hi == aqi_lo:
                return conc_lo
            frac = (si - aqi_lo) / (aqi_hi - aqi_lo)
            return conc_lo + frac * (conc_hi - conc_lo)

    # Above 500 → use last breakpoint extrapolation
    aqi_lo, aqi_hi, conc_lo, conc_hi = bps[-1]
    frac = (si - aqi_lo) / (aqi_hi - aqi_lo) if aqi_hi != aqi_lo else 1.0
    return conc_lo + frac * (conc_hi - conc_lo)


def concentration_to_sub_index(conc: float, pollutant: str) -> float:
    """
    Forward CPCB breakpoint: concentration → sub-index.
    Used for verification.
    """
    bps = BREAKPOINTS[pollutant]
    for aqi_lo, aqi_hi, conc_lo, conc_hi in bps:
        if conc_lo <= conc <= conc_hi:
            if conc_hi == conc_lo:
                return float(aqi_lo)
            frac = (conc - conc_lo) / (conc_hi - conc_lo)
            return aqi_lo + frac * (aqi_hi - aqi_lo)
    # Above max → extrapolate from last breakpoint
    aqi_lo, aqi_hi, conc_lo, conc_hi = bps[-1]
    if conc_hi == conc_lo:
        return float(aqi_hi)
    frac = (conc - conc_lo) / (conc_hi - conc_lo)
    return aqi_lo + frac * (aqi_hi - aqi_lo)


# ---------------------------------------------------------------------------
# City-Specific Dominant Pollutant Probability Profiles
# ---------------------------------------------------------------------------
# For each city, define the probability that each pollutant is the "dominant"
# one (i.e., the pollutant whose sub-index = the overall AQI).
# These are based on real-world knowledge of CG cities:
#   - Raipur: urban traffic → PM2.5 dominant, especially winter
#   - Bhilai: steel plant → SO2 + PM10 elevated
#   - Korba: coal power → SO2 dominant, PM10 from mining
#   - Bilaspur: urban + cement → PM2.5/PM10
#   - Mining towns (Chhal, Kunjemura, Milupara, Tumidih): PM10 dominant
#
# Each city has seasonal overrides (winter vs monsoon vs summer).
# ---------------------------------------------------------------------------


# Season classification
def _get_season(month: int) -> str:
    """Return season name for a month (1-12)."""
    if month in (11, 12, 1, 2):
        return "winter"
    elif month in (6, 7, 8, 9):
        return "monsoon"
    elif month in (3, 4, 5):
        return "summer"
    else:  # Oct
        return "post_monsoon"


# Base dominant-pollutant probability profiles per city category
# Keys are pollutant names, values are relative weights (will be normalized)
# Format: {season: {pollutant: weight}}

CITY_PROFILES: dict[str, dict[str, dict[str, float]]] = {
    # ---------------------------------------------------------------
    # Raipur: state capital, urban traffic, some nearby industry
    # ---------------------------------------------------------------
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
    # ---------------------------------------------------------------
    # Bhilai: Bhilai Steel Plant (BSP) — heavy SO2, PM10, CO
    # ---------------------------------------------------------------
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
    # ---------------------------------------------------------------
    # Korba: Coal power hub (NTPC, CSEB, BALCO) — SO2, PM10
    # ---------------------------------------------------------------
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
    # ---------------------------------------------------------------
    # Bilaspur: urban + cement + rice mills — PM2.5/PM10 dominant
    # ---------------------------------------------------------------
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
    # ---------------------------------------------------------------
    # Mining towns: Chhal, Kunjemura, Milupara, Tumidih
    # PM10 strongly dominant from open-pit mining dust
    # ---------------------------------------------------------------
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

# Map known CPCB city names → profile key
CITY_PROFILE_MAP: dict[str, str] = {
    "Raipur": "Raipur",
    "Bhilai": "Bhilai",
    "Korba": "Korba",
    "Bilaspur": "Bilaspur",
    # Mining/industrial towns → mining profile
    "Chhal": "mining_default",
    "Kunjemura": "mining_default",
    "Milupara": "mining_default",
    "Tumidih": "mining_default",
}


def get_dominant_weights(city: str, month: int, hour: int) -> dict[str, float]:
    """
    Get pollutant dominance weights for a given city, month, and hour.
    Applies diurnal adjustments on top of seasonal base.
    """
    profile_key = CITY_PROFILE_MAP.get(city, "Raipur")  # default to urban
    season = _get_season(month)
    base = CITY_PROFILES[profile_key][season].copy()

    # Diurnal adjustments:
    # Morning rush (7-10): boost NO2, CO (traffic)
    # Afternoon (12-16): boost O3 (photochemical)
    # Evening rush (17-20): boost NO2, CO
    # Night (22-5): boost PM2.5 (inversion trapping)
    if 7 <= hour <= 10:
        base["NO2"] *= 1.5
        base["CO"] *= 1.4
    elif 12 <= hour <= 16:
        base["O3"] *= 1.8
        base["NO2"] *= 0.8  # O3 consumes NO2
    elif 17 <= hour <= 20:
        base["NO2"] *= 1.4
        base["CO"] *= 1.3
    elif hour >= 22 or hour <= 5:
        base["PM2.5"] *= 1.3
        base["PM10"] *= 1.1

    # Normalize to sum = 1.0
    total = sum(base.values())
    return {k: v / total for k, v in base.items()}


# ---------------------------------------------------------------------------
# Sub-index ratio profiles
# For non-dominant pollutants, what fraction of the AQI do they typically
# contribute?  This controls the "spread" of sub-indices.
# ---------------------------------------------------------------------------

# Expected sub-index ratio (relative to AQI) per pollutant per city type
# Used as the mean of a Beta distribution
SUB_INDEX_RATIO: dict[str, dict[str, float]] = {
    # Urban (Raipur, Bilaspur)
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
    # Industrial/Steel (Bhilai)
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
    # Coal/Power (Korba)
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
    # Mining (Chhal, Kunjemura, etc.)
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


# ---------------------------------------------------------------------------
# Correlation groups — pollutants that should co-vary
# ---------------------------------------------------------------------------
# When PM2.5 is high, PM10 should also be high (PM2.5 is a subset of PM10).
# When NO2 is high (traffic), CO should also be high.
# These correlation pairs ensure consistency.

CORRELATION_PAIRS = [
    # (pollutant_A, pollutant_B, min_ratio_A/B, max_ratio_A/B)
    # PM2.5 is always ≤ PM10 in concentration; sub-index can be either way.
    # But physically PM2.5 conc ~ 40-70% of PM10 conc.
    ("PM2.5", "PM10", 0.30, 0.80),  # PM2.5_conc / PM10_conc ratio
    # NO2 and CO from traffic: when one is high, the other is too.
    # No strict ratio, but we make their sub-indices move together.
]


# ---------------------------------------------------------------------------
# Main Decomposition Function
# ---------------------------------------------------------------------------


def decompose_aqi(
    aqi: int,
    city: str,
    month: int,
    hour: int,
    rng: np.random.Generator,
) -> list[dict]:
    """
    Decompose a single composite AQI value into 8 pollutant readings.

    Returns a list of 8 dicts, each with keys:
      parameter, value (concentration), unit, aqi (sub-index)
    """
    if aqi <= 0:
        # AQI of 0 → all pollutants at 0
        return [
            {"parameter": p, "value": 0.0, "unit": UNITS[p], "aqi": 0}
            for p in POLLUTANTS
        ]

    aqi = min(500, max(1, aqi))

    # Step 1: Pick the dominant pollutant
    weights = get_dominant_weights(city, month, hour)
    pollutant_names = list(weights.keys())
    pollutant_probs = np.array([weights[p] for p in pollutant_names])
    pollutant_probs /= pollutant_probs.sum()  # ensure normalization

    dominant = rng.choice(pollutant_names, p=pollutant_probs)

    # Step 2: Generate sub-indices for all pollutants
    ratio_key = CITY_RATIO_MAP.get(city, "urban")
    ratio_profile = SUB_INDEX_RATIO[ratio_key]

    sub_indices: dict[str, float] = {}

    for p in POLLUTANTS:
        if p == dominant:
            # Dominant pollutant: sub-index = AQI (by definition of NAQI)
            sub_indices[p] = float(aqi)
        else:
            # Non-dominant: sample sub-index as fraction of AQI
            mean_ratio = ratio_profile[p]
            # Clamp mean_ratio away from 0 and 1 for Beta stability
            mean_ratio = max(0.05, min(0.95, mean_ratio))

            # Beta distribution parameterized by mean and concentration (kappa).
            # Higher kappa → tighter spread around the mean.
            kappa = 12.0  # moderate spread
            alpha = mean_ratio * kappa
            beta_param = (1 - mean_ratio) * kappa

            ratio = rng.beta(alpha, beta_param)
            # Sub-index must be < AQI (otherwise this pollutant would be dominant)
            raw_si = ratio * aqi
            # Enforce: non-dominant sub-index < AQI (with small tolerance)
            raw_si = min(raw_si, aqi - 1.0) if aqi > 1 else 0.0
            raw_si = max(0.0, raw_si)
            sub_indices[p] = raw_si

    # Step 3: Apply PM2.5/PM10 concentration consistency
    # PM2.5 concentration should be ~30-80% of PM10 concentration
    # We'll adjust sub-indices to ensure physical consistency
    pm25_conc = sub_index_to_concentration(sub_indices["PM2.5"], "PM2.5")
    pm10_conc = sub_index_to_concentration(sub_indices["PM10"], "PM10")

    if pm10_conc > 0 and pm25_conc > pm10_conc:
        # PM2.5 can't exceed PM10 — reduce PM2.5 sub-index
        target_pm25_conc = pm10_conc * rng.uniform(0.40, 0.70)
        new_pm25_si = concentration_to_sub_index(target_pm25_conc, "PM2.5")

        if dominant == "PM2.5":
            # PM2.5 was dominant but physically can't be higher than PM10.
            # Promote PM10 to be the new dominant: set PM10 sub-index = AQI.
            sub_indices["PM10"] = float(aqi)
            sub_indices["PM2.5"] = min(new_pm25_si, aqi - 1.0)
            dominant = "PM10"
        else:
            sub_indices["PM2.5"] = min(new_pm25_si, aqi - 1.0)

    # Step 4: Apply NO2/CO correlation (traffic-linked)
    # If NO2 sub-index is high, CO should be somewhat correlated
    no2_si = sub_indices["NO2"]
    co_si = sub_indices["CO"]
    if no2_si > 0 and co_si > 0:
        # Blend CO toward NO2's relative level
        no2_ratio = no2_si / aqi if aqi > 0 else 0.5
        co_ratio = co_si / aqi if aqi > 0 else 0.5
        # Nudge CO toward NO2's ratio (mild correlation, r≈0.4)
        corr_strength = 0.4
        blended_co_ratio = co_ratio * (1 - corr_strength) + no2_ratio * corr_strength
        blended_co_si = blended_co_ratio * aqi
        if dominant != "CO":
            blended_co_si = min(blended_co_si, aqi - 1.0)
        sub_indices["CO"] = max(0.0, blended_co_si)

    # Step 5: Convert sub-indices to concentrations
    results: list[dict] = []
    for p in POLLUTANTS:
        si = sub_indices[p]
        conc = sub_index_to_concentration(si, p)

        # Add small realistic noise (±5%) — but NOT to the dominant pollutant,
        # whose sub-index must stay = AQI for consistency
        if p != dominant:
            noise = rng.uniform(-0.05, 0.05)
            conc = max(0.0, conc * (1 + noise))
        # Ensure concentration is never negative
        conc = max(0.0, conc)

        # Round concentrations appropriately
        if p == "CO":
            conc = round(conc, 2)  # mg/m³ — 2 decimal places
        elif p == "Pb":
            conc = round(conc, 3)  # µg/m³ — 3 decimal places
        else:
            conc = round(conc, 1)  # µg/m³ — 1 decimal place

        # Recalculate sub-index from rounded concentration for consistency
        final_si = int(round(concentration_to_sub_index(conc, p)))
        final_si = max(0, min(500, final_si))

        # For the dominant pollutant, force sub-index = AQI exactly
        # For non-dominant, ensure sub-index doesn't exceed AQI
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


# ---------------------------------------------------------------------------
# ClickHouse I/O
# ---------------------------------------------------------------------------


def get_clickhouse_client():
    """Connect to ClickHouse."""
    import clickhouse_connect

    return clickhouse_connect.get_client(
        host="localhost",
        port=8123,
        username="admin",
        password="prithvinet_secure_2024",
        database="prithvinet",
    )


def fetch_aqi_rows(client, station_filter: Optional[str] = None) -> list[tuple]:
    """
    Fetch all existing AQI rows from air_quality_raw.
    Returns: list of (station_id, timestamp, value, city)
    """
    where = "WHERE parameter = 'AQI' AND value > 0 AND value <= 500"
    if station_filter:
        where += f" AND station_id = '{station_filter}'"

    query = f"""
        SELECT station_id, timestamp, value, city
        FROM air_quality_raw
        {where}
        ORDER BY station_id, timestamp
    """
    result = client.query(query)
    return result.result_rows


def check_existing_pollutant_data(client) -> int:
    """Check how many non-AQI pollutant rows already exist."""
    query = """
        SELECT count()
        FROM air_quality_raw
        WHERE parameter != 'AQI'
    """
    result = client.query(query)
    return result.result_rows[0][0]


def delete_existing_pollutant_data(client):
    """Remove previously decomposed pollutant data (to allow re-run)."""
    print("Deleting existing non-AQI pollutant data...")
    client.command("""
        ALTER TABLE air_quality_raw
        DELETE WHERE parameter != 'AQI'
    """)
    # Wait for mutation to complete
    import time

    for i in range(60):
        result = client.query("""
            SELECT count()
            FROM system.mutations
            WHERE database = 'prithvinet'
              AND table = 'air_quality_raw'
              AND is_done = 0
        """)
        pending = result.result_rows[0][0]
        if pending == 0:
            break
        time.sleep(1)
    print("Existing pollutant data deleted.")


def bulk_insert(client, rows: list[list], batch_label: str = ""):
    """Insert rows into air_quality_raw."""
    columns = [
        "station_id",
        "timestamp",
        "parameter",
        "value",
        "unit",
        "aqi",
        "city",
        "latitude",
        "longitude",
        "zone",
        "is_anomaly",
        "anomaly_type",
        "quality_flag",
    ]
    client.insert("air_quality_raw", rows, column_names=columns)


# ---------------------------------------------------------------------------
# Main Processing Loop
# ---------------------------------------------------------------------------


def run(
    station_filter: Optional[str],
    dry_run: bool,
    verify: bool,
    batch_size: int,
    seed: int,
    force: bool,
):
    """Main decomposition pipeline."""
    rng = np.random.default_rng(seed)

    # Connect (always — we need to read AQI data even for dry-run)
    client = None
    try:
        client = get_clickhouse_client()
        print("Connected to ClickHouse")
    except Exception as e:
        print(f"ClickHouse connection failed: {e}")
        return

    if not dry_run:
        # Check for existing pollutant data
        existing = check_existing_pollutant_data(client)
        if existing > 0:
            if force:
                delete_existing_pollutant_data(client)
            else:
                print(f"Found {existing:,} existing non-AQI pollutant rows.")
                print("Use --force to delete and regenerate, or --dry-run to preview.")
                client.close()
                return

    # Fetch AQI rows
    print("Fetching AQI rows from ClickHouse...")
    aqi_rows = fetch_aqi_rows(client, station_filter)
    total_aqi = len(aqi_rows)
    print(f"Found {total_aqi:,} AQI rows to decompose")

    if total_aqi == 0:
        print("No AQI data found. Run preprocess_cpcb_historical.py first.")
        if client:
            client.close()
        return

    # Process in batches
    total_generated = 0
    batch_buffer: list[list] = []
    t0 = time.time()
    last_report = t0

    for i, (station_id, timestamp, aqi_value, city) in enumerate(aqi_rows):
        aqi_int = int(round(aqi_value))

        # Extract month and hour from timestamp
        if isinstance(timestamp, datetime):
            month = timestamp.month
            hour = timestamp.hour
        else:
            # string timestamp
            dt = datetime.fromisoformat(str(timestamp))
            month = dt.month
            hour = dt.hour
            timestamp = dt

        # Decompose
        pollutant_readings = decompose_aqi(aqi_int, city, month, hour, rng)

        for reading in pollutant_readings:
            row = [
                station_id,
                timestamp,
                reading["parameter"],
                reading["value"],
                reading["unit"],
                reading["aqi"],
                city,
                0.0,  # latitude — placeholder
                0.0,  # longitude — placeholder
                "unknown",
                0,  # is_anomaly
                "",  # anomaly_type
                "valid",
            ]
            batch_buffer.append(row)

        total_generated += len(pollutant_readings)

        # Flush batch
        if len(batch_buffer) >= batch_size and not dry_run:
            try:
                bulk_insert(client, batch_buffer, f"batch at row {i + 1}")
            except Exception as e:
                print(f"  [ERROR] Batch insert failed at row {i + 1}: {e}")
            batch_buffer.clear()

        # Progress report every 10 seconds
        now = time.time()
        if now - last_report >= 10:
            elapsed = now - t0
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (total_aqi - i - 1) / rate if rate > 0 else 0
            print(
                f"  Progress: {i + 1:,}/{total_aqi:,} AQI rows "
                f"({100 * (i + 1) / total_aqi:.1f}%) | "
                f"{total_generated:,} pollutant rows | "
                f"{rate:.0f} rows/s | ETA {eta:.0f}s"
            )
            last_report = now

    # Flush remaining
    if batch_buffer and not dry_run:
        try:
            bulk_insert(client, batch_buffer, "final batch")
        except Exception as e:
            print(f"  [ERROR] Final batch insert failed: {e}")
        batch_buffer.clear()

    elapsed = time.time() - t0
    print()
    print("=" * 70)
    print(f"AQI rows processed:      {total_aqi:,}")
    print(f"Pollutant rows generated: {total_generated:,}")
    print(f"Time elapsed:            {elapsed:.1f}s")
    if not dry_run:
        print(f"Rows inserted into ClickHouse air_quality_raw")
    else:
        print(f"(dry-run — nothing inserted)")
    print("=" * 70)

    # Verification
    if verify and not dry_run and client:
        run_verification(client)

    if client:
        client.close()


# ---------------------------------------------------------------------------
# Verification / Statistical Checks
# ---------------------------------------------------------------------------


def run_verification(client):
    """Run statistical checks on the decomposed data."""
    print()
    print("=" * 70)
    print("VERIFICATION")
    print("=" * 70)

    # 1. Total row counts by parameter
    print("\n--- Row counts by parameter ---")
    result = client.query("""
        SELECT parameter, count() AS cnt, round(avg(value), 2) AS avg_val,
               round(min(value), 2) AS min_val, round(max(value), 2) AS max_val,
               round(avg(aqi), 1) AS avg_si
        FROM air_quality_raw
        GROUP BY parameter
        ORDER BY parameter
    """)
    print(
        f"  {'Parameter':<10} {'Count':>10} {'Avg Value':>12} {'Min':>10} {'Max':>10} {'Avg SI':>10}"
    )
    for row in result.result_rows:
        p, cnt, avg_v, min_v, max_v, avg_si = row
        print(f"  {p:<10} {cnt:>10,} {avg_v:>12} {min_v:>10} {max_v:>10} {avg_si:>10}")

    # 2. Check PM2.5/PM10 concentration ratio (should be 0.3-0.8)
    print("\n--- PM2.5/PM10 concentration ratio per station ---")
    result = client.query("""
        SELECT
            a.station_id,
            round(avg(a.value / b.value), 3) AS pm_ratio,
            count() AS pairs
        FROM air_quality_raw a
        INNER JOIN air_quality_raw b
            ON a.station_id = b.station_id
            AND a.timestamp = b.timestamp
            AND a.parameter = 'PM2.5'
            AND b.parameter = 'PM10'
            AND b.value > 0
        GROUP BY a.station_id
        ORDER BY a.station_id
    """)
    for row in result.result_rows:
        sid, ratio, pairs = row
        status = "OK" if 0.2 <= ratio <= 0.85 else "WARN"
        print(f"  {sid}: PM2.5/PM10 = {ratio:.3f}  ({pairs:,} pairs)  [{status}]")

    # 3. Dominant pollutant distribution per city
    print("\n--- Dominant pollutant (max sub-index) per city ---")
    result = client.query("""
        SELECT
            city,
            parameter,
            count() AS times_dominant
        FROM (
            SELECT
                station_id,
                timestamp,
                city,
                parameter,
                aqi,
                max(aqi) OVER (PARTITION BY station_id, timestamp) AS max_aqi
            FROM air_quality_raw
            WHERE parameter != 'AQI'
        )
        WHERE aqi = max_aqi
        GROUP BY city, parameter
        ORDER BY city, times_dominant DESC
    """)
    current_city = ""
    for row in result.result_rows:
        city, param, cnt = row
        if city != current_city:
            print(f"\n  {city}:")
            current_city = city
        print(f"    {param}: {cnt:,}")

    # 4. Verify AQI = max(sub-indices) holds approximately
    print("\n--- AQI vs max(sub-index) consistency ---")
    result = client.query("""
        SELECT
            station_id,
            round(avg(abs(orig_aqi - max_si)), 2) AS mean_abs_error,
            round(max(abs(orig_aqi - max_si)), 2) AS max_abs_error,
            count() AS samples
        FROM (
            SELECT
                a.station_id,
                a.timestamp,
                a.value AS orig_aqi,
                max(b.aqi) AS max_si
            FROM air_quality_raw a
            INNER JOIN air_quality_raw b
                ON a.station_id = b.station_id
                AND a.timestamp = b.timestamp
                AND b.parameter != 'AQI'
            WHERE a.parameter = 'AQI'
            GROUP BY a.station_id, a.timestamp, a.value
        )
        GROUP BY station_id
        ORDER BY station_id
    """)
    print(f"  {'Station':<12} {'MAE':>8} {'Max Err':>10} {'Samples':>10}")
    for row in result.result_rows:
        sid, mae, max_err, samples = row
        status = "OK" if mae < 10 else "WARN"
        print(f"  {sid:<12} {mae:>8} {max_err:>10} {samples:>10}  [{status}]")

    print("\nVerification complete.")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Decompose CPCB composite AQI → 8 individual pollutant concentrations"
    )
    parser.add_argument(
        "--station",
        type=str,
        default=None,
        help="Process only this station (e.g., site_5652)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Count and preview without inserting"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run statistical verification after decomposition",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100_000,
        help="Rows per ClickHouse insert batch (default: 100000)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete existing pollutant data and regenerate",
    )
    args = parser.parse_args()

    run(
        station_filter=args.station,
        dry_run=args.dry_run,
        verify=args.verify,
        batch_size=args.batch_size,
        seed=args.seed,
        force=args.force,
    )


if __name__ == "__main__":
    main()
