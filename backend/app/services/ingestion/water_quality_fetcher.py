"""
Water Quality Data Fetcher — data.gov.in CPCB/CWC Surface Water Quality
Resource ID: 19697d76-442e-4d76-aeae-13f8a17c91e1

Fetches ~378K water quality monitoring records with real lat/lng coordinates
and computes a composite Water Quality Index for heatmap visualization.

Actual field names from the API (case-sensitive):
  Latitude, Longitude, Station_Name, State, District, Basin, Sub_Basin,
  bod, tcol_mpn, fcol_mpn, ec_gen, no3_n, ph_fld, ph_gen, temp, tds,
  d_o, do_sat_, turb, ss, ... (many may be 'NA')
"""

import json
from typing import Optional

import httpx
from loguru import logger

DATA_GOV_API_KEY = "579b464db66ec23bdd000001bc6f0074ab864acb60a45cfbeb72efdd"
RESOURCE_ID = "19697d76-442e-4d76-aeae-13f8a17c91e1"
DATA_GOV_BASE = "https://api.data.gov.in/resource"

# WQI parameters: (api_field, BIS_limit, display_name)
# Higher ratio to BIS limit = worse quality
WQI_PARAMS = [
    ("bod", 3.0, "BOD (mg/L)"),  # BOD limit 3 mg/L
    ("tcol_mpn", 5000.0, "Total Coliform"),  # MPN/100ml
    ("fcol_mpn", 2500.0, "Fecal Coliform"),  # MPN/100ml
    ("ec_gen", 2250.0, "Conductivity (µS/cm)"),  # µmhos/cm
    ("no3_n", 45.0, "Nitrate-N (mg/L)"),  # mg/L
    ("tds", 2000.0, "TDS (mg/L)"),  # mg/L
    ("turb", 25.0, "Turbidity (NTU)"),  # NTU
]

# Extra display parameters (for tooltips)
DISPLAY_PARAMS = {
    "ph_fld": "pH (field)",
    "ph_gen": "pH (general)",
    "temp": "Temperature (C)",
    "d_o": "DO (mg/L)",
    "do_sat_": "DO Saturation (%)",
    "bod": "BOD (mg/L)",
    "cod": "COD (mg/L)",
    "tcol_mpn": "Total Coliform (MPN)",
    "fcol_mpn": "Fecal Coliform (MPN)",
    "ec_gen": "Conductivity (µS/cm)",
    "no3_n": "Nitrate-N (mg/L)",
    "tds": "TDS (mg/L)",
    "turb": "Turbidity (NTU)",
    "ss": "Susp. Solids (mg/L)",
    "cl": "Chloride (mg/L)",
    "so4": "Sulphate (mg/L)",
    "har_total": "Total Hardness",
}


def _safe_float(val) -> Optional[float]:
    """Parse a value to float, return None on failure. Treats 'NA' as None."""
    if val is None or val == "NA" or val == "na" or val == "":
        return None
    try:
        v = float(val)
        return v if v >= 0 else None
    except (ValueError, TypeError):
        return None


def _compute_wqi(record: dict) -> Optional[float]:
    """
    Compute a 0-1 composite WQI from available parameters.
    0 = excellent water quality, 1 = very poor.
    Uses ratio to BIS limit, capped and normalized.
    """
    scores = []
    for field, limit, _ in WQI_PARAMS:
        val = _safe_float(record.get(field))
        if val is not None and limit > 0:
            ratio = min(val / limit, 3.0)  # Cap at 3x BIS limit
            scores.append(ratio / 3.0)  # Normalize to 0-1

    if not scores:
        return None

    return round(sum(scores) / len(scores), 4)


async def fetch_water_quality_heatmap(
    limit: int = 5000,
    state: Optional[str] = None,
) -> list[dict]:
    """
    Fetch water quality data from data.gov.in and return heatmap-ready points.

    Returns list of dicts:
        {lat, lng, intensity, station_name, state, district, wqi, parameters}
    """
    all_points: list[dict] = []
    seen_coords: set[tuple[float, float]] = set()
    offset = 0
    batch_size = min(limit, 500)  # API max per page
    fetched = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        while fetched < limit:
            req_params = {
                "api-key": DATA_GOV_API_KEY,
                "format": "json",
                "offset": offset,
                "limit": batch_size,
            }
            if state:
                req_params["filters[State]"] = state

            try:
                resp = await client.get(
                    f"{DATA_GOV_BASE}/{RESOURCE_ID}", params=req_params
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.error(f"data.gov.in fetch error (offset={offset}): {e}")
                break

            records = data.get("records", [])
            if not records:
                break

            for rec in records:
                lat = _safe_float(rec.get("Latitude"))
                lng = _safe_float(rec.get("Longitude"))

                # Skip records without valid coordinates
                if lat is None or lng is None:
                    continue
                # Basic India bounds check
                if not (6.0 <= lat <= 38.0 and 68.0 <= lng <= 98.0):
                    continue

                wqi = _compute_wqi(rec)
                if wqi is None:
                    continue

                # Deduplicate by approximate coords (same station, different dates)
                coord_key = (round(lat, 3), round(lng, 3))
                if coord_key in seen_coords:
                    continue
                seen_coords.add(coord_key)

                # Extract display parameters for tooltip
                params_dict = {}
                for field, display_name in DISPLAY_PARAMS.items():
                    v = _safe_float(rec.get(field))
                    if v is not None:
                        params_dict[display_name] = round(v, 2)

                all_points.append(
                    {
                        "lat": lat,
                        "lng": lng,
                        "intensity": wqi,
                        "station_name": rec.get("Station_Name", "Unknown"),
                        "state": rec.get("State", ""),
                        "district": rec.get("District", ""),
                        "station_code": "",
                        "wqi": wqi,
                        "parameters": params_dict,
                    }
                )

            fetched += len(records)
            offset += batch_size

            if len(records) < batch_size:
                break  # No more data

    logger.info(
        f"Water quality heatmap: fetched {fetched} records, "
        f"{len(all_points)} unique station points with coordinates + WQI"
    )

    return all_points


async def fetch_water_quality_cached(
    redis_client,
    limit: int = 5000,
    state: Optional[str] = None,
    cache_ttl: int = 3600,
) -> list[dict]:
    """
    Fetch water quality data with Redis caching.
    Cache TTL defaults to 1 hour (data is historical, doesn't change).
    """
    cache_key = f"water_quality_heatmap:{state or 'all'}:{limit}"

    # Try cache first
    if redis_client:
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                logger.debug(f"Water quality heatmap cache hit: {cache_key}")
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis cache read error: {e}")

    # Fetch from API
    points = await fetch_water_quality_heatmap(limit=limit, state=state)

    # Store in cache
    if redis_client and points:
        try:
            await redis_client.setex(cache_key, cache_ttl, json.dumps(points))
            logger.debug(
                f"Water quality heatmap cached: {cache_key} ({len(points)} points)"
            )
        except Exception as e:
            logger.warning(f"Redis cache write error: {e}")

    return points
