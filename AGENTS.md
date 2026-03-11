# PRITHVINET — AI Agents Architecture

> Autonomous agents powering the intelligence layer of the Environmental Monitoring & Compliance Platform.

---

## Overview

PRITHVINET employs a multi-agent architecture where each agent is a specialized computational unit responsible for a distinct analytical domain. Agents operate autonomously on streaming environmental data, producing actionable intelligence for regulators, factory operators, and citizens.

---

## Agent 1: OCEMS Diagnostic Auto-Healer Agent

**Purpose**: Distinguish genuine pollution events from digital DAHS communication failures in real-time OCEMS data.

**Input**: Raw continuous emission monitoring readings (PM, SO2, NOx, CO) from factory OCEMS installations.

**Methodology**:
- **Temporal Gradient Analysis** — Detects physically implausible rate-of-change in sensor readings (e.g., PM jumping 45→950 in one interval)
- **Cross-Sensor Correlation** — Compares co-located sensor parameters for consistency; a genuine pollution event affects multiple correlated parameters simultaneously
- **Stuck-Value Detection** — Identifies sensors reporting identical values across consecutive intervals, indicating hardware freeze or DAHS software lock
- **Statistical Outlier Scoring** — Z-score analysis against rolling historical baselines per parameter per factory

**Scoring**: Weighted composite score across all 4 indicators produces a probabilistic diagnosis:
| Diagnosis | Meaning |
|---|---|
| `normal` | All indicators within expected ranges |
| `suspect` | Anomalous pattern detected, requires human review |
| `fault_detected` | High confidence digital/hardware malfunction — not a real pollution event |
| `real_event` | Genuine emission exceedance confirmed by cross-sensor corroboration |

**Output**: Per-sensor diagnosis with confidence score, severity level, indicator breakdown, and recommended action (e.g., `recalibrate_sensor`, `investigate_emission`, `none`).

---

## Agent 2: Causal Policy Simulator Agent (What-If Room)

**Purpose**: Run counterfactual policy intervention simulations using a Structural Equation Model (SEM) to answer "what would happen if..." questions.

**Input**: City name, target pollutant, and 5 pre-defined intervention scenarios (industrial emission cuts, vehicle density reduction, green cover expansion, fuel switching, meteorological confounders).

**Methodology**:
- **NumPy SEM** — Hand-rolled directed acyclic graph (DAG) with 13 nodes representing industrial output, vehicle density, meteorological variables, and pollutant concentrations
- **Causal Coefficients** — Edge weights derived from environmental science literature and Indian emission inventory studies
- **Bootstrapped Inference** — 1000 Monte Carlo samples per scenario to generate 90% confidence intervals and p-values for each counterfactual projection
- **Scenario Ranking** — Automatically identifies the optimal intervention by comparing relative change magnitudes across all scenarios

**Output**: Per-scenario results with baseline value, counterfactual value, absolute change, relative change percentage, confidence intervals, p-values, and a recommendation identifying the most effective policy lever.

---

## Agent 3: Probabilistic Forecasting Agent

**Purpose**: Generate AQI forecasts with quantified uncertainty bounds for regulatory planning and public health advisories.

**Input**: Station ID, target parameter (default: AQI), forecast horizon (default: 12 hours).

**Methodology**:
- **Primary Model**: Nixtla TimeGPT — foundation model for time series, providing probabilistic forecasts with confidence intervals
- **Fallback Model**: Holt Exponential Smoothing — activates when TimeGPT API is unavailable or rate-limited
- **Confidence Bands**: 90% prediction intervals (upper/lower bounds) conveying forecast uncertainty
- **Historical Pattern Matching**: Leverages 2024-2025 CPCB historical data patterns for seasonal decomposition

**Output**: Array of forecast points (timestamp, predicted value, upper_bound, lower_bound), model identification, and model performance metrics.

---

## Agent 4: LinUCB Contextual Bandit Dispatcher Agent

**Purpose**: Optimally allocate limited regulatory audit resources across factories by balancing exploration and exploitation.

**Input**: Factory compliance history, OCEMS diagnostic results, industry risk profiles, previous audit outcomes.

