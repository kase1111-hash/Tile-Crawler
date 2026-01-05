@echo off
echo ============================================
echo   Tile-Crawler - Starting Game
echo ============================================
echo.

:: Check if build was run
if not exist frontend\node_modules (
    echo ERROR: Dependencies not installed. Run build.bat first.
    pause
    exit /b 1
)

:: Find compatible Python version using py launcher
set PYTHON_CMD=
where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    py -3.13 --version >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        set PYTHON_CMD=py -3.13
        goto :found_python
    )
    py -3.12 --version >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        set PYTHON_CMD=py -3.12
        goto :found_python
    )
    py -3.11 --version >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        set PYTHON_CMD=py -3.11
        goto :found_python
    )
    py -3.10 --version >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        set PYTHON_CMD=py -3.10
        goto :found_python
    )
)

:: Fallback to python command
set PYTHON_CMD=python

:found_python
echo Using: %PYTHON_CMD%

echo Starting backend server...
start "Tile-Crawler Backend" cmd /k "cd backend && %PYTHON_CMD% main.py"

:: Wait for backend to start
timeout /t 2 /nobreak >nul

echo Starting frontend dev server...
start "Tile-Crawler Frontend" cmd /k "cd frontend && npm run dev"

:: Wait for frontend to start
timeout /t 3 /nobreak >nul

echo.
echo ============================================
echo   Game is starting!
echo ============================================
echo.
echo Opening browser to: http://localhost:5173
echo.
echo Press any key to open browser, or Ctrl+C to skip...
pause >nul

start http://localhost:5173

echo.
echo To stop the game, close both terminal windows.
echo.
