-- ==========================================================================
-- PRITHVINET ClickHouse Schema
-- Time-series tables for high-frequency environmental sensor data
-- ==========================================================================

CREATE DATABASE IF NOT EXISTS prithvinet;

-- --------------------------------------------------------------------------
-- AIR QUALITY MEASUREMENTS
-- ~23 stations × 8 params × 288 readings/day (5-min intervals)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS prithvinet.air_quality_raw
(
    station_id   LowCardinality(String),
    timestamp    DateTime64(3, 'Asia/Kolkata'),
    parameter    LowCardinality(String),   -- PM2.5, PM10, NO2, SO2, CO, O3, NH3, Pb
    value        Float64,
    unit         LowCardinality(String),   -- µg/m³
    aqi          UInt16,                    -- sub-index AQI for this parameter
    city         LowCardinality(String),
    latitude     Float64,
    longitude    Float64,
    zone         LowCardinality(String),   -- industrial, commercial, residential, silence, mining
    is_anomaly   UInt8  DEFAULT 0,
    anomaly_type LowCardinality(String) DEFAULT '',  -- spike, stuck, drift, dropout, calibration
    quality_flag LowCardinality(String) DEFAULT 'valid'  -- valid, suspect, invalid, missing
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (station_id, parameter, timestamp)
TTL toDateTime(timestamp) + INTERVAL 2 YEAR
SETTINGS index_granularity = 8192;

-- Materialized view for hourly aggregates
CREATE TABLE IF NOT EXISTS prithvinet.air_quality_hourly
(
    station_id   LowCardinality(String),
    hour         DateTime('Asia/Kolkata'),
    parameter    LowCardinality(String),
    avg_value    Float64,
    min_value    Float64,
    max_value    Float64,
    std_value    Float64,
    count        UInt32,
    city         LowCardinality(String)
)
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(hour)
ORDER BY (station_id, parameter, hour);

CREATE MATERIALIZED VIEW IF NOT EXISTS prithvinet.air_quality_hourly_mv
TO prithvinet.air_quality_hourly
AS SELECT
    station_id,
    toStartOfHour(timestamp) AS hour,
    parameter,
    avg(value) AS avg_value,
    min(value) AS min_value,
    max(value) AS max_value,
    stddevPop(value) AS std_value,
    count() AS count,
    any(city) AS city
FROM prithvinet.air_quality_raw
GROUP BY station_id, parameter, hour;


-- --------------------------------------------------------------------------
-- WATER QUALITY MEASUREMENTS
-- ~9 stations × 10 params × 24 readings/day (1-hour intervals)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS prithvinet.water_quality_raw
(
    station_id   LowCardinality(String),
    timestamp    DateTime64(3, 'Asia/Kolkata'),
    parameter    LowCardinality(String),   -- pH, DO, BOD, COD, TSS, Turbidity, Conductivity, Temperature, Nitrates, Phosphates
    value        Float64,
    unit         LowCardinality(String),
    wqi          Float64 DEFAULT 0,        -- water quality sub-index
    river_name   LowCardinality(String) DEFAULT '',
    city         LowCardinality(String),
    latitude     Float64,
    longitude    Float64,
    is_anomaly   UInt8  DEFAULT 0,
    anomaly_type LowCardinality(String) DEFAULT '',
    quality_flag LowCardinality(String) DEFAULT 'valid'
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (station_id, parameter, timestamp)
TTL toDateTime(timestamp) + INTERVAL 2 YEAR
SETTINGS index_granularity = 8192;

-- Materialized view for daily water quality aggregates
CREATE TABLE IF NOT EXISTS prithvinet.water_quality_daily
(
    station_id   LowCardinality(String),
    day          Date,
    parameter    LowCardinality(String),
    avg_value    Float64,
    min_value    Float64,
    max_value    Float64,
    count        UInt32,
    river_name   LowCardinality(String),
    city         LowCardinality(String)
)
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(day)
ORDER BY (station_id, parameter, day);

CREATE MATERIALIZED VIEW IF NOT EXISTS prithvinet.water_quality_daily_mv
TO prithvinet.water_quality_daily
AS SELECT
    station_id,
    toDate(timestamp) AS day,
    parameter,
    avg(value) AS avg_value,
    min(value) AS min_value,
    max(value) AS max_value,
    count() AS count,
    any(river_name) AS river_name,
    any(city) AS city
FROM prithvinet.water_quality_raw
GROUP BY station_id, parameter, day;


-- --------------------------------------------------------------------------
-- NOISE MEASUREMENTS
-- ~9 stations × 7 metrics × 1440 readings/day (1-min intervals)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS prithvinet.noise_raw
(
    station_id   LowCardinality(String),
    timestamp    DateTime64(3, 'Asia/Kolkata'),
    metric       LowCardinality(String),   -- Leq, Lmax, Lmin, L10, L50, L90, Lden
    value        Float64,                  -- dB(A)
    city         LowCardinality(String),
    latitude     Float64,
    longitude    Float64,
    zone         LowCardinality(String),
    day_limit    Float64,                  -- CPCB day limit for this zone
    night_limit  Float64,                  -- CPCB night limit for this zone
    is_exceedance UInt8 DEFAULT 0,
    is_anomaly   UInt8  DEFAULT 0,
    anomaly_type LowCardinality(String) DEFAULT '',
    quality_flag LowCardinality(String) DEFAULT 'valid'
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (station_id, metric, timestamp)
TTL toDateTime(timestamp) + INTERVAL 1 YEAR
SETTINGS index_granularity = 8192;

-- Hourly noise aggregates
CREATE TABLE IF NOT EXISTS prithvinet.noise_hourly
(
    station_id   LowCardinality(String),
    hour         DateTime('Asia/Kolkata'),
    metric       LowCardinality(String),
    avg_value    Float64,
    max_value    Float64,
    min_value    Float64,
    p95_value    Float64,
    count        UInt32,
    city         LowCardinality(String),
    zone         LowCardinality(String)
)
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(hour)
ORDER BY (station_id, metric, hour);

CREATE MATERIALIZED VIEW IF NOT EXISTS prithvinet.noise_hourly_mv
TO prithvinet.noise_hourly
AS SELECT
    station_id,
    toStartOfHour(timestamp) AS hour,
    metric,
    avg(value) AS avg_value,
    max(value) AS max_value,
    min(value) AS min_value,
    quantile(0.95)(value) AS p95_value,
    count() AS count,
    any(city) AS city,
    any(zone) AS zone
FROM prithvinet.noise_raw
GROUP BY station_id, metric, hour;


-- --------------------------------------------------------------------------
-- OCEMS (Online Continuous Emission Monitoring System)
-- ~20 factories × 4 params × 144 readings/day (10-min intervals)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS prithvinet.ocems_raw
(
    factory_id     LowCardinality(String),
    timestamp      DateTime64(3, 'Asia/Kolkata'),
    parameter      LowCardinality(String),   -- PM, SO2, NOx, CO
    value          Float64,                  -- mg/Nm³
    unit           LowCardinality(String) DEFAULT 'mg/Nm³',
    emission_limit Float64,                  -- applicable limit for this factory type
    exceedance_pct Float64 DEFAULT 0,        -- (value/limit - 1) * 100 if exceeding
    industry_type  LowCardinality(String),
    city           LowCardinality(String),
    latitude       Float64,
    longitude      Float64,
    -- OCEMS health diagnostics
    dahs_status    LowCardinality(String) DEFAULT 'online',  -- online, offline, maintenance
    sensor_health  Float64 DEFAULT 100.0,    -- 0-100 health score
    is_anomaly     UInt8  DEFAULT 0,
    anomaly_type   LowCardinality(String) DEFAULT '',  -- spike, stuck, drift, flatline, calibration_needed
    quality_flag   LowCardinality(String) DEFAULT 'valid'
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (factory_id, parameter, timestamp)
TTL toDateTime(timestamp) + INTERVAL 3 YEAR
SETTINGS index_granularity = 8192;

-- Daily OCEMS compliance summary
CREATE TABLE IF NOT EXISTS prithvinet.ocems_daily_compliance
(
    factory_id     LowCardinality(String),
    day            Date,
    parameter      LowCardinality(String),
    avg_value      Float64,
    max_value      Float64,
    p95_value      Float64,
    exceedance_count UInt32,
    total_readings   UInt32,
    compliance_pct   Float64,
    industry_type  LowCardinality(String),
    city           LowCardinality(String)
)
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(day)
ORDER BY (factory_id, parameter, day);

CREATE MATERIALIZED VIEW IF NOT EXISTS prithvinet.ocems_daily_compliance_mv
TO prithvinet.ocems_daily_compliance
AS SELECT
    factory_id,
    toDate(timestamp) AS day,
    parameter,
    avg(value) AS avg_value,
    max(value) AS max_value,
    quantile(0.95)(value) AS p95_value,
    countIf(value > emission_limit) AS exceedance_count,
    count() AS total_readings,
    100.0 * countIf(value <= emission_limit) / count() AS compliance_pct,
    any(industry_type) AS industry_type,
    any(city) AS city
FROM prithvinet.ocems_raw
GROUP BY factory_id, parameter, day;


-- --------------------------------------------------------------------------
-- OCEMS AUTO-HEALER EVENTS (diagnostic log)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS prithvinet.ocems_healer_events
(
    event_id       UUID DEFAULT generateUUIDv4(),
    factory_id     LowCardinality(String),
    timestamp      DateTime64(3, 'Asia/Kolkata'),
    event_type     LowCardinality(String),  -- fault_detected, healing_applied, false_alarm, real_event
    parameter      LowCardinality(String),
    severity       LowCardinality(String),  -- low, medium, high, critical
    diagnosis      String,                  -- JSON blob with diagnostic details
    confidence     Float64,                 -- 0-1 confidence in diagnosis
    action_taken   LowCardinality(String),  -- none, recalibrate, flag_review, escalate
    resolved       UInt8 DEFAULT 0
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (factory_id, timestamp);


-- --------------------------------------------------------------------------
-- FORECASTING RESULTS (store prediction runs)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS prithvinet.forecast_results
(
    forecast_id    UUID DEFAULT generateUUIDv4(),
    station_id     LowCardinality(String),
    parameter      LowCardinality(String),
    model_name     LowCardinality(String),  -- nixtla_timegpt, statsforecast_mstl
    created_at     DateTime64(3, 'Asia/Kolkata'),
    horizon_hours  UInt16,
    target_time    DateTime64(3, 'Asia/Kolkata'),
    predicted_mean Float64,
    predicted_lo90 Float64,
    predicted_hi90 Float64,
    predicted_lo50 Float64,
    predicted_hi50 Float64,
    actual_value   Float64 DEFAULT 0       -- filled in when actual arrives
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(created_at)
ORDER BY (station_id, parameter, target_time);


-- --------------------------------------------------------------------------
-- CAUSAL SIMULATION LOG
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS prithvinet.causal_simulations
(
    simulation_id  UUID DEFAULT generateUUIDv4(),
    created_at     DateTime64(3, 'Asia/Kolkata'),
    intervention   String,                 -- JSON: policy intervention description
    baseline       String,                 -- JSON: baseline scenario values
    counterfactual String,                 -- JSON: counterfactual scenario values
    effect_size    Float64,
    confidence     Float64,
    city           LowCardinality(String),
    station_ids    Array(String)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(created_at)
ORDER BY (city, created_at);
