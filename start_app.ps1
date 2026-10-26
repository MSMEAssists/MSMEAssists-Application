# MSMEAssist - Quick Start Script (PowerShell)
# Starts MongoDB (if not running), FastAPI Backend on Port 8000, and Vite Frontend on Port 5173

$Root = $PSScriptRoot

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Starting MSMEAssist Unified Application                 " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Verify MongoDB
$mongo = Get-Service -Name *mongo* -ErrorAction SilentlyContinue
if ($mongo -and $mongo.Status -ne 'Running') {
    Write-Host "[1/3] Starting MongoDB service..." -ForegroundColor Yellow
    Start-Service -Name $mongo.Name -ErrorAction SilentlyContinue
} else {
    Write-Host "[1/3] MongoDB service verified (Running)." -ForegroundColor Green
}

# 2. Start Backend
Write-Host "[2/3] Launching FastAPI Backend on http://127.0.0.1:8000..." -ForegroundColor Yellow
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "cd '$Root\msmeassist-module1\backend'; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

Start-Sleep -Seconds 3

# 3. Start Frontend
Write-Host "[3/3] Launching Vite Frontend on http://127.0.0.1:5173..." -ForegroundColor Yellow
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "cd '$Root\msmeassist-module1\frontend'; npm run dev"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  MSMEAssist is running!                                  " -ForegroundColor Green
Write-Host "  - Frontend URL: http://127.0.0.1:5173                   " -ForegroundColor White
Write-Host "  - Decision Page: http://127.0.0.1:5173/decision         " -ForegroundColor White
Write-Host "  - Backend API:  http://127.0.0.1:8000                   " -ForegroundColor White
Write-Host "  - API Docs:     http://127.0.0.1:8000/docs              " -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Cyan
