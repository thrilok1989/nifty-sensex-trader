@echo off
REM NIFTY SENSEX Trader - Lite Version Launcher (Windows)
REM Quick start script for the lite application

echo.
echo 🚀 Starting NIFTY SENSEX Trader - LITE VERSION
echo ================================================
echo.
echo Features:
echo   ✅ Technical Bias (8 indicators)
echo   ✅ PCR Analysis
echo   ✅ Option Chain Bias
echo   ✅ ATM Zone Bias
echo   ✅ Overall Market Bias
echo.
echo ================================================
echo.

REM Check if streamlit is installed
where streamlit >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Streamlit is not installed!
    echo Please install dependencies: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Check if config.py exists
if not exist "config.py" (
    echo ❌ config.py not found!
    echo Please ensure config.py exists with required credentials
    pause
    exit /b 1
)

REM Run the lite app
echo 🎯 Launching app...
echo The app will open in your browser at http://localhost:8501
echo.
echo Press Ctrl+C to stop the app
echo.

streamlit run app_lite.py --server.port 8501
