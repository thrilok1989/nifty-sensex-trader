"""
Lite Helpers - Minimal helper functions for the lite trading app
Provides essential data fetching and bias calculation support
"""

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz
from typing import Dict, Tuple, Optional
import requests
import time

# Import from existing modules
from config import DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN, IST
from market_hours_scheduler import is_within_trading_hours


def get_current_price(symbol: str) -> Optional[float]:
    """
    Get current price for a symbol using yfinance

    Args:
        symbol: Stock symbol (e.g., '^NSEI', '^BSESN')

    Returns:
        Current price or None if error
    """
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period='1d', interval='1m')
        if not data.empty:
            return round(data['Close'].iloc[-1], 2)
    except Exception as e:
        print(f"Error fetching price for {symbol}: {e}")
    return None


def get_intraday_data(symbol: str, period: str = '1d', interval: str = '5m') -> Optional[pd.DataFrame]:
    """
    Get intraday data for technical analysis

    Args:
        symbol: Stock symbol
        period: Data period ('1d', '5d', etc.)
        interval: Data interval ('1m', '5m', '15m', etc.)

    Returns:
        DataFrame with OHLCV data or None
    """
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period, interval=interval)
        if not data.empty:
            data = data.tz_convert(IST)
            return data
    except Exception as e:
        print(f"Error fetching intraday data for {symbol}: {e}")
    return None


def get_option_chain_dhan(symbol: str, security_id: int) -> Optional[Dict]:
    """
    Fetch option chain data from Dhan API

    Args:
        symbol: Index symbol ('NIFTY', 'SENSEX', 'BANKNIFTY')
        security_id: Dhan security ID for the index

    Returns:
        Dictionary with option chain data or None
    """
    try:
        url = "https://api.dhan.co/v2/optionchain"

        headers = {
            'client-id': DHAN_CLIENT_ID,
            'access-token': DHAN_ACCESS_TOKEN,
            'Content-Type': 'application/json'
        }

        # Get current price first
        price_url = f"https://api.dhan.co/v2/marketfeed/ltp"
        price_payload = {
            "NSE_EQ": [],
            "NSE_FNO": [str(security_id)],
            "BSE_EQ": [],
            "MCX_COMM": []
        }

        price_response = requests.post(price_url, json=price_payload, headers=headers, timeout=10)

        if price_response.status_code != 200:
            return None

        ltp_data = price_response.json()
        if not ltp_data.get('data'):
            return None

        current_price = ltp_data['data']['NSE_FNO'][str(security_id)]['last_price']

        # Get option chain
        payload = {
            "securityId": str(security_id),
            "expiryCode": 0  # 0 for nearest expiry
        }

        response = requests.post(url, json=payload, headers=headers, timeout=15)

        if response.status_code != 200:
            return None

        data = response.json()

        if data.get('status') == 'success':
            return {
                'symbol': symbol,
                'current_price': current_price,
                'option_chain': data.get('data', {}),
                'timestamp': datetime.now(IST)
            }

    except Exception as e:
        print(f"Error fetching option chain for {symbol}: {e}")

    return None


def calculate_pcr_metrics(option_chain_data: Dict) -> Dict:
    """
    Calculate PCR (Put-Call Ratio) metrics from option chain

    Args:
        option_chain_data: Option chain data from Dhan API

    Returns:
        Dictionary with PCR metrics
    """
    try:
        chain = option_chain_data.get('option_chain', {})

        total_ce_oi = 0
        total_pe_oi = 0
        total_ce_oi_change = 0
        total_pe_oi_change = 0
        total_ce_volume = 0
        total_pe_volume = 0

        for strike_data in chain.get('data', []):
            ce_data = strike_data.get('ce', {})
            pe_data = strike_data.get('pe', {})

            total_ce_oi += ce_data.get('openInterest', 0)
            total_pe_oi += pe_data.get('openInterest', 0)
            total_ce_oi_change += ce_data.get('oiChange', 0)
            total_pe_oi_change += pe_data.get('oiChange', 0)
            total_ce_volume += ce_data.get('volume', 0)
            total_pe_volume += pe_data.get('volume', 0)

        # Calculate PCR ratios
        pcr_oi = round(total_pe_oi / total_ce_oi, 3) if total_ce_oi > 0 else 0
        pcr_oi_change = round(total_pe_oi_change / total_ce_oi_change, 3) if total_ce_oi_change > 0 else 0
        pcr_volume = round(total_pe_volume / total_ce_volume, 3) if total_ce_volume > 0 else 0

        return {
            'pcr_oi': pcr_oi,
            'pcr_oi_change': pcr_oi_change,
            'pcr_volume': pcr_volume,
            'total_ce_oi': total_ce_oi,
            'total_pe_oi': total_pe_oi,
            'total_ce_oi_change': total_ce_oi_change,
            'total_pe_oi_change': total_pe_oi_change,
            'total_ce_volume': total_ce_volume,
            'total_pe_volume': total_pe_volume
        }

    except Exception as e:
        print(f"Error calculating PCR metrics: {e}")
        return {}


