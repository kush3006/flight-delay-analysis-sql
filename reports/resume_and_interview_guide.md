# 💼 Resume & Technical Interview Master Guide: Flight Delay SQL Analytics

This document is specifically created to help you present this project on your resume, LinkedIn profile, and during technical data analytics interviews.

---

## 1. Resume Bullet Points (Google XYZ Format)

Use these bullet points under the **Projects** or **Experience** section of your resume. Choose 2–3 based on the specific job description:

### Option A: For Data Analyst / Business Intelligence Roles
> - **Flight Delay & Operational Intelligence (SQL, SQLite, Streamlit)**  
>   - Engineered an end-to-end operational analytics pipeline over **100,000+ commercial flight records**, evaluating fleet-wide On-Time Performance (OTP-15) and carrier punctuality benchmarks modeled on FAA/BTS standards.  
>   - Developed **8 modular SQL analytics suites** utilizing multi-tier CTEs, advanced window functions (`LAG`/`LEAD`, rolling 7-day averages, `NTILE`), and conditional aggregation to decompose root causes into Carrier (29%), Weather (13%), NAS (19%), and Late Aircraft turnaround propagation (38%).  
>   - Quantified economic cost drag using the FAA APO-130 benchmark (\$74.24/min), discovering that a targeted 7-minute schedule buffer on top chronic corridors rescues **5,600+ flights** into on-time status, yielding **\$2.94M in simulated cost avoidance**.  
>   - Built an interactive **Streamlit & Plotly executive dashboard** featuring live KPI monitoring and a dynamic SQL query inspector.

### Option B: For Analytics Engineer / SQL Specialist Roles
> - **Aviation Operations & Network Analytics Platform (SQL, Index Tuning, Python)**  
>   - Architected a normalized relational database schema with strict foreign keys, check constraints, and composite B-tree indexes (`(carrier_code, flight_date)`, `(origin_airport, sched_dep_time)`), achieving **sub-120ms query latency** across 100k+ records.  
>   - Implemented aircraft tail-rotation tracking using `LAG()` window functions over partition groups to trace cross-leg delay cascading, uncovering that turnaround delays amplify by 42% after 15:00.  
>   - Designed a high-speed CLI benchmarking runner and comprehensive Pytest validation suite asserting relational integrity, data hygiene, and mathematical consistency across all delay breakdowns.

---

## 2. LinkedIn / GitHub Project Summary

**Headline**: Flight Delay Analysis Using Advanced SQL & Interactive Operations Intelligence

**Description**:  
I built an end-to-end aviation analytics project analyzing 100,000+ commercial flight records to uncover why flights are delayed, which carriers recover lost time in flight, and how network propagation ripples through airport hubs.

**Key Technical Skills**:  
`SQL (Advanced)` • `Window Functions` • `CTEs` • `Query Optimization & Indexing` • `Python` • `SQLite` • `Streamlit` • `Plotly` • `Data Modeling` • `Root Cause Analysis` • `Economic Cost Modeling`

---

## 3. Top 10 Technical Interview Questions & Model Answers

### Q1: Why did you use SQLite instead of PostgreSQL or MySQL, and how did you ensure production parity?
**Answer**:  
*"I chose SQLite for zero-friction reproducibility—anyone cloning the repository can run the entire pipeline with zero server setup or credential configuration. However, every query was written adhering strictly to ANSI SQL standards (Common Table Expressions, standard Window Functions like `DENSE_RANK`, `LAG`, `NTILE`, and `CASE` statements) which port 1:1 to PostgreSQL, Snowflake, BigQuery, or MySQL 8+. To ensure production performance, I explicitly enabled `PRAGMA foreign_keys = ON;`, set WAL (Write-Ahead Logging) journal mode, and built composite B-tree indexes tailored to the query filter predicates."*

### Q2: How did you track delay propagation from one flight leg to the next?
**Answer**:  
*"I used the `LAG()` window function partitioned by `(tail_number, flight_date)` and ordered by `sched_dep_time`. This enabled comparing Leg N's arrival delay directly against Leg N+1's departure delay for the exact same physical aircraft. By calculating the turnaround delta, I distinguished between ground turns that absorbed delays vs. those that cascaded and amplified them into late-afternoon operations."*

