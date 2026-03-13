#!/usr/bin/env python3
"""
Geocode 587 CPCB stations using OpenStreetMap Nominatim.

Strategy:
1. Extract unique (city, state) pairs from cpcb_stations_raw.json
2. Geocode each city using Nominatim (free, no API key)
3. Update PostgreSQL air_stations table with coordinates
4. Generate ClickHouse UPDATE statements too
5. Cache results to avoid re-geocoding on re-runs

Usage:
    python geocode_stations.py                # Geocode all cities
    python geocode_stations.py --dry-run      # Preview without DB writes
    python geocode_stations.py --cache-only   # Only use cached results, no API calls
"""

import asyncio
import json
import time
import argparse
import sys
from pathlib import Path

import httpx
import asyncpg

# ── Paths ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "processed"
STATIONS_JSON = DATA_DIR / "cpcb_stations_raw.json"
CACHE_FILE = DATA_DIR / "geocode_cache.json"

# ── DB Config ──────────────────────────────────────────────────────────
PG_DSN = "postgresql://admin:prithvinet_secure_2024@localhost:5432/prithvinet_geo"

# ── Nominatim Config ───────────────────────────────────────────────────
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_HEADERS = {
    "User-Agent": "PRITHVINET-Hackathon/1.0 (environmental monitoring research project)"
}
# Nominatim rate limit: 1 request per second
RATE_LIMIT_SECONDS = 1.1


def load_stations() -> list[dict]:
    """Load station list from CPCB JSON."""
    with open(STATIONS_JSON) as f:
        data = json.load(f)

    stations_by_city = data["dropdown"]["stations"]
    cities_by_state = data["dropdown"]["cities"]

    # Build state lookup: city -> state
    city_to_state = {}
    for state_name, city_list in cities_by_state.items():
        for city_obj in city_list:
            city_to_state[city_obj["label"]] = state_name

    all_stations = []
    for city_name, station_list in stations_by_city.items():
        state = city_to_state.get(city_name, "Unknown")
        for s in station_list:
            all_stations.append(
                {
                    "station_id": s["value"],
                    "label": s["label"],
                    "city": city_name,
                    "state": state,
                }
            )
    return all_stations


def get_unique_cities(stations: list[dict]) -> list[tuple[str, str]]:
    """Get unique (city, state) pairs."""
    seen = set()
    result = []
    for s in stations:
        key = (s["city"], s["state"])
        if key not in seen:
            seen.add(key)
            result.append(key)
    return sorted(result)


def load_cache() -> dict:
    """Load geocode cache from disk."""
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}