def calculate_atm_zone_bias(option_chain_data: Dict, atm_range: int = 5) -> Dict:
    """
    Calculate ATM zone bias (ATM ± range strikes)

    Args:
        option_chain_data: Option chain data
        atm_range: Number of strikes above and below ATM (default: 5)

    Returns:
        Dictionary with ATM zone analysis
    """
    try:
        current_price = option_chain_data.get('current_price', 0)
        chain = option_chain_data.get('option_chain', {})

        # Find ATM strike
        strikes = []
        for strike_data in chain.get('data', []):
            strike = strike_data.get('strikePrice', 0)
            if strike > 0:
                strikes.append(strike)

        if not strikes:
            return {}

        strikes = sorted(set(strikes))
        atm_strike = min(strikes, key=lambda x: abs(x - current_price))
        atm_index = strikes.index(atm_strike)

        # Get ATM zone strikes
        start_index = max(0, atm_index - atm_range)
        end_index = min(len(strikes), atm_index + atm_range + 1)
        atm_zone_strikes = strikes[start_index:end_index]

        # Analyze each strike in ATM zone
        strike_analysis = []
        zone_ce_oi = 0
        zone_pe_oi = 0

        for strike_data in chain.get('data', []):
            strike = strike_data.get('strikePrice', 0)

            if strike in atm_zone_strikes:
                ce_data = strike_data.get('ce', {})
                pe_data = strike_data.get('pe', {})

                ce_oi = ce_data.get('openInterest', 0)
                pe_oi = pe_data.get('openInterest', 0)

                zone_ce_oi += ce_oi
                zone_pe_oi += pe_oi

                # Strike-level PCR
                strike_pcr = round(pe_oi / ce_oi, 3) if ce_oi > 0 else 0

                # Determine bias
                if strike_pcr > 1.2:
                    bias = "Bullish"
                elif strike_pcr < 0.8:
                    bias = "Bearish"
                else:
                    bias = "Neutral"

                strike_analysis.append({
                    'strike': strike,
                    'is_atm': strike == atm_strike,
                    'ce_oi': ce_oi,
                    'pe_oi': pe_oi,
                    'pcr': strike_pcr,
                    'bias': bias
                })

        # Overall zone bias
        zone_pcr = round(zone_pe_oi / zone_ce_oi, 3) if zone_ce_oi > 0 else 0

        if zone_pcr > 1.2:
            zone_bias = "Bullish"
        elif zone_pcr < 0.8:
            zone_bias = "Bearish"
        else:
            zone_bias = "Neutral"

        return {
            'atm_strike': atm_strike,
            'current_price': current_price,
            'zone_range': f"ATM ±{atm_range}",
            'zone_strikes': atm_zone_strikes,
            'zone_pcr': zone_pcr,
            'zone_bias': zone_bias,
            'zone_ce_oi': zone_ce_oi,
            'zone_pe_oi': zone_pe_oi,
            'strike_analysis': strike_analysis
        }

    except Exception as e:
        print(f"Error calculating ATM zone bias: {e}")
        return {}


def format_number(num: float, decimals: int = 2) -> str:
    """Format number with commas and decimals"""
    if num >= 10000000:  # 1 Cr
        return f"{num/10000000:.{decimals}f}Cr"
    elif num >= 100000:  # 1 Lakh
        return f"{num/100000:.{decimals}f}L"
    else:
        return f"{num:,.{decimals}f}"


def get_bias_color(bias: str) -> str:
    """Get color for bias indicator"""
    if bias.lower() == 'bullish':
        return 'green'
    elif bias.lower() == 'bearish':
        return 'red'
    else:
        return 'gray'


def get_bias_emoji(bias: str) -> str:
    """Get emoji for bias indicator"""
    if bias.lower() == 'bullish':
        return '🟢'
    elif bias.lower() == 'bearish':
        return '🔴'
    else:
        return '⚪'


# Index configuration for quick access
INDEX_CONFIG = {
    'NIFTY': {
        'symbol': '^NSEI',
        'security_id': 13,
        'name': 'NIFTY 50'
    },
    'SENSEX': {
        'symbol': '^BSESN',
        'security_id': 51,
        'name': 'SENSEX'
    },
    'BANKNIFTY': {
        'symbol': '^NSEBANK',
        'security_id': 25,
        'name': 'BANK NIFTY'
    }
}
