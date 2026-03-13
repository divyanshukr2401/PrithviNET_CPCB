#!/usr/bin/env python3
"""
PRITHVINET - Historical Data Generator
=======================================
Generates 30 days of simulated environmental monitoring data for Chhattisgarh,
with 5 pre-planned anomaly events injected at specific days.

Data Volume (~7.8M rows):
  Air:   23 stations x 8 params x 288 readings/day x 30 days = ~1.6M rows
  Water:  9 stations x 10 params x 24 readings/day x 30 days = ~65K rows
  Noise:  9 stations x 7 metrics x 1440 readings/day x 30 days = ~2.7M rows
  OCEMS: 20 factories x 4 params x 144 readings/day x 30 days = ~3.5M rows

Pre-planned anomaly events:
  Day  3: Bhilai Steel Plant emission spike
  Day  7: Korba NTPC sensor stuck-value malfunction
  Day 12: Raipur festival noise spike (Holi season)
  Day 18: Policy intervention simulation point
  Day 25: Water quality deterioration in Sheonath river

Usage:
  python scripts/generate_historical_data.py --clickhouse
  python scripts/generate_historical_data.py --csv-dir data/simulated
  python scripts/generate_historical_data.py --clickhouse --batch-size 50000
"""

import argparse
import csv
import math
import os
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from loguru import logger

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from chhattisgarh_stations import (
    AIR_STATIONS,
    WATER_STATIONS,
    NOISE_STATIONS,
    FACTORIES,
    NAAQS_LIMITS,
    WQ_STANDARDS,
    CPCB_NOISE_LIMITS,
    OCEMS_EMISSION_LIMITS,
    Station,
    Factory,
    ZoneType,
)

# ============================================================================
# CONFIGURATION
# ============================================================================

IST = timezone(timedelta(hours=5, minutes=30))
DAYS = 30
# Start date: 30 days ago from "now" — use current time so data is always fresh
REFERENCE_NOW = datetime.now(tz=IST).replace(second=0, microsecond=0)
START_DATE = REFERENCE_NOW - timedelta(days=DAYS)

CLICKHOUSE_BATCH_SIZE = 50_000  # rows per batch insert

# Anomaly schedule (day offset from START_DATE)
ANOMALY_EVENTS = {
    3: {
        "name": "Bhilai Steel Plant emission spike",
        "type": "ocems_spike",
        "factory_ids": ["OCEMS-CG-001"],  # BSP
        "air_station_ids": ["AQ-CG-004", "AQ-CG-005", "AQ-CG-006"],  # Bhilai air
        "params": ["PM", "SO2"],
        "multiplier": (3.0, 6.0),
        "duration_hours": 8,
    },
    7: {
        "name": "Korba NTPC sensor stuck-value malfunction",
        "type": "ocems_stuck",
        "factory_ids": ["OCEMS-CG-005"],  # NTPC Korba
        "params": ["PM", "SO2", "NOx", "CO"],
        "duration_hours": 18,
    },
    12: {
        "name": "Raipur festival noise spike (Holi)",
        "type": "noise_spike",
        "station_ids": ["NS-CG-001", "NS-CG-002", "NS-CG-003"],  # Raipur noise
        "air_station_ids": ["AQ-CG-001", "AQ-CG-002", "AQ-CG-003"],  # firecracker PM
        "multiplier": (1.5, 2.5),
        "duration_hours": 14,  # 8 AM to 10 PM
    },
    18: {
        "name": "Policy intervention simulation point",
        "type": "policy_intervention",
        # From day 18 onward, Raipur industrial stations see a 15% drop (simulating
        # enforcement action). This gives the causal simulator a "before/after" signal.
        "air_station_ids": ["AQ-CG-002", "AQ-CG-016", "AQ-CG-017"],
        "factory_ids": ["OCEMS-CG-003", "OCEMS-CG-004"],
        "reduction_pct": 0.15,
    },
    25: {
        "name": "Water quality deterioration in Sheonath river",
        "type": "water_deterioration",
        "station_ids": ["WQ-CG-003", "WQ-CG-008"],  # Sheonath river stations
        "params": ["BOD", "COD", "TSS", "Turbidity"],
        "multiplier": (2.0, 4.0),
        "duration_hours": 48,
    },
    28: {
        "name": "Raipur Industrial Area emission spike (recent)",
        "type": "ocems_spike",
        "factory_ids": ["OCEMS-CG-003", "OCEMS-CG-004"],
        "air_station_ids": ["AQ-CG-002", "AQ-CG-003"],
        "params": ["PM", "NOx"],
        "multiplier": (2.5, 5.0),
        "duration_hours": 10,
    },
    29: {
        "name": "Korba sensor malfunction (recent stuck-value)",
        "type": "ocems_stuck",
        "factory_ids": ["OCEMS-CG-006"],
        "params": ["PM", "SO2"],
        "duration_hours": 12,
    },
}


