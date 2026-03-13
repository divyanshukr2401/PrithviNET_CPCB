#!/usr/bin/env python3
"""
PRITHVINET - Chhattisgarh IoT Sensor Data Simulator
====================================================
Simulates real-time environmental sensor data for 6 CG cities:
  Raipur, Bhilai, Korba, Bilaspur, Durg, Raigarh

Generates data for:
  - Air Quality: PM2.5, PM10, NO2, SO2, CO, O3, NH3, Pb (8 params)
  - Water Quality: pH, DO, BOD, COD, TSS, Turbidity, Conductivity, Temperature, Nitrates, Phosphates (10 params)
  - Noise: Leq, Lmax, Lmin, L10, L50, L90, Lden (7 metrics)
  - OCEMS: PM, SO2, NOx, CO (4 params per factory)

Features:
  - Diurnal variation (rush hour peaks, nighttime lows)
  - Zone-specific baselines (industrial > commercial > residential)
  - Sensor malfunction injection (stuck, spike, drift, dropout, calibration)
  - Async HTTP push to backend ingest API
  - Uses real CG station definitions from chhattisgarh_stations.py
"""

import asyncio
import random
import math
import json
import sys
import os
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

from loguru import logger

# Add project root to path so we can import station definitions
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from chhattisgarh_stations import (
    AIR_STATIONS, WATER_STATIONS, NOISE_STATIONS, FACTORIES,
    NAAQS_LIMITS, WQ_STANDARDS, CPCB_NOISE_LIMITS, OCEMS_EMISSION_LIMITS,
    Station, Factory, StationType, ZoneType,
)

# Try importing httpx for HTTP push (optional)
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    logger.warning("httpx not installed — HTTP push disabled, writing to file/console only")


# ============================================================================
# CONFIGURATION
# ============================================================================

INGEST_BASE_URL = os.getenv("INGEST_BASE_URL", "http://localhost:8000/api/v1/ingest")
SIMULATION_INTERVAL_SECONDS = 5  # For real-time mode
ENABLE_HTTP_PUSH = os.getenv("ENABLE_HTTP_PUSH", "false").lower() == "true"


# ============================================================================
# AIR QUALITY SENSOR
# ============================================================================

