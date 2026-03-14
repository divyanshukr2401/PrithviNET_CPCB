"""
Water Quality Data Fetcher — data.gov.in CPCB/CWC Surface Water Quality
Resource ID: 19697d76-442e-4d76-aeae-13f8a17c91e1

Fetches ~378K water quality monitoring records with real lat/lng coordinates
and computes a composite Water Quality Index for heatmap visualization.

Strategy: fetch per-state to guarantee uniform coverage across all Indian
states/UTs. Without this, a global limit=5000 only sees ~1.3% of the dataset
and misses entire states (Rajasthan, Punjab, Goa, Haryana, etc.).

Actual field names from the API (case-sensitive):
  Latitude, Longitude, Station_Name, State, District, Basin, Sub_Basin,
  bod, tcol_mpn, fcol_mpn, ec_gen, no3_n, ph_fld, ph_gen, temp, tds,
  d_o, do_sat_, turb, ss, ... (many may be 'NA')
"""

import asyncio
import json
from typing import Optional

import httpx
from loguru import logger

DATA_GOV_API_KEY = "579b464db66ec23bdd000001bc6f0074ab864acb60a45cfbeb72efdd"
RESOURCE_ID = "19697d76-442e-4d76-aeae-13f8a17c91e1"
DATA_GOV_BASE = "https://api.data.gov.in/resource"

# All Indian states/UTs that have water quality data in this dataset.
# This list drives the per-state fetch loop.
INDIAN_STATES = [
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chandigarh",
    "Chhattisgarh",
    "Delhi",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jammu & Kashmir",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Lakshadweep",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Puducherry",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
]

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


def _parse_record(
    rec: dict,
    seen_coords: set[tuple[float, float]],
) -> Optional[dict]:
    """
    Parse a single API record into a heatmap point.
    Returns None if the record is invalid, duplicate, or missing WQI data.
    """
    lat = _safe_float(rec.get("Latitude"))
    lng = _safe_float(rec.get("Longitude"))

    # Skip records without valid coordinates
    if lat is None or lng is None:
        return None
    # Basic India bounds check
    if not (6.0 <= lat <= 38.0 and 68.0 <= lng <= 98.0):
        return None

    wqi = _compute_wqi(rec)
    if wqi is None:
        return None

    # Deduplicate by approximate coords (same station, different dates)
    coord_key = (round(lat, 3), round(lng, 3))
    if coord_key in seen_coords:
        return None
    seen_coords.add(coord_key)

    # Extract display parameters for tooltip
    params_dict = {}
    for field, display_name in DISPLAY_PARAMS.items():
        v = _safe_float(rec.get(field))
        if v is not None:
            params_dict[display_name] = round(v, 2)

    return {
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


async def _fetch_state_points(
    client: httpx.AsyncClient,
    state: str,
    per_state_limit: int,
    seen_coords: set[tuple[float, float]],
) -> list[dict]:
    """
    Fetch water quality points for a single state.
    Pages through the API with filters[State]=<state>.
    """
    points: list[dict] = []
    offset = 0
    batch_size = 500  # API max per page
    fetched = 0

    while fetched < per_state_limit:
        req_params = {
            "api-key": DATA_GOV_API_KEY,
            "format": "json",
            "offset": offset,
            "limit": batch_size,
            "filters[State]": state,
        }

        try:
            resp = await client.get(f"{DATA_GOV_BASE}/{RESOURCE_ID}", params=req_params)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning(
                f"data.gov.in fetch error for {state} (offset={offset}): {e}"
            )
            break

        records = data.get("records", [])
        if not records:
            break

        for rec in records:
            point = _parse_record(rec, seen_coords)
            if point:
                points.append(point)

        fetched += len(records)
        offset += batch_size

        if len(records) < batch_size:
            break  # No more data for this state

    return points


async def fetch_water_quality_heatmap(
    limit: int = 5000,
    state: Optional[str] = None,
) -> list[dict]:
    """
    Fetch water quality data from data.gov.in and return heatmap-ready points.

    If state is specified, fetches only that state (up to `limit` records).
    If state is None, fetches ALL states using per-state iteration to guarantee
    uniform geographic coverage across India.

    Returns list of dicts:
        {lat, lng, intensity, station_name, state, district, wqi, parameters}
    """
    all_points: list[dict] = []
    seen_coords: set[tuple[float, float]] = set()

    async with httpx.AsyncClient(timeout=30.0) as client:
        if state:
            # Single-state fetch (used for filtered queries)
            all_points = await _fetch_state_points(client, state, limit, seen_coords)
        else:
            # Per-state fetch for full national coverage
            # Budget: distribute limit across states, with a minimum floor
            per_state_limit = max(500, limit // len(INDIAN_STATES))
            total_fetched = 0

            # Fetch states concurrently in small batches to avoid overwhelming the API
            # Process 5 states at a time
            for i in range(0, len(INDIAN_STATES), 5):
                batch_states = INDIAN_STATES[i : i + 5]
                tasks = [
                    _fetch_state_points(client, s, per_state_limit, seen_coords)
                    for s in batch_states
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for s, result in zip(batch_states, results):
                    if isinstance(result, Exception):
                        logger.warning(f"Failed to fetch {s}: {result}")
                        continue
                    state_points = result
                    all_points.extend(state_points)
                    total_fetched += len(state_points)
                    if state_points:
                        logger.debug(f"  {s}: {len(state_points)} unique stations")

            logger.info(
                f"Water quality per-state fetch complete: "
                f"{len(INDIAN_STATES)} states queried, "
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
    cache_key = f"water_quality_heatmap:v2:{state or 'all_states'}"

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
