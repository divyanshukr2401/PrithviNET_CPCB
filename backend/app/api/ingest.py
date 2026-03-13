"""
Ingest API — POST endpoints for receiving live/batch sensor data from simulators.
Writes to ClickHouse (time-series) for all data types.
"""

from fastapi import APIRouter, HTTPException
from loguru import logger

from app.models.schemas import (
    AirQualityReading,
    WaterQualityReading,
    NoiseReading,
    OCEMSReading,
    BatchIngestRequest,
    IngestResponse,
)
from app.services.ingestion.clickhouse_writer import ch_writer

router = APIRouter(prefix="/api/v1/ingest", tags=["Ingestion"])


@router.post("/air", response_model=IngestResponse)
async def ingest_air_readings(readings: list[AirQualityReading]):
    """Ingest one or more air quality readings."""
    try:
        count = await ch_writer.insert_air_readings(readings)
        return IngestResponse(status="ok", inserted=count, message=f"{count} air readings ingested")
    except Exception as e:
        logger.error(f"Air ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/water", response_model=IngestResponse)
async def ingest_water_readings(readings: list[WaterQualityReading]):
    """Ingest one or more water quality readings."""
    try:
        count = await ch_writer.insert_water_readings(readings)
        return IngestResponse(status="ok", inserted=count, message=f"{count} water readings ingested")
    except Exception as e:
        logger.error(f"Water ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/noise", response_model=IngestResponse)
async def ingest_noise_readings(readings: list[NoiseReading]):
    """Ingest one or more noise readings."""
    try:
        count = await ch_writer.insert_noise_readings(readings)
        return IngestResponse(status="ok", inserted=count, message=f"{count} noise readings ingested")
    except Exception as e:
        logger.error(f"Noise ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ocems", response_model=IngestResponse)
async def ingest_ocems_readings(readings: list[OCEMSReading]):
    """Ingest one or more OCEMS factory emission readings."""
    try:
        count = await ch_writer.insert_ocems_readings(readings)
        return IngestResponse(status="ok", inserted=count, message=f"{count} OCEMS readings ingested")
    except Exception as e:
        logger.error(f"OCEMS ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=IngestResponse)
async def ingest_batch(batch: BatchIngestRequest):
    """Bulk ingest mixed sensor data in a single request."""
    total = 0
    errors = 0

    for label, readings, inserter in [
        ("air", batch.air_readings, ch_writer.insert_air_readings),
        ("water", batch.water_readings, ch_writer.insert_water_readings),
        ("noise", batch.noise_readings, ch_writer.insert_noise_readings),
        ("ocems", batch.ocems_readings, ch_writer.insert_ocems_readings),
    ]:
        if readings:
            try:
                count = await inserter(readings)
                total += count
            except Exception as e:
                logger.error(f"Batch {label} insert failed: {e}")
                errors += len(readings)

    return IngestResponse(
        status="ok" if errors == 0 else "partial",
        inserted=total,
        errors=errors,
        message=f"Batch: {total} inserted, {errors} failed",
    )
