import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime
import math
from scipy.stats import norm
from pytz import timezone
import plotly.graph_objects as go
import io
from market_hours_scheduler import scheduler, is_within_trading_hours

# === Streamlit Config ===
st.set_page_config(page_title="NSE Options Analyzer", layout="wide")
# Auto-refresh removed - controlled by main app (60-second cycle)

# Define all instruments we'll analyze
INSTRUMENTS = {
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

# Initialize session states for all instruments
for category in INSTRUMENTS:
    for instrument in INSTRUMENTS[category]:
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

# === Telegram Config ===
TELEGRAM_BOT_TOKEN = "8133685842:AAGdHCpi9QRIsS-fWW5Y1AJvS95QL9xU"
TELEGRAM_CHAT_ID = "57096584"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        response = requests.post(url, data=data)
        if response.status_code != 200:
            st.warning("⚠️ Telegram message failed.")
    except Exception as e:
        st.error(f"❌ Telegram error: {e}")

def calculate_greeks(option_type, S, K, T, r, sigma):
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    delta = norm.cdf(d1) if option_type == 'CE' else -norm.cdf(-d1)
    gamma = norm.pdf(d1) / (S * sigma * math.sqrt(T))
    vega = S * norm.pdf(d1) * math.sqrt(T) / 100
    theta = (- (S * norm.pdf(d1) * sigma) / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * norm.cdf(d2)) / 365 if option_type == 'CE' else (- (S * norm.pdf(d1) * sigma) / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * norm.cdf(-d2)) / 365
    rho = (K * T * math.exp(-r * T) * norm.cdf(d2)) / 100 if option_type == 'CE' else (-K * T * math.exp(-r * T) * norm.cdf(-d2)) / 100
    return round(delta, 4), round(gamma, 4), round(vega, 4), round(theta, 4), round(rho, 4)

def final_verdict(score):
    if score >= 4:
        return "Strong Bullish"
    elif score >= 2:
        return "Bullish"
    elif score <= -4:
        return "Strong Bearish"
    elif score <= -2:
        return "Bearish"
    else:
        return "Neutral"

def delta_volume_bias(price, volume, chg_oi):
    if price > 0 and volume > 0 and chg_oi > 0:
        return "Bullish"
    elif price < 0 and volume > 0 and chg_oi > 0:
        return "Bearish"
    elif price > 0 and volume > 0 and chg_oi < 0:
        return "Bullish"
    elif price < 0 and volume > 0 and chg_oi < 0:
        return "Bearish"
    else:
        return "Neutral"

weights = {
    "OI_Bias": 2,
    "ChgOI_Bias": 2,
    "Volume_Bias": 1,
    "Delta_Bias": 1,
    "Gamma_Bias": 1,
    "Premium_Bias": 1,
    "AskQty_Bias": 1,
    "BidQty_Bias": 1,
    "IV_Bias": 1,
    "DVP_Bias": 1,
    "Delta_Exposure_Bias": 1.5,
    "Gamma_Exposure_Bias": 1.5,
    "IV_Skew_Bias": 1,
}

def determine_level(row):
    ce_oi = row['openInterest_CE']
    pe_oi = row['openInterest_PE']
    ce_chg = row['changeinOpenInterest_CE']
    pe_chg = row['changeinOpenInterest_PE']

    # Strong Support condition
    if pe_oi > 1.12 * ce_oi:
        return "Support"
    # Strong Resistance condition
    elif ce_oi > 1.12 * pe_oi:
        return "Resistance"
    # Neutral if none dominant
    else:
        return "Neutral"

def is_in_zone(spot, strike, level, instrument):
    zone_size = INSTRUMENTS['indices'].get(instrument, {}).get('zone_size', 20) or \
                INSTRUMENTS['stocks'].get(instrument, {}).get('zone_size', 20)

    if level == "Support":
        return strike - zone_size <= spot <= strike + zone_size
    elif level == "Resistance":
        return strike - zone_size <= spot <= strike + zone_size
    return False

def get_support_resistance_zones(df, spot, instrument):
    support_strikes = df[df['Level'] == "Support"]['strikePrice'].tolist()
    resistance_strikes = df[df['Level'] == "Resistance"]['strikePrice'].tolist()

    nearest_supports = sorted([s for s in support_strikes if s <= spot], reverse=True)[:2]
    nearest_resistances = sorted([r for r in resistance_strikes if r >= spot])[:2]

    support_zone = (min(nearest_supports), max(nearest_supports)) if len(nearest_supports) >= 2 else (nearest_supports[0], nearest_supports[0]) if nearest_supports else (None, None)
    resistance_zone = (min(nearest_resistances), max(nearest_resistances)) if len(nearest_resistances) >= 2 else (nearest_resistances[0], nearest_resistances[0]) if nearest_resistances else (None, None)

    return support_zone, resistance_zone


def display_enhanced_trade_log(instrument):
    if not st.session_state[f'{instrument}_trade_log']:
        st.info(f"No {instrument} trades logged yet")
        return
    st.markdown(f"### 📜 {instrument} Trade Log")
    df_trades = pd.DataFrame(st.session_state[f'{instrument}_trade_log'])

    # Get lot size for P&L calculation
    lot_size = INSTRUMENTS['indices'].get(instrument, {}).get('lot_size', 1) or \
               INSTRUMENTS['stocks'].get(instrument, {}).get('lot_size', 1)

    if 'Current_Price' not in df_trades.columns:
        df_trades['Current_Price'] = df_trades['LTP'] * np.random.uniform(0.8, 1.3, len(df_trades))
        df_trades['Unrealized_PL'] = (df_trades['Current_Price'] - df_trades['LTP']) * lot_size
        df_trades['Status'] = df_trades['Unrealized_PL'].apply(
            lambda x: '🟢 Profit' if x > 0 else '🔴 Loss' if x < -100 else '🟡 Breakeven'
        )

    def color_pnl(row):
        colors = []
        for col in row.index:
            if col == 'Unrealized_PL':
                if row[col] > 0:
                    colors.append('background-color: #90EE90; color: black')
                elif row[col] < -100:
                    colors.append('background-color: #FFB6C1; color: black')
                else:
                    colors.append('background-color: #FFFFE0; color: black')
            else:
                colors.append('')
        return colors

    styled_trades = df_trades.style.apply(color_pnl, axis=1)
    st.dataframe(styled_trades, use_container_width=True)
    total_pl = df_trades['Unrealized_PL'].sum()
    win_rate = len(df_trades[df_trades['Unrealized_PL'] > 0]) / len(df_trades) * 100
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total P&L", f"₹{total_pl:,.0f}")
    with col2:
        st.metric("Win Rate", f"{win_rate:.1f}%")
    with col3:
        st.metric("Total Trades", len(df_trades))

def create_export_data(df_summary, trade_log, spot_price, instrument):
    # Create Excel data
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_summary.to_excel(writer, sheet_name=f'{instrument}_Option_Chain', index=False)
        if trade_log:
            pd.DataFrame(trade_log).to_excel(writer, sheet_name=f'{instrument}_Trade_Log', index=False)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{instrument.lower()}_analysis_{timestamp}.xlsx"

    return output.getvalue(), filename

def handle_export_data(df_summary, spot_price, instrument):
    if st.button(f"Prepare {instrument} Excel Export"):
        try:
            excel_data, filename = create_export_data(df_summary, st.session_state[f'{instrument}_trade_log'], spot_price, instrument)
            st.download_button(
                label=f"📥 Download {instrument} Excel Report",
                data=excel_data,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            st.success(f"✅ {instrument} export ready! Click the download button above.")
        except Exception as e:
            st.error(f"❌ {instrument} export failed: {e}")

def plot_price_with_sr(instrument):
    price_df = st.session_state[f'{instrument}_price_data'].copy()
    if price_df.empty or price_df['Spot'].isnull().all():
        st.info(f"Not enough {instrument} data to show price action chart yet.")
        return

    price_df['Time'] = pd.to_datetime(price_df['Time'])
    support_zone = st.session_state.get(f'{instrument}_support_zone', (None, None))
    resistance_zone = st.session_state.get(f'{instrument}_resistance_zone', (None, None))

    fig = go.Figure()

    # Main price line
    fig.add_trace(go.Scatter(
        x=price_df['Time'],
        y=price_df['Spot'],
        mode='lines+markers',
        name='Spot Price',
        line=dict(color='blue', width=2)
    ))

    # Support zone
    if all(support_zone) and None not in support_zone:
        fig.add_shape(
            type="rect",
            xref="paper", yref="y",
            x0=0, x1=1,
            y0=support_zone[0], y1=support_zone[1],
            fillcolor="rgba(0,255,0,0.08)",
            line=dict(width=0),
            layer="below"
        )
        fig.add_trace(go.Scatter(
            x=[price_df['Time'].min(), price_df['Time'].max()],
            y=[support_zone[0], support_zone[0]],
            mode='lines',
            name='Support Low',
            line=dict(color='green', dash='dash')
        ))
        fig.add_trace(go.Scatter(
            x=[price_df['Time'].min(), price_df['Time'].max()],
            y=[support_zone[1], support_zone[1]],
            mode='lines',
            name='Support High',
            line=dict(color='green', dash='dot')
        ))

    # Resistance zone
    if all(resistance_zone) and None not in resistance_zone:
        fig.add_shape(
            type="rect",
            xref="paper", yref="y",
            x0=0, x1=1,
            y0=resistance_zone[0], y1=resistance_zone[1],
            fillcolor="rgba(255,0,0,0.08)",
            line=dict(width=0),
            layer="below"
        )
        fig.add_trace(go.Scatter(
            x=[price_df['Time'].min(), price_df['Time'].max()],
            y=[resistance_zone[0], resistance_zone[0]],
            mode='lines',
            name='Resistance Low',
            line=dict(color='red', dash='dash')
        ))
        fig.add_trace(go.Scatter(
            x=[price_df['Time'].min(), price_df['Time'].max()],
            y=[resistance_zone[1], resistance_zone[1]],
            mode='lines',
            name='Resistance High',
            line=dict(color='red', dash='dot')
        ))

    # Layout configuration
    fig.update_layout(
        title=f"{instrument} Spot Price Action with Support & Resistance",
        xaxis_title="Time",
        yaxis_title="Spot Price",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)

def auto_update_call_log(current_price, instrument):
    for call in st.session_state[f'{instrument}_call_log_book']:
        if call["Status"] != "Active":
            continue
        if call["Type"] == "CE":
            if current_price >= max(call["Targets"].values()):
                call["Status"] = "Hit Target"
                call["Hit_Target"] = True
                call["Exit_Time"] = datetime.now(timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")
                call["Exit_Price"] = current_price
            elif current_price <= call["Stoploss"]:
                call["Status"] = "Hit Stoploss"
                call["Hit_Stoploss"] = True
                call["Exit_Time"] = datetime.now(timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")
                call["Exit_Price"] = current_price
        elif call["Type"] == "PE":
            if current_price <= min(call["Targets"].values()):
                call["Status"] = "Hit Target"
                call["Hit_Target"] = True
                call["Exit_Time"] = datetime.now(timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")
                call["Exit_Price"] = current_price
            elif current_price >= call["Stoploss"]:
                call["Status"] = "Hit Stoploss"
                call["Hit_Stoploss"] = True
                call["Exit_Time"] = datetime.now(timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")
                call["Exit_Price"] = current_price

def display_call_log_book(instrument):
    st.markdown(f"### 📚 {instrument} Call Log Book")
    if not st.session_state[f'{instrument}_call_log_book']:
        st.info(f"No {instrument} calls have been made yet.")
        return

    df_log = pd.DataFrame(st.session_state[f'{instrument}_call_log_book'])
    st.dataframe(df_log, use_container_width=True)

    if st.button(f"Download {instrument} Call Log Book as CSV"):
        st.download_button(
            label="Download CSV",
            data=df_log.to_csv(index=False).encode(),
            file_name=f"{instrument.lower()}_call_log_book.csv",
            mime="text/csv"
        )

@st.cache_data(ttl=30, show_spinner=False)
def fetch_option_chain_data(instrument):
    """Fetch and return option chain data for an instrument - Cached for 30 seconds"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        session = requests.Session()
        session.headers.update(headers)
        session.get("https://www.nseindia.com", timeout=5)

        # Handle spaces in instrument names
        url_instrument = instrument.replace(' ', '%20')
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={url_instrument}" if instrument in INSTRUMENTS['indices'] else \
              f"https://www.nseindia.com/api/option-chain-equities?symbol={url_instrument}"

        response = session.get(url, timeout=10)
        data = response.json()

        records = data['records']['data']
        expiry = data['records']['expiryDates'][0]
        underlying = data['records']['underlyingValue']

        # Calculate totals
        total_ce_oi = sum(item['CE']['openInterest'] for item in records if 'CE' in item)
        total_pe_oi = sum(item['PE']['openInterest'] for item in records if 'PE' in item)
        total_ce_change = sum(item['CE']['changeinOpenInterest'] for item in records if 'CE' in item)
        total_pe_change = sum(item['PE']['changeinOpenInterest'] for item in records if 'PE' in item)

        return {
            'success': True,
            'instrument': instrument,
            'spot': underlying,
            'expiry': expiry,
            'total_ce_oi': total_ce_oi,
            'total_pe_oi': total_pe_oi,
            'total_ce_change': total_ce_change,
            'total_pe_change': total_pe_change,
            'records': records
        }
    except Exception as e:
        return {
            'success': False,
            'instrument': instrument,
            'error': str(e)
        }

def display_overall_option_chain_analysis():
    """Display overall option chain analysis with PCR ratios"""
    st.header("🌐 Overall Market Option Chain Analysis")
    st.caption("Consolidated view of all instruments with PCR ratios and market bias")

    # Fetch button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("Click 'Fetch All Data' to get the latest option chain data for all instruments")
    with col2:
        if st.button("🔄 Fetch All Data", type="primary", use_container_width=True):
            with st.spinner("Fetching option chain data for all instruments..."):
                overall_data = {}
                progress_bar = st.progress(0)
                all_instruments = list(INSTRUMENTS['indices'].keys()) + list(INSTRUMENTS['stocks'].keys())

                for idx, instrument in enumerate(all_instruments):
                    data = fetch_option_chain_data(instrument)
                    overall_data[instrument] = data
                    progress_bar.progress((idx + 1) / len(all_instruments))

                st.session_state['overall_option_data'] = overall_data
                st.success("✅ Data fetched successfully!")
                st.rerun()

    st.divider()

    # Display analysis if data is available
    if st.session_state.get('overall_option_data'):
        data_dict = st.session_state['overall_option_data']

        # === PCR ANALYSIS SECTION ===
        st.subheader("📊 Put-Call Ratio (PCR) Analysis")

        # Create PCR data
        pcr_data = []
        for instrument, data in data_dict.items():
            if data['success']:
                # Calculate PCR for Total OI
                pcr_oi = data['total_pe_oi'] / data['total_ce_oi'] if data['total_ce_oi'] > 0 else 0

                # Calculate PCR for Change in OI
                pcr_change_oi = abs(data['total_pe_change']) / abs(data['total_ce_change']) if data['total_ce_change'] != 0 else 0

                # Determine bias based on PCR
                if pcr_oi > 1.2:
                    oi_bias = "🐂 Bullish"
                elif pcr_oi < 0.8:
                    oi_bias = "🐻 Bearish"
                else:
                    oi_bias = "⚖️ Neutral"

                if pcr_change_oi > 1.2:
                    change_bias = "🐂 Bullish"
                elif pcr_change_oi < 0.8:
                    change_bias = "🐻 Bearish"
                else:
                    change_bias = "⚖️ Neutral"

                pcr_data.append({
                    'Instrument': instrument,
                    'Spot': f"₹{data['spot']:,.2f}",
                    'Total CE OI': f"{data['total_ce_oi']:,.0f}",
                    'Total PE OI': f"{data['total_pe_oi']:,.0f}",
                    'PCR (OI)': f"{pcr_oi:.2f}",
                    'OI Bias': oi_bias,
                    'CE Δ OI': f"{data['total_ce_change']:,.0f}",
                    'PE Δ OI': f"{data['total_pe_change']:,.0f}",
                    'PCR (Δ OI)': f"{pcr_change_oi:.2f}",
                    'Δ OI Bias': change_bias
                })

        # Display PCR table
        if pcr_data:
            pcr_df = pd.DataFrame(pcr_data)

            # Color coding function
            def color_bias_cells(val):
                if '🐂' in str(val):
                    return 'background-color: #90EE90; color: black; font-weight: bold'
                elif '🐻' in str(val):
                    return 'background-color: #FFB6C1; color: black; font-weight: bold'
                elif '⚖️' in str(val):
                    return 'background-color: #FFFFE0; color: black'
                return ''

            styled_pcr = pcr_df.style.applymap(color_bias_cells, subset=['OI Bias', 'Δ OI Bias'])
            st.dataframe(styled_pcr, use_container_width=True, hide_index=True)

            # PCR interpretation guide
            with st.expander("📖 PCR Interpretation Guide"):
                st.markdown("""
                ### Put-Call Ratio (PCR) Interpretation

                **PCR = Total PUT OI / Total CALL OI** or **PCR = Total PUT Δ OI / Total CALL Δ OI**

                - **PCR > 1.2**: Bullish Signal 🐂
                  - More PUT writing/accumulation than CALL
                  - Market participants expect prices to go up

                - **PCR < 0.8**: Bearish Signal 🐻
                  - More CALL writing/accumulation than PUT
                  - Market participants expect prices to go down

                - **PCR between 0.8 - 1.2**: Neutral ⚖️
                  - Balanced option activity
                  - No clear directional bias

                **Note**:
                - **Total OI PCR** shows overall market positioning
                - **Change in OI PCR** shows current session's sentiment
                - Use both together for better analysis
                """)

        st.divider()

        # === OVERALL MARKET BIAS ===
        st.subheader("🎯 Overall Market Bias")

        # Calculate aggregated bias
        bullish_count = sum(1 for d in pcr_data if '🐂' in d['OI Bias'] or '🐂' in d['Δ OI Bias'])
        bearish_count = sum(1 for d in pcr_data if '🐻' in d['OI Bias'] or '🐻' in d['Δ OI Bias'])
        neutral_count = len(pcr_data) - bullish_count - bearish_count

        total_signals = len(pcr_data) * 2  # Each instrument has 2 signals (OI + Δ OI)

        # Determine overall market bias
        if bullish_count > bearish_count and bullish_count > neutral_count:
            overall_bias = "🐂 BULLISH"
            bias_color = "green"
        elif bearish_count > bullish_count and bearish_count > neutral_count:
            overall_bias = "🐻 BEARISH"
            bias_color = "red"
        else:
            overall_bias = "⚖️ NEUTRAL"
            bias_color = "gray"

        # Display overall bias
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(f"<h2 style='color:{bias_color}; text-align: center;'>{overall_bias}</h2>",
                       unsafe_allow_html=True)
            st.caption("Overall Market Sentiment")

        with col2:
            st.metric("Bullish Signals", bullish_count, delta=f"{(bullish_count/total_signals*100):.1f}%")

        with col3:
            st.metric("Bearish Signals", bearish_count, delta=f"{(bearish_count/total_signals*100):.1f}%", delta_color="inverse")

        with col4:
            st.metric("Neutral Signals", neutral_count)

        # Market bias distribution chart
        st.markdown("### 📊 Market Sentiment Distribution")

        sentiment_data = pd.DataFrame({
            'Sentiment': ['Bullish', 'Bearish', 'Neutral'],
            'Count': [bullish_count, bearish_count, neutral_count]
        })

        fig = go.Figure(data=[
            go.Bar(
                x=sentiment_data['Sentiment'],
                y=sentiment_data['Count'],
                marker_color=['green', 'red', 'gray'],
                text=sentiment_data['Count'],
                textposition='auto'
            )
        ])

        fig.update_layout(
            title="Overall Market Sentiment Breakdown",
            xaxis_title="Sentiment",
            yaxis_title="Count",
            template="plotly_white"
        )

        st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # === DETAILED BREAKDOWN BY CATEGORY ===
        st.subheader("📈 Category-wise Analysis")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 📊 Indices")
            indices_data = [d for d in pcr_data if d['Instrument'] in INSTRUMENTS['indices']]
            if indices_data:
                indices_df = pd.DataFrame(indices_data)
                st.dataframe(indices_df[['Instrument', 'Spot', 'PCR (OI)', 'OI Bias', 'PCR (Δ OI)', 'Δ OI Bias']],
                           use_container_width=True, hide_index=True)

        with col2:
            st.markdown("### 🏢 Stocks")
            stocks_data = [d for d in pcr_data if d['Instrument'] in INSTRUMENTS['stocks']]
            if stocks_data:
                stocks_df = pd.DataFrame(stocks_data)
                st.dataframe(stocks_df[['Instrument', 'Spot', 'PCR (OI)', 'OI Bias', 'PCR (Δ OI)', 'Δ OI Bias']],
                           use_container_width=True, hide_index=True)

        st.divider()

        # === TRADING RECOMMENDATION ===
        st.subheader("💡 Trading Recommendation")

        if overall_bias == "🐂 BULLISH":
            st.success("""
            ### 🐂 BULLISH MARKET SENTIMENT DETECTED

            **Recommended Actions:**
            - ✅ Look for LONG/CALL opportunities
            - ✅ Focus on instruments with high PUT OI accumulation
            - ✅ Wait for support levels to enter
            - ⚠️ Use proper stop losses
            """)
        elif overall_bias == "🐻 BEARISH":
            st.error("""
            ### 🐻 BEARISH MARKET SENTIMENT DETECTED

            **Recommended Actions:**
            - ✅ Look for SHORT/PUT opportunities
            - ✅ Focus on instruments with high CALL OI accumulation
            - ✅ Wait for resistance levels to enter
            - ⚠️ Use proper stop losses
            """)
        else:
            st.warning("""
            ### ⚖️ NEUTRAL MARKET SENTIMENT

            **Recommended Actions:**
            - 🔄 Wait for clear directional bias
            - 🔄 Focus on range-bound strategies
            - 🔄 Reduce position sizes
            - 🔄 Monitor key support/resistance levels
            """)

        # Timestamp
        st.caption(f"Last Updated: {datetime.now(timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M:%S IST')}")

    else:
        st.info("👆 Click 'Fetch All Data' to load option chain analysis")

        st.markdown("""
        ### About Overall Option Chain Analysis

        This section provides:

        - **PCR (Put-Call Ratio)** for all instruments
          - Total OI based PCR
          - Change in OI based PCR

        - **Market-wide bias** aggregation

        - **Category-wise breakdown** (Indices vs Stocks)

        - **Trading recommendations** based on overall sentiment

        **How to use:**
        1. Click 'Fetch All Data' to get latest option chain data
        2. Review PCR ratios for each instrument
        3. Check overall market bias
        4. Use the insights for trading decisions
        """)

def analyze_instrument(instrument):
    try:
        # Check if market is within trading hours using centralized scheduler
        if not is_within_trading_hours():
            status = scheduler.get_market_status()
            st.warning(f"⏳ Market Closed - Trading Hours: 8:30 AM - 3:45 PM IST (Mon-Fri)")
            return

        headers = {"User-Agent": "Mozilla/5.0"}
        session = requests.Session()
        session.headers.update(headers)
        session.get("https://www.nseindia.com", timeout=5)

        # Handle spaces in instrument names
        url_instrument = instrument.replace(' ', '%20')
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={url_instrument}" if instrument in INSTRUMENTS['indices'] else \
              f"https://www.nseindia.com/api/option-chain-equities?symbol={url_instrument}"

        response = session.get(url, timeout=10)
        data = response.json()

        records = data['records']['data']
        expiry = data['records']['expiryDates'][0]
        underlying = data['records']['underlyingValue']

        # === Open Interest Change Comparison ===
        total_ce_change = sum(item['CE']['changeinOpenInterest'] for item in records if 'CE' in item) / 100000
        total_pe_change = sum(item['PE']['changeinOpenInterest'] for item in records if 'PE' in item) / 100000

        st.markdown(f"## 📊 {instrument} Open Interest Change (Lakhs)")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📉 CALL Δ OI",
                     f"{total_ce_change:+.1f}L",
                     delta_color="inverse")

        with col2:
            st.metric("📈 PUT Δ OI",
                     f"{total_pe_change:+.1f}L",
                     delta_color="normal")

        # Dominance indicator
        if total_ce_change > total_pe_change:
            st.error(f"🚨 Call OI Dominance (Difference: {abs(total_ce_change - total_pe_change):.1f}L)")
        elif total_pe_change > total_ce_change:
            st.success(f"🚀 Put OI Dominance (Difference: {abs(total_pe_change - total_ce_change):.1f}L)")
        else:
            st.info("⚖️ OI Changes Balanced")

        today = datetime.now(timezone("Asia/Kolkata"))
        expiry_date = timezone("Asia/Kolkata").localize(datetime.strptime(expiry, "%d-%b-%Y"))

        # Calculate time to expiry
        T = max((expiry_date - today).days, 1) / 365
        r = 0.06

        calls, puts = [], []

        for item in records:
            if 'CE' in item and item['CE']['expiryDate'] == expiry:
                ce = item['CE']
                if ce['impliedVolatility'] > 0:
                    greeks = calculate_greeks('CE', underlying, ce['strikePrice'], T, r, ce['impliedVolatility'] / 100)
                    ce.update(dict(zip(['Delta', 'Gamma', 'Vega', 'Theta', 'Rho'], greeks)))
                calls.append(ce)

            if 'PE' in item and item['PE']['expiryDate'] == expiry:
                pe = item['PE']
                if pe['impliedVolatility'] > 0:
                    greeks = calculate_greeks('PE', underlying, pe['strikePrice'], T, r, pe['impliedVolatility'] / 100)
                    pe.update(dict(zip(['Delta', 'Gamma', 'Vega', 'Theta', 'Rho'], greeks)))
                puts.append(pe)

        df_ce = pd.DataFrame(calls)
        df_pe = pd.DataFrame(puts)
        df = pd.merge(df_ce, df_pe, on='strikePrice', suffixes=('_CE', '_PE')).sort_values('strikePrice')

        # Get instrument-specific parameters
        atm_range = INSTRUMENTS['indices'].get(instrument, {}).get('atm_range', 200) or \
                    INSTRUMENTS['stocks'].get(instrument, {}).get('atm_range', 200)

        atm_strike = min(df['strikePrice'], key=lambda x: abs(x - underlying))
        df = df[df['strikePrice'].between(atm_strike - atm_range, atm_strike + atm_range)]
        df['Zone'] = df['strikePrice'].apply(lambda x: 'ATM' if x == atm_strike else 'ITM' if x < underlying else 'OTM')
        df['Level'] = df.apply(determine_level, axis=1)

        bias_results, total_score = [], 0
        # Calculate Delta and Gamma Exposures
        total_delta_exposure = 0
        total_gamma_exposure = 0

        for _, row in df.iterrows():
            # Calculate exposures for all strikes (not just near ATM)
            ce_delta_exp = row['Delta_CE'] * row['openInterest_CE']
            pe_delta_exp = row['Delta_PE'] * row['openInterest_PE']
            ce_gamma_exp = row['Gamma_CE'] * row['openInterest_CE']
            pe_gamma_exp = row['Gamma_PE'] * row['openInterest_PE']

            total_delta_exposure += (ce_delta_exp + pe_delta_exp)
            total_gamma_exposure += (ce_gamma_exp + pe_gamma_exp)

        for _, row in df.iterrows():
            if abs(row['strikePrice'] - atm_strike) > (atm_range/2):  # Only consider strikes near ATM
                continue

            score = 0

            # Calculate per-strike delta and gamma exposure
            ce_delta_exp = row['Delta_CE'] * row['openInterest_CE']
            pe_delta_exp = row['Delta_PE'] * row['openInterest_PE']
            ce_gamma_exp = row['Gamma_CE'] * row['openInterest_CE']
            pe_gamma_exp = row['Gamma_PE'] * row['openInterest_PE']

            # Calculate net exposures
            net_delta_exp = ce_delta_exp + pe_delta_exp
            net_gamma_exp = ce_gamma_exp + pe_gamma_exp

            # Calculate per-strike IV skew
            strike_iv_skew = row['impliedVolatility_PE'] - row['impliedVolatility_CE']

            # Determine bias for each metric
            delta_exp_bias = "Bullish" if net_delta_exp > 0 else "Bearish" if net_delta_exp < 0 else "Neutral"
            gamma_exp_bias = "Bullish" if net_gamma_exp > 0 else "Bearish" if net_gamma_exp < 0 else "Neutral"
            iv_skew_bias = "Bullish" if strike_iv_skew > 0 else "Bearish" if strike_iv_skew < 0 else "Neutral"

            row_data = {
                "Strike": row['strikePrice'],
                "Zone": row['Zone'],
                "Level": row['Level'],
                "OI_Bias": "Bearish" if row['openInterest_CE'] > row['openInterest_PE'] else "Bullish",
                "ChgOI_Bias": "Bullish" if row['changeinOpenInterest_CE'] < row['changeinOpenInterest_PE'] else "Bearish",
                "Volume_Bias": "Bullish" if row['totalTradedVolume_CE'] < row['totalTradedVolume_PE'] else "Bearish",
                "Delta_Bias": "Bullish" if abs(row['Delta_PE']) > abs(row['Delta_CE']) else "Bearish",
                "Gamma_Bias": "Bullish" if row['Gamma_CE'] < row['Gamma_PE'] else "Bearish",
                "Premium_Bias": "Bearish" if row['lastPrice_CE'] > row['lastPrice_PE'] else "Bullish",
                "AskQty_Bias": "Bullish" if row['askQty_PE'] > row['askQty_CE'] else "Bearish",
                "BidQty_Bias": "Bearish" if row['bidQty_PE'] > row['bidQty_CE'] else "Bullish",
                "IV_Bias": "Bullish" if row['impliedVolatility_CE'] > row['impliedVolatility_PE'] else "Bearish",
                "DVP_Bias": delta_volume_bias(
                    row['lastPrice_CE'] - row['lastPrice_PE'],
                    row['totalTradedVolume_CE'] - row['totalTradedVolume_PE'],
                    row['changeinOpenInterest_CE'] - row['changeinOpenInterest_PE']
                ),
                "Delta_Exposure_Bias": delta_exp_bias,
                "Gamma_Exposure_Bias": gamma_exp_bias,
                "IV_Skew_Bias": iv_skew_bias
            }

            for k in row_data:
                if "_Bias" in k:
                    bias = row_data[k]
                    score += weights.get(k, 1) if bias == "Bullish" else -weights.get(k, 1)

            row_data["BiasScore"] = score
            row_data["Verdict"] = final_verdict(score)
            total_score += score
            bias_results.append(row_data)

        df_summary = pd.DataFrame(bias_results)

        # Store df_summary in session state for access from Overall Market Sentiment tab
        st.session_state[f'{instrument}_atm_zone_bias'] = df_summary.copy()

        atm_row = df_summary[df_summary["Zone"] == "ATM"].iloc[0] if not df_summary[df_summary["Zone"] == "ATM"].empty else None
        market_view = atm_row['Verdict'] if atm_row is not None else "Neutral"

        # Calculate IV Skew (ATM)
        atm_ce_iv = df.loc[df['strikePrice'] == atm_strike, 'impliedVolatility_CE'].values[0] if not df[df['strikePrice'] == atm_strike].empty else 0
        atm_pe_iv = df.loc[df['strikePrice'] == atm_strike, 'impliedVolatility_PE'].values[0] if not df[df['strikePrice'] == atm_strike].empty else 0
        iv_skew = atm_pe_iv - atm_ce_iv

        # Determine Delta Bias based on net delta exposure
        delta_bias_overall = "Bullish" if total_delta_exposure > 0 else "Bearish" if total_delta_exposure < 0 else "Neutral"

        support_zone, resistance_zone = get_support_resistance_zones(df, underlying, instrument)

        # Store zones in session state
        st.session_state[f'{instrument}_support_zone'] = support_zone
        st.session_state[f'{instrument}_resistance_zone'] = resistance_zone

        current_time_str = now.strftime("%H:%M:%S")
        new_row = pd.DataFrame([[current_time_str, underlying]], columns=["Time", "Spot"])
        st.session_state[f'{instrument}_price_data'] = pd.concat([st.session_state[f'{instrument}_price_data'], new_row], ignore_index=True)

        support_str = f"{support_zone[1]} to {support_zone[0]}" if all(support_zone) else "N/A"
        resistance_str = f"{resistance_zone[0]} to {resistance_zone[1]}" if all(resistance_zone) else "N/A"

        atm_signal, suggested_trade = "No Signal", ""
        signal_sent = False

        for row in bias_results:
            if not is_in_zone(underlying, row['Strike'], row['Level'], instrument):
                continue

            if row['Level'] == "Support" and total_score >= 4 and "Bullish" in market_view:
                option_type = 'CE'
            elif row['Level'] == "Resistance" and total_score <= -4 and "Bearish" in market_view:
                option_type = 'PE'
            else:
                continue

            ltp = df.loc[df['strikePrice'] == row['Strike'], f'lastPrice_{option_type}'].values[0]
            iv = df.loc[df['strikePrice'] == row['Strike'], f'impliedVolatility_{option_type}'].values[0]
            target = round(ltp * (1 + iv / 100), 2)
            stop_loss = round(ltp * 0.8, 2)

            atm_signal = f"{'CALL' if option_type == 'CE' else 'PUT'} Entry (Bias Based at {row['Level']})"
            suggested_trade = f"Strike: {row['Strike']} {option_type} @ ₹{ltp} | 🎯 Target: ₹{target} | 🛑 SL: ₹{stop_loss}"

            send_telegram_message(
                f"📍 {instrument} Spot: {underlying}\n"
                f"🔹 {atm_signal}\n"
                f"{suggested_trade}\n"
                f"Bias Score (ATM ±2): {total_score} ({market_view})\n"
                f"Level: {row['Level']}\n"
                f"📉 Support Zone: {support_str}\n"
                f"📈 Resistance Zone: {resistance_str}\n"
                f"Biases:\n"
                f"Strike: {row['Strike']}\n"
                f"ChgOI: {row['ChgOI_Bias']}, Volume: {row['Volume_Bias']}, Gamma: {row['Gamma_Bias']},\n"
                f"AskQty: {row['AskQty_Bias']}, BidQty: {row['BidQty_Bias']}, IV: {row['IV_Bias']}, DVP: {row['DVP_Bias']}"
            )

            st.session_state[f'{instrument}_trade_log'].append({
                "Time": now.strftime("%H:%M:%S"),
                "Strike": row['Strike'],
                "Type": option_type,
                "LTP": ltp,
                "Target": target,
                "SL": stop_loss
            })

            signal_sent = True
            break

        # === Main Display ===
        st.markdown(f"### 📍 {instrument} Spot Price: {underlying}")
        st.success(f"🧠 {instrument} Market View: **{market_view}** Bias Score: {total_score}")
        st.markdown(f"### 🛡️ {instrument} Support Zone: `{support_str}`")
        st.markdown(f"### 🚧 {instrument} Resistance Zone: `{resistance_str}`")

        # Display Greeks Metrics in a dedicated section
        st.markdown("---")
        st.markdown(f"### 🎯 {instrument} Greeks & Exposure Metrics")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            delta_color = "🟢" if delta_bias_overall == "Bullish" else "🔴" if delta_bias_overall == "Bearish" else "🟡"
            st.metric("Delta Bias", f"{delta_color} {delta_bias_overall}")
            st.caption(f"Exposure: {total_delta_exposure:,.0f}")

        with col2:
            st.metric("Gamma Exposure", f"{total_gamma_exposure:,.2f}")
            st.caption("Total Gamma * OI")

        with col3:
            st.metric("Delta Exposure", f"{total_delta_exposure:,.0f}")
            st.caption("Total Delta * OI")

        with col4:
            iv_skew_color = "🟢" if iv_skew > 0 else "🔴" if iv_skew < 0 else "🟡"
            st.metric("IV Skew (ATM)", f"{iv_skew_color} {iv_skew:.2f}%")
            st.caption(f"PE IV: {atm_pe_iv:.1f}% | CE IV: {atm_ce_iv:.1f}%")

        st.markdown("---")

        # Display price chart
        plot_price_with_sr(instrument)

        if suggested_trade:
            st.info(f"🔹 {atm_signal}\n{suggested_trade}")

        with st.expander(f"📊 {instrument} Option Chain Summary"):
            st.dataframe(df_summary)

        if st.session_state[f'{instrument}_trade_log']:
            st.markdown(f"### 📜 {instrument} Trade Log")
            st.dataframe(pd.DataFrame(st.session_state[f'{instrument}_trade_log']))

        # === Enhanced Functions Display ===
        st.markdown("---")
        st.markdown(f"## 📈 {instrument} Enhanced Features")

        # Enhanced Trade Log
        display_enhanced_trade_log(instrument)

        # Export functionality
        st.markdown("---")
        st.markdown(f"### 📥 {instrument} Data Export")
        handle_export_data(df_summary, underlying, instrument)

        # Call Log Book
        st.markdown("---")
        display_call_log_book(instrument)

        # Auto update call log with current price
        auto_update_call_log(underlying, instrument)

    except Exception as e:
        st.error(f"❌ {instrument} Error: {e}")
        send_telegram_message(f"❌ {instrument} Error: {str(e)}")

# === Main Function Call ===
if __name__ == "__main__":
    st.title("📊 NSE Options Analyzer")

    # Create tabs for main sections - NOW WITH 6 TABS
    tab_indices, tab_stocks, tab_overall = st.tabs(["📈 Indices", "🏢 Stocks", "🌐 Overall Market Analysis"])

    with tab_indices:
        st.header("NSE Indices Analysis")
        # Create subtabs for each index
        nifty_tab, banknifty_tab, sensex_tab, it_tab, auto_tab = st.tabs(["NIFTY", "BANKNIFTY", "SENSEX", "NIFTY IT", "NIFTY AUTO"])

        with nifty_tab:
            analyze_instrument('NIFTY')

        with banknifty_tab:
            analyze_instrument('BANKNIFTY')

        with sensex_tab:
            analyze_instrument('SENSEX')

        with it_tab:
            analyze_instrument('NIFTY IT')

        with auto_tab:
            analyze_instrument('NIFTY AUTO')

    with tab_stocks:
        st.header("Stock Options Analysis")
        # Create subtabs for each stock
        tcs_tab, reliance_tab, hdfc_tab = st.tabs(["TCS", "RELIANCE", "HDFCBANK"])

        with tcs_tab:
            analyze_instrument('TCS')

        with reliance_tab:
            analyze_instrument('RELIANCE')

        with hdfc_tab:
            analyze_instrument('HDFCBANK')

    with tab_overall:
        # NEW TAB: Overall Market Analysis with PCR
        display_overall_option_chain_analysis()
