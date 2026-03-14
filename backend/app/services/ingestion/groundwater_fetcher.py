"""
Groundwater Level Data Fetcher — data.gov.in CGWB Urban Areas 2018
Resource ID: 9bff5b10-0481-4421-91ad-b9fe18fb7787

Fetches 50 city-level groundwater records with depth-to-water-level ranges
and well-count distributions across 6 depth bands.

Field mapping (API field IDs are extremely long):
  name_of_city_ut                                          → city
  no__of_wells_analysed                                    → wells
  depth_to_water_level__mbgl____min                        → depth_min
  depth_to_water_level__mbgl____max                        → depth_max
  ...in_the_range_of_0_2___no / ____                       → band 0-2m count/%
  ...in_the_range_of_2_5___no / ____                       → band 2-5m count/%
  ...in_the_range_of_5_10___no / ____                      → band 5-10m count/%
  ...in_the_range_of_10_20___no / ____                     → band 10-20m count/%
  ...in_the_range_of_20_40___no / ____                     → band 20-40m count/%
  ...in_the_range_of___40___no / ____                      → band >40m count/%
"""

import json
from typing import Optional

import httpx
from loguru import logger

DATA_GOV_API_KEY = "579b464db66ec23bdd000001bc6f0074ab864acb60a45cfbeb72efdd"
RESOURCE_ID = "9bff5b10-0481-4421-91ad-b9fe18fb7787"
DATA_GOV_BASE = "https://api.data.gov.in/resource"

# Depth band definitions: (suffix_for_no, suffix_for_pct, label, midpoint_m)
DEPTH_BANDS = [
    ("0_2", "0-2 m", 1.0),
    ("2_5", "2-5 m", 3.5),
    ("5_10", "5-10 m", 7.5),
    ("10_20", "10-20 m", 15.0),
    ("20_40", "20-40 m", 30.0),
    ("__40", ">40 m", 50.0),
]

# The horrifically long field name prefixes
_BAND_NO_PREFIX = (
    "number___percentage_of_wells_showing_depth_to_water_level__mbgl__in_the_range_of_"
)
_BAND_NO_SUFFIX = "___no"
_BAND_PCT_SUFFIX = "____"


def _safe_float(val) -> Optional[float]:
    """Parse a value to float, return None for NA/empty/invalid."""
    if val is None or val == "NA" or val == "na" or val == "":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _classify_level(avg_depth: float) -> dict:
    """
    Classify groundwater level by weighted average depth.
    Returns {level, color, description}.
    """
    if avg_depth <= 5.0:
        return {
            "level": "Adequate",
            "color": "#16a34a",  # green-600
            "description": "Shallow water table — adequate groundwater availability",
        }
    elif avg_depth <= 10.0:
        return {
            "level": "Moderate",
            "color": "#ca8a04",  # yellow-600
            "description": "Moderate depth — groundwater accessible but declining",
        }
    elif avg_depth <= 20.0:
        return {
            "level": "Low",
            "color": "#ea580c",  # orange-600
            "description": "Deep water table — limited groundwater availability",
        }
    else:
        return {
            "level": "Critical",
            "color": "#dc2626",  # red-600
            "description": "Very deep water table — critically low groundwater",
        }


def _parse_record(rec: dict) -> Optional[dict]:
    """Parse a single API record into a clean city groundwater dict."""
    city = (rec.get("name_of_city_ut") or "").strip()
    if not city or city.lower() == "total":
        return None

    wells = _safe_float(rec.get("no__of_wells_analysed"))
    depth_min = _safe_float(rec.get("depth_to_water_level__mbgl____min"))
    depth_max = _safe_float(rec.get("depth_to_water_level__mbgl____max"))

    # Parse depth bands
    bands = []
    weighted_sum = 0.0
    total_pct = 0.0

    for suffix, label, midpoint in DEPTH_BANDS:
        no_key = f"{_BAND_NO_PREFIX}{suffix}{_BAND_NO_SUFFIX}"
        pct_key = f"{_BAND_NO_PREFIX}{suffix}{_BAND_PCT_SUFFIX}"

        count = _safe_float(rec.get(no_key)) or 0.0
        pct = _safe_float(rec.get(pct_key)) or 0.0

        bands.append(
            {
                "range": label,
                "count": int(count),
                "percentage": round(pct, 1),
            }
        )

        weighted_sum += pct * midpoint
        total_pct += pct

    # Compute weighted average depth from band distribution
    avg_depth = (weighted_sum / total_pct) if total_pct > 0 else None

    # Fallback: use midpoint of min/max if band data is sparse
    if avg_depth is None or total_pct < 50:
        if depth_min is not None and depth_max is not None:
            avg_depth = (depth_min + depth_max) / 2.0
        elif depth_min is not None:
            avg_depth = depth_min
        elif depth_max is not None:
            avg_depth = depth_max

    if avg_depth is None:
        avg_depth = 0.0

    classification = _classify_level(avg_depth)

    return {
        "city": city,
        "wells_analysed": int(wells) if wells else 0,
        "depth_min_mbgl": round(depth_min, 2) if depth_min is not None else None,
        "depth_max_mbgl": round(depth_max, 2) if depth_max is not None else None,
        "avg_depth_mbgl": round(avg_depth, 2),
        "bands": bands,
        "classification": classification,
    }


async def fetch_groundwater_levels() -> list[dict]:
    """
    Fetch all 50 city groundwater records from data.gov.in.
    Returns list of parsed city dicts.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(
                f"{DATA_GOV_BASE}/{RESOURCE_ID}",
                params={
                    "api-key": DATA_GOV_API_KEY,
                    "format": "json",
                    "offset": 0,
                    "limit": 100,  # Dataset has only 50 records
                },
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"data.gov.in groundwater fetch error: {e}")
            return []

    records = data.get("records", [])
    cities = []

    for rec in records:
        parsed = _parse_record(rec)
        if parsed:
            cities.append(parsed)

    logger.info(f"Groundwater levels: fetched {len(cities)} cities")
    return cities


async def fetch_groundwater_cached(
    redis_client,
    cache_ttl: int = 86400,  # 24 hours — static dataset
) -> list[dict]:
    """Fetch groundwater data with Redis caching."""
    cache_key = "groundwater_levels:all"

    if redis_client:
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                logger.debug("Groundwater levels cache hit")
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis cache read error: {e}")

    cities = await fetch_groundwater_levels()

    if redis_client and cities:
        try:
            await redis_client.setex(cache_key, cache_ttl, json.dumps(cities))
            logger.debug(f"Groundwater levels cached ({len(cities)} cities)")
        except Exception as e:
            logger.warning(f"Redis cache write error: {e}")

    return cities
