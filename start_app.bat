@echo off
title Starting MSMEAssist Application
echo ==========================================================
echo   Starting MSMEAssist Unified Application
echo ==========================================================

cd /d "%~dp0"

echo [1/2] Launching Backend on http://127.0.0.1:8000...
start "MSMEAssist Backend" cmd /k "cd msmeassist-module1\backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 3 /nobreak >nul

echo [2/2] Launching Frontend on http://127.0.0.1:5173...
start "MSMEAssist Frontend" cmd /k "cd msmeassist-module1\frontend && npm run dev"

echo ==========================================================
echo   MSMEAssist is running!
echo   Frontend: http://127.0.0.1:5173
echo   Decision: http://127.0.0.1:5173/decision
echo   Backend:  http://127.0.0.1:8000
echo   API Docs: http://127.0.0.1:8000/docs
echo ==========================================================
pause
