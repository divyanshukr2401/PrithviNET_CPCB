#!/usr/bin/env python3
"""
PRITHVINET - IoT Sensor Data Simulator

Simulates real-time environmental sensor data for:
- Air Quality (PM2.5, PM10, SO2, NO2, CO, O3, AQI)
- Water Quality (pH, DO, BOD, COD, TDS, Turbidity, Conductivity)
- Noise Levels (LAeq, LAmax, LAmin, L10, L90, L50)

This simulator generates realistic data patterns including:
- Diurnal variations (day/night cycles)
- Industrial emission spikes (OCEMS pattern)
- Random sensor malfunctions for Auto-Healer testing
- Geographic clustering based on station location
"""

import asyncio
import random
import math
from datetime import datetime, timedelta
from typing import Optional
import json

from faker import Faker
from loguru import logger

fake = Faker()

# Configuration
NUM_AIR_STATIONS = 15
NUM_WATER_STATIONS = 10
NUM_NOISE_STATIONS = 8
SIMULATION_INTERVAL_SECONDS = 5  # Generate data every 5 seconds


class SensorSimulator:
    """Base class for environmental sensor simulation."""
    
    def __init__(self, station_id: str, lat: float, lon: float, station_type: str):
        self.station_id = station_id
        self.lat = lat
        self.lon = lon
        self.station_type = station_type
        self.is_malfunctioning = False
        self.malfunction_type: Optional[str] = None
        
    def _get_diurnal_factor(self) -> float:
        """Calculate time-of-day factor for realistic patterns."""
        hour = datetime.now().hour
        # Peak pollution during morning (8-10) and evening (17-20) rush hours
        if 8 <= hour <= 10 or 17 <= hour <= 20:
            return 1.3 + random.uniform(0, 0.2)
        # Low pollution during night (1-5)
        elif 1 <= hour <= 5:
            return 0.6 + random.uniform(0, 0.1)
        else:
            return 1.0 + random.uniform(-0.1, 0.1)
    
    def _maybe_malfunction(self) -> bool:
        """Randomly trigger sensor malfunction (1% chance)."""
        if random.random() < 0.01:
            self.is_malfunctioning = True
            self.malfunction_type = random.choice([
                "stuck_value",      # Sensor reading stuck at constant
                "spike",            # Sudden unrealistic spike
                "zero_reading",     # Sensor reporting zeros
                "drift",            # Gradual drift from calibration
                "communication_error"  # No data transmission
            ])
            return True
        elif self.is_malfunctioning and random.random() < 0.1:
            # 10% chance to recover from malfunction
            self.is_malfunctioning = False
            self.malfunction_type = None
        return self.is_malfunctioning


