"""
Market Data Module - Using Dhan API
====================================

Fetches market data from Dhan API with proper rate limiting.
Replaces the old NSE-based data fetching.
"""

from datetime import datetime
import pytz
from dhan_data_fetcher import get_nifty_data, get_sensex_data, DhanDataFetcher

IST = pytz.timezone("Asia/Kolkata")


def is_market_open():
    """Check if NSE market is open"""
    now = datetime.now(IST)
    if now.weekday() >= 5:
        return False
    market_open = now.replace(hour=9, minute=0, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=40, second=0, microsecond=0)
    return market_open <= now <= market_close


def fetch_nifty_data():
    """
    Fetch live NIFTY data from Dhan API

    Returns:
        Dict with NIFTY data including spot price, ATM strike, expiry dates, etc.
    """
    try:
        data = get_nifty_data()
        return data
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def fetch_sensex_data():
    """
    Fetch live SENSEX data from Dhan API

    Returns:
        Dict with SENSEX data including spot price, ATM strike, etc.
    """
    try:
        data = get_sensex_data()
        return data
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def fetch_all_market_data():
    """
    Fetch all market data (NIFTY, SENSEX) in one sequential call

    This uses the rate-limited sequential fetching from DhanDataFetcher

    Returns:
        Dict with all market data
    """
    try:
        fetcher = DhanDataFetcher()
        all_data = fetcher.fetch_all_data_sequential()
        return all_data
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def check_vob_touch(current_price, vob_level, tolerance=5):
    """Check if price touched VOB level"""
    return abs(current_price - vob_level) <= tolerance


def get_market_status():
    """Get current market status"""
    now = datetime.now(IST)

    if not is_market_open():
        if now.weekday() >= 5:
            return {
                'open': False,
                'message': '🔴 Market Closed (Weekend)'
            }
        else:
            return {
                'open': False,
                'message': '🔴 Market Closed'
            }

    return {
        'open': True,
        'message': '🟢 Market Open',
        'time': now.strftime('%H:%M:%S IST')
    }