# ============================================================================
# SENSOR SIMULATORS (lightweight, no HTTP, no asyncio)
# ============================================================================


class AirQualityGenerator:
    """Generate air quality rows for one station."""

    BASELINES = {
        "industrial": {
            "PM2.5": 85,
            "PM10": 160,
            "SO2": 35,
            "NO2": 40,
            "CO": 1800,
            "O3": 35,
            "NH3": 25,
            "Pb": 0.20,
        },
        "commercial": {
            "PM2.5": 60,
            "PM10": 110,
            "SO2": 20,
            "NO2": 35,
            "CO": 1200,
            "O3": 42,
            "NH3": 20,
            "Pb": 0.12,
        },
        "residential": {
            "PM2.5": 45,
            "PM10": 85,
            "SO2": 12,
            "NO2": 25,
            "CO": 800,
            "O3": 48,
            "NH3": 18,
            "Pb": 0.08,
        },
        "silence": {
            "PM2.5": 40,
            "PM10": 80,
            "SO2": 10,
            "NO2": 20,
            "CO": 600,
            "O3": 50,
            "NH3": 15,
            "Pb": 0.06,
        },
        "mining": {
            "PM2.5": 70,
            "PM10": 200,
            "SO2": 30,
            "NO2": 25,
            "CO": 1000,
            "O3": 30,
            "NH3": 12,
            "Pb": 0.25,
        },
        "riverfront": {
            "PM2.5": 42,
            "PM10": 78,
            "SO2": 10,
            "NO2": 22,
            "CO": 700,
            "O3": 52,
            "NH3": 16,
            "Pb": 0.07,
        },
    }
    NOISE_STD = {
        "PM2.5": 12,
        "PM10": 25,
        "SO2": 6,
        "NO2": 8,
        "CO": 200,
        "O3": 10,
        "NH3": 5,
        "Pb": 0.03,
    }
    PARAMS = ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3", "NH3", "Pb"]

    # AQI breakpoints (same as simulate_sensors.py)
    AQI_BP = {
        "PM2.5": [
            (0, 30, 0, 50),
            (30, 60, 50, 100),
            (60, 90, 100, 200),
            (90, 120, 200, 300),
            (120, 250, 300, 400),
            (250, 500, 400, 500),
        ],
        "PM10": [
            (0, 50, 0, 50),
            (50, 100, 50, 100),
            (100, 250, 100, 200),
            (250, 350, 200, 300),
            (350, 430, 300, 400),
            (430, 600, 400, 500),
        ],
        "NO2": [
            (0, 40, 0, 50),
            (40, 80, 50, 100),
            (80, 180, 100, 200),
            (180, 280, 200, 300),
            (280, 400, 300, 400),
            (400, 600, 400, 500),
        ],
        "SO2": [
            (0, 40, 0, 50),
            (40, 80, 50, 100),
            (80, 380, 100, 200),
            (380, 800, 200, 300),
            (800, 1600, 300, 400),
            (1600, 2400, 400, 500),
        ],
        "CO": [
            (0, 1000, 0, 50),
            (1000, 2000, 50, 100),
            (2000, 10000, 100, 200),
            (10000, 17000, 200, 300),
            (17000, 34000, 300, 400),
            (34000, 50000, 400, 500),
        ],
        "O3": [
            (0, 50, 0, 50),
            (50, 100, 50, 100),
            (100, 168, 100, 200),
            (168, 208, 200, 300),
            (208, 748, 300, 400),
            (748, 1000, 400, 500),
        ],
        "NH3": [
            (0, 200, 0, 50),
            (200, 400, 50, 100),
            (400, 800, 100, 200),
            (800, 1200, 200, 300),
            (1200, 1800, 300, 400),
            (1800, 2400, 400, 500),
        ],
        "Pb": [
            (0, 0.5, 0, 50),
            (0.5, 1.0, 50, 100),
            (1.0, 2.0, 100, 200),
            (2.0, 3.0, 200, 300),
            (3.0, 3.5, 300, 400),
            (3.5, 5.0, 400, 500),
        ],
    }

    def __init__(self, station: Station, rng: np.random.Generator):
        self.station = station
        self.rng = rng
        zone = station.zone.value
        self.baseline = self.BASELINES.get(zone, self.BASELINES["residential"])

    def generate(self, ts: datetime, anomaly_mult: float = 1.0) -> list[list]:
        """Return list of row-tuples for insertion. One row per parameter."""
        diurnal = self._diurnal(ts)
        rows = []
        for param in self.PARAMS:
            base = self.baseline[param]
            std = self.NOISE_STD[param]
            if param == "O3":
                factor = 2.0 - diurnal
            else:
                factor = diurnal

            value = max(0.0, base * factor * anomaly_mult + self.rng.normal(0, std))
            aqi = self._sub_aqi(param, value)
            is_anomaly = 1 if anomaly_mult > 1.05 else 0
            anomaly_type = "spike" if is_anomaly else ""
            quality_flag = "suspect" if is_anomaly else "valid"

            rows.append(
                [
                    self.station.station_id,
                    ts,
                    param,
                    round(value, 3),
                    "ug/m3",
                    aqi,
                    self.station.city,
                    self.station.latitude,
                    self.station.longitude,
                    self.station.zone.value,
                    is_anomaly,
                    anomaly_type,
                    quality_flag,
                ]
            )
        return rows

    def _diurnal(self, ts: datetime) -> float:
        hour = ts.hour + ts.minute / 60.0
        morning = 1.3 * math.exp(-0.5 * ((hour - 9) / 1.5) ** 2)
        evening = 1.2 * math.exp(-0.5 * ((hour - 18.5) / 2.0) ** 2)
        night = -0.35 * math.exp(-0.5 * ((hour - 3) / 2.0) ** 2)
        return 1.0 + morning + evening + night + self.rng.uniform(-0.05, 0.05)

    def _sub_aqi(self, param: str, value: float) -> int:
        bps = self.AQI_BP.get(param, [(0, 100, 0, 100)])
        for c_lo, c_hi, i_lo, i_hi in bps:
            if c_lo <= value <= c_hi:
                return int(i_lo + (value - c_lo) * (i_hi - i_lo) / max(1, c_hi - c_lo))
        return 500 if value > bps[-1][1] else 0


