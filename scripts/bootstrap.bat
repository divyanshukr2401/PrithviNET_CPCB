@echo off
REM ===========================================================================
REM PRITHVINET - Full System Bootstrap Script
REM ===========================================================================
REM Run this after Docker Desktop is installed and running.
REM
REM Steps:
REM   1. Start Docker containers (ClickHouse, PostgreSQL, Redis)
REM   2. Wait for services to become healthy
REM   3. Initialize ClickHouse tables
REM   4. Preprocess CG CPCB XLSX data into ClickHouse
REM   5. Start the FastAPI backend
REM ===========================================================================

echo.
echo =====================================================
echo   PRITHVINET - System Bootstrap
echo =====================================================
echo.

REM Check Docker is available
docker --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not installed or not in PATH.
    echo Please install Docker Desktop from https://docker.com
    pause
    exit /b 1
)

REM Check Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker daemon is not running.
    echo Please start Docker Desktop and wait for it to finish loading.
    pause
    exit /b 1
)

echo [1/6] Starting Docker containers...
cd /d D:\Coding\PRITHVINET\docker
docker compose up -d --build
if errorlevel 1 (
    echo ERROR: Docker compose failed. Check the output above.
    pause
    exit /b 1
)

echo.
echo [2/6] Waiting for services to become healthy...
echo       (ClickHouse, PostgreSQL, Redis)

:WAIT_LOOP
timeout /t 5 /nobreak >nul
docker compose ps --format "{{.Name}}: {{.Status}}" 2>nul

REM Check ClickHouse
docker exec prithvinet-clickhouse wget --spider -q http://localhost:8123/ping >nul 2>&1
if errorlevel 1 (
    echo       Waiting for ClickHouse...
    goto WAIT_LOOP
)

REM Check PostgreSQL
docker exec prithvinet-postgres pg_isready -U admin -d prithvinet_geo >nul 2>&1
if errorlevel 1 (
    echo       Waiting for PostgreSQL...
    goto WAIT_LOOP
)

REM Check Redis
docker exec prithvinet-redis redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo       Waiting for Redis...
    goto WAIT_LOOP
)

echo       All services healthy!

echo.
echo [3/6] Initializing ClickHouse tables...
docker exec -i prithvinet-clickhouse clickhouse-client --user admin --password prithvinet_secure_2024 < D:\Coding\PRITHVINET\docker\clickhouse\init_tables.sql
if errorlevel 1 (
    echo WARNING: ClickHouse init may have had issues. Check output above.
) else (
    echo       ClickHouse tables created successfully.
)

echo.
echo [4/6] Verifying PostgreSQL seeding...
docker exec prithvinet-postgres psql -U admin -d prithvinet_geo -c "SELECT count(*) AS air_stations FROM air_stations;"
docker exec prithvinet-postgres psql -U admin -d prithvinet_geo -c "SELECT count(*) AS water_stations FROM water_stations;"
docker exec prithvinet-postgres psql -U admin -d prithvinet_geo -c "SELECT count(*) AS factories FROM factories;"
docker exec prithvinet-postgres psql -U admin -d prithvinet_geo -c "SELECT count(*) AS users FROM users;"

echo.
echo [5/6] Preprocessing Chhattisgarh CPCB data into ClickHouse...
echo       (336 XLSX files, ~200K records)
cd /d D:\Coding\PRITHVINET
python scripts\preprocess_cpcb_historical.py --state Chhattisgarh
if errorlevel 1 (
    echo WARNING: Preprocessing may have had issues. Check output above.
) else (
    echo       CG data loaded into ClickHouse successfully.
)

echo.
echo [6/6] Starting FastAPI backend...
echo       (Access at http://localhost:8000/docs)
cd /d D:\Coding\PRITHVINET\backend
start "PRITHVINET Backend" python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

echo.
echo =====================================================
echo   PRITHVINET is running!
echo =====================================================
echo.
echo   API Docs:    http://localhost:8000/docs
echo   Health:      http://localhost:8000/health
echo   Air Live:    http://localhost:8000/api/v1/air/live
echo   ClickHouse:  http://localhost:8123
echo   PostgreSQL:  localhost:5432
echo   Redis:       localhost:6379
echo.
echo   To stop:  docker compose down  (from docker/ directory)
echo.
pause
