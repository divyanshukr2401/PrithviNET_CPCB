-- ============================================================================
-- NANMN (National Ambient Noise Monitoring Network) — 70 Stations
-- Source: CPCB Continuous Noise Monitoring across 7 major Indian cities
-- Each city has 10 stations covering Industrial, Commercial, Residential, Silence zones
-- CPCB Limits (dB(A)): Industrial 75/70, Commercial 65/55, Residential 55/45, Silence 50/40
-- ============================================================================

INSERT INTO noise_stations (station_id, station_name, zone_type, city, state, geom, day_limit, night_limit)
VALUES
-- ── DELHI (10 stations) ─────────────────────────────────────────────────────
('NANMN-DEL-01', 'ITO Junction',                    'commercial',  'Delhi',     'Delhi',             ST_SetSRID(ST_MakePoint(77.2406, 28.6289), 4326), 65, 55),
('NANMN-DEL-02', 'Anand Vihar ISBT',                'commercial',  'Delhi',     'Delhi',             ST_SetSRID(ST_MakePoint(77.3164, 28.6469), 4326), 65, 55),
('NANMN-DEL-03', 'Dilshad Garden',                  'residential', 'Delhi',     'Delhi',             ST_SetSRID(ST_MakePoint(77.3194, 28.6827), 4326), 55, 45),
('NANMN-DEL-04', 'Shahzada Bagh Industrial Area',   'industrial',  'Delhi',     'Delhi',             ST_SetSRID(ST_MakePoint(77.1629, 28.6741), 4326), 75, 70),
('NANMN-DEL-05', 'Naraina Industrial Area',         'industrial',  'Delhi',     'Delhi',             ST_SetSRID(ST_MakePoint(77.1401, 28.6293), 4326), 75, 70),
('NANMN-DEL-06', 'AIIMS Hospital Zone',             'silence',     'Delhi',     'Delhi',             ST_SetSRID(ST_MakePoint(77.2100, 28.5672), 4326), 50, 40),
('NANMN-DEL-07', 'Civil Lines',                     'residential', 'Delhi',     'Delhi',             ST_SetSRID(ST_MakePoint(77.2229, 28.6805), 4326), 55, 45),
('NANMN-DEL-08', 'Mayapuri Industrial Area',        'industrial',  'Delhi',     'Delhi',             ST_SetSRID(ST_MakePoint(77.1180, 28.6292), 4326), 75, 70),
('NANMN-DEL-09', 'Wazirpur Industrial Area',        'industrial',  'Delhi',     'Delhi',             ST_SetSRID(ST_MakePoint(77.1663, 28.6972), 4326), 75, 70),
('NANMN-DEL-10', 'Sarojini Nagar Market',           'commercial',  'Delhi',     'Delhi',             ST_SetSRID(ST_MakePoint(77.1985, 28.5752), 4326), 65, 55),

-- ── MUMBAI (10 stations) ────────────────────────────────────────────────────
('NANMN-MUM-01', 'Dadar TT Circle',                 'commercial',  'Mumbai',    'Maharashtra',       ST_SetSRID(ST_MakePoint(72.8430, 19.0183), 4326), 65, 55),
('NANMN-MUM-02', 'Worli Sea Face',                  'residential', 'Mumbai',    'Maharashtra',       ST_SetSRID(ST_MakePoint(72.8157, 19.0096), 4326), 55, 45),
('NANMN-MUM-03', 'Andheri East',                    'commercial',  'Mumbai',    'Maharashtra',       ST_SetSRID(ST_MakePoint(72.8682, 19.1197), 4326), 65, 55),
('NANMN-MUM-04', 'Chembur Industrial Area',         'industrial',  'Mumbai',    'Maharashtra',       ST_SetSRID(ST_MakePoint(72.8956, 19.0614), 4326), 75, 70),
('NANMN-MUM-05', 'Powai Lake Area',                 'residential', 'Mumbai',    'Maharashtra',       ST_SetSRID(ST_MakePoint(72.9065, 19.1266), 4326), 55, 45),
('NANMN-MUM-06', 'KEM Hospital Zone',               'silence',     'Mumbai',    'Maharashtra',       ST_SetSRID(ST_MakePoint(72.8416, 19.0013), 4326), 50, 40),
('NANMN-MUM-07', 'Borivali National Park Gate',     'residential', 'Mumbai',    'Maharashtra',       ST_SetSRID(ST_MakePoint(72.8567, 19.2307), 4326), 55, 45),
('NANMN-MUM-08', 'Mulund Industrial Estate',        'industrial',  'Mumbai',    'Maharashtra',       ST_SetSRID(ST_MakePoint(72.9563, 19.1726), 4326), 75, 70),
('NANMN-MUM-09', 'Bandra West Station Road',        'commercial',  'Mumbai',    'Maharashtra',       ST_SetSRID(ST_MakePoint(72.8295, 19.0596), 4326), 65, 55),
('NANMN-MUM-10', 'Goregaon Filmcity Road',          'commercial',  'Mumbai',    'Maharashtra',       ST_SetSRID(ST_MakePoint(72.8497, 19.1549), 4326), 65, 55),

