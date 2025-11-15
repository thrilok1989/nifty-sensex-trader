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
# TABS
# ═══════════════════════════════════════════════════════════════════════

tab1, tab2, tab3, tab4 = st.tabs(["🎯 Trade Setup", "📊 Active Signals", "📈 Positions", "📊 Smart Trading Dashboard"])

# ═══════════════════════════════════════════════════════════════════════
# TAB 1: TRADE SETUP
# ═══════════════════════════════════════════════════════════════════════

with tab1:
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

with tab2:
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

with tab3:
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

with tab4:
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
# FOOTER
# ═══════════════════════════════════════════════════════════════════════

st.divider()
st.caption(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Auto-refresh: {AUTO_REFRESH_INTERVAL}s")
