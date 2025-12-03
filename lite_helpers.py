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
from market_hours_scheduler import is_market_open


def get_current_price(symbol: str) -> Optional[float]:
    """
    Get current price for a symbol using yfinance

    Args:
        symbol: Symbol to fetch (e.g., '^NSEI' for NIFTY)

    Returns:
        Current price or None if failed
    """
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period='1d', interval='1m')
        if not data.empty:
            return float(data['Close'].iloc[-1])
    except Exception as e:
        print(f"Error fetching price for {symbol}: {e}")
    return None


def get_intraday_data(symbol: str, days: int = 7) -> Optional[pd.DataFrame]:
    """
    Get intraday data for bias analysis

    Args:
        symbol: Symbol to fetch (e.g., '^NSEI' for NIFTY)
        days: Number of days of data to fetch

    Returns:
        DataFrame with OHLCV data or None if failed
    """
    try:
        ticker = yf.Ticker(symbol)
        # Fetch 5-minute data for the specified number of days
        data = ticker.history(period=f'{days}d', interval='5m')

        if data.empty:
            return None

        # Rename columns to match expected format
        data = data.rename(columns={
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })

        # Reset index to have timestamp as column
        data = data.reset_index()
        data = data.rename(columns={'Datetime': 'timestamp'})

        return data

    except Exception as e:
        print(f"Error fetching intraday data for {symbol}: {e}")
        return None


