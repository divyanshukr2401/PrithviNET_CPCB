"""
PrithviNET — Report Generation API Endpoints.

Provides PDF report download endpoints:
  - GET /api/v1/report/city?city=Delhi         → City-level report
  - GET /api/v1/report/state?state=Chhattisgarh → State-level report
  - GET /api/v1/report/national                → National-level report
  - GET /api/v1/report/available-cities        → List of available cities
  - GET /api/v1/report/available-states        → List of available states
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import Response

from loguru import logger

from app.services.report_generator import (
    generate_city_report,
    generate_state_report,
    generate_national_report,
)
from app.services.ingestion.clickhouse_writer import ch_writer

router = APIRouter()


def _make_filename(scope: str, value: str) -> str:
    """Generate a clean filename for the PDF download."""
    ts = datetime.now().strftime("%Y-%m-%d")
    clean = value.replace(" ", "_").replace(",", "")
    return f"PrithviNET_Report_{scope}_{clean}_{ts}.pdf"


@router.get("/city")
async def report_city(
    city: str = Query(..., description="City name (e.g. Delhi, Mumbai, Raipur)"),
    include_aqi: bool = Query(True, description="Include AQI section"),
    include_water: bool = Query(True, description="Include Water Quality section"),
    include_noise: bool = Query(True, description="Include Noise section"),
):
    """Generate and download a city-level environmental monitoring report."""
    try:
        logger.info(f"Report request: city={city}")
        pdf_bytes = await generate_city_report(
            city=city,
            include_aqi=include_aqi,
            include_water=include_water,
            include_noise=include_noise,
        )
        filename = _make_filename("City", city)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(pdf_bytes)),
            },
        )
    except Exception as e:
        logger.error(f"City report generation failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Report generation failed: {str(e)}"
        )


@router.get("/state")
async def report_state(
    state: str = Query(
        ..., description="State name (e.g. Chhattisgarh, Delhi, Maharashtra)"
    ),
    include_aqi: bool = Query(True, description="Include AQI section"),
    include_water: bool = Query(True, description="Include Water Quality section"),
    include_noise: bool = Query(True, description="Include Noise section"),
):
    """Generate and download a state-level environmental monitoring report."""
    try:
        logger.info(f"Report request: state={state}")
        pdf_bytes = await generate_state_report(
            state=state,
            include_aqi=include_aqi,
            include_water=include_water,
            include_noise=include_noise,
        )
        filename = _make_filename("State", state)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(pdf_bytes)),
            },
        )
    except Exception as e:
        logger.error(f"State report generation failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Report generation failed: {str(e)}"
        )


@router.get("/national")
async def report_national(
    include_aqi: bool = Query(True, description="Include AQI section"),
    include_water: bool = Query(True, description="Include Water Quality section"),
    include_noise: bool = Query(True, description="Include Noise section"),
):
    """Generate and download a national-level environmental monitoring report."""
    try:
        logger.info("Report request: national")
        pdf_bytes = await generate_national_report(
            include_aqi=include_aqi,
            include_water=include_water,
            include_noise=include_noise,
        )
        filename = _make_filename("National", "AllIndia")
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(pdf_bytes)),
            },
        )
    except Exception as e:
        logger.error(f"National report generation failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Report generation failed: {str(e)}"
        )


@router.get("/available-cities")
async def available_cities():
    """Return list of cities with AQI data available for reporting."""
    try:
        client = ch_writer._get_client()
        result = client.query("""
            SELECT DISTINCT city
            FROM air_quality_raw
            WHERE parameter = 'AQI'
              AND timestamp >= now() - INTERVAL 2 HOUR
              AND city != ''
            ORDER BY city
        """)
        cities = [r[0] for r in result.result_rows if r[0]]
        return {"cities": cities, "count": len(cities)}
    except Exception as e:
        logger.warning(f"Failed to fetch available cities: {e}")
        return {"cities": [], "count": 0}


@router.get("/available-states")
async def available_states():
    """Return list of states with water quality data available for reporting."""
    try:
        from app.core.redis import get_redis
        import json

        r = await get_redis()
        raw = await r.get("water_quality_heatmap:v2:all_states:limit=5000")
        if not raw:
            keys = await r.keys("water_quality_heatmap:*")
            if keys:
                raw = await r.get(keys[0])

        if not raw:
            return {"states": [], "count": 0}

        points = json.loads(raw)
        if isinstance(points, dict) and "points" in points:
            points = points["points"]

        states = sorted(set(p.get("state", "") for p in points if p.get("state")))
        return {"states": states, "count": len(states)}
    except Exception as e:
        logger.warning(f"Failed to fetch available states: {e}")
        return {"states": [], "count": 0}
