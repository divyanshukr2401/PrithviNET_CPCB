<p align="center">
  <h1 align="center">PRITHVINET</h1>
  <p align="center"><strong>Autonomous Environmental Command & Causal Simulator</strong></p>
  <p align="center">Smart Environmental Monitoring & Compliance Platform for Air, Water & Noise</p>
  <p align="center">
    <em>Built for CECB (Chhattisgarh Environment Conservation Board) - Problem Statement PS-01</em>
  </p>
</p>

---

> **PRITHVINET** is a hackathon-grade environmental intelligence platform that combines real-time monitoring, forecasting, causal simulation, compliance analytics, AI assistance, and regulator-facing reporting in a single operational dashboard.

---

## Current Status

PRITHVINET has moved well beyond the concept stage. The current repository contains a working full-stack prototype with live-style sensor simulation, multiple FastAPI modules, interactive maps, PDF report generation, AI-assisted analysis, and OCEMS compliance tooling.

### Implemented Features

1. **Infrastructure & Data Layer**
   - Dockerized stack with **ClickHouse**, **PostgreSQL + PostGIS**, and **Redis**.
   - FastAPI backend with async services and multiple domain-specific API routers.
   - Time-series storage for air quality, noise, and OCEMS telemetry.
   - Spatial metadata for air, water, noise stations, and industrial units.

2. **National Air Quality Monitoring**
   - Live-style AQI and pollutant dashboard built from CPCB historical data replay.
   - Station metadata lookup with names, coordinates, city, and state.
   - AQI category breakdown and station-wise analytics.
   - Historical trend retrieval for individual stations.

3. **Water Quality Monitoring**
   - Surface water quality heatmap using CPCB/data.gov.in-derived WQI data.
   - State filtering, station selection, and detail views.
   - Groundwater level search and district-level visualization support.
   - WQI categorization and parameter-aware display logic.

4. **Noise Monitoring**
   - Environmental noise APIs and live/district visualization support.
   - Station-level noise summaries and standards-based interpretation.
   - Chhattisgarh noise station seeding and report integration.

5. **Probabilistic Forecasting**
   - Forecast page backed by **Nixtla TimeGPT** with fallback behavior.
   - Forecast bands for future air quality trends.
   - Yearly AQI profile support and related visual analysis.

6. **Causal AI What-If Simulator**
   - Structural causal simulation for environmental policy scenarios.
   - Interactive frontend for counterfactual analysis.
   - Backend DAG and what-if endpoints for policy experimentation.

7. **OCEMS Compliance & Auto-Healer**
   - Compliance summary APIs for monitored factories.
   - Recent exceedance detection from OCEMS telemetry.
   - Auto-healer workflow to diagnose likely sensor faults vs. real pollution events.
   - Per-factory diagnosis and health scoring.

8. **AI Copilot**
   - Backend copilot context service and chat endpoints.
   - Frontend floating copilot panel for guided analysis.
   - Context-aware suggestions based on the active monitoring layer.

9. **PDF Report Generation**
   - City, state, and national report generation endpoints.
   - Dedicated frontend reports page for scope selection and downloads.
   - Multi-section PDF output for AQI, water quality, and noise monitoring.
   - Report filtering fixes for city/state scope and station-name enrichment.

10. **Citizen / Regulator Experience**
   - Gamification APIs and leaderboard flows.
   - Stations explorer page.
   - Multi-layer environmental dashboard with interactive maps and detail panels.

---

## Frontend Modules Available

The current Next.js frontend includes these working routes/pages:

- `Dashboard` - live AQI, water, and noise monitoring layers
- `Stations` - station explorer and metadata views
- `Forecast` - forecast analysis and yearly profile views
- `Reports` - downloadable city/state/national PDF reports
- `What-If Simulator` - causal scenario testing
- `Compliance` - current OCEMS compliance and auto-healer workflow
- `Eco Points` - gamification and leaderboard experience

In addition, the dashboard includes an **AI Copilot panel** for contextual assistance.

---

## Backend API Surface

The FastAPI backend currently exposes these major functional areas:

- `Health`
- `Data Ingestion`
- `Air Quality`
- `Water Quality`
- `Noise Monitoring`
- `Forecasting`
- `Causal AI`
- `Compliance / OCEMS`
- `Gamification`
- `AI Copilot`
- `Report Generation`

