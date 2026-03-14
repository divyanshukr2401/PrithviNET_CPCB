"""
PRITHVINET Data.gov.in Real-Time Air Quality Fetcher
=====================================================
On-demand per-station fetcher that queries the CPCB Real-Time Air Quality
Index resource on data.gov.in.

Resource: "Real time Air Quality Index from various locations"
API: https://api.data.gov.in/resource/<resource_id>

Strategy:
  1. Given a station_id, look up its city from the live simulator's station_meta cache.
  2. Query data.gov.in filtered by city (rate-limit friendly — only on user click).
  3. Cache the result in Redis with TTL=30 min to avoid repeated API calls.
  4. Return pollutant data in the same format as the live simulator readings.
  5. Write real data to ClickHouse with quality_flag='real'.

Pollutant ID mapping (API → CPCB standard):
  OZONE → O3, CO → CO, PM2.5 → PM2.5, PM10 → PM10,
  NO2 → NO2, SO2 → SO2, NH3 → NH3
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
from loguru import logger

from app.core.config import settings
from app.services.ingestion.aqi_decomposer import POLLUTANTS, UNITS

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

IST = timezone(timedelta(hours=5, minutes=30))

DATA_GOV_BASE_URL = "https://api.data.gov.in/resource"

# Mapping from data.gov.in pollutant_id → our standard parameter names
POLLUTANT_ID_MAP = {
    "PM2.5": "PM2.5",
    "PM10": "PM10",
    "NO2": "NO2",
    "SO2": "SO2",
    "CO": "CO",
    "OZONE": "O3",
    "NH3": "NH3",
    "Pb": "Pb",
    # Some records may have lowercase or alternate names
    "pm2.5": "PM2.5",
    "pm10": "PM10",
    "no2": "NO2",
    "so2": "SO2",
    "co": "CO",
    "ozone": "O3",
    "o3": "O3",
    "nh3": "NH3",
    "pb": "Pb",
}

# CPCB AQI breakpoint table — (AQI_lo, AQI_hi, Conc_lo, Conc_hi) per pollutant
# Used to compute sub-index AQI from concentration
BREAKPOINTS = {
    "PM2.5": [
        (0, 50, 0, 30),
        (51, 100, 31, 60),
        (101, 200, 61, 90),
        (201, 300, 91, 120),
        (301, 400, 121, 250),
        (401, 500, 250, 380),
    ],
    "PM10": [
        (0, 50, 0, 50),
        (51, 100, 51, 100),
        (101, 200, 101, 250),
        (201, 300, 251, 350),
        (301, 400, 351, 430),
        (401, 500, 430, 510),
    ],
    "NO2": [
        (0, 50, 0, 40),
        (51, 100, 41, 80),
        (101, 200, 81, 180),
        (201, 300, 181, 280),
        (301, 400, 281, 400),
        (401, 500, 400, 520),
    ],
    "SO2": [
        (0, 50, 0, 40),
        (51, 100, 41, 80),
        (101, 200, 81, 380),
        (201, 300, 381, 800),
        (301, 400, 801, 1600),
        (401, 500, 1600, 2100),
    ],
    "CO": [
        (0, 50, 0, 1.0),
        (51, 100, 1.1, 2.0),
        (101, 200, 2.1, 10.0),
        (201, 300, 10.1, 17.0),
        (301, 400, 17.1, 34.0),
        (401, 500, 34.0, 46.0),
    ],
    "O3": [
        (0, 50, 0, 50),
        (51, 100, 51, 100),
        (101, 200, 101, 168),
        (201, 300, 169, 208),
        (301, 400, 209, 748),
        (401, 500, 748, 960),
    ],
    "NH3": [
        (0, 50, 0, 200),
        (51, 100, 201, 400),
        (101, 200, 401, 800),
        (201, 300, 801, 1200),
        (301, 400, 1201, 1800),
        (401, 500, 1800, 2400),
    ],
}


def _compute_sub_aqi(parameter: str, concentration: float) -> int:
    """Compute CPCB sub-index AQI for a given pollutant concentration."""
    bps = BREAKPOINTS.get(parameter)
    if not bps:
        return 0
    for aqi_lo, aqi_hi, c_lo, c_hi in bps:
        if c_lo <= concentration <= c_hi:
            if c_hi == c_lo:
                return aqi_lo
            aqi = ((aqi_hi - aqi_lo) / (c_hi - c_lo)) * (concentration - c_lo) + aqi_lo
            return round(aqi)
    # Above max bracket
    if concentration > bps[-1][3]:
        return 500
    return 0


# ---------------------------------------------------------------------------
# Haversine distance (for nearest-station matching)
# ---------------------------------------------------------------------------


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in km between two lat/lon points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# DataGovFetcher
# ---------------------------------------------------------------------------


class DataGovFetcher:
    """
    On-demand fetcher for real-time air quality data from data.gov.in.
    Called when a user clicks on a station — NOT bulk-fetched.
    """

    def __init__(self):
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=15.0)
        return self._http_client

    async def close(self):
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None

    async def fetch_city_data(self, city: str) -> list[dict]:
        """
        Fetch all real-time pollutant records for a given city from data.gov.in.
        Returns raw API records list.
        """
        api_key = settings.DATA_GOV_API_KEY
        resource_id = settings.DATA_GOV_RESOURCE_ID
        if not api_key:
            logger.warning("DataGovFetcher: No DATA_GOV_API_KEY configured")
            return []

        url = f"{DATA_GOV_BASE_URL}/{resource_id}"
        params = {
            "api-key": api_key,
            "format": "json",
            "limit": 500,
            "offset": 0,
            "filters[city]": city,
        }

        try:
            client = await self._get_client()
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            records = data.get("records", [])
            total = data.get("total", 0)
            logger.info(
                f"DataGovFetcher: Got {len(records)}/{total} records for city={city}"
            )
            return records

        except httpx.HTTPStatusError as e:
            logger.error(
                f"DataGovFetcher: HTTP {e.response.status_code} for city={city}: "
                f"{e.response.text[:200]}"
            )
            return []
        except Exception as e:
            logger.error(f"DataGovFetcher: Failed to fetch city={city}: {e}")
            return []

    def _find_best_station(
        self,
        records: list[dict],
        target_lat: float,
        target_lon: float,
    ) -> Optional[str]:
        """
        Among the API records (which may have multiple stations for one city),
        find the station name closest to our station's lat/lon.
        Returns the API station name, or None.
        """
        station_coords: dict[str, tuple[float, float]] = {}
        for r in records:
            name = r.get("station", "")
            if name and name not in station_coords:
                try:
                    lat = float(r.get("latitude", 0))
                    lon = float(r.get("longitude", 0))
                    if lat != 0 and lon != 0:
                        station_coords[name] = (lat, lon)
                except (ValueError, TypeError):
                    pass

        if not station_coords:
            return None

        # If target coords are zero or invalid, just pick the first station
        if target_lat == 0 and target_lon == 0:
            return next(iter(station_coords))

        # Find nearest
        best_name = None
        best_dist = float("inf")
        for name, (lat, lon) in station_coords.items():
            d = _haversine_km(target_lat, target_lon, lat, lon)
            if d < best_dist:
                best_dist = d
                best_name = name

        return best_name

    def parse_station_readings(
        self,
        records: list[dict],
        api_station_name: str,
        our_station_id: str,
    ) -> dict:
        """
        Parse API records for a specific station into our reading format.
        Returns a dict with keys:
          - aqi_reading: dict (the overall AQI row)
          - pollutant_readings: list[dict] (individual pollutant rows)
          - api_station_name: str
          - last_update: str
          - quality_flag: 'real'
        """
        # Filter records for this station
        station_records = [
            r for r in records if r.get("station", "") == api_station_name
        ]

        if not station_records:
            return {}

        # Parse each pollutant
        now_iso = datetime.now(IST).isoformat()
        last_update = station_records[0].get("last_update", now_iso)

        # Try to parse the API timestamp
        try:
            # Format: "13-03-2026 15:00:00"
            ts = datetime.strptime(last_update, "%d-%m-%Y %H:%M:%S")
            ts = ts.replace(tzinfo=IST)
            ts_iso = ts.isoformat()
        except (ValueError, TypeError):
            ts_iso = now_iso

        # Get station coordinates from the first record
        try:
            api_lat = float(station_records[0].get("latitude", 0))
            api_lon = float(station_records[0].get("longitude", 0))
        except (ValueError, TypeError):
            api_lat, api_lon = 0.0, 0.0

        city = station_records[0].get("city", "")

        pollutant_readings = []
        max_aqi = 0
        dominant_param = ""

        for rec in station_records:
            raw_pollutant = rec.get("pollutant_id", "")
            parameter = POLLUTANT_ID_MAP.get(raw_pollutant, raw_pollutant)

            if parameter not in POLLUTANTS and parameter not in BREAKPOINTS:
                continue  # skip unknown pollutants

            try:
                avg_val = float(rec.get("avg_value", 0))
            except (ValueError, TypeError):
                avg_val = 0.0

            # data.gov.in returns CO in µg/m³ but CPCB breakpoints use mg/m³
            # Convert: 1 mg = 1000 µg → divide by 1000
            aqi_concentration = avg_val
            display_val = avg_val
            if parameter == "CO":
                aqi_concentration = avg_val / 1000.0
                display_val = aqi_concentration  # store in mg/m³ to match UNITS

            # Compute sub-index AQI (using converted concentration for CO)
            sub_aqi = _compute_sub_aqi(parameter, aqi_concentration)

            unit = UNITS.get(parameter, "µg/m³")

            pollutant_readings.append(
                {
                    "station_id": our_station_id,
                    "timestamp": ts_iso,
                    "parameter": parameter,
                    "value": round(display_val, 4),
                    "unit": unit,
                    "aqi": sub_aqi,
                    "city": city,
                    "latitude": api_lat,
                    "longitude": api_lon,
                    "zone": "unknown",
                    "is_anomaly": 0,
                    "anomaly_type": "",
                    "quality_flag": "real",
                }
            )

            if sub_aqi > max_aqi:
                max_aqi = sub_aqi
                dominant_param = parameter

        if not pollutant_readings:
            return {}

        # Build overall AQI reading
        aqi_reading = {
            "station_id": our_station_id,
            "timestamp": ts_iso,
            "parameter": "AQI",
            "value": float(max_aqi),
            "unit": "index",
            "aqi": max_aqi,
            "city": city,
            "latitude": api_lat,
            "longitude": api_lon,
            "zone": "unknown",
            "is_anomaly": 0,
            "anomaly_type": "",
            "quality_flag": "real",
        }

        return {
            "aqi_reading": aqi_reading,
            "pollutant_readings": pollutant_readings,
            "api_station_name": api_station_name,
            "last_update": ts_iso,
            "quality_flag": "real",
            "dominant_pollutant": dominant_param,
        }

    async def fetch_for_station(
        self,
        station_id: str,
        city: str,
        latitude: float = 0.0,
        longitude: float = 0.0,
    ) -> dict:
        """
        Main entry point: fetch real data for a given station.

        1. Query data.gov.in by city
        2. Find the nearest API station by lat/lon
        3. Parse pollutant readings
        4. Cache in Redis (30 min TTL)
        5. Write to ClickHouse with quality_flag='real'

        Returns parsed result dict or empty dict if no data.
        """
        # Check Redis cache first
        cache_key = f"prithvinet:datagov:real:{station_id}"
        try:
            from app.core.redis import get_redis

            redis = await get_redis()
            cached = await redis.get(cache_key)
            if cached:
                logger.debug(f"DataGovFetcher: Redis cache HIT for {station_id}")
                return json.loads(cached)
        except Exception as e:
            logger.debug(f"DataGovFetcher: Redis read failed: {e}")

        # Fetch from API
        records = await self.fetch_city_data(city)
        if not records:
            return {}

        # Find best matching station
        best_station = self._find_best_station(records, latitude, longitude)
        if not best_station:
            return {}

        # Parse readings
        result = self.parse_station_readings(records, best_station, station_id)
        if not result:
            return {}

        # Cache in Redis (30 min TTL)
        try:
            from app.core.redis import get_redis

            redis = await get_redis()
            await redis.setex(
                cache_key,
                1800,  # 30 minutes
                json.dumps(result, default=str),
            )
            logger.debug(f"DataGovFetcher: Cached {station_id} in Redis (TTL=30m)")
        except Exception as e:
            logger.debug(f"DataGovFetcher: Redis write failed: {e}")

        # Write to ClickHouse with quality_flag='real'
        await self._write_to_clickhouse(result)

        return result

    async def _write_to_clickhouse(self, result: dict):
        """Write real data readings to ClickHouse air_quality_raw."""
        if not result:
            return

        all_readings = []
        aqi_reading = result.get("aqi_reading")
        if aqi_reading:
            all_readings.append(aqi_reading)
        all_readings.extend(result.get("pollutant_readings", []))

        if not all_readings:
            return

        try:
            import clickhouse_connect

            client = clickhouse_connect.get_client(
                host=settings.CLICKHOUSE_HOST,
                port=int(settings.CLICKHOUSE_PORT),
                username=settings.CLICKHOUSE_USER,
                password=settings.CLICKHOUSE_PASSWORD,
                database=settings.CLICKHOUSE_DB,
            )

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

            data = []
            for r in all_readings:
                ts = r["timestamp"]
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts)
                data.append(
                    [
                        r["station_id"],
                        ts,
                        r["parameter"],
                        r["value"],
                        r["unit"],
                        r["aqi"],
                        r["city"],
                        r["latitude"],
                        r["longitude"],
                        r["zone"],
                        r["is_anomaly"],
                        r["anomaly_type"],
                        r["quality_flag"],
                    ]
                )

            client.insert("air_quality_raw", data, column_names=columns)
            logger.info(
                f"DataGovFetcher: Wrote {len(data)} real readings to ClickHouse "
                f"(station={all_readings[0]['station_id']})"
            )
            client.close()

        except Exception as e:
            logger.error(f"DataGovFetcher: ClickHouse write failed: {e}")


# Singleton
datagov_fetcher = DataGovFetcher()
