@echo off
title FKYC Admin
echo ===================================================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Cannot find .venv directory at %~dp0
    echo Please check the Python environment.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

echo Starting ADMIN ...
echo.

".venv\Scripts\python.exe" -m fkyc.admin

pause
