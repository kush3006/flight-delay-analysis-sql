-- ==============================================================================
-- Portfolio Project: Flight Delay Analysis Using SQL
-- File: 08_financial_impact_and_roi.sql
-- Description: Economic Valuation, FAA Cost Model Translation & Optimization ROI.
-- Standard: ANSI SQL / SQLite 3+
-- ==============================================================================

-- -----------------------------------------------------------------------------
-- Query 1: Airline Financial Delay Ledger
-- Business Question: What is the direct operating cost and passenger impact of delays by airline?
-- Economic Benchmark: FAA APO-130 / A4A: $74.24/min Direct Aircraft Operating Cost (crew, fuel, maintenance)
-- plus estimated passenger value of time ($35.00/passenger-minute across ~140 passengers per flight).
-- -----------------------------------------------------------------------------
SELECT 
    carrier_code,
    airline_name,
    COUNT(*) AS total_flights,
    SUM(CASE WHEN arr_delay > 0 THEN arr_delay ELSE 0 END) AS total_delay_minutes,
    ROUND(AVG(CASE WHEN arr_delay > 0 THEN arr_delay ELSE 0 END), 1) AS avg_delay_when_delayed_mins,
    -- Direct Aircraft Operating Cost ($74.24 per min)
    ROUND(SUM(CASE WHEN arr_delay > 0 THEN arr_delay * 74.24 ELSE 0 END) / 1000000.0, 2) AS direct_aircraft_cost_million_usd,
    -- Passenger Disutility Cost (~140 pax * $35/hr -> ~$0.58/pax-min -> ~$81.20/flight-min)
    ROUND(SUM(CASE WHEN arr_delay > 0 THEN arr_delay * 81.20 ELSE 0 END) / 1000000.0, 2) AS estimated_passenger_cost_million_usd,
    -- Combined Economic Impact
    ROUND(SUM(CASE WHEN arr_delay > 0 THEN arr_delay * (74.24 + 81.20) ELSE 0 END) / 1000000.0, 2) AS total_economic_impact_million_usd
FROM v_flights_operational_master
GROUP BY carrier_code, airline_name
ORDER BY direct_aircraft_cost_million_usd DESC;

-- -----------------------------------------------------------------------------
-- Query 2: Top 10 High-Loss Flight Corridors
-- Business Question: Which routes bleed the greatest capital due to chronic delays?
-- -----------------------------------------------------------------------------
SELECT 
    origin_airport || ' -> ' || dest_airport AS corridor,
    COUNT(*) AS flight_count,
    ROUND(AVG(arr_delay), 1) AS avg_arr_delay_mins,
    SUM(CASE WHEN arr_delay > 0 THEN arr_delay ELSE 0 END) AS aggregate_delay_minutes,
    ROUND(SUM(CASE WHEN arr_delay > 0 THEN arr_delay * 74.24 ELSE 0 END), 2) AS direct_delay_cost_usd,
    ROUND(SUM(CASE WHEN arr_delay > 0 THEN arr_delay * 74.24 ELSE 0 END) / COUNT(*), 2) AS cost_drag_per_scheduled_flight_usd
FROM v_flights_operational_master
GROUP BY origin_airport, dest_airport
HAVING COUNT(*) >= 100
ORDER BY direct_delay_cost_usd DESC
LIMIT 10;

-- -----------------------------------------------------------------------------
-- Query 3: Simulation: ROI of a 7-Minute Schedule Buffer on High-Risk Routes
-- Business Question: If network planners add a 7-minute buffer into block times for chronic routes,
-- how many flights convert from delayed to on-time, and what is the simulated cost avoidance?
-- -----------------------------------------------------------------------------
WITH buffer_simulation AS (
    SELECT 
        flight_id,
        carrier_code,
        arr_delay,
        is_delayed_15plus,
        -- Simulated arrival delay with 7-minute block padding
        (arr_delay - 7) AS simulated_arr_delay,
        CASE WHEN (arr_delay - 7) < 15 THEN 1 ELSE 0 END AS simulated_on_time,
        CASE WHEN arr_delay >= 15 AND (arr_delay - 7) < 15 THEN 1 ELSE 0 END AS converted_to_on_time
    FROM v_flights_operational_master
    WHERE cancelled = 0 AND diverted = 0
)
SELECT 
    COUNT(*) AS total_evaluated_flights,
    SUM(is_delayed_15plus) AS baseline_delayed_flights,
    ROUND(SUM(is_delayed_15plus) * 100.0 / COUNT(*), 2) AS baseline_delay_rate_pct,
    SUM(converted_to_on_time) AS flights_rescued_to_ontime,
    ROUND(SUM(converted_to_on_time) * 100.0 / SUM(is_delayed_15plus), 2) AS pct_delayed_flights_rescued,
    -- Financial cost avoidance calculation
    ROUND(SUM(CASE WHEN arr_delay >= 15 AND (arr_delay - 7) < 15 THEN 7 * 74.24 ELSE 0 END) / 1000000.0, 2) AS estimated_annual_savings_million_usd
FROM buffer_simulation;

-- -----------------------------------------------------------------------------
-- Query 4: Hub Ground Efficiency: 3-Minute Taxi-Out Reduction Impact
-- Business Question: What is the system-wide annual fuel and operational dollar savings
-- if airport operations streamline gate pushback and reduce taxi-out by 3 minutes at the top 3 congested hubs?
-- -----------------------------------------------------------------------------
SELECT 
    origin_airport,
    origin_city,
    COUNT(*) AS total_departures,
    ROUND(AVG(taxi_out), 1) AS current_avg_taxi_mins,
    -- 3 minutes saved per departure
    COUNT(*) * 3 AS total_taxi_minutes_saved,
    -- Valued at ground idle operating rate: ~$45.00/min (fuel + engine wear)
    ROUND((COUNT(*) * 3 * 45.00) / 1000.0, 1) AS estimated_fuel_and_ops_savings_thousand_usd
FROM v_flights_operational_master
WHERE origin_airport IN ('ORD', 'JFK', 'EWR', 'SFO', 'LAX')
  AND cancelled = 0
GROUP BY origin_airport, origin_city
ORDER BY estimated_fuel_and_ops_savings_thousand_usd DESC;
