-- ==============================================================================
-- Portfolio Project: Flight Delay Analysis Using SQL
-- File: 05_hub_and_route_bottlenecks.sql
-- Description: Airport Hub Congestion, Corridor Risk Index, and Taxi-Out Bottlenecks.
-- Standard: ANSI SQL / SQLite 3+
-- ==============================================================================

-- -----------------------------------------------------------------------------
-- Query 1: Top 10 Congested Origin Hubs
-- Business Question: Which departure airports impose the most severe operational friction?
-- -----------------------------------------------------------------------------
SELECT 
    origin_airport,
    origin_city,
    origin_state,
    origin_congestion,
    COUNT(*) AS departing_flights,
    ROUND(AVG(dep_delay), 2) AS avg_dep_delay_mins,
    ROUND(AVG(taxi_out), 2) AS avg_taxi_out_mins,
    ROUND(SUM(is_on_time_otp15) * 100.0 / SUM(CASE WHEN cancelled = 0 AND diverted = 0 THEN 1 ELSE 0 END), 2) AS outbound_otp15_pct,
    ROUND(SUM(cancelled) * 100.0 / COUNT(*), 2) AS outbound_cancellation_pct
FROM v_flights_operational_master
GROUP BY origin_airport, origin_city, origin_state, origin_congestion
ORDER BY avg_dep_delay_mins DESC
LIMIT 10;

-- -----------------------------------------------------------------------------
-- Query 2: Hub Asymmetry: Inbound vs. Outbound Operational Imbalance
-- Business Question: Are specific hubs more vulnerable to inbound arrival delays or outbound departure logjams?
-- -----------------------------------------------------------------------------
WITH outbound_stats AS (
    SELECT 
        origin_airport AS airport_code,
        COUNT(*) AS outbound_flights,
        ROUND(AVG(dep_delay), 2) AS avg_outbound_dep_delay,
        ROUND(AVG(taxi_out), 2) AS avg_taxi_out
    FROM flights
    WHERE cancelled = 0
    GROUP BY origin_airport
),
inbound_stats AS (
    SELECT 
        dest_airport AS airport_code,
        COUNT(*) AS inbound_flights,
        ROUND(AVG(arr_delay), 2) AS avg_inbound_arr_delay
    FROM flights
    WHERE cancelled = 0 AND diverted = 0
    GROUP BY dest_airport
)
SELECT 
    o.airport_code,
    a.airport_name,
    a.city,
    o.outbound_flights,
    o.avg_outbound_dep_delay,
    o.avg_taxi_out,
    i.avg_inbound_arr_delay,
    -- Net Asymmetry: positive means departure operations cause more delay than arrival flow
    ROUND(o.avg_outbound_dep_delay - i.avg_inbound_arr_delay, 2) AS outbound_net_delay_delta
FROM outbound_stats o
INNER JOIN inbound_stats i ON o.airport_code = i.airport_code
INNER JOIN airports a      ON o.airport_code = a.iata_code
ORDER BY outbound_net_delay_delta DESC
LIMIT 15;

-- -----------------------------------------------------------------------------
-- Query 3: Most Vulnerable Flight Corridors (Origin-Destination Route Pairs)
-- Business Question: Which specific city pairs experience the greatest frequency and magnitude of delays?
-- -----------------------------------------------------------------------------
WITH route_aggregates AS (
    SELECT 
        origin_airport,
        dest_airport,
        COUNT(*) AS flight_count,
        ROUND(AVG(distance), 0) AS route_distance_miles,
        ROUND(AVG(dep_delay), 2) AS avg_dep_delay,
        ROUND(AVG(arr_delay), 2) AS avg_arr_delay,
        ROUND(SUM(is_delayed_15plus) * 100.0 / COUNT(*), 1) AS delay_frequency_pct,
        ROUND(SUM(cancelled) * 100.0 / COUNT(*), 1) AS cancellation_pct
    FROM v_flights_operational_master
    GROUP BY origin_airport, dest_airport
    HAVING COUNT(*) >= 100 -- Focus on statistically meaningful high-density routes
)
SELECT 
    origin_airport || ' -> ' || dest_airport AS flight_corridor,
    flight_count,
    route_distance_miles,
    avg_dep_delay,
    avg_arr_delay,
    delay_frequency_pct,
    cancellation_pct,
    -- Composite Risk Score: Weighted formula reflecting severity and probability of disruption
    ROUND((avg_arr_delay * 0.6) + (delay_frequency_pct * 0.4), 2) AS corridor_risk_index
FROM route_aggregates
ORDER BY corridor_risk_index DESC
LIMIT 15;

-- -----------------------------------------------------------------------------
-- Query 4: Ground Idling & Fuel Consumption Proxy (Excess Taxi-Out Analysis)
-- Business Question: Assuming standard nominal taxi-out baseline is 15 minutes, which airports
-- generate the highest aggregate excess taxi time (a direct proxy for fuel burn and carbon emissions)?
-- -----------------------------------------------------------------------------
SELECT 
    origin_airport,
    origin_city,
    COUNT(*) AS total_departures,
    ROUND(AVG(taxi_out), 1) AS avg_taxi_out_mins,
    SUM(CASE WHEN taxi_out > 15 THEN taxi_out - 15 ELSE 0 END) AS total_excess_taxi_minutes,
    -- Fuel burn proxy: commercial jet averages ~25 lbs of fuel per minute during taxi
    ROUND(SUM(CASE WHEN taxi_out > 15 THEN taxi_out - 15 ELSE 0 END) * 25.0 / 2000.0, 1) AS est_excess_fuel_tons
FROM v_flights_operational_master
WHERE cancelled = 0
GROUP BY origin_airport, origin_city
ORDER BY total_excess_taxi_minutes DESC
LIMIT 10;