---

## Architecture Overview

```text
Frontend (Next.js App Router)
  |- Dashboard
  |- Stations
  |- Forecast
  |- Reports
  |- What-If Simulator
  |- Compliance / OCEMS
  |- Gamification
  `- AI Copilot Panel

Backend (FastAPI)
  |- Air Quality APIs
  |- Water Quality APIs
  |- Noise APIs
  |- Forecasting APIs
  |- Causal AI APIs
  |- Compliance / OCEMS APIs
  |- AI Copilot APIs
  `- Report Generation APIs

Data Layer
  |- ClickHouse: time-series sensor telemetry
  |- PostgreSQL + PostGIS: station and spatial metadata
  `- Redis: cache and transient data
```

---

## Core Engines

### 1. Live Data Simulator

Because official live environmental systems are difficult to consume directly, the platform simulates live operational feeds using historical profiles plus controlled noise and replay logic.

### 2. OCEMS Auto-Healer

The auto-healer helps distinguish suspected sensor/DAHS failures from genuine emission events using weighted indicators such as:

1. temporal gradient
2. cross-sensor consistency
3. stuck-value behavior
4. statistical outlier scoring

### 3. Causal Policy Simulator

The causal engine supports what-if analysis for regulator-style policy scenarios instead of only descriptive dashboards.

### 4. Probabilistic Forecasting

The forecasting stack returns forward-looking trajectories with uncertainty bands rather than a single deterministic estimate.

### 5. Report Generator

The report module produces regulator-style PDF summaries for national, state, and city scopes using AQI, water quality, and noise monitoring data.

### 6. AI Copilot

The AI copilot summarizes current environmental context, suggests questions, and helps interpret monitoring outputs directly inside the frontend workflow.

---

## OCEMS Alerts

The next major UX upgrade for compliance is **OCEMS Alerts**.

This is the planned evolution of the current compliance/auto-healer module into a more alert-first regulator workflow.

### OCEMS Alerts Direction

- Rename the current compliance experience to **OCEMS Alerts**
- Shift from diagnosis-first UI to **alert-first triage**
- Use the attached industry-contact workbook as the new directory/context layer
- Use the standards/legal workbook for compliance references, limits, and penalty context
- Keep current live OCEMS telemetry and auto-healer logic as the monitoring backbone
- Add a believable **email drafting workflow** for non-compliance notices

### Important Note

At this stage, **real email delivery is not required**. The planned workflow is to make the draft/notice experience look regulator-ready and believable without claiming actual outbound delivery.

---

## Quick Start

### Prerequisites

- Docker Desktop
- Python 3.11+
- Node.js 18+

### 1. Start Infrastructure

```bash
cd docker
docker-compose up -d
```

### 2. Start Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8005
```

Notes:

- Use port `8005` for the backend.
- Do not rely on `--reload` for backend development in this workspace.

### 3. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on:

- `http://localhost:3000`

Backend runs on:

- `http://localhost:8005`

---

## Selected API Capabilities

- `/api/v1/air/*` - live air, historical air, station metadata
- `/api/v1/water/*` - water quality heatmap and groundwater views
- `/api/v1/noise/*` - live noise, standards, historical noise
- `/api/v1/forecast/*` - forecasting endpoints
- `/api/v1/causal/*` - DAG and what-if simulation
- `/api/v1/compliance/*` - OCEMS summary, exceedances, diagnosis
- `/api/v1/copilot/*` - AI copilot chat and suggestions
- `/api/v1/report/*` - PDF report generation and reporting metadata

---

## Current Limitations / In-Progress Areas

- **OCEMS Alerts** redesign is planned, but the current shipped page is still the existing compliance workflow.
- **Believable draft email flow** for alerts is planned; actual email sending is not wired.
- **Temperature monitoring** is scaffolded in the frontend but not fully implemented.
- Some modules still rely on simulated/live-style replay rather than direct live government feeds.

---

## Acknowledgments

- **Central Pollution Control Board (CPCB)** - environmental monitoring data and standards context
- **Chhattisgarh Environment Conservation Board (CECB)** - problem statement PS-01
- **Nixtla** - probabilistic forecasting support
- **OpenStreetMap / Carto** - map infrastructure

*Built for the CECB Web2 Hackathon.*
