"""
Realistic Flight Data Generator for SQL Analytics Portfolio.
Simulates Bureau of Transportation Statistics (BTS) / FAA On-Time Performance data.
Generates realistic distributions: log-normal delay tails, hub congestion,
cascading afternoon delays, seasonal weather spikes, and exact delay cause decomposition.
"""

import argparse
from datetime import datetime, timedelta
import math
from pathlib import Path
import random
import sys
import numpy as np
import pandas as pd

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import RAW_DATA_DIR

# ---------------------------------------------------------
# Reference Master Data
# ---------------------------------------------------------

AIRLINES_DATA = [
    {"carrier_code": "DL", "airline_name": "Delta Air Lines", "callsign": "DELTA", "fleet_size": 980, "base_reliability": 0.84},
    {"carrier_code": "AA", "airline_name": "American Airlines", "callsign": "AMERICAN", "fleet_size": 965, "base_reliability": 0.80},
    {"carrier_code": "UA", "airline_name": "United Airlines", "callsign": "UNITED", "fleet_size": 940, "base_reliability": 0.81},
    {"carrier_code": "WN", "airline_name": "Southwest Airlines", "callsign": "SOUTHWEST", "fleet_size": 820, "base_reliability": 0.78},
    {"carrier_code": "AS", "airline_name": "Alaska Airlines", "callsign": "ALASKA", "fleet_size": 315, "base_reliability": 0.83},
    {"carrier_code": "B6", "airline_name": "JetBlue Airways", "callsign": "JETBLUE", "fleet_size": 290, "base_reliability": 0.74},
    {"carrier_code": "NK", "airline_name": "Spirit Airlines", "callsign": "SPIRIT WINGS", "fleet_size": 210, "base_reliability": 0.73},
    {"carrier_code": "F9", "airline_name": "Frontier Airlines", "callsign": "FRONTIER FLIGHT", "fleet_size": 140, "base_reliability": 0.72},
    {"carrier_code": "G4", "airline_name": "Allegiant Air", "callsign": "ALLEGIANT", "fleet_size": 130, "base_reliability": 0.75},
    {"carrier_code": "HA", "airline_name": "Hawaiian Airlines", "callsign": "HAWAIIAN", "fleet_size": 65, "base_reliability": 0.87},
    {"carrier_code": "OO", "airline_name": "SkyWest Airlines", "callsign": "SKYWEST", "fleet_size": 520, "base_reliability": 0.81},
    {"carrier_code": "MQ", "airline_name": "Envoy Air", "callsign": "ENVOY", "fleet_size": 130, "base_reliability": 0.79},
]

