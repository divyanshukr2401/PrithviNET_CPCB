-- ==========================================================================
-- PRITHVINET PostgreSQL Seed Data
-- Seeds 41 CG monitoring stations + 20 OCEMS factories into PostGIS tables
-- Run AFTER init.sql has created the tables
-- ==========================================================================

-- --------------------------------------------------------------------------
-- AIR QUALITY STATIONS (23)
-- Matches: air_stations(station_id, station_name, city, state, geom, station_type, operator)
-- --------------------------------------------------------------------------
INSERT INTO air_stations (station_id, station_name, city, state, geom, elevation_m, station_type, operator) VALUES
('AQ-CG-001', 'Raipur Collectorate CAAQMS', 'Raipur', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(81.6296, 21.2514), 4326), 298, 'commercial', 'CECB'),
('AQ-CG-002', 'Mana Camp Industrial CAAQMS', 'Raipur', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(81.5700, 21.2200), 4326), 295, 'industrial', 'CECB'),
('AQ-CG-003', 'Shankar Nagar Residential CAAQMS', 'Raipur', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(81.6148, 21.2365), 4326), 300, 'residential', 'CECB'),
('AQ-CG-004', 'BSP Main Gate CAAQMS', 'Bhilai', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(81.3784, 21.2094), 4326), 305, 'industrial', 'CECB'),
('AQ-CG-005', 'Civic Centre CAAQMS', 'Bhilai', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(81.4278, 21.2167), 4326), 302, 'commercial', 'CECB'),
('AQ-CG-006', 'Nehru Nagar Residential CAAQMS', 'Bhilai', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(81.4100, 21.1983), 4326), 300, 'residential', 'CECB'),
('AQ-CG-007', 'NTPC Korba CAAQMS', 'Korba', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(82.7501, 22.3595), 4326), 260, 'industrial', 'CECB'),
('AQ-CG-008', 'Korba City Centre CAAQMS', 'Korba', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(82.6830, 22.3490), 4326), 265, 'commercial', 'CECB'),
('AQ-CG-009', 'SECL Gevra Mine CAAQMS', 'Korba', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(82.5800, 22.2986), 4326), 255, 'mining', 'CECB'),
('AQ-CG-010', 'Bilaspur Railway CAAQMS', 'Bilaspur', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(82.1391, 22.0796), 4326), 270, 'commercial', 'CECB'),
('AQ-CG-011', 'Uslapur Industrial CAAQMS', 'Bilaspur', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(82.1700, 22.0550), 4326), 268, 'industrial', 'CECB'),
('AQ-CG-012', 'Durg City CAAQMS', 'Durg', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(81.2849, 21.1904), 4326), 295, 'commercial', 'CECB'),
('AQ-CG-013', 'Durg Industrial Estate CAAQMS', 'Durg', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(81.3100, 21.1700), 4326), 290, 'industrial', 'CECB'),
('AQ-CG-014', 'Raigarh City CAAQMS', 'Raigarh', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(83.3950, 21.8974), 4326), 215, 'commercial', 'CECB'),
('AQ-CG-015', 'Tamnar Coal Belt CAAQMS', 'Raigarh', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(83.3600, 21.7900), 4326), 220, 'mining', 'CECB'),
('AQ-CG-016', 'Siltara GIDC CAAQMS', 'Raipur', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(81.5400, 21.3100), 4326), 292, 'industrial', 'CECB'),
('AQ-CG-017', 'Urla Industrial CAAQMS', 'Raipur', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(81.5150, 21.2650), 4326), 296, 'industrial', 'CECB'),
('AQ-CG-018', 'Jamul Cement CAAQMS', 'Bhilai', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(81.3200, 21.2500), 4326), 310, 'industrial', 'CECB'),
('AQ-CG-019', 'BALCO Korba CAAQMS', 'Korba', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(82.6900, 22.3200), 4326), 258, 'industrial', 'CECB'),
('AQ-CG-020', 'Kusmunda Mine CAAQMS', 'Korba', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(82.6200, 22.3100), 4326), 250, 'mining', 'CECB'),
('AQ-CG-021', 'Bilaspur Torwa CAAQMS', 'Bilaspur', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(82.1200, 22.1000), 4326), 272, 'residential', 'CECB'),
('AQ-CG-022', 'Durg Pulgaon CAAQMS', 'Durg', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(81.2600, 21.2000), 4326), 293, 'residential', 'CECB'),
('AQ-CG-023', 'Raigarh Lara STPS CAAQMS', 'Raigarh', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(83.4200, 21.8100), 4326), 210, 'industrial', 'CECB');

