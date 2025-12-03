"""
Configuration settings for NIFTY/SENSEX Manual Trader
All sensitive credentials are loaded from Streamlit secrets
"""

import streamlit as st
import pytz
from datetime import datetime
import os

# ═══════════════════════════════════════════════════════════════════════
# TIMEZONE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

# Indian Standard Time (IST) - Use this for all datetime operations
IST = pytz.timezone('Asia/Kolkata')

def get_current_time_ist():
    """Get current time in IST timezone"""
    return datetime.now(IST)

# ═══════════════════════════════════════════════════════════════════════
# CREDENTIALS - Loaded from Streamlit Secrets
# ═══════════════════════════════════════════════════════════════════════

def get_dhan_credentials():
    """Load DhanHQ credentials from secrets"""
    try:
        return {
            'client_id': st.secrets["DHAN"]["CLIENT_ID"],
            'access_token': st.secrets["DHAN"].get("ACCESS_TOKEN", ""),
            'api_key': st.secrets["DHAN"].get("API_KEY", ""),
            'api_secret': st.secrets["DHAN"].get("API_SECRET", "")
        }
    except Exception as e:
        print(f"⚠️ DhanHQ credentials missing: {e}")
        return None

def get_telegram_credentials():
    """Load Telegram credentials from secrets with fallback to hardcoded values"""
    try:
        return {
            'bot_token': st.secrets["TELEGRAM"]["BOT_TOKEN"],
            'chat_id': st.secrets["TELEGRAM"]["CHAT_ID"],
            'enabled': True
        }
    except Exception as e:
        # Fallback to hardcoded credentials if secrets.toml is not available
        print(f"⚠️ Telegram secrets.toml missing, using fallback credentials: {e}")
        # These are the credentials used in other parts of the codebase
        return {
            'bot_token': "8133685842:AAGdHCpi9QRIsS-fWW5Y1AJvS95QL9xU",
            'chat_id': "57096584",
            'enabled': True
        }

# ═══════════════════════════════════════════════════════════════════════
# MARKET HOURS SETTINGS (All times in IST - Indian Standard Time)
# ═══════════════════════════════════════════════════════════════════════

MARKET_HOURS_ENABLED = True  # Set to False to disable market hours checking

# Market session timings (IST)
MARKET_HOURS = {
    'pre_market_open': '08:30',    # 8:30 AM IST
    'market_open': '09:15',        # 9:15 AM IST
    'market_close': '15:30',       # 3:30 PM IST
    'post_market_close': '15:45'   # 3:45 PM IST (App will run until this time)
}

# Session-based refresh intervals (seconds)
# CONSERVATIVE settings to prevent API rate limiting (HTTP 429)
# Data fetch cycle takes ~40-50 seconds, so intervals must be longer
REFRESH_INTERVALS = {
    'pre_market': 90,      # 90 seconds during pre-market (increased from 45s)
    'regular': 90,         # 90 seconds during regular trading (increased from 45s)
    'post_market': 180,    # 180 seconds during post-market (increased from 120s)
    'closed': 300          # 5 minutes when market is closed (minimal activity)
}

# ═══════════════════════════════════════════════════════════════════════
# TRADING SETTINGS
# ═══════════════════════════════════════════════════════════════════════

LOT_SIZES = {
    "NIFTY": 75,
    "SENSEX": 30
}

STRIKE_INTERVALS = {
    "NIFTY": 50,
    "SENSEX": 100
}

SENSEX_NIFTY_RATIO = 3.3  # SENSEX ≈ 3.3 × NIFTY

STOP_LOSS_OFFSET = 10  # Points
SIGNALS_REQUIRED = 3
VOB_TOUCH_TOLERANCE = 5  # Points

# ═══════════════════════════════════════════════════════════════════════
# UI SETTINGS
# ═══════════════════════════════════════════════════════════════════════

# Auto-refresh interval: 5 minutes (300 seconds)
AUTO_REFRESH_INTERVAL = 300  # seconds (5 minutes - optimized for fast clicks)
DEMO_MODE = False

APP_TITLE = "🎯 NIFTY/SENSEX Manual Trader"
APP_SUBTITLE = "VOB-Based Trading | Manual Signal Entry"

COLORS = {
    'bullish': '#089981',
    'bearish': '#f23645',
    'neutral': '#787B86'
}

# ═══════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def get_all_credentials():
    """Get all credentials in a single call"""
    return {
        'dhan': get_dhan_credentials(),
        'telegram': get_telegram_credentials()
    }
