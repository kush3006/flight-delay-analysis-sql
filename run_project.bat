@echo off
REM ==============================================================================
REM Flight Delay Analysis Using SQL - One-Click Project Runner
REM ==============================================================================

echo ==============================================================================
echo        FLIGHT DELAY ANALYSIS USING SQL - PORTFOLIO RUNNER
echo ==============================================================================
echo.

REM Step 1: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in system PATH.
    pause
    exit /b 1
)

echo [1/4] Checking Python environment...
python --version

echo.
echo [2/4] Seeding SQLite database with 100,000 flight records...
python src/seed_database.py --records 100000
if %errorlevel% neq 0 (
    echo [ERROR] Seeding failed.
    pause
    exit /b 1
)

echo.
echo [3/4] Running automated test suite (12 tests)...
python -m pytest tests/ -v
if %errorlevel% neq 0 (
    echo [ERROR] Automated tests encountered failures.
    pause
    exit /b 1
)

echo.
echo [4/4] Running sample SQL analytics query suite...
python src/run_analysis.py --file 03_operational_kpis.sql --limit 10

echo.
echo ==============================================================================
echo  ALL CHECKS PASSED! Project is ready for your resume and portfolio.
echo  To launch the interactive dashboard, run:
echo      streamlit run dashboard/app.py
echo ==============================================================================
pause