AIRPORTS_DATA = [
    {"iata_code": "ATL", "icao_code": "KATL", "airport_name": "Hartsfield-Jackson Atlanta International", "city": "Atlanta", "state": "GA", "latitude": 33.6407, "longitude": -84.4277, "tz_offset": -5, "congestion_factor": 1.25},
    {"iata_code": "ORD", "icao_code": "KORD", "airport_name": "O'Hare International Airport", "city": "Chicago", "state": "IL", "latitude": 41.9742, "longitude": -87.9073, "tz_offset": -6, "congestion_factor": 1.38},
    {"iata_code": "DFW", "icao_code": "KDFW", "airport_name": "Dallas/Fort Worth International", "city": "Dallas", "state": "TX", "latitude": 32.8998, "longitude": -97.0403, "tz_offset": -6, "congestion_factor": 1.28},
    {"iata_code": "DEN", "icao_code": "KDEN", "airport_name": "Denver International Airport", "city": "Denver", "state": "CO", "latitude": 39.8561, "longitude": -104.6737, "tz_offset": -7, "congestion_factor": 1.22},
    {"iata_code": "CLT", "icao_code": "KCLT", "airport_name": "Charlotte Douglas International", "city": "Charlotte", "state": "NC", "latitude": 35.2144, "longitude": -80.9473, "tz_offset": -5, "congestion_factor": 1.15},
    {"iata_code": "LAX", "icao_code": "KLAX", "airport_name": "Los Angeles International", "city": "Los Angeles", "state": "CA", "latitude": 33.9416, "longitude": -118.4085, "tz_offset": -8, "congestion_factor": 1.30},
    {"iata_code": "LAS", "icao_code": "KLAS", "airport_name": "Harry Reid International Airport", "city": "Las Vegas", "state": "NV", "latitude": 36.0840, "longitude": -115.1537, "tz_offset": -8, "congestion_factor": 1.12},
    {"iata_code": "PHX", "icao_code": "KPHX", "airport_name": "Phoenix Sky Harbor International", "city": "Phoenix", "state": "AZ", "latitude": 33.4373, "longitude": -112.0078, "tz_offset": -7, "congestion_factor": 1.10},
    {"iata_code": "MCO", "icao_code": "KMCO", "airport_name": "Orlando International Airport", "city": "Orlando", "state": "FL", "latitude": 28.4312, "longitude": -81.3081, "tz_offset": -5, "congestion_factor": 1.20},
    {"iata_code": "SEA", "icao_code": "KSEA", "airport_name": "Seattle-Tacoma International", "city": "Seattle", "state": "WA", "latitude": 47.4502, "longitude": -122.3088, "tz_offset": -8, "congestion_factor": 1.18},
    {"iata_code": "MIA", "icao_code": "KMIA", "airport_name": "Miami International Airport", "city": "Miami", "state": "FL", "latitude": 25.7959, "longitude": -80.2870, "tz_offset": -5, "congestion_factor": 1.22},
    {"iata_code": "IAH", "icao_code": "KIAH", "airport_name": "George Bush Intercontinental", "city": "Houston", "state": "TX", "latitude": 29.9902, "longitude": -95.3368, "tz_offset": -6, "congestion_factor": 1.20},
    {"iata_code": "JFK", "icao_code": "KJFK", "airport_name": "John F. Kennedy International", "city": "New York", "state": "NY", "latitude": 40.6413, "longitude": -73.7781, "tz_offset": -5, "congestion_factor": 1.42},
    {"iata_code": "EWR", "icao_code": "KEWR", "airport_name": "Newark Liberty International", "city": "Newark", "state": "NJ", "latitude": 40.6895, "longitude": -74.1745, "tz_offset": -5, "congestion_factor": 1.45},
    {"iata_code": "SFO", "icao_code": "KSFO", "airport_name": "San Francisco International", "city": "San Francisco", "state": "CA", "latitude": 37.6213, "longitude": -122.3790, "tz_offset": -8, "congestion_factor": 1.40},
    {"iata_code": "BOS", "icao_code": "KBOS", "airport_name": "Logan International Airport", "city": "Boston", "state": "MA", "latitude": 42.3656, "longitude": -71.0096, "tz_offset": -5, "congestion_factor": 1.26},
    {"iata_code": "MSP", "icao_code": "KMSP", "airport_name": "Minneapolis-Saint Paul International", "city": "Minneapolis", "state": "MN", "latitude": 44.8848, "longitude": -93.2223, "tz_offset": -6, "congestion_factor": 1.16},
    {"iata_code": "DTW", "icao_code": "KDTW", "airport_name": "Detroit Metropolitan Airport", "city": "Detroit", "state": "MI", "latitude": 42.2162, "longitude": -83.3554, "tz_offset": -5, "congestion_factor": 1.14},
    {"iata_code": "FLL", "icao_code": "KFLL", "airport_name": "Fort Lauderdale-Hollywood International", "city": "Fort Lauderdale", "state": "FL", "latitude": 26.0742, "longitude": -80.1506, "tz_offset": -5, "congestion_factor": 1.21},
    {"iata_code": "PHL", "icao_code": "KPHL", "airport_name": "Philadelphia International Airport", "city": "Philadelphia", "state": "PA", "latitude": 39.8729, "longitude": -75.2437, "tz_offset": -5, "congestion_factor": 1.24},
    {"iata_code": "BWI", "icao_code": "KBWI", "airport_name": "Baltimore/Washington International", "city": "Baltimore", "state": "MD", "latitude": 39.1774, "longitude": -76.6684, "tz_offset": -5, "congestion_factor": 1.15},
    {"iata_code": "SLC", "icao_code": "KSLC", "airport_name": "Salt Lake City International", "city": "Salt Lake City", "state": "UT", "latitude": 40.7899, "longitude": -111.9791, "tz_offset": -7, "congestion_factor": 1.05},
    {"iata_code": "SAN", "icao_code": "KSAN", "airport_name": "San Diego International Airport", "city": "San Diego", "state": "CA", "latitude": 32.7338, "longitude": -117.1933, "tz_offset": -8, "congestion_factor": 1.12},
    {"iata_code": "IAD", "icao_code": "KIAD", "airport_name": "Washington Dulles International", "city": "Washington", "state": "DC", "latitude": 38.9531, "longitude": -77.4565, "tz_offset": -5, "congestion_factor": 1.18},
    {"iata_code": "TPA", "icao_code": "KTPA", "airport_name": "Tampa International Airport", "city": "Tampa", "state": "FL", "latitude": 27.9755, "longitude": -82.5332, "tz_offset": -5, "congestion_factor": 1.10},
    {"iata_code": "MDW", "icao_code": "KMDW", "airport_name": "Chicago Midway International", "city": "Chicago", "state": "IL", "latitude": 41.7868, "longitude": -87.7522, "tz_offset": -6, "congestion_factor": 1.22},
    {"iata_code": "BNA", "icao_code": "KBNA", "airport_name": "Nashville International Airport", "city": "Nashville", "state": "TN", "latitude": 36.1263, "longitude": -86.6774, "tz_offset": -6, "congestion_factor": 1.16},
    {"iata_code": "AUS", "icao_code": "KAUS", "airport_name": "Austin-Bergstrom International", "city": "Austin", "state": "TX", "latitude": 30.1975, "longitude": -97.6664, "tz_offset": -6, "congestion_factor": 1.14},
    {"iata_code": "DAL", "icao_code": "KDAL", "airport_name": "Dallas Love Field", "city": "Dallas", "state": "TX", "latitude": 32.8481, "longitude": -96.8512, "tz_offset": -6, "congestion_factor": 1.15},
    {"iata_code": "PDX", "icao_code": "KPDX", "airport_name": "Portland International Airport", "city": "Portland", "state": "OR", "latitude": 45.5898, "longitude": -122.5951, "tz_offset": -8, "congestion_factor": 1.08},
]


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """Calculates approximate great-circle distance between two airport coordinates in miles."""
    r = 3958.8  # Earth radius in miles
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return int(round(r * c))