-- ── KOLKATA (10 stations) ───────────────────────────────────────────────────
('NANMN-KOL-01', 'Park Street Junction',            'commercial',  'Kolkata',   'West Bengal',       ST_SetSRID(ST_MakePoint(88.3583, 22.5516), 4326), 65, 55),
('NANMN-KOL-02', 'Howrah Railway Station',          'commercial',  'Kolkata',   'West Bengal',       ST_SetSRID(ST_MakePoint(88.3390, 22.5839), 4326), 65, 55),
('NANMN-KOL-03', 'Salt Lake Sector V',              'residential', 'Kolkata',   'West Bengal',       ST_SetSRID(ST_MakePoint(88.4142, 22.5804), 4326), 55, 45),
('NANMN-KOL-04', 'Jadavpur',                        'residential', 'Kolkata',   'West Bengal',       ST_SetSRID(ST_MakePoint(88.3714, 22.4989), 4326), 55, 45),
('NANMN-KOL-05', 'Belgachia Industrial Area',       'industrial',  'Kolkata',   'West Bengal',       ST_SetSRID(ST_MakePoint(88.3648, 22.5917), 4326), 75, 70),
('NANMN-KOL-06', 'Tollygunge Metro Junction',       'commercial',  'Kolkata',   'West Bengal',       ST_SetSRID(ST_MakePoint(88.3512, 22.4986), 4326), 65, 55),
('NANMN-KOL-07', 'SSKM Hospital Zone',              'silence',     'Kolkata',   'West Bengal',       ST_SetSRID(ST_MakePoint(88.3432, 22.5380), 4326), 50, 40),
('NANMN-KOL-08', 'Ultadanga Flyover',               'commercial',  'Kolkata',   'West Bengal',       ST_SetSRID(ST_MakePoint(88.3870, 22.5900), 4326), 65, 55),
('NANMN-KOL-09', 'Dum Dum Airport Road',            'residential', 'Kolkata',   'West Bengal',       ST_SetSRID(ST_MakePoint(88.4264, 22.6221), 4326), 55, 45),
('NANMN-KOL-10', 'Behala Chowrasta',                'residential', 'Kolkata',   'West Bengal',       ST_SetSRID(ST_MakePoint(88.3150, 22.4600), 4326), 55, 45),

