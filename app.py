import streamlit as st
import time
from datetime import datetime
import pandas as pd

# Import modules
from config import *
from market_data import *
from signal_manager import SignalManager
from strike_calculator import calculate_strike, calculate_levels
from trade_executor import TradeExecutor
from telegram_alerts import TelegramBot, send_test_message
from dhan_api import check_dhan_connection
from smart_trading_dashboard import SmartTradingDashboard
from bias_analysis import BiasAnalysisPro
from option_chain_analysis import OptionChainAnalyzer

# ═══════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="NIFTY/SENSEX Trader",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════════════════
# INITIALIZE SESSION STATE
# ═══════════════════════════════════════════════════════════════════════

if 'signal_manager' not in st.session_state:
    st.session_state.signal_manager = SignalManager()

if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

if 'active_setup_id' not in st.session_state:
    st.session_state.active_setup_id = None

if 'smart_dashboard' not in st.session_state:
    st.session_state.smart_dashboard = SmartTradingDashboard()

if 'dashboard_results' not in st.session_state:
    st.session_state.dashboard_results = None

if 'bias_analyzer' not in st.session_state:
    st.session_state.bias_analyzer = BiasAnalysisPro()

if 'bias_analysis_results' not in st.session_state:
    st.session_state.bias_analysis_results = None

if 'option_chain_analyzer' not in st.session_state:
    st.session_state.option_chain_analyzer = OptionChainAnalyzer()

if 'option_chain_results' not in st.session_state:
    st.session_state.option_chain_results = None

if 'active_tab' not in st.session_state:
    st.session_state.active_tab = 0

# ═══════════════════════════════════════════════════════════════════════
# AUTO REFRESH
# ═══════════════════════════════════════════════════════════════════════

current_time = time.time()
if current_time - st.session_state.last_refresh > AUTO_REFRESH_INTERVAL:
    st.session_state.last_refresh = current_time
    st.rerun()

# ═══════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════

st.title(APP_TITLE)
st.caption(APP_SUBTITLE)

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

# ═══════════════════════════════════════════════════════════════════════
# MAIN CONTENT
# ═══════════════════════════════════════════════════════════════════════

# Fetch NIFTY data
nifty_data = fetch_nifty_data()

if not nifty_data['success']:
    st.error(f"❌ Failed to fetch NIFTY data: {nifty_data.get('error')}")
    st.stop()

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
    is_expiry = is_expiry_day(nifty_data['current_expiry'])
    if is_expiry:
        st.warning("⚠️ EXPIRY DAY")
    else:
        st.info("📅 Normal Day")

st.divider()

# ═══════════════════════════════════════════════════════════════════════
# TABS WITH PERSISTENT STATE
# ═══════════════════════════════════════════════════════════════════════

# Tab selector that persists across reruns
tab_options = ["🎯 Trade Setup", "📊 Active Signals", "📈 Positions", "📊 Smart Trading Dashboard", "🎯 Bias Analysis Pro", "📊 Option Chain Analysis"]
selected_tab = st.radio("Select Tab", tab_options, index=st.session_state.active_tab, horizontal=True, key="tab_selector", label_visibility="collapsed")

# Update active tab in session state
st.session_state.active_tab = tab_options.index(selected_tab)

# ═══════════════════════════════════════════════════════════════════════
# TAB 1: TRADE SETUP
# ═══════════════════════════════════════════════════════════════════════

if selected_tab == "🎯 Trade Setup":
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

if selected_tab == "📊 Active Signals":
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

if selected_tab == "📈 Positions":
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
# TAB 4: SMART TRADING DASHBOARD
# ═══════════════════════════════════════════════════════════════════════

