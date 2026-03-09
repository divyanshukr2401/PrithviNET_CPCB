---
name: clickhouse-timeseries
description: Optimize ClickHouse for high-velocity environmental time-series data ingestion and real-time OLAP queries
license: MIT
compatibility: opencode
metadata:
  domain: databases
  difficulty: intermediate
  database: ClickHouse
---

# ClickHouse for Environmental Time-Series Data

## Overview
ClickHouse is a column-oriented OLAP database capable of ingesting hundreds of millions of rows per second. Essential for environmental monitoring platforms handling massive streams of IoT sensor data.

## Why ClickHouse over PostgreSQL?
- 10-100x faster for aggregation queries
- Optimized for time-series data patterns
- Efficient compression for sensor data
- Real-time ingestion without write amplification
- Native support for temporal functions

## Schema Design Patterns

### Air Quality Measurements Table
```sql
CREATE TABLE air_quality_measurements (
    station_id String,
    timestamp DateTime,
    
    -- Parameters
    pm25 Float32,
    pm10 Float32,
    no2 Float32,
    so2 Float32,
    co Float32,
    o3 Float32,
    aqi UInt16,
    
    -- Metadata
    lat Float64,
    lon Float64,
    city LowCardinality(String),
    state LowCardinality(String),
    
    -- Ingestion metadata
    ingested_at DateTime DEFAULT now()
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (station_id, timestamp)
TTL timestamp + INTERVAL 2 YEAR DELETE
SETTINGS index_granularity = 8192;
```

### Water Quality Table
```sql
CREATE TABLE water_quality_measurements (
    station_id String,
    station_type LowCardinality(String),  -- surface, groundwater
    timestamp DateTime,
    
    -- Parameters
    ph Float32,
    dissolved_oxygen Float32,
    bod Float32,
    cod Float32,
    turbidity Float32,
    tds Float32,
    wqi UInt16,
    
    -- Location
    lat Float64,
    lon Float64,
    water_body LowCardinality(String),
    
    ingested_at DateTime DEFAULT now()
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (station_id, timestamp);
```

### Noise Measurements Table
```sql
CREATE TABLE noise_measurements (
    station_id String,
    timestamp DateTime,
    
    leq Float32,
    lmax Float32,
    lmin Float32,
    l10 Float32,
    l50 Float32,
    l90 Float32,
    lden Float32,
    
    zone_type LowCardinality(String),
    lat Float64,
    lon Float64,
    
    ingested_at DateTime DEFAULT now()
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (station_id, timestamp);
```

### OCEMS/DAHS Logs Table
```sql
CREATE TABLE ocems_logs (
    factory_id String,
    timestamp DateTime64(3),
    
    -- Status
    data_status LowCardinality(String),
    error_code Nullable(String),
    
    -- Raw measurements
    pm_emission Float32,
    so2_emission Float32,
    nox_emission Float32,
    
    -- DAHS metadata
    dahs_software_version String,
    analyzer_status LowCardinality(String),
    
    ingested_at DateTime DEFAULT now()
)
ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(timestamp)
ORDER BY (factory_id, timestamp);
```

## Query Patterns

### Real-Time Dashboard Aggregations
```sql
-- Hourly AQI averages for last 24 hours
SELECT
    station_id,
    toStartOfHour(timestamp) as hour,
    avg(pm25) as avg_pm25,
    avg(aqi) as avg_aqi,
    max(aqi) as max_aqi,
    count() as reading_count
FROM air_quality_measurements
WHERE timestamp >= now() - INTERVAL 24 HOUR
GROUP BY station_id, hour
ORDER BY station_id, hour;
```

### Probabilistic Forecasting Data Preparation
```sql
-- Get hourly aggregates for TimesFM input
SELECT
    toStartOfHour(timestamp) as ts,
    avg(pm25) as pm25,
    stddevPop(pm25) as pm25_std,
    count() as n
FROM air_quality_measurements
WHERE station_id = 'STATION_001'
  AND timestamp >= now() - INTERVAL 30 DAY
GROUP BY ts
ORDER BY ts
WITH FILL
    FROM toStartOfHour(now() - INTERVAL 30 DAY)
    TO toStartOfHour(now())
    STEP INTERVAL 1 HOUR;
```

### Compliance Analysis
```sql
-- Factories with data gaps in last 7 days
SELECT
    factory_id,
    count() as total_readings,
    countIf(data_status = 'gap') as gap_count,
    round(gap_count / total_readings * 100, 2) as gap_percentage,
    max(timestamp) as last_reading
FROM ocems_logs
WHERE timestamp >= now() - INTERVAL 7 DAY
GROUP BY factory_id
HAVING gap_percentage > 5
ORDER BY gap_percentage DESC;
```

