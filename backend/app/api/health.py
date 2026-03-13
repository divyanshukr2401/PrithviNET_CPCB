"""Health Check API Endpoints — wired to real DB connections."""

from fastapi import APIRouter
from loguru import logger

from app.services.ingestion.clickhouse_writer import ch_writer
from app.services.ingestion.postgres_writer import pg_writer

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint — pings PostgreSQL and ClickHouse."""
    pg_ok = await pg_writer.health_check()
    ch_ok = False
    try:
        client = ch_writer._get_client()
        result = client.query("SELECT 1")
        ch_ok = result.result_rows[0][0] == 1
    except Exception as e:
        logger.warning(f"ClickHouse health check failed: {e}")

    overall = "healthy" if (pg_ok and ch_ok) else "degraded"
    return {
        "status": overall,
        "service": "PRITHVINET",
        "components": {
            "postgres": "connected" if pg_ok else "disconnected",
            "clickhouse": "connected" if ch_ok else "disconnected",
        },
    }


@router.get("/health/detailed")
async def detailed_health():
    """Detailed health check with latency measurements."""
    import time

    # PostgreSQL
    pg_status = "disconnected"
    pg_latency = -1
    try:
        t0 = time.monotonic()
        pg_ok = await pg_writer.health_check()
        pg_latency = round((time.monotonic() - t0) * 1000, 1)
        pg_status = "healthy" if pg_ok else "unhealthy"
    except Exception:
        pass

    # ClickHouse
    ch_status = "disconnected"
    ch_latency = -1
    try:
        client = ch_writer._get_client()
        t0 = time.monotonic()
        client.query("SELECT 1")
        ch_latency = round((time.monotonic() - t0) * 1000, 1)
        ch_status = "healthy"
    except Exception:
        pass

    overall = "healthy" if (pg_status == "healthy" and ch_status == "healthy") else "degraded"

    return {
        "status": overall,
        "components": {
            "database": {
                "postgres": {"status": pg_status, "latency_ms": pg_latency},
                "clickhouse": {"status": ch_status, "latency_ms": ch_latency},
            },
            "services": {
                "forecasting": {"status": "ready"},
                "causal_engine": {"status": "ready"},
                "auto_healer": {"status": "ready"},
                "gamification": {"status": "ready"},
            },
        },
    }
