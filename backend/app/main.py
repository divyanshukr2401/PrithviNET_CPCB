"""
PRITHVINET - Smart Environmental Monitoring & Compliance Platform
FastAPI Backend Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api import health, air_quality, water_quality, noise, forecasting, causal, compliance, gamification


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events"""
    # Startup
    print("🌍 PRITHVINET Environmental Monitoring Platform Starting...")
    print(f"📊 Environment: {settings.ENVIRONMENT}")
    # Initialize database connections, load ML models, etc.
    yield
    # Shutdown
    print("🔒 PRITHVINET Shutting Down...")


app = FastAPI(
    title="PRITHVINET API",
    description="""
    ## Smart Environmental Monitoring & Compliance Platform
    
    PRITHVINET is an Autonomous Environmental Command and Causal Simulator that provides:
    
    - **Real-time Air Quality Monitoring** - PM2.5, PM10, NO2, SO2, CO, O3 tracking
    - **Water Quality Analysis** - Surface and groundwater quality parameters
    - **Environmental Noise Mapping** - CNOSSOS-EU compliant acoustic analysis
    - **Probabilistic Forecasting** - TimesFM and Nixtla powered predictions with confidence intervals
    - **Causal AI Policy Simulation** - DoWhy-based counterfactual analysis
    - **OCEMS Auto-Healer** - Diagnostic system for compliance monitoring
    - **Contextual Bandit Dispatcher** - Optimal audit resource allocation
    - **Gamified Citizen Engagement** - Eco-Points and community verification
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
app.include_router(air_quality.router, prefix="/api/v1/air", tags=["Air Quality"])
app.include_router(water_quality.router, prefix="/api/v1/water", tags=["Water Quality"])
app.include_router(noise.router, prefix="/api/v1/noise", tags=["Noise Monitoring"])
app.include_router(forecasting.router, prefix="/api/v1/forecast", tags=["Forecasting"])
app.include_router(causal.router, prefix="/api/v1/causal", tags=["Causal AI"])
app.include_router(compliance.router, prefix="/api/v1/compliance", tags=["Compliance"])
app.include_router(gamification.router, prefix="/api/v1/gamification", tags=["Gamification"])


@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "name": "PRITHVINET API",
        "version": "1.0.0",
        "description": "Smart Environmental Monitoring & Compliance Platform",
        "status": "operational",
        "docs": "/docs",
        "health": "/health"
    }
