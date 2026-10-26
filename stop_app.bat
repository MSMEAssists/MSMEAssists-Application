@echo off
title Stopping MSMEAssist Application
echo Stopping MSMEAssist services...

powershell -ExecutionPolicy Bypass -File "%~dp0stop_app.ps1"

pause