class AirQualitySensor(SensorSimulator):
    """Simulates CPCB-style Continuous Ambient Air Quality Monitoring (CAAQM)."""
    
    # Baseline values for different station types (industrial, residential, commercial)
    BASELINES = {
        "industrial": {"pm25": 80, "pm10": 150, "so2": 40, "no2": 45, "co": 1.5, "o3": 35},
        "residential": {"pm25": 45, "pm10": 90, "so2": 15, "no2": 25, "co": 0.8, "o3": 45},
        "commercial": {"pm25": 60, "pm10": 120, "so2": 25, "no2": 35, "co": 1.2, "o3": 40},
    }
    
    def __init__(self, station_id: str, lat: float, lon: float, zone_type: str = "residential"):
        super().__init__(station_id, lat, lon, "air_quality")
        self.zone_type = zone_type
        self.baseline = self.BASELINES.get(zone_type, self.BASELINES["residential"])
        self._stuck_values = {}
        
    def generate_reading(self) -> dict:
        """Generate a single air quality reading."""
        timestamp = datetime.utcnow().isoformat()
        diurnal = self._get_diurnal_factor()
        
        if self._maybe_malfunction():
            return self._generate_malfunction_reading(timestamp)
        
        # Normal readings with realistic variation
        pm25 = max(0, self.baseline["pm25"] * diurnal + random.gauss(0, 10))
        pm10 = max(0, self.baseline["pm10"] * diurnal + random.gauss(0, 20))
        so2 = max(0, self.baseline["so2"] * diurnal + random.gauss(0, 5))
        no2 = max(0, self.baseline["no2"] * diurnal + random.gauss(0, 8))
        co = max(0, self.baseline["co"] * diurnal + random.gauss(0, 0.2))
        o3 = max(0, self.baseline["o3"] * (2 - diurnal) + random.gauss(0, 10))  # O3 inversely related
        
        # Calculate AQI (simplified Indian AQI)
        aqi = self._calculate_aqi(pm25, pm10, so2, no2, co, o3)
        
        return {
            "station_id": self.station_id,
            "timestamp": timestamp,
            "lat": self.lat,
            "lon": self.lon,
            "zone_type": self.zone_type,
            "parameters": {
                "pm25": round(pm25, 2),
                "pm10": round(pm10, 2),
                "so2": round(so2, 2),
                "no2": round(no2, 2),
                "co": round(co, 3),
                "o3": round(o3, 2),
            },
            "aqi": round(aqi),
            "aqi_category": self._aqi_category(aqi),
            "sensor_status": "normal",
            "data_quality_flag": "valid"
        }
    
    def _generate_malfunction_reading(self, timestamp: str) -> dict:
        """Generate malfunction data for OCEMS Auto-Healer testing."""
        if self.malfunction_type == "communication_error":
            return {
                "station_id": self.station_id,
                "timestamp": timestamp,
                "error": "COMMUNICATION_TIMEOUT",
                "sensor_status": "error",
                "malfunction_type": self.malfunction_type
            }
        
        # Stuck value malfunction
        if self.malfunction_type == "stuck_value":
            if not self._stuck_values:
                self._stuck_values = {
                    "pm25": random.uniform(30, 100),
                    "pm10": random.uniform(60, 200),
                }
            params = {"pm25": self._stuck_values["pm25"], "pm10": self._stuck_values["pm10"]}
        
        # Spike malfunction (unrealistic values)
        elif self.malfunction_type == "spike":
            params = {
                "pm25": random.uniform(800, 1500),  # Unrealistically high
                "pm10": random.uniform(1500, 3000),
            }
        
        # Zero readings
        elif self.malfunction_type == "zero_reading":
            params = {"pm25": 0.0, "pm10": 0.0, "so2": 0.0, "no2": 0.0}
        
        else:  # drift
            diurnal = self._get_diurnal_factor()
            drift_factor = 1.5 + random.uniform(0, 0.5)
            params = {
                "pm25": round(self.baseline["pm25"] * diurnal * drift_factor, 2),
                "pm10": round(self.baseline["pm10"] * diurnal * drift_factor, 2),
            }
        
        return {
            "station_id": self.station_id,
            "timestamp": timestamp,
            "lat": self.lat,
            "lon": self.lon,
            "parameters": params,
            "sensor_status": "malfunction",
            "malfunction_type": self.malfunction_type,
            "data_quality_flag": "suspect"
        }
    
    def _calculate_aqi(self, pm25, pm10, so2, no2, co, o3) -> float:
        """Simplified Indian AQI calculation (PM2.5 dominant)."""
        # Sub-indices (simplified linear interpolation)
        pm25_si = (pm25 / 60) * 100 if pm25 <= 60 else 100 + ((pm25 - 60) / 30) * 100
        return min(500, pm25_si)
    
    def _aqi_category(self, aqi: float) -> str:
        if aqi <= 50: return "Good"
        elif aqi <= 100: return "Satisfactory"
        elif aqi <= 200: return "Moderate"
        elif aqi <= 300: return "Poor"
        elif aqi <= 400: return "Very Poor"
        else: return "Severe"


