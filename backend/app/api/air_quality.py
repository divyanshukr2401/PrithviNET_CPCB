"""Air Quality Monitoring API Endpoints — wired to ClickHouse + PostGIS."""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from datetime import datetime

from app.services.ingestion.clickhouse_writer import ch_writer
from app.services.ingestion.postgres_writer import pg_writer
from app.services.ingestion.live_simulator import live_simulator
from app.services.ingestion.datagov_fetcher import datagov_fetcher
from app.core.redis import cached

router = APIRouter()

# NAAQS AQI categories
AQI_CATEGORIES = [
    (0, 50, "Good"),
    (51, 100, "Satisfactory"),
    (101, 200, "Moderate"),
    (201, 300, "Poor"),
    (301, 400, "Very Poor"),
    (401, 500, "Severe"),
]


def aqi_category(aqi: int) -> str:
    for lo, hi, cat in AQI_CATEGORIES:
        if lo <= aqi <= hi:
            return cat
    return "Severe" if aqi > 500 else "Good"


@router.get("/")
@cached(ttl_seconds=60, prefix="air_summary")
async def get_air_quality_summary(
    state: Optional[str] = Query(None, description="Filter by state"),
    city: Optional[str] = Query(None, description="Filter by city"),
):
    """Get overall air quality summary — supports All-India with state/city filters."""
    stations = await pg_writer.get_air_stations(city=city, state=state)
    # Get latest readings from ClickHouse — one per station
    try:
        client = ch_writer._get_client()
        state_filter = f"AND state = '{state}'" if state else ""
        city_filter = f"AND city = '{city}'" if city else ""
        result = client.query(f"""
            SELECT station_id, parameter,
                   argMax(value, timestamp) AS latest_value,
                   argMax(aqi, timestamp) AS latest_aqi,
                   max(timestamp) AS latest_ts
            FROM air_quality_raw
            WHERE timestamp >= now() - INTERVAL 2 HOUR
              {state_filter}
              {city_filter}
            GROUP BY station_id, parameter
        """)
        columns = result.column_names
        readings = [dict(zip(columns, row)) for row in result.result_rows]
    except Exception:
        readings = []

    return {
        "summary": "Air quality monitoring active",
        "stations_count": len(stations),
        "parameters": ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3", "NH3", "Pb"],
        "recent_readings_count": len(readings),
        "filters": {"state": state, "city": city},
        "last_updated": datetime.utcnow().isoformat(),
    }


@router.get("/stations")
async def get_stations(
    city: Optional[str] = Query(None, description="Filter by city"),
    state: Optional[str] = Query(None, description="Filter by state"),
    limit: int = Query(100, ge=1, le=1000),
):
    """Get list of air quality monitoring stations from PostGIS."""
    stations = await pg_writer.get_air_stations(city=city, state=state)
    return {
        "stations": stations[:limit],
        "total": len(stations),
        "filters": {"city": city, "state": state},
    }


@router.get("/stations/{station_id}")
async def get_station_data(station_id: str):
    """Get real-time air quality data for a specific station."""
    readings = await ch_writer.query_recent_readings(
        "air_quality_raw",
        station_id,
        id_column="station_id",
        hours=2,
    )
    if not readings:
        raise HTTPException(
            status_code=404, detail=f"No recent data for station {station_id}"
        )

    # Group by parameter, take latest
    latest: dict[str, dict] = {}
    for r in readings:
        p = r.get("parameter", "")
        if p not in latest or r["timestamp"] > latest[p]["timestamp"]:
            latest[p] = r

    # Compute overall AQI = max of sub-indices
    max_aqi = max((v.get("aqi", 0) for v in latest.values()), default=0)
    dominant = max(latest.values(), key=lambda v: v.get("aqi", 0), default={})

    return {
        "station_id": station_id,
        "city": dominant.get("city", ""),
        "location": {
            "lat": dominant.get("latitude", 0),
            "lon": dominant.get("longitude", 0),
        },
        "parameters": {
            p: {
                "value": round(v.get("value", 0), 2),
                "unit": v.get("unit", "ug/m3"),
                "aqi": v.get("aqi", 0),
            }
            for p, v in latest.items()
        },
        "aqi": {"value": max_aqi, "category": aqi_category(max_aqi)},
        "dominant_pollutant": dominant.get("parameter", ""),
        "timestamp": dominant.get("timestamp", datetime.utcnow()).isoformat()
        if hasattr(dominant.get("timestamp", ""), "isoformat")
        else str(dominant.get("timestamp", "")),
    }