class WaterQualityGenerator:
    """Generate water quality rows for one station."""

    BASELINES = {
        "riverfront": {
            "pH": 7.2,
            "DO": 6.5,
            "BOD": 2.5,
            "COD": 15,
            "TSS": 40,
            "Turbidity": 8,
            "Conductivity": 400,
            "Temperature": 26,
            "Nitrates": 8,
            "Phosphates": 0.8,
        },
        "industrial": {
            "pH": 6.8,
            "DO": 4.5,
            "BOD": 5.0,
            "COD": 30,
            "TSS": 80,
            "Turbidity": 20,
            "Conductivity": 700,
            "Temperature": 28,
            "Nitrates": 18,
            "Phosphates": 2.5,
        },
        "commercial": {
            "pH": 7.0,
            "DO": 5.5,
            "BOD": 3.5,
            "COD": 20,
            "TSS": 55,
            "Turbidity": 12,
            "Conductivity": 500,
            "Temperature": 27,
            "Nitrates": 12,
            "Phosphates": 1.5,
        },
    }
    NOISE_STD = {
        "pH": 0.3,
        "DO": 1.0,
        "BOD": 0.8,
        "COD": 5,
        "TSS": 10,
        "Turbidity": 4,
        "Conductivity": 60,
        "Temperature": 1.5,
        "Nitrates": 3,
        "Phosphates": 0.4,
    }
    UNITS = {
        "pH": "pH",
        "DO": "mg/L",
        "BOD": "mg/L",
        "COD": "mg/L",
        "TSS": "mg/L",
        "Turbidity": "NTU",
        "Conductivity": "uS/cm",
        "Temperature": "C",
        "Nitrates": "mg/L",
        "Phosphates": "mg/L",
    }
    PARAMS = [
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
    ]

    def __init__(self, station: Station, rng: np.random.Generator):
        self.station = station
        self.rng = rng
        zone = station.zone.value
        self.baseline = self.BASELINES.get(zone, self.BASELINES["riverfront"])

    def generate(
        self,
        ts: datetime,
        anomaly_params: set[str] | None = None,
        anomaly_mult: float = 1.0,
    ) -> list[list]:
        hour = ts.hour + ts.minute / 60.0
        temp_factor = 1.0 + 0.1 * math.sin(2 * math.pi * (hour - 14) / 24)
        rows = []
        for param in self.PARAMS:
            base = self.baseline[param]
            std = self.NOISE_STD[param]

            mult = anomaly_mult if (anomaly_params and param in anomaly_params) else 1.0
            is_anomaly = 1 if mult > 1.05 else 0
            anomaly_type = "spike" if is_anomaly else ""
            quality_flag = "suspect" if is_anomaly else "valid"

            if param == "Temperature":
                value = base * temp_factor * mult + self.rng.normal(0, std)
            elif param == "DO":
                # DO decreases when pollution worsens
                value = base * (2.0 - temp_factor) / mult + self.rng.normal(0, std)
                value = max(0, value)
            elif param == "pH":
                value = base + self.rng.normal(0, std)
                if is_anomaly:
                    value -= self.rng.uniform(0.5, 1.5)  # acidification
                value = max(5.5, min(9.5, value))
            else:
                value = max(0, base * mult + self.rng.normal(0, std))

            wqi = self._sub_wqi(param, value)

            rows.append(
                [
                    self.station.station_id,
                    ts,
                    param,
                    round(value, 3),
                    self.UNITS[param],
                    round(wqi, 1),
                    self.station.river_name or "",
                    self.station.city,
                    self.station.latitude,
                    self.station.longitude,
                    is_anomaly,
                    anomaly_type,
                    quality_flag,
                ]
            )
        return rows

    def _sub_wqi(self, param: str, value: float) -> float:
        limits = WQ_STANDARDS.get(param, {})
        if "max" in limits:
            return max(0.0, 100 * (1 - value / limits["max"]))
        elif "min" in limits:
            return (
                min(100.0, 100 * value / limits["min"]) if limits["min"] > 0 else 50.0
            )
        return 50.0


