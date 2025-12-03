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
from supabase_manager import get_supabase_manager
from dhan_option_chain_analyzer import DhanOptionChainAnalyzer


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
    Fetch option chain data from Dhan API using DhanOptionChainAnalyzer

    Args:
        underlying: Underlying symbol ('NIFTY', 'BANKNIFTY', or 'SENSEX')

    Returns:
        Dictionary with option chain data or None if failed
    """
    try:
        analyzer = DhanOptionChainAnalyzer()
        result = analyzer.fetch_option_chain(underlying)

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
    Calculate PCR metrics using DhanOptionChainAnalyzer

    Args:
        underlying: Underlying symbol ('NIFTY', 'BANKNIFTY', or 'SENSEX')

    Returns:
        Dictionary with PCR metrics
    """
    try:
        analyzer = DhanOptionChainAnalyzer()
        pcr_result = analyzer.calculate_pcr(underlying)

        if pcr_result.get('success'):
            return {
                'pcr_oi': round(pcr_result.get('pcr_oi', 0), 4),
                'pcr_oi_change': round(pcr_result.get('pcr_change_oi', 0), 4),
                'pcr_volume': round(pcr_result.get('pcr_volume', 0), 4),
                'total_ce_oi': pcr_result.get('total_ce_oi', 0),
                'total_pe_oi': pcr_result.get('total_pe_oi', 0),
                'total_ce_volume': pcr_result.get('total_ce_volume', 0),
                'total_pe_volume': pcr_result.get('total_pe_volume', 0),
                'bias': pcr_result.get('overall_bias', 'NEUTRAL')
            }
        else:
            print(f"Failed to calculate PCR for {underlying}: {pcr_result.get('error')}")
            return None

    except Exception as e:
        print(f"Error calculating PCR metrics: {e}")
        return None


def get_atm_zone_bias(underlying: str, num_strikes: int = 5) -> Dict:
    """
    Calculate ATM zone bias using DhanOptionChainAnalyzer

    Args:
        underlying: Underlying symbol ('NIFTY', 'BANKNIFTY', or 'SENSEX')
        num_strikes: Number of strikes above and below ATM to analyze

    Returns:
        Dictionary with ATM zone analysis
    """
    try:
        analyzer = DhanOptionChainAnalyzer()
        atm_result = analyzer.calculate_atm_zone_bias(underlying, atm_range=num_strikes)

        if atm_result.get('success'):
            atm_zone_data = atm_result.get('atm_zone_data', [])

            # Convert to expected format
            strike_analysis = []
            total_ce_oi = 0
            total_pe_oi = 0
            bullish_count = 0
            bearish_count = 0
            neutral_count = 0

            for strike_data in atm_zone_data:
                strike_analysis.append({
                    'strike': strike_data['strike_price'],
                    'ce_oi': strike_data['ce_oi'],
                    'pe_oi': strike_data['pe_oi'],
                    'ce_oi_change': strike_data['ce_oi_change'],
                    'pe_oi_change': strike_data['pe_oi_change'],
                    'ce_volume': strike_data['ce_volume'],
                    'pe_volume': strike_data['pe_volume'],
                    'pcr_oi': strike_data['pcr_oi'],
                    'pcr_oi_change': strike_data['pcr_oi_change'],
                    'pcr_volume': strike_data['pcr_volume'],
                    'bias': strike_data['strike_bias']
                })

                total_ce_oi += strike_data['ce_oi']
                total_pe_oi += strike_data['pe_oi']

                if strike_data['strike_bias'] == 'BULLISH':
                    bullish_count += 1
                elif strike_data['strike_bias'] == 'BEARISH':
                    bearish_count += 1
                else:
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
        else:
            print(f"Failed to calculate ATM zone bias for {underlying}: {atm_result.get('error')}")
            return None

    except Exception as e:
        print(f"Error calculating ATM zone bias: {e}")
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