-- --------------------------------------------------------------------------
-- WATER QUALITY STATIONS (9)
-- Matches: water_stations(station_id, station_name, station_type, water_body, district, state, geom)
-- --------------------------------------------------------------------------
INSERT INTO water_stations (station_id, station_name, station_type, water_body, district, state, geom) VALUES
('WQ-CG-001', 'Kharun River - Raipur Upstream', 'surface', 'Kharun River', 'Raipur', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(81.6100, 21.2800), 4326)),
('WQ-CG-002', 'Kharun River - Raipur Downstream', 'surface', 'Kharun River', 'Raipur', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(81.6500, 21.2100), 4326)),
('WQ-CG-003', 'Sheonath River - Bhilai', 'surface', 'Sheonath River', 'Durg', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(81.3500, 21.2300), 4326)),
('WQ-CG-004', 'Hasdeo River - Korba Upstream', 'surface', 'Hasdeo River', 'Korba', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(82.7700, 22.3900), 4326)),
('WQ-CG-005', 'Hasdeo River - Korba Downstream', 'surface', 'Hasdeo River', 'Korba', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(82.7200, 22.3300), 4326)),
('WQ-CG-006', 'Arpa River - Bilaspur City', 'surface', 'Arpa River', 'Bilaspur', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(82.1500, 22.0850), 4326)),
('WQ-CG-007', 'Arpa River - Bilaspur Industrial', 'surface', 'Arpa River', 'Bilaspur', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(82.1800, 22.0500), 4326)),
('WQ-CG-008', 'Sheonath River - Durg Bridge', 'surface', 'Sheonath River', 'Durg', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(81.2700, 21.1800), 4326)),
('WQ-CG-009', 'Kelo River - Raigarh', 'surface', 'Kelo River', 'Raigarh', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(83.4100, 21.9000), 4326));

-- --------------------------------------------------------------------------
-- NOISE MONITORING STATIONS (9)
-- Matches: noise_stations(station_id, station_name, zone_type, city, state, geom, day_limit, night_limit)
-- --------------------------------------------------------------------------
INSERT INTO noise_stations (station_id, station_name, zone_type, city, state, geom, day_limit, night_limit) VALUES
('NS-CG-001', 'Jaistambh Chowk Noise Monitor', 'commercial', 'Raipur', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(81.6310, 21.2490), 4326), 65, 55),
('NS-CG-002', 'Ambedkar Hospital Silence Zone', 'silence', 'Raipur', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(81.6200, 21.2400), 4326), 50, 40),
('NS-CG-003', 'Raipur Railway Station Noise Monitor', 'commercial', 'Raipur', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(81.6350, 21.2350), 4326), 65, 55),
('NS-CG-004', 'BSP Industrial Noise Monitor', 'industrial', 'Bhilai', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(81.3800, 21.2050), 4326), 75, 70),
('NS-CG-005', 'Bhilai Sector 6 Residential', 'residential', 'Bhilai', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(81.4150, 21.2200), 4326), 55, 45),
('NS-CG-006', 'NTPC Colony Noise Monitor', 'industrial', 'Korba', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(82.7400, 22.3500), 4326), 75, 70),
('NS-CG-007', 'Bilaspur Bus Stand Noise Monitor', 'commercial', 'Bilaspur', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(82.1400, 22.0800), 4326), 65, 55),
('NS-CG-008', 'Durg Clock Tower Noise Monitor', 'commercial', 'Durg', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(81.2850, 21.1900), 4326), 65, 55),
('NS-CG-009', 'Raigarh Kotra Road Noise Monitor', 'commercial', 'Raigarh', 'Chhattisgarh', ST_SetSRID(ST_MakePoint(83.3960, 21.8950), 4326), 65, 55);