-- ── CHENNAI (10 stations) ───────────────────────────────────────────────────
('NANMN-CHN-01', 'T Nagar Ranganathan Street',      'commercial',  'Chennai',   'Tamil Nadu',        ST_SetSRID(ST_MakePoint(80.2296, 13.0358), 4326), 65, 55),
('NANMN-CHN-02', 'Anna Nagar Tower Park',           'residential', 'Chennai',   'Tamil Nadu',        ST_SetSRID(ST_MakePoint(80.2099, 13.0865), 4326), 55, 45),
('NANMN-CHN-03', 'Guindy Industrial Estate',        'industrial',  'Chennai',   'Tamil Nadu',        ST_SetSRID(ST_MakePoint(80.2133, 13.0100), 4326), 75, 70),
('NANMN-CHN-04', 'Egmore Railway Station',          'commercial',  'Chennai',   'Tamil Nadu',        ST_SetSRID(ST_MakePoint(80.2609, 13.0732), 4326), 65, 55),
('NANMN-CHN-05', 'Adyar Signal Junction',           'residential', 'Chennai',   'Tamil Nadu',        ST_SetSRID(ST_MakePoint(80.2573, 13.0062), 4326), 55, 45),
('NANMN-CHN-06', 'Ambattur Industrial Estate',      'industrial',  'Chennai',   'Tamil Nadu',        ST_SetSRID(ST_MakePoint(80.1594, 13.1141), 4326), 75, 70),
('NANMN-CHN-07', 'Royapettah Hospital Zone',        'silence',     'Chennai',   'Tamil Nadu',        ST_SetSRID(ST_MakePoint(80.2641, 13.0550), 4326), 50, 40),
('NANMN-CHN-08', 'Perambur Loco Works',             'industrial',  'Chennai',   'Tamil Nadu',        ST_SetSRID(ST_MakePoint(80.2405, 13.1126), 4326), 75, 70),
('NANMN-CHN-09', 'Tambaram Station Road',           'residential', 'Chennai',   'Tamil Nadu',        ST_SetSRID(ST_MakePoint(80.1168, 12.9249), 4326), 55, 45),
('NANMN-CHN-10', 'Mylapore Tank',                   'commercial',  'Chennai',   'Tamil Nadu',        ST_SetSRID(ST_MakePoint(80.2676, 13.0368), 4326), 65, 55),

-- ── BENGALURU (10 stations) ─────────────────────────────────────────────────
('NANMN-BLR-01', 'MG Road Metro Station',           'commercial',  'Bengaluru', 'Karnataka',         ST_SetSRID(ST_MakePoint(77.6074, 12.9757), 4326), 65, 55),
('NANMN-BLR-02', 'Peenya Industrial Area',          'industrial',  'Bengaluru', 'Karnataka',         ST_SetSRID(ST_MakePoint(77.5197, 13.0298), 4326), 75, 70),
('NANMN-BLR-03', 'Jayanagar 4th Block',             'residential', 'Bengaluru', 'Karnataka',         ST_SetSRID(ST_MakePoint(77.5838, 12.9308), 4326), 55, 45),
('NANMN-BLR-04', 'Whitefield ITPL Road',            'commercial',  'Bengaluru', 'Karnataka',         ST_SetSRID(ST_MakePoint(77.7500, 12.9698), 4326), 65, 55),
('NANMN-BLR-05', 'Rajajinagar Industrial Town',     'commercial',  'Bengaluru', 'Karnataka',         ST_SetSRID(ST_MakePoint(77.5555, 12.9892), 4326), 65, 55),
('NANMN-BLR-06', 'Kidwai Hospital Zone',            'silence',     'Bengaluru', 'Karnataka',         ST_SetSRID(ST_MakePoint(77.5718, 12.9381), 4326), 50, 40),
('NANMN-BLR-07', 'Yeshwanthpur Industrial Suburb',  'industrial',  'Bengaluru', 'Karnataka',         ST_SetSRID(ST_MakePoint(77.5533, 13.0226), 4326), 75, 70),
('NANMN-BLR-08', 'Koramangala Inner Ring Road',     'residential', 'Bengaluru', 'Karnataka',         ST_SetSRID(ST_MakePoint(77.6245, 12.9352), 4326), 55, 45),
('NANMN-BLR-09', 'Banashankari BDA Complex',        'residential', 'Bengaluru', 'Karnataka',         ST_SetSRID(ST_MakePoint(77.5633, 12.9109), 4326), 55, 45),
('NANMN-BLR-10', 'Electronic City Phase 1',         'industrial',  'Bengaluru', 'Karnataka',         ST_SetSRID(ST_MakePoint(77.6702, 12.8455), 4326), 75, 70),

