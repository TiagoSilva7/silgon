@echo off
cd /d %~dp0
start "" python app.py
timeout /t 1 >nul
start "" "chrome" "http://127.0.0.1:5000"
