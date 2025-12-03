"""
ATM Zone Bias Component for Streamlit
Displays detailed ATM Zone Bias tables with strike-wise PCR analysis
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from config import COLORS
from dhan_option_chain_analyzer import DhanOptionChainAnalyzer
from supabase_manager import get_supabase_manager
from option_chain_manager import get_option_chain_manager

def format_number(value, decimals=0):
    """Format number with commas and specified decimals"""
    if pd.isna(value) or value == 0:
        return "-"
    if decimals > 0:
        return f"{value:,.{decimals}f}"
    return f"{int(value):,}"

def get_bias_color(bias):
    """Get color based on bias"""
    if bias == "BULLISH":
        return COLORS['bullish']
    elif bias == "BEARISH":
        return COLORS['bearish']
    else:
        return COLORS['neutral']

def display_atm_zone_table(symbol, atm_data):
    """
    Display ATM Zone Bias table for a symbol

    Args:
        symbol: Trading symbol (NIFTY, SENSEX, etc.)
        atm_data: ATM zone bias data dictionary
    """
    if not atm_data or not atm_data.get('success'):
        st.error(f"❌ Failed to load ATM zone data for {symbol}")
        if atm_data:
            st.caption(f"Error: {atm_data.get('error', 'Unknown error')}")
        return

    # Extract data
    spot_price = atm_data.get('spot_price', 0)
    atm_strike = atm_data.get('atm_strike', 0)
    atm_zone_data = atm_data.get('atm_zone_data', [])
    timestamp = atm_data.get('timestamp', datetime.now())

    # Header
    st.markdown(f"### 🎯 {symbol} ATM Zone Bias (ATM ±5)")

    # Info row
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        st.metric("Spot Price", f"₹{spot_price:,.2f}")
    with col2:
        st.metric("ATM Strike", f"₹{atm_strike:,.0f}")
    with col3:
        st.metric("Total Strikes", len(atm_zone_data))
    with col4:
        if isinstance(timestamp, str):
            st.caption(f"⏱️ {timestamp}")
        else:
            st.caption(f"⏱️ {timestamp.strftime('%I:%M:%S %p')}")

    # Create DataFrame for display
    if not atm_zone_data:
        st.warning(f"⚠️ No ATM zone data available for {symbol}")
        return

    df = pd.DataFrame(atm_zone_data)

    # Prepare display DataFrame
    display_df = pd.DataFrame({
        'Strike': df['strike_price'].apply(lambda x: f"₹{x:,.0f}"),
        'Offset': df['strike_offset'].apply(lambda x: f"ATM{x:+d}" if x != 0 else "ATM"),
        'CE OI': df['ce_oi'].apply(lambda x: format_number(x, 0)),
        'PE OI': df['pe_oi'].apply(lambda x: format_number(x, 0)),
        'CE OI Δ': df['ce_oi_change'].apply(lambda x: format_number(x, 0)),
        'PE OI Δ': df['pe_oi_change'].apply(lambda x: format_number(x, 0)),
        'CE Vol': df['ce_volume'].apply(lambda x: format_number(x, 0)),
        'PE Vol': df['pe_volume'].apply(lambda x: format_number(x, 0)),
        'PCR (OI)': df['pcr_oi'].apply(lambda x: format_number(x, 4)),
        'PCR (OI Δ)': df['pcr_oi_change'].apply(lambda x: format_number(x, 4)),
        'PCR (Vol)': df['pcr_volume'].apply(lambda x: format_number(x, 4)),
        'Bias': df['strike_bias']
    })

    # Style the dataframe
    def style_bias(row):
        bias = row['Bias']
        color = get_bias_color(bias)
        return ['' for _ in range(len(row) - 1)] + [f'background-color: {color}; color: white; font-weight: bold']

    styled_df = display_df.style.apply(style_bias, axis=1)

    # Display table
    st.dataframe(
        styled_df,
        use_container_width=True,
        height=450
    )

    # Summary statistics
    st.markdown("#### 📊 Zone Summary")
    col1, col2, col3, col4 = st.columns(4)

    total_ce_oi = df['ce_oi'].sum()
    total_pe_oi = df['pe_oi'].sum()
    zone_pcr_oi = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 0

    bullish_count = len(df[df['strike_bias'] == 'BULLISH'])
    bearish_count = len(df[df['strike_bias'] == 'BEARISH'])
    neutral_count = len(df[df['strike_bias'] == 'NEUTRAL'])

    with col1:
        st.metric("Total CE OI", format_number(total_ce_oi, 0))
    with col2:
        st.metric("Total PE OI", format_number(total_pe_oi, 0))
    with col3:
        pcr_color = "🟢" if zone_pcr_oi > 1.2 else ("🔴" if zone_pcr_oi < 0.8 else "🟡")
        st.metric("Zone PCR", f"{pcr_color} {zone_pcr_oi:.4f}")
    with col4:
        st.metric("Bias Distribution", f"🟢{bullish_count} | 🟡{neutral_count} | 🔴{bearish_count}")

def render_atm_zone_bias_analysis():
    """Main function to render ATM Zone Bias Analysis"""
    st.markdown("## 🎯 Detailed ATM Zone Bias Analysis")
    st.caption("📌 Using shared option chain data from centralized manager")
    st.markdown("---")

    # Symbol selection
    symbols = ['NIFTY', 'SENSEX', 'BANKNIFTY', 'FINNIFTY']

    # Create tabs for each symbol
    tabs = st.tabs([f"📊 {symbol}" for symbol in symbols])

    # Get option chain manager and analyzer
    option_manager = get_option_chain_manager()
    analyzer = DhanOptionChainAnalyzer()
    supabase = get_supabase_manager()

    for idx, symbol in enumerate(symbols):
        with tabs[idx]:
            # Add save to DB and view history buttons
            col1, col2 = st.columns([1, 3])
            with col1:
                if supabase.is_enabled():
                    save_to_db = st.checkbox("💾 Save to DB", value=False, key=f"save_{symbol}")
                else:
                    st.caption("⚠️ Supabase not configured")
                    save_to_db = False
            with col2:
                if supabase.is_enabled():
                    view_history = st.button(f"📜 View History", key=f"history_{symbol}")
                else:
                    view_history = False

            # Check if data exists in session state
            session_key = f"atm_zone_{symbol}"

            # Get shared option chain data from manager
            oc_data = option_manager.get_option_chain(symbol, auto_fetch=False)

            # If data available, calculate ATM zone bias
            if oc_data and oc_data.get('success'):
                # Calculate ATM zone bias using the shared data
                # We need to call the calculation part only
                if session_key not in st.session_state or option_manager.get_fetch_timestamp():
                    try:
                        # Use the existing analyzer method but with shared data
                        # Pass the records from shared data
                        atm_data = analyzer.calculate_atm_zone_bias(symbol)

                        if atm_data.get('success'):
                            st.session_state[session_key] = atm_data

                            # Save to Supabase if enabled
                            if save_to_db and supabase.is_enabled():
                                success = supabase.save_atm_zone_bias(
                                    symbol=symbol,
                                    spot_price=atm_data['spot_price'],
                                    atm_zone_data=atm_data['atm_zone_data']
                                )
                                if success:
                                    st.success(f"✅ Data saved to database")
                                else:
                                    st.warning(f"⚠️ Failed to save to database")
                    except Exception as e:
                        st.error(f"❌ Error calculating ATM zone bias: {str(e)}")

            # Display the table
            if session_key in st.session_state:
                display_atm_zone_table(symbol, st.session_state[session_key])
            else:
                st.info(f"ℹ️ Click 'Refresh All' button above to load ATM zone bias data")

            # Show history if requested
            if view_history and supabase.is_enabled():
                st.markdown("---")
                st.markdown("### 📜 Historical Data (Last 24 Hours)")

                history_df = supabase.get_atm_zone_bias_history(symbol, hours=24)

                if history_df is not None and not history_df.empty:
                    # Show unique timestamps
                    timestamps = history_df['timestamp'].unique()
                    st.caption(f"Found {len(timestamps)} snapshots in last 24 hours")

                    # Group by timestamp and show summary
                    for ts in sorted(timestamps, reverse=True)[:5]:  # Show last 5 snapshots
                        ts_data = history_df[history_df['timestamp'] == ts]

                        with st.expander(f"📅 {ts}"):
                            # Display data
                            display_cols = ['strike_price', 'strike_offset', 'ce_oi', 'pe_oi',
                                          'pcr_oi', 'pcr_oi_change', 'pcr_volume', 'strike_bias']

                            st.dataframe(
                                ts_data[display_cols].sort_values('strike_offset'),
                                use_container_width=True
                            )
                else:
                    st.info("ℹ️ No historical data available")

    # Database status at bottom
    if supabase.is_enabled():
        st.markdown("---")
        st.markdown("### 💾 Database Status")
        stats = supabase.get_table_stats()

        if stats:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("ATM Zone Records", stats.get('atm_zone_bias', 0))
            with col2:
                st.metric("Option Chain Snapshots", stats.get('option_chain_snapshots', 0))
            with col3:
                st.metric("Trading Signals", stats.get('trading_signals', 0))
            with col4:
                st.metric("Bias History", stats.get('bias_analysis_history', 0))

            # Test connection
            if st.button("🧪 Test Database Connection"):
                if supabase.test_connection():
                    st.success("✅ Database connection successful")
                else:
                    st.error("❌ Database connection failed")
