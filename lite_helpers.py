"""
Lite Helpers - Minimal helper functions for the lite trading app
Provides essential data fetching and bias calculation support
"""

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz
from typing import Dict, Tuple, Optional
import time

# Import from existing modules
from config import IST
from market_hours_scheduler import is_market_open
# Use the same helper functions as the main option chain analysis
from nse_options_helpers import fetch_option_chain_data

# NSE Instruments configuration (required by helper functions)
NSE_INSTRUMENTS = {
    'indices': {
        'NIFTY': {'lot_size': 75, 'zone_size': 20, 'atm_range': 200},
        'BANKNIFTY': {'lot_size': 25, 'zone_size': 100, 'atm_range': 500},
        'SENSEX': {'lot_size': 10, 'zone_size': 50, 'atm_range': 300},
    },
    'stocks': {}
}


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


def fetch_dhan_option_chain(underlying: str) -> Optional[Dict]:
    """
    Fetch option chain data from Dhan API using nse_options_helpers

    Args:
        underlying: Underlying symbol ('NIFTY', 'BANKNIFTY', or 'SENSEX')

    Returns:
        Dictionary with option chain data or None if failed
    """
    try:
        # Use the same fetch function as the main option chain analysis
        result = fetch_option_chain_data(underlying, NSE_INSTRUMENTS)

        if result.get('success'):
            return result
        else:
            print(f"Failed to fetch option chain for {underlying}: {result.get('error')}")
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


def calculate_pcr_metrics(underlying: str) -> Dict:
    """
    Calculate PCR metrics using nse_options_helpers

    Args:
        underlying: Underlying symbol ('NIFTY', 'BANKNIFTY', or 'SENSEX')

    Returns:
        Dictionary with PCR metrics
    """
    try:
        # Fetch option chain data using helper function
        oc_data = fetch_option_chain_data(underlying, NSE_INSTRUMENTS)

        if not oc_data.get('success'):
            print(f"Failed to fetch option chain for PCR calculation: {oc_data.get('error')}")
            return None

        # Extract totals from the result
        total_ce_oi = oc_data.get('total_ce_oi', 0)
        total_pe_oi = oc_data.get('total_pe_oi', 0)
        total_ce_change = oc_data.get('total_ce_change', 0)
        total_pe_change = oc_data.get('total_pe_change', 0)

        # Calculate volumes from records
        records = oc_data.get('records', [])
        total_ce_volume = sum(item['CE']['totalTradedVolume'] for item in records if 'CE' in item)
        total_pe_volume = sum(item['PE']['totalTradedVolume'] for item in records if 'PE' in item)

        # Calculate PCR ratios
        pcr_oi = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 0
        pcr_change_oi = abs(total_pe_change) / abs(total_ce_change) if total_ce_change != 0 else 0
        pcr_volume = total_pe_volume / total_ce_volume if total_ce_volume > 0 else 0

        # Determine bias based on PCR (weighted approach)
        # PCR OI weight: 3, PCR Change OI weight: 5, PCR Volume weight: 2
        bias_score = 0

        if pcr_oi > 1.2:
            bias_score += 3
        elif pcr_oi < 0.8:
            bias_score -= 3

        if pcr_change_oi > 1.2:
            bias_score += 5
        elif pcr_change_oi < 0.8:
            bias_score -= 5

        if pcr_volume > 1.2:
            bias_score += 2
        elif pcr_volume < 0.8:
            bias_score -= 2

        # Determine overall bias
        if bias_score >= 5:
            overall_bias = "BULLISH"
        elif bias_score <= -5:
            overall_bias = "BEARISH"
        else:
            overall_bias = "NEUTRAL"

        return {
            'pcr_oi': round(pcr_oi, 4),
            'pcr_oi_change': round(pcr_change_oi, 4),
            'pcr_volume': round(pcr_volume, 4),
            'total_ce_oi': total_ce_oi,
            'total_pe_oi': total_pe_oi,
            'total_ce_volume': total_ce_volume,
            'total_pe_volume': total_pe_volume,
            'bias': overall_bias
        }

    except Exception as e:
        print(f"Error calculating PCR metrics: {e}")
        import traceback
        print(traceback.format_exc())
        return None


