import streamlit as st
import time
from datetime import datetime
import pandas as pd
import numpy as np
import math
from scipy.stats import norm
from pytz import timezone as pytz_timezone
import plotly.graph_objects as go
import io
import requests

# Import modules
from config import *
from market_data import *
from market_hours_scheduler import scheduler, is_within_trading_hours, should_run_app
from signal_manager import SignalManager
from strike_calculator import calculate_strike, calculate_levels
from trade_executor import TradeExecutor
from telegram_alerts import TelegramBot, send_test_message
from dhan_api import check_dhan_connection
from bias_analysis import BiasAnalysisPro
from option_chain_analysis import OptionChainAnalyzer
from nse_options_helpers import *
from advanced_chart_analysis import AdvancedChartAnalysis
from overall_market_sentiment import render_overall_market_sentiment, calculate_overall_sentiment
from data_cache_manager import (
    get_cache_manager,
    preload_all_data,
    get_cached_nifty_data,
    get_cached_sensex_data,
    get_cached_bias_analysis_results
)
from vob_signal_generator import VOBSignalGenerator
from htf_sr_signal_generator import HTFSRSignalGenerator

# ═══════════════════════════════════════════════════════════════════════
# PAGE CONFIG & PERFORMANCE OPTIMIZATION
# ═══════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="NIFTY/SENSEX Trader",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Performance optimization: Reduce widget refresh overhead
# This improves app responsiveness and reduces lag
if 'performance_mode' not in st.session_state:
    st.session_state.performance_mode = True

# ═══════════════════════════════════════════════════════════════════════
# INITIALIZE SESSION STATE
# ═══════════════════════════════════════════════════════════════════════

if 'signal_manager' not in st.session_state:
    st.session_state.signal_manager = SignalManager()

if 'vob_signal_generator' not in st.session_state:
    st.session_state.vob_signal_generator = VOBSignalGenerator(proximity_threshold=8.0)

if 'active_vob_signals' not in st.session_state:
    st.session_state.active_vob_signals = []

if 'last_vob_check_time' not in st.session_state:
    st.session_state.last_vob_check_time = 0

if 'htf_sr_signal_generator' not in st.session_state:
    st.session_state.htf_sr_signal_generator = HTFSRSignalGenerator(proximity_threshold=8.0)

if 'active_htf_sr_signals' not in st.session_state:
    st.session_state.active_htf_sr_signals = []

if 'last_htf_sr_check_time' not in st.session_state:
    st.session_state.last_htf_sr_check_time = 0

if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

if 'active_setup_id' not in st.session_state:
    st.session_state.active_setup_id = None

if 'active_tab' not in st.session_state:
    st.session_state.active_tab = 0

# Lazy initialization - only create these objects when needed (on tab access)
# This significantly reduces initial load time
def get_bias_analyzer():
    """Lazy load bias analyzer"""
    if 'bias_analyzer' not in st.session_state:
        st.session_state.bias_analyzer = BiasAnalysisPro()
    return st.session_state.bias_analyzer

def get_option_chain_analyzer():
    """Lazy load option chain analyzer"""
    if 'option_chain_analyzer' not in st.session_state:
        st.session_state.option_chain_analyzer = OptionChainAnalyzer()
    return st.session_state.option_chain_analyzer

def get_advanced_chart_analyzer():
    """Lazy load advanced chart analyzer"""
    if 'advanced_chart_analyzer' not in st.session_state:
        st.session_state.advanced_chart_analyzer = AdvancedChartAnalysis()
    return st.session_state.advanced_chart_analyzer

if 'bias_analysis_results' not in st.session_state:
    st.session_state.bias_analysis_results = None

if 'option_chain_results' not in st.session_state:
    st.session_state.option_chain_results = None

if 'chart_data' not in st.session_state:
    st.session_state.chart_data = None

# Initialize background data loading
if 'data_preloaded' not in st.session_state:
    st.session_state.data_preloaded = False
    # Start background data loading on first run
    preload_all_data()
    st.session_state.data_preloaded = True

# NSE Options Analyzer - Initialize instruments session state
NSE_INSTRUMENTS = {
    'indices': {
        'NIFTY': {'lot_size': 75, 'zone_size': 20, 'atm_range': 200},
        'BANKNIFTY': {'lot_size': 25, 'zone_size': 100, 'atm_range': 500},
        'SENSEX': {'lot_size': 10, 'zone_size': 50, 'atm_range': 300},
        'NIFTY IT': {'lot_size': 50, 'zone_size': 50, 'atm_range': 300},
        'NIFTY AUTO': {'lot_size': 50, 'zone_size': 50, 'atm_range': 300}
    },
    'stocks': {
        'TCS': {'lot_size': 150, 'zone_size': 30, 'atm_range': 150},
        'RELIANCE': {'lot_size': 250, 'zone_size': 40, 'atm_range': 200},
        'HDFCBANK': {'lot_size': 550, 'zone_size': 50, 'atm_range': 250}
    }
}

# Initialize session states for all NSE instruments
for category in NSE_INSTRUMENTS:
    for instrument in NSE_INSTRUMENTS[category]:
        if f'{instrument}_price_data' not in st.session_state:
            st.session_state[f'{instrument}_price_data'] = pd.DataFrame(columns=["Time", "Spot"])

        if f'{instrument}_trade_log' not in st.session_state:
            st.session_state[f'{instrument}_trade_log'] = []

        if f'{instrument}_call_log_book' not in st.session_state:
            st.session_state[f'{instrument}_call_log_book'] = []

        if f'{instrument}_support_zone' not in st.session_state:
            st.session_state[f'{instrument}_support_zone'] = (None, None)

        if f'{instrument}_resistance_zone' not in st.session_state:
            st.session_state[f'{instrument}_resistance_zone'] = (None, None)

# Initialize overall option chain data
if 'overall_option_data' not in st.session_state:
    st.session_state['overall_option_data'] = {}

# ═══════════════════════════════════════════════════════════════════════
# AUTO REFRESH & PERFORMANCE OPTIMIZATIONS
# ═══════════════════════════════════════════════════════════════════════
# Optimized for fast loading and refresh:
# - Chart data cached for 60 seconds
# - Signal checks reduced to 30-second intervals
# - Lazy loading for tab-specific data
# - Streamlit caching for expensive computations

# ═══════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════

st.title(APP_TITLE)
st.caption(APP_SUBTITLE)

# ═══════════════════════════════════════════════════════════════════════
# MARKET HOURS WARNING BANNER
# ═══════════════════════════════════════════════════════════════════════

if MARKET_HOURS_ENABLED:
    should_run, reason = should_run_app()

    if not should_run:
        # Display prominent warning banner when market is closed
        st.error(f"""
        ⚠️ **MARKET CLOSED - APP RUNNING IN LIMITED MODE**

        **Reason:** {reason}

        **Trading Hours:** 8:30 AM - 3:45 PM IST (Monday - Friday, excluding holidays)

        The app will automatically resume full operation during market hours.
        Background data refresh is paused to conserve API quota.
        """)

        # Show next market open time if available
        market_status = get_market_status()
        if 'next_open' in market_status:
            st.info(f"📅 **Next Market Open:** {market_status['next_open']}")
    else:
        # Show market session info when market is open
        market_status = get_market_status()
        session = market_status.get('session', 'unknown')

        if session == 'pre_market':
            st.info(f"⏰ **{reason}** - Limited liquidity expected")
        elif session == 'post_market':
            st.warning(f"⏰ **{reason}** - Trading session ending soon")
        # Don't show banner during regular market hours to save space

# ═══════════════════════════════════════════════════════════════════════
# SIDEBAR - SYSTEM STATUS
# ═══════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.header("⚙️ System Status")
    
    # Market status
    market_status = get_market_status()
    if market_status['open']:
        st.success(f"{market_status['message']} | {market_status['time']}")
    else:
        st.error(market_status['message'])
    
    st.divider()
    
    # DhanHQ connection
    st.subheader("🔌 DhanHQ API")
    if DEMO_MODE:
        st.info("🧪 DEMO MODE Active")
    else:
        if check_dhan_connection():
            st.success("✅ Connected")
        else:
            st.error("❌ Connection Failed")
    
    st.divider()
    
    # Telegram status
    st.subheader("📱 Telegram Alerts")
    telegram_creds = get_telegram_credentials()
    if telegram_creds['enabled']:
        st.success("✅ Connected")
        if st.button("Send Test Message"):
            if send_test_message():
                st.success("Test message sent!")
            else:
                st.error("Failed to send")
    else:
        st.warning("⚠️ Not Configured")
    
    st.divider()
    
    # Settings
    st.subheader("⚙️ Settings")
    st.write(f"**Auto Refresh:** {AUTO_REFRESH_INTERVAL}s")
    st.write(f"**NIFTY Lot Size:** {LOT_SIZES['NIFTY']}")
    st.write(f"**SENSEX Lot Size:** {LOT_SIZES['SENSEX']}")
    st.write(f"**SL Offset:** {STOP_LOSS_OFFSET} points")

    st.divider()

    # Background Data Loading Status
    st.subheader("🔄 Data Loading")
    cache_manager = get_cache_manager()

    # Check cache status for each data type
    data_status = {
        'Market Data': cache_manager.is_valid('nifty_data'),
        'Bias Analysis': cache_manager.is_valid('bias_analysis'),
    }

    for name, is_valid in data_status.items():
        if is_valid:
            st.success(f"✅ {name}")
        else:
            st.info(f"⏳ {name} Loading...")

    st.caption("🔄 Auto-refreshing every 10-60 seconds")

