@echo off
REM Local build helper. Run from a Developer Command Prompt or normal cmd.
REM Requires Python 3.10+ on PATH.
setlocal
python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
pyinstaller build.spec --clean --noconfirm
echo.
echo Built: dist\ClaudeMeter.exe
endlocal