class NoiseGenerator:
    """Generate noise rows for one station."""

    BASELINES = {"industrial": 70, "commercial": 60, "residential": 48, "silence": 42}
    METRICS = ["Leq", "Lmax", "Lmin", "L10", "L50", "L90", "Lden"]

    def __init__(self, station: Station, rng: np.random.Generator):
        self.station = station
        self.rng = rng
        zone = station.zone.value
        self.base_leq = self.BASELINES.get(zone, 50)
        limits = CPCB_NOISE_LIMITS.get(zone, {"day": 65, "night": 55})
        self.day_limit = limits["day"]
        self.night_limit = limits["night"]
        # Running buffer for Lden
        self._hourly_leq: list[float] = []

    def generate(self, ts: datetime, anomaly_mult: float = 1.0) -> list[list]:
        hour = ts.hour + ts.minute / 60.0
        is_night = hour < 6 or hour >= 22

        # Diurnal
        if is_night:
            factor = 0.7 + self.rng.uniform(-0.05, 0.05)
        elif 7 <= hour <= 9 or 17 <= hour <= 19:
            factor = 1.25 + self.rng.uniform(-0.05, 0.1)
        else:
            factor = 1.0 + self.rng.uniform(-0.1, 0.1)

        leq = self.base_leq * factor * anomaly_mult + self.rng.normal(0, 3)
        is_anomaly = 1 if anomaly_mult > 1.05 else 0
        anomaly_type = "spike" if is_anomaly else ""
        quality_flag = "suspect" if is_anomaly else "valid"

        lmax = leq + self.rng.uniform(5, 18)
        lmin = max(25, leq - self.rng.uniform(8, 20))
        l10 = leq + self.rng.uniform(2, 7)
        l50 = leq + self.rng.uniform(-2, 2)
        l90 = max(25, leq - self.rng.uniform(5, 12))

        self._hourly_leq.append(leq)
        if len(self._hourly_leq) > 24:
            self._hourly_leq = self._hourly_leq[-24:]
        lden = self._compute_lden()

        limit = self.night_limit if is_night else self.day_limit
        is_exceedance = 1 if leq > limit else 0

        metrics_values = {
            "Leq": leq,
            "Lmax": lmax,
            "Lmin": lmin,
            "L10": l10,
            "L50": l50,
            "L90": l90,
            "Lden": lden,
        }
        rows = []
        for metric in self.METRICS:
            val = metrics_values[metric]
            rows.append(
                [
                    self.station.station_id,
                    ts,
                    metric,
                    round(val, 1),
                    self.station.city,
                    self.station.latitude,
                    self.station.longitude,
                    self.station.zone.value,
                    float(self.day_limit),
                    float(self.night_limit),
                    is_exceedance if metric == "Leq" else 0,
                    is_anomaly,
                    anomaly_type,
                    quality_flag,
                ]
            )
        return rows

    def _compute_lden(self) -> float:
        buf = self._hourly_leq
        if len(buf) < 3:
            return buf[-1] if buf else self.base_leq
        n = len(buf)
        day_vals = buf[: max(1, n // 2)]
        eve_vals = buf[max(1, n // 2) : max(2, 3 * n // 4)]
        night_vals = buf[max(2, 3 * n // 4) :]

        def energy_avg(vals):
            if not vals:
                return float(self.base_leq)
            return 10 * math.log10(sum(10 ** (v / 10) for v in vals) / len(vals))

        ld = energy_avg(day_vals)
        le = energy_avg(eve_vals)
        ln = energy_avg(night_vals)
        return 10 * math.log10(
            (
                12 * 10 ** (ld / 10)
                + 4 * 10 ** ((le + 5) / 10)
                + 8 * 10 ** ((ln + 10) / 10)
            )
            / 24
        )


class OCEMSGenerator:
    """Generate OCEMS rows for one factory."""

    BASE_FRACTION = {
        "Thermal Power": 0.55,
        "Integrated Steel": 0.65,
        "Sponge Iron": 0.70,
        "Cement": 0.50,
        "Aluminium Smelting": 0.60,
        "Coal Mining": 0.45,
        "Coal Washery": 0.40,
        "Rice Mill": 0.35,
        "Ferro Alloys": 0.65,
    }

    def __init__(self, factory: Factory, rng: np.random.Generator):
        self.factory = factory
        self.rng = rng
        self.limits = OCEMS_EMISSION_LIMITS.get(factory.industry_type, {})
        self.base_frac = self.BASE_FRACTION.get(factory.industry_type, 0.5)
        self._stuck_values: dict[str, float] = {}

    def generate(
        self,
        ts: datetime,
        anomaly_type_override: str = "",
        anomaly_mult: float = 1.0,
        anomaly_params: set[str] | None = None,
    ) -> list[list]:
        hour = ts.hour
        shift_factor = 1.0 + 0.1 * math.sin(2 * math.pi * (hour - 8) / 8)

        rows = []
        for param in self.factory.emission_params:
            limit = self.limits.get(param, 100)
            base_val = limit * self.base_frac

            apply_anomaly = anomaly_params is None or param in anomaly_params
            a_type = anomaly_type_override if apply_anomaly else ""

            if a_type == "spike" and apply_anomaly:
                value = base_val * self.rng.uniform(
                    *(
                        (anomaly_mult, anomaly_mult + 1)
                        if isinstance(anomaly_mult, float)
                        else anomaly_mult
                    )
                )
                is_anomaly = 1
                quality_flag = "suspect"
                dahs_status = "online"
                sensor_health = round(self.rng.uniform(50, 80), 1)
            elif a_type == "stuck" and apply_anomaly:
                if param not in self._stuck_values:
                    self._stuck_values[param] = base_val + self.rng.normal(0, 1)
                value = self._stuck_values[param]
                is_anomaly = 1
                quality_flag = "suspect"
                dahs_status = "degraded"
                sensor_health = round(self.rng.uniform(20, 50), 1)
            elif a_type == "reduction" and apply_anomaly:
                value = max(
                    0,
                    base_val * shift_factor * (1 - anomaly_mult)
                    + self.rng.normal(0, base_val * 0.08),
                )
                is_anomaly = 0
                quality_flag = "valid"
                dahs_status = "online"
                sensor_health = 100.0
            else:
                value = max(
                    0, base_val * shift_factor + self.rng.normal(0, base_val * 0.1)
                )
                is_anomaly = 0
                quality_flag = "valid"
                dahs_status = "online"
                sensor_health = 100.0

            exceedance_pct = max(0, (value / limit - 1) * 100) if limit > 0 else 0

            rows.append(
                [
                    self.factory.factory_id,
                    ts,
                    param,
                    round(value, 2),
                    "mg/Nm3",
                    float(limit),
                    round(exceedance_pct, 2),
                    self.factory.industry_type,
                    self.factory.city,
                    self.factory.latitude,
                    self.factory.longitude,
                    dahs_status,
                    sensor_health,
                    is_anomaly,
                    a_type if is_anomaly else "",
                    quality_flag,
                ]
            )
        return rows


# ============================================================================
# TIMESTAMP GENERATORS
# ============================================================================


def air_timestamps(start: datetime, days: int) -> list[datetime]:
    """5-minute intervals = 288 per day."""
    ts = []
    current = start
    end = start + timedelta(days=days)
    while current < end:
        ts.append(current)
        current += timedelta(minutes=5)
    return ts


def water_timestamps(start: datetime, days: int) -> list[datetime]:
    """1-hour intervals = 24 per day."""
    ts = []
    current = start
    end = start + timedelta(days=days)
    while current < end:
        ts.append(current)
        current += timedelta(hours=1)
    return ts


def noise_timestamps(start: datetime, days: int) -> list[datetime]:
    """1-minute intervals = 1440 per day."""
    ts = []
    current = start
    end = start + timedelta(days=days)
    while current < end:
        ts.append(current)
        current += timedelta(minutes=1)
    return ts


def ocems_timestamps(start: datetime, days: int) -> list[datetime]:
    """10-minute intervals = 144 per day."""
    ts = []
    current = start
    end = start + timedelta(days=days)
    while current < end:
        ts.append(current)
        current += timedelta(minutes=10)
    return ts


# ============================================================================
# ANOMALY EVENT HELPERS
# ============================================================================


def is_in_anomaly_window(ts: datetime, day_offset: int, event: dict) -> bool:
    """Check if timestamp falls within the anomaly event window."""
    event_start = START_DATE + timedelta(days=day_offset)
    duration = event.get("duration_hours", 24)
    # For noise Holi event, start at 8 AM
    if event["type"] == "noise_spike":
        event_start = event_start.replace(hour=8, minute=0, second=0)
    event_end = event_start + timedelta(hours=duration)
    return event_start <= ts < event_end


def get_anomaly_multiplier(ts: datetime) -> dict:
    """
    Returns a dict with keys:
      air_anomaly: {station_id: multiplier}
      water_anomaly: {station_id: {params, multiplier}}
      noise_anomaly: {station_id: multiplier}
      ocems_anomaly: {factory_id: {type, multiplier, params}}
      air_reduction: {station_id: reduction_pct}
      ocems_reduction: {factory_id: reduction_pct}
    """
    result = {
        "air_anomaly": {},
        "water_anomaly": {},
        "noise_anomaly": {},
        "ocems_anomaly": {},
        "air_reduction": {},
        "ocems_reduction": {},
    }

    day_offset = (ts - START_DATE).days

    for event_day, event in ANOMALY_EVENTS.items():
        if event["type"] == "ocems_spike" and is_in_anomaly_window(
            ts, event_day, event
        ):
            mult = random.uniform(*event["multiplier"])
            for fid in event["factory_ids"]:
                result["ocems_anomaly"][fid] = {
                    "type": "spike",
                    "multiplier": mult,
                    "params": set(event["params"]),
                }
            # Also bump nearby air stations
            for sid in event.get("air_station_ids", []):
                result["air_anomaly"][sid] = random.uniform(1.5, 2.5)

        elif event["type"] == "ocems_stuck" and is_in_anomaly_window(
            ts, event_day, event
        ):
            for fid in event["factory_ids"]:
                result["ocems_anomaly"][fid] = {
                    "type": "stuck",
                    "multiplier": 1.0,
                    "params": set(event["params"]),
                }

        elif event["type"] == "noise_spike" and is_in_anomaly_window(
            ts, event_day, event
        ):
            mult = random.uniform(*event["multiplier"])
            for sid in event["station_ids"]:
                result["noise_anomaly"][sid] = mult
            for sid in event.get("air_station_ids", []):
                result["air_anomaly"][sid] = random.uniform(1.3, 2.0)  # firecracker PM

        elif event["type"] == "policy_intervention" and day_offset >= event_day:
            # Persistent reduction from day 18 onward
            reduction = event["reduction_pct"]
            for sid in event["air_station_ids"]:
                result["air_reduction"][sid] = reduction
            for fid in event["factory_ids"]:
                result["ocems_reduction"][fid] = reduction

        elif event["type"] == "water_deterioration" and is_in_anomaly_window(
            ts, event_day, event
        ):
            mult = random.uniform(*event["multiplier"])
            for sid in event["station_ids"]:
                result["water_anomaly"][sid] = {
                    "params": set(event["params"]),
                    "multiplier": mult,
                }

    return result


# ============================================================================
# RANDOM MALFUNCTION INJECTION (beyond pre-planned events)
# ============================================================================


def maybe_inject_random_malfunction(rng: np.random.Generator) -> tuple[str, float]:
    """Return (anomaly_type, multiplier) for random malfunctions.
    Returns ("", 1.0) most of the time.
    """
    if rng.random() < 0.006:  # ~0.6% chance per reading
        mtype = rng.choice(["spike", "drift", "stuck"])
        if mtype == "spike":
            return "spike", rng.uniform(2.0, 5.0)
        elif mtype == "drift":
            return "drift", rng.uniform(1.3, 1.8)
        else:
            return "stuck", 1.0
    return "", 1.0


# ============================================================================
# MAIN GENERATION
# ============================================================================


def generate_air_data(rng: np.random.Generator) -> list[list]:
    """Generate all air quality rows. Returns list of row-lists."""
    logger.info("Generating air quality data...")
    timestamps = air_timestamps(START_DATE, DAYS)
    generators = {s.station_id: AirQualityGenerator(s, rng) for s in AIR_STATIONS}

    all_rows = []
    for ts in timestamps:
        anomalies = get_anomaly_multiplier(ts)
        for sid, gen in generators.items():
            mult = 1.0
            # Pre-planned spike
            if sid in anomalies["air_anomaly"]:
                mult = anomalies["air_anomaly"][sid]
            # Policy intervention reduction
            elif sid in anomalies["air_reduction"]:
                mult = 1.0 - anomalies["air_reduction"][sid]
            rows = gen.generate(ts, anomaly_mult=mult)
            all_rows.extend(rows)

    logger.info(f"Air quality: {len(all_rows)} rows generated")
    return all_rows


def generate_water_data(rng: np.random.Generator) -> list[list]:
    """Generate all water quality rows."""
    logger.info("Generating water quality data...")
    timestamps = water_timestamps(START_DATE, DAYS)
    generators = {s.station_id: WaterQualityGenerator(s, rng) for s in WATER_STATIONS}

    all_rows = []
    for ts in timestamps:
        anomalies = get_anomaly_multiplier(ts)
        for sid, gen in generators.items():
            if sid in anomalies["water_anomaly"]:
                info = anomalies["water_anomaly"][sid]
                rows = gen.generate(
                    ts, anomaly_params=info["params"], anomaly_mult=info["multiplier"]
                )
            else:
                rows = gen.generate(ts)
            all_rows.extend(rows)

    logger.info(f"Water quality: {len(all_rows)} rows generated")
    return all_rows


def generate_noise_data(rng: np.random.Generator) -> list[list]:
    """Generate all noise rows."""
    logger.info("Generating noise data...")
    timestamps = noise_timestamps(START_DATE, DAYS)
    generators = {s.station_id: NoiseGenerator(s, rng) for s in NOISE_STATIONS}

    all_rows = []
    for ts in timestamps:
        anomalies = get_anomaly_multiplier(ts)
        for sid, gen in generators.items():
            mult = anomalies["noise_anomaly"].get(sid, 1.0)
            rows = gen.generate(ts, anomaly_mult=mult)
            all_rows.extend(rows)

    logger.info(f"Noise: {len(all_rows)} rows generated")
    return all_rows


def generate_ocems_data(rng: np.random.Generator) -> list[list]:
    """Generate all OCEMS rows."""
    logger.info("Generating OCEMS data...")
    timestamps = ocems_timestamps(START_DATE, DAYS)
    generators = {f.factory_id: OCEMSGenerator(f, rng) for f in FACTORIES}

    all_rows = []
    for ts in timestamps:
        anomalies = get_anomaly_multiplier(ts)
        for fid, gen in generators.items():
            if fid in anomalies["ocems_anomaly"]:
                info = anomalies["ocems_anomaly"][fid]
                rows = gen.generate(
                    ts,
                    anomaly_type_override=info["type"],
                    anomaly_mult=info["multiplier"],
                    anomaly_params=info["params"],
                )
            elif fid in anomalies["ocems_reduction"]:
                rows = gen.generate(
                    ts,
                    anomaly_type_override="reduction",
                    anomaly_mult=anomalies["ocems_reduction"][fid],
                )
            else:
                rows = gen.generate(ts)
            all_rows.extend(rows)

    logger.info(f"OCEMS: {len(all_rows)} rows generated")
    return all_rows


# ============================================================================
# CLICKHOUSE BULK INSERT
# ============================================================================


def insert_to_clickhouse(
    table: str,
    columns: list[str],
    rows: list[list],
    batch_size: int = CLICKHOUSE_BATCH_SIZE,
    ch_host: str = "localhost",
    ch_port: int = 8123,
    ch_user: str = "default",
    ch_password: str = "prithvinet_ch_pass",
    ch_database: str = "prithvinet",
):
    """Bulk insert rows into ClickHouse in batches."""
    import clickhouse_connect

    client = clickhouse_connect.get_client(
        host=ch_host,
        port=ch_port,
        username=ch_user,
        password=ch_password,
        database=ch_database,
    )

    total = len(rows)
    inserted = 0
    for i in range(0, total, batch_size):
        batch = rows[i : i + batch_size]
        client.insert(table, batch, column_names=columns)
        inserted += len(batch)
        pct = 100 * inserted / total
        logger.info(f"  {table}: {inserted}/{total} rows inserted ({pct:.1f}%)")

    client.close()
    logger.info(f"  {table}: COMPLETE ({total} rows)")


def write_to_csv(table: str, columns: list[str], rows: list[list], output_dir: str):
    """Write rows to a CSV file."""
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"{table}.csv")
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)
    logger.info(f"  Wrote {len(rows)} rows to {filepath}")


# ============================================================================
# COLUMN DEFINITIONS (must match ClickHouse DDL)
# ============================================================================

AIR_COLUMNS = [
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

WATER_COLUMNS = [
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

NOISE_COLUMNS = [
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

OCEMS_COLUMNS = [
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


# ============================================================================
# ENTRY POINT
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Generate 30 days of historical environmental data for PRITHVINET"
    )
    parser.add_argument(
        "--clickhouse", action="store_true", help="Insert directly to ClickHouse"
    )
    parser.add_argument(
        "--csv-dir", type=str, default=None, help="Write CSV files to this directory"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=CLICKHOUSE_BATCH_SIZE,
        help="ClickHouse batch size",
    )
    parser.add_argument("--ch-host", type=str, default="localhost")
    parser.add_argument("--ch-port", type=int, default=8123)
    parser.add_argument("--ch-user", type=str, default="default")
    parser.add_argument("--ch-password", type=str, default="prithvinet_ch_pass")
    parser.add_argument("--ch-database", type=str, default="prithvinet")
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--skip-air", action="store_true", help="Skip air quality generation"
    )
    parser.add_argument(
        "--skip-water", action="store_true", help="Skip water quality generation"
    )
    parser.add_argument(
        "--skip-noise", action="store_true", help="Skip noise generation"
    )
    parser.add_argument(
        "--skip-ocems", action="store_true", help="Skip OCEMS generation"
    )
    args = parser.parse_args()

    if not args.clickhouse and not args.csv_dir:
        logger.error("Specify --clickhouse and/or --csv-dir")
        sys.exit(1)

    rng = np.random.default_rng(args.seed)
    random.seed(args.seed)

    logger.info("=" * 70)
    logger.info("PRITHVINET Historical Data Generator")
    logger.info(
        f"  Period: {START_DATE.strftime('%Y-%m-%d')} to {REFERENCE_NOW.strftime('%Y-%m-%d')} ({DAYS} days)"
    )
    logger.info(
        f"  Stations: {len(AIR_STATIONS)} air, {len(WATER_STATIONS)} water, {len(NOISE_STATIONS)} noise"
    )
    logger.info(f"  Factories: {len(FACTORIES)} OCEMS")
    logger.info(f"  Anomaly events: {len(ANOMALY_EVENTS)}")
    logger.info(f"  Random seed: {args.seed}")
    logger.info("=" * 70)

    t0 = time.time()

    ch_kwargs = dict(
        batch_size=args.batch_size,
        ch_host=args.ch_host,
        ch_port=args.ch_port,
        ch_user=args.ch_user,
        ch_password=args.ch_password,
        ch_database=args.ch_database,
    )

    # --- AIR QUALITY ---
    if not args.skip_air:
        air_rows = generate_air_data(rng)
        if args.clickhouse:
            insert_to_clickhouse("air_quality_raw", AIR_COLUMNS, air_rows, **ch_kwargs)
        if args.csv_dir:
            write_to_csv("air_quality_raw", AIR_COLUMNS, air_rows, args.csv_dir)
        del air_rows  # free memory

    # --- WATER QUALITY ---
    if not args.skip_water:
        water_rows = generate_water_data(rng)
        if args.clickhouse:
            insert_to_clickhouse(
                "water_quality_raw", WATER_COLUMNS, water_rows, **ch_kwargs
            )
        if args.csv_dir:
            write_to_csv("water_quality_raw", WATER_COLUMNS, water_rows, args.csv_dir)
        del water_rows

    # --- NOISE ---
    if not args.skip_noise:
        noise_rows = generate_noise_data(rng)
        if args.clickhouse:
            insert_to_clickhouse("noise_raw", NOISE_COLUMNS, noise_rows, **ch_kwargs)
        if args.csv_dir:
            write_to_csv("noise_raw", NOISE_COLUMNS, noise_rows, args.csv_dir)
        del noise_rows

    # --- OCEMS ---
    if not args.skip_ocems:
        ocems_rows = generate_ocems_data(rng)
        if args.clickhouse:
            insert_to_clickhouse("ocems_raw", OCEMS_COLUMNS, ocems_rows, **ch_kwargs)
        if args.csv_dir:
            write_to_csv("ocems_raw", OCEMS_COLUMNS, ocems_rows, args.csv_dir)
        del ocems_rows

    elapsed = time.time() - t0
    logger.info(f"Historical data generation complete in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