### Spatial Aggregations (with S2 cells)
```sql
-- AQI heatmap grid using S2 geometry
SELECT
    geoToS2(lon, lat) as s2_cell,
    avg(aqi) as avg_aqi,
    count() as station_count
FROM air_quality_measurements
WHERE timestamp >= now() - INTERVAL 1 HOUR
GROUP BY s2_cell;
```

## Python Integration

### Using clickhouse-connect
```python
import clickhouse_connect
from datetime import datetime, timedelta

class ClickHouseClient:
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        self.client = clickhouse_connect.get_client(
            host=host,
            port=port,
            username=user,
            password=password,
            database=database
        )
    
    async def insert_air_quality(self, records: list):
        """Bulk insert air quality measurements"""
        columns = [
            'station_id', 'timestamp', 'pm25', 'pm10', 
            'no2', 'so2', 'co', 'o3', 'aqi',
            'lat', 'lon', 'city', 'state'
        ]
        
        data = [
            [r.get(col) for col in columns]
            for r in records
        ]
        
        self.client.insert(
            'air_quality_measurements',
            data,
            column_names=columns
        )
    
    async def get_station_history(
        self,
        station_id: str,
        parameter: str,
        hours: int = 168  # 1 week
    ) -> list:
        """Get historical data for forecasting"""
        query = f"""
            SELECT
                toStartOfHour(timestamp) as ts,
                avg({parameter}) as value
            FROM air_quality_measurements
            WHERE station_id = %(station_id)s
              AND timestamp >= now() - INTERVAL {hours} HOUR
            GROUP BY ts
            ORDER BY ts
            WITH FILL STEP INTERVAL 1 HOUR
        """
        
        result = self.client.query(
            query,
            parameters={'station_id': station_id}
        )
        
        return [
            {'timestamp': row[0], 'value': row[1]}
            for row in result.result_rows
        ]
```

### FastAPI Integration
```python
from fastapi import APIRouter, Depends

router = APIRouter()

async def get_clickhouse():
    return ClickHouseClient(
        host=settings.CLICKHOUSE_HOST,
        port=settings.CLICKHOUSE_PORT,
        user=settings.CLICKHOUSE_USER,
        password=settings.CLICKHOUSE_PASSWORD,
        database=settings.CLICKHOUSE_DB
    )

@router.get("/stations/{station_id}/history")
async def get_station_history(
    station_id: str,
    parameter: str = "pm25",
    hours: int = 168,
    ch: ClickHouseClient = Depends(get_clickhouse)
):
    return await ch.get_station_history(station_id, parameter, hours)
```

## Performance Optimization

### Materialized Views for Pre-Aggregation
```sql
-- Hourly aggregates materialized view
CREATE MATERIALIZED VIEW air_quality_hourly
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(hour)
ORDER BY (station_id, hour)
AS SELECT
    station_id,
    toStartOfHour(timestamp) as hour,
    sum(pm25) as sum_pm25,
    sum(aqi) as sum_aqi,
    count() as count
FROM air_quality_measurements
GROUP BY station_id, hour;
```

### Projection for Fast Lookups
```sql
ALTER TABLE air_quality_measurements
ADD PROJECTION aqi_by_city (
    SELECT * ORDER BY city, timestamp
);
```

## Docker Deployment
```yaml
# docker-compose.yml
services:
  clickhouse:
    image: clickhouse/clickhouse-server:24.1
    ports:
      - "8123:8123"  # HTTP
      - "9000:9000"  # Native
    volumes:
      - clickhouse_data:/var/lib/clickhouse
    environment:
      - CLICKHOUSE_DB=prithvinet
      - CLICKHOUSE_USER=admin
      - CLICKHOUSE_PASSWORD=secure_password
    ulimits:
      nofile:
        soft: 262144
        hard: 262144
```

## Best Practices
1. Use `LowCardinality(String)` for categorical columns
2. Partition by month for time-series data
3. Order by (entity_id, timestamp) for efficient queries
4. Use materialized views for dashboard aggregations
5. Set appropriate TTL for data retention
6. Use `WITH FILL` to handle missing timestamps in time-series

## References
- ClickHouse Documentation: https://clickhouse.com/docs
- ClickHouse for Time-Series: https://clickhouse.com/use-cases/time-series
- clickhouse-connect: https://clickhouse.com/docs/en/integrations/python