@router.get("/aqi")
@cached(ttl_seconds=60, prefix="air_aqi")
async def get_aqi_data(
    city: Optional[str] = Query(None, description="City name"),
    state: Optional[str] = Query(None, description="State name"),
    hours: int = Query(2, ge=1, le=24, description="Lookback hours"),
):
    """Get latest AQI data for a city/state (or all)."""
    try:
        client = ch_writer._get_client()
        city_filter = f"AND city = '{city}'" if city else ""
        state_filter = f"AND state = '{state}'" if state else ""
        result = client.query(f"""
            SELECT city,
                   max(aqi) AS max_aqi,
                   argMax(parameter, aqi) AS dominant_pollutant,
                   max(timestamp) AS latest_ts
            FROM air_quality_raw
            WHERE timestamp >= now() - INTERVAL {hours} HOUR
              {city_filter}
              {state_filter}
            GROUP BY city
            ORDER BY max_aqi DESC
        """)
        columns = result.column_names
        rows = [dict(zip(columns, row)) for row in result.result_rows]
    except Exception:
        rows = []

    return {
        "filter": {"city": city, "state": state, "hours": hours},
        "cities": [
            {
                "city": r.get("city", ""),
                "aqi": r.get("max_aqi", 0),
                "category": aqi_category(r.get("max_aqi", 0)),
                "dominant_pollutant": r.get("dominant_pollutant", ""),
                "latest_timestamp": str(r.get("latest_ts", "")),
            }
            for r in rows
        ],
    }


@router.get("/historical")
@cached(ttl_seconds=300, prefix="air_historical")
async def get_historical_data(
    station_id: str,
    parameter: str = Query("PM2.5", description="Parameter to retrieve"),
    days: int = Query(7, ge=1, le=30, description="Number of days"),
):
    """Get historical air quality data for analysis."""
    series = await ch_writer.query_historical_series(
        "air_quality_raw",
        station_id,
        parameter,
        days=days,
    )
    if not series:
        return {
            "station_id": station_id,
            "parameter": parameter,
            "days": days,
            "data": [],
            "statistics": {},
        }

    values = [s["value"] for s in series]
    import numpy as np

    arr = np.array(values)

    return {
        "station_id": station_id,
        "parameter": parameter,
        "days": days,
        "data_points": len(series),
        "data": series[:5000],  # cap for response size
        "statistics": {
            "mean": round(float(np.mean(arr)), 2),
            "median": round(float(np.median(arr)), 2),
            "std": round(float(np.std(arr)), 2),
            "min": round(float(np.min(arr)), 2),
            "max": round(float(np.max(arr)), 2),
            "p95": round(float(np.percentile(arr, 95)), 2),
        },
    }


# ---------------------------------------------------------------------------
# LIVE SIMULATED DATA (from historical-pattern-based simulator)
# ---------------------------------------------------------------------------


@router.get("/live")
async def get_live_aqi(
    station_id: Optional[str] = Query(None, description="Specific station ID"),
    city: Optional[str] = Query(None, description="Filter by city"),
    include_pollutants: bool = Query(
        False, description="Include individual pollutant readings"
    ),
):
    """
    Get latest simulated live AQI readings.

    These readings are generated in real-time from statistical profiles
    built from 2024/2025 CPCB historical data. They represent realistic
    AQI values that follow the same diurnal, seasonal, and station-specific
    patterns observed in real data.

    Set include_pollutants=true to also get individual pollutant readings
    (PM2.5, PM10, NO2, SO2, CO, O3, NH3, Pb) alongside the AQI.
    """
    if not live_simulator.ready:
        raise HTTPException(
            status_code=503,
            detail="Live simulator not ready — historical data may not be loaded yet",
        )

    readings = live_simulator.get_latest(
        station_id=station_id,
        include_pollutants=include_pollutants,
    )

    # Filter by city if requested
    if city:
        readings = [r for r in readings if r.get("city", "").lower() == city.lower()]

    # Enrich with AQI category
    enriched = []
    for r in readings:
        aqi_val = r.get("aqi", 0)
        enriched.append(
            {
                **r,
                "category": aqi_category(aqi_val),
            }
        )

    return {
        "source": "historical_pattern_simulator",
        "simulator_status": "active" if live_simulator.ready else "loading",
        "total_stations": live_simulator.station_count,
        "readings_count": len(enriched),
        "filter": {
            "station_id": station_id,
            "city": city,
            "include_pollutants": include_pollutants,
        },
        "readings": enriched,
    }


