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

def get_supabase_credentials():
    """Load Supabase credentials from secrets"""
    try:
        return {
            'url': st.secrets["SUPABASE"]["URL"],
            'key': st.secrets["SUPABASE"]["KEY"],
            'enabled': True
        }
    except Exception as e:
        print(f"⚠️ Supabase credentials missing: {e}")
        return {
            'url': None,
            'key': None,
            'enabled': False
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

# Unified 30-second refresh interval
# All data fetches synchronized to single 30-second cycle
REFRESH_INTERVALS = {
    'pre_market': 30,      # 30 seconds during pre-market
    'regular': 30,         # 30 seconds during regular trading
    'post_market': 30,     # 30 seconds during post-market
    'closed': 30           # 30 seconds even when market is closed
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

# Auto-refresh interval: 30 seconds (unified refresh cycle)
AUTO_REFRESH_INTERVAL = 30  # seconds
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
        'telegram': get_telegram_credentials(),
        'supabase': get_supabase_credentials()
    }