**Methodology**:
- **LinUCB Algorithm** — Upper Confidence Bound linear contextual bandit that models expected violation probability as a linear function of factory features
- **Context Features**: Industry type, historical violation count, OCEMS health score, time since last audit, geographic cluster risk
- **Exploration Bonus**: UCB term ensures previously unvisited or data-sparse factories receive fair audit probability, preventing systematic blind spots
- **Exploitation**: Prioritizes factories with highest predicted violation probability based on accumulated reward signal

**Output**: Ranked factory audit schedule with expected violation probability, confidence bounds, and recommended audit intensity.

> *Note: Agent 4 is architecturally defined and API-stubbed. Full RL training loop requires accumulated audit outcome data from deployment.*

---

## Agent 5: Live Data Simulation Agent

**Purpose**: Generate realistic real-time environmental readings by replaying historical CPCB patterns with controlled stochastic variation.

**Input**: 2024-2025 CPCB historical XLSX data from 14 Chhattisgarh stations (591 stations nationally).

**Methodology**:
- **Historical Pattern Extraction** — Computes hourly means and standard deviations per station per parameter from preprocessed CPCB data
- **Time-Aligned Replay** — Maps current wall-clock time to the corresponding historical hour, producing readings that follow real diurnal and seasonal patterns
- **Gaussian Perturbation** — Adds calibrated random noise (scaled to historical standard deviation) to prevent identical replay cycles
- **AQI Sub-Index Decomposition** — Breaks composite AQI into constituent pollutant concentrations (PM2.5, PM10, NO2, SO2, CO, O3, NH3, Pb) using NAQI breakpoint inversion

**Output**: Streaming pollutant readings with station metadata (coordinates, city, state) written to ClickHouse `air_quality_raw` at configurable intervals.

---

## Agent 6: Citizen Gamification Agent

**Purpose**: Drive citizen environmental engagement through gamified incentives — eco-points, badges, leaderboards, and community pollution reports.

**Input**: User actions (pollution reports, sensor verifications, community challenges completed).

**Scoring**:
| Action | Points |
|---|---|
| Verified pollution report | +50 |
| Sensor reading verification | +20 |
| Community challenge completion | +100 |
| Daily check-in | +5 |

**Badge Progression**: Eco Seedling → Green Guardian → Climate Champion → Planet Protector

**Output**: User profiles with accumulated eco-points, earned badges, rank on public leaderboard, and submitted geo-tagged pollution reports.

---

## Inter-Agent Data Flow

```
CPCB Historical Data ──→ [Agent 5: Live Simulator] ──→ ClickHouse
                                                           │
                          ┌────────────────────────────────┤
                          ▼                                ▼
              [Agent 3: Forecasting]            [Agent 1: Auto-Healer]
              Predict future AQI                Diagnose OCEMS health
                          │                                │
                          ▼                                ▼
              [Agent 2: Causal SEM]             [Agent 4: LinUCB Bandit]
              What-if policy simulation         Optimal audit scheduling
                          │                                │
                          └──────────┬─────────────────────┘
                                     ▼
                          [Agent 6: Gamification]
                          Citizen engagement & verification
                                     │
                                     ▼
                            Next.js Dashboard
                         (6 pages, real-time updates)
```

---

## Technical Stack per Agent

| Agent | Core Library | Data Store | API Endpoint |
|---|---|---|---|
| OCEMS Auto-Healer | NumPy, custom scoring | ClickHouse `ocems_raw` | `GET /api/v1/compliance/auto-healer/diagnose/{id}` |
| Causal Simulator | NumPy SEM, bootstrapping | In-memory DAG | `POST /api/v1/causal/what-if`, `GET /api/v1/causal/dag` |
| Forecasting | Nixtla TimeGPT, Holt ES | ClickHouse `air_quality_raw` | `POST /api/v1/forecast/air-quality` |
| LinUCB Bandit | NumPy (stubbed) | PostgreSQL `factories` | `GET /api/v1/compliance/audit-schedule` |
| Live Simulator | NumPy, ClickHouse Connect | ClickHouse `air_quality_raw` | Internal (background service) |
| Gamification | FastAPI, PostgreSQL | PostgreSQL `users`, `reports` | `GET /api/v1/gamification/*` |

---

*PRITHVINET — Shifting environmental monitoring from passive visualization to autonomous intelligence.*
