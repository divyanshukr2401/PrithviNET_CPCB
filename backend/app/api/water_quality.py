"""Water Quality Monitoring API Endpoints — wired to ClickHouse + PostGIS."""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from datetime import datetime

from app.services.ingestion.clickhouse_writer import ch_writer
from app.services.ingestion.postgres_writer import pg_writer
from app.services.ingestion.water_quality_fetcher import fetch_water_quality_cached
from app.services.ingestion.groundwater_fetcher import fetch_groundwater_cached
from app.core.redis import get_redis

router = APIRouter()


@router.get("/")
async def get_water_quality_summary():
    """Get overall water quality summary for CG rivers."""
    stations = await pg_writer.get_water_stations()
    try:
        client = ch_writer._get_client()
        result = client.query("""
            SELECT count() AS total_readings,
                   countDistinct(station_id) AS active_stations,
                   max(timestamp) AS latest_ts
            FROM water_quality_raw
            WHERE timestamp >= now() - INTERVAL 2 HOUR
        """)
        row = (
            dict(zip(result.column_names, result.result_rows[0]))
            if result.result_rows
            else {}
        )
    except Exception:
        row = {}

    return {
        "summary": "Water quality monitoring active",
        "total_stations": len(stations),
        "active_stations_2h": row.get("active_stations", 0),
        "parameters": [
            "pH",
            "DO",
            "BOD",
            "COD",
            "TSS",
            "Turbidity",
            "Conductivity",
            "Temperature",
            "Nitrates",
            "Phosphates",
        ],
        "rivers": ["Kharun", "Sheonath", "Hasdeo", "Arpa", "Kelo"],
        "last_updated": datetime.utcnow().isoformat(),
    }


@router.get("/stations")
async def get_water_stations(
    district: Optional[str] = Query(None, description="Filter by district/city"),
):
    """Get list of water quality monitoring stations."""
    stations = await pg_writer.get_water_stations(district=district)
    return {
        "stations": stations,
        "total": len(stations),
        "filters": {"district": district},
    }


