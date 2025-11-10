# market_data.py
"""
Market data fetcher - NIFTY ONLY (NSE API)
"""

import requests
import pandas as pd
from datetime import datetime
import pytz
import streamlit as st

IST = pytz.timezone("Asia/Kolkata")

def is_market_open():
    """Check if NSE market is open"""
    now = datetime.now(IST)
    if now.weekday() >= 5:
        return False
    market_open = now.replace(hour=9, minute=0, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=40, second=0, microsecond=0)
    return market_open <= now <= market_close

@st.cache_data(ttl=60)
def fetch_nifty_data():
    """Fetch live NIFTY data from NSE"""
    url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers, timeout=5)
        response = session.get(url, headers=headers, timeout=10)
        data = response.json()
        
        records = data['records']['data']
        underlying = data['records'].get('underlyingValue', 0)
        expiry_dates = data['records']['expiryDates']
        
        atm_strike = round(underlying / 50) * 50
        
        return {
            'success': True,
            'spot_price': underlying,
            'atm_strike': atm_strike,
            'expiry_dates': expiry_dates,
            'current_expiry': expiry_dates[0],
            'timestamp': datetime.now(IST)
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def check_vob_touch(current_price, vob_level, tolerance=5):
    """Check if price touched VOB level"""
    return abs(current_price - vob_level) <= tolerance

def is_expiry_day(expiry_date_str):
    """Check if today is expiry day"""
    try:
        expiry_date = datetime.strptime(expiry_date_str, "%d-%b-%Y").date()
        today = datetime.now(IST).date()
        return expiry_date == today
    except:
        return False

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
