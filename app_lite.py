"""
NIFTY SENSEX Trader - LITE VERSION
Simplified trading app with essential bias indicators
Focus: Fast, lightweight, all bias indicators for NIFTY
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import time
from typing import Dict, Optional

# Import from existing modules
from config import IST
from bias_analysis import BiasAnalysisPro
from market_hours_scheduler import is_within_trading_hours
from lite_helpers import (
    get_current_price,
    get_intraday_data,
    get_option_chain_dhan,
    calculate_pcr_metrics,
    calculate_atm_zone_bias,
    format_number,
    get_bias_color,
    get_bias_emoji,
    INDEX_CONFIG
)

# Page configuration
st.set_page_config(
    page_title="NIFTY Trader - Lite",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for compact display
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
    }
    .bias-card {
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
        border-left: 4px solid;
    }
    .bullish { border-color: #00cc00; background-color: #e6ffe6; }
    .bearish { border-color: #ff0000; background-color: #ffe6e6; }
    .neutral { border-color: #808080; background-color: #f5f5f5; }
</style>
""", unsafe_allow_html=True)


def display_header():
    """Display app header with market status"""
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.title("📈 NIFTY SENSEX Trader - LITE")

    with col2:
        market_open = is_within_trading_hours()
        status = "🟢 LIVE" if market_open else "🔴 CLOSED"
        st.metric("Market Status", status)

    with col3:
        current_time = datetime.now(IST).strftime("%H:%M:%S IST")
        st.metric("Time", current_time)

    st.markdown("---")


