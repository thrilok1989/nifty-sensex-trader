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
from market_hours_scheduler import is_market_open
from lite_helpers import (
    get_current_price,
    get_intraday_data,
    fetch_dhan_option_chain,
    get_nearest_expiry,
    calculate_pcr_metrics,
    get_atm_zone_bias,
    format_number,
    get_bias_color,
    get_bias_emoji
)

# Page configuration
st.set_page_config(
    page_title="NIFTY Trader Lite",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for lite version
st.markdown("""
<style>
    .main {
        padding: 1rem;
    }
    .stMetric {
        background-color: #1e1e1e;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #333;
    }
    .bias-card {
        background-color: #1e1e1e;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 2px solid #333;
        margin: 1rem 0;
    }
    .bullish {
        border-color: #00ff00;
        color: #00ff00;
    }
    .bearish {
        border-color: #ff0000;
        color: #ff0000;
    }
    .neutral {
        border-color: #ffff00;
        color: #ffff00;
    }
    h1 {
        color: #00d4ff;
        text-align: center;
        margin-bottom: 1rem;
    }
    h2 {
        color: #00d4ff;
        border-bottom: 2px solid #00d4ff;
        padding-bottom: 0.5rem;
        margin-top: 2rem;
    }
    h3 {
        color: #00d4ff;
        margin-top: 1rem;
    }
    .indicator-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }
    .indicator-item {
        background-color: #2a2a2a;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    .dataframe {
        font-size: 0.9rem;
    }
    .market-status {
        text-align: center;
        padding: 0.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        font-weight: bold;
    }
    .market-open {
        background-color: #00ff0033;
        color: #00ff00;
    }
    .market-closed {
        background-color: #ff000033;
        color: #ff0000;
    }
    .overall-bias {
        font-size: 2rem;
        font-weight: bold;
        text-align: center;
        padding: 2rem;
        border-radius: 1rem;
        margin: 2rem 0;
        background: linear-gradient(135deg, #1e1e1e 0%, #2a2a2a 100%);
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown("# 📈 NIFTY TRADER LITE")

# Initialize session state
if 'last_update' not in st.session_state:
    st.session_state.last_update = None

# Sidebar for settings
with st.sidebar:
    st.header("⚙️ Settings")

    symbol_map = {
        'NIFTY 50': '^NSEI',
        'SENSEX': '^BSESN',
        'BANK NIFTY': '^NSEBANK'
    }

    selected_index = st.selectbox(
        "Select Index",
        options=list(symbol_map.keys()),
        index=0
    )

    symbol = symbol_map[selected_index]
    underlying = selected_index.split()[0]  # 'NIFTY' or 'SENSEX' or 'BANK'

    auto_refresh = st.checkbox("Auto Refresh", value=True)
    refresh_interval = st.slider("Refresh Interval (seconds)", 60, 300, 120)

    st.markdown("---")
    st.markdown("### 📊 About Lite Version")
    st.markdown("""
    **Features:**
    - ✅ Technical Bias (8 indicators)
    - ✅ PCR Analysis
    - ✅ Option Chain Bias
    - ✅ ATM Zone Bias
    - ✅ Overall Market Bias

    **Removed for Speed:**
    - ❌ Advanced Charts
    - ❌ Multiple Tabs
    - ❌ Database Integration
    - ❌ Trade Logging
    """)

# Market status
market_open = is_market_open()
market_status_html = f"""
<div class="market-status {'market-open' if market_open else 'market-closed'}">
    {'🟢 MARKET OPEN' if market_open else '🔴 MARKET CLOSED'}
</div>
"""
st.markdown(market_status_html, unsafe_allow_html=True)

# Main content
def load_data():
    """Load all data for analysis"""
    data = {
        'symbol': symbol,
        'underlying': underlying,
        'timestamp': datetime.now(IST),
        'current_price': None,
        'intraday_data': None,
        'technical_bias': None,
        'pcr_metrics': None,
        'atm_zone': None,
        'option_chain': None
    }

    with st.spinner(f"📡 Loading {selected_index} data..."):
        # Get current price
        data['current_price'] = get_current_price(symbol)

        # Get intraday data for technical analysis
        data['intraday_data'] = get_intraday_data(symbol, days=7)

        # Get option chain data (only for NIFTY and BANKNIFTY)
        if underlying in ['NIFTY', 'BANK', 'BANKNIFTY']:
            expiry = get_nearest_expiry()
            underlying_key = 'BANKNIFTY' if underlying == 'BANK' else underlying
            data['option_chain'] = fetch_dhan_option_chain(underlying_key, expiry)

            if data['option_chain']:
                # Calculate PCR metrics
                data['pcr_metrics'] = calculate_pcr_metrics(data['option_chain'])

                # Calculate ATM zone bias
                if data['current_price']:
                    data['atm_zone'] = get_atm_zone_bias(
                        data['option_chain'],
                        data['current_price'],
                        num_strikes=5
                    )

    return data


def display_technical_bias(data: Dict):
    """Display Technical Bias section"""
    st.markdown("## 🎯 TECHNICAL BIAS (8 Indicators)")

    # Get intraday data and check if it's None or empty
    intraday_data = data.get('intraday_data')
    if intraday_data is None or (isinstance(intraday_data, pd.DataFrame) and intraday_data.empty):
        st.warning("⚠️ Unable to fetch intraday data for technical analysis")
        return

    with st.spinner("Calculating technical indicators..."):
        try:
            # Initialize bias analyzer
            analyzer = BiasAnalysisPro()

            # Analyze bias
            bias_result = analyzer.analyze_all_bias_indicators(
                intraday_data,
                symbol=data['underlying']
            )

            if not bias_result:
                st.error("❌ Failed to calculate technical bias")
                return

            # Store in data
            data['technical_bias'] = bias_result

            # Display overall bias
            overall_bias = bias_result.get('overall_bias', 'NEUTRAL')
            overall_percentage = bias_result.get('overall_percentage', 0)
            bias_color = get_bias_color(overall_bias)
            bias_emoji = get_bias_emoji(overall_bias)

            st.markdown(f"""
            <div class="bias-card {overall_bias.lower()}">
                <h2 style="text-align: center; margin: 0;">
                    {bias_emoji} OVERALL: {overall_bias}
                </h2>
                <p style="text-align: center; font-size: 1.5rem; margin: 0.5rem 0 0 0;">
                    {overall_percentage:+.1f}%
                </p>
            </div>
            """, unsafe_allow_html=True)

            # Display individual indicators
            st.markdown("### 📊 Individual Indicators")

            indicators = bias_result.get('indicators', {})

            # Create 4 columns for 8 indicators
            col1, col2, col3, col4 = st.columns(4)

            indicator_list = [
                ('Volume Delta', 'volume_delta'),
                ('HVP', 'hvp'),
                ('VOB', 'vob'),
                ('Order Blocks', 'order_blocks'),
                ('RSI', 'rsi'),
                ('DMI', 'dmi'),
                ('VIDYA', 'vidya'),
                ('MFI', 'mfi')
            ]

            for idx, (name, key) in enumerate(indicator_list):
                col = [col1, col2, col3, col4][idx % 4]

                with col:
                    indicator_data = indicators.get(key, {})
                    indicator_bias = indicator_data.get('bias', 'NEUTRAL')
                    indicator_emoji = get_bias_emoji(indicator_bias)

                    st.markdown(f"""
                    <div class="indicator-item">
                        <div style="font-size: 1.5rem;">{indicator_emoji}</div>
                        <div style="font-weight: bold; margin: 0.5rem 0;">{name}</div>
                        <div style="color: {get_bias_color(indicator_bias)};">{indicator_bias}</div>
                    </div>
                    """, unsafe_allow_html=True)

            # Display bias breakdown
            st.markdown("### 📈 Bias Breakdown")

            col1, col2, col3 = st.columns(3)

            bullish_count = sum(1 for ind in indicators.values() if ind.get('bias') == 'BULLISH')
            bearish_count = sum(1 for ind in indicators.values() if ind.get('bias') == 'BEARISH')
            neutral_count = sum(1 for ind in indicators.values() if ind.get('bias') == 'NEUTRAL')

            with col1:
                st.metric("🟢 Bullish", f"{bullish_count}/8")
            with col2:
                st.metric("🔴 Bearish", f"{bearish_count}/8")
            with col3:
                st.metric("🟡 Neutral", f"{neutral_count}/8")

        except Exception as e:
            st.error(f"❌ Error calculating technical bias: {str(e)}")


def display_pcr_bias(data: Dict):
    """Display PCR Bias section"""
    st.markdown("## 📊 PCR ANALYSIS (Put-Call Ratio)")

    if not data['pcr_metrics']:
        st.warning("⚠️ Unable to fetch option chain data for PCR analysis")
        return

    pcr = data['pcr_metrics']

    # Display PCR bias
    bias = pcr.get('bias', 'NEUTRAL')
    pcr_oi = pcr.get('pcr_oi', 0)
    bias_emoji = get_bias_emoji(bias)

    st.markdown(f"""
    <div class="bias-card {bias.lower()}">
        <h2 style="text-align: center; margin: 0;">
            {bias_emoji} PCR BIAS: {bias}
        </h2>
        <p style="text-align: center; font-size: 1.5rem; margin: 0.5rem 0 0 0;">
            PCR (OI): {pcr_oi}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Display PCR metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("PCR (OI)", f"{pcr.get('pcr_oi', 0):.2f}")
    with col2:
        st.metric("PCR (OI Change)", f"{pcr.get('pcr_oi_change', 0):.2f}")
    with col3:
        st.metric("PCR (Volume)", f"{pcr.get('pcr_volume', 0):.2f}")
    with col4:
        st.metric("Bias", bias)

    # Display OI breakdown
    st.markdown("### 📊 Open Interest Breakdown")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("🔴 Total CE OI", format_number(pcr.get('total_ce_oi', 0)))
        st.metric("🔴 Total CE Volume", format_number(pcr.get('total_ce_volume', 0)))

    with col2:
        st.metric("🟢 Total PE OI", format_number(pcr.get('total_pe_oi', 0)))
        st.metric("🟢 Total PE Volume", format_number(pcr.get('total_pe_volume', 0)))

    # PCR interpretation
    st.markdown("### 📖 PCR Interpretation")
    st.info("""
    - **PCR > 1.2**: BULLISH - More puts indicate support building
    - **PCR < 0.8**: BEARISH - More calls indicate resistance building
    - **PCR 0.8-1.2**: NEUTRAL - Balanced market
    """)


def display_atm_zone_bias(data: Dict):
    """Display ATM Zone Bias section"""
    st.markdown("## 🎯 ATM ZONE BIAS (ATM ±5 Strikes)")

    if not data['atm_zone'] or not data['atm_zone'].get('strikes'):
        st.warning("⚠️ Unable to calculate ATM zone bias")
        return

    atm_data = data['atm_zone']
    summary = atm_data.get('summary', {})
    strikes = atm_data.get('strikes', [])

    # Display zone bias
    zone_bias = summary.get('zone_bias', 'NEUTRAL')
    zone_pcr = summary.get('zone_pcr', 0)
    bias_emoji = get_bias_emoji(zone_bias)

    st.markdown(f"""
    <div class="bias-card {zone_bias.lower()}">
        <h2 style="text-align: center; margin: 0;">
            {bias_emoji} ATM ZONE BIAS: {zone_bias}
        </h2>
        <p style="text-align: center; font-size: 1.5rem; margin: 0.5rem 0 0 0;">
            Zone PCR: {zone_pcr}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Display zone summary
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Zone PCR", f"{zone_pcr:.2f}")
    with col2:
        st.metric("🟢 Bullish Strikes", summary.get('bullish_strikes', 0))
    with col3:
        st.metric("🔴 Bearish Strikes", summary.get('bearish_strikes', 0))
    with col4:
        st.metric("🟡 Neutral Strikes", summary.get('neutral_strikes', 0))

    # Display strike-wise data
    st.markdown("### 📊 Strike-wise Analysis")

    # Create DataFrame for display
    strike_df = pd.DataFrame(strikes)

    if not strike_df.empty:
        # Format columns
        strike_df['CE OI'] = strike_df['ce_oi'].apply(format_number)
        strike_df['PE OI'] = strike_df['pe_oi'].apply(format_number)
        strike_df['CE Vol'] = strike_df['ce_volume'].apply(format_number)
        strike_df['PE Vol'] = strike_df['pe_volume'].apply(format_number)

        # Select columns for display
        display_df = strike_df[[
            'strike', 'CE OI', 'PE OI', 'CE Vol', 'PE Vol',
            'pcr_oi', 'pcr_volume', 'bias'
        ]]

        # Highlight ATM row
        current_price = data['current_price']
        if current_price:
            display_df['Distance'] = abs(display_df['strike'] - current_price)
            atm_idx = display_df['Distance'].idxmin()

            st.markdown(f"**Current Price: {current_price:.2f}** | **ATM Strike: {display_df.loc[atm_idx, 'strike']:.0f}**")

        # Display table with styling
        def highlight_bias(row):
            if row['bias'] == 'BULLISH':
                return ['background-color: #00ff0033'] * len(row)
            elif row['bias'] == 'BEARISH':
                return ['background-color: #ff000033'] * len(row)
            else:
                return [''] * len(row)

        styled_df = display_df.drop('Distance', axis=1) if 'Distance' in display_df.columns else display_df
        st.dataframe(
            styled_df.style.apply(highlight_bias, axis=1),
            use_container_width=True,
            hide_index=True
        )


def display_overall_market_bias(data: Dict):
    """Display Overall Market Bias section"""
    st.markdown("## 🌍 OVERALL MARKET BIAS")

    # Collect all biases
    biases = []

    # Technical bias
    if data['technical_bias']:
        tech_bias = data['technical_bias'].get('overall_bias', 'NEUTRAL')
        tech_percentage = data['technical_bias'].get('overall_percentage', 0)
        biases.append({
            'source': 'Technical (8 Indicators)',
            'bias': tech_bias,
            'value': tech_percentage
        })

    # PCR bias
    if data['pcr_metrics']:
        pcr_bias = data['pcr_metrics'].get('bias', 'NEUTRAL')
        pcr_value = data['pcr_metrics'].get('pcr_oi', 0)
        biases.append({
            'source': 'PCR Analysis',
            'bias': pcr_bias,
            'value': pcr_value
        })

    # ATM zone bias
    if data['atm_zone']:
        zone_bias = data['atm_zone'].get('summary', {}).get('zone_bias', 'NEUTRAL')
        zone_pcr = data['atm_zone'].get('summary', {}).get('zone_pcr', 0)
        biases.append({
            'source': 'ATM Zone',
            'bias': zone_bias,
            'value': zone_pcr
        })

    if not biases:
        st.warning("⚠️ No bias data available")
        return

    # Calculate overall bias
    bullish_count = sum(1 for b in biases if b['bias'] == 'BULLISH')
    bearish_count = sum(1 for b in biases if b['bias'] == 'BEARISH')
    neutral_count = sum(1 for b in biases if b['bias'] == 'NEUTRAL')

    total_count = len(biases)

    if bullish_count > bearish_count and bullish_count >= total_count * 0.6:
        overall_bias = 'BULLISH'
    elif bearish_count > bullish_count and bearish_count >= total_count * 0.6:
        overall_bias = 'BEARISH'
    else:
        overall_bias = 'NEUTRAL'

    bias_emoji = get_bias_emoji(overall_bias)

    # Display overall bias
    st.markdown(f"""
    <div class="overall-bias" style="border: 3px solid {get_bias_color(overall_bias)};">
        <div style="font-size: 3rem;">{bias_emoji}</div>
        <div style="color: {get_bias_color(overall_bias)}; margin-top: 1rem;">
            {overall_bias}
        </div>
        <div style="font-size: 1.2rem; color: #888; margin-top: 0.5rem;">
            {bullish_count} Bullish | {bearish_count} Bearish | {neutral_count} Neutral
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Display bias breakdown
    st.markdown("### 📊 Bias Source Breakdown")

    for bias_data in biases:
        bias_emoji = get_bias_emoji(bias_data['bias'])
        bias_color = get_bias_color(bias_data['bias'])

        st.markdown(f"""
        <div style="background-color: #2a2a2a; padding: 1rem; border-radius: 0.5rem;
                    border-left: 4px solid {bias_color}; margin: 0.5rem 0;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="font-size: 1.2rem;">{bias_emoji}</span>
                    <span style="font-weight: bold; margin-left: 0.5rem;">{bias_data['source']}</span>
                </div>
                <div style="color: {bias_color}; font-weight: bold;">
                    {bias_data['bias']} ({bias_data['value']:.2f})
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# Main execution
if st.button("🔄 Refresh Data") or (auto_refresh and (st.session_state.last_update is None or
    (datetime.now(IST) - st.session_state.last_update).total_seconds() > refresh_interval)):

    # Load all data
    data = load_data()
    st.session_state.last_update = datetime.now(IST)

    # Display current price
    if data['current_price']:
        st.markdown(f"""
        <div style="text-align: center; font-size: 2rem; margin: 1rem 0;">
            <span style="color: #888;">Current Price:</span>
            <span style="color: #00ff00; font-weight: bold; margin-left: 1rem;">
                ₹{data['current_price']:.2f}
            </span>
        </div>
        """, unsafe_allow_html=True)

    # Display all bias sections
    display_overall_market_bias(data)

    st.markdown("---")

    display_technical_bias(data)

    st.markdown("---")

    display_pcr_bias(data)

    st.markdown("---")

    display_atm_zone_bias(data)

    # Display last update time
    st.markdown(f"""
    <div style="text-align: center; color: #888; margin-top: 2rem;">
        Last Updated: {data['timestamp'].strftime('%Y-%m-%d %H:%M:%S IST')}
    </div>
    """, unsafe_allow_html=True)

else:
    st.info("👆 Click 'Refresh Data' to load bias analysis or enable Auto Refresh in the sidebar")

# Auto-refresh logic
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <strong>NIFTY SENSEX Trader - Lite Version</strong><br>
    Fast | Lightweight | Essential Bias Indicators Only<br>
    🚀 Optimized for Speed | 📊 All Critical Biases | ⚡ Real-time Analysis
</div>
""", unsafe_allow_html=True)
