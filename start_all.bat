@echo off
cd /d "%~dp0"
echo ===================================================
echo Starting ClipGenR AI Platform (Backend + Frontend)
echo ===================================================

echo [1/2] Launching Backend API Server (Port 8000)...
start "ClipGenR Backend" cmd /k "cd /d ""%~dp0"" && .\backend\venv\Scripts\python.exe run_backend.py"

timeout /t 2 >nul

echo [2/2] Launching Frontend Next.js Studio (Port 3000)...
start "ClipGenR Frontend" cmd /k "cd /d ""%~dp0frontend"" && npm run dev"

echo.
echo ===================================================
echo Both servers are starting up!
echo - Frontend Studio: http://localhost:3000
echo - Backend API Docs: http://localhost:8000/docs
echo ===================================================
timeout /t 4 >nul
start http://localhost:3000
