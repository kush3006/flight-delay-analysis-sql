from pathlib import Path
import sqlite3
import sys
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Setup Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import DB_PATH, SQL_DIR, get_db_connection

# Page Configuration
st.set_page_config(
    page_title="Flight Delay SQL Analytics | Executive Dashboard",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: 700; color: #1E293B; margin-bottom: 0.2rem; }
    .sub-header { font-size: 1.05rem; color: #64748B; margin-bottom: 1.5rem; }
    .metric-card { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 1rem; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_connection():
    if not DB_PATH.exists():
        st.error(f"Database not found at {DB_PATH}. Please run `python src/seed_database.py` first.")
        st.stop()
    return get_db_connection(DB_PATH)


conn = load_connection()


# ---------------------------------------------------------
# Sidebar Filters
# ---------------------------------------------------------
st.sidebar.title("✈️ Analytics Controls")
st.sidebar.markdown("Filter commercial flight operations:")

carriers_df = pd.read_sql_query("SELECT carrier_code, airline_name FROM airlines ORDER BY carrier_code;", conn)
carrier_options = ["ALL"] + list(carriers_df["carrier_code"] + " - " + carriers_df["airline_name"])
selected_carrier_str = st.sidebar.selectbox("Select Airline", carrier_options, index=0)
selected_carrier = selected_carrier_str.split(" - ")[0] if selected_carrier_str != "ALL" else "ALL"

airports_df = pd.read_sql_query("SELECT iata_code, city FROM airports ORDER BY iata_code;", conn)
airport_options = ["ALL"] + list(airports_df["iata_code"] + " (" + airports_df["city"] + ")")
selected_airport_str = st.sidebar.selectbox("Select Origin Airport", airport_options, index=0)
selected_origin = selected_airport_str.split(" (")[0] if selected_airport_str != "ALL" else "ALL"

st.sidebar.markdown("---")
st.sidebar.info("""
**Data Source**: FAA APO-130 & BTS TranStats Benchmark  
**Standard Cost**: $74.24 / delay minute  
**Target OTP SLA**: 80.0%
""")

# ---------------------------------------------------------
# Dynamic Filter Query Clause
# ---------------------------------------------------------
where_clauses = ["1=1"]
params = []

if selected_carrier != "ALL":
    where_clauses.append("carrier_code = ?")
    params.append(selected_carrier)

if selected_origin != "ALL":
    where_clauses.append("origin_airport = ?")
    params.append(selected_origin)

where_sql = " AND ".join(where_clauses)

# ---------------------------------------------------------
# Header & KPI Metrics
# ---------------------------------------------------------
st.markdown('<div class="main-header">✈️ Commercial Flight Delay & Operations Intelligence</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Relational SQL Analytics Portfolio & Executive Operations Dashboard</div>', unsafe_allow_html=True)

kpi_query = f"""
SELECT 
    COUNT(*) AS total_flights,
    ROUND(SUM(is_on_time_otp15) * 100.0 / NULLIF(SUM(CASE WHEN cancelled = 0 AND diverted = 0 THEN 1 ELSE 0 END), 0), 1) AS otp15_pct,
    ROUND(AVG(dep_delay), 1) AS avg_dep_delay,
    ROUND(AVG(arr_delay), 1) AS avg_arr_delay,
    ROUND(SUM(cancelled) * 100.0 / COUNT(*), 2) AS cancellation_rate,
    ROUND(SUM(CASE WHEN arr_delay > 0 THEN arr_delay * 74.24 ELSE 0 END) / 1000000.0, 2) AS total_delay_cost_million
FROM v_flights_operational_master
WHERE {where_sql};
"""
kpi_df = pd.read_sql_query(kpi_query, conn, params=params)

c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1:
    st.metric("Total Scheduled", f"{kpi_df['total_flights'].iloc[0]:,}")
with c2:
    otp_val = kpi_df['otp15_pct'].iloc[0] or 0.0
    st.metric("On-Time (OTP-15)", f"{otp_val}%", delta=f"{otp_val - 80.0:.1f}% vs Target" if otp_val else None)
with c3:
    st.metric("Avg Dep Delay", f"{kpi_df['avg_dep_delay'].iloc[0] or 0.0} min")
with c4:
    st.metric("Avg Arr Delay", f"{kpi_df['avg_arr_delay'].iloc[0] or 0.0} min")
with c5:
    st.metric("Cancellation Rate", f"{kpi_df['cancellation_rate'].iloc[0] or 0.0}%")
with c6:
    st.metric("Est. Delay Cost", f"${kpi_df['total_delay_cost_million'].iloc[0] or 0.0}M")

st.markdown("---")

# ---------------------------------------------------------
# Tabs for Analytical Modules
# ---------------------------------------------------------
tab_overview, tab_benchmarking, tab_bottlenecks, tab_causes, tab_sql_inspector = st.tabs([
    "📊 Operational Trends", 
    "🏆 Carrier League Table", 
    "🛫 Hub & Corridor Bottlenecks", 
    "🔍 Delay Root Causes", 
    "💻 SQL Query Inspector"
])

# TAB 1: Operational Trends
with tab_overview:
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Monthly On-Time Performance & Cost")
        monthly_query = f"""
        SELECT 
            flight_month,
            ROUND(SUM(is_on_time_otp15) * 100.0 / NULLIF(SUM(CASE WHEN cancelled = 0 AND diverted = 0 THEN 1 ELSE 0 END), 0), 1) AS otp_pct,
            ROUND(SUM(CASE WHEN arr_delay > 0 THEN arr_delay * 74.24 ELSE 0 END) / 1000.0, 1) AS delay_cost_thousand
        FROM v_flights_operational_master
        WHERE {where_sql}
        GROUP BY flight_month
        ORDER BY flight_month ASC;
        """
        df_monthly = pd.read_sql_query(monthly_query, conn, params=params)
        fig_monthly = px.line(
            df_monthly, 
            x="flight_month", 
            y="otp_pct", 
            markers=True, 
            title="Monthly On-Time Arrival Rate (OTP-15)",
            labels={"flight_month": "Month", "otp_pct": "OTP-15 (%)"},
            color_discrete_sequence=["#2563EB"]
        )
        fig_monthly.add_hline(y=80.0, line_dash="dash", line_color="green", annotation_text="Target 80% SLA")
        st.plotly_chart(fig_monthly, use_container_width=True)

    with col_right:
        st.subheader("The Afternoon Delay Cascade (By Departure Hour)")
        hourly_query = f"""
        SELECT 
            dep_hour_bucket || ':00' AS hour_of_day,
            ROUND(AVG(dep_delay), 1) AS avg_departure_delay,
            ROUND(AVG(arr_delay), 1) AS avg_arrival_delay
        FROM v_flights_operational_master
        WHERE {where_sql}
        GROUP BY dep_hour_bucket
        ORDER BY dep_hour_bucket ASC;
        """
        df_hourly = pd.read_sql_query(hourly_query, conn, params=params)
        fig_hourly = px.bar(
            df_hourly, 
            x="hour_of_day", 
            y=["avg_departure_delay", "avg_arrival_delay"],
            barmode="group",
            title="Departure vs Arrival Delay by Hour of Day",
            labels={"value": "Delay Minutes", "hour_of_day": "Scheduled Departure Hour"},
            color_discrete_sequence=["#F59E0B", "#EF4444"]
        )
        st.plotly_chart(fig_hourly, use_container_width=True)


# TAB 2: Carrier Benchmarking
with tab_benchmarking:
    st.subheader("Carrier Punctuality League Table & Ranking")
    league_sql = """
    WITH carrier_metrics AS (
        SELECT 
            carrier_code,
            airline_name,
            COUNT(*) AS total_flights,
            ROUND(SUM(is_on_time_otp15) * 100.0 / NULLIF(SUM(CASE WHEN cancelled = 0 AND diverted = 0 THEN 1 ELSE 0 END), 0), 1) AS otp15_pct,
            ROUND(AVG(dep_delay), 1) AS avg_dep_delay,
            ROUND(AVG(arr_delay), 1) AS avg_arr_delay,
            ROUND(SUM(cancelled) * 100.0 / COUNT(*), 2) AS cancellation_pct,
            ROUND(SUM(CASE WHEN arr_delay > 0 THEN arr_delay * 74.24 ELSE 0 END) / 1000000.0, 2) AS total_delay_cost_m_usd
        FROM v_flights_operational_master
        GROUP BY carrier_code, airline_name
    )
    SELECT 
        DENSE_RANK() OVER (ORDER BY otp15_pct DESC) AS rank,
        carrier_code,
        airline_name,
        total_flights,
        otp15_pct,
        avg_dep_delay,
        avg_arr_delay,
        cancellation_pct,
        total_delay_cost_m_usd
    FROM carrier_metrics
    ORDER BY rank ASC;
    """
    df_league = pd.read_sql_query(league_sql, conn)
    st.dataframe(df_league, use_container_width=True, hide_index=True)

    fig_league = px.bar(
        df_league, 
        x="carrier_code", 
        y="otp15_pct", 
        color="otp15_pct",
        color_continuous_scale="RdYlGn",
        title="Carrier On-Time Performance (OTP-15 %)",
        text="otp15_pct"
    )
    fig_league.update_layout(xaxis_title="Carrier Code", yaxis_title="OTP-15 (%)")
    st.plotly_chart(fig_league, use_container_width=True)


# TAB 3: Hub & Corridor Bottlenecks
with tab_bottlenecks:
    c_hub1, c_hub2 = st.columns(2)

    with c_hub1:
        st.subheader("Worst 10 Origin Airports by Departure Delay")
        worst_airports_sql = """
        SELECT 
            origin_airport,
            origin_city,
            COUNT(*) AS departures,
            ROUND(AVG(dep_delay), 1) AS avg_dep_delay,
            ROUND(AVG(taxi_out), 1) AS avg_taxi_out
        FROM v_flights_operational_master
        GROUP BY origin_airport, origin_city
        ORDER BY avg_dep_delay DESC
        LIMIT 10;
        """
        df_worst_airports = pd.read_sql_query(worst_airports_sql, conn)
        fig_airports = px.bar(
            df_worst_airports,
            x="origin_airport",
            y="avg_dep_delay",
            color="avg_taxi_out",
            title="Avg Departure Delay & Taxi-Out by Origin Hub",
            labels={"origin_airport": "Airport", "avg_dep_delay": "Avg Dep Delay (mins)", "avg_taxi_out": "Taxi-Out (mins)"},
            color_continuous_scale="Oranges"
        )
        st.plotly_chart(fig_airports, use_container_width=True)

    with c_hub2:
        st.subheader("High-Risk Flight Corridors")
        corridor_sql = """
        SELECT 
            origin_airport || ' -> ' || dest_airport AS corridor,
            COUNT(*) AS flight_count,
            ROUND(AVG(arr_delay), 1) AS avg_arr_delay,
            ROUND((AVG(arr_delay) * 0.6) + (SUM(is_delayed_15plus) * 40.0 / COUNT(*)), 1) AS corridor_risk_score
        FROM v_flights_operational_master
        GROUP BY origin_airport, dest_airport
        HAVING COUNT(*) >= 100
        ORDER BY corridor_risk_score DESC
        LIMIT 10;
        """
        df_corridor = pd.read_sql_query(corridor_sql, conn)
        fig_corridor = px.bar(
            df_corridor,
            x="corridor",
            y="corridor_risk_score",
            color="avg_arr_delay",
            title="Top 10 High-Risk Route Corridors",
            labels={"corridor": "Flight Route", "corridor_risk_score": "Risk Index", "avg_arr_delay": "Avg Arr Delay"},
            color_continuous_scale="Reds"
        )
        st.plotly_chart(fig_corridor, use_container_width=True)


# TAB 4: Root Cause Breakdown
with tab_causes:
    st.subheader("Decomposition of Flight Delay Causes (BTS Standard)")
    causes_sql = f"""
    SELECT 
        SUM(carrier_delay) AS "Carrier Internal",
        SUM(late_aircraft_delay) AS "Late Aircraft Turnaround",
        SUM(nas_delay) AS "National Airspace (ATC)",
        SUM(weather_delay) AS "Extreme Weather",
        SUM(security_delay) AS "Security"
    FROM v_flights_operational_master
    WHERE {where_sql} AND is_delayed_15plus = 1;
    """
    df_causes = pd.read_sql_query(causes_sql, conn, params=params)
    causes_melted = df_causes.T.reset_index()
    causes_melted.columns = ["Delay Cause", "Minutes"]

    fig_pie = px.pie(
        causes_melted, 
        names="Delay Cause", 
        values="Minutes", 
        hole=0.45,
        title="Aggregate Delay Minutes by Root Cause Attribution",
        color_discrete_sequence=["#3B82F6", "#F97316", "#8B5CF6", "#10B981", "#64748B"]
    )
    st.plotly_chart(fig_pie, use_container_width=True)


# TAB 5: SQL Query Inspector
with tab_sql_inspector:
    st.subheader("💻 SQL Code & Execution Inspector")
    st.markdown("Inspect and run any production query directly from the SQL repository:")

    sql_files = sorted([f.name for f in SQL_DIR.glob("*.sql") if not f.name.startswith("01_")])
    selected_script = st.selectbox("Select Analysis Module:", sql_files, index=1)

    target_file = SQL_DIR / selected_script
    with open(target_file, "r", encoding="utf-8") as f:
        file_text = f.read()

    from src.run_analysis import split_sql_queries
    parsed_queries = split_sql_queries(file_text)

    query_choices = [q[0] for q in parsed_queries]
    selected_q_name = st.selectbox("Select Query:", query_choices)
    selected_q_sql = [q[1] for q in parsed_queries if q[0] == selected_q_name][0]

    col_code, col_result = st.columns([1, 1])

    with col_code:
        st.markdown("**Executed SQL Query:**")
        st.code(selected_q_sql, language="sql")

    with col_result:
        st.markdown("**Live Query Result:**")
        try:
            df_live = pd.read_sql_query(selected_q_sql, conn)
            st.dataframe(df_live, use_container_width=True)
            st.caption(f"Rows returned: {len(df_live)}")
        except Exception as e:
            st.error(f"Execution Error: {e}")
