<p align="center">
  <h1 align="center">PRITHVINET</h1>
  <p align="center"><strong>Autonomous Environmental Command & Causal Simulator</strong></p>
  <p align="center">Smart Environmental Monitoring & Compliance Platform for Air, Water & Noise</p>
  <p align="center">
    <em>Built for CECB (Chhattisgarh Environment Conservation Board) — Problem Statement PS-01</em>
  </p>
</p>

---

> **PRITHVINET** shifts the environmental monitoring paradigm from passive, read-only dashboards to an **active, intelligence-driven computational engine**. It diagnoses OCEMS sensor faults, predicts future pollution events with quantified statistical uncertainty, simulates the real-world impacts of policy interventions using causal AI, and gamifies citizen environmental engagement.

---

## 🚧 Current Project Progress (Hackathon State)

The project has transitioned from concept to a **fully functioning prototype**. The core infrastructure, backend APIs, data simulators, and the Next.js frontend are implemented and working.

### ✅ What is Completed & Working

1. **Infrastructure & Databases**
   - Fully dockerized stack: **ClickHouse** (Time-series data), **PostgreSQL + PostGIS** (Spatial/Relational data), and **Redis**.
   - DB schemas initialized. ClickHouse contains ~1.63M rows of real historical CPCB data for Chhattisgarh and synthetic OCEMS data.
   - PostGIS populated with 610 geocoded CPCB monitoring stations across India.

2. **Data Pipeline & Live Simulation**
   - **Historical Ingestion**: Scripts to download, parse, and ingest base64-encoded CPCB historical XLSX files.
   - **AQI Decomposition**: Mathematical inversion of the NAQI breakpoint tables to derive 8 individual pollutant concentrations from composite AQI.
   - **Live Simulator**: A backend background process that replays historical hour-of-day patterns with Gaussian noise to simulate realistic, real-time 5-minute interval readings for the dashboard.

3. **Backend Intelligence Engine (FastAPI)**
   - **OCEMS Auto-Healer**: Implemented a 4-indicator weighted scoring algorithm (temporal gradient, cross-sensor, stuck-value, statistical outlier) to diagnose sensor faults vs. real pollution events.
   - **Causal Policy Simulator**: Built a hand-rolled NumPy Structural Equation Model (DAG) with bootstrapping to test 5 "What-If" policy counterfactuals and return p-values/confidence intervals.
   - **Probabilistic Forecasting**: Integrated Nixtla TimeGPT with a local Holt Exponential Smoothing fallback to provide 12-hour AQI forecasts with 90% confidence bands.
   - **Gamification API**: Eco-points, badges, and leaderboard system logic implemented.

4. **Frontend Dashboard (Next.js 16)**
   - **6 Fully Functional Pages**: Dashboard (AQI Map & Stats), Forecast, Causal Simulator, Compliance (Auto-Healer), Gamification, and Stations Explorer.
   - Interactive Recharts with confidence bands, Leaflet maps with Carto dark tiles, and real-time polling.
   - Clean, zero-JS dark mode utilizing Tailwind CSS v4.

### ⏳ What is Pending (Vision vs. Reality)
- **LinUCB Contextual Bandit**: Architected and API-stubbed, but the reinforcement learning training loop is pending accumulation of real audit data.
- **Water & Noise Data**: The UI, API endpoints, and database tables exist, but the data ingestion pipelines for India-WRIS (Water) and NoiseModelling are pending (currently focused exclusively on Air & OCEMS).
- **All-India Data Scaledown**: While 591 stations are geocoded, the heavy historical data download was scoped down to Chhattisgarh (14 stations) for the hackathon time constraints.
- **Redis Caching**: Container is running, but caching logic is not fully wired into the FastAPI routers yet.

---

## Architecture & Data Flow

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                    COMPLIANCE & CITIZEN INTERFACE (FRONTEND)                 │
│  Next.js 16 (App Router) + React 19 + Tailwind CSS v4 + Dark Theme           │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌───────────┐ ┌──────────┐ ┌────────┐  │
│  │Dashboard │ │ Forecast │ │ Causal │ │Compliance │ │Gamificat.│ │Stations│  │
│  └──────────┘ └──────────┘ └────────┘ └───────────┘ └──────────┘ └────────┘  │
└────────────────────────────────┬─────────────────────────────────────────────┘
                                 │  REST API (JSON) proxied via Next.js
┌────────────────────────────────▼─────────────────────────────────────────────┐
│                    CAUSAL-PROBABILISTIC INTELLIGENCE ENGINE (BACKEND)        │
│  FastAPI (Python 3.14) + Pydantic v2 + 9 API Routers + CORS + Async          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │  Live        │ │   OCEMS      │ │ Forecasting  │ │   Causal AI          │ │
│  │  Simulator   │ │  Auto-Healer │ │ Nixtla/Holt  │ │   NumPy SEM          │ │
│  └──────▲───────┘ └──────▲───────┘ └──────▲───────┘ └──────────▲───────────┘ │
└─────────│────────────────│────────────────│────────────────────│─────────────┘
          │ (Reads/Writes) │                │                    │
