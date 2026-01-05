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

echo Starting backend server...
start "Tile-Crawler Backend" cmd /k "cd backend && python main.py"

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
