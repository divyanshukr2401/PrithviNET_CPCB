"""Environmental Noise Monitoring API Endpoints — wired to ClickHouse + PostGIS."""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from datetime import datetime

from app.services.ingestion.clickhouse_writer import ch_writer
from app.services.ingestion.postgres_writer import pg_writer

router = APIRouter()


@router.get("/")
async def get_noise_summary():
    """Get overall environmental noise monitoring summary."""
    stations = await pg_writer.get_noise_stations()
    try:
        client = ch_writer._get_client()
        result = client.query("""
            SELECT city,
                   avg(value) AS avg_leq,
                   max(value) AS max_leq,
                   countIf(is_exceedance = 1) AS exceedances,
                   count() AS readings
            FROM noise_raw
            WHERE metric = 'Leq'
              AND timestamp >= now() - INTERVAL 2 HOUR
            GROUP BY city
            ORDER BY avg_leq DESC
        """)
        columns = result.column_names
        city_data = [dict(zip(columns, row)) for row in result.result_rows]
    except Exception:
        city_data = []

    return {
        "summary": "Noise monitoring active",
        "total_stations": len(stations),
        "monitoring_zones": ["Industrial", "Commercial", "Residential", "Silence"],
        "standards": "CPCB Noise Standards 2000",
        "cities": [
            {
                "city": c.get("city", ""),
                "avg_leq_dba": round(c.get("avg_leq", 0), 1),
                "max_leq_dba": round(c.get("max_leq", 0), 1),
                "exceedances_2h": c.get("exceedances", 0),
            }
            for c in city_data
        ],
        "last_updated": datetime.utcnow().isoformat(),
    }


@router.get("/stations")
async def get_noise_stations(
    city: Optional[str] = Query(None, description="Filter by city"),
):
    """Get list of noise monitoring stations."""
    stations = await pg_writer.get_noise_stations(city=city)
    return {
        "stations": stations,
        "total": len(stations),
        "filters": {"city": city},
    }


@router.get("/stations/{station_id}")
async def get_noise_station_data(station_id: str):
    """Get noise level data for a specific station."""
    readings = await ch_writer.query_recent_readings(
        "noise_raw", station_id, id_column="station_id", hours=1,
    )
    if not readings:
        raise HTTPException(status_code=404, detail=f"No recent data for station {station_id}")

    # Group by metric, take latest
    latest: dict[str, dict] = {}
    for r in readings:
        m = r.get("metric", "")
        if m not in latest or r["timestamp"] > latest[m]["timestamp"]:
            latest[m] = r

    sample = next(iter(latest.values()), {})
    zone = sample.get("zone", "commercial")
    day_limit = sample.get("day_limit", 65)
    night_limit = sample.get("night_limit", 55)

    leq_val = latest.get("Leq", {}).get("value", 0)
    hour_now = datetime.utcnow().hour
    is_night = hour_now < 6 or hour_now >= 22
    limit = night_limit if is_night else day_limit
    exceedance_db = max(0, leq_val - limit)

    return {
        "station_id": station_id,
        "city": sample.get("city", ""),
        "zone": zone,
        "location": {
            "lat": sample.get("latitude", 0),
            "lon": sample.get("longitude", 0),
        },
        "measurements": {
            m: {"value": round(v.get("value", 0), 1), "unit": "dB(A)"}
            for m, v in latest.items()
        },
        "limits": {"day": day_limit, "night": night_limit},
        "compliance": {
            "status": "Non-Compliant" if exceedance_db > 0 else "Compliant",
            "exceedance_db": round(exceedance_db, 1),
            "period": "night" if is_night else "day",
        },
        "timestamp": str(sample.get("timestamp", "")),
    }


@router.get("/historical")
async def get_noise_historical(
    station_id: str,
    metric: str = Query("Leq", description="Noise metric"),
    days: int = Query(7, ge=1, le=30),
):
    """Get historical noise data for a station."""
    try:
        client = ch_writer._get_client()
        result = client.query(f"""
            SELECT toStartOfHour(timestamp) AS hour,
                   avg(value) AS avg_value,
                   max(value) AS max_value,
                   min(value) AS min_value,
                   countIf(is_exceedance = 1) AS exceedances
            FROM noise_raw
            WHERE station_id = '{station_id}'
              AND metric = '{metric}'
              AND timestamp >= now() - INTERVAL {days} DAY
            GROUP BY hour
            ORDER BY hour ASC
        """)
        columns = result.column_names
        rows = [dict(zip(columns, row)) for row in result.result_rows]
    except Exception:
        rows = []

    return {
        "station_id": station_id,
        "metric": metric,
        "days": days,
        "hourly_data": [
            {
                "hour": str(r.get("hour", "")),
                "avg": round(r.get("avg_value", 0), 1),
                "max": round(r.get("max_value", 0), 1),
                "min": round(r.get("min_value", 0), 1),
                "exceedances": r.get("exceedances", 0),
            }
            for r in rows
        ],
        "data_points": len(rows),
    }


@router.get("/standards")
async def get_noise_standards():
    """Get CPCB noise level standards for different zones."""
    return {
        "standards": {
            "Industrial": {"day_limit": 75, "night_limit": 70, "unit": "dB(A)"},
            "Commercial": {"day_limit": 65, "night_limit": 55, "unit": "dB(A)"},
            "Residential": {"day_limit": 55, "night_limit": 45, "unit": "dB(A)"},
            "Silence": {"day_limit": 50, "night_limit": 40, "unit": "dB(A)"},
        },
        "day_hours": "6:00 AM - 10:00 PM",
        "night_hours": "10:00 PM - 6:00 AM",
        "reference": "CPCB Noise Pollution (Regulation and Control) Rules, 2000",
    }