if selected_tab == "📊 Smart Trading Dashboard":
    st.header("📊 Smart Trading Dashboard")
    st.caption("Adaptive Market Analysis with Volume Order Blocks")

    # Analysis controls
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        analyze_symbol = st.selectbox(
            "Select Market",
            ["^NSEI (NIFTY 50)", "^BSESN (SENSEX)", "^DJI (DOW JONES)"],
            key="dashboard_symbol"
        )
        symbol = analyze_symbol.split()[0]

    with col2:
        if st.button("🔄 Analyze Market", type="primary", use_container_width=True):
            with st.spinner("Analyzing market data..."):
                try:
                    results = st.session_state.smart_dashboard.analyze_market(symbol)
                    st.session_state.dashboard_results = results
                    st.success("✅ Analysis completed!")
                except Exception as e:
                    st.error(f"❌ Analysis failed: {e}")

    with col3:
        if st.session_state.dashboard_results:
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state.dashboard_results = None
                st.rerun()

    st.divider()

    # Display results if available
    if st.session_state.dashboard_results:
        results = st.session_state.dashboard_results

        # Market Overview
        st.subheader("📈 Market Overview")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Current Price",
                f"₹{results['current_price']:,.2f}"
            )

        with col2:
            bias = results['market_bias']
            bias_emoji = "🐂" if bias == "BULLISH" else "🐻" if bias == "BEARISH" else "⏸"
            st.metric(
                "Market Bias",
                f"{bias} {bias_emoji}"
            )

        with col3:
            st.metric(
                "Condition",
                results['market_condition']
            )

        with col4:
            mode = "⚡ REVERSAL" if results['bias_data']['reversal_mode'] else "📊 NORMAL"
            st.metric(
                "Mode",
                mode
            )

        st.divider()

        # Bias Analysis
        st.subheader("🎯 Market Bias Analysis")

        bias_data = results['bias_data']

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Overall Bias**")
            bias_df = pd.DataFrame({
                'Type': ['Bullish', 'Bearish'],
                'Percentage': [bias_data['bullish_bias_pct'], bias_data['bearish_bias_pct']]
            })
            st.bar_chart(bias_df.set_index('Type'))

        with col2:
            st.markdown("**Signal Breakdown**")
            signal_df = pd.DataFrame({
                'Signal Type': ['Fast (Technical)', 'Medium (Price)', 'Slow (Stocks)'],
                'Bullish %': [
                    bias_data['fast_bull_pct'],
                    bias_data['medium_bull_pct'],
                    bias_data['slow_bull_pct']
                ],
                'Bearish %': [
                    bias_data['fast_bear_pct'],
                    bias_data['medium_bear_pct'],
                    bias_data['slow_bear_pct']
                ]
            })
            st.dataframe(signal_df, use_container_width=True, hide_index=True)

        # Divergence alerts
        if bias_data['divergence_detected']:
            if bias_data['bullish_divergence']:
                st.warning("⚠️ **BULLISH DIVERGENCE** - Reversal UP possible!")
            if bias_data['bearish_divergence']:
                st.warning("⚠️ **BEARISH DIVERGENCE** - Reversal DOWN possible!")

        st.divider()

        # Technical Indicators
        st.subheader("🔧 Technical Indicators")

        col1, col2, col3, col4 = st.columns(4)

        ind = results['indicators']

        with col1:
            st.metric("RSI", f"{ind['rsi']:.2f}",
                     delta="Bullish" if ind['rsi'] > 50 else "Bearish",
                     delta_color="normal")

        with col2:
            st.metric("MFI", f"{ind['mfi']:.2f}",
                     delta="Bullish" if ind['mfi'] > 50 else "Bearish",
                     delta_color="normal")

        with col3:
            st.metric("ADX", f"{ind['adx']:.2f}",
                     delta="Strong" if ind['adx'] >= 25 else "Weak",
                     delta_color="normal")

        with col4:
            vwap_signal = "Above" if results['current_price'] > ind['vwap'] else "Below"
            st.metric("VWAP", f"₹{ind['vwap']:.2f}",
                     delta=vwap_signal,
                     delta_color="normal")

        col1, col2 = st.columns(2)

        with col1:
            di_signal = "Bullish" if ind['plus_di'] > ind['minus_di'] else "Bearish"
            st.metric("DI+ vs DI-", f"{ind['plus_di']:.2f} vs {ind['minus_di']:.2f}",
                     delta=di_signal,
                     delta_color="normal")

        st.divider()

        # Market Condition Details
        st.subheader("🎯 Market Condition Details")

        range_data = results['range_data']

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Movement Quality", range_data['movement_quality'])

        with col2:
            st.metric("Range %", f"{range_data['range_pct']:.2f}%")

        with col3:
            st.metric("EMA Spread %", f"{range_data['ema_spread_pct']:.2f}%")

        if results['market_condition'] == "RANGE-BOUND":
            st.info("📦 **Market is RANGE-BOUND** - Range trading recommended")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Range High", f"₹{range_data['range_high']:.2f}")

            with col2:
                st.metric("Range Mid", f"₹{range_data['range_mid']:.2f}")

            with col3:
                st.metric("Range Low", f"₹{range_data['range_low']:.2f}")

        st.divider()

        # Stocks Performance
        st.subheader("📊 Top Stocks Performance")

        if results.get('stock_data_table'):
            # Convert to DataFrame for better display
            stock_df = pd.DataFrame(
                results['stock_data_table'],
                columns=["Symbol", "LTP", "Change", "Change%", "15m%", "1h%", "Status"]
            )
            st.dataframe(stock_df, use_container_width=True, hide_index=True)

        # Market averages
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Market Avg (Daily)", f"{bias_data['weighted_avg_daily']:.2f}%")

        with col2:
            st.metric("Market Avg (15m)", f"{bias_data['weighted_avg_tf1']:.2f}%")

        with col3:
            st.metric("Market Avg (1h)", f"{bias_data['weighted_avg_tf2']:.2f}%")

        st.divider()

        # Trading Signal
        st.subheader("🎯 Trading Signal")

        bias = results['bias_data']['market_bias']
        condition = results['market_condition']

        if bias == "BULLISH":
            st.success("🐂 **BULLISH SIGNAL**")
            st.info("**Strategy:** Wait for support level touch for LONG entry")
            if condition == "RANGE-BOUND":
                st.write(f"**Entry Zone:** Near Range Low ₹{range_data['range_low']:.2f}")
                st.write(f"**Target:** Range High ₹{range_data['range_high']:.2f}")
            else:
                st.write("**Entry:** Wait for pivot support level")

        elif bias == "BEARISH":
            st.error("🐻 **BEARISH SIGNAL**")
            st.info("**Strategy:** Wait for resistance level touch for SHORT entry")
            if condition == "RANGE-BOUND":
                st.write(f"**Entry Zone:** Near Range High ₹{range_data['range_high']:.2f}")
                st.write(f"**Target:** Range Low ₹{range_data['range_low']:.2f}")
            else:
                st.write("**Entry:** Wait for pivot resistance level")

        else:
            st.warning("⏸ **NEUTRAL - NO CLEAR SIGNAL**")
            st.info("**Strategy:** Wait for clear bias formation")

        if results['bias_data']['divergence_detected']:
            st.warning("⚠️ **WARNING:** Divergence detected - Reversal possible!")

        if condition == "RANGE-BOUND":
            st.info("📦 Market is RANGE-BOUND - Range trading recommended")

        # Timestamp
        st.caption(f"Analysis Time: {results['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")

    else:
        st.info("👆 Click 'Analyze Market' button to start analysis")

        st.markdown("""
        ### About Smart Trading Dashboard

        This dashboard provides comprehensive market analysis using:

        - **Adaptive Bias Calculation**: 3-tier signal system (Fast/Medium/Slow)
        - **Volume Order Blocks**: EMA-based order block detection
        - **Range Detection**: Identifies range-bound vs trending markets
        - **Technical Indicators**: RSI, MFI, DMI, VWAP, VIDYA, ATR
        - **Multi-Stock Analysis**: Analyzes top 9 NSE stocks for weighted bias
        - **Divergence Detection**: Identifies potential reversals
        - **Reversal Mode**: Adaptive weights when divergence is detected

        **How to use:**
        1. Select the market to analyze
        2. Click "Analyze Market" button
        3. Review the comprehensive analysis and trading signals
        4. Use the signals to inform your trading decisions
        """)

