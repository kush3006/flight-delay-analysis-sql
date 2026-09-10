-- ==============================================================================
-- Portfolio Project: Flight Delay Analysis Using SQL
-- File: 07_advanced_window_functions.sql
-- Description: Advanced Window Functions (Rolling Averages, LAG/LEAD Propagation, NTILE).
-- Standard: ANSI SQL / SQLite 3+
-- ==============================================================================

-- -----------------------------------------------------------------------------
-- Query 1: Rolling 7-Day Moving Average of Punctuality by Carrier
-- Business Question: Smooth out daily noise to track systemic operational trends per carrier.
-- -----------------------------------------------------------------------------
WITH daily_carrier_metrics AS (
    SELECT 
        carrier_code,
        flight_date,
        COUNT(*) AS daily_flights,
        ROUND(AVG(arr_delay), 2) AS avg_daily_arr_delay,
        ROUND(SUM(is_on_time_otp15) * 100.0 / COUNT(*), 2) AS daily_otp15_pct
    FROM v_flights_operational_master
    WHERE cancelled = 0 AND diverted = 0
    GROUP BY carrier_code, flight_date
)
SELECT 
    carrier_code,
    flight_date,
    daily_flights,
    avg_daily_arr_delay,
    daily_otp15_pct,
    -- 7-Day Rolling Moving Average of OTP-15
    ROUND(AVG(daily_otp15_pct) OVER (
        PARTITION BY carrier_code 
        ORDER BY flight_date 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2) AS rolling_7d_otp15_pct,
    -- 7-Day Rolling Moving Average of Arrival Delay
    ROUND(AVG(avg_daily_arr_delay) OVER (
        PARTITION BY carrier_code 
        ORDER BY flight_date 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2) AS rolling_7d_avg_delay_mins
FROM daily_carrier_metrics
WHERE carrier_code IN ('DL', 'AA', 'UA', 'WN')
ORDER BY carrier_code, flight_date DESC
LIMIT 40;

-- -----------------------------------------------------------------------------
-- Query 2: Aircraft Leg-to-Leg Turnaround Delay Propagation (LAG Analysis)
-- Business Question: How does a delay on Leg N directly impact departure punctuality on Leg N+1 for the same physical aircraft?
-- -----------------------------------------------------------------------------
WITH aircraft_flight_sequence AS (
    SELECT 
        tail_number,
        flight_date,
        carrier_code,
        flight_number,
        origin_airport,
        dest_airport,
        sched_dep_time,
        dep_delay,
        arr_delay,
        -- Prior Leg metrics using LAG window function
        LAG(dest_airport) OVER (
            PARTITION BY tail_number, flight_date 
            ORDER BY sched_dep_time
        ) AS prior_arrival_airport,
        LAG(arr_delay) OVER (
            PARTITION BY tail_number, flight_date 
            ORDER BY sched_dep_time
        ) AS prior_leg_arrival_delay,
        ROW_NUMBER() OVER (
            PARTITION BY tail_number, flight_date 
            ORDER BY sched_dep_time
        ) AS daily_leg_number
    FROM flights
    WHERE cancelled = 0
)
SELECT 
    tail_number,
    flight_date,
    daily_leg_number,
    carrier_code,
    origin_airport,
    dest_airport,
    prior_leg_arrival_delay,
    dep_delay AS current_leg_dep_delay,
    -- Turnaround Absorption / Amplification
    CASE 
        WHEN prior_leg_arrival_delay IS NULL THEN 'First Leg of Day'
        WHEN prior_leg_arrival_delay > 15 AND dep_delay <= prior_leg_arrival_delay THEN 'Delay Absorbed During Ground Turn'
        WHEN prior_leg_arrival_delay > 15 AND dep_delay > prior_leg_arrival_delay THEN 'Delay Cascaded & Amplified'
        ELSE 'On-Schedule Turnaround'
    END AS turnaround_operational_status
FROM aircraft_flight_sequence
WHERE prior_leg_arrival_delay > 20
ORDER BY flight_date DESC, tail_number, daily_leg_number
LIMIT 25;

-- -----------------------------------------------------------------------------
-- Query 3: Delay Quartile Segmentation (NTILE) by Flight Distance
-- Business Question: Partition flights into 4 statistical delay cohorts to isolate extreme systemic tail risk.
-- -----------------------------------------------------------------------------
WITH flight_quartiles AS (
    SELECT 
        flight_id,
        carrier_code,
        origin_airport,
        dest_airport,
        distance,
        arr_delay,
        NTILE(4) OVER (ORDER BY arr_delay) AS delay_quartile
    FROM flights
    WHERE cancelled = 0 AND diverted = 0
)
SELECT 
    delay_quartile,
    CASE delay_quartile
        WHEN 1 THEN 'Q1: Highly Punctual / Early'
        WHEN 2 THEN 'Q2: Nominal On-Time Range'
        WHEN 3 THEN 'Q3: Moderate Delays'
        WHEN 4 THEN 'Q4: Severe Disruption Outliers'
    END AS quartile_label,
    COUNT(*) AS flights_in_cohort,
    ROUND(MIN(arr_delay), 1) AS min_delay_mins,
    ROUND(MAX(arr_delay), 1) AS max_delay_mins,
    ROUND(AVG(arr_delay), 1) AS avg_delay_mins,
    ROUND(AVG(distance), 0) AS avg_distance_miles
FROM flight_quartiles
GROUP BY delay_quartile
ORDER BY delay_quartile ASC;

-- -----------------------------------------------------------------------------
-- Query 4: Cumulative Running Total of System Delay Cost (UNBOUNDED PRECEDING)
-- Business Question: Track year-to-date financial cost accumulation day by day.
-- -----------------------------------------------------------------------------
WITH daily_financials AS (
    SELECT 
        flight_date,
        SUM(CASE WHEN arr_delay > 0 THEN arr_delay * 74.24 ELSE 0 END) AS daily_delay_cost_usd
    FROM flights
    WHERE cancelled = 0 AND diverted = 0
    GROUP BY flight_date
)
SELECT 
    flight_date,
    ROUND(daily_delay_cost_usd, 2) AS daily_cost_usd,
    -- Running Total Window Function
    ROUND(SUM(daily_delay_cost_usd) OVER (
        ORDER BY flight_date 
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) / 1000000.0, 2) AS ytd_cumulative_cost_million_usd
FROM daily_financials
ORDER BY flight_date ASC
LIMIT 30;

-- -----------------------------------------------------------------------------
-- Query 5: Peak Outlier Incident Identification (ROW_NUMBER per Airline)
-- Business Question: Identify the single most severe operational disruption event for each airline.
-- -----------------------------------------------------------------------------
WITH ranked_disruptions AS (
    SELECT 
        carrier_code,
        flight_date,
        flight_number,
        origin_airport,
        dest_airport,
        dep_delay,
        arr_delay,
        weather_delay,
        nas_delay,
        late_aircraft_delay,
        ROW_NUMBER() OVER (PARTITION BY carrier_code ORDER BY arr_delay DESC) AS severity_rank
    FROM flights
    WHERE cancelled = 0 AND diverted = 0
)
SELECT 
    r.carrier_code,
    al.airline_name,
    r.flight_date,
    r.flight_number,
    r.origin_airport || ' -> ' || r.dest_airport AS route,
    r.arr_delay AS worst_arrival_delay_mins,
    r.weather_delay,
    r.nas_delay,
    r.late_aircraft_delay
FROM ranked_disruptions r
INNER JOIN airlines al ON r.carrier_code = al.carrier_code
WHERE r.severity_rank = 1
ORDER BY worst_arrival_delay_mins DESC;
