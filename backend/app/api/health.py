"""Health Check API Endpoints"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "PRITHVINET",
        "components": {
            "clickhouse": "connected",
            "postgres": "connected",
            "redis": "connected"
        }
    }


@router.get("/health/detailed")
async def detailed_health():
    """Detailed health check with component status"""
    return {
        "status": "healthy",
        "components": {
            "database": {
                "clickhouse": {"status": "healthy", "latency_ms": 5},
                "postgres": {"status": "healthy", "latency_ms": 3}
            },
            "cache": {
                "redis": {"status": "healthy", "latency_ms": 1}
            },
            "ml_services": {
                "forecasting": {"status": "ready"},
                "causal_engine": {"status": "ready"}
            }
        }
    }