@router.get("/stations/{station_id}")
async def get_water_station_data(station_id: str):
    """Get water quality data for a specific monitoring station."""
    readings = await ch_writer.query_recent_readings(
        "water_quality_raw",
        station_id,
        id_column="station_id",
        hours=6,
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

    # Average WQI (0-1 scale: 0 = excellent, 1 = very poor)
    wqi_values = [v.get("wqi", 0.5) for v in latest.values()]
    avg_wqi = round(sum(wqi_values) / max(1, len(wqi_values)), 4)

    wqi_category = (
        "Excellent"
        if avg_wqi <= 0.15
        else "Good"
        if avg_wqi <= 0.3
        else "Fair"
        if avg_wqi <= 0.5
        else "Poor"
        if avg_wqi <= 0.7
        else "Very Poor"
    )

    sample = next(iter(latest.values()), {})

    return {
        "station_id": station_id,
        "river_name": sample.get("river_name", ""),
        "city": sample.get("city", ""),
        "location": {
            "lat": sample.get("latitude", 0),
            "lon": sample.get("longitude", 0),
        },
        "parameters": {
            p: {
                "value": round(v.get("value", 0), 3),
                "unit": v.get("unit", ""),
                "wqi": round(v.get("wqi", 50), 1),
            }
            for p, v in latest.items()
        },
        "wqi": {"value": avg_wqi, "category": wqi_category},
        "timestamp": str(sample.get("timestamp", "")),
    }


@router.get("/rivers")
async def get_river_data(
    river: Optional[str] = Query(None, description="River name"),
    hours: int = Query(6, ge=1, le=48),
):
    """Get water quality data grouped by river."""
    try:
        client = ch_writer._get_client()
        if river:
            river_filter = "AND river_name = {river_name:String}"
            query_params = {"river_name": river}
        else:
            river_filter = ""
            query_params = {}
        result = client.query(
            f"""
            SELECT river_name, parameter,
                   avg(value) AS avg_value,
                   min(value) AS min_value,
                   max(value) AS max_value,
                   count() AS readings
            FROM water_quality_raw
            WHERE timestamp >= now() - INTERVAL {hours} HOUR
              AND river_name != ''
              {river_filter}
            GROUP BY river_name, parameter
            ORDER BY river_name, parameter
        """,
            parameters=query_params,
        )
        columns = result.column_names
        rows = [dict(zip(columns, row)) for row in result.result_rows]
    except Exception:
        rows = []

    # Group by river
    rivers: dict[str, list] = {}
    for r in rows:
        rn = r.get("river_name", "Unknown")
        rivers.setdefault(rn, []).append(
            {
                "parameter": r.get("parameter", ""),
                "avg_value": round(r.get("avg_value", 0), 2),
                "min_value": round(r.get("min_value", 0), 2),
                "max_value": round(r.get("max_value", 0), 2),
                "readings": r.get("readings", 0),
            }
        )

    return {"rivers": rivers, "filter": {"river": river, "hours": hours}}


@router.get("/quality-heatmap")
async def get_water_quality_heatmap(
    limit: int = Query(5000, ge=5, le=50000, description="Max records to fetch"),
    state: Optional[str] = Query(None, description="Filter by state name"),
):
    """
    Get water quality heatmap data from data.gov.in CPCB monitoring stations.
    Returns points with lat, lng, intensity (WQI 0-1), station info, and parameters.
    Data source: CPCB Surface Water Quality March 2018.
    """
    try:
        redis = await get_redis()
    except Exception:
        redis = None

    points = await fetch_water_quality_cached(
        redis_client=redis,
        limit=limit,
        state=state,
        cache_ttl=7200,  # 2 hours (static dataset)
    )

    return {
        "source": "data.gov.in CPCB Surface Water Quality 2018",
        "total_points": len(points),
        "filter": {"state": state, "limit": limit},
        "points": points,
    }


@router.get("/groundwater-level")
async def get_groundwater_level(
    city: Optional[str] = Query(
        None, description="Filter by city name (case-insensitive partial match)"
    ),
):
    """
    Get groundwater level data for 50 major Indian cities from CGWB 2018 survey.
    Returns depth-to-water-level ranges, well distribution across depth bands,
    and a qualitative classification (Adequate/Moderate/Low/Critical).
    Source: data.gov.in Ministry of Jal Shakti.
    """
    try:
        redis = await get_redis()
    except Exception:
        redis = None

    all_cities = await fetch_groundwater_cached(redis_client=redis)

    if city:
        q = city.lower().strip()
        filtered = [c for c in all_cities if q in c["city"].lower()]
    else:
        filtered = all_cities

    return {
        "source": "data.gov.in CGWB Urban Groundwater Level 2018",
        "total_cities": len(filtered),
        "filter": {"city": city},
        "cities": filtered,
    }


@router.get("/wqi")
async def get_water_quality_index(
    city: Optional[str] = Query(None, description="City filter"),
    hours: int = Query(6, ge=1, le=48),
):
    """Get Water Quality Index summary for CG stations."""
    try:
        client = ch_writer._get_client()
        if city:
            city_filter = "AND city = {city_name:String}"
            query_params = {"city_name": city}
        else:
            city_filter = ""
            query_params = {}
        result = client.query(
            f"""
            SELECT station_id, city, river_name,
                   avg(wqi) AS avg_wqi,
                   min(wqi) AS min_wqi,
                   count() AS readings
            FROM water_quality_raw
            WHERE timestamp >= now() - INTERVAL {hours} HOUR
              {city_filter}
            GROUP BY station_id, city, river_name
            ORDER BY avg_wqi ASC
        """,
            parameters=query_params,
        )
        columns = result.column_names
        rows = [dict(zip(columns, row)) for row in result.result_rows]
    except Exception:
        rows = []

    return {
        "stations": [
            {
                "station_id": r.get("station_id", ""),
                "city": r.get("city", ""),
                "river_name": r.get("river_name", ""),
                "avg_wqi": round(r.get("avg_wqi", 0), 1),
                "min_wqi": round(r.get("min_wqi", 0), 1),
                "readings": r.get("readings", 0),
            }
            for r in rows
        ],
        "filter": {"city": city, "hours": hours},
    }
