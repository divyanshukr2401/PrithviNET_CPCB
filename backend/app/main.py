"""
PRITHVINET - Smart Environmental Monitoring & Compliance Platform
FastAPI Backend Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger

from app.core.config import settings
from app.api import (
    health,
    air_quality,
    water_quality,
    noise,
    forecasting,
    causal,
    compliance,
    gamification,
    ingest,
)
from app.core.redis import get_redis, close_redis
from app.services.ingestion.clickhouse_writer import ch_writer
from app.services.ingestion.postgres_writer import pg_writer
from app.services.ingestion.live_simulator import live_simulator
from app.services.ingestion.datagov_fetcher import datagov_fetcher


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events."""
    # Startup
    logger.info("PRITHVINET Environmental Monitoring Platform Starting...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Connect to PostgreSQL
    try:
        await pg_writer.connect()
        logger.info("PostgreSQL connection pool established")
    except Exception as e:
        logger.error(f"PostgreSQL connection failed: {e}")

    # ClickHouse connects lazily on first query (via clickhouse-connect)
    logger.info("ClickHouse will connect lazily on first query")

    # Connect to Redis (for caching)
    try:
        await get_redis()
        logger.info("Redis cache connection established")
    except Exception as e:
        logger.warning(f"Redis connection failed (caching disabled): {e}")

    # Start live simulator (loads historical profiles + begins background generation)
    try:
        await live_simulator.start(
            interval_seconds=300,  # Generate new readings every 5 minutes
        )
        logger.info(
            f"Live simulator started: {live_simulator.station_count} stations, "
            f"generating every 5 minutes"
        )
    except Exception as e:
        logger.warning(
            f"Live simulator failed to start (will retry when data is available): {e}"
        )

    yield

    # Shutdown
    logger.info("PRITHVINET Shutting Down...")
    await live_simulator.stop()
    await datagov_fetcher.close()
    await close_redis()
    await pg_writer.close()
    await ch_writer.close()
    logger.info("All connections closed (Redis, PostgreSQL, ClickHouse)")


app = FastAPI(
    title="PRITHVINET API",
    description="""
    ## Smart Environmental Monitoring & Compliance Platform
    
    PRITHVINET is an Autonomous Environmental Command and Causal Simulator that provides:
    
    - **Real-time Air Quality Monitoring** - PM2.5, PM10, NO2, SO2, CO, O3, NH3, Pb tracking
    - **Water Quality Analysis** - Surface water quality parameters for CG rivers
    - **Environmental Noise Mapping** - CNOSSOS-EU compliant acoustic analysis
    - **Probabilistic Forecasting** - Nixtla TimeGPT with Holt exponential smoothing fallback
    - **Causal AI Policy Simulation** - NumPy SEM-based counterfactual analysis
    - **OCEMS Auto-Healer** - 4-indicator weighted scoring for sensor fault detection
    - **Gamified Citizen Engagement** - Eco-Points, badges, and community leaderboard
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(health.router, tags=["Health"])
app.include_router(ingest.router, prefix="/api/v1/ingest", tags=["Data Ingestion"])
app.include_router(air_quality.router, prefix="/api/v1/air", tags=["Air Quality"])
app.include_router(water_quality.router, prefix="/api/v1/water", tags=["Water Quality"])
app.include_router(noise.router, prefix="/api/v1/noise", tags=["Noise Monitoring"])
app.include_router(forecasting.router, prefix="/api/v1/forecast", tags=["Forecasting"])
app.include_router(causal.router, prefix="/api/v1/causal", tags=["Causal AI"])
app.include_router(compliance.router, prefix="/api/v1/compliance", tags=["Compliance"])
app.include_router(
    gamification.router, prefix="/api/v1/gamification", tags=["Gamification"]
)


@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "name": "PRITHVINET API",
        "version": "1.0.0",
        "description": "Smart Environmental Monitoring & Compliance Platform — All India (591 CPCB Stations, 32 States/UTs)",
        "status": "operational",
        "coverage": {
            "stations": 591,
            "states": 32,
            "data_rows": "63M+",
            "parameters": [
                "PM2.5",
                "PM10",
                "NO2",
                "SO2",
                "CO",
                "O3",
                "NH3",
                "Pb",
                "AQI",
            ],
        },
        "features": [
            "Real-time air quality monitoring (554 live stations)",
            "OCEMS Auto-Healer — sensor fault vs real pollution detection",
            "Causal AI policy simulator — NumPy SEM what-if analysis",
            "Probabilistic forecasting — Nixtla TimeGPT + Holt fallback",
            "Gamified citizen engagement — eco-points & leaderboard",
        ],
        "docs": "/docs",
        "health": "/health",
    }