def get_pcr_from_supabase(underlying: str) -> Optional[Dict]:
    """
    Get PCR metrics from the latest option chain snapshot in Supabase

    Args:
        underlying: Underlying symbol ('NIFTY', 'BANKNIFTY', 'SENSEX')

    Returns:
        Dictionary with PCR metrics or None if not available
    """
    try:
        supabase = get_supabase_manager()

        if not supabase.is_enabled():
            print("Supabase not enabled, cannot fetch PCR data")
            return None

        # Get latest option chain snapshot
        response = (
            supabase.client.table('option_chain_snapshots')
            .select('*')
            .eq('symbol', underlying)
            .order('timestamp', desc=True)
            .limit(1)
            .execute()
        )

        if response.data and len(response.data) > 0:
            snapshot = response.data[0]

            # Extract PCR metrics from snapshot
            total_ce_oi = snapshot.get('total_ce_oi', 0)
            total_pe_oi = snapshot.get('total_pe_oi', 0)

            # Validate data - if both OI values are 0, data is invalid
            if total_ce_oi == 0 and total_pe_oi == 0:
                print(f"⚠️ Invalid PCR data in Supabase (all zeros) for {underlying}, will try API fallback")
                return None

            pcr_metrics = {
                'pcr_oi': snapshot.get('pcr_oi', 0),
                'pcr_oi_change': snapshot.get('pcr_oi_change', 0),
                'pcr_volume': snapshot.get('pcr_volume', 0),
                'total_ce_oi': total_ce_oi,
                'total_pe_oi': total_pe_oi,
                'total_ce_volume': snapshot.get('data', {}).get('total_ce_volume', 0),
                'total_pe_volume': snapshot.get('data', {}).get('total_pe_volume', 0),
                'bias': snapshot.get('overall_bias', 'NEUTRAL'),
                'timestamp': snapshot.get('timestamp', '')
            }

            print(f"✅ Fetched PCR data from Supabase for {underlying}")
            return pcr_metrics
        else:
            print(f"⚠️ No PCR data found in Supabase for {underlying}")
            return None

    except Exception as e:
        print(f"❌ Error fetching PCR data from Supabase: {e}")
        return None


def get_atm_zone_from_supabase(underlying: str, num_strikes: int = 11) -> Optional[Dict]:
    """
    Get ATM zone bias data from Supabase

    Args:
        underlying: Underlying symbol ('NIFTY', 'BANKNIFTY', 'SENSEX')
        num_strikes: Number of strikes to retrieve (default 11 for ATM ±5)

    Returns:
        Dictionary with ATM zone analysis or None if not available
    """
    try:
        supabase = get_supabase_manager()

        if not supabase.is_enabled():
            print("Supabase not enabled, cannot fetch ATM zone data")
            return None

        # Get latest ATM zone data
        df = supabase.get_latest_atm_zone_bias(underlying, limit=num_strikes)

        if df is not None and not df.empty:
            # Calculate summary first to validate data
            total_ce_oi = df['ce_oi'].sum()
            total_pe_oi = df['pe_oi'].sum()

            # Validate data - if both OI values are 0, data is invalid
            if total_ce_oi == 0 and total_pe_oi == 0:
                print(f"⚠️ Invalid ATM zone data in Supabase (all zeros) for {underlying}, will try API fallback")
                return None

            # Convert DataFrame to the expected format
            strike_analysis = []

            for _, row in df.iterrows():
                strike_analysis.append({
                    'strike': row['strike_price'],
                    'ce_oi': row['ce_oi'],
                    'pe_oi': row['pe_oi'],
                    'ce_oi_change': row['ce_oi_change'],
                    'pe_oi_change': row['pe_oi_change'],
                    'ce_volume': row['ce_volume'],
                    'pe_volume': row['pe_volume'],
                    'pcr_oi': row['pcr_oi'],
                    'pcr_oi_change': row['pcr_oi_change'],
                    'pcr_volume': row['pcr_volume'],
                    'bias': row['strike_bias']
                })

            zone_pcr = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 0

            bullish_count = len(df[df['strike_bias'] == 'BULLISH'])
            bearish_count = len(df[df['strike_bias'] == 'BEARISH'])
            neutral_count = len(df[df['strike_bias'] == 'NEUTRAL'])

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
                'zone_bias': zone_bias,
                'timestamp': df['timestamp'].iloc[0] if 'timestamp' in df.columns else ''
            }

            print(f"✅ Fetched ATM zone data from Supabase for {underlying}")
            return {
                'strikes': strike_analysis,
                'summary': summary
            }
        else:
            print(f"⚠️ No ATM zone data found in Supabase for {underlying}")
            return None

    except Exception as e:
        print(f"❌ Error fetching ATM zone data from Supabase: {e}")
        return None