@router.get("/live/real/{station_id}")
async def get_real_station_data(station_id: str):
    """
    Fetch real-time air quality data from data.gov.in for a specific station.

    This endpoint is called on-demand when a user clicks a station on the map.
    It queries the CPCB Real-Time AQI resource, finds the nearest real monitoring
    station by city + lat/lon, and returns actual pollutant readings.

    Falls back to simulated data if no real data is available for this station.
    """
    from app.core.config import settings

    # Look up station city from simulator's station metadata
    meta = live_simulator._station_meta.get(station_id)
    if not meta:
        # Try to get it from the latest cache
        cached_reading = live_simulator._latest_cache.get(station_id)
        if cached_reading:
            meta = {
                "city": cached_reading.get("city", ""),
                "latitude": cached_reading.get("latitude", 0.0),
                "longitude": cached_reading.get("longitude", 0.0),
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Station {station_id} not found in simulator metadata",
            )

    city = meta.get("city", "")
    lat = meta.get("latitude", 0.0)
    lon = meta.get("longitude", 0.0)

    if not city:
        raise HTTPException(
            status_code=404,
            detail=f"No city found for station {station_id}",
        )

    # Check if API key is configured
    if not settings.DATA_GOV_API_KEY:
        # No API key — return simulated data with flag
        return _simulated_fallback(station_id)

    # Fetch real data from data.gov.in (with Redis caching inside)
    result = await datagov_fetcher.fetch_for_station(
        station_id=station_id,
        city=city,
        latitude=lat,
        longitude=lon,
    )

    if not result:
        # API returned no data for this city — fall back to simulator
        return _simulated_fallback(station_id)

    # Format response
    aqi_reading = result.get("aqi_reading", {})
    pollutant_readings = result.get("pollutant_readings", [])

    return {
        "source": "data.gov.in",
        "quality_flag": "real",
        "station_id": station_id,
        "api_station_name": result.get("api_station_name", ""),
        "city": aqi_reading.get("city", city),
        "last_update": result.get("last_update", ""),
        "aqi": {
            "value": aqi_reading.get("aqi", 0),
            "category": aqi_category(aqi_reading.get("aqi", 0)),
        },
        "dominant_pollutant": result.get("dominant_pollutant", ""),
        "location": {
            "lat": aqi_reading.get("latitude", lat),
            "lon": aqi_reading.get("longitude", lon),
        },
        "pollutants": {
            r["parameter"]: {
                "value": r["value"],
                "unit": r["unit"],
                "aqi": r["aqi"],
            }
            for r in pollutant_readings
        },
        "all_readings": [aqi_reading] + pollutant_readings,
    }


def _simulated_fallback(station_id: str) -> dict:
    """Return simulated data as fallback when real data is unavailable."""
    readings = live_simulator.get_latest(station_id=station_id, include_pollutants=True)
    if not readings:
        raise HTTPException(
            status_code=404,
            detail=f"No data available for station {station_id}",
        )

    aqi_reading = next((r for r in readings if r.get("parameter") == "AQI"), {})
    pollutant_readings = [r for r in readings if r.get("parameter") != "AQI"]

    return {
        "source": "historical_pattern_simulator",
        "quality_flag": "simulated",
        "station_id": station_id,
        "api_station_name": None,
        "city": aqi_reading.get("city", ""),
        "last_update": aqi_reading.get("timestamp", ""),
        "aqi": {
            "value": aqi_reading.get("aqi", 0),
            "category": aqi_category(aqi_reading.get("aqi", 0)),
        },
        "dominant_pollutant": "",
        "location": {
            "lat": aqi_reading.get("latitude", 0),
            "lon": aqi_reading.get("longitude", 0),
        },
        "pollutants": {
            r["parameter"]: {
                "value": r["value"],
                "unit": r.get("unit", "µg/m³"),
                "aqi": r.get("aqi", 0),
            }
            for r in pollutant_readings
        },
        "all_readings": readings,
    }


@router.get("/live/stats")
async def get_live_simulator_stats():
    """Get live simulator status and statistics."""
    readings = live_simulator.get_latest()
    aqi_values = [r.get("aqi", 0) for r in readings if r.get("aqi", 0) > 0]

    stats = {}
    if aqi_values:
        import numpy as np

        arr = np.array(aqi_values)
        stats = {
            "mean_aqi": round(float(np.mean(arr)), 1),
            "median_aqi": round(float(np.median(arr)), 1),
            "min_aqi": int(np.min(arr)),
            "max_aqi": int(np.max(arr)),
            "std_aqi": round(float(np.std(arr)), 1),
        }
        # Category distribution
        categories = {}
        for v in aqi_values:
            cat = aqi_category(int(v))
            categories[cat] = categories.get(cat, 0) + 1
        stats["category_distribution"] = categories

    return {
        "simulator_ready": live_simulator.ready,
        "total_stations": live_simulator.station_count,
        "cached_readings": len(readings),
        "statistics": stats,
    }
