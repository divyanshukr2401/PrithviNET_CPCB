"""Water Quality Monitoring API Endpoints"""

from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime

router = APIRouter()


@router.get("/")
async def get_water_quality_summary():
    """Get overall water quality summary"""
    return {
        "summary": "Water quality monitoring active",
        "surface_stations": 500,
        "groundwater_stations": 200,
        "parameters": ["pH", "DO", "BOD", "COD", "Turbidity", "TDS", "Nitrates", "Phosphates"],
        "last_updated": datetime.utcnow().isoformat()
    }


@router.get("/surface")
async def get_surface_water_quality(
    river: Optional[str] = Query(None, description="Filter by river name"),
    state: Optional[str] = Query(None, description="Filter by state")
):
    """Get surface water quality data from rivers and lakes"""
    return {
        "type": "surface",
        "sources": [],
        "filters": {"river": river, "state": state}
    }


@router.get("/groundwater")
async def get_groundwater_quality(
    state: Optional[str] = Query(None, description="Filter by state"),
    district: Optional[str] = Query(None, description="Filter by district")
):
    """Get groundwater quality data from CGWB In-GRES system"""
    return {
        "type": "groundwater",
        "assessment_units": [],
        "categories": ["Safe", "Semi-critical", "Critical", "Over-exploited"],
        "filters": {"state": state, "district": district}
    }


@router.get("/stations/{station_id}")
async def get_water_station_data(station_id: str):
    """Get water quality data for a specific monitoring station"""
    return {
        "station_id": station_id,
        "type": "surface",
        "location": {"lat": 25.5941, "lon": 85.1376},
        "parameters": {
            "pH": {"value": 7.2, "unit": "-", "status": "Normal"},
            "DO": {"value": 6.5, "unit": "mg/L", "status": "Good"},
            "BOD": {"value": 3.2, "unit": "mg/L", "status": "Acceptable"},
            "Turbidity": {"value": 15.3, "unit": "NTU", "status": "Normal"}
        },
        "wqi": {"value": 72, "category": "Good"},
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/wqi")
async def get_water_quality_index(
    lat: float,
    lon: float,
    radius_km: float = Query(10, description="Search radius in km")
):
    """Calculate Water Quality Index for a geographic area"""
    return {
        "location": {"lat": lat, "lon": lon, "radius_km": radius_km},
        "wqi": 72,
        "category": "Good",
        "parameters_summary": {
            "critical": [],
            "warning": ["BOD"],
            "normal": ["pH", "DO", "Turbidity"]
        }
    }
