@echo off
REM Build a real standalone ClaudeMeter.exe via PyInstaller.
REM Output: dist\ClaudeMeter.exe — copy/move anywhere, no Python required.
setlocal
cd /d "%~dp0"

if not exist .venv (
    python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
pip install --quiet -r requirements-dev.txt
pip install --quiet -e .

pyinstaller build.spec --clean --noconfirm

echo.
echo ==========================================================
echo  Built: dist\ClaudeMeter.exe
echo  Move it anywhere; double-click to launch (no console).
echo  Right-click the tray icon to enable "Run at startup".
echo ==========================================================
echo.
pause
endlocal
