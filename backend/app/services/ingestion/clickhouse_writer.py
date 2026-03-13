"""
ClickHouse Writer — bulk insert sensor readings into ClickHouse time-series tables.
Uses clickhouse-connect for async-compatible batch inserts.
"""

import clickhouse_connect
from clickhouse_connect.driver.client import Client
from loguru import logger
from typing import Optional

from app.models.schemas import (
    AirQualityReading,
    WaterQualityReading,
    NoiseReading,
    OCEMSReading,
)
from app.core.config import settings


class ClickHouseWriter:
    """Manages bulk inserts to ClickHouse time-series tables."""

    def __init__(self):
        self._client: Optional[Client] = None

    def _get_client(self) -> Client:
        if self._client is None:
            self._client = clickhouse_connect.get_client(
                host=settings.CLICKHOUSE_HOST,
                port=int(settings.CLICKHOUSE_PORT),
                username=settings.CLICKHOUSE_USER,
                password=settings.CLICKHOUSE_PASSWORD,
                database=settings.CLICKHOUSE_DB,
            )
        return self._client

    async def close(self):
        if self._client:
            self._client.close()
            self._client = None

    # ------------------------------------------------------------------
    # AIR QUALITY
    # ------------------------------------------------------------------
    async def insert_air_readings(self, readings: list[AirQualityReading]) -> int:
        if not readings:
            return 0
        client = self._get_client()
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
        data = [
            [
                r.station_id,
                r.timestamp,
                r.parameter,
                r.value,
                r.unit,
                r.aqi,
                r.city,
                r.latitude,
                r.longitude,
                r.zone.value,
                1 if r.is_anomaly else 0,
                r.anomaly_type.value,
                r.quality_flag.value,
            ]
            for r in readings
        ]
        try:
            client.insert("air_quality_raw", data, column_names=columns)
            logger.info(f"Inserted {len(data)} air quality readings to ClickHouse")
            return len(data)
        except Exception as e:
            logger.error(f"ClickHouse air insert failed: {e}")
            raise

    # ------------------------------------------------------------------
    # WATER QUALITY
    # ------------------------------------------------------------------
    async def insert_water_readings(self, readings: list[WaterQualityReading]) -> int:
        if not readings:
            return 0
        client = self._get_client()
        columns = [
            "station_id",
            "timestamp",
            "parameter",
            "value",
            "unit",
            "wqi",
            "river_name",
            "city",
            "latitude",
            "longitude",
            "is_anomaly",
            "anomaly_type",
            "quality_flag",
        ]
        data = [
            [
                r.station_id,
                r.timestamp,
                r.parameter,
                r.value,
                r.unit,
                r.wqi,
                r.river_name,
                r.city,
                r.latitude,
                r.longitude,
                1 if r.is_anomaly else 0,
                r.anomaly_type.value,
                r.quality_flag.value,
            ]
            for r in readings
        ]
        try:
            client.insert("water_quality_raw", data, column_names=columns)
            logger.info(f"Inserted {len(data)} water quality readings to ClickHouse")
            return len(data)
        except Exception as e:
            logger.error(f"ClickHouse water insert failed: {e}")
            raise

    # ------------------------------------------------------------------
    # NOISE
    # ------------------------------------------------------------------
    async def insert_noise_readings(self, readings: list[NoiseReading]) -> int:
        if not readings:
            return 0
        client = self._get_client()
        columns = [
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
        ]
        data = [
            [
                r.station_id,
                r.timestamp,
                r.metric,
                r.value,
                r.city,
                r.latitude,
                r.longitude,
                r.zone.value,
                r.day_limit,
                r.night_limit,
                1 if r.is_exceedance else 0,
                1 if r.is_anomaly else 0,
                r.anomaly_type.value,
                r.quality_flag.value,
            ]
            for r in readings
        ]
        try:
            client.insert("noise_raw", data, column_names=columns)
            logger.info(f"Inserted {len(data)} noise readings to ClickHouse")
            return len(data)
        except Exception as e:
            logger.error(f"ClickHouse noise insert failed: {e}")
            raise

    # ------------------------------------------------------------------
    # OCEMS
    # ------------------------------------------------------------------
    async def insert_ocems_readings(self, readings: list[OCEMSReading]) -> int:
        if not readings:
            return 0
        client = self._get_client()
        columns = [
            "factory_id",
            "timestamp",
            "parameter",
            "value",
            "unit",
            "emission_limit",
            "exceedance_pct",
            "industry_type",
            "city",
            "latitude",
            "longitude",
            "dahs_status",
            "sensor_health",
            "is_anomaly",
            "anomaly_type",
            "quality_flag",
        ]
        data = [
            [
                r.factory_id,
                r.timestamp,
                r.parameter,
                r.value,
                r.unit,
                r.emission_limit,
                r.exceedance_pct,
                r.industry_type,
                r.city,
                r.latitude,
                r.longitude,
                r.dahs_status,
                r.sensor_health,
                1 if r.is_anomaly else 0,
                r.anomaly_type.value,
                r.quality_flag.value,
            ]
            for r in readings
        ]
        try:
            client.insert("ocems_raw", data, column_names=columns)
            logger.info(f"Inserted {len(data)} OCEMS readings to ClickHouse")
            return len(data)
        except Exception as e:
            logger.error(f"ClickHouse OCEMS insert failed: {e}")
            raise

    # ------------------------------------------------------------------
    # QUERY HELPERS (used by services)
    # ------------------------------------------------------------------
    async def query_recent_readings(
        self,
        table: str,
        station_or_factory_id: str,
        id_column: str = "station_id",
        hours: int = 24,
        parameter: Optional[str] = None,
    ) -> list[dict]:
        """Query recent readings for a station/factory. Returns list of dicts.

        Uses the most recent timestamp in the table as the reference point
        instead of now(), because historical CPCB data is from 2024-2025.
        """
        client = self._get_client()
        param_filter = f"AND parameter = '{parameter}'" if parameter else ""
        # Use subquery to find the max timestamp for this station, so we
        # get data relative to the latest available reading (not wall-clock now()).
        query = f"""
            SELECT *
            FROM {table}
            WHERE {id_column} = '{station_or_factory_id}'
              AND timestamp >= (
                  SELECT max(timestamp) - INTERVAL {hours} HOUR
                  FROM {table}
                  WHERE {id_column} = '{station_or_factory_id}'
              )
              {param_filter}
            ORDER BY timestamp DESC
            LIMIT 10000
        """
        try:
            result = client.query(query)
            columns = result.column_names
            return [dict(zip(columns, row)) for row in result.result_rows]
        except Exception as e:
            logger.error(f"ClickHouse query failed: {e}")
            return []

    async def query_historical_series(
        self,
        table: str,
        station_id: str,
        parameter: str,
        days: int = 30,
    ) -> list[dict]:
        """Get time series for a station+parameter, ordered by time.

        Fetches the most recent N records (days * 24 for hourly data) rather
        than filtering by wall-clock time.  Historical CPCB data is from
        2024-2025 while the live simulator writes sparse 2026 readings, so a
        time-based window around max(timestamp) would miss the dense
        historical block.  Fetching by row count always works.
        """
        client = self._get_client()
        limit = days * 24  # hourly data → 720 rows for 30 days
        query = f"""
            SELECT timestamp, value
            FROM (
                SELECT timestamp, value
                FROM {table}
                WHERE station_id = '{station_id}'
                  AND parameter = '{parameter}'
                ORDER BY timestamp DESC
                LIMIT {limit}
            )
            ORDER BY timestamp ASC
        """
        try:
            result = client.query(query)
            return [
                {"timestamp": row[0], "value": row[1]} for row in result.result_rows
            ]
        except Exception as e:
            logger.error(f"ClickHouse historical query failed: {e}")
            return []


# Singleton instance
ch_writer = ClickHouseWriter()
