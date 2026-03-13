"""Probabilistic Forecasting API Endpoints — wired to NixtlaForecaster service."""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from datetime import datetime
import hashlib
import json

from loguru import logger

from app.models.schemas import ForecastRequest
from app.services.forecasting.nixtla_forecaster import forecaster
from app.services.ingestion.clickhouse_writer import ch_writer
from app.core.redis import cached, get_redis

router = APIRouter()


@router.get("/")
async def get_forecasting_info():
    """Get information about available forecasting models."""
    return {
        "models": [
            {
                "name": "Nixtla TimeGPT",
                "type": "Foundation Model",
                "description": "Zero-shot time-series forecasting via Nixtla API",
                "supports_probabilistic": True,
            },
            {
                "name": "Holt Double Exponential Smoothing",
                "type": "Statistical Fallback",
                "description": "Level + trend smoothing with bootstrap confidence intervals",
                "supports_probabilistic": True,
            },
        ],
        "supported_parameters": [
            "PM2.5",
            "PM10",
            "NO2",
            "SO2",
            "CO",
            "O3",
            "NH3",
            "Pb",
            "pH",
            "DO",
            "BOD",
            "COD",
            "Leq",
            "Lden",
        ],
        "forecast_horizons": ["1h", "6h", "12h", "24h", "48h", "72h"],
        "confidence_intervals": ["50%", "90%"],
    }


@router.post("/air-quality")
async def forecast_air_quality(
    station_id: str,
    parameter: str = Query("PM2.5", description="Parameter to forecast"),
    horizon_hours: int = Query(24, ge=1, le=72),
):
    """Generate probabilistic air quality forecast with confidence intervals."""

    # ── Manual cache keying (replaces broken @cached decorator) ───────
    # The @cached decorator couldn't capture FastAPI query params in its
    # cache key, so every station got the same cached result.  We now
    # build the key explicitly from the actual request values.
    cache_ttl = 600  # 10 minutes
    key_raw = f"forecast_air:{station_id}:{parameter}:{horizon_hours}"
    cache_key = f"prithvinet:{hashlib.sha256(key_raw.encode()).hexdigest()[:32]}"

    try:
        r = await get_redis()
        hit = await r.get(cache_key)
        if hit is not None:
            logger.debug(f"Cache HIT: forecast_air_quality (key={cache_key[:20]}...)")
            return json.loads(hit)
    except Exception as e:
        logger.debug(f"Cache read failed for forecast_air_quality: {e}")

    # ── Cache miss — run the actual forecast ──────────────────────────
    request = ForecastRequest(
        station_id=station_id,
        parameter=parameter,
        horizon_hours=horizon_hours,
    )
    try:
        result = await forecaster.forecast(request, data_type="air")
        payload = result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forecast failed: {str(e)}")

    # ── Write to cache (fire-and-forget) ──────────────────────────────
    try:
        r = await get_redis()
        serialized = json.dumps(payload, default=str)
        await r.setex(cache_key, cache_ttl, serialized)
        logger.debug(f"Cache SET: forecast_air_quality (ttl={cache_ttl}s)")
    except Exception as e:
        logger.debug(f"Cache write failed for forecast_air_quality: {e}")

    return payload


@router.post("/water-quality")
async def forecast_water_quality(
    station_id: str,
    parameter: str = Query("DO", description="Parameter to forecast"),
    horizon_hours: int = Query(48, ge=1, le=72),
):
    """Generate water quality forecast."""
    request = ForecastRequest(
        station_id=station_id,
        parameter=parameter,
        horizon_hours=horizon_hours,
    )
    try:
        result = await forecaster.forecast(request, data_type="water")
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forecast failed: {str(e)}")


@router.post("/noise")
async def forecast_noise_levels(
    station_id: str,
    metric: str = Query("Leq", description="Noise metric"),
    horizon_hours: int = Query(24, ge=1, le=72),
):
    """Generate noise level forecast."""
    request = ForecastRequest(
        station_id=station_id,
        parameter=metric,
        horizon_hours=horizon_hours,
    )
    try:
        result = await forecaster.forecast(request, data_type="noise")
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forecast failed: {str(e)}")


@router.get("/model-performance")
@cached(ttl_seconds=300, prefix="forecast_perf")
async def get_model_performance(
    station_id: str = Query("AQ-CG-001", description="Station ID"),
    parameter: str = Query("PM2.5", description="Parameter"),
):
    """Get performance metrics for recent forecasts (backtesting)."""
    try:
        client = ch_writer._get_client()
        result = client.query(f"""
            SELECT
                model_name,
                count() AS forecasts,
                avg(abs(predicted_mean - actual_value)) AS mae,
                sqrt(avg(pow(predicted_mean - actual_value, 2))) AS rmse,
                avg(abs(predicted_mean - actual_value) / nullIf(actual_value, 0)) * 100 AS mape,
                countIf(actual_value BETWEEN predicted_lo90 AND predicted_hi90) / count() * 100 AS coverage_90
            FROM forecast_results
            WHERE station_id = '{station_id}'
              AND parameter = '{parameter}'
              AND actual_value > 0
            GROUP BY model_name
        """)
        columns = result.column_names
        rows = [dict(zip(columns, row)) for row in result.result_rows]
    except Exception:
        rows = []

    if not rows:
        return {
            "station_id": station_id,
            "parameter": parameter,
            "message": "No forecast results stored yet. Run forecasts first to see performance.",
            "metrics": {},
        }

    return {
        "station_id": station_id,
        "parameter": parameter,
        "models": [
            {
                "model": r.get("model_name", ""),
                "forecasts": r.get("forecasts", 0),
                "mae": round(r.get("mae", 0), 2),
                "rmse": round(r.get("rmse", 0), 2),
                "mape": round(r.get("mape", 0), 1),
                "coverage_90_pct": round(r.get("coverage_90", 0), 1),
            }
            for r in rows
        ],
    }
