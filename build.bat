@echo off
title Build FKYC
echo ===================================================
echo Building FKYC (click-to-run folder)
echo ===================================================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Cannot find .venv at %~dp0
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install -q pyinstaller
if errorlevel 1 (
    echo [ERROR] Could not install PyInstaller.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean fkyc.spec
if errorlevel 1 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

echo.
echo Done. Double-click:
echo   %~dp0dist\FKYC\FKYC.exe
echo.
echo Copy the whole dist\FKYC folder to another PC. Do not copy only the exe.
echo User data is stored in %%LOCALAPPDATA%%\FKYC
echo.
pause
