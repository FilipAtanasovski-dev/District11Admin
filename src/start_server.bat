@echo off
title Restaurant Server

echo.
echo ==========================================
echo          RESTAURANT SERVER
echo ==========================================
echo.
echo Finding server IP...
echo.

for /f "tokens=2 delims=[]" %%A in ('ping %COMPUTERNAME% -4 -n 1 ^| findstr "["') do set "IP=%%A"

echo Server IP: %IP%
echo Server URL: http://%IP%:8000
echo.
echo Starting server...
echo.

python -m uvicorn main:app --reload --host 0.0.0.0

pause