def display_technical_bias(symbol: str, index_name: str):
    """Display technical bias analysis"""
    st.subheader(f"📊 Technical Bias - {index_name}")

    # Get intraday data
    data = get_intraday_data(INDEX_CONFIG[symbol]['symbol'])

    if data is None or data.empty:
        st.warning("Unable to fetch technical data")
        return

    # Calculate technical indicators using BiasAnalysisPro
    bias_analyzer = BiasAnalysisPro()

    try:
        # Get all technical biases
        tech_data = {
            'close': data['Close'].values,
            'high': data['High'].values,
            'low': data['Low'].values,
            'volume': data['Volume'].values
        }

        # Calculate individual biases
        vd_bias = bias_analyzer.calculate_volume_delta_bias(tech_data)
        hvp_bias = bias_analyzer.calculate_hvp_bias(tech_data)
        vob_bias = bias_analyzer.calculate_vob_bias(tech_data)
        ob_bias = bias_analyzer.calculate_order_blocks_bias(tech_data)
        rsi_bias = bias_analyzer.calculate_rsi_bias(tech_data)
        dmi_bias = bias_analyzer.calculate_dmi_bias(tech_data)
        vidya_bias = bias_analyzer.calculate_vidya_bias(tech_data)
        mfi_bias = bias_analyzer.calculate_mfi_bias(tech_data)

        # Display in grid
        col1, col2, col3, col4 = st.columns(4)

        indicators = [
            ("Volume Delta", vd_bias),
            ("HVP", hvp_bias),
            ("VOB", vob_bias),
            ("Order Blocks", ob_bias),
            ("RSI", rsi_bias),
            ("DMI", dmi_bias),
            ("VIDYA", vidya_bias),
            ("MFI", mfi_bias)
        ]

        for i, (name, bias) in enumerate(indicators):
            col = [col1, col2, col3, col4][i % 4]
            with col:
                emoji = get_bias_emoji(bias)
                st.metric(name, f"{emoji} {bias}")

        # Overall technical bias
        bullish_count = sum(1 for _, bias in indicators if bias.lower() == 'bullish')
        bearish_count = sum(1 for _, bias in indicators if bias.lower() == 'bearish')

        if bullish_count > bearish_count:
            overall = "Bullish"
        elif bearish_count > bullish_count:
            overall = "Bearish"
        else:
            overall = "Neutral"

        st.markdown(f"""
        <div class="bias-card {overall.lower()}">
            <h4>{get_bias_emoji(overall)} Overall Technical Bias: {overall}</h4>
            <p>Bullish: {bullish_count} | Bearish: {bearish_count} | Neutral: {8 - bullish_count - bearish_count}</p>
        </div>
        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error calculating technical bias: {str(e)}")


def display_pcr_analysis(symbol: str, index_name: str):
    """Display PCR (Put-Call Ratio) analysis"""
    st.subheader(f"📊 PCR Analysis - {index_name}")

    # Get option chain data
    oc_data = get_option_chain_dhan(symbol, INDEX_CONFIG[symbol]['security_id'])

    if oc_data is None:
        st.warning("Unable to fetch option chain data")
        return

    # Calculate PCR metrics
    pcr_metrics = calculate_pcr_metrics(oc_data)

    if not pcr_metrics:
        st.warning("Unable to calculate PCR metrics")
        return

    # Display PCR values
    col1, col2, col3 = st.columns(3)

    with col1:
        pcr_oi = pcr_metrics['pcr_oi']
        bias = "Bullish" if pcr_oi > 1.2 else "Bearish" if pcr_oi < 0.8 else "Neutral"
        st.metric("PCR (OI)", f"{pcr_oi:.3f}", delta=bias)

    with col2:
        pcr_oi_change = pcr_metrics['pcr_oi_change']
        bias = "Bullish" if pcr_oi_change > 1.2 else "Bearish" if pcr_oi_change < 0.8 else "Neutral"
        st.metric("PCR (OI Change)", f"{pcr_oi_change:.3f}", delta=bias)

    with col3:
        pcr_volume = pcr_metrics['pcr_volume']
        bias = "Bullish" if pcr_volume > 1.2 else "Bearish" if pcr_volume < 0.8 else "Neutral"
        st.metric("PCR (Volume)", f"{pcr_volume:.3f}", delta=bias)

    # CE/PE breakdown
    st.markdown("#### Call vs Put Breakdown")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**📞 Call (CE) Data**")
        st.metric("Total CE OI", format_number(pcr_metrics['total_ce_oi']))
        st.metric("CE OI Change", format_number(pcr_metrics['total_ce_oi_change']))
        st.metric("CE Volume", format_number(pcr_metrics['total_ce_volume']))

    with col2:
        st.markdown("**📈 Put (PE) Data**")
        st.metric("Total PE OI", format_number(pcr_metrics['total_pe_oi']))
        st.metric("PE OI Change", format_number(pcr_metrics['total_pe_oi_change']))
        st.metric("PE Volume", format_number(pcr_metrics['total_pe_volume']))


def display_atm_zone_bias(symbol: str, index_name: str):
    """Display ATM Zone Bias (ATM ±5 strikes)"""
    st.subheader(f"🎯 ATM Zone Bias - {index_name}")

    # Get option chain data
    oc_data = get_option_chain_dhan(symbol, INDEX_CONFIG[symbol]['security_id'])

    if oc_data is None:
        st.warning("Unable to fetch option chain data")
        return

    # Calculate ATM zone bias
    atm_analysis = calculate_atm_zone_bias(oc_data, atm_range=5)

    if not atm_analysis:
        st.warning("Unable to calculate ATM zone bias")
        return

    # Display summary
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Current Price", f"₹{atm_analysis['current_price']:,.2f}")

    with col2:
        st.metric("ATM Strike", f"₹{atm_analysis['atm_strike']:,.0f}")

    with col3:
        st.metric("Zone PCR", f"{atm_analysis['zone_pcr']:.3f}")

    with col4:
        emoji = get_bias_emoji(atm_analysis['zone_bias'])
        st.metric("Zone Bias", f"{emoji} {atm_analysis['zone_bias']}")

    # Strike-wise analysis
    st.markdown("#### Strike-wise Analysis (ATM ±5)")

    strike_df = pd.DataFrame(atm_analysis['strike_analysis'])

    if not strike_df.empty:
        # Format DataFrame
        strike_df['Strike'] = strike_df['strike'].apply(lambda x: f"₹{x:,.0f}")
        strike_df['ATM'] = strike_df['is_atm'].apply(lambda x: "✓" if x else "")
        strike_df['CE OI'] = strike_df['ce_oi'].apply(format_number)
        strike_df['PE OI'] = strike_df['pe_oi'].apply(format_number)
        strike_df['PCR'] = strike_df['pcr'].apply(lambda x: f"{x:.3f}")
        strike_df['Bias'] = strike_df['bias'].apply(lambda x: f"{get_bias_emoji(x)} {x}")

        # Display table
        display_df = strike_df[['Strike', 'ATM', 'CE OI', 'PE OI', 'PCR', 'Bias']]
        st.dataframe(display_df, use_container_width=True, hide_index=True)


def display_overall_market_bias(symbol: str, index_name: str):
    """Display overall market bias summary"""
    st.subheader(f"🌍 Overall Market Bias - {index_name}")

    # This would aggregate all bias sources
    # For lite version, we'll show a summary

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Technical Bias**")
        # Placeholder - would get actual calculated bias
        st.info("Check Technical Bias section above")

    with col2:
        st.markdown("**PCR Bias**")
        st.info("Check PCR Analysis section above")

    with col3:
        st.markdown("**ATM Zone Bias**")
        st.info("Check ATM Zone section above")

    st.markdown("""
    <div class="bias-card neutral">
        <h4>ℹ️ Consensus Bias</h4>
        <p>The overall market bias is determined by aggregating signals from Technical Indicators, PCR Analysis, and ATM Zone Bias.</p>
        <p><strong>Action:</strong> Review all bias sections above for comprehensive analysis.</p>
    </div>
    """, unsafe_allow_html=True)


def main():
    """Main application function"""
    display_header()

    # Symbol selection
    selected_symbol = st.selectbox(
        "Select Index",
        options=list(INDEX_CONFIG.keys()),
        format_func=lambda x: INDEX_CONFIG[x]['name']
    )

    index_name = INDEX_CONFIG[selected_symbol]['name']

    # Get current price
    current_price = get_current_price(INDEX_CONFIG[selected_symbol]['symbol'])

    if current_price:
        st.markdown(f"### Current Price: ₹{current_price:,.2f}")
    else:
        st.warning("Unable to fetch current price")

    st.markdown("---")

    # Display all bias sections
    with st.spinner("Loading Technical Bias..."):
        display_technical_bias(selected_symbol, index_name)

    st.markdown("---")

    with st.spinner("Loading PCR Analysis..."):
        display_pcr_analysis(selected_symbol, index_name)

    st.markdown("---")

    with st.spinner("Loading ATM Zone Bias..."):
        display_atm_zone_bias(selected_symbol, index_name)

    st.markdown("---")

    with st.spinner("Loading Overall Market Bias..."):
        display_overall_market_bias(selected_symbol, index_name)

    # Footer
    st.markdown("---")
    st.markdown(f"**Last Updated:** {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')}")
    st.markdown("**Lite Version** - Fast & Lightweight | All Essential Bias Indicators")

    # Auto-refresh every 30 seconds during market hours
    if is_within_trading_hours():
        time.sleep(30)
        st.rerun()


if __name__ == "__main__":
    main()
