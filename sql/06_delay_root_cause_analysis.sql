-- ==============================================================================
-- Portfolio Project: Flight Delay Analysis Using SQL
-- File: 06_delay_root_cause_analysis.sql
-- Description: Root Cause Attribution Modeling (Carrier, Weather, NAS, Security, Late Aircraft).
-- Standard: ANSI SQL / SQLite 3+
-- ==============================================================================

-- -----------------------------------------------------------------------------
-- Query 1: Macro Delay Attribution Breakdown (National Level)
-- Business Question: What primary mechanisms drive aggregate flight delays across the aviation system?
-- -----------------------------------------------------------------------------
WITH delay_totals AS (
    SELECT 
        SUM(carrier_delay) AS total_carrier_delay,
        SUM(weather_delay) AS total_weather_delay,
        SUM(nas_delay) AS total_nas_delay,
        SUM(security_delay) AS total_security_delay,
        SUM(late_aircraft_delay) AS total_late_aircraft_delay,
        SUM(arr_delay) AS total_net_delay_minutes
    FROM flights
    WHERE arr_delay >= 15 AND cancelled = 0 AND diverted = 0
)
SELECT 
    'Carrier Internal (Maintenance / Crew / Baggage)' AS delay_cause,
    total_carrier_delay AS total_delay_minutes,
    ROUND(total_carrier_delay * 100.0 / total_net_delay_minutes, 2) AS pct_share_of_total_delays
FROM delay_totals
UNION ALL
SELECT 
    'Late Aircraft Cascading Propagation (Turnaround)',
    total_late_aircraft_delay,
    ROUND(total_late_aircraft_delay * 100.0 / total_net_delay_minutes, 2)
FROM delay_totals
UNION ALL
SELECT 
    'National Airspace System (ATC Volume & Flow)',
    total_nas_delay,
    ROUND(total_nas_delay * 100.0 / total_net_delay_minutes, 2)
FROM delay_totals
UNION ALL
SELECT 
    'Extreme Weather Conditions',
    total_weather_delay,
    ROUND(total_weather_delay * 100.0 / total_net_delay_minutes, 2)
FROM delay_totals
UNION ALL
SELECT 
    'Security Breaches / Re-Screening',
    total_security_delay,
    ROUND(total_security_delay * 100.0 / total_net_delay_minutes, 2)
FROM delay_totals
ORDER BY total_delay_minutes DESC;

-- -----------------------------------------------------------------------------
-- Query 2: Airline Vulnerability Fingerprint (Cause Breakdown by Carrier)
-- Business Question: Does each airline suffer from internal execution issues or external system congestion?
-- -----------------------------------------------------------------------------
WITH carrier_causes AS (
    SELECT 
        carrier_code,
        airline_name,
        SUM(arr_delay) AS total_arr_delay,
        SUM(carrier_delay) AS carrier_mins,
        SUM(weather_delay) AS weather_mins,
        SUM(nas_delay) AS nas_mins,
        SUM(late_aircraft_delay) AS late_aircraft_mins
    FROM v_flights_operational_master
    WHERE is_delayed_15plus = 1
    GROUP BY carrier_code, airline_name
)
SELECT 
    carrier_code,
    airline_name,
    total_arr_delay AS aggregate_delay_minutes,
    ROUND(carrier_mins * 100.0 / total_arr_delay, 1) AS pct_carrier_internal,
    ROUND(late_aircraft_mins * 100.0 / total_arr_delay, 1) AS pct_late_aircraft,
    ROUND(nas_mins * 100.0 / total_arr_delay, 1) AS pct_nas_atc,
    ROUND(weather_mins * 100.0 / total_arr_delay, 1) AS pct_weather
FROM carrier_causes
ORDER BY aggregate_delay_minutes DESC;

-- -----------------------------------------------------------------------------
-- Query 3: Airport Vulnerability Profile: Weather-Sensitive vs ATC-Congested Hubs
-- Business Question: Which airports suffer primarily from runway/airspace capacity (NAS) vs weather events?
-- -----------------------------------------------------------------------------
SELECT 
    origin_airport,
    origin_city,
    COUNT(*) AS delayed_departures,
    SUM(nas_delay) AS total_nas_mins,
    SUM(weather_delay) AS total_weather_mins,
    ROUND(SUM(nas_delay) * 100.0 / SUM(arr_delay), 1) AS pct_nas_delay,
    ROUND(SUM(weather_delay) * 100.0 / SUM(arr_delay), 1) AS pct_weather_delay,
    CASE 
        WHEN SUM(nas_delay) > 1.8 * SUM(weather_delay) THEN 'Airspace / Runway Capacity Bottleneck (NAS)'
        WHEN SUM(weather_delay) > 1.2 * SUM(nas_delay) THEN 'Meteorological Vulnerability (Weather)'
        ELSE 'Balanced Multi-Factor Friction'
    END AS primary_hub_friction_profile
FROM v_flights_operational_master
WHERE is_delayed_15plus = 1
GROUP BY origin_airport, origin_city
HAVING COUNT(*) >= 200
ORDER BY total_nas_mins DESC
LIMIT 12;

-- -----------------------------------------------------------------------------
-- Query 4: Progression of Late Aircraft Cascades by Hour of Day
-- Business Question: How does aircraft rotation delay propagate through flight legs as the day advances?
-- -----------------------------------------------------------------------------
SELECT 
    dep_hour_bucket || ':00' AS time_of_day,
    COUNT(*) AS delayed_flights,
    SUM(carrier_delay) AS carrier_delay_mins,
    SUM(late_aircraft_delay) AS late_aircraft_delay_mins,
    -- Ratio of late aircraft delay to internal carrier delay
    ROUND(CAST(SUM(late_aircraft_delay) AS REAL) / NULLIF(SUM(carrier_delay), 0), 2) AS late_aircraft_to_carrier_ratio,
    ROUND(SUM(late_aircraft_delay) * 100.0 / SUM(arr_delay), 1) AS late_aircraft_pct_of_total
FROM v_flights_operational_master
WHERE is_delayed_15plus = 1
GROUP BY dep_hour_bucket
ORDER BY dep_hour_bucket ASC;
