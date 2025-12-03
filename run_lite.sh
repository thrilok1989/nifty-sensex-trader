#!/bin/bash

# NIFTY SENSEX Trader - Lite Version Launcher
# Quick start script for the lite application

echo "🚀 Starting NIFTY SENSEX Trader - LITE VERSION"
echo "================================================"
echo ""
echo "Features:"
echo "  ✅ Technical Bias (8 indicators)"
echo "  ✅ PCR Analysis"
echo "  ✅ Option Chain Bias"
echo "  ✅ ATM Zone Bias"
echo "  ✅ Overall Market Bias"
echo ""
echo "================================================"
echo ""

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null
then
    echo "❌ Streamlit is not installed!"
    echo "Please install dependencies: pip install -r requirements.txt"
    exit 1
fi

# Check if config.py exists
if [ ! -f "config.py" ]; then
    echo "❌ config.py not found!"
    echo "Please ensure config.py exists with required credentials"
    exit 1
fi

# Run the lite app
echo "🎯 Launching app..."
echo "The app will open in your browser at http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the app"
echo ""

streamlit run app_lite.py --server.port 8501
