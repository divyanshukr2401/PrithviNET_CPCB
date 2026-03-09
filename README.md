# PRITHVINET

**Smart Environmental Monitoring & Compliance Platform for Air, Water & Noise**

PRITHVINET is an Autonomous Environmental Command and Causal Simulator that provides real-time environmental monitoring, probabilistic forecasting, causal AI policy simulation, and gamified citizen engagement.

## Features

- **Real-time Environmental Monitoring** - Air quality, water quality, and noise level tracking
- **Probabilistic Forecasting** - TimesFM and Nixtla powered predictions with 90%/95% confidence intervals
- **Causal AI Policy Simulation** - DoWhy-based counterfactual analysis for regulatory decisions
- **OCEMS Auto-Healer** - Intelligent diagnostics to distinguish digital failures from pollution events
- **Contextual Bandit Audit Dispatch** - LinUCB algorithm for optimal inspector allocation
- **Acoustic Noise Mapping** - CNOSSOS-EU compliant noise propagation heatmaps
- **Gamified Citizen Engagement** - Eco-Points, leaderboards, and community challenges

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI (Python 3.11+) |
| Time-Series DB | ClickHouse |
| Spatial DB | PostgreSQL + PostGIS |
| Cache | Redis |
| Forecasting | Google TimesFM, Nixtla StatsForecast |
| Causal AI | DoWhy, EconML |
| Noise Modeling | NoiseModelling (Java) |
| Frontend | ToolJet |
| Containerization | Docker Compose |

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git

### Installation

1. **Clone the repository**
   ```bash
   cd D:\Coding\PRITHVINET
   ```

2. **Create Python virtual environment**
   ```bash
   cd backend
   python -m venv venv
   
   # Windows
   .\venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   
   pip install -r requirements.txt
   ```

3. **Start infrastructure services**
   ```bash
   cd docker
   docker-compose up -d
   ```

4. **Configure environment**
   ```bash
   cd backend
   copy .env.example .env
   # Edit .env with your API keys and database credentials
   ```

5. **Run the backend**
   ```bash
   cd backend
   uvicorn app.main:app --reload --port 8000
   ```

6. **Access the API**
   - API Docs: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

## Project Structure

```
PRITHVINET/
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── core/           # Configuration
│   │   ├── models/         # Data models
│   │   └── services/       # Business logic
│   ├── requirements.txt
│   └── Dockerfile
├── docker/                  # Docker Compose setup
│   └── docker-compose.yml
├── data/                    # Data storage
├── frontend/                # ToolJet configuration
├── scripts/                 # Utility scripts
├── tests/                   # Test files
├── .opencode/skills/        # AI Agent Skills
└── AGENTS.md               # AI Agent instructions
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /api/v1/air/*` | Air quality monitoring |
| `GET /api/v1/water/*` | Water quality monitoring |
| `GET /api/v1/noise/*` | Noise monitoring |
| `POST /api/v1/forecast/*` | Probabilistic forecasting |
| `POST /api/v1/causal/*` | Policy simulation |
| `GET /api/v1/compliance/*` | OCEMS compliance |
| `GET /api/v1/gamification/*` | Citizen engagement |

## AI Agent Skills

This project includes specialized AI skills in `.opencode/skills/`:

| Skill | Description |
|-------|-------------|
| `causal-inference` | DoWhy framework for policy simulation |
| `probabilistic-forecasting` | TimesFM/Nixtla for predictions |
| `ocems-diagnostics` | Auto-healer for compliance |
| `contextual-bandits` | LinUCB for audit optimization |
| `noise-modelling` | CNOSSOS-EU acoustic maps |
| `environmental-apis` | Data source integration |
| `gamification-system` | Eco-Points and engagement |
| `clickhouse-timeseries` | Database optimization |

## Data Sources

- **CPCB AQI API** - Indian air quality data
- **OpenAQ** - Global air quality data
- **India-WRIS** - Surface water quality
- **CGWB In-GRES** - Groundwater levels
- **IoT Simulator** - Synthetic sensor data

## Development

```bash
# Run tests
cd backend && pytest

# Format code
cd backend && black . && ruff check .

# Type checking
cd backend && mypy app/
```

## Docker Services

```bash
# Start all services
cd docker && docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Services included:
- **ClickHouse**: Port 8123 (HTTP), 9000 (Native)
- **PostgreSQL/PostGIS**: Port 5432
- **Redis**: Port 6379
- **Backend**: Port 8000

## Environment Variables

Create a `.env` file in the `backend/` directory:

```env
# Application
APP_NAME=PRITHVINET
ENVIRONMENT=development
DEBUG=True

# ClickHouse
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=admin
CLICKHOUSE_PASSWORD=prithvinet_secure_2024

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=admin
POSTGRES_PASSWORD=prithvinet_secure_2024
POSTGRES_DB=prithvinet_geo

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# External APIs (optional)
NIXTLA_API_KEY=your_key_here
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

MIT License

## Acknowledgments

- Central Pollution Control Board (CPCB)
- OpenAQ for global air quality data
- Google Research for TimesFM
- Microsoft Research for DoWhy
- NoiseModelling project
