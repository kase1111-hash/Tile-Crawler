@echo off
echo ============================================
echo   Tile-Crawler Build Script
echo ============================================
echo.

:: Try to find a compatible Python version using py launcher
set PYTHON_CMD=

:: Check if py launcher is available (standard on Windows)
where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    :: Try Python 3.13 first, then 3.12, 3.11, 3.10
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
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set PYTHON_CMD=python
)

if "%PYTHON_CMD%"=="" (
    echo ERROR: Python not found. Please install Python 3.10-3.13
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

:found_python
:: Get and display version
for /f "tokens=2" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set PYVER=%%i
echo Using: %PYTHON_CMD% ^(%PYVER%^)

:: Extract major.minor version
for /f "tokens=1,2 delims=." %%a in ("%PYVER%") do (
    set PYMAJOR=%%a
    set PYMINOR=%%b
)

:: Check version compatibility
if %PYMAJOR% NEQ 3 (
    echo ERROR: Python 3.x required, found Python %PYMAJOR%
    pause
    exit /b 1
)

if %PYMINOR% LSS 10 (
    echo ERROR: Python 3.10+ required, found Python 3.%PYMINOR%
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

if %PYMINOR% GTR 13 (
    echo ERROR: Python 3.14+ is not yet supported by pydantic
    echo.
    echo You have Python 3.13 installed. Try running:
    echo     py -3.13 -m pip install -r backend\requirements.txt
    echo.
    echo Or uninstall Python 3.14 to make 3.13 the default.
    pause
    exit /b 1
)

echo Python version OK

:: Check for Node.js
where node >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: Node.js not found. Please install Node.js 18+
    echo Download from: https://nodejs.org/
    pause
    exit /b 1
)

echo.
echo [1/4] Installing backend dependencies...
cd backend
%PYTHON_CMD% -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to install backend dependencies
    pause
    exit /b 1
)

echo.
echo [2/4] Setting up environment...
if not exist .env (
    copy .env.example .env
    echo Created .env from .env.example
    echo NOTE: Edit backend\.env to configure your LLM provider
)

echo.
echo [3/4] Installing frontend dependencies...
cd ..\frontend
call npm install
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to install frontend dependencies
    pause
    exit /b 1
)

echo.
echo [4/4] Building frontend...
call npm run build
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to build frontend
    pause
    exit /b 1
)

cd ..
echo.
echo ============================================
echo   Build Complete!
echo ============================================
echo.
echo Next steps:
echo   1. (Optional) Edit backend\.env for Ollama/OpenAI
echo   2. Run: run.bat
echo.
pause
