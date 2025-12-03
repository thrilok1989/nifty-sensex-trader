"""
Intraday Momentum Component
============================

Displays intraday option chain momentum changes:
- Recent 15-min momentum vs Full Day
- Morning vs Afternoon bias comparison
- Reversal detection alerts
- Fresh OI building analysis
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from config import COLORS
from intraday_snapshot_manager import get_snapshot_manager
from option_chain_manager import get_option_chain_manager


def display_momentum_comparison(symbol: str):
    """
    Display momentum comparison: Recent vs Full Day

    Args:
        symbol: Trading symbol (NIFTY, SENSEX, etc.)
    """
    snapshot_manager = get_snapshot_manager()

    # Get recent changes
    recent_15min = snapshot_manager.get_recent_change(symbol, minutes=15)
    recent_30min = snapshot_manager.get_recent_change(symbol, minutes=30)
    recent_1hour = snapshot_manager.get_recent_change(symbol, minutes=60)
    full_day = snapshot_manager.get_recent_change(symbol, minutes=360)

    snapshot_count = snapshot_manager.get_snapshot_count(symbol)

    # Header
    st.markdown(f"### 📈 {symbol} - Intraday Momentum Tracker")
    st.caption(f"📊 Tracking {snapshot_count} snapshots")

    if snapshot_count < 2:
        st.warning("⏳ Collecting snapshots... Need at least 2 snapshots (15 mins) to show momentum")
        st.caption("💡 Snapshots are saved automatically every 15 minutes when you click 'Refresh All'")
        return

    # Reversal detection
    reversal_data = snapshot_manager.detect_reversal(symbol)

    if reversal_data and reversal_data['is_reversal']:
        st.error(f"""
        🚨 **REVERSAL ALERT!**

        **Recent Trend (Last 15 mins):** {reversal_data['recent_trend']}
        **Full Day Trend:** {reversal_data['full_day_trend']}
        **ATM Strike:** {reversal_data['atm_strike']}

        ⚠️ Market momentum has shifted! Recent activity shows {reversal_data['recent_trend']} bias
        while full day is {reversal_data['full_day_trend']}. Watch for confirmation!
        """)
    elif reversal_data:
        if reversal_data['recent_trend'] == reversal_data['full_day_trend']:
            st.success(f"✅ **Trend Confirmed:** {reversal_data['recent_trend']} (Recent matches Full Day)")

    st.markdown("---")

    # Momentum comparison table
    st.markdown("#### 🕐 Momentum Comparison: Recent vs Full Day")

    momentum_data = []

    for period_name, period_data in [
        ("Last 15 Minutes", recent_15min),
        ("Last 30 Minutes", recent_30min),
        ("Last 1 Hour", recent_1hour),
        ("Full Day (6 Hours)", full_day)
    ]:
        if period_data:
            # Calculate ATM strikes total
            strike_intervals = {'NIFTY': 50, 'BANKNIFTY': 100, 'FINNIFTY': 50, 'SENSEX': 100}
            strike_interval = strike_intervals.get(symbol, 50)

            # Get spot price from option manager
            option_manager = get_option_chain_manager()
            oc_data = option_manager.get_option_chain(symbol, auto_fetch=False)
            if oc_data:
                spot_price = oc_data.get('spot_price', 0)
                atm_strike = round(spot_price / strike_interval) * strike_interval
                atm_strikes = [atm_strike + (i * strike_interval) for i in range(-2, 3)]

                # Sum ATM changes
                ce_oi_atm = sum(period_data['strikes'].get(s, {}).get('ce_oi_change', 0) for s in atm_strikes)
                pe_oi_atm = sum(period_data['strikes'].get(s, {}).get('pe_oi_change', 0) for s in atm_strikes)

                # Determine bias
                if abs(pe_oi_atm) > abs(ce_oi_atm) and pe_oi_atm > 0:
                    bias = "🟢 BULLISH"
                elif abs(ce_oi_atm) > abs(pe_oi_atm) and ce_oi_atm > 0:
                    bias = "🔴 BEARISH"
                else:
                    bias = "🟡 NEUTRAL"

                momentum_data.append({
                    'Period': period_name,
                    'CE OI Δ (ATM±2)': f"{ce_oi_atm:,.0f}",
                    'PE OI Δ (ATM±2)': f"{pe_oi_atm:,.0f}",
                    'Net OI Δ': f"{pe_oi_atm - ce_oi_atm:,.0f}",
                    'Bias': bias,
                    'Spot Δ': f"{period_data.get('spot_change', 0):+.2f}"
                })

    if momentum_data:
        df = pd.DataFrame(momentum_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Morning vs Afternoon comparison
    st.markdown("#### 🌅 Session Comparison: Morning vs Afternoon")

    morning_bias = snapshot_manager.get_period_bias(symbol, 'morning')
    afternoon_bias = snapshot_manager.get_period_bias(symbol, 'afternoon')

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### 🌅 Morning Session (9:15 AM - 12:00 PM)")
        if morning_bias:
            bias_color = COLORS.get('bullish') if 'BULLISH' in morning_bias['bias'] else (
                COLORS.get('bearish') if 'BEARISH' in morning_bias['bias'] else COLORS.get('neutral')
            )

            st.markdown(f"**Bias:** <span style='color: white; background-color: {bias_color}; padding: 5px 10px; border-radius: 5px;'>{morning_bias['bias']}</span>", unsafe_allow_html=True)

            col1_1, col1_2 = st.columns(2)
            with col1_1:
                st.metric("CE OI Change", f"{morning_bias['ce_oi_change']:,.0f}")
                st.metric("CE Volume", f"{morning_bias['ce_volume']:,.0f}")
            with col1_2:
                st.metric("PE OI Change", f"{morning_bias['pe_oi_change']:,.0f}")
                st.metric("PE Volume", f"{morning_bias['pe_volume']:,.0f}")

            st.metric("Spot Movement", f"{morning_bias['spot_change']:+.2f}")

            start_time = morning_bias['start_time']
            end_time = morning_bias['end_time']
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time)
            if isinstance(end_time, str):
                end_time = datetime.fromisoformat(end_time)

            st.caption(f"📅 {start_time.strftime('%I:%M %p')} to {end_time.strftime('%I:%M %p')}")
        else:
            st.info("⏳ No morning data yet. Market opens at 9:15 AM.")

    with col2:
        st.markdown("##### 🌆 Afternoon Session (12:00 PM - 3:30 PM)")
        if afternoon_bias:
            bias_color = COLORS.get('bullish') if 'BULLISH' in afternoon_bias['bias'] else (
                COLORS.get('bearish') if 'BEARISH' in afternoon_bias['bias'] else COLORS.get('neutral')
            )

            st.markdown(f"**Bias:** <span style='color: white; background-color: {bias_color}; padding: 5px 10px; border-radius: 5px;'>{afternoon_bias['bias']}</span>", unsafe_allow_html=True)

            col2_1, col2_2 = st.columns(2)
            with col2_1:
                st.metric("CE OI Change", f"{afternoon_bias['ce_oi_change']:,.0f}")
                st.metric("CE Volume", f"{afternoon_bias['ce_volume']:,.0f}")
            with col2_2:
                st.metric("PE OI Change", f"{afternoon_bias['pe_oi_change']:,.0f}")
                st.metric("PE Volume", f"{afternoon_bias['pe_volume']:,.0f}")

            st.metric("Spot Movement", f"{afternoon_bias['spot_change']:+.2f}")

            start_time = afternoon_bias['start_time']
            end_time = afternoon_bias['end_time']
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time)
            if isinstance(end_time, str):
                end_time = datetime.fromisoformat(end_time)

            st.caption(f"📅 {start_time.strftime('%I:%M %p')} to {end_time.strftime('%I:%M %p')}")
        else:
            st.info("⏳ No afternoon data yet. Afternoon starts at 12:00 PM.")

    # Session shift detection
    if morning_bias and afternoon_bias:
        if morning_bias['bias'] != afternoon_bias['bias']:
            st.warning(f"""
            ⚠️ **Session Shift Detected!**

            Morning was **{morning_bias['bias']}** but Afternoon is **{afternoon_bias['bias']}**

            This indicates a change in market sentiment during the day.
            """)
        else:
            st.success(f"✅ **Consistent Bias:** Both sessions are {morning_bias['bias']}")

    # Explanation
    with st.expander("📖 How to Use Intraday Momentum"):
        st.markdown("""
        ### Understanding Intraday Momentum

        #### 🎯 Key Insights:

        1. **Recent Momentum (15 mins):**
           - Shows FRESH option buying/selling happening NOW
           - More relevant for immediate trades than full day data

        2. **Reversal Alert:**
           - Triggers when recent trend ≠ full day trend
           - Example: Full day BEARISH but last 15 mins BULLISH = Possible reversal

        3. **Morning vs Afternoon:**
           - Morning (9:15 AM - 12:00 PM): Opening sentiment
           - Afternoon (12:00 PM - 3:30 PM): Closing bias
           - Shifts between sessions = Change in control

        #### 💡 Trading Tips:

        - **Trust Recent Over Full Day:** Last 15-30 mins shows active sentiment
        - **Watch for Reversals:** When recent opposes full day, momentum is shifting
        - **Session Consistency:** Same bias both sessions = Strong trend
        - **Session Shift:** Different bias = Indecision or reversal

        #### 🔔 Alert Priority:
        1. **🚨 Reversal Alert** (Highest) - Immediate action
        2. **⚠️ Session Shift** (Medium) - Watch confirmation
        3. **✅ Trend Confirmed** (Low) - Stay with trend

        ### How Snapshots Work:
        - App saves option chain snapshot every 15 minutes
        - Calculates delta between snapshots
        - Shows you NET changes (not cumulative)
        - Stored in Supabase for persistent tracking
        """)


def render_intraday_momentum_analysis():
    """Main function to render Intraday Momentum Analysis"""
    st.markdown("## 📊 Intraday Momentum & Reversal Tracker")
    st.markdown("**Track Fresh OI Building | Detect Reversals | Morning vs Afternoon Bias**")
    st.caption("📌 Using snapshot-based delta analysis (15-min intervals)")
    st.markdown("---")

    # Info banner
    st.info("""
    💡 **How This Works:**
    - Every time you click "Refresh All", a snapshot is saved
    - App calculates the DIFFERENCE between snapshots
    - Shows you FRESH momentum (not cumulative from 9:15 AM)
    - Detects when recent trend differs from full day (reversals!)
    """)

    # Symbol selection
    symbols = ['NIFTY', 'SENSEX', 'BANKNIFTY', 'FINNIFTY']

    # Create tabs for each symbol
    tabs = st.tabs([f"📊 {symbol}" for symbol in symbols])

    snapshot_manager = get_snapshot_manager()

    for idx, symbol in enumerate(symbols):
        with tabs[idx]:
            display_momentum_comparison(symbol)

    # Snapshot management section
    st.markdown("---")
    st.markdown("### 🗄️ Snapshot Management")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_snapshots = sum(snapshot_manager.get_snapshot_count(s) for s in symbols)
        st.metric("Total Snapshots", total_snapshots)

    with col2:
        latest = snapshot_manager._get_latest_snapshot_time()
        if latest:
            time_str = latest.strftime('%I:%M:%S %p') if isinstance(latest, datetime) else latest
            st.metric("Last Snapshot", time_str)
        else:
            st.metric("Last Snapshot", "None")

    with col3:
        st.caption("Snapshot Counts:")
        for symbol in symbols:
            count = snapshot_manager.get_snapshot_count(symbol)
            st.caption(f"• {symbol}: {count}")

    with col4:
        if st.button("🗑️ Clear Old Snapshots", help="Clear snapshots older than 24 hours"):
            snapshot_manager.clear_old_snapshots(hours=24)
            st.success("✅ Cleared old snapshots")
            st.rerun()