def fetch_dhan_option_chain(underlying: str, expiry_date: str) -> Optional[Dict]:
    """
    Fetch option chain data from Dhan API

    Args:
        underlying: Underlying symbol ('NIFTY' or 'BANKNIFTY')
        expiry_date: Expiry date in 'YYYY-MM-DD' format

    Returns:
        Dictionary with option chain data or None if failed
    """
    try:
        # Security IDs for Dhan API
        security_ids = {
            'NIFTY': '13',
            'BANKNIFTY': '25',
            'SENSEX': '51'
        }

        if underlying not in security_ids:
            print(f"Unsupported underlying: {underlying}")
            return None

        security_id = security_ids[underlying]

        # Dhan API endpoint
        url = f"https://api.dhan.co/v2/option-chain"

        headers = {
            'access-token': DHAN_ACCESS_TOKEN,
            'Content-Type': 'application/json'
        }

        params = {
            'underlying_security_id': security_id,
            'expiry_date': expiry_date
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to fetch option chain: {response.status_code}")
            return None

    except Exception as e:
        print(f"Error fetching option chain: {e}")
        return None


def get_nearest_expiry() -> str:
    """
    Get the nearest Thursday expiry date for NIFTY

    Returns:
        Expiry date in 'YYYY-MM-DD' format
    """
    try:
        today = datetime.now(IST).date()

        # Find next Thursday
        days_ahead = (3 - today.weekday()) % 7  # Thursday is 3
        if days_ahead == 0 and datetime.now(IST).time().hour >= 15:
            # If it's Thursday and market has closed, get next Thursday
            days_ahead = 7

        next_thursday = today + timedelta(days=days_ahead)
        return next_thursday.strftime('%Y-%m-%d')

    except Exception as e:
        print(f"Error calculating expiry: {e}")
        # Default fallback
        return (datetime.now(IST).date() + timedelta(days=7)).strftime('%Y-%m-%d')


def calculate_pcr_metrics(option_chain_data: Dict) -> Dict:
    """
    Calculate PCR metrics from option chain data

    Args:
        option_chain_data: Option chain data from Dhan API

    Returns:
        Dictionary with PCR metrics
    """
    try:
        if not option_chain_data or 'data' not in option_chain_data:
            return {
                'pcr_oi': 0,
                'pcr_oi_change': 0,
                'pcr_volume': 0,
                'total_ce_oi': 0,
                'total_pe_oi': 0,
                'total_ce_volume': 0,
                'total_pe_volume': 0,
                'bias': 'NEUTRAL'
            }

        total_ce_oi = 0
        total_pe_oi = 0
        total_ce_oi_change = 0
        total_pe_oi_change = 0
        total_ce_volume = 0
        total_pe_volume = 0

        for strike in option_chain_data['data']:
            # CE data
            if 'CE' in strike:
                ce = strike['CE']
                total_ce_oi += ce.get('openInterest', 0)
                total_ce_oi_change += ce.get('openInterestChange', 0)
                total_ce_volume += ce.get('volume', 0)

            # PE data
            if 'PE' in strike:
                pe = strike['PE']
                total_pe_oi += pe.get('openInterest', 0)
                total_pe_oi_change += pe.get('openInterestChange', 0)
                total_pe_volume += pe.get('volume', 0)

        # Calculate PCR ratios
        pcr_oi = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 0
        pcr_oi_change = total_pe_oi_change / total_ce_oi_change if total_ce_oi_change != 0 else 0
        pcr_volume = total_pe_volume / total_ce_volume if total_ce_volume > 0 else 0

        # Determine bias
        if pcr_oi > 1.2:
            bias = 'BULLISH'
        elif pcr_oi < 0.8:
            bias = 'BEARISH'
        else:
            bias = 'NEUTRAL'

        return {
            'pcr_oi': round(pcr_oi, 2),
            'pcr_oi_change': round(pcr_oi_change, 2) if pcr_oi_change != 0 else 0,
            'pcr_volume': round(pcr_volume, 2),
            'total_ce_oi': total_ce_oi,
            'total_pe_oi': total_pe_oi,
            'total_ce_volume': total_ce_volume,
            'total_pe_volume': total_pe_volume,
            'bias': bias
        }

    except Exception as e:
        print(f"Error calculating PCR metrics: {e}")
        return {
            'pcr_oi': 0,
            'pcr_oi_change': 0,
            'pcr_volume': 0,
            'total_ce_oi': 0,
            'total_pe_oi': 0,
            'total_ce_volume': 0,
            'total_pe_volume': 0,
            'bias': 'NEUTRAL'
        }


def get_atm_zone_bias(option_chain_data: Dict, spot_price: float, num_strikes: int = 5) -> Dict:
    """
    Calculate ATM zone bias (ATM ±num_strikes)

    Args:
        option_chain_data: Option chain data from Dhan API
        spot_price: Current spot price
        num_strikes: Number of strikes above and below ATM to analyze

    Returns:
        Dictionary with ATM zone analysis
    """
    try:
        if not option_chain_data or 'data' not in option_chain_data:
            return {'strikes': [], 'summary': {}}

        # Find ATM strike
        strikes = []
        for strike_data in option_chain_data['data']:
            if 'strikePrice' in strike_data:
                strikes.append(strike_data)

        # Sort by proximity to spot price
        strikes.sort(key=lambda x: abs(x['strikePrice'] - spot_price))

        # Get ATM and surrounding strikes
        atm_strikes = strikes[:num_strikes * 2 + 1]  # ATM + num_strikes on each side

        strike_analysis = []
        total_ce_oi = 0
        total_pe_oi = 0
        bullish_count = 0
        bearish_count = 0
        neutral_count = 0

        for strike in atm_strikes:
            strike_price = strike['strikePrice']

            ce_data = strike.get('CE', {})
            pe_data = strike.get('PE', {})

            ce_oi = ce_data.get('openInterest', 0)
            pe_oi = pe_data.get('openInterest', 0)
            ce_oi_change = ce_data.get('openInterestChange', 0)
            pe_oi_change = pe_data.get('openInterestChange', 0)
            ce_volume = ce_data.get('volume', 0)
            pe_volume = pe_data.get('volume', 0)

            total_ce_oi += ce_oi
            total_pe_oi += pe_oi

            # Calculate PCR for this strike
            pcr_oi = pe_oi / ce_oi if ce_oi > 0 else 0
            pcr_oi_change = pe_oi_change / ce_oi_change if ce_oi_change != 0 else 0
            pcr_volume = pe_volume / ce_volume if ce_volume > 0 else 0

            # Determine strike bias
            if pcr_oi > 1.2:
                strike_bias = 'BULLISH'
                bullish_count += 1
            elif pcr_oi < 0.8:
                strike_bias = 'BEARISH'
                bearish_count += 1
            else:
                strike_bias = 'NEUTRAL'
                neutral_count += 1

            strike_analysis.append({
                'strike': strike_price,
                'ce_oi': ce_oi,
                'pe_oi': pe_oi,
                'ce_oi_change': ce_oi_change,
                'pe_oi_change': pe_oi_change,
                'ce_volume': ce_volume,
                'pe_volume': pe_volume,
                'pcr_oi': round(pcr_oi, 2),
                'pcr_oi_change': round(pcr_oi_change, 2) if pcr_oi_change != 0 else 0,
                'pcr_volume': round(pcr_volume, 2),
                'bias': strike_bias
            })

        # Calculate zone PCR
        zone_pcr = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 0

        # Determine overall zone bias
        if bullish_count > bearish_count and zone_pcr > 1.0:
            zone_bias = 'BULLISH'
        elif bearish_count > bullish_count and zone_pcr < 1.0:
            zone_bias = 'BEARISH'
        else:
            zone_bias = 'NEUTRAL'

        summary = {
            'total_ce_oi': total_ce_oi,
            'total_pe_oi': total_pe_oi,
            'zone_pcr': round(zone_pcr, 2),
            'bullish_strikes': bullish_count,
            'bearish_strikes': bearish_count,
            'neutral_strikes': neutral_count,
            'zone_bias': zone_bias
        }

        return {
            'strikes': strike_analysis,
            'summary': summary
        }

    except Exception as e:
        print(f"Error calculating ATM zone bias: {e}")
        return {'strikes': [], 'summary': {}}


def format_number(num: float) -> str:
    """Format large numbers with K/M/B suffix"""
    if num >= 1_000_000_000:
        return f"{num / 1_000_000_000:.2f}B"
    elif num >= 1_000_000:
        return f"{num / 1_000_000:.2f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.2f}K"
    else:
        return f"{num:.0f}"


def get_bias_color(bias: str) -> str:
    """Get color for bias display"""
    if bias == 'BULLISH':
        return '#00ff00'
    elif bias == 'BEARISH':
        return '#ff0000'
    else:
        return '#ffff00'


def get_bias_emoji(bias: str) -> str:
    """Get emoji for bias display"""
    if bias == 'BULLISH':
        return '🟢'
    elif bias == 'BEARISH':
        return '🔴'
    else:
        return '🟡'