# ═══════════════════════════════════════════════════════════════════════
# MAIN CONTENT
# ═══════════════════════════════════════════════════════════════════════

# Get NIFTY data from cache (loaded in background)
nifty_data = get_cached_nifty_data()

if not nifty_data or not nifty_data.get('success'):
    # Fallback to direct fetch if cache is empty
    nifty_data = fetch_nifty_data()
    if not nifty_data['success']:
        st.error(f"❌ Failed to fetch NIFTY data: {nifty_data.get('error')}")
        st.stop()

# ═══════════════════════════════════════════════════════════════════════
# CACHED CHART DATA FETCHER (Performance Optimization)
# ═══════════════════════════════════════════════════════════════════════
# Cache chart data for 60 seconds to avoid repeated API calls
if 'chart_data_cache' not in st.session_state:
    st.session_state.chart_data_cache = {}
if 'chart_data_cache_time' not in st.session_state:
    st.session_state.chart_data_cache_time = {}

@st.cache_data(ttl=60, show_spinner=False)
def get_cached_chart_data(symbol, period, interval):
    """Cached chart data fetcher - reduces API calls"""
    chart_analyzer = AdvancedChartAnalysis()
    return chart_analyzer.fetch_intraday_data(symbol, period=period, interval=interval)

@st.cache_data(ttl=60, show_spinner=False)
def calculate_vob_indicators(df_key, sensitivity=5):
    """Cached VOB calculation - reduces redundant computations"""
    from indicators.volume_order_blocks import VolumeOrderBlocks

    # Get dataframe from cache
    cache_manager = get_cache_manager()
    df = cache_manager.get(df_key)

    if df is None or len(df) == 0:
        return None

    vob_indicator = VolumeOrderBlocks(sensitivity=sensitivity)
    return vob_indicator.calculate(df)

@st.cache_data(ttl=60, show_spinner=False)
def calculate_sentiment():
    """Cached sentiment calculation"""
    try:
        return calculate_overall_sentiment()
    except:
        return None

# ═══════════════════════════════════════════════════════════════════════
# VOB-BASED SIGNAL MONITORING (Optimized)
# ═══════════════════════════════════════════════════════════════════════
# Initialize sentiment cache in session state
if 'cached_sentiment' not in st.session_state:
    st.session_state.cached_sentiment = None
if 'sentiment_cache_time' not in st.session_state:
    st.session_state.sentiment_cache_time = 0

# Calculate sentiment once every 60 seconds and cache it (avoid redundant calculations)
current_time = time.time()
if current_time - st.session_state.sentiment_cache_time > 60:
    sentiment_result = calculate_sentiment()
    if sentiment_result:
        st.session_state.cached_sentiment = sentiment_result
        st.session_state.sentiment_cache_time = current_time

# Check for VOB signals every 30 seconds (reduced from 10s for better performance)
if current_time - st.session_state.last_vob_check_time > 30:
    st.session_state.last_vob_check_time = current_time

    try:
        # Use cached sentiment (calculated once per minute to avoid redundancy)
        if st.session_state.cached_sentiment:
            overall_sentiment = st.session_state.cached_sentiment.get('overall_sentiment', 'NEUTRAL')
        else:
            overall_sentiment = 'NEUTRAL'

        # Fetch chart data and calculate VOB for NIFTY (using cached function)
        df = get_cached_chart_data('^NSEI', '1d', '1m')

        if df is not None and len(df) > 0:
            # Calculate VOB blocks
            from indicators.volume_order_blocks import VolumeOrderBlocks
            vob_indicator = VolumeOrderBlocks(sensitivity=5)
            vob_data = vob_indicator.calculate(df)

            # Check for NIFTY signal
            nifty_signal = st.session_state.vob_signal_generator.check_for_signal(
                spot_price=nifty_data['spot_price'],
                market_sentiment=overall_sentiment,
                bullish_blocks=vob_data['bullish_blocks'],
                bearish_blocks=vob_data['bearish_blocks'],
                index='NIFTY'
            )

            if nifty_signal:
                # Check if this is a new signal (not already in active signals)
                is_new = True
                for existing_signal in st.session_state.active_vob_signals:
                    if (existing_signal['index'] == nifty_signal['index'] and
                        existing_signal['direction'] == nifty_signal['direction'] and
                        abs(existing_signal['entry_price'] - nifty_signal['entry_price']) < 5):
                        is_new = False
                        break

                if is_new:
                    # Add to active signals
                    st.session_state.active_vob_signals.append(nifty_signal)

                    # Send telegram notification
                    telegram_bot = TelegramBot()
                    telegram_bot.send_vob_entry_signal(nifty_signal)

        # Fetch chart data and calculate VOB for SENSEX (using cached function)
        df_sensex = get_cached_chart_data('^BSESN', '1d', '1m')

        if df_sensex is not None and len(df_sensex) > 0:
            # Calculate VOB blocks for SENSEX
            vob_indicator_sensex = VolumeOrderBlocks(sensitivity=5)
            vob_data_sensex = vob_indicator_sensex.calculate(df_sensex)

            # Get SENSEX spot price
            sensex_data = get_cached_sensex_data()
            if sensex_data:
                sensex_signal = st.session_state.vob_signal_generator.check_for_signal(
                    spot_price=sensex_data['spot_price'],
                    market_sentiment=overall_sentiment,
                    bullish_blocks=vob_data_sensex['bullish_blocks'],
                    bearish_blocks=vob_data_sensex['bearish_blocks'],
                    index='SENSEX'
                )

                if sensex_signal:
                    # Check if this is a new signal
                    is_new = True
                    for existing_signal in st.session_state.active_vob_signals:
                        if (existing_signal['index'] == sensex_signal['index'] and
                            existing_signal['direction'] == sensex_signal['direction'] and
                            abs(existing_signal['entry_price'] - sensex_signal['entry_price']) < 5):
                            is_new = False
                            break

                    if is_new:
                        # Add to active signals
                        st.session_state.active_vob_signals.append(sensex_signal)

                        # Send telegram notification
                        telegram_bot = TelegramBot()
                        telegram_bot.send_vob_entry_signal(sensex_signal)

        # Clean up old signals (older than 30 minutes)
        st.session_state.active_vob_signals = [
            sig for sig in st.session_state.active_vob_signals
            if (current_time - sig['timestamp'].timestamp()) < 1800
        ]

    except Exception as e:
        # Silently fail - don't disrupt the app
        pass

# ═══════════════════════════════════════════════════════════════════════
# HTF SUPPORT/RESISTANCE SIGNAL MONITORING (Optimized)
# ═══════════════════════════════════════════════════════════════════════
# Check for HTF S/R signals every 30 seconds (reduced from 10s for better performance)
if current_time - st.session_state.last_htf_sr_check_time > 30:
    st.session_state.last_htf_sr_check_time = current_time

    try:
        # Use cached sentiment (calculated once per minute to avoid redundancy)
        if st.session_state.cached_sentiment:
            overall_sentiment = st.session_state.cached_sentiment.get('overall_sentiment', 'NEUTRAL')
        else:
            overall_sentiment = 'NEUTRAL'

        # Only check if market sentiment is BULLISH or BEARISH
        if overall_sentiment in ['BULLISH', 'BEARISH']:
            # Import HTF S/R indicator
            from indicators.htf_support_resistance import HTFSupportResistance

            # Fetch chart data for NIFTY (using cached function)
            df_nifty = get_cached_chart_data('^NSEI', '7d', '1m')

            if df_nifty is not None and len(df_nifty) > 0:
                # Calculate HTF S/R levels for 5min, 10min, 15min
                htf_sr = HTFSupportResistance()
                levels_config = [
                    {'timeframe': '5T', 'length': 5},
                    {'timeframe': '10T', 'length': 5},
                    {'timeframe': '15T', 'length': 5}
                ]
                htf_levels = htf_sr.calculate_multi_timeframe(df_nifty, levels_config)

                # Check for NIFTY signal
                nifty_htf_signal = st.session_state.htf_sr_signal_generator.check_for_signal(
                    spot_price=nifty_data['spot_price'],
                    market_sentiment=overall_sentiment,
                    htf_levels=htf_levels,
                    index='NIFTY'
                )

                if nifty_htf_signal:
                    # Check if this is a new signal (not already in active signals)
                    is_new = True
                    for existing_signal in st.session_state.active_htf_sr_signals:
                        if (existing_signal['index'] == nifty_htf_signal['index'] and
                            existing_signal['direction'] == nifty_htf_signal['direction'] and
                            abs(existing_signal['entry_price'] - nifty_htf_signal['entry_price']) < 5):
                            is_new = False
                            break

                    if is_new:
                        # Add to active signals
                        st.session_state.active_htf_sr_signals.append(nifty_htf_signal)

                        # Send telegram notification
                        telegram_bot = TelegramBot()
                        telegram_bot.send_htf_sr_entry_signal(nifty_htf_signal)

            # Fetch chart data for SENSEX (using cached function)
            df_sensex = get_cached_chart_data('^BSESN', '7d', '1m')

            if df_sensex is not None and len(df_sensex) > 0:
                # Calculate HTF S/R levels for SENSEX
                htf_sr_sensex = HTFSupportResistance()
                htf_levels_sensex = htf_sr_sensex.calculate_multi_timeframe(df_sensex, levels_config)

                # Get SENSEX spot price
                sensex_data = get_cached_sensex_data()
                if sensex_data:
                    sensex_htf_signal = st.session_state.htf_sr_signal_generator.check_for_signal(
                        spot_price=sensex_data['spot_price'],
                        market_sentiment=overall_sentiment,
                        htf_levels=htf_levels_sensex,
                        index='SENSEX'
                    )

                    if sensex_htf_signal:
                        # Check if this is a new signal
                        is_new = True
                        for existing_signal in st.session_state.active_htf_sr_signals:
                            if (existing_signal['index'] == sensex_htf_signal['index'] and
                                existing_signal['direction'] == sensex_htf_signal['direction'] and
                                abs(existing_signal['entry_price'] - sensex_htf_signal['entry_price']) < 5):
                                is_new = False
                                break

                        if is_new:
                            # Add to active signals
                            st.session_state.active_htf_sr_signals.append(sensex_htf_signal)

                            # Send telegram notification
                            telegram_bot = TelegramBot()
                            telegram_bot.send_htf_sr_entry_signal(sensex_htf_signal)

            # Clean up old HTF S/R signals (older than 30 minutes)
            st.session_state.active_htf_sr_signals = [
                sig for sig in st.session_state.active_htf_sr_signals
                if (current_time - sig['timestamp'].timestamp()) < 1800
            ]

    except Exception as e:
        # Silently fail - don't disrupt the app
        pass

