"""
OI Winding & Unwinding Analysis Component for Streamlit
Institutional ATM ± 3 Strike Model for Market Bias Detection

Uses comprehensive analysis of:
- OI Winding/Unwinding
- Volume Analysis
- IV (Implied Volatility)
- Delta, Gamma, Theta, Vega (Greeks)
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import math
from config import COLORS, get_current_time_ist
from dhan_option_chain_analyzer import DhanOptionChainAnalyzer
from nse_options_helpers import calculate_greeks

def calculate_strike_strength(strike_data, option_type='CE'):
    """
    Calculate strength metrics for a strike

    Args:
        strike_data: Dictionary with OI, Volume, IV, Greeks data
        option_type: 'CE' or 'PE'

    Returns:
        Dictionary with strength scores
    """
    prefix = 'ce_' if option_type == 'CE' else 'pe_'

    # OI Winding/Unwinding Strength (based on OI change)
    oi_change = strike_data.get(f'{prefix}oi_change', 0)
    oi = strike_data.get(f'{prefix}oi', 1)
    oi_change_pct = (oi_change / oi * 100) if oi > 0 else 0

    # Winding = OI increase, Unwinding = OI decrease
    if oi_change_pct > 10:
        oi_strength = 2  # Strong winding
    elif oi_change_pct > 5:
        oi_strength = 1  # Moderate winding
    elif oi_change_pct < -10:
        oi_strength = -2  # Strong unwinding
    elif oi_change_pct < -5:
        oi_strength = -1  # Moderate unwinding
    else:
        oi_strength = 0  # Stable

    # Volume Strength
    volume = strike_data.get(f'{prefix}volume', 0)
    avg_volume = strike_data.get('avg_volume', 1)
    volume_ratio = volume / avg_volume if avg_volume > 0 else 0

    if volume_ratio > 1.5:
        volume_strength = 2
    elif volume_ratio > 1.2:
        volume_strength = 1
    else:
        volume_strength = 0

    # IV Strength (for fear/calm measurement)
    iv = strike_data.get(f'{prefix}iv', 0)
    iv_change = strike_data.get(f'{prefix}iv_change', 0)

    if iv_change > 5:
        iv_surge = 1  # IV rising = fear
    elif iv_change < -5:
        iv_drop = 1  # IV falling = calm
    else:
        iv_surge = 0
        iv_drop = 0

    # Delta Strength (directional probability)
    delta = abs(strike_data.get(f'{prefix}delta', 0))
    delta_strength = 2 if delta > 0.5 else (1 if delta > 0.3 else 0)

    # Gamma Level (speed of move)
    gamma = strike_data.get(f'{prefix}gamma', 0)
    gamma_level = 1 if 0.001 < gamma < 0.005 else 0

    # Theta Level (time decay)
    theta = abs(strike_data.get(f'{prefix}theta', 0))
    theta_high = 1 if theta > 10 else 0

    return {
        'oi_winding_strength': oi_strength if oi_change > 0 else 0,
        'oi_unwinding_strength': abs(oi_strength) if oi_change < 0 else 0,
        'volume_strength': volume_strength,
        'iv_surge': iv_surge,
        'iv_drop': iv_drop,
        'delta_strength': delta_strength,
        'gamma_level': gamma_level,
        'theta_high': theta_high,
        'oi_change_pct': oi_change_pct
    }

def calculate_bullish_score(strike_data):
    """
    Calculate Bullish Bias Score

    Bullish Conditions:
    - PE OI Winding ↑ (weight: 2)
    - CE OI Unwinding ↓ (weight: 2)
    - PE Volume ↑ (weight: 2)
    - CE IV ↓ (weight: 1)
    - PE Delta ↑ (weight: 2)
    - PE Gamma moderate-high (weight: 1)
    - CE Theta high (weight: 1)
    """
    pe_strength = calculate_strike_strength(strike_data, 'PE')
    ce_strength = calculate_strike_strength(strike_data, 'CE')

    score = 0
    score += pe_strength['oi_winding_strength'] * 2
    score += ce_strength['oi_unwinding_strength'] * 2
    score += pe_strength['volume_strength'] * 2
    score += ce_strength['iv_drop'] * 1
    score += pe_strength['delta_strength'] * 2
    score += pe_strength['gamma_level'] * 1
    score += ce_strength['theta_high'] * 1

    return score

def calculate_bearish_score(strike_data):
    """
    Calculate Bearish Bias Score

    Bearish Conditions:
    - CE OI Winding ↑ (weight: 2)
    - PE OI Unwinding ↓ (weight: 2)
    - CE Volume ↑ (weight: 2)
    - PE IV ↑ (weight: 1)
    - CE Delta ↑ (weight: 2)
    - CE Gamma moderate-high (weight: 1)
    - PE Theta high (weight: 1)
    """
    ce_strength = calculate_strike_strength(strike_data, 'CE')
    pe_strength = calculate_strike_strength(strike_data, 'PE')

    score = 0
    score += ce_strength['oi_winding_strength'] * 2
    score += pe_strength['oi_unwinding_strength'] * 2
    score += ce_strength['volume_strength'] * 2
    score += pe_strength['iv_surge'] * 1
    score += ce_strength['delta_strength'] * 2
    score += ce_strength['gamma_level'] * 1
    score += pe_strength['theta_high'] * 1

    return score

def calculate_sideways_score(strike_data):
    """
    Calculate Sideways/Range Score

    Sideways Conditions:
    - Both CE & PE OI Winding
    - Low Gamma
    - Stable IV
    - Volume balanced
    """
    ce_strength = calculate_strike_strength(strike_data, 'CE')
    pe_strength = calculate_strike_strength(strike_data, 'PE')

    score = 0

    # Both sides winding
    if ce_strength['oi_winding_strength'] > 0 and pe_strength['oi_winding_strength'] > 0:
        score += ce_strength['oi_winding_strength'] + pe_strength['oi_winding_strength']

    # Low gamma = low movement
    if ce_strength['gamma_level'] == 0 and pe_strength['gamma_level'] == 0:
        score += 2

    # Stable IV
    if ce_strength['iv_surge'] == 0 and pe_strength['iv_surge'] == 0:
        score += 1

    return score

def calculate_reversal_score(strike_data):
    """
    Calculate Reversal Score

    Reversal Conditions:
    - Both CE & PE OI Unwinding
    - Falling IV
    - Low Volume
    """
    ce_strength = calculate_strike_strength(strike_data, 'CE')
    pe_strength = calculate_strike_strength(strike_data, 'PE')

    score = 0

    # Both sides unwinding
    score += ce_strength['oi_unwinding_strength']
    score += pe_strength['oi_unwinding_strength']

    # Falling IV
    score += ce_strength['iv_drop']
    score += pe_strength['iv_drop']

    # Low volume
    if ce_strength['volume_strength'] == 0 and pe_strength['volume_strength'] == 0:
        score += 1

    return score

def fetch_atm_strikes_with_greeks(symbol, atm_range=3):
    """
    Fetch ATM ± 3 strikes with Greeks calculation

    Args:
        symbol: Trading symbol (NIFTY, SENSEX, etc.)
        atm_range: Number of strikes above/below ATM (default: 3)

    Returns:
        Dictionary with strike data including Greeks
    """
    analyzer = DhanOptionChainAnalyzer()
    oc_data = analyzer.fetch_option_chain(symbol)

    if not oc_data['success']:
        return oc_data

    try:
        records = oc_data['records']
        spot_price = oc_data['spot_price']
        current_expiry = oc_data['current_expiry']

        # Strike interval
        strike_intervals = {
            'NIFTY': 50,
            'BANKNIFTY': 100,
            'FINNIFTY': 50,
            'SENSEX': 100
        }
        strike_interval = strike_intervals.get(symbol, 50)

        # Find ATM strike
        atm_strike = round(spot_price / strike_interval) * strike_interval

        # Generate ATM ± 3 strikes
        target_strikes = [
            atm_strike + (i * strike_interval)
            for i in range(-atm_range, atm_range + 1)
        ]

        # Parse option chain data
        strike_data_map = {}

        # Calculate time to expiry (T) - assuming weekly expiry ~5 days
        T = 5 / 365  # Time to expiry in years
        r = 0.06  # Risk-free rate

        # Handle dict format (most common)
        if isinstance(records, dict):
            for strike_key, strike_record in records.items():
                if isinstance(strike_record, dict):
                    strike_price = strike_record.get('strikePrice', strike_record.get('strike_price', 0))

                    if strike_price in target_strikes:
                        ce_data = strike_record.get('CE', {})
                        pe_data = strike_record.get('PE', {})

                        # Get basic data
                        ce_oi = ce_data.get('openInterest', ce_data.get('oi', 0))
                        pe_oi = pe_data.get('openInterest', pe_data.get('oi', 0))
                        ce_oi_change = ce_data.get('changeinOpenInterest', ce_data.get('oi_change', 0))
                        pe_oi_change = pe_data.get('changeinOpenInterest', pe_data.get('oi_change', 0))
                        ce_volume = ce_data.get('totalTradedVolume', ce_data.get('volume', 0))
                        pe_volume = pe_data.get('totalTradedVolume', pe_data.get('volume', 0))
                        ce_iv = ce_data.get('impliedVolatility', 0)
                        pe_iv = pe_data.get('impliedVolatility', 0)

                        # Calculate Greeks for CE
                        ce_greeks = {'delta': 0, 'gamma': 0, 'vega': 0, 'theta': 0}
                        if ce_iv > 0:
                            try:
                                delta, gamma, vega, theta, rho = calculate_greeks(
                                    'CE', spot_price, strike_price, T, r, ce_iv / 100
                                )
                                ce_greeks = {'delta': delta, 'gamma': gamma, 'vega': vega, 'theta': theta}
                            except:
                                pass

                        # Calculate Greeks for PE
                        pe_greeks = {'delta': 0, 'gamma': 0, 'vega': 0, 'theta': 0}
                        if pe_iv > 0:
                            try:
                                delta, gamma, vega, theta, rho = calculate_greeks(
                                    'PE', spot_price, strike_price, T, r, pe_iv / 100
                                )
                                pe_greeks = {'delta': delta, 'gamma': gamma, 'vega': vega, 'theta': theta}
                            except:
                                pass

                        strike_data_map[strike_price] = {
                            'strike_price': strike_price,
                            'ce_oi': ce_oi,
                            'pe_oi': pe_oi,
                            'ce_oi_change': ce_oi_change,
                            'pe_oi_change': pe_oi_change,
                            'ce_volume': ce_volume,
                            'pe_volume': pe_volume,
                            'ce_iv': ce_iv,
                            'pe_iv': pe_iv,
                            'ce_iv_change': 0,  # Would need historical data
                            'pe_iv_change': 0,  # Would need historical data
                            'ce_delta': ce_greeks['delta'],
                            'pe_delta': pe_greeks['delta'],
                            'ce_gamma': ce_greeks['gamma'],
                            'pe_gamma': pe_greeks['gamma'],
                            'ce_vega': ce_greeks['vega'],
                            'pe_vega': pe_greeks['vega'],
                            'ce_theta': ce_greeks['theta'],
                            'pe_theta': pe_greeks['theta'],
                            'avg_volume': (ce_volume + pe_volume) / 2 if (ce_volume + pe_volume) > 0 else 1
                        }

        # Calculate bias scores for each strike
        atm_strikes_data = []

        for strike_price in target_strikes:
            strike_offset = int((strike_price - atm_strike) / strike_interval)

            if strike_price in strike_data_map:
                data = strike_data_map[strike_price]

                # Calculate all bias scores
                bullish_score = calculate_bullish_score(data)
                bearish_score = calculate_bearish_score(data)
                sideways_score = calculate_sideways_score(data)
                reversal_score = calculate_reversal_score(data)

                atm_strikes_data.append({
                    'strike_price': strike_price,
                    'strike_offset': strike_offset,
                    **data,
                    'bullish_score': bullish_score,
                    'bearish_score': bearish_score,
                    'sideways_score': sideways_score,
                    'reversal_score': reversal_score
                })
            else:
                # No data for this strike
                atm_strikes_data.append({
                    'strike_price': strike_price,
                    'strike_offset': strike_offset,
                    'ce_oi': 0,
                    'pe_oi': 0,
                    'ce_oi_change': 0,
                    'pe_oi_change': 0,
                    'ce_volume': 0,
                    'pe_volume': 0,
                    'ce_iv': 0,
                    'pe_iv': 0,
                    'ce_delta': 0,
                    'pe_delta': 0,
                    'ce_gamma': 0,
                    'pe_gamma': 0,
                    'ce_theta': 0,
                    'pe_theta': 0,
                    'bullish_score': 0,
                    'bearish_score': 0,
                    'sideways_score': 0,
                    'reversal_score': 0
                })

        # Sort by strike offset
        atm_strikes_data.sort(key=lambda x: x['strike_offset'])

        return {
            'success': True,
            'symbol': symbol,
            'spot_price': spot_price,
            'atm_strike': atm_strike,
            'expiry': current_expiry,
            'strike_interval': strike_interval,
            'atm_strikes_data': atm_strikes_data,
            'timestamp': get_current_time_ist()
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def calculate_overall_bias(atm_strikes_data):
    """
    Calculate overall market bias from all 7 strikes

    Returns:
        Dictionary with total scores and final bias
    """
    if not atm_strikes_data:
        return {
            'bullish_total': 0,
            'bearish_total': 0,
            'sideways_total': 0,
            'reversal_total': 0,
            'final_bias': 'NEUTRAL',
            'bullish_pct': 0,
            'bearish_pct': 0,
            'sideways_pct': 0,
            'reversal_pct': 0
        }

    # Sum scores across all strikes
    bullish_total = sum(strike['bullish_score'] for strike in atm_strikes_data)
    bearish_total = sum(strike['bearish_score'] for strike in atm_strikes_data)
    sideways_total = sum(strike['sideways_score'] for strike in atm_strikes_data)
    reversal_total = sum(strike['reversal_score'] for strike in atm_strikes_data)

    # Calculate total
    total_score = bullish_total + bearish_total + sideways_total + reversal_total
    if total_score == 0:
        total_score = 1  # Avoid division by zero

    # Calculate percentages
    bullish_pct = (bullish_total / total_score) * 100
    bearish_pct = (bearish_total / total_score) * 100
    sideways_pct = (sideways_total / total_score) * 100
    reversal_pct = (reversal_total / total_score) * 100

    # Determine final bias
    max_score = max(bullish_total, bearish_total, sideways_total, reversal_total)

    if max_score == bullish_total:
        final_bias = "BULLISH"
    elif max_score == bearish_total:
        final_bias = "BEARISH"
    elif max_score == sideways_total:
        final_bias = "SIDEWAYS/RANGE"
    elif max_score == reversal_total:
        final_bias = "REVERSAL"
    else:
        final_bias = "NEUTRAL"

    return {
        'bullish_total': bullish_total,
        'bearish_total': bearish_total,
        'sideways_total': sideways_total,
        'reversal_total': reversal_total,
        'final_bias': final_bias,
        'bullish_pct': round(bullish_pct, 2),
        'bearish_pct': round(bearish_pct, 2),
        'sideways_pct': round(sideways_pct, 2),
        'reversal_pct': round(reversal_pct, 2)
    }

def format_number(value, decimals=0):
    """Format number with commas and specified decimals"""
    if pd.isna(value) or value == 0:
        return "-"
    if decimals > 0:
        return f"{value:,.{decimals}f}"
    return f"{int(value):,}"

def display_oi_winding_table(symbol, strike_data):
    """
    Display OI Winding/Unwinding Analysis table

    Args:
        symbol: Trading symbol
        strike_data: Dictionary with strike data and scores
    """
    if not strike_data or not strike_data.get('success'):
        st.error(f"❌ Failed to load data for {symbol}")
        if strike_data:
            st.caption(f"Error: {strike_data.get('error', 'Unknown error')}")
        return

    # Extract data
    spot_price = strike_data.get('spot_price', 0)
    atm_strike = strike_data.get('atm_strike', 0)
    atm_strikes_data = strike_data.get('atm_strikes_data', [])
    timestamp = strike_data.get('timestamp', datetime.now())

    # Header
    st.markdown(f"### 🔥 {symbol} - Institutional OI Winding/Unwinding Analysis")
    st.caption("ATM ± 3 Strike Model with Greeks Analysis")

    # Info row
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        st.metric("Spot Price", f"₹{spot_price:,.2f}")
    with col2:
        st.metric("ATM Strike", f"₹{atm_strike:,.0f}")
    with col3:
        st.metric("Strikes Analyzed", f"{len(atm_strikes_data)} (ATM ±3)")
    with col4:
        if isinstance(timestamp, str):
            st.caption(f"⏱️ {timestamp}")
        else:
            st.caption(f"⏱️ {timestamp.strftime('%I:%M:%S %p')}")

    st.markdown("---")

    # Calculate overall bias
    overall_bias = calculate_overall_bias(atm_strikes_data)

    # Display overall bias with large metrics
    st.markdown("### 📊 Market Bias Summary")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "🟢 Bullish Score",
            overall_bias['bullish_total'],
            f"{overall_bias['bullish_pct']:.1f}%"
        )

    with col2:
        st.metric(
            "🔴 Bearish Score",
            overall_bias['bearish_total'],
            f"{overall_bias['bearish_pct']:.1f}%"
        )

    with col3:
        st.metric(
            "🟡 Sideways Score",
            overall_bias['sideways_total'],
            f"{overall_bias['sideways_pct']:.1f}%"
        )

    with col4:
        st.metric(
            "🔵 Reversal Score",
            overall_bias['reversal_total'],
            f"{overall_bias['reversal_pct']:.1f}%"
        )

    # Final Bias - Large display
    st.markdown("---")
    bias_color = {
        'BULLISH': '🟢',
        'BEARISH': '🔴',
        'SIDEWAYS/RANGE': '🟡',
        'REVERSAL': '🔵',
        'NEUTRAL': '⚪'
    }.get(overall_bias['final_bias'], '⚪')

    st.markdown(f"### {bias_color} **FINAL MARKET BIAS: {overall_bias['final_bias']}**")

    st.markdown("---")

    # Detailed Strike Table
    st.markdown("### 📋 Detailed Strike Analysis")

    if not atm_strikes_data:
        st.warning(f"⚠️ No strike data available for {symbol}")
        return

    df = pd.DataFrame(atm_strikes_data)

    # Create display DataFrame
    display_df = pd.DataFrame({
        'Strike': df['strike_price'].apply(lambda x: f"₹{x:,.0f}"),
        'Offset': df['strike_offset'].apply(lambda x: f"ATM{x:+d}" if x != 0 else "ATM"),
        'CE OI': df['ce_oi'].apply(lambda x: format_number(x, 0)),
        'PE OI': df['pe_oi'].apply(lambda x: format_number(x, 0)),
        'CE OI Δ': df['ce_oi_change'].apply(lambda x: format_number(x, 0)),
        'PE OI Δ': df['pe_oi_change'].apply(lambda x: format_number(x, 0)),
        'CE Vol': df['ce_volume'].apply(lambda x: format_number(x, 0)),
        'PE Vol': df['pe_volume'].apply(lambda x: format_number(x, 0)),
        'CE IV': df['ce_iv'].apply(lambda x: format_number(x, 2)),
        'PE IV': df['pe_iv'].apply(lambda x: format_number(x, 2)),
        'CE Δ': df['ce_delta'].apply(lambda x: format_number(x, 4)),
        'PE Δ': df['pe_delta'].apply(lambda x: format_number(x, 4)),
        'CE Γ': df['ce_gamma'].apply(lambda x: format_number(x, 4)),
        'PE Γ': df['pe_gamma'].apply(lambda x: format_number(x, 4)),
        'CE Θ': df['ce_theta'].apply(lambda x: format_number(x, 2)),
        'PE Θ': df['pe_theta'].apply(lambda x: format_number(x, 2)),
        '🟢 Bull': df['bullish_score'],
        '🔴 Bear': df['bearish_score'],
        '🟡 Side': df['sideways_score'],
        '🔵 Rev': df['reversal_score']
    })

    # Display table with colors
    st.dataframe(
        display_df,
        use_container_width=True,
        height=400
    )

    # Explanation section
    with st.expander("📖 How to Read This Analysis"):
        st.markdown("""
        ### Understanding the Bias Scores

        **🟢 Bullish Score:**
        - PE OI Winding ↑ (Puts being bought = support)
        - CE OI Unwinding ↓ (Calls being closed = less resistance)
        - High PE Volume (Strong put buying)
        - CE IV Drop (Call sellers confident)
        - High PE Delta (Directional strength)

        **🔴 Bearish Score:**
        - CE OI Winding ↑ (Calls being bought = resistance)
        - PE OI Unwinding ↓ (Puts being closed = less support)
        - High CE Volume (Strong call selling)
        - PE IV Rise (Fear in puts)
        - High CE Delta (Downside probability)

        **🟡 Sideways Score:**
        - Both CE & PE OI rising (Fight zone)
        - Low Gamma (Market won't move fast)
        - Stable IV (No directional fear)

        **🔵 Reversal Score:**
        - Both CE & PE OI falling (Profit booking)
        - Falling IV (Uncertainty reducing)
        - Low Volume (Trend exhaustion)

        ### Greeks Explained
        - **Delta (Δ):** Directional probability (0-1 for CE, 0 to -1 for PE)
        - **Gamma (Γ):** Rate of change of Delta (speed of move)
        - **Theta (Θ):** Time decay per day
        - **Vega (V):** Sensitivity to IV changes

        ### OI Interpretation
        - **OI Winding:** Open Interest increasing = New positions building
        - **OI Unwinding:** Open Interest decreasing = Positions closing
        """)

def render_oi_winding_unwinding_analysis():
    """Main function to render OI Winding/Unwinding Analysis"""
    st.markdown("## 🔥 OI Winding & Unwinding Bias Analysis")
    st.markdown("**Institutional ATM ± 3 Strike Model with Complete Greeks**")
    st.markdown("---")

    # Symbol selection
    symbols = ['NIFTY', 'SENSEX', 'BANKNIFTY', 'FINNIFTY']

    # Create tabs for each symbol
    tabs = st.tabs([f"📊 {symbol}" for symbol in symbols])

    for idx, symbol in enumerate(symbols):
        with tabs[idx]:
            # Add refresh button
            col1, col2 = st.columns([1, 3])
            with col1:
                refresh_btn = st.button(f"🔄 Refresh {symbol}", key=f"refresh_oi_{symbol}")

            # Check if data exists in session state
            session_key = f"oi_winding_{symbol}"

            # Load data on refresh or if not in session
            if refresh_btn or session_key not in st.session_state:
                with st.spinner(f"📡 Fetching OI data with Greeks for {symbol}..."):
                    strike_data = fetch_atm_strikes_with_greeks(symbol, atm_range=3)

                    if strike_data.get('success'):
                        st.session_state[session_key] = strike_data
                        st.success(f"✅ Data loaded for {symbol}")
                    else:
                        st.error(f"❌ Failed to fetch data: {strike_data.get('error', 'Unknown error')}")

            # Display the analysis
            if session_key in st.session_state:
                display_oi_winding_table(symbol, st.session_state[session_key])
            else:
                st.info(f"ℹ️ Click 'Refresh {symbol}' to load OI Winding/Unwinding Analysis")
