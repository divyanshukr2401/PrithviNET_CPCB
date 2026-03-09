# PRITHVINET - Agent Instructions

## Project Overview

PRITHVINET (Smart Environmental Monitoring & Compliance Platform) is an **Autonomous Environmental Command and Causal Simulator** for Air, Water, and Noise monitoring. This is a hackathon project designed to be built within 24-48 hours.

## Architecture

```
PRITHVINET/
├── backend/                 # FastAPI Python backend
│   ├── app/
│   │   ├── api/            # REST API endpoints
│   │   ├── core/           # Configuration and utilities
│   │   ├── models/         # Pydantic models and database schemas
│   │   └── services/       # Business logic services
│   │       ├── forecasting/  # TimesFM, Nixtla integration
│   │       ├── causal/       # DoWhy integration
│   │       └── bandit/       # LinUCB contextual bandit
│   ├── requirements.txt
│   └── Dockerfile
├── docker/                  # Docker Compose configuration
├── data/                    # Data storage
│   ├── raw/                # Raw API data
│   ├── processed/          # Processed data
│   └── simulated/          # IoT simulation data
├── frontend/                # ToolJet or React frontend
├── scripts/                 # Utility scripts
├── tests/                   # Test files
└── .opencode/skills/        # AI Skills for this project
```

## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Backend | FastAPI (Python) | High-concurrency async API |
| Database (OLAP) | ClickHouse | Time-series data, 100M+ rows/sec |
| Database (Spatial) | PostgreSQL + PostGIS | Geospatial queries |
| Cache | Redis | Real-time data caching |
| ML - Forecasting | TimesFM, Nixtla | Probabilistic time-series forecasting |
| ML - Causal | DoWhy, EconML | Policy simulation, counterfactuals |
| ML - Optimization | LinUCB | Contextual bandit for audits |
| Acoustics | NoiseModelling | CNOSSOS-EU noise maps |
| Frontend | ToolJet | Low-code dashboard builder |

## Available Skills

Load these skills to understand specific technical implementations:

1. **causal-inference** - DoWhy framework for policy simulation
2. **probabilistic-forecasting** - TimesFM and Nixtla for predictions
3. **ocems-diagnostics** - Auto-healer for compliance monitoring
4. **contextual-bandits** - LinUCB for audit resource allocation
5. **noise-modelling** - CNOSSOS-EU compliant acoustic maps
6. **environmental-apis** - CPCB, India-WRIS, OpenAQ integration
7. **gamification-system** - Eco-Points and citizen engagement
8. **clickhouse-timeseries** - Database schema and queries

## Core Features to Implement

### Priority 1: Foundation
- [ ] ClickHouse schema for air/water/noise data
- [ ] FastAPI endpoints structure
- [ ] Data ingestion from CPCB/OpenAQ APIs
- [ ] IoT sensor data simulator

### Priority 2: Intelligence Layer
- [ ] Probabilistic forecasting with confidence intervals
- [ ] OCEMS Auto-Healer diagnostics
- [ ] DoWhy causal policy simulator

### Priority 3: Advanced Features
- [ ] LinUCB contextual bandit for audits
- [ ] NoiseModelling acoustic heatmaps
- [ ] Gamified citizen portal

## API Endpoints Structure

```
/health                    - Health check
/api/v1/air/*             - Air quality monitoring
/api/v1/water/*           - Water quality monitoring
/api/v1/noise/*           - Noise monitoring
/api/v1/forecast/*        - Probabilistic forecasting
/api/v1/causal/*          - Policy simulation
/api/v1/compliance/*      - OCEMS and auto-healer
/api/v1/gamification/*    - Citizen engagement
```

## Development Commands

```bash
# Start infrastructure
cd docker && docker-compose up -d

# Install dependencies
cd backend && pip install -r requirements.txt

# Run backend
cd backend && uvicorn app.main:app --reload --port 8000

# Run tests
cd backend && pytest
```

## Data Sources

| Data Type | Source | Update Frequency |
|-----------|--------|------------------|
| Air Quality (India) | CPCB AQI API | Hourly |
| Air Quality (Global) | OpenAQ | Varies |
| Water (Surface) | India-WRIS | Daily |
| Water (Ground) | CGWB In-GRES | Weekly |
| Simulated IoT | Local script | Real-time |

## Key Differentiators

1. **OCEMS Auto-Healer**: Distinguishes digital failures from pollution events
2. **Causal AI**: DoWhy-based counterfactual policy simulation
3. **Probabilistic Forecasts**: Confidence intervals, not just point predictions
4. **Contextual Bandits**: Optimal audit resource allocation
5. **CNOSSOS-EU Noise Maps**: Professional-grade acoustic modeling

## Coding Guidelines

- Use async/await for all I/O operations
- Type hints required on all functions
- Pydantic models for request/response validation
- ClickHouse for time-series, PostgreSQL for spatial
- Cache expensive computations in Redis
- Log all external API calls

## Demo Flow (4 minutes)

1. **0:00-0:45** - Dashboard overview with geospatial map
2. **0:45-1:30** - OCEMS Auto-Healer diagnosis demo
3. **1:30-2:30** - Causal AI "What-If" policy simulation
4. **2:30-3:15** - Probabilistic forecasts with confidence intervals
5. **3:15-4:00** - Gamification and citizen engagement

## References

- Hackathon PDF: See `/docs/hackathon_brief.pdf`
- CPCB API: https://app.cpcbccr.com/
- OpenAQ: https://openaq.org/
- DoWhy: https://www.pywhy.org/dowhy/
- TimesFM: https://github.com/google-research/timesfm
- NoiseModelling: https://noise-planet.org/noisemodelling.html
