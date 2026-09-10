-- ==============================================================================
-- Portfolio Project: Flight Delay Analysis Using SQL
-- File: 01_schema_and_indexes.sql
-- Description: Core Relational DDL, Constraints, Performance Indexes, and Views.
-- Standard: ANSI SQL / SQLite 3+
-- Author: Data Analytics Engineering
-- ==============================================================================

PRAGMA foreign_keys = ON;

-- -----------------------------------------------------------------------------
-- 1. Master Airlines Dimension Table
-- -----------------------------------------------------------------------------
DROP TABLE IF EXISTS flights;
DROP TABLE IF EXISTS airlines;
DROP TABLE IF EXISTS airports;

CREATE TABLE airlines (
    airline_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    carrier_code        TEXT NOT NULL UNIQUE,
    airline_name        TEXT NOT NULL,
    callsign            TEXT,
    fleet_size          INTEGER NOT NULL DEFAULT 0 CHECK (fleet_size >= 0),
    base_reliability    REAL NOT NULL DEFAULT 0.80 CHECK (base_reliability BETWEEN 0.0 AND 1.0),
    country             TEXT NOT NULL DEFAULT 'USA',
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 2. Master Airports Dimension Table
-- -----------------------------------------------------------------------------
CREATE TABLE airports (
    airport_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    iata_code           TEXT NOT NULL UNIQUE,
    icao_code           TEXT NOT NULL UNIQUE,
    airport_name        TEXT NOT NULL,
    city                TEXT NOT NULL,
    state               TEXT NOT NULL,
    country             TEXT NOT NULL DEFAULT 'USA',
    latitude            REAL NOT NULL CHECK (latitude BETWEEN -90.0 AND 90.0),
    longitude           REAL NOT NULL CHECK (longitude BETWEEN -180.0 AND 180.0),
    tz_offset           INTEGER NOT NULL DEFAULT -5,
    congestion_factor   REAL NOT NULL DEFAULT 1.00 CHECK (congestion_factor > 0.0)
);

-- -----------------------------------------------------------------------------
-- 3. Core Flights Fact Table (Granularity: 1 row per scheduled commercial flight)
-- -----------------------------------------------------------------------------
CREATE TABLE flights (
    flight_id           INTEGER PRIMARY KEY,
    flight_date         TEXT NOT NULL,                        -- ISO-8601: YYYY-MM-DD
    carrier_code        TEXT NOT NULL,
    flight_number       INTEGER NOT NULL,
    tail_number         TEXT NOT NULL,
    origin_airport      TEXT NOT NULL,
    dest_airport        TEXT NOT NULL,
    sched_dep_time      TEXT NOT NULL,                        -- Format: HH:MM
    dep_time            TEXT,                                 -- NULL if flight cancelled
    dep_delay           INTEGER NOT NULL DEFAULT 0,           -- Delay in minutes (negative = early)
    taxi_out            INTEGER NOT NULL DEFAULT 0,           -- Pushback to wheels-off (minutes)
    sched_arr_time      TEXT NOT NULL,                        -- Format: HH:MM
    arr_time            TEXT,                                 -- NULL if flight cancelled/diverted
    arr_delay           INTEGER NOT NULL DEFAULT 0,           -- Gate arrival delay in minutes
    cancelled           INTEGER NOT NULL DEFAULT 0 CHECK (cancelled IN (0, 1)),
    cancellation_code   TEXT CHECK (cancellation_code IN ('A', 'B', 'C', 'D') OR cancellation_code IS NULL),
    diverted            INTEGER NOT NULL DEFAULT 0 CHECK (diverted IN (0, 1)),
    distance            INTEGER NOT NULL CHECK (distance > 0),-- Flight distance in statute miles
    air_time            INTEGER NOT NULL DEFAULT 0,           -- Airborne flight duration in minutes
    carrier_delay       INTEGER NOT NULL DEFAULT 0,           -- Minutes attributable to airline operations
    weather_delay       INTEGER NOT NULL DEFAULT 0,           -- Minutes attributable to meteorological conditions
    nas_delay           INTEGER NOT NULL DEFAULT 0,           -- Minutes attributable to National Airspace System
    security_delay      INTEGER NOT NULL DEFAULT 0,           -- Minutes attributable to security breaches/delays
    late_aircraft_delay INTEGER NOT NULL DEFAULT 0,           -- Minutes attributable to previous leg propagation
    
    FOREIGN KEY (carrier_code)   REFERENCES airlines(carrier_code) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (origin_airport) REFERENCES airports(iata_code)    ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (dest_airport)   REFERENCES airports(iata_code)    ON UPDATE CASCADE ON DELETE RESTRICT,
    CHECK (origin_airport <> dest_airport)
);

-- -----------------------------------------------------------------------------
-- 4. High-Performance B-Tree Composite Indexes
-- Designed specifically for accelerating analytical queries & filtering patterns:
-- -----------------------------------------------------------------------------

-- Accelerates Carrier-level monthly and daily trend aggregations
CREATE INDEX idx_flights_carrier_date 
    ON flights (carrier_code, flight_date);

-- Accelerates origin airport departure peak-hour bottlenecks
CREATE INDEX idx_flights_origin_dep 
    ON flights (origin_airport, sched_dep_time);

-- Accelerates destination arrival lookups
CREATE INDEX idx_flights_dest 
    ON flights (dest_airport);

-- Accelerates aircraft rotation analysis (cascading delay tracking via LAG/LEAD)
CREATE INDEX idx_flights_tail_rotation 
    ON flights (tail_number, flight_date, sched_dep_time);

-- Accelerates filter predicates on arrival delays (e.g., WHERE arr_delay >= 15)
CREATE INDEX idx_flights_arr_delay 
    ON flights (arr_delay);

-- Accelerates route pair analysis (Origin-Destination corridor density)
CREATE INDEX idx_flights_corridor 
    ON flights (origin_airport, dest_airport, flight_date);

-- Accelerates cancellation tracking queries
CREATE INDEX idx_flights_cancellations 
    ON flights (cancelled, cancellation_code);

-- -----------------------------------------------------------------------------
-- 5. Analytical Reporting View: Denormalized Operational Flight Master
-- Pre-calculates FAA on-time metrics and airborne delay recovery.
-- -----------------------------------------------------------------------------
DROP VIEW IF EXISTS v_flights_operational_master;

CREATE VIEW v_flights_operational_master AS
SELECT 
    f.flight_id,
    f.flight_date,
    SUBSTR(f.flight_date, 1, 7) AS flight_month,
    f.carrier_code,
    al.airline_name,
    f.flight_number,
    f.tail_number,
    f.origin_airport,
    orig.city AS origin_city,
    orig.state AS origin_state,
    orig.congestion_factor AS origin_congestion,
    f.dest_airport,
    dest.city AS dest_city,
    dest.state AS dest_state,
    f.sched_dep_time,
    SUBSTR(f.sched_dep_time, 1, 2) AS dep_hour_bucket,
    f.dep_time,
    f.dep_delay,
    f.sched_arr_time,
    f.arr_time,
    f.arr_delay,
    -- BTS On-Time Performance definition: arrival delay < 15 minutes
    CASE 
        WHEN f.cancelled = 1 THEN 0
        WHEN f.diverted = 1 THEN 0
        WHEN f.arr_delay < 15 THEN 1 
        ELSE 0 
    END AS is_on_time_otp15,
    -- Flight Delay Indicator (>= 15 mins)
    CASE 
        WHEN f.arr_delay >= 15 AND f.cancelled = 0 AND f.diverted = 0 THEN 1 
        ELSE 0 
    END AS is_delayed_15plus,
    f.cancelled,
    f.cancellation_code,
    CASE f.cancellation_code
        WHEN 'A' THEN 'Carrier Operation'
        WHEN 'B' THEN 'Extreme Weather'
        WHEN 'C' THEN 'National Airspace System'
        WHEN 'D' THEN 'Security'
        ELSE 'Not Cancelled'
    END AS cancellation_reason,
    f.diverted,
    f.distance,
    f.air_time,
    f.taxi_out,
    f.carrier_delay,
    f.weather_delay,
    f.nas_delay,
    f.security_delay,
    f.late_aircraft_delay,
    -- En-route time recovery: difference between arrival delay and departure delay
    -- Negative value means the pilot actively made up time in the air
    (f.arr_delay - f.dep_delay) AS en_route_delay_delta,
    -- FAA benchmark: direct aircraft operating cost at $74.24 per minute of arrival delay
    ROUND(CASE WHEN f.arr_delay > 0 THEN f.arr_delay * 74.24 ELSE 0 END, 2) AS estimated_cost_usd
FROM flights f
INNER JOIN airlines al  ON f.carrier_code = al.carrier_code
INNER JOIN airports orig ON f.origin_airport = orig.iata_code
INNER JOIN airports dest ON f.dest_airport = dest.iata_code;