class AirQualitySensor:
    """
    Simulates a CAAQMS station in Chhattisgarh.
    8 parameters: PM2.5, PM10, NO2, SO2, CO, O3, NH3, Pb
    """

    # Zone-specific baselines (µg/m³ except CO in mg/m³)
    BASELINES = {
        "industrial": {"PM2.5": 85, "PM10": 160, "SO2": 35, "NO2": 40, "CO": 1800, "O3": 35, "NH3": 25, "Pb": 0.20},
        "commercial": {"PM2.5": 60, "PM10": 110, "SO2": 20, "NO2": 35, "CO": 1200, "O3": 42, "NH3": 20, "Pb": 0.12},
        "residential": {"PM2.5": 45, "PM10": 85, "SO2": 12, "NO2": 25, "CO": 800, "O3": 48, "NH3": 18, "Pb": 0.08},
        "silence": {"PM2.5": 40, "PM10": 80, "SO2": 10, "NO2": 20, "CO": 600, "O3": 50, "NH3": 15, "Pb": 0.06},
        "mining": {"PM2.5": 70, "PM10": 200, "SO2": 30, "NO2": 25, "CO": 1000, "O3": 30, "NH3": 12, "Pb": 0.25},
        "riverfront": {"PM2.5": 42, "PM10": 78, "SO2": 10, "NO2": 22, "CO": 700, "O3": 52, "NH3": 16, "Pb": 0.07},
    }

    # Noise stds for gaussian variation per parameter
    NOISE_STD = {"PM2.5": 12, "PM10": 25, "SO2": 6, "NO2": 8, "CO": 200, "O3": 10, "NH3": 5, "Pb": 0.03}

    PARAMS = ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3", "NH3", "Pb"]
    UNITS = {"PM2.5": "µg/m³", "PM10": "µg/m³", "NO2": "µg/m³", "SO2": "µg/m³",
             "CO": "µg/m³", "O3": "µg/m³", "NH3": "µg/m³", "Pb": "µg/m³"}

    def __init__(self, station: Station):
        self.station = station
        zone = station.zone.value
        self.baseline = self.BASELINES.get(zone, self.BASELINES["residential"])
        self.is_malfunctioning = False
        self.malfunction_type: Optional[str] = None
        self._stuck_values: dict = {}

    def generate_readings(self, timestamp: Optional[datetime] = None) -> list[dict]:
        """Generate readings for all 8 parameters at one timestamp."""
        ts = timestamp or datetime.utcnow()
        diurnal = self._diurnal_factor(ts)
        is_malfunction = self._maybe_malfunction()

        readings = []
        for param in self.PARAMS:
            base = self.baseline[param]
            noise_std = self.NOISE_STD[param]

            if is_malfunction:
                value, anomaly_type, quality_flag = self._malfunction_value(param, base, diurnal)
            else:
                # O3 is inversely related to traffic (peaks midday, not rush hour)
                if param == "O3":
                    factor = 2.0 - diurnal  # inverse diurnal
                else:
                    factor = diurnal

                value = max(0, base * factor + random.gauss(0, noise_std))
                anomaly_type = ""
                quality_flag = "valid"

            aqi = self._sub_aqi(param, value)

            readings.append({
                "station_id": self.station.station_id,
                "timestamp": ts.isoformat(),
                "parameter": param,
                "value": round(value, 3),
                "unit": self.UNITS[param],
                "aqi": aqi,
                "city": self.station.city,
                "latitude": self.station.latitude,
                "longitude": self.station.longitude,
                "zone": self.station.zone.value,
                "is_anomaly": anomaly_type != "",
                "anomaly_type": anomaly_type,
                "quality_flag": quality_flag,
            })

        return readings

    def _diurnal_factor(self, ts: datetime) -> float:
        hour = ts.hour + ts.minute / 60.0
        # Rush hours: 8-10 AM and 5-8 PM
        morning = 1.3 * math.exp(-0.5 * ((hour - 9) / 1.5) ** 2)
        evening = 1.2 * math.exp(-0.5 * ((hour - 18.5) / 2.0) ** 2)
        # Night low: 1-5 AM
        night = -0.35 * math.exp(-0.5 * ((hour - 3) / 2.0) ** 2)
        return 1.0 + morning + evening + night + random.uniform(-0.05, 0.05)

    def _maybe_malfunction(self) -> bool:
        if random.random() < 0.008:  # 0.8% chance per tick
            self.is_malfunctioning = True
            self.malfunction_type = random.choice(["stuck", "spike", "drift", "dropout", "calibration"])
            return True
        elif self.is_malfunctioning and random.random() < 0.12:
            self.is_malfunctioning = False
            self.malfunction_type = None
            self._stuck_values = {}
        return self.is_malfunctioning

    def _malfunction_value(self, param: str, base: float, diurnal: float) -> tuple[float, str, str]:
        mtype = self.malfunction_type
        if mtype == "stuck":
            if param not in self._stuck_values:
                self._stuck_values[param] = base * diurnal + random.gauss(0, 2)
            return self._stuck_values[param], "stuck", "suspect"
        elif mtype == "spike":
            return base * random.uniform(5, 15), "spike", "suspect"
        elif mtype == "drift":
            drift = 1.5 + random.uniform(0, 0.5)
            return max(0, base * diurnal * drift + random.gauss(0, 3)), "drift", "suspect"
        elif mtype == "dropout":
            return 0.0, "dropout", "invalid"
        elif mtype == "calibration":
            offset = base * random.uniform(0.2, 0.4)
            return max(0, base * diurnal + offset), "calibration", "suspect"
        return max(0, base * diurnal), "", "valid"

    def _sub_aqi(self, param: str, value: float) -> int:
        """Simplified Indian NAQI sub-index for a single parameter."""
        breakpoints = {
            "PM2.5": [(0, 30, 0, 50), (30, 60, 50, 100), (60, 90, 100, 200), (90, 120, 200, 300), (120, 250, 300, 400), (250, 500, 400, 500)],
            "PM10": [(0, 50, 0, 50), (50, 100, 50, 100), (100, 250, 100, 200), (250, 350, 200, 300), (350, 430, 300, 400), (430, 600, 400, 500)],
            "NO2": [(0, 40, 0, 50), (40, 80, 50, 100), (80, 180, 100, 200), (180, 280, 200, 300), (280, 400, 300, 400), (400, 600, 400, 500)],
            "SO2": [(0, 40, 0, 50), (40, 80, 50, 100), (80, 380, 100, 200), (380, 800, 200, 300), (800, 1600, 300, 400), (1600, 2400, 400, 500)],
            "CO": [(0, 1000, 0, 50), (1000, 2000, 50, 100), (2000, 10000, 100, 200), (10000, 17000, 200, 300), (17000, 34000, 300, 400), (34000, 50000, 400, 500)],
            "O3": [(0, 50, 0, 50), (50, 100, 50, 100), (100, 168, 100, 200), (168, 208, 200, 300), (208, 748, 300, 400), (748, 1000, 400, 500)],
            "NH3": [(0, 200, 0, 50), (200, 400, 50, 100), (400, 800, 100, 200), (800, 1200, 200, 300), (1200, 1800, 300, 400), (1800, 2400, 400, 500)],
            "Pb": [(0, 0.5, 0, 50), (0.5, 1.0, 50, 100), (1.0, 2.0, 100, 200), (2.0, 3.0, 200, 300), (3.0, 3.5, 300, 400), (3.5, 5.0, 400, 500)],
        }
        bps = breakpoints.get(param, [(0, 100, 0, 100)])
        for c_lo, c_hi, i_lo, i_hi in bps:
            if c_lo <= value <= c_hi:
                return int(i_lo + (value - c_lo) * (i_hi - i_lo) / max(1, c_hi - c_lo))
        return 500 if value > bps[-1][1] else 0