# ═══════════════════════════════════════════════════════════════════════
# TAB 5: BIAS ANALYSIS PRO
# ═══════════════════════════════════════════════════════════════════════

if selected_tab == "🎯 Bias Analysis Pro":
    st.header("🎯 Comprehensive Bias Analysis Pro")
    st.caption("15+ Bias Indicators with Weighted Scoring System | Converted from Pine Script")

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
            with st.spinner("Analyzing 15+ bias indicators... This may take a moment..."):
                try:
                    results = st.session_state.bias_analyzer.analyze_all_bias_indicators(symbol_code)
                    st.session_state.bias_analysis_results = results
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
# TAB 6: OPTION CHAIN ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

if selected_tab == "📊 Option Chain Analysis":
    st.header("📊 NSE Option Chain Analysis")
    st.caption("Put-Call Ratio Analysis for NIFTY, BANKNIFTY, and FINNIFTY")

    # Analysis controls
    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown("**Analyze option chain data from NSE for comprehensive PCR ratios and market bias**")

    with col2:
        if st.button("🔄 Fetch All Data", type="primary", use_container_width=True):
            with st.spinner("Fetching option chain data from NSE..."):
                try:
                    results = st.session_state.option_chain_analyzer.analyze_all_instruments()
                    st.session_state.option_chain_results = results
                    if results['success']:
                        st.success("✅ Option chain data fetched successfully!")
                    else:
                        st.error(f"❌ Failed to fetch data: {results.get('error')}")
                except Exception as e:
                    st.error(f"❌ Analysis failed: {e}")

    # Clear button
    if st.session_state.option_chain_results:
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🗑️ Clear Data", use_container_width=True):
                st.session_state.option_chain_results = None
                st.rerun()

    st.divider()

    # Display results if available
    if st.session_state.option_chain_results and st.session_state.option_chain_results.get('success'):
        results = st.session_state.option_chain_results

        # =====================================================================
        # OVERALL MARKET BIAS
        # =====================================================================
        st.subheader("🌐 Overall Market Bias (Based on Option Chain)")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            market_bias = results['market_bias']
            bias_emoji = "🐂" if market_bias == "BULLISH" else "🐻" if market_bias == "BEARISH" else "⚖️"
            bias_color = "green" if market_bias == "BULLISH" else "red" if market_bias == "BEARISH" else "gray"

            st.markdown(f"<h2 style='color:{bias_color};'>{bias_emoji} {market_bias}</h2>",
                       unsafe_allow_html=True)
            st.caption("Overall Market Bias")

        with col2:
            confidence = results['confidence']
            confidence_color = "green" if confidence > 70 else "orange" if confidence > 50 else "red"
            st.markdown(f"<h2 style='color:{confidence_color};'>{confidence:.1f}%</h2>",
                       unsafe_allow_html=True)
            st.caption("Confidence Level")

        with col3:
            st.metric("🐂 Bullish Instruments", results['bullish_count'])

        with col4:
            st.metric("🐻 Bearish Instruments", results['bearish_count'])

        # Bias distribution visualization
        st.markdown("### 📊 Market Sentiment Distribution")
        sentiment_df = pd.DataFrame({
            'Sentiment': ['Bullish', 'Bearish', 'Neutral'],
            'Count': [results['bullish_count'], results['bearish_count'], results['neutral_count']]
        })
        st.bar_chart(sentiment_df.set_index('Sentiment'))

        st.divider()

        # =====================================================================
        # INDIVIDUAL INSTRUMENT ANALYSIS
        # =====================================================================
        st.subheader("📈 Individual Instrument Analysis")

        for instrument in results['instruments']:
            with st.expander(f"📊 {instrument['symbol']} - {instrument['overall_bias']} {('🐂' if instrument['overall_bias'] == 'BULLISH' else '🐻' if instrument['overall_bias'] == 'BEARISH' else '⚖️')}", expanded=True):

                # Spot price and expiry
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Spot Price", f"₹{instrument['spot_price']:,.2f}")

                with col2:
                    st.metric("Expiry", instrument['expiry'])

                with col3:
                    bias_score = instrument['bias_score']
                    score_color = "green" if bias_score > 0 else "red" if bias_score < 0 else "gray"
                    st.markdown(f"<h3 style='color:{score_color};'>Score: {bias_score}</h3>",
                               unsafe_allow_html=True)

                st.markdown("---")

                # PCR Ratios
                st.markdown("**📊 Put-Call Ratio (PCR) Analysis**")

                col1, col2, col3 = st.columns(3)

                with col1:
                    pcr_oi = instrument['pcr_oi']
                    oi_bias = instrument['oi_bias']
                    oi_color = "green" if oi_bias == "BULLISH" else "red" if oi_bias == "BEARISH" else "gray"

                    st.markdown(f"**PCR (Total OI)**")
                    st.markdown(f"<h3 style='color:{oi_color};'>{pcr_oi:.2f}</h3>", unsafe_allow_html=True)
                    st.caption(f"{oi_bias} {'🐂' if oi_bias == 'BULLISH' else '🐻' if oi_bias == 'BEARISH' else '⚖️'}")

                    st.caption("_PCR > 1.2: Bullish | PCR < 0.8: Bearish_")

                with col2:
                    pcr_change = instrument['pcr_change_oi']
                    change_bias = instrument['change_oi_bias']
                    change_color = "green" if change_bias == "BULLISH" else "red" if change_bias == "BEARISH" else "gray"

                    st.markdown(f"**PCR (Change in OI)**")
                    st.markdown(f"<h3 style='color:{change_color};'>{pcr_change:.2f}</h3>", unsafe_allow_html=True)
                    st.caption(f"{change_bias} {'🐂' if change_bias == 'BULLISH' else '🐻' if change_bias == 'BEARISH' else '⚖️'}")

                    st.caption("_More weighted - Recent activity_")

                with col3:
                    pcr_vol = instrument['pcr_volume']
                    vol_bias = instrument['volume_bias']
                    vol_color = "green" if vol_bias == "BULLISH" else "red" if vol_bias == "BEARISH" else "gray"

                    st.markdown(f"**PCR (Volume)**")
                    st.markdown(f"<h3 style='color:{vol_color};'>{pcr_vol:.2f}</h3>", unsafe_allow_html=True)
                    st.caption(f"{vol_bias} {'🐂' if vol_bias == 'BULLISH' else '🐻' if vol_bias == 'BEARISH' else '⚖️'}")

                st.markdown("---")

                # Detailed OI breakdown
                st.markdown("**📋 Detailed Open Interest Breakdown**")

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**📉 CALL Side**")
                    st.write(f"Total OI: {instrument['total_ce_oi']:,}")
                    st.write(f"Change in OI: {instrument['total_ce_change']:+,}")
                    st.write(f"Total Volume: {instrument['total_ce_volume']:,}")

                with col2:
                    st.markdown("**📈 PUT Side**")
                    st.write(f"Total OI: {instrument['total_pe_oi']:,}")
                    st.write(f"Change in OI: {instrument['total_pe_change']:+,}")
                    st.write(f"Total Volume: {instrument['total_pe_volume']:,}")

                # Visual comparison
                st.markdown("**📊 OI Comparison**")

                oi_comparison = pd.DataFrame({
                    'Type': ['CALL OI', 'PUT OI', 'CALL ΔOI', 'PUT ΔOI'],
                    'Value': [
                        instrument['total_ce_oi'] / 100000,  # In lakhs
                        instrument['total_pe_oi'] / 100000,
                        abs(instrument['total_ce_change']) / 100000,
                        abs(instrument['total_pe_change']) / 100000
                    ]
                })
                st.bar_chart(oi_comparison.set_index('Type'))

        st.divider()

        # =====================================================================
        # TRADING RECOMMENDATIONS
        # =====================================================================
        st.subheader("💡 Trading Recommendations")

        market_bias = results['market_bias']
        confidence = results['confidence']

        if market_bias == "BULLISH" and confidence > 70:
            st.success("### 🐂 STRONG BULLISH SIGNAL (Option Chain)")
            st.info("""
            **Based on Option Chain PCR Analysis:**
            - ✅ High PUT OI compared to CALL OI
            - ✅ PUT writing is dominant (Bearish premium sellers)
            - ✅ Market expects upside movement

            **Recommended Strategy:**
            - Look for CALL buying opportunities on dips
            - Sell PUT options at support levels
            - Avoid naked CALL selling
            """)
        elif market_bias == "BULLISH" and confidence >= 50:
            st.success("### 🐂 MODERATE BULLISH SIGNAL (Option Chain)")
            st.info("""
            **Based on Option Chain PCR Analysis:**
            - ⚠️ Moderately high PUT OI
            - ⚠️ Mixed signals from different instruments

            **Recommended Strategy:**
            - Consider CALL spreads instead of naked calls
            - Use defined risk strategies
            - Monitor PCR changes closely
            """)
        elif market_bias == "BEARISH" and confidence > 70:
            st.error("### 🐻 STRONG BEARISH SIGNAL (Option Chain)")
            st.info("""
            **Based on Option Chain PCR Analysis:**
            - ✅ High CALL OI compared to PUT OI
            - ✅ CALL writing is dominant (Bullish premium sellers)
            - ✅ Market expects downside movement

            **Recommended Strategy:**
            - Look for PUT buying opportunities on rallies
            - Sell CALL options at resistance levels
            - Avoid naked PUT selling
            """)
        elif market_bias == "BEARISH" and confidence >= 50:
            st.error("### 🐻 MODERATE BEARISH SIGNAL (Option Chain)")
            st.info("""
            **Based on Option Chain PCR Analysis:**
            - ⚠️ Moderately high CALL OI
            - ⚠️ Mixed signals from different instruments

            **Recommended Strategy:**
            - Consider PUT spreads instead of naked puts
            - Use defined risk strategies
            - Monitor PCR changes closely
            """)
        else:
            st.warning("### ⚖️ NEUTRAL SIGNAL (Option Chain)")
            st.info("""
            **Based on Option Chain PCR Analysis:**
            - 🔄 Balanced PUT and CALL OI
            - 🔄 No clear directional bias

            **Recommended Strategy:**
            - Use non-directional strategies (Iron Condor, Butterfly)
            - Wait for clearer bias formation
            - Reduce position sizes
            - Focus on premium selling in range-bound conditions
            """)

        # PCR Interpretation Guide
        st.divider()
        st.markdown("### 📚 PCR Interpretation Guide")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
            **Understanding PCR:**
            - **PCR = PUT OI / CALL OI**
            - PCR > 1.2: **Bullish** (More PUTs = Expecting UP move)
            - PCR < 0.8: **Bearish** (More CALLs = Expecting DOWN move)
            - PCR 0.8-1.2: **Neutral** (Balanced)
            """)

        with col2:
            st.markdown("""
            **Weight Priority:**
            1. **PCR (Change in OI)** - Highest weight (Recent activity)
            2. **PCR (Total OI)** - Medium weight (Overall sentiment)
            3. **PCR (Volume)** - Lower weight (Trading activity)
            """)

        # Timestamp
        st.caption(f"Data Updated: {results['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")

    else:
        st.info("👆 Click 'Fetch All Data' button to analyze option chain")

        st.markdown("""
        ### About Option Chain Analysis

        This tool analyzes NSE option chain data to provide comprehensive Put-Call Ratio (PCR) analysis:

        #### 📊 Instruments Analyzed
        - **NIFTY** - Nifty 50 Index Options
        - **BANKNIFTY** - Bank Nifty Index Options
        - **FINNIFTY** - Nifty Financial Services Options

        #### 📈 PCR Ratios Calculated
        1. **PCR (Total OI)**: PUT OI / CALL OI
           - Shows overall market positioning
           - Indicates long-term sentiment

        2. **PCR (Change in OI)**: PUT ΔOI / CALL ΔOI
           - Shows recent activity
           - **Most important** - Higher weight in bias calculation
           - Indicates fresh positions

        3. **PCR (Volume)**: PUT Volume / CALL Volume
           - Shows trading activity
           - Indicates intraday sentiment

        #### 🎯 Bias Calculation
        - Each PCR ratio gets a bias (BULLISH/BEARISH/NEUTRAL)
        - **Weighted scoring system:**
          - Change in OI Bias: Weight = 5 (Most important)
          - Total OI Bias: Weight = 3
          - Volume Bias: Weight = 2
        - Overall bias based on combined weighted score

        #### 📊 Interpretation
        - **PCR > 1.2**: Bullish (More PUT writers - Expect UP move)
        - **PCR < 0.8**: Bearish (More CALL writers - Expect DOWN move)
        - **PCR 0.8-1.2**: Neutral (Balanced)

        #### ✅ How to Use
        1. Click "Fetch All Data" to get latest NSE option chain
        2. Review overall market bias
        3. Check individual instrument PCR ratios
        4. Review trading recommendations
        5. Combine with other technical analysis for better decision making

        **Note:** Option chain data is fetched live from NSE during market hours.
        """)

# ═══════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════

st.divider()
st.caption(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Auto-refresh: {AUTO_REFRESH_INTERVAL}s")
