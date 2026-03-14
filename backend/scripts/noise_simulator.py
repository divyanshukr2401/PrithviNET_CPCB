"""
Noise Data Simulator — Generates realistic ambient noise data for 70 NANMN stations.

Produces 5-minute interval readings with:
  - Leq  (Equivalent Continuous Sound Level — the main metric)
  - Lmax (Maximum sound level in the interval)
  - Lmin (Minimum / background sound level)

Realism is achieved through:
  1. Zone-specific baselines (Industrial > Commercial > Residential > Silence)
  2. Diurnal sine-wave curves (peaks at morning/evening rush, dips at 2-4 AM)
  3. Gaussian noise for natural variation
  4. Random spike events (honking, sirens, machinery bursts)
  5. Station-specific offsets so nearby stations differ slightly

Usage:
  # Backfill 48 hours of history:
  python -m backend.scripts.noise_simulator --backfill-hours 48

  # Or import and call from app startup for continuous simulation
"""

import math
import random
import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import Optional

import asyncpg
import clickhouse_connect
from loguru import logger


# ── Zone baselines (dB(A)) ──────────────────────────────────────────────────
# These represent the "typical daytime average" for each zone type.
ZONE_BASELINES = {
    "industrial": 68.0,  # Factories, heavy machinery
    "commercial": 62.0,  # Markets, traffic junctions
    "residential": 50.0,  # Housing areas
    "silence": 44.0,  # Hospitals, schools, courts
}

# CPCB limits
ZONE_LIMITS = {
    "industrial": {"day": 75, "night": 70},
    "commercial": {"day": 65, "night": 55},
    "residential": {"day": 55, "night": 45},
    "silence": {"day": 50, "night": 40},
}

# Night drop: how much quieter the zone gets at night (dB reduction)
ZONE_NIGHT_DROP = {
    "industrial": 6.0,  # Factories may run 24/7 but less activity
    "commercial": 14.0,  # Markets close, traffic drops sharply
    "residential": 10.0,  # People sleep
    "silence": 8.0,  # Already quiet, slight further drop
}


def _station_offset(station_id: str) -> float:
    """
    Deterministic per-station offset (-3 to +3 dB) so stations in the same
    zone/city don't produce identical readings.
    """
    h = int(hashlib.md5(station_id.encode()).hexdigest()[:8], 16)
    return (h % 600 - 300) / 100.0  # range: -3.0 to +2.99


def _diurnal_factor(hour: float) -> float:
    """
    Returns a multiplier (roughly -1.0 to +1.0) representing time-of-day
    activity level. Uses a dual-peak sine model:
      - Morning rush peak at ~9 AM
      - Evening rush peak at ~6 PM
      - Deepest quiet at ~3 AM
    """
    # Morning peak (centered at 9.0, width ~4 hours)
    morning = 0.6 * math.exp(-((hour - 9.0) ** 2) / 8.0)
    # Evening peak (centered at 18.0, width ~4 hours)
    evening = 0.8 * math.exp(-((hour - 18.0) ** 2) / 8.0)
    # Midday plateau (centered at 13.5)
    midday = 0.4 * math.exp(-((hour - 13.5) ** 2) / 18.0)
    # Night dip (sine trough centered at 3 AM)
    night_dip = -0.7 * math.exp(-((hour - 3.0) ** 2) / 6.0)

    return morning + evening + midday + night_dip


def generate_noise_reading(
    station_id: str,
    zone_type: str,
    timestamp: datetime,
) -> dict:
    """
    Generate a single 5-minute noise reading for a station.
    Returns dict with Leq, Lmax, Lmin values and metadata.
    """
    zone = zone_type.lower()
    baseline = ZONE_BASELINES.get(zone, 55.0)
    night_drop = ZONE_NIGHT_DROP.get(zone, 10.0)
    limits = ZONE_LIMITS.get(zone, {"day": 65, "night": 55})

    # Fractional hour (e.g., 14.5 = 2:30 PM)
    hour = timestamp.hour + timestamp.minute / 60.0

    # Is it night time? (10 PM - 6 AM)
    is_night = hour >= 22.0 or hour < 6.0

    # Diurnal curve: scale the factor by the night_drop range
    diurnal = _diurnal_factor(hour)
    diurnal_db = diurnal * (night_drop / 2.0)

    # Station-specific offset
    offset = _station_offset(station_id)

    # Gaussian noise (natural variation)
    noise = random.gauss(0, 1.8)

    # Random spike events (~8% probability during day, ~3% at night)
    spike_prob = 0.03 if is_night else 0.08
    spike = 0.0
    if random.random() < spike_prob:
        spike = random.uniform(4.0, 12.0)  # +4 to +12 dB spike

    # Compute Leq
    leq = baseline + diurnal_db + offset + noise + spike
    if is_night:
        leq -= night_drop * 0.5  # Additional night reduction

    # Clamp to realistic range
    leq = max(30.0, min(95.0, leq))

    # Lmax: Leq + 5-15 dB (peaks within the 5-min window)
    lmax = leq + random.uniform(5.0, 15.0)
    lmax = min(110.0, lmax)

    # Lmin: Leq - 5-12 dB (quiet moments within the 5-min window)
    lmin = leq - random.uniform(5.0, 12.0)
    lmin = max(25.0, lmin)

    # Determine compliance
    limit = limits["night"] if is_night else limits["day"]
    is_exceedance = 1 if leq > limit else 0
    is_anomaly = 1 if spike > 8.0 else 0

    return {
        "leq": round(leq, 1),
        "lmax": round(lmax, 1),
        "lmin": round(lmin, 1),
        "is_exceedance": is_exceedance,
        "is_anomaly": is_anomaly,
        "anomaly_type": "spike_event" if is_anomaly else "",
        "day_limit": limits["day"],
        "night_limit": limits["night"],
    }


