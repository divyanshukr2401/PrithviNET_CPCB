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


@router.get("/live")
async def get_noise_live():
    """
    Get latest noise readings for ALL 70 NANMN stations.
    Returns each station's current Leq/Lmax/Lmin, coordinates, zone,
    compliance status, and CPCB limits — ready for map rendering.
    """
    try:
        client = ch_writer._get_client()
        # Get the latest Leq reading per station (within last 30 min)
        result = client.query("""
            SELECT
                nr.station_id,
                nr.city,
                nr.latitude,
                nr.longitude,
                nr.zone,
                nr.day_limit,
                nr.night_limit,
                nr.value AS leq,
                nr.is_exceedance,
                nr.timestamp
            FROM noise_raw nr
            INNER JOIN (
                SELECT station_id, max(timestamp) AS max_ts
                FROM noise_raw
                WHERE metric = 'Leq'
                  AND timestamp >= now() - INTERVAL 30 MINUTE
                GROUP BY station_id
            ) latest ON nr.station_id = latest.station_id
                    AND nr.timestamp = latest.max_ts
                    AND nr.metric = 'Leq'
            ORDER BY nr.station_id
        """)
        leq_cols = result.column_names
        leq_rows = [dict(zip(leq_cols, row)) for row in result.result_rows]

        # Also get latest Lmax and Lmin per station
        result2 = client.query("""
            SELECT
                nr.station_id,
                nr.metric,
                nr.value
            FROM noise_raw nr
            INNER JOIN (
                SELECT station_id, metric, max(timestamp) AS max_ts
                FROM noise_raw
                WHERE metric IN ('Lmax', 'Lmin')
                  AND timestamp >= now() - INTERVAL 30 MINUTE
                GROUP BY station_id, metric
            ) latest ON nr.station_id = latest.station_id
                    AND nr.metric = latest.metric
                    AND nr.timestamp = latest.max_ts
            ORDER BY nr.station_id
        """)
        extra_cols = result2.column_names
        extra_rows = [dict(zip(extra_cols, row)) for row in result2.result_rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ClickHouse query failed: {e}")

    # Build Lmax/Lmin lookup
    lmax_lmin: dict[str, dict[str, float]] = {}
    for r in extra_rows:
        sid = r["station_id"]
        if sid not in lmax_lmin:
            lmax_lmin[sid] = {}
        lmax_lmin[sid][r["metric"]] = round(r["value"], 1)

    # Get station names from Postgres
    pg_stations = await pg_writer.get_noise_stations()
    name_map = {s["station_id"]: s["station_name"] for s in pg_stations}

    # Determine current period
    hour_now = datetime.now().hour
    is_night = hour_now < 6 or hour_now >= 22

    stations = []
    for row in leq_rows:
        sid = row["station_id"]
        leq = round(row["leq"], 1)
        day_limit = row["day_limit"]
        night_limit = row["night_limit"]
        limit = night_limit if is_night else day_limit
        exceedance_db = round(max(0, leq - limit), 1)

        extras = lmax_lmin.get(sid, {})
        stations.append(
            {
                "station_id": sid,
                "station_name": name_map.get(sid, sid),
                "city": row["city"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "zone": row["zone"],
                "leq": leq,
                "lmax": extras.get("Lmax", leq + 8),
                "lmin": extras.get("Lmin", leq - 8),
                "day_limit": day_limit,
                "night_limit": night_limit,
                "active_limit": limit,
                "is_exceedance": exceedance_db > 0,
                "exceedance_db": exceedance_db,
                "period": "night" if is_night else "day",
                "timestamp": str(row["timestamp"]),
            }
        )

    return {
        "total_stations": len(stations),
        "period": "night" if is_night else "day",
        "exceedance_count": sum(1 for s in stations if s["is_exceedance"]),
        "compliant_count": sum(1 for s in stations if not s["is_exceedance"]),
        "stations": stations,
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
        "noise_raw",
        station_id,
        id_column="station_id",
        hours=1,
    )
    if not readings:
        raise HTTPException(
            status_code=404, detail=f"No recent data for station {station_id}"
        )

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
    hour_now = datetime.now().hour
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


@router.get("/historical/{station_id}")
async def get_noise_historical(
    station_id: str,
    hours: int = Query(24, ge=1, le=72, description="Hours of history"),
):
    """Get historical noise data for a station — hourly aggregates."""
    try:
        client = ch_writer._get_client()
        result = client.query(
            """
            SELECT
                toStartOfHour(timestamp) AS hour,
                metric,
                round(avg(value), 1) AS avg_value,
                round(max(value), 1) AS max_value,
                round(min(value), 1) AS min_value,
                countIf(is_exceedance = 1) AS exceedances,
                any(day_limit) AS day_limit,
                any(night_limit) AS night_limit
            FROM noise_raw
            WHERE station_id = {sid:String}
              AND timestamp >= now() - INTERVAL {hrs:UInt32} HOUR
            GROUP BY hour, metric
            ORDER BY hour ASC, metric ASC
            """,
            parameters={"sid": station_id, "hrs": hours},
        )
        columns = result.column_names
        rows = [dict(zip(columns, row)) for row in result.result_rows]
    except Exception:
        rows = []

    # Reshape: group by hour, nest metrics
    hourly: dict[str, dict] = {}
    for r in rows:
        h = str(r["hour"])
        if h not in hourly:
            hourly[h] = {
                "hour": h,
                "day_limit": r.get("day_limit", 65),
                "night_limit": r.get("night_limit", 55),
            }
        metric = r["metric"]
        hourly[h][f"{metric}_avg"] = r["avg_value"]
        hourly[h][f"{metric}_max"] = r["max_value"]
        hourly[h][f"{metric}_min"] = r["min_value"]
        hourly[h]["exceedances"] = hourly[h].get("exceedances", 0) + r["exceedances"]

    return {
        "station_id": station_id,
        "hours": hours,
        "data": list(hourly.values()),
        "data_points": len(hourly),
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
