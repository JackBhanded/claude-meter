@echo off
REM Launch Claude Meter — silent, no persistent console window.
REM First run sets up a virtual environment (~30s). Subsequent runs are instant.
setlocal
cd /d "%~dp0"

if not exist .venv (
    echo Setting up Claude Meter ^(first run only^)...
    python -m venv .venv
    .venv\Scripts\python.exe -m pip install --upgrade pip --quiet
    .venv\Scripts\python.exe -m pip install --quiet -r requirements.txt
    .venv\Scripts\python.exe -m pip install --quiet -e .
)

REM Use pythonw.exe — no console window. `start ""` detaches the process so
REM this cmd window can close immediately while the widget keeps running.
start "" .venv\Scripts\pythonw.exe -m claude_usage_widget
endlocal
exit