def save_cache(cache: dict):
    """Save geocode cache to disk."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


async def geocode_city(
    client: httpx.AsyncClient,
    city: str,
    state: str,
    cache: dict,
) -> tuple[float, float] | None:
    """Geocode a city using Nominatim. Returns (lat, lon) or None."""
    cache_key = f"{city}|{state}"
    if cache_key in cache:
        return tuple(cache[cache_key]) if cache[cache_key] else None

    # Try progressively broader queries
    queries = [
        f"{city}, {state}, India",
        f"{city}, India",
    ]

    for query in queries:
        try:
            resp = await client.get(
                NOMINATIM_URL,
                params={
                    "q": query,
                    "format": "json",
                    "limit": 1,
                    "countrycodes": "in",
                },
                headers=NOMINATIM_HEADERS,
                timeout=15.0,
            )
            if resp.status_code == 200:
                results = resp.json()
                if results:
                    lat = float(results[0]["lat"])
                    lon = float(results[0]["lon"])
                    cache[cache_key] = [lat, lon]
                    return (lat, lon)
        except Exception as e:
            print(f"  ERROR geocoding '{query}': {e}")

        await asyncio.sleep(RATE_LIMIT_SECONDS)

    # Not found
    cache[cache_key] = None
    return None


async def geocode_all_cities(
    cities: list[tuple[str, str]],
    cache: dict,
    cache_only: bool = False,
) -> dict[tuple[str, str], tuple[float, float]]:
    """Geocode all cities, returning {(city, state): (lat, lon)}."""
    results = {}
    to_geocode = []

    # Check cache first
    for city, state in cities:
        cache_key = f"{city}|{state}"
        if cache_key in cache and cache[cache_key] is not None:
            results[(city, state)] = tuple(cache[cache_key])
        elif cache_key in cache and cache[cache_key] is None:
            pass  # Previously failed, skip
        else:
            to_geocode.append((city, state))

    print(
        f"Cache hits: {len(results)}, Cache misses (failed): {len(cities) - len(results) - len(to_geocode)}, To geocode: {len(to_geocode)}"
    )

    if cache_only:
        print("--cache-only mode, skipping API calls")
        return results

    if not to_geocode:
        print("All cities already geocoded!")
        return results

    async with httpx.AsyncClient() as client:
        for i, (city, state) in enumerate(to_geocode):
            coords = await geocode_city(client, city, state, cache)
            if coords:
                results[(city, state)] = coords
                status = f"({coords[0]:.4f}, {coords[1]:.4f})"
            else:
                status = "FAILED"
            print(f"  [{i + 1}/{len(to_geocode)}] {city}, {state} -> {status}")

            # Rate limiting
            await asyncio.sleep(RATE_LIMIT_SECONDS)

            # Save cache every 20 cities
            if (i + 1) % 20 == 0:
                save_cache(cache)

    save_cache(cache)
    return results


async def update_postgres(
    stations: list[dict],
    coords: dict[tuple[str, str], tuple[float, float]],
    dry_run: bool = False,
):
    """Update PostgreSQL air_stations with geocoded coordinates."""
    updates = []
    for s in stations:
        key = (s["city"], s["state"])
        if key in coords:
            lat, lon = coords[key]
            updates.append((s["station_id"], lon, lat))  # PostGIS: POINT(lon lat)

    print(f"\nPostgreSQL: {len(updates)} stations to update out of {len(stations)}")

    if dry_run:
        for sid, lon, lat in updates[:5]:
            print(
                f"  DRY-RUN: UPDATE air_stations SET geom = ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326) WHERE station_id = '{sid}'"
            )
        if len(updates) > 5:
            print(f"  ... and {len(updates) - 5} more")
        return

    conn = await asyncpg.connect(PG_DSN)
    try:
        # Batch update using executemany
        await conn.executemany(
            """
            UPDATE air_stations
            SET geom = ST_SetSRID(ST_MakePoint($2, $3), 4326),
                updated_at = NOW()
            WHERE station_id = $1
            """,
            updates,
        )
        print(f"  Updated {len(updates)} stations in PostgreSQL")
    finally:
        await conn.close()


def generate_clickhouse_updates(
    stations: list[dict],
    coords: dict[tuple[str, str], tuple[float, float]],
) -> str:
    """Generate ClickHouse ALTER UPDATE statements for air_quality_raw."""
    lines = [
        "-- ClickHouse: Update latitude/longitude in air_quality_raw",
        "-- Run with: clickhouse-client --user admin --password prithvinet_secure_2024 --multiquery",
        "",
    ]

    # Group stations by coordinates to minimize UPDATE statements
    # Update by station_id
    for s in stations:
        key = (s["city"], s["state"])
        if key in coords:
            lat, lon = coords[key]
            lines.append(
                f"ALTER TABLE prithvinet.air_quality_raw UPDATE "
                f"latitude = {lat}, longitude = {lon} "
                f"WHERE station_id = '{s['station_id']}';"
            )

    return "\n".join(lines)


async def main():
    parser = argparse.ArgumentParser(description="Geocode CPCB stations")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview without DB writes"
    )
    parser.add_argument(
        "--cache-only", action="store_true", help="Only use cached results"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("PRITHVINET Station Geocoder")
    print("=" * 60)

    # Load data
    stations = load_stations()
    cities = get_unique_cities(stations)
    cache = load_cache()
    print(f"Loaded {len(stations)} stations across {len(cities)} unique cities")

    # Geocode
    coords = await geocode_all_cities(cities, cache, cache_only=args.cache_only)
    save_cache(cache)

    matched = sum(1 for s in stations if (s["city"], s["state"]) in coords)
    unmatched = len(stations) - matched
    print(f"\nGeocoding results: {matched} matched, {unmatched} unmatched")

    if unmatched > 0:
        failed = set()
        for s in stations:
            key = (s["city"], s["state"])
            if key not in coords:
                failed.add(key)
        print(f"Failed cities ({len(failed)}):")
        for city, state in sorted(failed):
            print(f"  - {city}, {state}")

    # Update PostgreSQL
    await update_postgres(stations, coords, dry_run=args.dry_run)

    # Generate ClickHouse SQL
    ch_sql = generate_clickhouse_updates(stations, coords)
    ch_sql_path = DATA_DIR / "clickhouse_geocode_update.sql"
    if not args.dry_run:
        with open(ch_sql_path, "w") as f:
            f.write(ch_sql)
        print(f"\nClickHouse SQL written to: {ch_sql_path}")
        print(
            f"Run it with: docker exec -i prithvinet-clickhouse clickhouse-client --user admin --password prithvinet_secure_2024 --multiquery < {ch_sql_path}"
        )
    else:
        print(f"\nDRY-RUN: Would write ClickHouse SQL to {ch_sql_path}")

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
