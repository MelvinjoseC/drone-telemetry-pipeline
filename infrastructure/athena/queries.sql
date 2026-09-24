-- ────────────────────────────────────────────────────────
--  Amazon Athena Analytical Queries for Drone Telemetry
-- ────────────────────────────────────────────────────────

-- 1. Fleet Flight Summary (Total distance, avg speed, min battery)
SELECT 
    drone_id,
    COUNT(*) AS total_telemetry_points,
    ROUND(AVG(speed_kmh), 2) AS avg_speed_kmh,
    ROUND(MAX(speed_kmh), 2) AS max_speed_kmh,
    ROUND(MAX(altitude_m), 2) AS max_altitude_m,
    ROUND(MIN(battery_pct), 1) AS min_battery_pct,
    MIN(timestamp) AS mission_start,
    MAX(timestamp) AS mission_end
FROM "drone_telemetry_db_dev"."telemetry_records"
WHERE year = '2024' AND month = '01'
GROUP BY drone_id
ORDER BY total_telemetry_points DESC;


-- 2. Detect Safety Ceiling Violations (> 120m regulatory limit)
SELECT 
    drone_id,
    timestamp,
    altitude_m,
    speed_kmh,
    latitude,
    longitude,
    flight_mode
FROM "drone_telemetry_db_dev"."telemetry_records"
WHERE altitude_m > 120.0
ORDER BY altitude_m DESC;


-- 3. Critical Battery Alerts (< 15% charge)
SELECT 
    drone_id,
    timestamp,
    battery_pct,
    altitude_m,
    speed_kmh,
    flight_mode,
    latitude,
    longitude
FROM "drone_telemetry_db_dev"."telemetry_records"
WHERE battery_pct <= 15.0
ORDER BY timestamp DESC;


-- 4. Hourly Telemetry Ingestion Volume
SELECT 
    year,
    month,
    day,
    hour,
    COUNT(*) AS records_ingested,
    COUNT(DISTINCT drone_id) AS active_drones
FROM "drone_telemetry_db_dev"."telemetry_records"
GROUP BY year, month, day, hour
ORDER BY year DESC, month DESC, day DESC, hour DESC;


-- 5. Flight Mode Distribution Analysis
SELECT 
    flight_mode,
    COUNT(*) AS count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage
FROM "drone_telemetry_db_dev"."telemetry_records"
GROUP BY flight_mode
ORDER BY count DESC;
