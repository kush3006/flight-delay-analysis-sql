-- ==============================================================================
-- Portfolio Project: Flight Delay Analysis Using SQL
-- File: 04_carrier_benchmarking.sql
-- Description: Competitive Airline Benchmarking, OTP Rankings, and En-Route Recovery.
-- Standard: ANSI SQL / SQLite 3+
-- ==============================================================================

-- -----------------------------------------------------------------------------
-- Query 1: Airline Punctuality League Table & DENSE_RANK()
-- Business Question: How do commercial airlines rank when evaluated by On-Time Performance?
-- -----------------------------------------------------------------------------
WITH carrier_metrics AS (
    SELECT 
        carrier_code,
        airline_name,
        COUNT(*) AS total_flights,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM flights), 2) AS market_share_pct,
        SUM(cancelled) AS cancellations,
        ROUND(SUM(cancelled) * 100.0 / COUNT(*), 2) AS cancellation_rate_pct,
        SUM(CASE WHEN cancelled = 0 AND diverted = 0 THEN 1 ELSE 0 END) AS completed_flights,
        ROUND(SUM(is_on_time_otp15) * 100.0 / SUM(CASE WHEN cancelled = 0 AND diverted = 0 THEN 1 ELSE 0 END), 2) AS otp15_pct,
        ROUND(AVG(dep_delay), 2) AS avg_dep_delay_mins,
        ROUND(AVG(arr_delay), 2) AS avg_arr_delay_mins
    FROM v_flights_operational_master
    GROUP BY carrier_code, airline_name
)
SELECT 
    DENSE_RANK() OVER (ORDER BY otp15_pct DESC) AS punctuality_rank,
    carrier_code,
    airline_name,
    total_flights,
    market_share_pct,
    otp15_pct,
    avg_dep_delay_mins,
    avg_arr_delay_mins,
    cancellation_rate_pct
FROM carrier_metrics
ORDER BY punctuality_rank ASC;

-- -----------------------------------------------------------------------------
-- Query 2: In-Flight Delay Recovery (Airborne Operational Efficiency)
-- Business Question: When an aircraft departs late (>= 15 mins), which airline is most effective
-- at throttling up en-route to recover lost time before gate arrival?
-- -----------------------------------------------------------------------------
WITH delayed_departures AS (
    SELECT 
        carrier_code,
        airline_name,
        flight_id,
        dep_delay,
        arr_delay,
        en_route_delay_delta, -- arr_delay - dep_delay (negative indicates recovered time)
        CASE WHEN arr_delay < 15 THEN 1 ELSE 0 END AS recovered_to_on_time
    FROM v_flights_operational_master
    WHERE dep_delay >= 15 AND cancelled = 0 AND diverted = 0
)
SELECT 
    carrier_code,
    airline_name,
    COUNT(*) AS late_departing_flights,
    ROUND(AVG(dep_delay), 1) AS avg_late_departure_mins,
    ROUND(AVG(arr_delay), 1) AS avg_arrival_delay_mins,
    -- Negative value means net minutes shaved off during cruise
    ROUND(AVG(en_route_delay_delta), 2) AS avg_minutes_recovered_en_route,
    SUM(recovered_to_on_time) AS flights_recovered_to_on_time,
    ROUND(SUM(recovered_to_on_time) * 100.0 / COUNT(*), 2) AS recovery_success_rate_pct
FROM delayed_departures
GROUP BY carrier_code, airline_name
ORDER BY avg_minutes_recovered_en_route ASC;

-- -----------------------------------------------------------------------------
-- Query 3: Carrier Scale vs. Operational Stability
-- Business Question: Does high flight volume inherently result in higher delay variance?
-- -----------------------------------------------------------------------------
SELECT 
    carrier_code,
    airline_name,
    COUNT(*) AS flight_volume,
    ROUND(AVG(arr_delay), 2) AS mean_arr_delay,
    -- Quantify dispersion between scheduled and actual performance
    ROUND(MIN(arr_delay), 1) AS best_arrival_delta,
    ROUND(MAX(arr_delay), 1) AS worst_arrival_delay,
    ROUND(SUM(CASE WHEN arr_delay > 60 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS severe_delay_pct_60m,
    ROUND(SUM(CASE WHEN arr_delay > 0 THEN arr_delay * 74.24 ELSE 0 END) / 1000000.0, 2) AS total_delay_cost_million_usd
FROM v_flights_operational_master
WHERE cancelled = 0 AND diverted = 0
GROUP BY carrier_code, airline_name
ORDER BY flight_volume DESC;

-- -----------------------------------------------------------------------------
-- Query 4: Carrier Cancellation Attribution Matrix
-- Business Question: What primary vulnerabilities trigger cancellations for each airline?
-- -----------------------------------------------------------------------------
SELECT 
    carrier_code,
    airline_name,
    COUNT(*) AS total_cancelled_flights,
    SUM(CASE WHEN cancellation_code = 'A' THEN 1 ELSE 0 END) AS carrier_internal_cancellations,
    SUM(CASE WHEN cancellation_code = 'B' THEN 1 ELSE 0 END) AS weather_cancellations,
    SUM(CASE WHEN cancellation_code = 'C' THEN 1 ELSE 0 END) AS nas_atc_cancellations,
    SUM(CASE WHEN cancellation_code = 'D' THEN 1 ELSE 0 END) AS security_cancellations,
    ROUND(SUM(CASE WHEN cancellation_code = 'A' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_due_to_internal_carrier_issues
FROM v_flights_operational_master
WHERE cancelled = 1
GROUP BY carrier_code, airline_name
ORDER BY total_cancelled_flights DESC;