class WaterQualitySensor(SensorSimulator):
    """Simulates water quality monitoring stations (rivers, groundwater)."""
    
    def __init__(self, station_id: str, lat: float, lon: float, water_body: str = "river"):
        super().__init__(station_id, lat, lon, "water_quality")
        self.water_body = water_body
        
    def generate_reading(self) -> dict:
        """Generate water quality reading."""
        timestamp = datetime.utcnow().isoformat()
        
        if self._maybe_malfunction():
            return {
                "station_id": self.station_id,
                "timestamp": timestamp,
                "sensor_status": "malfunction",
                "malfunction_type": self.malfunction_type
            }
        
        # Realistic water quality parameters
        ph = 7.0 + random.gauss(0, 0.5)
        ph = max(5.5, min(9.5, ph))
        
        do = max(0, 6.5 + random.gauss(0, 1.5))  # Dissolved Oxygen mg/L
        bod = max(0, 3.0 + random.gauss(0, 1.0))  # BOD mg/L
        cod = max(0, bod * 2.5 + random.gauss(0, 5))  # COD mg/L
        tds = max(0, 350 + random.gauss(0, 100))  # Total Dissolved Solids mg/L
        turbidity = max(0, 15 + random.gauss(0, 8))  # NTU
        conductivity = max(0, 450 + random.gauss(0, 100))  # μS/cm
        temperature = 25 + random.gauss(0, 3)  # °C
        
        # Water Quality Index (simplified)
        wqi = self._calculate_wqi(ph, do, bod, tds, turbidity)
        
        return {
            "station_id": self.station_id,
            "timestamp": timestamp,
            "lat": self.lat,
            "lon": self.lon,
            "water_body": self.water_body,
            "parameters": {
                "ph": round(ph, 2),
                "dissolved_oxygen": round(do, 2),
                "bod": round(bod, 2),
                "cod": round(cod, 2),
                "tds": round(tds, 1),
                "turbidity": round(turbidity, 2),
                "conductivity": round(conductivity, 1),
                "temperature": round(temperature, 1),
            },
            "wqi": round(wqi),
            "wqi_category": self._wqi_category(wqi),
            "sensor_status": "normal",
            "data_quality_flag": "valid"
        }
    
    def _calculate_wqi(self, ph, do, bod, tds, turbidity) -> float:
        """Simplified Water Quality Index."""
        # Weighted average of normalized parameters
        ph_score = 100 - abs(ph - 7) * 20
        do_score = min(100, do * 15)
        bod_score = max(0, 100 - bod * 10)
        tds_score = max(0, 100 - tds / 10)
        
        return (ph_score * 0.3 + do_score * 0.3 + bod_score * 0.25 + tds_score * 0.15)
    
    def _wqi_category(self, wqi: float) -> str:
        if wqi >= 80: return "Excellent"
        elif wqi >= 60: return "Good"
        elif wqi >= 40: return "Fair"
        elif wqi >= 20: return "Poor"
        else: return "Very Poor"


class NoiseSensor(SensorSimulator):
    """Simulates CNOSSOS-EU compliant noise monitoring."""
    
    def __init__(self, station_id: str, lat: float, lon: float, zone_type: str = "residential"):
        super().__init__(station_id, lat, lon, "noise")
        self.zone_type = zone_type
        
        # CPCB noise standards (dB)
        self.standards = {
            "industrial": {"day": 75, "night": 70},
            "commercial": {"day": 65, "night": 55},
            "residential": {"day": 55, "night": 45},
            "silence": {"day": 50, "night": 40},  # Schools, hospitals
        }
        
    def generate_reading(self) -> dict:
        """Generate noise level reading with CNOSSOS-EU metrics."""
        timestamp = datetime.utcnow().isoformat()
        hour = datetime.now().hour
        is_night = hour < 6 or hour >= 22
        
        if self._maybe_malfunction():
            return {
                "station_id": self.station_id,
                "timestamp": timestamp,
                "sensor_status": "malfunction",
                "malfunction_type": self.malfunction_type
            }
        
        # Base noise level depends on zone and time
        standard = self.standards.get(self.zone_type, self.standards["residential"])
        base_level = standard["night"] if is_night else standard["day"]
        
        # Add realistic variations
        laeq = base_level + random.gauss(-5, 8)  # Equivalent continuous level
        lamax = laeq + random.uniform(5, 20)  # Maximum level
        lamin = max(30, laeq - random.uniform(10, 25))  # Minimum level
        
        # Statistical noise levels (CNOSSOS-EU)
        l10 = laeq + random.uniform(3, 8)   # Level exceeded 10% of time
        l50 = laeq + random.uniform(-2, 2)  # Median level
        l90 = laeq - random.uniform(5, 12)  # Background level (exceeded 90%)
        
        # Check compliance
        limit = standard["night"] if is_night else standard["day"]
        is_compliant = laeq <= limit
        
        return {
            "station_id": self.station_id,
            "timestamp": timestamp,
            "lat": self.lat,
            "lon": self.lon,
            "zone_type": self.zone_type,
            "period": "night" if is_night else "day",
            "parameters": {
                "laeq": round(laeq, 1),      # Equivalent continuous A-weighted
                "lamax": round(lamax, 1),    # Maximum A-weighted
                "lamin": round(lamin, 1),    # Minimum A-weighted
                "l10": round(l10, 1),        # 10th percentile
                "l50": round(l50, 1),        # 50th percentile (median)
                "l90": round(l90, 1),        # 90th percentile (background)
            },
            "limit_db": limit,
            "is_compliant": is_compliant,
            "exceedance_db": round(max(0, laeq - limit), 1),
            "sensor_status": "normal",
            "data_quality_flag": "valid"
        }


