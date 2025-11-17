import streamlit as st

# ═══════════════════════════════════════════════════════════════════════
# CREDENTIALS
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
        st.error(f"⚠️ DhanHQ credentials missing: {e}")
        return None

def get_telegram_credentials():
    """Load Telegram credentials from secrets"""
    try:
        return {
            'bot_token': st.secrets["TELEGRAM"]["BOT_TOKEN"],
            'chat_id': st.secrets["TELEGRAM"]["CHAT_ID"],
            'enabled': True
        }
    except:
        return {'enabled': False}

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
REFRESH_INTERVALS = {
    'pre_market': 30,      # 30 seconds during pre-market
    'regular': 10,         # 10 seconds during regular trading
    'post_market': 60,     # 60 seconds during post-market
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

# Auto-refresh interval: 60 seconds (1 minute)
# Data Loading Strategy (OPTIMIZED):
# - Background threading with smart caching
# - Market data (NIFTY/SENSEX): Refreshes every 10 seconds in background
# - Analysis data (Dashboard/Bias): Refreshes every 60 seconds in background
# - UI updates: Page reloads every 60 seconds to display fresh cached data
# - All tabs show pre-loaded data immediately (no waiting for button clicks)
# - Manual refresh available via "Refresh Now" buttons
AUTO_REFRESH_INTERVAL = 60  # seconds
DEMO_MODE = False

APP_TITLE = "🎯 NIFTY/SENSEX Manual Trader"
APP_SUBTITLE = "VOB-Based Trading | Manual Signal Entry"

COLORS = {
    'bullish': '#089981',
    'bearish': '#f23645',
    'neutral': '#787B86'
}
