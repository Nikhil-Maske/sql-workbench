@echo off
title Launching SQL Data Workbench...
echo Preparing Local SQL Processing Sandbox...

:: Create isolated sandbox environment
if not exist "%TEMP%\sql_workbench_venv" (
    echo Creating isolated environment...
    python -m venv "%TEMP%\sql_workbench_venv"
)

:: Activate sandbox
call "%TEMP%\sql_workbench_venv\Scripts\activate"

:: Install dependencies quietly (Safe Module Method to avoid Pip self-modification errors)
echo Verifying and updating core frameworks...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet streamlit duckdb pandas openpyxl streamlit-ace python-calamine

:: Pull the file you uploaded to GitHub
echo Pulling code from GitHub workspace...
curl -s "https://raw.githubusercontent.com/Nikhil-Maske/sql-workbench/main/app.py" -o "%TEMP%\app.py"

:: Run it!
echo Launching dashboard inside your browser...
streamlit run "%TEMP%\app.py" --client.showErrorDetails=false
pause