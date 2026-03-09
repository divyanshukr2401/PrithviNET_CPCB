---
name: environmental-apis
description: Integrate with Indian environmental data APIs including CPCB AQI, India-WRIS, CGWB In-GRES, and OpenAQ for real-time monitoring data
license: MIT
compatibility: opencode
metadata:
  domain: data-integration
  difficulty: beginner
  apis: CPCB, India-WRIS, CGWB, OpenAQ
---

# Environmental Data APIs Integration

## Overview
This skill covers integration with public environmental data APIs in India and globally. Essential for building real-world environmental monitoring platforms with authoritative data sources.

## Available APIs

### 1. CPCB AQI API (Air Quality - India)
Central Pollution Control Board provides official Indian Air Quality Index data.

**Endpoint**: `https://app.cpcbccr.com/ccr_docs/AQI_Bulletin.json`

**Parameters Provided**:
- PM2.5, PM10 (µg/m³)
- NO2, SO2, CO, O3 (ppb/ppm)
- NH3, Pb
- Calculated AQI

```python
import httpx
from datetime import datetime

async def fetch_cpcb_aqi():
    """Fetch current AQI data from CPCB"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://app.cpcbccr.com/ccr_docs/AQI_Bulletin.json"
        )
        data = response.json()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "stations": [
                {
                    "station_name": station["station"],
                    "city": station["city"],
                    "state": station["state"],
                    "aqi": station["AQI"],
                    "prominent_pollutant": station["pollutant"],
                    "parameters": {
                        "PM25": station.get("PM2.5"),
                        "PM10": station.get("PM10"),
                        "NO2": station.get("NO2"),
                        "SO2": station.get("SO2"),
                        "CO": station.get("CO"),
                        "O3": station.get("O3")
                    }
                }
                for station in data
            ]
        }
```

### 2. OpenAQ API (Global Air Quality)
Open-source, reference-grade air quality data globally.

**Base URL**: `https://api.openaq.org/v2`

**Key Endpoints**:
- `/locations` - List monitoring locations
- `/measurements` - Get measurements
- `/latest` - Latest readings per location

```python
async def fetch_openaq_data(
    country: str = "IN",
    parameter: str = "pm25",
    limit: int = 100
):
    """Fetch air quality data from OpenAQ"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.openaq.org/v2/latest",
            params={
                "country": country,
                "parameter": parameter,
                "limit": limit
            }
        )
        data = response.json()
        
        return {
            "meta": data["meta"],
            "results": [
                {
                    "location": r["location"],
                    "city": r["city"],
                    "coordinates": r["coordinates"],
                    "measurements": r["measurements"]
                }
                for r in data["results"]
            ]
        }
```

### 3. India-WRIS (Water Resources - Surface)
Water Resources Information System of India for surface water data.

**Portal**: `https://indiawris.gov.in`

**Data Available**:
- River flow metrics
- Surface water quality (pH, DO, BOD, etc.)
- Reservoir levels
- Hydrological parameters

```python
async def fetch_india_wris_data(river: str, state: str):
    """
    Fetch surface water data from India-WRIS
    Note: May require web scraping or specific API access
    """
    # India-WRIS provides data through WebGIS interface
    # Integration typically requires:
    # 1. WMS/WFS service endpoints
    # 2. Specific data download APIs
    
    wms_url = "https://indiawris.gov.in/wms"
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": "water_quality_stations",
        "outputFormat": "json",
        "CQL_FILTER": f"state='{state}'"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(wms_url, params=params)
        return response.json()
```

### 4. CGWB In-GRES (Groundwater)
Central Ground Water Board's In-GRES system for groundwater data.

**Portal**: `https://ingres.iith.ac.in`

**Data Available**:
- Groundwater levels (DWLR telemetry)
- Assessment unit categories: Safe, Semi-critical, Critical, Over-exploited
- Aquifer maps

```python
async def fetch_cgwb_groundwater(state: str, district: str = None):
    """
    Fetch groundwater data from CGWB
    Categories: Safe, Semi-critical, Critical, Over-exploited
    """
    # CGWB data available through data.gov.in
    data_gov_url = "https://api.data.gov.in/resource/cgwb-groundwater"
    
    params = {
        "api-key": "YOUR_DATA_GOV_API_KEY",
        "format": "json",
        "filters[state]": state
    }
    
    if district:
        params["filters[district]"] = district
    
    async with httpx.AsyncClient() as client:
        response = await client.get(data_gov_url, params=params)
        data = response.json()
        
        return {
            "state": state,
            "assessment_units": [
                {
                    "unit_id": unit["id"],
                    "district": unit["district"],
                    "block": unit["block"],
                    "category": unit["category"],  # Safe, Semi-critical, etc.
                    "groundwater_level_m": unit["gwl"],
                    "extraction_rate": unit["extraction_rate"]
                }
                for unit in data["records"]
            ]
        }
```

## Unified Data Ingestion Pattern

```python
from abc import ABC, abstractmethod
from datetime import datetime
import asyncio

class EnvironmentalDataSource(ABC):
    """Abstract base class for environmental data sources"""
    
    @abstractmethod
    async def fetch(self) -> dict:
        pass
    
    @abstractmethod
    def normalize(self, raw_data: dict) -> dict:
        """Normalize data to common schema"""
        pass

class CPCBAirQuality(EnvironmentalDataSource):
    async def fetch(self):
        return await fetch_cpcb_aqi()
    
    def normalize(self, raw_data):
        return {
            "source": "CPCB",
            "type": "air_quality",
            "timestamp": datetime.utcnow().isoformat(),
            "records": raw_data["stations"]
        }

class DataIngestionPipeline:
    """Pipeline to ingest from multiple sources"""
    
    def __init__(self, sources: list):
        self.sources = sources
    
    async def ingest_all(self):
        """Fetch from all sources concurrently"""
        tasks = [source.fetch() for source in self.sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        normalized = []
        for source, result in zip(self.sources, results):
            if not isinstance(result, Exception):
                normalized.append(source.normalize(result))
        
        return normalized
```

## Data Refresh Strategies

| Source | Refresh Rate | Strategy |
|--------|--------------|----------|
| CPCB AQI | Hourly | Poll every hour, cache aggressively |
| OpenAQ | Varies by station | Subscribe to updates or poll hourly |
| India-WRIS | Daily | Daily batch ingestion |
| CGWB | Weekly/Monthly | Scheduled batch job |

## Error Handling

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def fetch_with_retry(url: str, params: dict = None):
    """Fetch with exponential backoff retry"""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()
```

## Best Practices
1. Always cache API responses with appropriate TTL
2. Implement rate limiting to respect API quotas
3. Use async/await for concurrent API calls
4. Normalize data to common schema for unified processing
5. Log all API failures with request details
6. Have fallback data sources for critical parameters

## References
- CPCB API: https://medium.com/@atharva-again/cpcbs-aqi-api-everything-you-need-to-know-41f5eff85c5a
- OpenAQ API: https://docs.openaq.org/
- India-WRIS: https://indiawris.gov.in
- Data.gov.in: https://data.gov.in
