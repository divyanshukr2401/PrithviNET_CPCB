-- PRITHVINET PostgreSQL/PostGIS Initialization Script

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Air Quality Stations
CREATE TABLE IF NOT EXISTS air_stations (
    station_id VARCHAR(50) PRIMARY KEY,
    station_name VARCHAR(255) NOT NULL,
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(50) DEFAULT 'India',
    geom GEOMETRY(POINT, 4326),
    elevation_m FLOAT,
    station_type VARCHAR(50),
    operator VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_air_stations_geom ON air_stations USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_air_stations_city ON air_stations(city);
CREATE INDEX IF NOT EXISTS idx_air_stations_state ON air_stations(state);

-- Water Quality Stations
CREATE TABLE IF NOT EXISTS water_stations (
    station_id VARCHAR(50) PRIMARY KEY,
    station_name VARCHAR(255) NOT NULL,
    station_type VARCHAR(50), -- surface, groundwater
    water_body VARCHAR(255),
    district VARCHAR(100),
    state VARCHAR(100),
    geom GEOMETRY(POINT, 4326),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_water_stations_geom ON water_stations USING GIST(geom);

-- Noise Monitoring Stations
CREATE TABLE IF NOT EXISTS noise_stations (
    station_id VARCHAR(50) PRIMARY KEY,
    station_name VARCHAR(255) NOT NULL,
    zone_type VARCHAR(50), -- Industrial, Commercial, Residential, Silence
    city VARCHAR(100),
    state VARCHAR(100),
    geom GEOMETRY(POINT, 4326),
    day_limit FLOAT,
    night_limit FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_noise_stations_geom ON noise_stations USING GIST(geom);

-- Factories for OCEMS Compliance
CREATE TABLE IF NOT EXISTS factories (
    factory_id VARCHAR(50) PRIMARY KEY,
    factory_name VARCHAR(255) NOT NULL,
    industry_type VARCHAR(100),
    industry_risk VARCHAR(20), -- low, medium, high, critical
    state VARCHAR(100),
    district VARCHAR(100),
    geom GEOMETRY(POINT, 4326),
    ocems_installed BOOLEAN DEFAULT TRUE,
    last_audit_date DATE,
    violation_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_factories_geom ON factories USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_factories_risk ON factories(industry_risk);

-- Terrain Elevation for Noise Modelling
CREATE TABLE IF NOT EXISTS terrain_elevation (
    id SERIAL PRIMARY KEY,
    geom GEOMETRY(POINTZ, 4326),
    elevation FLOAT
);

CREATE INDEX IF NOT EXISTS idx_terrain_geom ON terrain_elevation USING GIST(geom);

-- Buildings for Noise Barriers
CREATE TABLE IF NOT EXISTS buildings (
    id SERIAL PRIMARY KEY,
    geom GEOMETRY(POLYGONZ, 4326),
    height FLOAT,
    ground_absorption FLOAT DEFAULT 0.5,
    building_type VARCHAR(50)
);

CREATE INDEX IF NOT EXISTS idx_buildings_geom ON buildings USING GIST(geom);

-- Roads for Traffic Noise
CREATE TABLE IF NOT EXISTS roads (
    id SERIAL PRIMARY KEY,
    geom GEOMETRY(LINESTRING, 4326),
    road_type VARCHAR(50),
    road_name VARCHAR(255),
    traffic_volume_day INT,
    traffic_volume_night INT,
    speed_limit INT,
    heavy_vehicle_percent FLOAT DEFAULT 0.1
);

CREATE INDEX IF NOT EXISTS idx_roads_geom ON roads USING GIST(geom);

-- Users for Gamification
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(50) PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    eco_points INT DEFAULT 0,
    level INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Eco-Point Transactions
CREATE TABLE IF NOT EXISTS eco_point_transactions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES users(user_id),
    points INT NOT NULL,
    action VARCHAR(50) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_eco_transactions_user ON eco_point_transactions(user_id);

-- Badges
CREATE TABLE IF NOT EXISTS user_badges (
    user_id VARCHAR(50) REFERENCES users(user_id),
    badge_id VARCHAR(50),
    earned_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_id, badge_id)
);

-- Citizen Reports
CREATE TABLE IF NOT EXISTS citizen_reports (
    report_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES users(user_id),
    report_type VARCHAR(50) NOT NULL,
    geom GEOMETRY(POINT, 4326),
    description TEXT,
    severity VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(20) DEFAULT 'pending',
    verified_by VARCHAR(50),
    verified_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reports_geom ON citizen_reports USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_reports_user ON citizen_reports(user_id);
CREATE INDEX IF NOT EXISTS idx_reports_status ON citizen_reports(status);

-- Challenges
CREATE TABLE IF NOT EXISTS challenges (
    challenge_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    challenge_type VARCHAR(20), -- individual, community
    target_action VARCHAR(50),
    target_count INT,
    reward_points INT,
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Challenge Progress
CREATE TABLE IF NOT EXISTS challenge_progress (
    user_id VARCHAR(50) REFERENCES users(user_id),
    challenge_id VARCHAR(50) REFERENCES challenges(challenge_id),
    current_count INT DEFAULT 0,
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    PRIMARY KEY (user_id, challenge_id)
);

-- Contextual Bandit Model State
CREATE TABLE IF NOT EXISTS bandit_state (
    factory_id VARCHAR(50) PRIMARY KEY,
    feature_weights JSONB,
    design_matrix JSONB,
    reward_vector JSONB,
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE air_stations IS 'Air quality monitoring station locations';
COMMENT ON TABLE water_stations IS 'Water quality monitoring station locations';
COMMENT ON TABLE noise_stations IS 'Noise monitoring station locations';
COMMENT ON TABLE factories IS 'Industrial factories with OCEMS for compliance monitoring';
COMMENT ON TABLE users IS 'Citizen users for gamification system';
COMMENT ON TABLE citizen_reports IS 'Geo-tagged environmental reports from citizens';