# ============================================================================
# WATER QUALITY SENSOR
# ============================================================================

class WaterQualitySensor:
    """
    Simulates a water quality monitoring station on CG rivers.
    10 parameters: pH, DO, BOD, COD, TSS, Turbidity, Conductivity, Temperature, Nitrates, Phosphates
    """

    # Zone-specific baselines
    BASELINES = {
        "riverfront": {"pH": 7.2, "DO": 6.5, "BOD": 2.5, "COD": 15, "TSS": 40, "Turbidity": 8, "Conductivity": 400, "Temperature": 26, "Nitrates": 8, "Phosphates": 0.8},
        "industrial": {"pH": 6.8, "DO": 4.5, "BOD": 5.0, "COD": 30, "TSS": 80, "Turbidity": 20, "Conductivity": 700, "Temperature": 28, "Nitrates": 18, "Phosphates": 2.5},
        "commercial": {"pH": 7.0, "DO": 5.5, "BOD": 3.5, "COD": 20, "TSS": 55, "Turbidity": 12, "Conductivity": 500, "Temperature": 27, "Nitrates": 12, "Phosphates": 1.5},
    }
    NOISE_STD = {"pH": 0.3, "DO": 1.0, "BOD": 0.8, "COD": 5, "TSS": 10, "Turbidity": 4, "Conductivity": 60, "Temperature": 1.5, "Nitrates": 3, "Phosphates": 0.4}
    UNITS = {"pH": "pH", "DO": "mg/L", "BOD": "mg/L", "COD": "mg/L", "TSS": "mg/L", "Turbidity": "NTU", "Conductivity": "µS/cm", "Temperature": "°C", "Nitrates": "mg/L", "Phosphates": "mg/L"}
    PARAMS = ["pH", "DO", "BOD", "COD", "TSS", "Turbidity", "Conductivity", "Temperature", "Nitrates", "Phosphates"]

    def __init__(self, station: Station):
        self.station = station
        zone = station.zone.value
        self.baseline = self.BASELINES.get(zone, self.BASELINES["riverfront"])
        self.is_malfunctioning = False
        self.malfunction_type: Optional[str] = None

    def generate_readings(self, timestamp: Optional[datetime] = None) -> list[dict]:
        ts = timestamp or datetime.utcnow()
        # Water quality has mild diurnal variation (temperature-driven)
        hour = ts.hour + ts.minute / 60.0
        temp_factor = 1.0 + 0.1 * math.sin(2 * math.pi * (hour - 14) / 24)  # peak at 2 PM

        is_malfunction = self._maybe_malfunction()
        readings = []

        for param in self.PARAMS:
            base = self.baseline[param]
            std = self.NOISE_STD[param]

            if is_malfunction:
                value = base * random.uniform(1.5, 3.0) if random.random() > 0.5 else 0.0
                anomaly_type = self.malfunction_type or "spike"
                quality_flag = "suspect"
            else:
                if param == "Temperature":
                    value = base * temp_factor + random.gauss(0, std)
                elif param == "DO":
                    # DO decreases with temperature
                    value = base * (2.0 - temp_factor) + random.gauss(0, std)
                    value = max(0, value)
                elif param == "pH":
                    value = base + random.gauss(0, std)
                    value = max(5.5, min(9.5, value))
                else:
                    value = max(0, base + random.gauss(0, std))
                anomaly_type = ""
                quality_flag = "valid"

            # Simple WQI sub-index
            wqi = self._sub_wqi(param, value)

            readings.append({
                "station_id": self.station.station_id,
                "timestamp": ts.isoformat(),
                "parameter": param,
                "value": round(value, 3),
                "unit": self.UNITS[param],
                "wqi": round(wqi, 1),
                "river_name": self.station.river_name or "",
                "city": self.station.city,
                "latitude": self.station.latitude,
                "longitude": self.station.longitude,
                "is_anomaly": anomaly_type != "",
                "anomaly_type": anomaly_type,
                "quality_flag": quality_flag,
            })

        return readings

    def _maybe_malfunction(self) -> bool:
        if random.random() < 0.005:
            self.is_malfunctioning = True
            self.malfunction_type = random.choice(["spike", "drift", "dropout"])
            return True
        elif self.is_malfunctioning and random.random() < 0.15:
            self.is_malfunctioning = False
            self.malfunction_type = None
        return self.is_malfunctioning

    def _sub_wqi(self, param: str, value: float) -> float:
        """Simple WQI sub-index (0-100, 100=best)."""
        limits = WQ_STANDARDS.get(param, {})
        if "max" in limits:
            return max(0, 100 * (1 - value / limits["max"]))
        elif "min" in limits:
            return min(100, 100 * value / limits["min"]) if limits["min"] > 0 else 50
        return 50.0