def precompute_airport_distances():
    """Builds a lookup table of airport-to-airport distances."""
    coords = {a["iata_code"]: (a["latitude"], a["longitude"]) for a in AIRPORTS_DATA}
    dist_map = {}
    for code1, (lat1, lon1) in coords.items():
        for code2, (lat2, lon2) in coords.items():
            if code1 != code2:
                dist_map[(code1, code2)] = max(120, haversine_distance(lat1, lon1, lat2, lon2))
    return dist_map


def format_minutes_to_time(minutes_from_midnight: int) -> str:
    """Converts minute offset (0..1439) to HH:MM format."""
    normalized = minutes_from_midnight % 1440
    hours = normalized // 60
    mins = normalized % 60
    return f"{hours:02d}:{mins:02d}"


def generate_flight_dataset(num_records: int = 100000, seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Generates realistic flight data with statistical integrity.
    
    Args:
        num_records (int): Target number of flight records (default 100,000).
        seed (int): Deterministic random seed.
        
    Returns:
        tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]: (df_airlines, df_airports, df_flights)
    """
    print(f"[+] Initializing data generation with seed={seed}, target_records={num_records:,}...")
    np.random.seed(seed)
    random.seed(seed)

    # 1. Master DataFrames
    df_airlines = pd.DataFrame(AIRLINES_DATA)
    df_airlines.insert(0, "airline_id", range(1, len(df_airlines) + 1))
    df_airlines["country"] = "USA"

    df_airports = pd.DataFrame(AIRPORTS_DATA)
    df_airports.insert(0, "airport_id", range(1, len(df_airports) + 1))
    df_airports["country"] = "USA"

    dist_map = precompute_airport_distances()
    airport_codes = [a["iata_code"] for a in AIRPORTS_DATA]
    airport_weights = np.array([a["congestion_factor"] for a in AIRPORTS_DATA])
    airport_weights /= airport_weights.sum()

    carrier_codes = [c["carrier_code"] for c in AIRLINES_DATA]
    carrier_probs = np.array([c["fleet_size"] for c in AIRLINES_DATA], dtype=float)
    carrier_probs /= carrier_probs.sum()

    reliability_map = {c["carrier_code"]: c["base_reliability"] for c in AIRLINES_DATA}
    congestion_map = {a["iata_code"]: a["congestion_factor"] for a in AIRPORTS_DATA}

    # Generate Tail Number Pool per Airline
    tail_pool = {}
    for c in AIRLINES_DATA:
        code = c["carrier_code"]
        num_tails = min(c["fleet_size"], 120)
        tail_pool[code] = [f"N{100 + i}{code}" for i in range(num_tails)]

    # 2. Vectorized Generation Setup
    print("[-] Generating flight temporal and route schedules...")
    start_date = datetime(2024, 1, 1)
    date_offsets = np.random.randint(0, 366, size=num_records)
    flight_dates = [start_date + timedelta(days=int(d)) for d in date_offsets]
    flight_dates_str = [d.strftime("%Y-%m-%d") for d in flight_dates]
    months = np.array([d.month for d in flight_dates])

    carriers = np.random.choice(carrier_codes, size=num_records, p=carrier_probs)
    origins = np.random.choice(airport_codes, size=num_records, p=airport_weights)
    
    # Destination must not equal origin
    dests = np.random.choice(airport_codes, size=num_records, p=airport_weights)
    for i in range(num_records):
        while dests[i] == origins[i]:
            dests[i] = random.choice(airport_codes)

    # Flight numbers and tail numbers
    flight_numbers = np.random.randint(100, 5999, size=num_records)
    tail_numbers = [random.choice(tail_pool[carrier]) for carrier in carriers]

    # Departure time distribution (peaks around 07:00-09:00 and 16:00-19:00)
    # Mixture distribution for departure hour
    hour_distribution = [
        0.005, 0.005, 0.005, 0.010, 0.020, 0.045, # 00:00 - 05:00
        0.080, 0.085, 0.075, 0.065, 0.060, 0.055, # 06:00 - 11:00
        0.055, 0.050, 0.050, 0.055, 0.070, 0.075, # 12:00 - 17:00
        0.070, 0.055, 0.040, 0.025, 0.015, 0.005  # 18:00 - 23:00
    ]
    hour_distribution = np.array(hour_distribution) / sum(hour_distribution)
    sched_dep_hours = np.random.choice(24, size=num_records, p=hour_distribution)
    sched_dep_minutes = np.random.choice([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55], size=num_records)
    sched_dep_mins_from_midnight = sched_dep_hours * 60 + sched_dep_minutes

    print("[-] Computing distances, air times, and scheduled flight windows...")
    distances = np.array([dist_map[(origins[i], dests[i])] for i in range(num_records)])
    # Air time roughly 450 mph + 25 min climb/descend
    sched_air_times = np.round((distances / 460.0) * 60 + 22).astype(int)
    sched_taxi_out = np.random.randint(12, 22, size=num_records)
    sched_taxi_in = np.random.randint(5, 12, size=num_records)
    sched_elapsed_times = sched_taxi_out + sched_air_times + sched_taxi_in
    sched_arr_mins_from_midnight = (sched_dep_mins_from_midnight + sched_elapsed_times) % 1440

    # 3. Simulate Delays, Cancellations & Root Causes
    print("[-] Simulating realistic delay causes, cancellations, and operational recovery...")
    cancelled = np.zeros(num_records, dtype=int)
    cancellation_codes = [None] * num_records
    diverted = np.zeros(num_records, dtype=int)

    dep_delays = np.zeros(num_records, dtype=int)
    arr_delays = np.zeros(num_records, dtype=int)
    actual_taxi_outs = np.zeros(num_records, dtype=int)
    actual_taxi_ins = np.zeros(num_records, dtype=int)
    actual_air_times = np.zeros(num_records, dtype=int)

    carrier_delays = np.zeros(num_records, dtype=int)
    weather_delays = np.zeros(num_records, dtype=int)
    nas_delays = np.zeros(num_records, dtype=int)
    security_delays = np.zeros(num_records, dtype=int)
    late_aircraft_delays = np.zeros(num_records, dtype=int)

    # Weather seasonality multiplier (spikes in Jan-Feb winter storms and Jul-Aug summer storms)
    weather_season_factor = {
        1: 1.45, 2: 1.40, 3: 1.10, 4: 0.90, 5: 0.95, 6: 1.15,
        7: 1.25, 8: 1.20, 9: 0.85, 10: 0.80, 11: 1.05, 12: 1.35
    }

    # Simulation loop
    for i in range(num_records):
        carrier = carriers[i]
        orig = origins[i]
        hour = sched_dep_hours[i]
        month = months[i]

        base_rel = reliability_map[carrier]
        orig_cong = congestion_map[orig]
        w_factor = weather_season_factor[month]

        # Probability of cancellation: ~1.4% overall
        cancel_prob = 0.012 * (orig_cong / 1.1) * w_factor
        if np.random.random() < cancel_prob:
            cancelled[i] = 1
            # Cancellation reason breakdown: Weather 50%, Carrier 32%, NAS 17%, Security 1%
            cancellation_codes[i] = np.random.choice(["B", "A", "C", "D"], p=[0.50, 0.32, 0.17, 0.01])
            continue

        # Probability of diversion: ~0.2%
        if np.random.random() < 0.002:
            diverted[i] = 1

        # Cascading effect: afternoon & evening flights have higher delay probability due to aircraft rotation
        time_penalty = 1.0 + (max(0, hour - 10) * 0.035)  # escalates up to 1.45x by 22:00
        delay_probability = (1.0 - base_rel) * (orig_cong / 1.15) * time_penalty

        # Determine Departure Delay
        if np.random.random() < delay_probability:
            # Right-skewed delay distribution (log-normal)
            # Most delays are 15-45 mins; few reach 120-300+ mins
            raw_delay = int(np.random.lognormal(mean=3.2, sigma=0.75))
            dep_delay = max(5, min(raw_delay, 480))
        else:
            # On-time or early departure (-10 to +4 mins)
            dep_delay = int(np.random.normal(loc=-2, scale=3))
            dep_delay = max(-15, min(dep_delay, 12))

        dep_delays[i] = dep_delay

        # Taxi-out delay influenced by airport congestion factor
        taxi_out = int(sched_taxi_out[i] * (orig_cong ** 0.8) + np.random.normal(0, 3))
        taxi_out = max(8, taxi_out)
        actual_taxi_outs[i] = taxi_out

        # En-route air time and airborne delay recovery
        # Pilots often throttle up to recover 2 to 8 mins of delay on long flights
        distance = distances[i]
        air_time = sched_air_times[i] + int(np.random.normal(0, 4))
        if dep_delay > 15 and distance > 800:
            makeup = min(12, int(dep_delay * 0.15) + np.random.randint(1, 5))
            air_time -= makeup
        air_time = max(35, air_time)
        actual_air_times[i] = air_time

        # Taxi-in
        taxi_in = max(3, int(sched_taxi_in[i] + np.random.normal(0, 2)))
        actual_taxi_ins[i] = taxi_in

        # Total Arrival Delay = Departure Delay + (Actual Elapsed - Scheduled Elapsed)
        actual_elapsed = taxi_out + air_time + taxi_in
        sched_elapsed = sched_elapsed_times[i]
        arr_delay = dep_delay + (actual_elapsed - sched_elapsed)
        arr_delays[i] = arr_delay

        # Delay Cause Attribution (BTS Rule: only populated when arr_delay >= 15)
        if arr_delay >= 15 and cancelled[i] == 0 and diverted[i] == 0:
            remaining_delay = arr_delay

            # If departure occurred after 15:00 and dep_delay was significant, Late Aircraft is often dominant
            if hour >= 14 and dep_delay >= 20:
                p_late = 0.42
                p_carrier = 0.26
                p_nas = 0.18
                p_weather = 0.13
                p_sec = 0.01
            else:
                p_late = 0.18
                p_carrier = 0.40
                p_nas = 0.24
                p_weather = 0.17
                p_sec = 0.01

            # Distribute delay among categories such that their sum EXACTLY equals arr_delay
            draws = np.random.dirichlet([p_carrier * 5, p_weather * 5, p_nas * 5, p_sec * 5, p_late * 5])
            allocated = np.floor(draws * remaining_delay).astype(int)
            remainder = remaining_delay - int(allocated.sum())
            for k in range(remainder):
                allocated[k % 5] += 1

            carrier_delays[i] = int(allocated[0])
            weather_delays[i] = int(allocated[1])
            nas_delays[i] = int(allocated[2])
            security_delays[i] = int(allocated[3])
            late_aircraft_delays[i] = int(allocated[4])

    print("[-] Formatting timestamps and building final flights DataFrame...")
    # Calculate clock HH:MM
    sched_dep_formatted = [format_minutes_to_time(m) for m in sched_dep_mins_from_midnight]
    sched_arr_formatted = [format_minutes_to_time(m) for m in sched_arr_mins_from_midnight]

    actual_dep_formatted = [
        format_minutes_to_time(sched_dep_mins_from_midnight[i] + dep_delays[i]) if cancelled[i] == 0 else None
        for i in range(num_records)
    ]
    actual_arr_formatted = [
        format_minutes_to_time(sched_arr_mins_from_midnight[i] + arr_delays[i]) if (cancelled[i] == 0 and diverted[i] == 0) else None
        for i in range(num_records)
    ]

    df_flights = pd.DataFrame({
        "flight_id": range(1, num_records + 1),
        "flight_date": flight_dates_str,
        "carrier_code": carriers,
        "flight_number": flight_numbers,
        "tail_number": tail_numbers,
        "origin_airport": origins,
        "dest_airport": dests,
        "sched_dep_time": sched_dep_formatted,
        "dep_time": actual_dep_formatted,
        "dep_delay": dep_delays,
        "taxi_out": actual_taxi_outs,
        "sched_arr_time": sched_arr_formatted,
        "arr_time": actual_arr_formatted,
        "arr_delay": arr_delays,
        "cancelled": cancelled,
        "cancellation_code": cancellation_codes,
        "diverted": diverted,
        "distance": distances,
        "air_time": actual_air_times,
        "carrier_delay": carrier_delays,
        "weather_delay": weather_delays,
        "nas_delay": nas_delays,
        "security_delay": security_delays,
        "late_aircraft_delay": late_aircraft_delays,
    })

    return df_airlines, df_airports, df_flights


def save_datasets(num_records: int = 100000, seed: int = 42) -> None:
    """Generates and exports raw CSV files."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    df_airlines, df_airports, df_flights = generate_flight_dataset(num_records=num_records, seed=seed)

    airlines_path = RAW_DATA_DIR / "airlines.csv"
    airports_path = RAW_DATA_DIR / "airports.csv"
    flights_path = RAW_DATA_DIR / "flights.csv"

    print(f"[+] Exporting master airlines table to: {airlines_path.name} ({len(df_airlines)} rows)")
    df_airlines.to_csv(airlines_path, index=False)

    print(f"[+] Exporting master airports table to: {airports_path.name} ({len(df_airports)} rows)")
    df_airports.to_csv(airports_path, index=False)

    print(f"[+] Exporting flights table to: {flights_path.name} ({len(df_flights):,} rows)...")
    df_flights.to_csv(flights_path, index=False)
    print("[OK] Raw CSV generation successfully completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate realistic flight dataset for SQL analytics.")
    parser.add_argument("--records", type=int, default=100000, help="Number of flight records (default: 100,000)")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed (default: 42)")
    args = parser.parse_args()

    save_datasets(num_records=args.records, seed=args.seed)
