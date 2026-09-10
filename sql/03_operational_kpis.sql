-- ==============================================================================
-- Portfolio Project: Flight Delay Analysis Using SQL
-- File: 03_operational_kpis.sql
-- Description: Core Operational KPIs: Volume, OTP-15, Cancellations & Seasonality.
-- Standard: ANSI SQL / SQLite 3+
-- ==============================================================================

-- -----------------------------------------------------------------------------
-- Query 1: Executive KPI Dashboard Overview
-- Business Question: What are the fleet-wide baseline operational metrics across all carriers?
-- -----------------------------------------------------------------------------
SELECT 
    COUNT(*) AS total_scheduled_flights,
    SUM(CASE WHEN cancelled = 0 AND diverted = 0 THEN 1 ELSE 0 END) AS completed_flights,
    SUM(cancelled) AS cancelled_flights,
    ROUND(SUM(cancelled) * 100.0 / COUNT(*), 2) AS cancellation_rate_pct,
    SUM(diverted) AS diverted_flights,
    ROUND(SUM(diverted) * 100.0 / COUNT(*), 2) AS diversion_rate_pct,
    ROUND(SUM(CASE WHEN cancelled = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS completion_factor_pct,
    -- FAA / BTS Industry Standard: Arrival within 14 minutes of schedule is classified On-Time
    ROUND(SUM(is_on_time_otp15) * 100.0 / SUM(CASE WHEN cancelled = 0 AND diverted = 0 THEN 1 ELSE 0 END), 2) AS on_time_arrival_rate_pct,
    ROUND(AVG(dep_delay), 2) AS avg_departure_delay_mins,
    ROUND(AVG(arr_delay), 2) AS avg_arrival_delay_mins,
    ROUND(AVG(taxi_out), 2) AS avg_taxi_out_mins,
    ROUND(AVG(distance), 0) AS avg_flight_distance_miles
FROM v_flights_operational_master;

-- -----------------------------------------------------------------------------
-- Query 2: Monthly Seasonality & Operational Degradation Trend
-- Business Question: How do on-time performance and delays fluctuate month-over-month?
-- -----------------------------------------------------------------------------
SELECT 
    flight_month,
    COUNT(*) AS total_flights,
    SUM(cancelled) AS cancellations,
    ROUND(SUM(cancelled) * 100.0 / COUNT(*), 2) AS cancellation_rate_pct,
    ROUND(SUM(is_on_time_otp15) * 100.0 / SUM(CASE WHEN cancelled = 0 AND diverted = 0 THEN 1 ELSE 0 END), 2) AS otp15_pct,
    ROUND(AVG(dep_delay), 2) AS avg_dep_delay_mins,
    ROUND(AVG(arr_delay), 2) AS avg_arr_delay_mins,
    ROUND(SUM(CASE WHEN arr_delay > 0 THEN arr_delay * 74.24 ELSE 0 END) / 1000000.0, 2) AS est_delay_cost_million_usd
FROM v_flights_operational_master
GROUP BY flight_month
ORDER BY flight_month ASC;

-- -----------------------------------------------------------------------------
-- Query 3: Hourly Departure Profile & The "Afternoon Delay Cascade"
-- Business Question: At what hour of the day does system congestion peak?
-- -----------------------------------------------------------------------------
SELECT 
    dep_hour_bucket || ':00' AS departure_hour,
    COUNT(*) AS scheduled_flights,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM flights), 2) AS pct_of_daily_volume,
    ROUND(AVG(dep_delay), 2) AS avg_dep_delay_mins,
    ROUND(AVG(arr_delay), 2) AS avg_arr_delay_mins,
    ROUND(AVG(taxi_out), 2) AS avg_taxi_out_mins,
    ROUND(SUM(is_on_time_otp15) * 100.0 / SUM(CASE WHEN cancelled = 0 AND diverted = 0 THEN 1 ELSE 0 END), 2) AS otp15_pct,
    ROUND(SUM(is_delayed_15plus) * 100.0 / SUM(CASE WHEN cancelled = 0 AND diverted = 0 THEN 1 ELSE 0 END), 2) AS severe_delay_pct
FROM v_flights_operational_master
GROUP BY dep_hour_bucket
ORDER BY dep_hour_bucket ASC;

-- -----------------------------------------------------------------------------
-- Query 4: Day-of-Week Operational Punctuality Profile
-- Business Question: Does day-of-week passenger load impact flight punctuality?
-- -----------------------------------------------------------------------------
SELECT 
    CASE strftime('%w', flight_date)
        WHEN '0' THEN 'Sunday'
        WHEN '1' THEN 'Monday'
        WHEN '2' THEN 'Tuesday'
        WHEN '3' THEN 'Wednesday'
        WHEN '4' THEN 'Thursday'
        WHEN '5' THEN 'Friday'
        WHEN '6' THEN 'Saturday'
    END AS day_name,
    COUNT(*) AS scheduled_flights,
    ROUND(SUM(is_on_time_otp15) * 100.0 / SUM(CASE WHEN cancelled = 0 AND diverted = 0 THEN 1 ELSE 0 END), 2) AS otp15_pct,
    ROUND(AVG(dep_delay), 2) AS avg_dep_delay_mins,
    ROUND(AVG(arr_delay), 2) AS avg_arr_delay_mins,
    ROUND(SUM(cancelled) * 100.0 / COUNT(*), 2) AS cancellation_rate_pct
FROM v_flights_operational_master
GROUP BY strftime('%w', flight_date)
ORDER BY CAST(strftime('%w', flight_date) AS INTEGER) ASC;

-- -----------------------------------------------------------------------------
-- Query 5: Distance Tier Segmentation & Delay Absorption
-- Business Question: Do long-haul flights absorb departure delays better than short hops?
-- -----------------------------------------------------------------------------
WITH distance_tiers AS (
    SELECT 
        CASE 
            WHEN distance < 500 THEN '1. Short-Haul (<500 mi)'
            WHEN distance BETWEEN 500 AND 1500 THEN '2. Medium-Haul (500-1500 mi)'
            ELSE '3. Long-Haul (>1500 mi)'
        END AS distance_category,
        dep_delay,
        arr_delay,
        en_route_delay_delta,
        is_on_time_otp15,
        cancelled,
        diverted
    FROM v_flights_operational_master
)
SELECT 
    distance_category,
    COUNT(*) AS flight_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM flights), 2) AS pct_of_flights,
    ROUND(AVG(dep_delay), 2) AS avg_dep_delay_mins,
    ROUND(AVG(arr_delay), 2) AS avg_arr_delay_mins,
    ROUND(AVG(en_route_delay_delta), 2) AS avg_airborne_time_delta_mins,
    ROUND(SUM(is_on_time_otp15) * 100.0 / SUM(CASE WHEN cancelled = 0 AND diverted = 0 THEN 1 ELSE 0 END), 2) AS otp15_pct
FROM distance_tiers
GROUP BY distance_category
ORDER BY distance_category ASC;