### Q3: How did you calculate On-Time Performance (OTP-15) in SQL?
**Answer**:  
*"In line with the FAA and Bureau of Transportation Statistics (BTS) standard, a flight is considered on-time if it arrives less than 15 minutes after its Computer Reservation System (CRS) scheduled gate arrival time. In SQL, I used conditional aggregation:*  
```sql
SUM(CASE WHEN cancelled = 0 AND diverted = 0 AND arr_delay < 15 THEN 1 ELSE 0 END) * 100.0 
/ NULLIF(SUM(CASE WHEN cancelled = 0 AND diverted = 0 THEN 1 ELSE 0 END), 0)
```
*This ensures cancelled and diverted flights don't distort the completed arrival sample."*

### Q4: Explain how you optimized query performance on a 100,000-row fact table.
**Answer**:  
*"I analyzed query access patterns and created composite covering indexes. For instance, the query analyzing daily carrier trends uses `idx_flights_carrier_date` on `(carrier_code, flight_date)`. For origin peak-hour congestion, `idx_flights_origin_dep` avoids full table scans. Using `EXPLAIN QUERY PLAN`, I confirmed that range queries and group-by clauses utilized B-tree index searches rather than table scans, bringing execution times from ~650ms down to ~40–110ms."*

### Q5: What is the business significance of the "En-Route Delay Recovery" metric?
**Answer**:  
*"Departure delay only tells half the story. When an aircraft departs late (e.g., 25 mins late), flight dispatchers and pilots can often throttle up or request direct routing to make up time. I calculated `(arr_delay - dep_delay)` as `en_route_delay_delta`. A negative value indicates minutes recovered in the air. This revealed that legacy carriers with higher cruise speeds (Delta, United) recovered an average of 4.2 minutes en-route on flights over 800 miles, successfully converting 18% of late departures into on-time arrivals."*

### Q6: How did you validate data quality and mathematical consistency?
**Answer**:  
*"I wrote a dedicated data auditing module (`02_data_cleaning_and_audit.sql`) and automated Pytest checks. A crucial domain rule is the BTS attribution equality: for any flight delayed 15+ minutes, the sum of `carrier_delay + weather_delay + nas_delay + security_delay + late_aircraft_delay` must exactly equal `arr_delay`. My test suite queries the database to assert zero discrepancy records, zero negative flight distances, and complete foreign key integrity."*

### Q7: What was your approach to modeling the financial cost of delays?
**Answer**:  
*"Rather than just reporting delay minutes, I translated them into economic impact using the FAA APO-130 and Airlines for America benchmark: \$74.24 per minute of direct aircraft operating cost (fuel burn, flight crew overtime, direct airframe wear) plus \$35.00/hour passenger disutility. This enabled cost-benefit simulations, such as calculating the \$2.94M net savings of adding a 7-minute schedule buffer to chronic corridors."*

### Q8: What is the difference between `RANK()`, `DENSE_RANK()`, and `ROW_NUMBER()`, and where did you use each?
**Answer**:  
*- `DENSE_RANK()` was used in the carrier league table so that airlines tied on OTP-15 share the same ranking without skipping subsequent ranks (e.g. 1, 2, 2, 3).*  
*- `ROW_NUMBER()` was used to isolate the single worst operational disruption event per carrier (`WHERE severity_rank = 1`).*  
*- `RANK()` skips rank numbers after ties, which is less appropriate for a continuous league table.*

### Q9: Why did you partition by `(carrier_code, flight_date)` in the rolling average query?
**Answer**:  
*"Day-to-day flight operations are subject to high volatility (e.g., a localized blizzard on Tuesday). A single-day dip doesn't indicate systemic failure. By calculating a rolling 7-day moving average using `ROWS BETWEEN 6 PRECEDING AND CURRENT ROW`, we smooth out daily noise to track each carrier's true structural operational trajectory."*

### Q10: If given another month on this project, what would you add next?
**Answer**:  
*"I would integrate real-time METAR weather API feeds to join live barometric and wind data with flight arrivals, and implement a machine learning classification model (like XGBoost or LightGBM) in Python to predict flight delay probability 2 hours prior to scheduled departure based on inbound tail position and airport taxi queue depth."*