async def get_stations_from_postgres() -> list[dict]:
    """Fetch all noise stations from Postgres."""
    conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="admin",
        password="prithvinet_secure_2024",
        database="prithvinet_geo",
    )
    try:
        rows = await conn.fetch("""
            SELECT station_id, station_name, zone_type, city, state,
                   ST_Y(geom) AS latitude, ST_X(geom) AS longitude,
                   day_limit, night_limit
            FROM noise_stations
            ORDER BY station_id
        """)
        return [dict(r) for r in rows]
    finally:
        await conn.close()


def get_clickhouse_client():
    """Get ClickHouse client."""
    return clickhouse_connect.get_client(
        host="localhost",
        port=8123,
        username="admin",
        password="prithvinet_secure_2024",
        database="prithvinet",
    )


def insert_noise_batch(client, rows: list[list]):
    """
    Insert a batch of noise readings into ClickHouse.
    Each row: [station_id, timestamp, metric, value, city, lat, lng, zone,
               day_limit, night_limit, is_exceedance, is_anomaly, anomaly_type, quality_flag]
    """
    client.insert(
        "noise_raw",
        rows,
        column_names=[
            "station_id",
            "timestamp",
            "metric",
            "value",
            "city",
            "latitude",
            "longitude",
            "zone",
            "day_limit",
            "night_limit",
            "is_exceedance",
            "is_anomaly",
            "anomaly_type",
            "quality_flag",
        ],
    )


async def backfill(hours: int = 48):
    """
    Generate and insert historical noise data for the past N hours
    at 5-minute intervals for all 70 NANMN stations.
    """
    logger.info(f"Starting noise backfill: {hours} hours for 70 NANMN stations...")
    stations = await get_stations_from_postgres()
    logger.info(f"Loaded {len(stations)} stations from Postgres")

    client = get_clickhouse_client()

    # Clear any existing noise data
    client.command("TRUNCATE TABLE noise_raw")
    logger.info("Cleared existing noise_raw data")

    now = datetime.now()
    start = now - timedelta(hours=hours)

    total_rows = 0
    batch: list[list] = []
    batch_size = 10000  # Flush every 10K rows

    # Generate readings: every 5 minutes for every station
    current = start
    interval = timedelta(minutes=5)

    while current <= now:
        for station in stations:
            reading = generate_noise_reading(
                station["station_id"],
                station["zone_type"],
                current,
            )

            # Each reading produces 3 metrics: Leq, Lmax, Lmin
            for metric, value in [
                ("Leq", reading["leq"]),
                ("Lmax", reading["lmax"]),
                ("Lmin", reading["lmin"]),
            ]:
                batch.append(
                    [
                        station["station_id"],
                        current,
                        metric,
                        value,
                        station["city"],
                        float(station["latitude"]),
                        float(station["longitude"]),
                        station["zone_type"],
                        float(reading["day_limit"]),
                        float(reading["night_limit"]),
                        reading["is_exceedance"],
                        reading["is_anomaly"],
                        reading["anomaly_type"],
                        "simulated",
                    ]
                )

            if len(batch) >= batch_size:
                insert_noise_batch(client, batch)
                total_rows += len(batch)
                batch = []

        current += interval

    # Flush remaining
    if batch:
        insert_noise_batch(client, batch)
        total_rows += len(batch)

    logger.info(
        f"Noise backfill complete: {total_rows:,} rows inserted "
        f"({len(stations)} stations × {hours}h × 12/hr × 3 metrics)"
    )

    # Verify
    result = client.query("SELECT count() FROM noise_raw")
    count = result.result_rows[0][0]
    logger.info(f"Verified: {count:,} rows in noise_raw")

    client.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NANMN Noise Data Simulator")
    parser.add_argument(
        "--backfill-hours",
        type=int,
        default=48,
        help="Hours of historical data to generate (default: 48)",
    )
    args = parser.parse_args()

    asyncio.run(backfill(args.backfill_hours))