# ============================================================================
# NOISE SENSOR
# ============================================================================

class NoiseSensor:
    """
    Simulates noise monitoring with CNOSSOS-EU metrics + Lden computation.
    7 metrics: Leq, Lmax, Lmin, L10, L50, L90, Lden
    """

    # Zone baselines for Leq (dB(A))
    BASELINES = {
        "industrial": 70,
        "commercial": 60,
        "residential": 48,
        "silence": 42,
    }

    METRICS = ["Leq", "Lmax", "Lmin", "L10", "L50", "L90", "Lden"]

    def __init__(self, station: Station):
        self.station = station
        zone = station.zone.value
        self.base_leq = self.BASELINES.get(zone, 50)
        self.limits = CPCB_NOISE_LIMITS.get(zone, {"day": 65, "night": 55})
        self.is_malfunctioning = False
        self.malfunction_type: Optional[str] = None
        # Keep a buffer for Lden calculation (24h of hourly Leq values)
        self._hourly_leq_buffer: list[float] = []

    def generate_readings(self, timestamp: Optional[datetime] = None) -> list[dict]:
        ts = timestamp or datetime.utcnow()
        hour = ts.hour + ts.minute / 60.0
        is_night = hour < 6 or hour >= 22
        is_evening = 19 <= hour < 22

        is_malfunction = self._maybe_malfunction()

        if is_malfunction:
            leq = self.base_leq + random.uniform(20, 40)  # abnormally high
            anomaly_type = self.malfunction_type or "spike"
            quality_flag = "suspect"
        else:
            # Diurnal noise pattern
            if is_night:
                factor = 0.7 + random.uniform(-0.05, 0.05)
            elif 7 <= hour <= 9 or 17 <= hour <= 19:
                factor = 1.25 + random.uniform(-0.05, 0.1)
            else:
                factor = 1.0 + random.uniform(-0.1, 0.1)

            leq = self.base_leq * factor + random.gauss(0, 3)
            anomaly_type = ""
            quality_flag = "valid"

        # Derive other metrics from Leq
        lmax = leq + random.uniform(5, 18)
        lmin = max(25, leq - random.uniform(8, 20))
        l10 = leq + random.uniform(2, 7)
        l50 = leq + random.uniform(-2, 2)
        l90 = max(25, leq - random.uniform(5, 12))

        # Lden: day-evening-night weighted metric
        self._hourly_leq_buffer.append(leq)
        if len(self._hourly_leq_buffer) > 24:
            self._hourly_leq_buffer = self._hourly_leq_buffer[-24:]
        lden = self._compute_lden()

        # Compliance check
        limit = self.limits["night"] if is_night else self.limits["day"]
        is_exceedance = leq > limit

        day_limit = self.limits["day"]
        night_limit = self.limits["night"]

        readings = []
        metrics_values = {
            "Leq": leq, "Lmax": lmax, "Lmin": lmin,
            "L10": l10, "L50": l50, "L90": l90, "Lden": lden,
        }

        for metric in self.METRICS:
            val = metrics_values[metric]
            readings.append({
                "station_id": self.station.station_id,
                "timestamp": ts.isoformat(),
                "metric": metric,
                "value": round(val, 1),
                "city": self.station.city,
                "latitude": self.station.latitude,
                "longitude": self.station.longitude,
                "zone": self.station.zone.value,
                "day_limit": day_limit,
                "night_limit": night_limit,
                "is_exceedance": is_exceedance and metric == "Leq",
                "is_anomaly": anomaly_type != "",
                "anomaly_type": anomaly_type,
                "quality_flag": quality_flag,
            })

        return readings

    def _compute_lden(self) -> float:
        """
        Compute Lden (day-evening-night indicator) per EU Directive 2002/49/EC.
        Lden = 10 * log10( (12*10^(Ld/10) + 4*10^((Le+5)/10) + 8*10^((Ln+10)/10) ) / 24 )
        """
        buf = self._hourly_leq_buffer
        if len(buf) < 3:
            return buf[-1] if buf else self.base_leq

        # Split buffer into day (7-19), evening (19-22), night (22-7) approximation
        # Use available data as proxy
        n = len(buf)
        day_vals = buf[:max(1, n // 2)]
        eve_vals = buf[max(1, n // 2):max(2, 3 * n // 4)]
        night_vals = buf[max(2, 3 * n // 4):]

        def energy_avg(vals):
            if not vals:
                return self.base_leq
            return 10 * math.log10(sum(10 ** (v / 10) for v in vals) / len(vals))

        ld = energy_avg(day_vals)
        le = energy_avg(eve_vals)
        ln = energy_avg(night_vals)

        lden = 10 * math.log10(
            (12 * 10 ** (ld / 10) + 4 * 10 ** ((le + 5) / 10) + 8 * 10 ** ((ln + 10) / 10)) / 24
        )
        return lden

    def _maybe_malfunction(self) -> bool:
        if random.random() < 0.005:
            self.is_malfunctioning = True
            self.malfunction_type = random.choice(["spike", "stuck", "dropout"])
            return True
        elif self.is_malfunctioning and random.random() < 0.15:
            self.is_malfunctioning = False
            self.malfunction_type = None
        return self.is_malfunctioning


# ============================================================================
# OCEMS FACTORY SENSOR
# ============================================================================

class OCEMSSensor:
    """
    Simulates OCEMS (Online Continuous Emission Monitoring System) for a factory.
    Parameters: PM, SO2, NOx, CO (stack emissions in mg/Nm³)
    """

    # Base emission levels as fraction of limit (0.5 = 50% of limit normally)
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

    def __init__(self, factory: Factory):
        self.factory = factory
        self.limits = OCEMS_EMISSION_LIMITS.get(factory.industry_type, {})
        self.base_frac = self.BASE_FRACTION.get(factory.industry_type, 0.5)
        self.is_malfunctioning = False
        self.malfunction_type: Optional[str] = None
        self._stuck_values: dict = {}
        self.sensor_health = 100.0

    def generate_readings(self, timestamp: Optional[datetime] = None) -> list[dict]:
        ts = timestamp or datetime.utcnow()
        is_malfunction = self._maybe_malfunction()

        readings = []
        for param in self.factory.emission_params:
            limit = self.limits.get(param, 100)
            base_val = limit * self.base_frac

            if is_malfunction:
                value, anomaly_type, qf, health = self._malfunction_value(param, base_val, limit)
            else:
                # Normal: Gaussian around baseline with slight diurnal variation
                hour = ts.hour
                # Factories run 24/7 but have shift-change bumps
                shift_factor = 1.0 + 0.1 * math.sin(2 * math.pi * (hour - 8) / 8)
                value = max(0, base_val * shift_factor + random.gauss(0, base_val * 0.1))
                anomaly_type = ""
                qf = "valid"
                health = min(100, self.sensor_health + random.uniform(0, 0.5))
                self.sensor_health = health

            exceedance_pct = max(0, (value / limit - 1) * 100) if limit > 0 else 0

            readings.append({
                "factory_id": self.factory.factory_id,
                "timestamp": ts.isoformat(),
                "parameter": param,
                "value": round(value, 2),
                "unit": "mg/Nm³",
                "emission_limit": limit,
                "exceedance_pct": round(exceedance_pct, 2),
                "industry_type": self.factory.industry_type,
                "city": self.factory.city,
                "latitude": self.factory.latitude,
                "longitude": self.factory.longitude,
                "dahs_status": "online" if not is_malfunction else "degraded",
                "sensor_health": round(self.sensor_health, 1),
                "is_anomaly": anomaly_type != "",
                "anomaly_type": anomaly_type,
                "quality_flag": qf,
            })

        return readings

    def _maybe_malfunction(self) -> bool:
        if random.random() < 0.01:
            self.is_malfunctioning = True
            self.malfunction_type = random.choice(["stuck", "spike", "drift", "flatline", "calibration_needed"])
            self.sensor_health = max(0, self.sensor_health - random.uniform(10, 30))
            return True
        elif self.is_malfunctioning and random.random() < 0.08:
            self.is_malfunctioning = False
            self.malfunction_type = None
            self._stuck_values = {}
            self.sensor_health = min(100, self.sensor_health + random.uniform(5, 15))
        return self.is_malfunctioning

    def _malfunction_value(self, param: str, base: float, limit: float) -> tuple[float, str, str, float]:
        mtype = self.malfunction_type
        health = max(0, self.sensor_health - random.uniform(0, 2))
        if mtype == "stuck":
            if param not in self._stuck_values:
                self._stuck_values[param] = base + random.gauss(0, 1)
            return self._stuck_values[param], "stuck", "suspect", health
        elif mtype == "spike":
            return limit * random.uniform(2, 5), "spike", "suspect", health
        elif mtype == "drift":
            return max(0, base * random.uniform(1.3, 2.0)), "drift", "suspect", health
        elif mtype == "flatline":
            return 0.0, "flatline", "invalid", health
        elif mtype == "calibration_needed":
            return max(0, base + base * random.uniform(0.15, 0.35)), "calibration_needed", "suspect", health
        return base, "", "valid", health


# ============================================================================
# SENSOR NETWORK
# ============================================================================

class ChhattisagrSensorNetwork:
    """Complete sensor network for all 6 CG cities."""

    def __init__(self):
        self.air_sensors = [AirQualitySensor(s) for s in AIR_STATIONS]
        self.water_sensors = [WaterQualitySensor(s) for s in WATER_STATIONS]
        self.noise_sensors = [NoiseSensor(s) for s in NOISE_STATIONS]
        self.ocems_sensors = [OCEMSSensor(f) for f in FACTORIES]

        logger.info(
            f"CG Sensor Network initialized: "
            f"{len(self.air_sensors)} air, {len(self.water_sensors)} water, "
            f"{len(self.noise_sensors)} noise, {len(self.ocems_sensors)} OCEMS"
        )

    def generate_all_readings(self, timestamp: Optional[datetime] = None) -> dict:
        """Generate one tick of readings from all sensors."""
        ts = timestamp or datetime.utcnow()
        return {
            "timestamp": ts.isoformat(),
            "air": [r for s in self.air_sensors for r in s.generate_readings(ts)],
            "water": [r for s in self.water_sensors for r in s.generate_readings(ts)],
            "noise": [r for s in self.noise_sensors for r in s.generate_readings(ts)],
            "ocems": [r for s in self.ocems_sensors for r in s.generate_readings(ts)],
        }


# ============================================================================
# HTTP PUSH CLIENT
# ============================================================================

async def push_readings(readings: dict, client: Optional["httpx.AsyncClient"] = None):
    """Push readings to backend ingest API via HTTP POST."""
    if not client:
        return

    endpoints = {
        "air": f"{INGEST_BASE_URL}/air",
        "water": f"{INGEST_BASE_URL}/water",
        "noise": f"{INGEST_BASE_URL}/noise",
        "ocems": f"{INGEST_BASE_URL}/ocems",
    }

    for data_type, url in endpoints.items():
        data = readings.get(data_type, [])
        if not data:
            continue
        try:
            resp = await client.post(url, json=data, timeout=10)
            if resp.status_code != 200:
                logger.warning(f"Ingest {data_type} returned {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.error(f"Failed to push {data_type} readings: {e}")


# ============================================================================
# MAIN SIMULATION LOOP
# ============================================================================

async def run_simulation(
    output_file: Optional[str] = None,
    console_output: bool = True,
    http_push: bool = False,
    interval: int = 5,
    max_iterations: Optional[int] = None,
):
    """Run continuous real-time sensor simulation."""
    network = ChhattisagrSensorNetwork()
    iteration = 0

    client = None
    if http_push and HTTPX_AVAILABLE:
        client = httpx.AsyncClient()
        logger.info(f"HTTP push enabled → {INGEST_BASE_URL}")

    logger.info(f"Starting PRITHVINET CG simulation (interval: {interval}s)")

    try:
        while True:
            iteration += 1
            if max_iterations and iteration > max_iterations:
                break

            readings = network.generate_all_readings()

            # Count anomalies
            anomalies = sum(
                1 for r in readings["air"] + readings["ocems"]
                if r.get("is_anomaly")
            )

            if console_output:
                total = sum(len(readings[k]) for k in ["air", "water", "noise", "ocems"])
                logger.info(
                    f"Tick {iteration}: {total} readings "
                    f"(air={len(readings['air'])}, water={len(readings['water'])}, "
                    f"noise={len(readings['noise'])}, ocems={len(readings['ocems'])}) "
                    f"anomalies={anomalies}"
                )

            # HTTP push
            if http_push and client:
                await push_readings(readings, client)

            # File output
            if output_file:
                with open(output_file, "a") as f:
                    f.write(json.dumps(readings, default=str) + "\n")

            await asyncio.sleep(interval)

    except KeyboardInterrupt:
        logger.info("Simulation stopped by user")
    finally:
        if client:
            await client.aclose()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="PRITHVINET Chhattisgarh Sensor Simulator")
    parser.add_argument("--output", "-o", help="Output JSONL file path")
    parser.add_argument("--interval", "-i", type=int, default=5, help="Interval between ticks (seconds)")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress console output")
    parser.add_argument("--http-push", action="store_true", help="Enable HTTP push to ingest API")
    parser.add_argument("--max-iterations", type=int, default=None, help="Max simulation ticks (None = infinite)")
    args = parser.parse_args()

    asyncio.run(run_simulation(
        output_file=args.output,
        console_output=not args.quiet,
        http_push=args.http_push or ENABLE_HTTP_PUSH,
        interval=args.interval,
        max_iterations=args.max_iterations,
    ))


if __name__ == "__main__":
    main()
