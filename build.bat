@echo off
echo ============================================
echo   Tile-Crawler Build Script
echo ============================================
echo.

:: Check for Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python not found. Please install Python 3.10+
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Check for Node.js
where node >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: Node.js not found. Please install Node.js 18+
    echo Download from: https://nodejs.org/
    pause
    exit /b 1
)

echo [1/4] Installing backend dependencies...
cd backend
pip install -r requirements.txt
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
