@echo off
REM Windows batch launcher for Protein MD TUI

echo ============================================================
echo Protein MD Simulation TUI Launcher
echo ============================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo Please install Python 3.11+ from python.org
    pause
    exit /b 1
)

echo Python found!
echo.

REM Launch the Python launcher
python launch_tui.py

if errorlevel 1 (
    echo.
    echo TUI exited with error
    pause
)