┌─────────▼────────────────▼──────┐ ┌───────▼───────────┐ ┌──────▼───────────┐
│   ClickHouse (OLAP Time-Series) │ │  PostgreSQL + GIS │ │      Redis       │
│                                 │ │                   │ │                  │
│  air_quality_raw (1.63M rows)   │ │  610 stations     │ │  Session cache   │
│  ocems_raw (384 seed rows)      │ │  20 factories     │ │  (Container up)  │
└─────────────────────────────────┘ └───────────────────┘ └──────────────────┘

==== DATA INGESTION PIPELINE (OFFLINE) ====
[CPCB Government Portal] -> Download Base64 XLSX -> [Python Scripts] -> Geocode (Nominatim) -> ClickHouse/PostgreSQL
```

---

## Tech Stack

| Layer | Technology | Role & Justification |
|---|---|---|
| **Frontend** | Next.js 16, React 19, Tailwind v4 | Server components + API route proxying avoids CORS. Tailwind v4 `@theme inline` for seamless dark mode. |
| **Visualization** | Recharts 3, React-Leaflet | Composable chart primitives for complex confidence bands. Leaflet avoids map API key limits. |
| **Backend** | FastAPI, Python 3.14 | Async-native, automatic OpenAPI schema. Handled DoWhy library incompatibility by building a custom NumPy SEM. |
| **Time-Series DB** | ClickHouse 24.1 | Sub-second aggregation on millions of rows. Optimal for storing high-frequency sensor telemetry. |
| **Spatial DB** | PostgreSQL 16 + PostGIS | Manages station coordinates and factory locations. Standard for GIS terrain mapping. |
| **Forecasting** | Nixtla TimeGPT / Holt | Probabilistic intervals. Holt fallback ensures availability if API limits are hit. |
| **Infrastructure** | Docker Compose | One-command spin up of all databases with automatic schema initialization. |

---

## Deep Dive: How the Core Engines Work

### 1. Live Data Simulator
Because the official CPCB live dashboard is captcha-protected, we simulate live data to power the hackathon prototype:
- Historical hourly XLSX data from 2024-2025 is loaded into ClickHouse.
- A FastAPI background task computes **hour-of-day profiles** per station/parameter.
- It applies **Gaussian noise** scaled to historical variance.
- It decomposes AQI back into 8 constituent pollutants using NAQI breakpoint mathematical inversion.
- Result: Highly realistic, seasonal, and diurnal live readings streaming every 5 minutes.

### 2. OCEMS Auto-Healer
Solves the problem of "digital false positives" in continuous emission monitoring. It analyzes sliding windows of sensor data using 4 weighted indicators:
1. **Temporal Gradient (0.25):** Impossible physical jumps (e.g., 950 to 20 in 15 mins).
2. **Cross-Sensor (0.25):** Do co-located sensors corroborate the spike?
3. **Stuck-Value (0.30):** Dead sensor / DAHS software freeze.
4. **Statistical Outlier (0.20):** 3-sigma deviations.
Outputs a diagnosis: `normal`, `suspect`, `real_event`, or `fault_detected`.

### 3. Causal Policy Simulator (What-If Room)
Traditional ML shows correlation; Policy requires Causation.
- We built a Directed Acyclic Graph (DAG) representing relationships between industrial output, traffic, meteorology, and pollution.
- Users input a counterfactual (e.g., "reduce industry by 30%").
- The engine uses matrix propagation and 1000 Monte Carlo bootstrap samples to output the expected change, 90% confidence intervals, and p-values for statistical significance.

### 4. Probabilistic Forecasting
Generates 12-hour future projections.
- Instead of a single deterministic line, it provides Upper and Lower prediction bounds.
- Crucial for regulators to understand the *uncertainty* of a pollution event before issuing public advisories.

---

## Quick Start Guide

### Prerequisites
- Docker Desktop (v20+)
- Python 3.11+
- Node.js 18+

### 1. Start Infrastructure & Databases
```bash
cd docker
docker-compose up -d
```
*Note: This spins up ClickHouse, PostgreSQL, and Redis. Schemas and seed data (1.6M rows) are automatically initialized.*

### 2. Start Backend API
```bash
cd backend
python -m venv venv
# Windows: .\venv\Scripts\activate
# Linux/Mac: source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
*The Live Simulator background task starts automatically. Verify at `http://localhost:8000/health`*

### 3. Start Frontend Dashboard
```bash
cd frontend
npm install
npm run dev
```
*Access the dashboard at `http://localhost:3000`*

---

## Acknowledgments
- **Central Pollution Control Board (CPCB)** — Historical air quality data
- **Chhattisgarh Environment Conservation Board (CECB)** — Problem statement PS-01
- **Nixtla** — TimeGPT probabilistic forecasting framework
- **OpenStreetMap / Carto** — Map tiles

*Built for the CECB Web2 Hackathon.*
