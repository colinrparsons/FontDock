@echo off
REM FontDock Server Startup Script (Windows)

cd /d "%~dp0"

echo =========================================
echo Starting FontDock Server
echo =========================================
echo.
echo Server URL: http://localhost:9998
echo Web UI: http://localhost:9998/ui/login
echo.
echo Press Ctrl+C to stop the server
echo =========================================
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 9998 --reload --log-level debug
pause