-- --------------------------------------------------------------------------
-- OCEMS FACTORIES (20)
-- Matches: factories(factory_id, factory_name, industry_type, industry_risk, state, district, geom, ocems_installed)
-- --------------------------------------------------------------------------
INSERT INTO factories (factory_id, factory_name, industry_type, industry_risk, state, district, geom, ocems_installed) VALUES
('OCEMS-CG-001', 'Bhilai Steel Plant (BSP)', 'Integrated Steel', 'critical', 'Chhattisgarh', 'Durg', ST_SetSRID(ST_MakePoint(81.3784, 21.2094), 4326), true),
('OCEMS-CG-002', 'Vandana Global Ltd - Sponge Iron', 'Sponge Iron', 'high', 'Chhattisgarh', 'Raigarh', ST_SetSRID(ST_MakePoint(83.3700, 21.8800), 4326), true),
('OCEMS-CG-003', 'Godawari Power & Ispat', 'Integrated Steel', 'critical', 'Chhattisgarh', 'Raipur', ST_SetSRID(ST_MakePoint(81.5500, 21.3000), 4326), true),
('OCEMS-CG-004', 'Jayaswal Neco Industries', 'Sponge Iron', 'high', 'Chhattisgarh', 'Raipur', ST_SetSRID(ST_MakePoint(81.5200, 21.2700), 4326), true),
('OCEMS-CG-005', 'NTPC Korba Super TPS', 'Thermal Power', 'critical', 'Chhattisgarh', 'Korba', ST_SetSRID(ST_MakePoint(82.7501, 22.3595), 4326), true),
('OCEMS-CG-006', 'NTPC Lara STPS', 'Thermal Power', 'critical', 'Chhattisgarh', 'Raigarh', ST_SetSRID(ST_MakePoint(83.4200, 21.8100), 4326), true),
('OCEMS-CG-007', 'CSEB Korba East TPS', 'Thermal Power', 'high', 'Chhattisgarh', 'Korba', ST_SetSRID(ST_MakePoint(82.7100, 22.3400), 4326), true),
('OCEMS-CG-008', 'BALCO Captive Power Plant', 'Thermal Power', 'high', 'Chhattisgarh', 'Korba', ST_SetSRID(ST_MakePoint(82.6900, 22.3200), 4326), true),
('OCEMS-CG-009', 'ACC Jamul Cement Works', 'Cement', 'high', 'Chhattisgarh', 'Durg', ST_SetSRID(ST_MakePoint(81.3200, 21.2500), 4326), true),
('OCEMS-CG-010', 'Lafarge Arasmeta Cement', 'Cement', 'medium', 'Chhattisgarh', 'Bilaspur', ST_SetSRID(ST_MakePoint(82.2300, 22.1200), 4326), true),
('OCEMS-CG-011', 'Ambuja Cement - Bhatapara', 'Cement', 'medium', 'Chhattisgarh', 'Raipur', ST_SetSRID(ST_MakePoint(81.9500, 21.7300), 4326), true),
('OCEMS-CG-012', 'UltraTech Cement - Hirmi', 'Cement', 'medium', 'Chhattisgarh', 'Durg', ST_SetSRID(ST_MakePoint(81.4000, 21.4500), 4326), true),
('OCEMS-CG-013', 'BALCO Aluminium Smelter', 'Aluminium Smelting', 'critical', 'Chhattisgarh', 'Korba', ST_SetSRID(ST_MakePoint(82.6850, 22.3150), 4326), true),
('OCEMS-CG-014', 'SECL Gevra Opencast Mine', 'Coal Mining', 'high', 'Chhattisgarh', 'Korba', ST_SetSRID(ST_MakePoint(82.5800, 22.2986), 4326), true),
('OCEMS-CG-015', 'SECL Kusmunda Mine', 'Coal Mining', 'high', 'Chhattisgarh', 'Korba', ST_SetSRID(ST_MakePoint(82.6200, 22.3100), 4326), true),
('OCEMS-CG-016', 'Raigarh Coal Washery', 'Coal Washery', 'medium', 'Chhattisgarh', 'Raigarh', ST_SetSRID(ST_MakePoint(83.3800, 21.8700), 4326), true),
('OCEMS-CG-017', 'Raipur Rice Mills Cluster', 'Rice Mill', 'low', 'Chhattisgarh', 'Raipur', ST_SetSRID(ST_MakePoint(81.5900, 21.2400), 4326), true),
('OCEMS-CG-018', 'Bilaspur Rice Mill Complex', 'Rice Mill', 'low', 'Chhattisgarh', 'Bilaspur', ST_SetSRID(ST_MakePoint(82.1600, 22.0600), 4326), true),
('OCEMS-CG-019', 'Chhattisgarh Ferro Alloys', 'Ferro Alloys', 'high', 'Chhattisgarh', 'Durg', ST_SetSRID(ST_MakePoint(81.3050, 21.1750), 4326), true),
('OCEMS-CG-020', 'Raigarh Ferro Alloys', 'Ferro Alloys', 'high', 'Chhattisgarh', 'Raigarh', ST_SetSRID(ST_MakePoint(83.3800, 21.9100), 4326), true);