-- ── HYDERABAD (10 stations) ─────────────────────────────────────────────────
('NANMN-HYD-01', 'Abids GPO Junction',              'commercial',  'Hyderabad', 'Telangana',         ST_SetSRID(ST_MakePoint(78.4747, 17.3923), 4326), 65, 55),
('NANMN-HYD-02', 'Moosapet Crossroads',             'commercial',  'Hyderabad', 'Telangana',         ST_SetSRID(ST_MakePoint(78.4285, 17.4594), 4326), 65, 55),
('NANMN-HYD-03', 'Kukatpally Housing Board',        'commercial',  'Hyderabad', 'Telangana',         ST_SetSRID(ST_MakePoint(78.3997, 17.4947), 4326), 65, 55),
('NANMN-HYD-04', 'Nacharam Industrial Area',        'industrial',  'Hyderabad', 'Telangana',         ST_SetSRID(ST_MakePoint(78.5488, 17.4260), 4326), 75, 70),
('NANMN-HYD-05', 'Banjara Hills Road No. 12',       'residential', 'Hyderabad', 'Telangana',         ST_SetSRID(ST_MakePoint(78.4436, 17.4138), 4326), 55, 45),
('NANMN-HYD-06', 'Osmania General Hospital Zone',   'silence',     'Hyderabad', 'Telangana',         ST_SetSRID(ST_MakePoint(78.4748, 17.3668), 4326), 50, 40),
('NANMN-HYD-07', 'Jeedimetla Industrial Area',      'industrial',  'Hyderabad', 'Telangana',         ST_SetSRID(ST_MakePoint(78.4357, 17.5125), 4326), 75, 70),
('NANMN-HYD-08', 'Secunderabad Railway Station',    'commercial',  'Hyderabad', 'Telangana',         ST_SetSRID(ST_MakePoint(78.5016, 17.4337), 4326), 65, 55),
('NANMN-HYD-09', 'Himayatnagar Main Road',          'residential', 'Hyderabad', 'Telangana',         ST_SetSRID(ST_MakePoint(78.4870, 17.3990), 4326), 55, 45),
('NANMN-HYD-10', 'LB Nagar Crossroads',             'residential', 'Hyderabad', 'Telangana',         ST_SetSRID(ST_MakePoint(78.5481, 17.3491), 4326), 55, 45),

-- ── LUCKNOW (10 stations) ───────────────────────────────────────────────────
('NANMN-LKO-01', 'Charbagh Railway Station',        'commercial',  'Lucknow',   'Uttar Pradesh',     ST_SetSRID(ST_MakePoint(80.9389, 26.8552), 4326), 65, 55),
('NANMN-LKO-02', 'Hazratganj Crossing',             'commercial',  'Lucknow',   'Uttar Pradesh',     ST_SetSRID(ST_MakePoint(80.9479, 26.8489), 4326), 65, 55),
('NANMN-LKO-03', 'Aliganj Kapoorthala Complex',     'residential', 'Lucknow',   'Uttar Pradesh',     ST_SetSRID(ST_MakePoint(80.9399, 26.8889), 4326), 55, 45),
('NANMN-LKO-04', 'Talkatora Industrial Area',       'industrial',  'Lucknow',   'Uttar Pradesh',     ST_SetSRID(ST_MakePoint(80.9018, 26.8629), 4326), 75, 70),
('NANMN-LKO-05', 'Amausi Industrial Belt',          'industrial',  'Lucknow',   'Uttar Pradesh',     ST_SetSRID(ST_MakePoint(80.8889, 26.7667), 4326), 75, 70),
('NANMN-LKO-06', 'KGMU Hospital Zone',              'silence',     'Lucknow',   'Uttar Pradesh',     ST_SetSRID(ST_MakePoint(80.9375, 26.8628), 4326), 50, 40),
('NANMN-LKO-07', 'Gomti Nagar Vibhuti Khand',       'residential', 'Lucknow',   'Uttar Pradesh',     ST_SetSRID(ST_MakePoint(80.9788, 26.8530), 4326), 55, 45),
('NANMN-LKO-08', 'Alambagh Bus Station',            'commercial',  'Lucknow',   'Uttar Pradesh',     ST_SetSRID(ST_MakePoint(80.9120, 26.8198), 4326), 65, 55),
('NANMN-LKO-09', 'Indira Nagar Munshi Pulia',       'residential', 'Lucknow',   'Uttar Pradesh',     ST_SetSRID(ST_MakePoint(80.9960, 26.8729), 4326), 55, 45),
('NANMN-LKO-10', 'Chinhat Industrial Area',         'industrial',  'Lucknow',   'Uttar Pradesh',     ST_SetSRID(ST_MakePoint(81.0267, 26.8739), 4326), 75, 70)

ON CONFLICT (station_id) DO NOTHING;
