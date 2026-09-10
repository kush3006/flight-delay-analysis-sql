-- ==============================================================================
-- Portfolio Project: Flight Delay Analysis Using SQL
-- File: 02_data_cleaning_and_audit.sql
-- Description: Data Quality Profiling, Anomaly Detection & Integrity Auditing.
-- Standard: ANSI SQL / SQLite 3+
-- ==============================================================================

-- -----------------------------------------------------------------------------
-- Query 1: Comprehensive Data Profiling & Null Value Audit
-- Business Purpose: Ensure required fields meet completeness thresholds before downstream reporting.
-- -----------------------------------------------------------------------------
SELECT 
    COUNT(*) AS total_records,
    COUNT(flight_id) AS valid_flight_ids,
    SUM(CASE WHEN flight_date IS NULL OR flight_date = '' THEN 1 ELSE 0 END) AS missing_dates,
    SUM(CASE WHEN carrier_code IS NULL THEN 1 ELSE 0 END) AS missing_carrier,
    SUM(CASE WHEN origin_airport IS NULL OR dest_airport IS NULL THEN 1 ELSE 0 END) AS missing_airports,
    SUM(CASE WHEN dep_time IS NULL AND cancelled = 0 THEN 1 ELSE 0 END) AS missing_dep_time_unexplained,
    SUM(CASE WHEN arr_time IS NULL AND cancelled = 0 AND diverted = 0 THEN 1 ELSE 0 END) AS missing_arr_time_unexplained,
    SUM(CASE WHEN distance <= 0 THEN 1 ELSE 0 END) AS invalid_distance_records
FROM flights;

-- -----------------------------------------------------------------------------
-- Query 2: Natural Key Duplicate Detection
-- Business Purpose: Confirm that no physical aircraft was double-scheduled at the same instant.
-- -----------------------------------------------------------------------------
WITH duplicate_audit AS (
    SELECT 
        flight_date,
        carrier_code,
        flight_number,
        origin_airport,
        sched_dep_time,
        COUNT(*) AS occurrence_count
    FROM flights
    GROUP BY flight_date, carrier_code, flight_number, origin_airport, sched_dep_time
    HAVING COUNT(*) > 1
)
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN 'PASS: No duplicate flight schedules detected.'
        ELSE 'FAIL: Duplicate schedules found.'
    END AS audit_result,
    COUNT(*) AS duplicate_schedule_clusters
FROM duplicate_audit;

-- -----------------------------------------------------------------------------
-- Query 3: Mathematical Consistency of BTS Delay Attributions
-- Business Purpose: FAA/BTS standard stipulates that for all delayed flights (arr_delay >= 15),
-- the sum of carrier, weather, nas, security, and late_aircraft delays must match arrival delay.
-- -----------------------------------------------------------------------------
SELECT 
    COUNT(*) AS delayed_flight_count,
    SUM(CASE 
        WHEN (carrier_delay + weather_delay + nas_delay + security_delay + late_aircraft_delay) = arr_delay 
        THEN 1 ELSE 0 
    END) AS mathematically_sound_records,
    SUM(CASE 
        WHEN (carrier_delay + weather_delay + nas_delay + security_delay + late_aircraft_delay) <> arr_delay 
        THEN 1 ELSE 0 
    END) AS discrepant_delay_records
FROM flights
WHERE arr_delay >= 15 AND cancelled = 0 AND diverted = 0;

-- -----------------------------------------------------------------------------
-- Query 4: Operational Boundary Auditing (Taxi Times and Airborne Speed)
-- Business Purpose: Identify extreme physical outliers (e.g. taxi-out exceeding 2 hours or implausible ground speeds).
-- -----------------------------------------------------------------------------
SELECT 
    flight_id,
    flight_date,
    carrier_code,
    origin_airport,
    dest_airport,
    distance,
    air_time,
    ROUND((CAST(distance AS REAL) / (air_time / 60.0)), 1) AS computed_ground_speed_mph,
    taxi_out,
    CASE 
        WHEN taxi_out > 90 THEN 'Extreme Taxi-Out Anomaly (>90m)'
        WHEN air_time < 20 THEN 'Implausible Short Air-Time (<20m)'
        WHEN (CAST(distance AS REAL) / (air_time / 60.0)) > 650 THEN 'Excessive Ground Speed (>650 mph)'
        ELSE 'Normal'
    END AS operational_flag
FROM flights
WHERE cancelled = 0 AND diverted = 0
  AND (taxi_out > 90 OR air_time < 20 OR (CAST(distance AS REAL) / (air_time / 60.0)) > 650)
LIMIT 20;

-- -----------------------------------------------------------------------------
-- Query 5: Cancellation Reason Categorization Audit
-- Business Purpose: Verify that every cancelled flight has a valid DOT reason code (A, B, C, D).
-- -----------------------------------------------------------------------------
SELECT 
    COALESCE(cancellation_code, 'UNASSIGNED') AS raw_code,
    CASE cancellation_code
        WHEN 'A' THEN 'Carrier Operation (Crew, Maintenance)'
        WHEN 'B' THEN 'Extreme Weather'
        WHEN 'C' THEN 'National Airspace System (ATC Volume)'
        WHEN 'D' THEN 'Security'
        ELSE 'Uncategorized'
    END AS reason_description,
    COUNT(*) AS cancellation_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM flights WHERE cancelled = 1), 2) AS pct_of_cancellations
FROM flights
WHERE cancelled = 1
GROUP BY cancellation_code
ORDER BY cancellation_count DESC;