def get_atm_zone_bias(underlying: str, num_strikes: int = 5) -> Dict:
    """
    Calculate ATM zone bias using nse_options_helpers

    Args:
        underlying: Underlying symbol ('NIFTY', 'BANKNIFTY', or 'SENSEX')
        num_strikes: Number of strikes above and below ATM to analyze

    Returns:
        Dictionary with ATM zone analysis
    """
    try:
        # Fetch option chain data using helper function
        oc_data = fetch_option_chain_data(underlying, NSE_INSTRUMENTS)

        if not oc_data.get('success'):
            print(f"Failed to fetch option chain for ATM zone bias: {oc_data.get('error')}")
            return None

        records = oc_data.get('records', [])
        spot_price = oc_data.get('spot', 0)

        # Strike interval based on symbol
        strike_intervals = {
            'NIFTY': 50,
            'BANKNIFTY': 100,
            'SENSEX': 100
        }
        strike_interval = strike_intervals.get(underlying, 50)

        # Find ATM strike (round spot price to nearest strike interval)
        atm_strike = round(spot_price / strike_interval) * strike_interval

        # Generate ATM ±num_strikes strikes
        target_strikes = [
            atm_strike + (i * strike_interval)
            for i in range(-num_strikes, num_strikes + 1)
        ]

        # Parse option chain data and extract strike-wise data
        strike_data_map = {}

        for record in records:
            # Both CE and PE should have the same strike price
            if 'CE' in record and 'PE' in record:
                strike_price = record['CE'].get('strikePrice')

                if strike_price in target_strikes:
                    ce_data = record['CE']
                    pe_data = record['PE']

                    strike_data_map[strike_price] = {
                        'ce_oi': ce_data.get('openInterest', 0),
                        'ce_oi_change': ce_data.get('changeinOpenInterest', 0),
                        'ce_volume': ce_data.get('totalTradedVolume', 0),
                        'pe_oi': pe_data.get('openInterest', 0),
                        'pe_oi_change': pe_data.get('changeinOpenInterest', 0),
                        'pe_volume': pe_data.get('totalTradedVolume', 0)
                    }

        # Calculate PCR for each strike and prepare result
        strike_analysis = []
        total_ce_oi = 0
        total_pe_oi = 0
        bullish_count = 0
        bearish_count = 0
        neutral_count = 0

        for strike_price in target_strikes:
            if strike_price in strike_data_map:
                data = strike_data_map[strike_price]

                # Calculate strike-wise PCR
                pcr_oi = data['pe_oi'] / data['ce_oi'] if data['ce_oi'] > 0 else 0
                pcr_oi_change = data['pe_oi_change'] / data['ce_oi_change'] if data['ce_oi_change'] != 0 else 0
                pcr_volume = data['pe_volume'] / data['ce_volume'] if data['ce_volume'] > 0 else 0

                # Determine strike bias (weighted approach)
                score = 0
                if pcr_oi > 1.2:
                    score += 3
                elif pcr_oi < 0.8:
                    score -= 3

                if pcr_oi_change > 1.2:
                    score += 5
                elif pcr_oi_change < 0.8:
                    score -= 5

                if score >= 5:
                    strike_bias = "BULLISH"
                    bullish_count += 1
                elif score <= -5:
                    strike_bias = "BEARISH"
                    bearish_count += 1
                else:
                    strike_bias = "NEUTRAL"
                    neutral_count += 1

                strike_analysis.append({
                    'strike': strike_price,
                    'ce_oi': data['ce_oi'],
                    'pe_oi': data['pe_oi'],
                    'ce_oi_change': data['ce_oi_change'],
                    'pe_oi_change': data['pe_oi_change'],
                    'ce_volume': data['ce_volume'],
                    'pe_volume': data['pe_volume'],
                    'pcr_oi': round(pcr_oi, 4),
                    'pcr_oi_change': round(pcr_oi_change, 4),
                    'pcr_volume': round(pcr_volume, 4),
                    'bias': strike_bias
                })

                total_ce_oi += data['ce_oi']
                total_pe_oi += data['pe_oi']
            else:
                # No data for this strike
                strike_analysis.append({
                    'strike': strike_price,
                    'ce_oi': 0,
                    'pe_oi': 0,
                    'ce_oi_change': 0,
                    'pe_oi_change': 0,
                    'ce_volume': 0,
                    'pe_volume': 0,
                    'pcr_oi': 0,
                    'pcr_oi_change': 0,
                    'pcr_volume': 0,
                    'bias': 'NEUTRAL'
                })
                neutral_count += 1

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
            'zone_pcr': round(zone_pcr, 4),
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
        import traceback
        print(traceback.format_exc())
        return None


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