-- --------------------------------------------------------------------------
-- SEED GAMIFICATION DATA (sample users, challenges, badges)
-- --------------------------------------------------------------------------
INSERT INTO users (user_id, username, email, city, state, eco_points, level) VALUES
('USR-001', 'eco_warrior_raipur', 'demo1@prithvinet.cg.gov.in', 'Raipur', 'Chhattisgarh', 1250, 5),
('USR-002', 'green_korba', 'demo2@prithvinet.cg.gov.in', 'Korba', 'Chhattisgarh', 890, 4),
('USR-003', 'clean_bhilai', 'demo3@prithvinet.cg.gov.in', 'Bhilai', 'Chhattisgarh', 2100, 7),
('USR-004', 'bilaspur_guardian', 'demo4@prithvinet.cg.gov.in', 'Bilaspur', 'Chhattisgarh', 450, 2),
('USR-005', 'durg_defender', 'demo5@prithvinet.cg.gov.in', 'Durg', 'Chhattisgarh', 680, 3);

INSERT INTO challenges (challenge_id, name, description, challenge_type, target_action, target_count, reward_points, start_date, end_date) VALUES
('CH-001', 'Air Aware Week', 'Report 5 air quality observations in your area this week', 'individual', 'air_report', 5, 100, NOW() - INTERVAL '7 days', NOW() + INTERVAL '7 days'),
('CH-002', 'River Guardian', 'Submit 3 water quality reports for local rivers', 'individual', 'water_report', 3, 150, NOW() - INTERVAL '14 days', NOW() + INTERVAL '14 days'),
('CH-003', 'Noise Patrol', 'Report noise violations in silence zones', 'community', 'noise_report', 20, 200, NOW() - INTERVAL '30 days', NOW() + INTERVAL '30 days'),
('CH-004', 'Green Commute', 'Log 10 days of green commuting (walk/cycle/public transport)', 'individual', 'green_commute', 10, 250, NOW(), NOW() + INTERVAL '30 days');