class SensorNetwork:
    """Manages a network of environmental sensors."""
    
    def __init__(self):
        self.air_sensors: list[AirQualitySensor] = []
        self.water_sensors: list[WaterQualitySensor] = []
        self.noise_sensors: list[NoiseSensor] = []
        
        self._initialize_sensors()
        
    def _initialize_sensors(self):
        """Create sensor network across Delhi NCR region."""
        # Delhi NCR bounding box (approximate)
        lat_min, lat_max = 28.40, 28.85
        lon_min, lon_max = 76.85, 77.35
        
        zone_types = ["industrial", "residential", "commercial"]
        water_bodies = ["river", "groundwater", "lake", "canal"]
        
        # Initialize air quality stations
        for i in range(NUM_AIR_STATIONS):
            lat = random.uniform(lat_min, lat_max)
            lon = random.uniform(lon_min, lon_max)
            zone = random.choice(zone_types)
            self.air_sensors.append(
                AirQualitySensor(f"AQ-DEL-{i+1:03d}", lat, lon, zone)
            )
        
        # Initialize water quality stations
        for i in range(NUM_WATER_STATIONS):
            lat = random.uniform(lat_min, lat_max)
            lon = random.uniform(lon_min, lon_max)
            water_body = random.choice(water_bodies)
            self.water_sensors.append(
                WaterQualitySensor(f"WQ-DEL-{i+1:03d}", lat, lon, water_body)
            )
        
        # Initialize noise monitoring stations
        for i in range(NUM_NOISE_STATIONS):
            lat = random.uniform(lat_min, lat_max)
            lon = random.uniform(lon_min, lon_max)
            zone = random.choice(zone_types + ["silence"])
            self.noise_sensors.append(
                NoiseSensor(f"NS-DEL-{i+1:03d}", lat, lon, zone)
            )
        
        logger.info(f"Initialized sensor network: {NUM_AIR_STATIONS} air, "
                   f"{NUM_WATER_STATIONS} water, {NUM_NOISE_STATIONS} noise stations")
    
    def generate_all_readings(self) -> dict:
        """Generate readings from all sensors."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "air_quality": [s.generate_reading() for s in self.air_sensors],
            "water_quality": [s.generate_reading() for s in self.water_sensors],
            "noise": [s.generate_reading() for s in self.noise_sensors],
        }


async def run_simulation(output_file: Optional[str] = None, console_output: bool = True):
    """Run continuous sensor simulation."""
    network = SensorNetwork()
    iteration = 0
    
    logger.info(f"Starting PRITHVINET sensor simulation (interval: {SIMULATION_INTERVAL_SECONDS}s)")
    
    try:
        while True:
            iteration += 1
            readings = network.generate_all_readings()
            
            # Count malfunctions for Auto-Healer testing
            malfunctions = sum(
                1 for r in readings["air_quality"] 
                if r.get("sensor_status") == "malfunction"
            )
            
            if console_output:
                logger.info(f"Iteration {iteration}: Generated {NUM_AIR_STATIONS + NUM_WATER_STATIONS + NUM_NOISE_STATIONS} readings "
                           f"(malfunctions: {malfunctions})")
                
                # Show sample readings
                if iteration % 10 == 1:
                    sample_air = readings["air_quality"][0]
                    if "parameters" in sample_air:
                        logger.debug(f"Sample Air: PM2.5={sample_air['parameters'].get('pm25', 'N/A')} μg/m³, "
                                    f"AQI={sample_air.get('aqi', 'N/A')} ({sample_air.get('aqi_category', 'N/A')})")
            
            if output_file:
                with open(output_file, "a") as f:
                    f.write(json.dumps(readings) + "\n")
            
            await asyncio.sleep(SIMULATION_INTERVAL_SECONDS)
            
    except KeyboardInterrupt:
        logger.info("Simulation stopped by user")


def main():
    """Entry point for sensor simulation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="PRITHVINET IoT Sensor Simulator")
    parser.add_argument("--output", "-o", help="Output file for JSON readings")
    parser.add_argument("--interval", "-i", type=int, default=5, 
                       help="Simulation interval in seconds")
    parser.add_argument("--quiet", "-q", action="store_true", 
                       help="Suppress console output")
    args = parser.parse_args()
    
    global SIMULATION_INTERVAL_SECONDS
    SIMULATION_INTERVAL_SECONDS = args.interval
    
    asyncio.run(run_simulation(
        output_file=args.output,
        console_output=not args.quiet
    ))


if __name__ == "__main__":
    main()