# Display market data
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "NIFTY Spot",
        f"₹{nifty_data['spot_price']:,.2f}",
        delta=None
    )

with col2:
    st.metric(
        "ATM Strike",
        f"{nifty_data['atm_strike']}"
    )

with col3:
    st.metric(
        "Current Expiry",
        nifty_data['current_expiry']
    )

with col4:
    # Show data freshness status
    cache_manager = get_cache_manager()
    nifty_cache_time = cache_manager._cache_timestamps.get('nifty_data', 0)
    if nifty_cache_time > 0:
        age_seconds = int(time.time() - nifty_cache_time)
        if age_seconds < 15:
            st.success(f"🟢 Live ({age_seconds}s ago)")
        elif age_seconds < 60:
            st.info(f"🔵 Fresh ({age_seconds}s ago)")
        else:
            st.warning(f"🟡 Updating...")
    else:
        st.info("📅 Loading...")

st.divider()

# ═══════════════════════════════════════════════════════════════════════
# VOB TRADING SIGNALS DISPLAY
# ═══════════════════════════════════════════════════════════════════════
st.markdown("### 🎯 NIFTY/SENSEX Manual Trader")
st.markdown("**VOB-Based Trading | Manual Signal Entry**")

if st.session_state.active_vob_signals:
    for signal in st.session_state.active_vob_signals:
        signal_emoji = "🟢" if signal['direction'] == 'CALL' else "🔴"
        direction_label = "BULLISH" if signal['direction'] == 'CALL' else "BEARISH"
        sentiment_color = "#26ba9f" if signal['market_sentiment'] == 'BULLISH' else "#ba2646"

        with st.container():
            st.markdown(f"""
            <div style='border: 2px solid {sentiment_color}; border-radius: 10px; padding: 15px; margin: 10px 0; background-color: rgba(38, 186, 159, 0.1);'>
                <h3 style='margin: 0;'>{signal_emoji} {signal['index']} {direction_label} ENTRY SIGNAL</h3>
                <p style='margin: 5px 0;'><b>Market Sentiment:</b> {signal['market_sentiment']}</p>
                <hr style='margin: 10px 0;'>
                <div style='display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;'>
                    <div>
                        <p style='margin: 0; font-size: 12px; color: #888;'>Entry Price</p>
                        <p style='margin: 0; font-size: 18px; font-weight: bold;'>₹{signal['entry_price']}</p>
                    </div>
                    <div>
                        <p style='margin: 0; font-size: 12px; color: #888;'>Stop Loss</p>
                        <p style='margin: 0; font-size: 18px; font-weight: bold; color: #ff5252;'>₹{signal['stop_loss']}</p>
                    </div>
                    <div>
                        <p style='margin: 0; font-size: 12px; color: #888;'>Target</p>
                        <p style='margin: 0; font-size: 18px; font-weight: bold; color: #4caf50;'>₹{signal['target']}</p>
                    </div>
                    <div>
                        <p style='margin: 0; font-size: 12px; color: #888;'>Risk:Reward</p>
                        <p style='margin: 0; font-size: 18px; font-weight: bold;'>{signal['risk_reward']}</p>
                    </div>
                </div>
                <hr style='margin: 10px 0;'>
                <div style='display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;'>
                    <div>
                        <p style='margin: 0; font-size: 12px; color: #888;'>VOB Level</p>
                        <p style='margin: 0; font-size: 14px;'>₹{signal['vob_level']}</p>
                    </div>
                    <div>
                        <p style='margin: 0; font-size: 12px; color: #888;'>Distance from VOB</p>
                        <p style='margin: 0; font-size: 14px;'>{signal['distance_from_vob']} points</p>
                    </div>
                    <div>
                        <p style='margin: 0; font-size: 12px; color: #888;'>Signal Time</p>
                        <p style='margin: 0; font-size: 14px;'>{signal['timestamp'].strftime('%H:%M:%S')}</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.info("⏳ Monitoring market for VOB-based entry signals... No active signals at the moment.")
    st.caption("Signals are generated when spot price is within 8 points of a Volume Order Block and aligned with overall market sentiment.")

st.divider()

# ═══════════════════════════════════════════════════════════════════════
# HTF S/R TRADING SIGNALS DISPLAY
# ═══════════════════════════════════════════════════════════════════════
st.markdown("### 📊 HTF Support/Resistance Signals")
st.markdown("**HTF S/R Based Trading | 5min, 10min, 15min Timeframes**")

if st.session_state.active_htf_sr_signals:
    for signal in st.session_state.active_htf_sr_signals:
        signal_emoji = "🟢" if signal['direction'] == 'CALL' else "🔴"
        direction_label = "BULLISH" if signal['direction'] == 'CALL' else "BEARISH"
        sentiment_color = "#26ba9f" if signal['market_sentiment'] == 'BULLISH' else "#ba2646"

        # Format timeframe for display
        timeframe_display = {
            '5T': '5 Min',
            '10T': '10 Min',
            '15T': '15 Min'
        }.get(signal.get('timeframe', ''), signal.get('timeframe', 'N/A'))

        # Determine level type and value
        if signal['direction'] == 'CALL':
            level_type = "Support Level"
            level_value = signal['support_level']
        else:
            level_type = "Resistance Level"
            level_value = signal.get('resistance_level', 'N/A')

        with st.container():
            st.markdown(f"""
            <div style='border: 2px solid {sentiment_color}; border-radius: 10px; padding: 15px; margin: 10px 0; background-color: rgba(38, 186, 159, 0.1);'>
                <h3 style='margin: 0;'>{signal_emoji} {signal['index']} {direction_label} HTF S/R ENTRY SIGNAL</h3>
                <p style='margin: 5px 0;'><b>Market Sentiment:</b> {signal['market_sentiment']} | <b>Timeframe:</b> {timeframe_display}</p>
                <hr style='margin: 10px 0;'>
                <div style='display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;'>
                    <div>
                        <p style='margin: 0; font-size: 12px; color: #888;'>Entry Price</p>
                        <p style='margin: 0; font-size: 18px; font-weight: bold;'>₹{signal['entry_price']}</p>
                    </div>
                    <div>
                        <p style='margin: 0; font-size: 12px; color: #888;'>Stop Loss</p>
                        <p style='margin: 0; font-size: 18px; font-weight: bold; color: #ff5252;'>₹{signal['stop_loss']}</p>
                    </div>
                    <div>
                        <p style='margin: 0; font-size: 12px; color: #888;'>Target</p>
                        <p style='margin: 0; font-size: 18px; font-weight: bold; color: #4caf50;'>₹{signal['target']}</p>
                    </div>
                    <div>
                        <p style='margin: 0; font-size: 12px; color: #888;'>Risk:Reward</p>
                        <p style='margin: 0; font-size: 18px; font-weight: bold;'>{signal['risk_reward']}</p>
                    </div>
                </div>
                <hr style='margin: 10px 0;'>
                <div style='display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;'>
                    <div>
                        <p style='margin: 0; font-size: 12px; color: #888;'>{level_type}</p>
                        <p style='margin: 0; font-size: 14px;'>₹{level_value}</p>
                    </div>
                    <div>
                        <p style='margin: 0; font-size: 12px; color: #888;'>Distance from Level</p>
                        <p style='margin: 0; font-size: 14px;'>{signal['distance_from_level']} points</p>
                    </div>
                    <div>
                        <p style='margin: 0; font-size: 12px; color: #888;'>Signal Time</p>
                        <p style='margin: 0; font-size: 14px;'>{signal['timestamp'].strftime('%H:%M:%S')}</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.info("⏳ Monitoring market for HTF S/R entry signals... No active signals at the moment.")
    st.caption("Signals are generated when spot price is within 8 points of HTF Support (for bullish) or Resistance (for bearish) and aligned with overall market sentiment.")

st.divider()

# ═══════════════════════════════════════════════════════════════════════
# TABS WITH PERSISTENT STATE
# ═══════════════════════════════════════════════════════════════════════

# Tab selector that persists across reruns
tab_options = ["🌟 Overall Market Sentiment", "🎯 Trade Setup", "📊 Active Signals", "📈 Positions", "🎯 Bias Analysis Pro", "📊 Option Chain Analysis", "📈 Advanced Chart Analysis"]
selected_tab = st.radio("Select Tab", tab_options, index=st.session_state.active_tab, horizontal=True, key="tab_selector", label_visibility="collapsed")

# Update active tab in session state
st.session_state.active_tab = tab_options.index(selected_tab)

# ═══════════════════════════════════════════════════════════════════════
# TAB 1: OVERALL MARKET SENTIMENT
# ═══════════════════════════════════════════════════════════════════════

if selected_tab == "🌟 Overall Market Sentiment":
    render_overall_market_sentiment(NSE_INSTRUMENTS)

# ═══════════════════════════════════════════════════════════════════════
# TAB 2: TRADE SETUP
# ═══════════════════════════════════════════════════════════════════════

elif selected_tab == "🎯 Trade Setup":
    st.header("🎯 Create New Trade Setup")
    
    col1, col2 = st.columns(2)
    
    with col1:
        selected_index = st.selectbox(
            "Select Index",
            ["NIFTY", "SENSEX"],
            key="setup_index"
        )
    
    with col2:
        selected_direction = st.selectbox(
            "Select Direction",
            ["CALL", "PUT"],
            key="setup_direction"
        )
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        vob_support = st.number_input(
            "VOB Support Level",
            min_value=0.0,
            value=float(nifty_data['spot_price'] - 50),
            step=10.0,
            key="vob_support"
        )
    
    with col2:
        vob_resistance = st.number_input(
            "VOB Resistance Level",
            min_value=0.0,
            value=float(nifty_data['spot_price'] + 50),
            step=10.0,
            key="vob_resistance"
        )
    
    st.divider()
    
    # Preview calculated levels
    st.subheader("📋 Preview Trade Levels")
    
    levels = calculate_levels(
        selected_index,
        selected_direction,
        vob_support,
        vob_resistance,
        STOP_LOSS_OFFSET
    )
    
    strike_info = calculate_strike(
        selected_index,
        nifty_data['spot_price'],
        selected_direction,
        nifty_data['current_expiry']
    )
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Entry Level", f"{levels['entry_level']:.2f}")
    
    with col2:
        st.metric("Stop Loss", f"{levels['sl_level']:.2f}")
    
    with col3:
        st.metric("Target", f"{levels['target_level']:.2f}")
    
    with col4:
        st.metric("Risk:Reward", f"1:{levels['rr_ratio']}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"**Strike:** {strike_info['strike']} {strike_info['option_type']} ({strike_info['strike_type']})")
    
    with col2:
        lot_size = LOT_SIZES[selected_index]
        st.info(f"**Quantity:** {lot_size} ({selected_index} lot size)")
    
    st.divider()
    
    # Create setup button
    if st.button("✅ Create Signal Setup", type="primary", use_container_width=True):
        signal_id = st.session_state.signal_manager.create_setup(
            selected_index,
            selected_direction,
            vob_support,
            vob_resistance
        )
        st.session_state.active_setup_id = signal_id
        st.success(f"✅ Signal setup created! ID: {signal_id[:20]}...")
        st.rerun()

# ═══════════════════════════════════════════════════════════════════════
# TAB 2: ACTIVE SIGNALS
# ═══════════════════════════════════════════════════════════════════════

elif selected_tab == "📊 Active Signals":
    st.header("📊 Active Signal Setups")
    
    active_setups = st.session_state.signal_manager.get_active_setups()
    
    if not active_setups:
        st.info("No active signal setups. Create one in the Trade Setup tab.")
    else:
        for signal_id, setup in active_setups.items():
            with st.container():
                st.subheader(f"{setup['index']} {setup['direction']}")
                
                # Signal count display
                signal_count = setup['signal_count']
                signals_display = "⭐" * signal_count + "☆" * (3 - signal_count)
                
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**Signals:** {signals_display} ({signal_count}/3)")
                    st.write(f"**VOB Support:** {setup['vob_support']}")
                    st.write(f"**VOB Resistance:** {setup['vob_resistance']}")
                
                with col2:
                    if signal_count < 3:
                        if st.button(f"➕ Add Signal", key=f"add_{signal_id}"):
                            st.session_state.signal_manager.add_signal(signal_id)
                            
                            # Check if ready and send Telegram
                            updated_setup = st.session_state.signal_manager.get_setup(signal_id)
                            if updated_setup['status'] == 'ready':
                                telegram = TelegramBot()
                                telegram.send_signal_ready(updated_setup)
                            
                            st.rerun()
                    
                    if signal_count > 0:
                        if st.button(f"➖ Remove Signal", key=f"remove_{signal_id}"):
                            st.session_state.signal_manager.remove_signal(signal_id)
                            st.rerun()
                
                with col3:
                    if st.button(f"🗑️ Delete", key=f"delete_{signal_id}"):
                        st.session_state.signal_manager.delete_setup(signal_id)
                        st.rerun()
                
                # Check VOB touch and show execute button
                if setup['status'] == 'ready':
                    current_price = nifty_data['spot_price']
                    
                    if setup['direction'] == 'CALL':
                        vob_touched = check_vob_touch(current_price, setup['vob_support'], VOB_TOUCH_TOLERANCE)
                        vob_type = "Support"
                        vob_level = setup['vob_support']
                    else:
                        vob_touched = check_vob_touch(current_price, setup['vob_resistance'], VOB_TOUCH_TOLERANCE)
                        vob_type = "Resistance"
                        vob_level = setup['vob_resistance']
                    
                    if vob_touched:
                        st.success(f"✅ VOB {vob_type} TOUCHED! Current: {current_price} | VOB: {vob_level}")
                        
                        if st.button(f"🚀 EXECUTE TRADE NOW", key=f"execute_{signal_id}", type="primary", use_container_width=True):
                            with st.spinner("Executing trade..."):
                                executor = TradeExecutor()
                                result = executor.execute_trade(
                                    setup,
                                    nifty_data['spot_price'],
                                    nifty_data['current_expiry']
                                )
                                
                                if result['success']:
                                    st.success(f"✅ {result['message']}")
                                    st.success(f"**Order ID:** {result['order_id']}")
                                    
                                    # Mark as executed
                                    st.session_state.signal_manager.mark_executed(signal_id, result['order_id'])
                                    
                                    # Display order details
                                    details = result['order_details']
                                    st.write("**Order Details:**")
                                    st.write(f"- Strike: {details['strike']} {details['option_type']} ({details['strike_type']})")
                                    st.write(f"- Quantity: {details['quantity']}")
                                    st.write(f"- Entry: {details['entry_level']}")
                                    st.write(f"- Stop Loss: {details['sl_price']}")
                                    st.write(f"- Target: {details['target_price']}")
                                    st.write(f"- R:R Ratio: 1:{details['rr_ratio']}")
                                    
                                    time.sleep(2)
                                    st.rerun()
                                else:
                                    st.error(f"❌ {result['message']}")
                                    if 'error' in result:
                                        st.error(f"Error: {result['error']}")
                    else:
                        st.warning(f"⏳ Waiting for price to touch VOB {vob_type} ({vob_level})")
                        st.info(f"Current Price: {current_price} | Distance: {abs(current_price - vob_level):.2f} points")
                
                st.divider()

# ═══════════════════════════════════════════════════════════════════════
# TAB 3: POSITIONS
# ═══════════════════════════════════════════════════════════════════════

elif selected_tab == "📈 Positions":
    st.header("📈 Active Positions")
    
    if DEMO_MODE:
        st.warning("🧪 DEMO MODE - No real positions")
        
        # Show executed setups
        executed = {k: v for k, v in st.session_state.signal_manager.signals.items() if v['status'] == 'executed'}
        
        if executed:
            for signal_id, setup in executed.items():
                st.info(f"**Demo Order:** {setup['index']} {setup['direction']} | Order ID: {setup['order_id']}")
        else:
            st.info("No executed trades yet")
    else:
        from dhan_api import DhanAPI
        
        try:
            dhan = DhanAPI()
            positions_result = dhan.get_positions()
            
            if positions_result['success']:
                positions = positions_result['positions']
                
                if not positions:
                    st.info("No active positions")
                else:
                    for pos in positions:
                        with st.container():
                            col1, col2, col3 = st.columns([3, 2, 1])
                            
                            with col1:
                                st.write(f"**Symbol:** {pos.get('tradingSymbol', 'N/A')}")
                                st.write(f"**Quantity:** {pos.get('netQty', 0)}")
                            
                            with col2:
                                pnl = pos.get('unrealizedProfit', 0)
                                pnl_color = "green" if pnl > 0 else "red"
                                st.markdown(f"**P&L:** <span style='color:{pnl_color}'>₹{pnl:,.2f}</span>", unsafe_allow_html=True)
                            
                            with col3:
                                if st.button("❌ Exit", key=f"exit_{pos.get('orderId')}"):
                                    result = dhan.exit_position(pos.get('orderId'))
                                    if result['success']:
                                        st.success("Position exited!")
                                        st.rerun()
                                    else:
                                        st.error("Exit failed")
                            
                            st.divider()
            else:
                st.error(f"Failed to fetch positions: {positions_result.get('error')}")
        
        except Exception as e:
            st.error(f"Error: {e}")

# ═══════════════════════════════════════════════════════════════════════
# TAB 5: BIAS ANALYSIS PRO
# ═══════════════════════════════════════════════════════════════════════

elif selected_tab == "🎯 Bias Analysis Pro":
    st.header("🎯 Comprehensive Bias Analysis Pro")
    st.caption("15+ Bias Indicators with Weighted Scoring System | 🔄 Auto-refreshing every 60 seconds")

    # Auto-load cached results if not already in session state
    if not st.session_state.bias_analysis_results:
        cached_results = get_cached_bias_analysis_results()
        if cached_results:
            st.session_state.bias_analysis_results = cached_results

    # Analysis controls
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        bias_symbol = st.selectbox(
            "Select Market for Bias Analysis",
            ["^NSEI (NIFTY 50)", "^BSESN (SENSEX)", "^DJI (DOW JONES)"],
            key="bias_analysis_symbol"
        )
        symbol_code = bias_symbol.split()[0]

    with col2:
        if st.button("🔍 Analyze All Bias", type="primary", use_container_width=True):
            with st.spinner("Analyzing bias indicators..."):
                try:
                    bias_analyzer = get_bias_analyzer()
                    results = bias_analyzer.analyze_all_bias_indicators(symbol_code)
                    st.session_state.bias_analysis_results = results
                    # Update cache
                    cache_manager = get_cache_manager()
                    cache_manager.set('bias_analysis', results)
                    if results['success']:
                        st.success("✅ Bias analysis completed!")
                    else:
                        st.error(f"❌ Analysis failed: {results.get('error')}")
                except Exception as e:
                    st.error(f"❌ Analysis failed: {e}")

    with col3:
        if st.session_state.bias_analysis_results:
            if st.button("🗑️ Clear Analysis", use_container_width=True):
                st.session_state.bias_analysis_results = None
                st.rerun()

    st.divider()

    # Display results if available
    if st.session_state.bias_analysis_results and st.session_state.bias_analysis_results.get('success'):
        results = st.session_state.bias_analysis_results

        # =====================================================================
        # OVERALL BIAS SUMMARY
        # =====================================================================
        st.subheader("📊 Overall Market Bias")

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric(
                "Current Price",
                f"₹{results['current_price']:,.2f}"
            )

        with col2:
            overall_bias = results['overall_bias']
            bias_emoji = "🐂" if overall_bias == "BULLISH" else "🐻" if overall_bias == "BEARISH" else "⚖️"
            bias_color = "green" if overall_bias == "BULLISH" else "red" if overall_bias == "BEARISH" else "gray"

            st.markdown(f"<h3 style='color:{bias_color};'>{bias_emoji} {overall_bias}</h3>",
                       unsafe_allow_html=True)
            st.caption("Overall Market Bias")

        with col3:
            score = results['overall_score']
            score_color = "green" if score > 0 else "red" if score < 0 else "gray"
            st.markdown(f"<h3 style='color:{score_color};'>{score:.1f}</h3>",
                       unsafe_allow_html=True)
            st.caption("Overall Score")

        with col4:
            confidence = results['overall_confidence']
            st.metric(
                "Confidence",
                f"{confidence:.1f}%"
            )

        with col5:
            st.metric(
                "Total Indicators",
                results['total_indicators']
            )

        # Bias distribution
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("🐂 Bullish Signals", results['bullish_count'])

        with col2:
            st.metric("🐻 Bearish Signals", results['bearish_count'])

        with col3:
            st.metric("⚖️ Neutral Signals", results['neutral_count'])

        st.divider()

        # =====================================================================
        # DETAILED BIAS BREAKDOWN TABLE
        # =====================================================================
        st.subheader("📋 Detailed Bias Breakdown")

        # Convert bias results to DataFrame
        bias_df = pd.DataFrame(results['bias_results'])

        # Function to color code bias
        def color_bias(val):
            if 'BULLISH' in str(val):
                return 'background-color: #26a69a; color: white;'
            elif 'BEARISH' in str(val):
                return 'background-color: #ef5350; color: white;'
            else:
                return 'background-color: #78909c; color: white;'

        # Function to color code scores
        def color_score(val):
            try:
                score = float(val)
                if score > 50:
                    return 'background-color: #1b5e20; color: white; font-weight: bold;'
                elif score > 0:
                    return 'background-color: #4caf50; color: white;'
                elif score < -50:
                    return 'background-color: #b71c1c; color: white; font-weight: bold;'
                elif score < 0:
                    return 'background-color: #f44336; color: white;'
                else:
                    return 'background-color: #616161; color: white;'
            except:
                return ''

        # Create styled dataframe
        styled_df = bias_df.style.applymap(color_bias, subset=['bias']) \
                                 .applymap(color_score, subset=['score']) \
                                 .format({'score': '{:.2f}', 'weight': '{:.1f}'})

        st.dataframe(styled_df, use_container_width=True, hide_index=True, height=600)

        st.divider()

        # =====================================================================
        # VISUAL SCORE REPRESENTATION
        # =====================================================================
        st.subheader("📊 Visual Bias Representation")

        # Create a chart showing each indicator's contribution
        chart_data = pd.DataFrame({
            'Indicator': [b['indicator'] for b in results['bias_results']],
            'Weighted Score': [b['score'] * b['weight'] for b in results['bias_results']]
        })

        # Sort by weighted score
        chart_data = chart_data.sort_values('Weighted Score', ascending=True)

        # Display bar chart
        st.bar_chart(chart_data.set_index('Indicator'))

        st.divider()

        # =====================================================================
        # BIAS CATEGORY BREAKDOWN
        # =====================================================================
        st.subheader("📈 Bias by Category")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**🔧 Technical Indicators**")
            technical_bias = [b for b in results['bias_results'] if b['indicator'] in
                             ['RSI', 'MFI (Money Flow)', 'DMI/ADX', 'VWAP', 'EMA Crossover (5/18)']]

            tech_df = pd.DataFrame(technical_bias)
            if not tech_df.empty:
                tech_bull = len(tech_df[tech_df['bias'].str.contains('BULLISH', na=False)])
                tech_bear = len(tech_df[tech_df['bias'].str.contains('BEARISH', na=False)])
                tech_neutral = len(tech_df) - tech_bull - tech_bear

                st.write(f"🐂 Bullish: {tech_bull} | 🐻 Bearish: {tech_bear} | ⚖️ Neutral: {tech_neutral}")
                st.dataframe(tech_df[['indicator', 'bias', 'score']],
                           use_container_width=True, hide_index=True)

        with col2:
            st.markdown("**📊 Volume Indicators**")
            volume_bias = [b for b in results['bias_results'] if b['indicator'] in
                          ['Volume ROC', 'OBV (On Balance Volume)', 'Force Index', 'Volume Trend']]

            vol_df = pd.DataFrame(volume_bias)
            if not vol_df.empty:
                vol_bull = len(vol_df[vol_df['bias'].str.contains('BULLISH', na=False)])
                vol_bear = len(vol_df[vol_df['bias'].str.contains('BEARISH', na=False)])
                vol_neutral = len(vol_df) - vol_bull - vol_bear

                st.write(f"🐂 Bullish: {vol_bull} | 🐻 Bearish: {vol_bear} | ⚖️ Neutral: {vol_neutral}")
                st.dataframe(vol_df[['indicator', 'bias', 'score']],
                           use_container_width=True, hide_index=True)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**📉 Momentum Indicators**")
            momentum_bias = [b for b in results['bias_results'] if b['indicator'] in
                           ['Price Momentum (ROC)', 'RSI Divergence', 'Choppiness Index']]

            mom_df = pd.DataFrame(momentum_bias)
            if not mom_df.empty:
                mom_bull = len(mom_df[mom_df['bias'].str.contains('BULLISH', na=False)])
                mom_bear = len(mom_df[mom_df['bias'].str.contains('BEARISH', na=False)])
                mom_neutral = len(mom_df) - mom_bull - mom_bear

                st.write(f"🐂 Bullish: {mom_bull} | 🐻 Bearish: {mom_bear} | ⚖️ Neutral: {mom_neutral}")
                st.dataframe(mom_df[['indicator', 'bias', 'score']],
                           use_container_width=True, hide_index=True)

        with col2:
            st.markdown("**🌍 Market Wide Indicators**")
            market_bias = [b for b in results['bias_results'] if b['indicator'] in
                          ['Market Breadth', 'Volatility Ratio', 'ATR Trend']]

            mkt_df = pd.DataFrame(market_bias)
            if not mkt_df.empty:
                mkt_bull = len(mkt_df[mkt_df['bias'].str.contains('BULLISH', na=False)])
                mkt_bear = len(mkt_df[mkt_df['bias'].str.contains('BEARISH', na=False)])
                mkt_neutral = len(mkt_df) - mkt_bull - mkt_bear

                st.write(f"🐂 Bullish: {mkt_bull} | 🐻 Bearish: {mkt_bear} | ⚖️ Neutral: {mkt_neutral}")
                st.dataframe(mkt_df[['indicator', 'bias', 'score']],
                           use_container_width=True, hide_index=True)

        st.divider()

        # =====================================================================
        # TOP STOCKS PERFORMANCE (from market breadth analysis)
        # =====================================================================
        if results.get('stock_data'):
            st.subheader("📊 Top Stocks Performance")

            stock_df = pd.DataFrame(results['stock_data'])
            stock_df = stock_df.sort_values('change_pct', ascending=False)

            # Add bias column
            stock_df['bias'] = stock_df['change_pct'].apply(
                lambda x: '🐂 BULLISH' if x > 0.5 else '🐻 BEARISH' if x < -0.5 else '⚖️ NEUTRAL'
            )

            # Format percentage
            stock_df['change_pct'] = stock_df['change_pct'].apply(lambda x: f"{x:.2f}%")
            stock_df['weight'] = stock_df['weight'].apply(lambda x: f"{x:.2f}%")

            st.dataframe(stock_df, use_container_width=True, hide_index=True)

        st.divider()

        # =====================================================================
        # TRADING RECOMMENDATION
        # =====================================================================
        st.subheader("💡 Trading Recommendation")

        overall_bias = results['overall_bias']
        overall_score = results['overall_score']
        confidence = results['overall_confidence']

        if overall_bias == "BULLISH" and confidence > 70:
            st.success("### 🐂 STRONG BULLISH SIGNAL")
            st.info("""
            **Recommended Strategy:**
            - ✅ Look for LONG entries on dips
            - ✅ Wait for support levels or VOB support touch
            - ✅ Set stop loss below recent swing low
            - ✅ Target: Risk-Reward ratio 1:2 or higher
            """)
        elif overall_bias == "BULLISH" and confidence >= 50:
            st.success("### 🐂 MODERATE BULLISH SIGNAL")
            st.info("""
            **Recommended Strategy:**
            - ⚠️ Consider LONG entries with caution
            - ⚠️ Use tighter stop losses
            - ⚠️ Take partial profits at resistance levels
            - ⚠️ Monitor for trend confirmation
            """)
        elif overall_bias == "BEARISH" and confidence > 70:
            st.error("### 🐻 STRONG BEARISH SIGNAL")
            st.info("""
            **Recommended Strategy:**
            - ✅ Look for SHORT entries on rallies
            - ✅ Wait for resistance levels or VOB resistance touch
            - ✅ Set stop loss above recent swing high
            - ✅ Target: Risk-Reward ratio 1:2 or higher
            """)
        elif overall_bias == "BEARISH" and confidence >= 50:
            st.error("### 🐻 MODERATE BEARISH SIGNAL")
            st.info("""
            **Recommended Strategy:**
            - ⚠️ Consider SHORT entries with caution
            - ⚠️ Use tighter stop losses
            - ⚠️ Take partial profits at support levels
            - ⚠️ Monitor for trend reversal
            """)
        else:
            st.warning("### ⚖️ NEUTRAL / NO CLEAR SIGNAL")
            st.info("""
            **Recommended Strategy:**
            - 🔄 Stay out of the market or use range trading
            - 🔄 Wait for clearer bias formation
            - 🔄 Monitor key support/resistance levels
            - 🔄 Reduce position sizes if trading
            """)

        # Key levels for entry
        st.divider()
        st.subheader("🎯 Key Considerations")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**Bullish Signals Count**")
            st.markdown(f"<h2 style='color:green;'>{results['bullish_count']}/{results['total_indicators']}</h2>",
                       unsafe_allow_html=True)

        with col2:
            st.markdown("**Bearish Signals Count**")
            st.markdown(f"<h2 style='color:red;'>{results['bearish_count']}/{results['total_indicators']}</h2>",
                       unsafe_allow_html=True)

        with col3:
            st.markdown("**Confidence Level**")
            confidence_color = "green" if confidence > 70 else "orange" if confidence > 50 else "red"
            st.markdown(f"<h2 style='color:{confidence_color};'>{confidence:.1f}%</h2>",
                       unsafe_allow_html=True)

        # Timestamp
        st.caption(f"Analysis Time: {results['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")

    else:
        st.info("👆 Click 'Analyze All Bias' button to start comprehensive bias analysis")

        st.markdown("""
        ### About Bias Analysis Pro

        This comprehensive bias analyzer evaluates **15+ different bias indicators** to provide:

        #### 📊 Technical Indicators
        - **RSI** (Relative Strength Index)
        - **MFI** (Money Flow Index)
        - **DMI/ADX** (Directional Movement Index)
        - **VWAP** (Volume Weighted Average Price)
        - **EMA Crossover** (5/18 periods)

        #### 📈 Volume Indicators
        - **Volume ROC** (Rate of Change)
        - **OBV** (On Balance Volume)
        - **Force Index**
        - **Volume Trend**

        #### 📉 Momentum Indicators
        - **Price ROC** (Momentum)
        - **RSI Divergence** (Bullish/Bearish)
        - **Choppiness Index**

        #### 🌍 Market Wide Indicators
        - **Market Breadth** (Top 9 NSE stocks analysis)
        - **Volatility Ratio**
        - **ATR Trend**

        #### 🎯 Scoring System
        - Each indicator has a **weight** based on reliability
        - Scores range from **-100 (Strong Bearish)** to **+100 (Strong Bullish)**
        - Overall bias is calculated using **weighted average** of all indicators
        - Final recommendation considers both **bias direction** and **confidence level**

        #### ✅ How to Use
        1. Select the market (NIFTY, SENSEX, or DOW)
        2. Click "Analyze All Bias" button
        3. Review comprehensive bias breakdown
        4. Check trading recommendation
        5. Use signals to inform your trading decisions

        **Note:** This tool is converted from the Pine Script "Smart Trading Dashboard - Enhanced Pro" indicator with 80% accuracy.
        """)

# ═══════════════════════════════════════════════════════════════════════
# TAB 6: OPTION CHAIN ANALYSIS (NSE Options Analyzer)
# ═══════════════════════════════════════════════════════════════════════

elif selected_tab == "📊 Option Chain Analysis":
    st.header("📊 NSE Options Analyzer")
    st.caption("Comprehensive Option Chain Analysis with Bias Detection, Support/Resistance Zones, and Trade Signals")

    # Create tabs for main sections
    tab_indices, tab_stocks, tab_overall = st.tabs(["📈 Indices", "🏢 Stocks", "🌐 Overall Market Analysis"])

    with tab_indices:
        st.header("NSE Indices Analysis")
        # Create subtabs for each index
        nifty_tab, banknifty_tab, sensex_tab, it_tab, auto_tab = st.tabs(["NIFTY", "BANKNIFTY", "SENSEX", "NIFTY IT", "NIFTY AUTO"])

        with nifty_tab:
            analyze_instrument('NIFTY', NSE_INSTRUMENTS)

        with banknifty_tab:
            analyze_instrument('BANKNIFTY', NSE_INSTRUMENTS)

        with sensex_tab:
            analyze_instrument('SENSEX', NSE_INSTRUMENTS)

        with it_tab:
            analyze_instrument('NIFTY IT', NSE_INSTRUMENTS)

        with auto_tab:
            analyze_instrument('NIFTY AUTO', NSE_INSTRUMENTS)

    with tab_stocks:
        st.header("Stock Options Analysis")
        # Create subtabs for each stock
        tcs_tab, reliance_tab, hdfc_tab = st.tabs(["TCS", "RELIANCE", "HDFCBANK"])

        with tcs_tab:
            analyze_instrument('TCS', NSE_INSTRUMENTS)

        with reliance_tab:
            analyze_instrument('RELIANCE', NSE_INSTRUMENTS)

        with hdfc_tab:
            analyze_instrument('HDFCBANK', NSE_INSTRUMENTS)

    with tab_overall:
        # Overall Market Analysis with PCR
        display_overall_option_chain_analysis(NSE_INSTRUMENTS)

# ═══════════════════════════════════════════════════════════════════════
# TAB 7: ADVANCED CHART ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

elif selected_tab == "📈 Advanced Chart Analysis":
    st.header("📈 Advanced Chart Analysis")
    st.caption("TradingView-style Chart with 6 Advanced Indicators: Volume Bars, Volume Order Blocks, HTF Support/Resistance (3min, 5min, 10min, 15min levels), Volume Footprint (1D timeframe, 10 bins, Dynamic POC), Ultimate RSI, OM Indicator (Order Flow & Momentum)")

    # Chart controls
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

    with col1:
        chart_symbol = st.selectbox(
            "Select Market",
            ["^NSEI (NIFTY 50)", "^BSESN (SENSEX)", "^DJI (DOW JONES)"],
            key="chart_symbol"
        )
        symbol_code = chart_symbol.split()[0]

    with col2:
        chart_period = st.selectbox(
            "Period",
            ["1d", "5d", "1mo"],
            index=0,
            key="chart_period"
        )

    with col3:
        chart_interval = st.selectbox(
            "Interval",
            ["1m", "5m", "15m", "1h"],
            index=0,
            key="chart_interval"
        )

    with col4:
        if st.button("🔄 Load Chart", type="primary", use_container_width=True):
            with st.spinner("Loading chart data and calculating indicators..."):
                try:
                    # Fetch data using cached function (60s cache)
                    df = get_cached_chart_data(symbol_code, chart_period, chart_interval)

                    if df is not None and len(df) > 0:
                        st.session_state.chart_data = df
                        st.success(f"✅ Loaded {len(df)} candles")
                    else:
                        st.error("❌ Failed to fetch data. Try a different period or interval.")
                        st.session_state.chart_data = None

                except Exception as e:
                    st.error(f"❌ Error loading chart: {e}")
                    st.session_state.chart_data = None

    st.divider()

    # Indicator toggles
    st.subheader("🔧 Indicator Settings")

    col1, col2, col3 = st.columns(3)

    with col1:
        show_vob = st.checkbox("📦 Volume Order Blocks", value=True, key="show_vob")
        show_htf_sr = st.checkbox("📊 HTF Support/Resistance", value=True, key="show_htf_sr")

    with col2:
        show_footprint = st.checkbox("👣 Volume Footprint", value=True, key="show_footprint")
        show_rsi = st.checkbox("📈 Ultimate RSI", value=True, key="show_rsi")

    with col3:
        show_volume = st.checkbox("📊 Volume Bars", value=True, key="show_volume")
        show_om = st.checkbox("🎯 OM Indicator", value=False, key="show_om")
        show_liquidity_profile = st.checkbox("💧 Liquidity Sentiment Profile", value=False, key="show_liquidity_profile")

    st.divider()

    # Indicator Configuration Section
    st.subheader("⚙️ Indicator Configuration")
    st.caption("Configure each indicator's parameters below")

    # Volume Order Blocks Settings
    if show_vob:
        with st.expander("📦 Volume Order Blocks Settings", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                vob_sensitivity = st.slider(
                    "Sensitivity",
                    min_value=3,
                    max_value=15,
                    value=5,
                    step=1,
                    help="Detection sensitivity for order blocks",
                    key="vob_sensitivity"
                )
            with col2:
                vob_mid_line = st.checkbox("Show Mid Line", value=True, key="vob_mid_line")
                vob_trend_shadow = st.checkbox("Show Trend Shadow", value=True, key="vob_trend_shadow")

    # HTF Support/Resistance Settings
    if show_htf_sr:
        with st.expander("📊 HTF Support/Resistance Settings", expanded=False):
            st.markdown("**Timeframe Configuration**")
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                htf_3min_enabled = st.checkbox("3min", value=True, key="htf_3min_enabled")
                htf_3min_length = st.number_input("3min Length", min_value=2, max_value=10, value=4, step=1, key="htf_3min_length")

            with col2:
                htf_5min_enabled = st.checkbox("5min", value=True, key="htf_5min_enabled")
                htf_5min_length = st.number_input("5min Length", min_value=2, max_value=10, value=5, step=1, key="htf_5min_length")

            with col3:
                htf_10min_enabled = st.checkbox("10min", value=True, key="htf_10min_enabled")
                htf_10min_length = st.number_input("10min Length", min_value=2, max_value=10, value=5, step=1, key="htf_10min_length")

            with col4:
                htf_15min_enabled = st.checkbox("15min", value=True, key="htf_15min_enabled")
                htf_15min_length = st.number_input("15min Length", min_value=2, max_value=10, value=5, step=1, key="htf_15min_length")

    # Volume Footprint Settings
    if show_footprint:
        with st.expander("👣 Volume Footprint Settings", expanded=False):
            col1, col2 = st.columns(2)

            with col1:
                footprint_bins = st.slider(
                    "Number of Bins",
                    min_value=5,
                    max_value=30,
                    value=10,
                    step=1,
                    help="Number of price bins for volume distribution",
                    key="footprint_bins"
                )
                footprint_timeframe = st.selectbox(
                    "Timeframe",
                    options=["D", "W", "2W", "M"],
                    index=0,
                    help="Higher timeframe for footprint analysis",
                    key="footprint_timeframe"
                )

            with col2:
                footprint_dynamic_poc = st.checkbox(
                    "Dynamic POC",
                    value=True,
                    help="Show dynamic Point of Control",
                    key="footprint_dynamic_poc"
                )

    # Ultimate RSI Settings
    if show_rsi:
        with st.expander("📈 Ultimate RSI Settings", expanded=False):
            col1, col2, col3 = st.columns(3)

            with col1:
                rsi_length = st.slider(
                    "RSI Length",
                    min_value=5,
                    max_value=30,
                    value=14,
                    step=1,
                    help="RSI calculation period",
                    key="rsi_length"
                )
                rsi_method = st.selectbox(
                    "Calculation Method",
                    options=["RMA", "EMA", "SMA", "TMA"],
                    index=0,
                    help="Moving average method for RSI",
                    key="rsi_method"
                )

            with col2:
                rsi_smooth = st.slider(
                    "Signal Smoothing",
                    min_value=5,
                    max_value=30,
                    value=14,
                    step=1,
                    help="Signal line smoothing period",
                    key="rsi_smooth"
                )
                rsi_signal_method = st.selectbox(
                    "Signal Method",
                    options=["EMA", "SMA", "RMA", "TMA"],
                    index=0,
                    help="Signal line calculation method",
                    key="rsi_signal_method"
                )

            with col3:
                rsi_ob_level = st.slider(
                    "Overbought Level",
                    min_value=70,
                    max_value=90,
                    value=80,
                    step=5,
                    help="Overbought threshold",
                    key="rsi_ob_level"
                )
                rsi_os_level = st.slider(
                    "Oversold Level",
                    min_value=10,
                    max_value=30,
                    value=20,
                    step=5,
                    help="Oversold threshold",
                    key="rsi_os_level"
                )

    # Liquidity Sentiment Profile Settings
    if show_liquidity_profile:
        with st.expander("💧 Liquidity Sentiment Profile Settings", expanded=False):
            st.markdown("**Profile Configuration**")
            col1, col2, col3 = st.columns(3)

            with col1:
                lsp_anchor_period = st.selectbox(
                    "Anchor Period",
                    options=["Auto", "Session", "Day", "Week", "Month", "Quarter", "Year"],
                    index=0,
                    key="lsp_anchor_period"
                )
                lsp_num_rows = st.slider(
                    "Number of Rows",
                    min_value=10,
                    max_value=100,
                    value=25,
                    step=5,
                    key="lsp_num_rows"
                )

            with col2:
                lsp_profile_width = st.slider(
                    "Profile Width %",
                    min_value=10,
                    max_value=50,
                    value=50,
                    step=5,
                    key="lsp_profile_width"
                ) / 100.0
                lsp_show_liquidity = st.checkbox("Show Liquidity Profile", value=True, key="lsp_show_liquidity")
                lsp_show_sentiment = st.checkbox("Show Sentiment Profile", value=True, key="lsp_show_sentiment")

            with col3:
                lsp_show_poc = st.checkbox("Show Level of Significance", value=False, key="lsp_show_poc")
                lsp_show_price_levels = st.checkbox("Show Price Levels", value=False, key="lsp_show_price_levels")
                lsp_show_range_bg = st.checkbox("Show Range Background", value=True, key="lsp_show_range_bg")

            st.markdown("**Volume Thresholds**")
            col1, col2 = st.columns(2)

            with col1:
                lsp_hv_threshold = st.slider(
                    "High Volume Threshold %",
                    min_value=50,
                    max_value=99,
                    value=73,
                    step=1,
                    key="lsp_hv_threshold"
                ) / 100.0

            with col2:
                lsp_lv_threshold = st.slider(
                    "Low Volume Threshold %",
                    min_value=10,
                    max_value=40,
                    value=21,
                    step=1,
                    key="lsp_lv_threshold"
                ) / 100.0

    # OM Indicator Settings
    if show_om:
        with st.expander("🎯 OM Indicator Settings", expanded=False):
            st.markdown("**Volume Order Blocks (VOB) Module**")
            col1, col2 = st.columns(2)
            with col1:
                om_vob_sensitivity = st.slider(
                    "VOB Sensitivity",
                    min_value=3,
                    max_value=15,
                    value=5,
                    step=1,
                    key="om_vob_sensitivity"
                )

            st.markdown("**High Volume Pivots (HVP) Module**")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                om_show_hvp = st.checkbox("Show HVP", value=True, key="om_show_hvp")
            with col2:
                om_hvp_left_bars = st.number_input("Left Bars", min_value=5, max_value=30, value=15, step=1, key="om_hvp_left_bars")
            with col3:
                om_hvp_right_bars = st.number_input("Right Bars", min_value=5, max_value=30, value=15, step=1, key="om_hvp_right_bars")
            with col4:
                om_hvp_volume_filter = st.number_input("Volume Filter", min_value=1.0, max_value=5.0, value=2.0, step=0.5, key="om_hvp_volume_filter")

            st.markdown("**Delta Module**")
            col1, col2 = st.columns(2)
            with col1:
                om_delta_length = st.slider("Delta Length", min_value=5, max_value=30, value=10, step=1, key="om_delta_length")
            with col2:
                om_delta_threshold = st.slider("Delta Threshold", min_value=0.5, max_value=5.0, value=1.5, step=0.5, key="om_delta_threshold")

            st.markdown("**VIDYA Module**")
            col1, col2, col3 = st.columns(3)
            with col1:
                om_vidya_length = st.slider("VIDYA Length", min_value=5, max_value=30, value=10, step=1, key="om_vidya_length")
            with col2:
                om_vidya_momentum = st.slider("Momentum Period", min_value=10, max_value=40, value=20, step=5, key="om_vidya_momentum")
            with col3:
                om_band_distance = st.slider("Band Distance", min_value=1.0, max_value=5.0, value=2.0, step=0.5, key="om_band_distance")

    st.divider()

    # Display chart if data is available
    if st.session_state.chart_data is not None:
        try:
            with st.spinner("Rendering chart with indicators..."):
                # Prepare indicator parameters
                vob_params = {
                    'sensitivity': vob_sensitivity if show_vob else 5,
                    'mid_line': vob_mid_line if show_vob else True,
                    'trend_shadow': vob_trend_shadow if show_vob else True
                } if show_vob else None

                htf_params = {
                    'levels_config': []
                }
                if show_htf_sr:
                    if htf_3min_enabled:
                        htf_params['levels_config'].append({'timeframe': '3T', 'length': htf_3min_length, 'style': 'Solid', 'color': '#26a69a'})
                    if htf_5min_enabled:
                        htf_params['levels_config'].append({'timeframe': '5T', 'length': htf_5min_length, 'style': 'Solid', 'color': '#2196f3'})
                    if htf_10min_enabled:
                        htf_params['levels_config'].append({'timeframe': '10T', 'length': htf_10min_length, 'style': 'Solid', 'color': '#9c27b0'})
                    if htf_15min_enabled:
                        htf_params['levels_config'].append({'timeframe': '15T', 'length': htf_15min_length, 'style': 'Solid', 'color': '#ff9800'})

                footprint_params = {
                    'bins': footprint_bins if show_footprint else 10,
                    'timeframe': footprint_timeframe if show_footprint else 'D',
                    'dynamic_poc': footprint_dynamic_poc if show_footprint else True
                } if show_footprint else None

                rsi_params = {
                    'length': rsi_length if show_rsi else 14,
                    'smooth': rsi_smooth if show_rsi else 14,
                    'method': rsi_method if show_rsi else 'RMA',
                    'signal_method': rsi_signal_method if show_rsi else 'EMA',
                    'ob_level': rsi_ob_level if show_rsi else 80,
                    'os_level': rsi_os_level if show_rsi else 20
                } if show_rsi else None

                om_params = {
                    'vob_sensitivity': om_vob_sensitivity if show_om else 5,
                    'hvp_left_bars': om_hvp_left_bars if show_om else 15,
                    'hvp_right_bars': om_hvp_right_bars if show_om else 15,
                    'hvp_volume_filter': om_hvp_volume_filter if show_om else 2.0,
                    'delta_length': om_delta_length if show_om else 10,
                    'delta_threshold': om_delta_threshold if show_om else 1.5,
                    'vidya_length': om_vidya_length if show_om else 10,
                    'vidya_momentum': om_vidya_momentum if show_om else 20,
                    'band_distance': om_band_distance if show_om else 2.0,
                    'show_hvp': om_show_hvp if show_om else True
                } if show_om else None

                liquidity_params = {
                    'anchor_period': lsp_anchor_period if show_liquidity_profile else 'Auto',
                    'num_rows': lsp_num_rows if show_liquidity_profile else 25,
                    'profile_width': lsp_profile_width if show_liquidity_profile else 0.50,
                    'show_liquidity_profile': lsp_show_liquidity if show_liquidity_profile else True,
                    'show_sentiment_profile': lsp_show_sentiment if show_liquidity_profile else True,
                    'show_poc': lsp_show_poc if show_liquidity_profile else False,
                    'show_price_levels': lsp_show_price_levels if show_liquidity_profile else False,
                    'show_range_bg': lsp_show_range_bg if show_liquidity_profile else True,
                    'hv_threshold': lsp_hv_threshold if show_liquidity_profile else 0.73,
                    'lv_threshold': lsp_lv_threshold if show_liquidity_profile else 0.21
                } if show_liquidity_profile else None

                # Create chart with selected indicators
                chart_analyzer = get_advanced_chart_analyzer()
                fig = chart_analyzer.create_advanced_chart(
                    st.session_state.chart_data,
                    symbol_code,
                    show_vob=show_vob,
                    show_htf_sr=show_htf_sr,
                    show_footprint=show_footprint,
                    show_rsi=show_rsi,
                    show_om=show_om,
                    show_volume=show_volume,
                    show_liquidity_profile=show_liquidity_profile,
                    vob_params=vob_params,
                    htf_params=htf_params,
                    footprint_params=footprint_params,
                    rsi_params=rsi_params,
                    om_params=om_params,
                    liquidity_params=liquidity_params
                )

                # Display chart
                st.plotly_chart(fig, use_container_width=True)

                # Chart statistics
                st.subheader("📊 Chart Statistics")

                col1, col2, col3, col4, col5 = st.columns(5)

                df_stats = st.session_state.chart_data

                with col1:
                    st.metric("Current Price", f"₹{df_stats['close'].iloc[-1]:,.2f}")

                with col2:
                    price_change = df_stats['close'].iloc[-1] - df_stats['close'].iloc[0]
                    price_change_pct = (price_change / df_stats['close'].iloc[0]) * 100
                    st.metric("Change", f"₹{price_change:,.2f}", delta=f"{price_change_pct:.2f}%")

                with col3:
                    st.metric("High", f"₹{df_stats['high'].max():,.2f}")

                with col4:
                    st.metric("Low", f"₹{df_stats['low'].min():,.2f}")

                with col5:
                    avg_volume = df_stats['volume'].mean()
                    st.metric("Avg Volume", f"{avg_volume:,.0f}")

                # Trading signals based on indicators
                st.divider()
                st.subheader("🎯 Trading Signals")

                if show_rsi:
                    from indicators.ultimate_rsi import UltimateRSI
                    rsi_indicator = UltimateRSI(**rsi_params) if rsi_params else UltimateRSI()
                    rsi_signals = rsi_indicator.get_signals(df_stats)

                    latest_rsi = rsi_signals['ultimate_rsi'][-1]
                    latest_signal = rsi_signals['signal'][-1]

                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("**Ultimate RSI Analysis**")
                        ob_threshold = rsi_params['ob_level'] if rsi_params else 80
                        os_threshold = rsi_params['os_level'] if rsi_params else 20
                        rsi_state = "Overbought" if latest_rsi > ob_threshold else "Oversold" if latest_rsi < os_threshold else "Neutral"
                        rsi_color = "red" if latest_rsi > ob_threshold else "green" if latest_rsi < os_threshold else "gray"

                        st.markdown(f"Current RSI: <span style='color:{rsi_color}; font-size:24px;'>{latest_rsi:.2f}</span>", unsafe_allow_html=True)
                        st.write(f"Signal Line: {latest_signal:.2f}")
                        st.write(f"State: **{rsi_state}**")

                    with col2:
                        st.markdown("**RSI Trading Recommendation**")
                        if latest_rsi > ob_threshold:
                            st.warning("⚠️ **OVERBOUGHT** - Consider taking profits or waiting for pullback")
                        elif latest_rsi < os_threshold:
                            st.success("✅ **OVERSOLD** - Potential buying opportunity")
                        elif latest_rsi > latest_signal:
                            st.info("📈 **BULLISH** - RSI above signal line")
                        elif latest_rsi < latest_signal:
                            st.info("📉 **BEARISH** - RSI below signal line")
                        else:
                            st.info("⏸ **NEUTRAL** - No clear signal")

                if show_vob:
                    from indicators.volume_order_blocks import VolumeOrderBlocks
                    vob_indicator = VolumeOrderBlocks(**vob_params) if vob_params else VolumeOrderBlocks()
                    vob_data = vob_indicator.calculate(df_stats)

                    st.divider()
                    st.markdown("**Volume Order Blocks**")

                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(f"🟢 **Bullish OBs:** {len([b for b in vob_data['bullish_blocks'] if b['active']])}")
                        if len(vob_data['bullish_blocks']) > 0:
                            for i, block in enumerate(vob_data['bullish_blocks'][-3:]):
                                if block['active']:
                                    st.write(f"  - Support: {block['lower']:.2f} - {block['upper']:.2f}")

                    with col2:
                        st.write(f"🔴 **Bearish OBs:** {len([b for b in vob_data['bearish_blocks'] if b['active']])}")
                        if len(vob_data['bearish_blocks']) > 0:
                            for i, block in enumerate(vob_data['bearish_blocks'][-3:]):
                                if block['active']:
                                    st.write(f"  - Resistance: {block['lower']:.2f} - {block['upper']:.2f}")

                # Data table
                st.divider()
                st.subheader("📋 Recent Candles Data")

                # Show last 20 candles
                display_df = df_stats.tail(20).copy()
                display_df = display_df.reset_index()

                if 'timestamp' in display_df.columns:
                    display_df['timestamp'] = display_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
                elif display_df.index.name == 'Datetime':
                    display_df['Time'] = display_df.index.strftime('%Y-%m-%d %H:%M')

                st.dataframe(display_df[['open', 'high', 'low', 'close', 'volume']].tail(20),
                           use_container_width=True)

        except Exception as e:
            st.error(f"❌ Error rendering chart: {e}")
            st.write("Error details:", str(e))

    else:
        st.info("👆 Click 'Load Chart' button to display the advanced chart")

        st.markdown("""
        ### About Advanced Chart Analysis

        This advanced charting module provides professional-grade technical analysis with 6 powerful indicators:

        #### 📊 Volume Bars
        - TradingView-style volume histogram
        - Green bars for bullish candles (close > open)
        - Red bars for bearish candles (close < open)
        - Essential for confirming price movements and identifying volume spikes

        #### 📦 Volume Order Blocks (BigBeluga)
        - Detects institutional order blocks based on volume and EMA crossovers
        - Shows bullish (support) and bearish (resistance) zones
        - Helps identify high-probability entry/exit zones

        #### 📊 HTF Support/Resistance (BigBeluga)
        - Multi-timeframe pivot analysis (4H, 12H, Daily, Weekly)
        - Identifies key support and resistance levels
        - Non-repainting pivot detection

        #### 👣 Real-Time HTF Volume Footprint (BigBeluga)
        - Volume distribution across price levels
        - Point of Control (POC) - highest volume traded price
        - Value Area - where 70% of volume occurred

        #### 📈 Ultimate RSI (LuxAlgo)
        - Enhanced RSI using price range instead of just price change
        - More responsive to market conditions
        - Signal line for trend confirmation
        - Overbought/Oversold detection

        #### 🎯 OM Indicator (Order Flow & Momentum)
        - **VWAP**: Volume Weighted Average Price for intraday trading
        - **VOB**: Volume Order Blocks with EMA-based detection
        - **HVP**: High Volume Pivots marking significant support/resistance
        - **Delta Module**: Buy/Sell pressure analysis with spike detection
        - **VIDYA**: Variable Index Dynamic Average with trend detection
        - **LTP Trap**: Last Traded Price trap signals for reversal detection
        - Comprehensive order flow analysis combining 6 sub-indicators

        #### 🎯 How to Use
        1. Select market (NIFTY, SENSEX, or DOW)
        2. Choose period and interval (default: 1 day, 1 minute)
        3. Click "Load Chart" to fetch data
        4. Toggle indicators on/off as needed
        5. Analyze chart and trading signals
        6. Use signals to inform your trading decisions

        **Note:** All indicators are converted from Pine Script with high accuracy and optimized for Python/Plotly.
        """)

# ═══════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════

st.divider()
st.caption(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Auto-refresh: {AUTO_REFRESH_INTERVAL}s")
