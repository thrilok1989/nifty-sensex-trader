"""
Overall Market Sentiment Analysis

Aggregates bias data from all sources to provide a comprehensive market sentiment view

Data Sources:
1. Stock Performance (Market Breadth)
2. Technical Indicators (Bias Analysis Pro - 15+ indicators)
3. Option Chain ATM Zone Analysis (Multiple bias metrics)
4. PCR Analysis (Put-Call Ratio for indices)
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import time


def calculate_stock_performance_sentiment(stock_data):
    """
    Calculate sentiment from individual stock performance
    Returns: dict with sentiment, score, and details
    """
    if not stock_data:
        return None

    bullish_stocks = 0
    bearish_stocks = 0
    neutral_stocks = 0

    total_weighted_change = 0
    total_weight = 0

    for stock in stock_data:
        change_pct = stock.get('change_pct', 0)
        weight = stock.get('weight', 1)

        total_weighted_change += change_pct * weight
        total_weight += weight

        if change_pct > 0.5:
            bullish_stocks += 1
        elif change_pct < -0.5:
            bearish_stocks += 1
        else:
            neutral_stocks += 1

    # Calculate weighted average change
    avg_change = total_weighted_change / total_weight if total_weight > 0 else 0

    # Calculate market breadth
    total_stocks = len(stock_data)
    breadth_pct = (bullish_stocks / total_stocks * 100) if total_stocks > 0 else 50

    # Determine bias
    if avg_change > 1:
        bias = "BULLISH"
    elif avg_change < -1:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    # Calculate score based on weighted change and breadth
    score = avg_change * 5 + (breadth_pct - 50)

    # Calculate confidence
    confidence = min(100, abs(score))

    return {
        'bias': bias,
        'score': score,
        'breadth_pct': breadth_pct,
        'avg_change': avg_change,
        'bullish_stocks': bullish_stocks,
        'bearish_stocks': bearish_stocks,
        'neutral_stocks': neutral_stocks,
        'confidence': confidence,
        'stock_details': stock_data
    }


def calculate_technical_indicators_sentiment(bias_results):
    """
    Calculate sentiment from technical indicators (Bias Analysis Pro)
    Returns: dict with sentiment, score, and details
    """
    if not bias_results:
        return None

    bullish_indicators = 0
    bearish_indicators = 0
    neutral_indicators = 0

    total_weighted_score = 0
    total_weight = 0

    for indicator in bias_results:
        bias = indicator.get('bias', 'NEUTRAL')
        score = indicator.get('score', 0)
        weight = indicator.get('weight', 1)

        total_weighted_score += score * weight
        total_weight += weight

        if 'BULLISH' in bias.upper():
            bullish_indicators += 1
        elif 'BEARISH' in bias.upper():
            bearish_indicators += 1
        else:
            neutral_indicators += 1

    # Calculate overall score
    overall_score = total_weighted_score / total_weight if total_weight > 0 else 0

    # Determine bias
    if overall_score > 20:
        bias = "BULLISH"
    elif overall_score < -20:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    # Calculate confidence based on score magnitude and indicator agreement
    score_magnitude = min(100, abs(overall_score))

    total_indicators = len(bias_results)
    if bias == "BULLISH":
        agreement = bullish_indicators / total_indicators if total_indicators > 0 else 0
    elif bias == "BEARISH":
        agreement = bearish_indicators / total_indicators if total_indicators > 0 else 0
    else:
        agreement = neutral_indicators / total_indicators if total_indicators > 0 else 0

    confidence = score_magnitude * agreement

    return {
        'bias': bias,
        'score': overall_score,
        'bullish_count': bullish_indicators,
        'bearish_count': bearish_indicators,
        'neutral_count': neutral_indicators,
        'total_count': total_indicators,
        'confidence': confidence,
        'indicator_details': bias_results
    }


def calculate_option_chain_pcr_sentiment(NSE_INSTRUMENTS):
    """
    Calculate sentiment from PCR (Put-Call Ratio) analysis
    Returns: dict with sentiment, score, and details
    """
    if 'overall_option_data' not in st.session_state or not st.session_state.overall_option_data:
        return None

    option_data = st.session_state.overall_option_data

    # Focus on main indices
    main_indices = ['NIFTY', 'SENSEX']

    bullish_instruments = 0
    bearish_instruments = 0
    neutral_instruments = 0

    total_score = 0
    instruments_analyzed = 0

    pcr_details = []

    for instrument in main_indices:
        if instrument not in option_data:
            continue

        data = option_data[instrument]
        if not data.get('success'):
            continue

        # Calculate PCR for Total OI
        total_ce_oi = data.get('total_ce_oi', 0)
        total_pe_oi = data.get('total_pe_oi', 0)
        pcr_oi = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 1

        # Calculate PCR for Change in OI
        total_ce_change = data.get('total_ce_change', 0)
        total_pe_change = data.get('total_pe_change', 0)
        pcr_change_oi = abs(total_pe_change) / abs(total_ce_change) if abs(total_ce_change) > 0 else 1

        # Determine OI bias
        if pcr_oi > 1.2:
            oi_bias = "BULLISH"
            oi_score = min(50, (pcr_oi - 1) * 50)
        elif pcr_oi < 0.8:
            oi_bias = "BEARISH"
            oi_score = -min(50, (1 - pcr_oi) * 50)
        else:
            oi_bias = "NEUTRAL"
            oi_score = 0

        # Determine Change OI bias
        if pcr_change_oi > 1.2:
            change_bias = "BULLISH"
            change_score = min(50, (pcr_change_oi - 1) * 50)
        elif pcr_change_oi < 0.8:
            change_bias = "BEARISH"
            change_score = -min(50, (1 - pcr_change_oi) * 50)
        else:
            change_bias = "NEUTRAL"
            change_score = 0

        # Combined score for this instrument
        instrument_score = (oi_score + change_score) / 2

        # Determine overall instrument bias
        if instrument_score > 10:
            instrument_bias = "BULLISH"
            bullish_instruments += 1
        elif instrument_score < -10:
            instrument_bias = "BEARISH"
            bearish_instruments += 1
        else:
            instrument_bias = "NEUTRAL"
            neutral_instruments += 1

        total_score += instrument_score
        instruments_analyzed += 1

        # Add to details
        pcr_details.append({
            'Instrument': instrument,
            'Spot': f"₹ {data.get('spot', 0):,.2f}",
            'Total CE OI': f"{total_ce_oi:,}",
            'Total PE OI': f"{total_pe_oi:,}",
            'PCR (OI)': f"{pcr_oi:.2f}",
            'OI Bias': f"{oi_bias} {'⚖️' if oi_bias == 'NEUTRAL' else '🐂' if oi_bias == 'BULLISH' else '🐻'}",
            'CE Δ OI': f"{total_ce_change:,}",
            'PE Δ OI': f"{total_pe_change:,}",
            'PCR (Δ OI)': f"{pcr_change_oi:.2f}",
            'Δ OI Bias': f"{change_bias} {'⚖️' if change_bias == 'NEUTRAL' else '🐂' if change_bias == 'BULLISH' else '🐻'}"
        })

    # Calculate overall score
    overall_score = total_score / instruments_analyzed if instruments_analyzed > 0 else 0

    # Determine overall bias
    if overall_score > 10:
        bias = "BULLISH"
    elif overall_score < -10:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    # Calculate confidence
    confidence = min(100, abs(overall_score))

    return {
        'bias': bias,
        'score': overall_score,
        'bullish_instruments': bullish_instruments,
        'bearish_instruments': bearish_instruments,
        'neutral_instruments': neutral_instruments,
        'total_instruments': instruments_analyzed,
        'confidence': confidence,
        'pcr_details': pcr_details
    }


def calculate_option_chain_atm_sentiment(NSE_INSTRUMENTS):
    """
    Calculate sentiment from Option Chain ATM Zone Analysis
    Returns: dict with sentiment, score, and details
    """
    # Check if ATM zone bias data exists in session state
    instruments = ['NIFTY', 'SENSEX', 'FINNIFTY', 'MIDCPNIFTY']

    bullish_instruments = 0
    bearish_instruments = 0
    neutral_instruments = 0
    total_score = 0
    instruments_analyzed = 0

    atm_details = []

    for instrument in instruments:
        atm_key = f'{instrument}_atm_zone_bias'
        if atm_key not in st.session_state:
            continue

        df_atm = st.session_state[atm_key]

        # Get ATM zone data (Zone == "ATM")
        atm_row = df_atm[df_atm["Zone"] == "ATM"]
        if atm_row.empty:
            continue

        atm_row = atm_row.iloc[0]
        verdict = str(atm_row.get('Verdict', 'Neutral')).upper()

        # Calculate score based on verdict
        if 'STRONG BULLISH' in verdict:
            score = 75
            bullish_instruments += 1
        elif 'BULLISH' in verdict:
            score = 40
            bullish_instruments += 1
        elif 'STRONG BEARISH' in verdict:
            score = -75
            bearish_instruments += 1
        elif 'BEARISH' in verdict:
            score = -40
            bearish_instruments += 1
        else:
            score = 0
            neutral_instruments += 1

        total_score += score
        instruments_analyzed += 1

        # Collect detailed ATM zone information for this instrument with ALL bias metrics
        # Note: OI_Change_Bias is same as ChgOI_Bias (included for compatibility)
        atm_detail = {
            'Instrument': instrument,
            'Strike': atm_row.get('Strike', 'N/A'),
            'Zone': atm_row.get('Zone', 'ATM'),
            'Level': atm_row.get('Level', 'N/A'),
            'OI_Bias': atm_row.get('OI_Bias', 'N/A'),
            'ChgOI_Bias': atm_row.get('ChgOI_Bias', 'N/A'),
            'Volume_Bias': atm_row.get('Volume_Bias', 'N/A'),
            'Delta_Bias': atm_row.get('Delta_Bias', 'N/A'),
            'Gamma_Bias': atm_row.get('Gamma_Bias', 'N/A'),
            'Premium_Bias': atm_row.get('Premium_Bias', 'N/A'),
            'AskQty_Bias': atm_row.get('AskQty_Bias', 'N/A'),
            'BidQty_Bias': atm_row.get('BidQty_Bias', 'N/A'),
            'IV_Bias': atm_row.get('IV_Bias', 'N/A'),
            'DVP_Bias': atm_row.get('DVP_Bias', 'N/A'),
            'Delta_Exposure_Bias': atm_row.get('Delta_Exposure_Bias', 'N/A'),
            'Gamma_Exposure_Bias': atm_row.get('Gamma_Exposure_Bias', 'N/A'),
            'IV_Skew_Bias': atm_row.get('IV_Skew_Bias', 'N/A'),
            'OI_Change_Bias': atm_row.get('ChgOI_Bias', atm_row.get('OI_Change_Bias', 'N/A')),  # Alias for ChgOI_Bias
            'BiasScore': atm_row.get('BiasScore', 0),
            'Verdict': atm_row.get('Verdict', 'Neutral'),
            'Score': f"{score:+.0f}"
        }
        atm_details.append(atm_detail)

    # Calculate overall score and bias
    if instruments_analyzed == 0:
        return None

    overall_score = total_score / instruments_analyzed

    # Determine overall bias
    if overall_score > 30:
        bias = "BULLISH"
    elif overall_score < -30:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    # Calculate confidence
    confidence = min(100, abs(overall_score))

    return {
        'bias': bias,
        'score': overall_score,
        'bullish_instruments': bullish_instruments,
        'bearish_instruments': bearish_instruments,
        'neutral_instruments': neutral_instruments,
        'total_instruments': instruments_analyzed,
        'confidence': confidence,
        'atm_details': atm_details
    }


def calculate_overall_sentiment():
    """
    Calculate overall market sentiment by combining all data sources
    """
    # Initialize sentiment sources
    sentiment_sources = {}

    # 1. Stock Performance Sentiment
    if 'bias_analysis_results' in st.session_state and st.session_state.bias_analysis_results:
        analysis = st.session_state.bias_analysis_results
        if analysis.get('success'):
            stock_data = analysis.get('stock_data', [])
            stock_sentiment = calculate_stock_performance_sentiment(stock_data)
            if stock_sentiment:
                sentiment_sources['Stock Performance'] = stock_sentiment

    # 2. Technical Indicators Sentiment
    if 'bias_analysis_results' in st.session_state and st.session_state.bias_analysis_results:
        analysis = st.session_state.bias_analysis_results
        if analysis.get('success'):
            bias_results = analysis.get('bias_results', [])
            tech_sentiment = calculate_technical_indicators_sentiment(bias_results)
            if tech_sentiment:
                sentiment_sources['Technical Indicators'] = tech_sentiment

    # 3. PCR Analysis Sentiment
    pcr_sentiment = calculate_option_chain_pcr_sentiment(None)
    if pcr_sentiment:
        sentiment_sources['PCR Analysis'] = pcr_sentiment

    # 4. Option Chain Analysis Sentiment
    oc_sentiment = calculate_option_chain_atm_sentiment(None)
    if oc_sentiment and oc_sentiment['total_instruments'] > 0:
        sentiment_sources['Option Chain Analysis'] = oc_sentiment

    # If no data available
    if not sentiment_sources:
        return {
            'data_available': False,
            'overall_sentiment': 'NEUTRAL',
            'overall_score': 0,
            'confidence': 0,
            'sources': {},
            'bullish_sources': 0,
            'bearish_sources': 0,
            'neutral_sources': 0,
            'source_count': 0
        }

    # Calculate weighted overall sentiment
    source_weights = {
        'Stock Performance': 2.0,
        'Technical Indicators': 3.0,
        'PCR Analysis': 2.5,
        'Option Chain Analysis': 2.0
    }

    total_weighted_score = 0
    total_weight = 0

    bullish_sources = 0
    bearish_sources = 0
    neutral_sources = 0

    for source_name, source_data in sentiment_sources.items():
        score = source_data.get('score', 0)
        weight = source_weights.get(source_name, 1.0)

        total_weighted_score += score * weight
        total_weight += weight

        # Count source bias
        bias = source_data.get('bias', 'NEUTRAL')
        if bias == 'BULLISH':
            bullish_sources += 1
        elif bias == 'BEARISH':
            bearish_sources += 1
        else:
            neutral_sources += 1

    # Calculate overall score
    overall_score = total_weighted_score / total_weight if total_weight > 0 else 0

    # Determine overall sentiment
    if overall_score > 25:
        overall_sentiment = "BULLISH"
    elif overall_score < -25:
        overall_sentiment = "BEARISH"
    else:
        overall_sentiment = "NEUTRAL"

    # Calculate confidence
    score_magnitude = min(100, abs(overall_score))

    # Factor in source agreement
    total_sources = len(sentiment_sources)
    if overall_sentiment == 'BULLISH':
        source_agreement = bullish_sources / total_sources if total_sources > 0 else 0
    elif overall_sentiment == 'BEARISH':
        source_agreement = bearish_sources / total_sources if total_sources > 0 else 0
    else:
        source_agreement = neutral_sources / total_sources if total_sources > 0 else 0

    final_confidence = score_magnitude * source_agreement

    return {
        'overall_sentiment': overall_sentiment,
        'overall_score': overall_score,
        'confidence': final_confidence,
        'sources': sentiment_sources,
        'data_available': True,
        'bullish_sources': bullish_sources,
        'bearish_sources': bearish_sources,
        'neutral_sources': neutral_sources,
        'source_count': len(sentiment_sources)
    }


def run_all_analyses(NSE_INSTRUMENTS):
    """
    Runs all analyses and stores results in session state:
    1. Bias Analysis Pro (includes stock data and technical indicators)
    2. Option Chain Analysis (includes PCR and ATM zone analysis)
    """
    success = True
    errors = []

    try:
        # 1. Run Bias Analysis Pro
        with st.spinner("🎯 Running Bias Analysis Pro..."):
            try:
                symbol = "^NSEI"  # NIFTY 50
                results = st.session_state.bias_analyzer.analyze_all_bias_indicators(symbol)
                st.session_state.bias_analysis_results = results
                if results.get('success'):
                    st.success("✅ Bias Analysis Pro completed!")
                else:
                    errors.append(f"Bias Analysis Pro: {results.get('error', 'Unknown error')}")
                    success = False
            except Exception as e:
                errors.append(f"Bias Analysis Pro: {str(e)}")
                success = False

        # 2. Run Option Chain Analysis for all instruments
        with st.spinner("📊 Running Option Chain Analysis for all instruments..."):
            try:
                from nse_options_helpers import calculate_and_store_atm_zone_bias_silent
                from nse_options_analyzer import fetch_option_chain_data as fetch_oc

                overall_data = {}
                all_instruments = list(NSE_INSTRUMENTS['indices'].keys())

                # Create a progress bar
                progress_bar = st.progress(0)
                progress_text = st.empty()

                for idx, instrument in enumerate(all_instruments):
                    progress_text.text(f"Analyzing {instrument}... ({idx + 1}/{len(all_instruments)})")

                    # Fetch basic option chain data
                    data = fetch_oc(instrument)
                    overall_data[instrument] = data

                    # Calculate and store ATM zone bias data silently
                    calculate_and_store_atm_zone_bias_silent(instrument, NSE_INSTRUMENTS)

                    progress_bar.progress((idx + 1) / len(all_instruments))

                st.session_state['overall_option_data'] = overall_data
                progress_bar.progress(1.0)
                progress_text.empty()
                st.success("✅ Option Chain Analysis completed!")
            except Exception as e:
                errors.append(f"Option Chain Analysis: {str(e)}")
                success = False

    except Exception as e:
        errors.append(f"Overall error: {str(e)}")
        success = False

    return success, errors


def render_overall_market_sentiment(NSE_INSTRUMENTS=None):
    """
    Renders the Overall Market Sentiment tab with comprehensive analysis
    Auto-refreshes every 60 seconds
    """
    st.markdown("## 🌟 Overall Market Sentiment")
    st.caption("🔄 Auto-refreshing every 60 seconds")
    st.markdown("---")

    # Initialize auto-refresh timestamp
    if 'sentiment_last_refresh' not in st.session_state:
        st.session_state.sentiment_last_refresh = 0

    # Initialize auto-run flag
    if 'sentiment_auto_run_done' not in st.session_state:
        st.session_state.sentiment_auto_run_done = False

    # Auto-run analyses on first load
    if not st.session_state.sentiment_auto_run_done and NSE_INSTRUMENTS is not None:
        with st.spinner("🔄 Running initial analyses..."):
            success, errors = run_all_analyses(NSE_INSTRUMENTS)
            st.session_state.sentiment_auto_run_done = True
            st.session_state.sentiment_last_refresh = time.time()
            if not success:
                for error in errors:
                    st.warning(f"⚠️ {error}")

    # Auto-refresh every 60 seconds
    current_time = time.time()
    time_since_refresh = current_time - st.session_state.sentiment_last_refresh

    if time_since_refresh >= 60 and NSE_INSTRUMENTS is not None:
        with st.spinner("🔄 Auto-refreshing analyses..."):
            success, errors = run_all_analyses(NSE_INSTRUMENTS)
            st.session_state.sentiment_last_refresh = time.time()
            if success:
                st.rerun()

    # Calculate overall sentiment
    result = calculate_overall_sentiment()

    if not result['data_available']:
        st.warning("⚠️ No data available. Running analyses...")

        # Automatically run analyses
        if NSE_INSTRUMENTS is not None:
            with st.spinner("🔄 Running all analyses..."):
                success, errors = run_all_analyses(NSE_INSTRUMENTS)

                if success:
                    st.session_state.sentiment_last_refresh = time.time()
                    st.success("✅ Analyses completed! Refreshing...")
                    st.rerun()
                else:
                    st.error("❌ Some analyses failed:")
                    for error in errors:
                        st.error(f"  - {error}")

        return

    # ═══════════════════════════════════════════════════════════════════
    # HEADER METRICS
    # ═══════════════════════════════════════════════════════════════════

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        sentiment = result['overall_sentiment']
        if sentiment == 'BULLISH':
            st.markdown(f"""
            <div style='padding: 20px; background: linear-gradient(135deg, #00ff88 0%, #00cc66 100%);
                        border-radius: 10px; text-align: center;'>
                <h2 style='margin: 0; color: white;'>🚀 {sentiment}</h2>
                <p style='margin: 5px 0 0 0; color: white; font-size: 14px;'>Overall Sentiment</p>
            </div>
            """, unsafe_allow_html=True)
        elif sentiment == 'BEARISH':
            st.markdown(f"""
            <div style='padding: 20px; background: linear-gradient(135deg, #ff4444 0%, #cc0000 100%);
                        border-radius: 10px; text-align: center;'>
                <h2 style='margin: 0; color: white;'>📉 {sentiment}</h2>
                <p style='margin: 5px 0 0 0; color: white; font-size: 14px;'>Overall Sentiment</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style='padding: 20px; background: linear-gradient(135deg, #ffa500 0%, #ff8c00 100%);
                        border-radius: 10px; text-align: center;'>
                <h2 style='margin: 0; color: white;'>⚖️ {sentiment}</h2>
                <p style='margin: 5px 0 0 0; color: white; font-size: 14px;'>Overall Sentiment</p>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        score = result['overall_score']
        score_color = '#00ff88' if score > 0 else '#ff4444' if score < 0 else '#ffa500'
        st.markdown(f"""
        <div style='padding: 20px; background: #1e1e1e; border-radius: 10px; text-align: center;
                    border-left: 4px solid {score_color};'>
            <h2 style='margin: 0; color: {score_color};'>{score:+.1f}</h2>
            <p style='margin: 5px 0 0 0; color: #888; font-size: 14px;'>Overall Score</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        confidence = result['confidence']
        conf_color = '#00ff88' if confidence > 70 else '#ffa500' if confidence > 40 else '#ff4444'
        st.markdown(f"""
        <div style='padding: 20px; background: #1e1e1e; border-radius: 10px; text-align: center;
                    border-left: 4px solid {conf_color};'>
            <h2 style='margin: 0; color: {conf_color};'>{confidence:.1f}%</h2>
            <p style='margin: 5px 0 0 0; color: #888; font-size: 14px;'>Confidence</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        source_count = result['source_count']
        st.markdown(f"""
        <div style='padding: 20px; background: #1e1e1e; border-radius: 10px; text-align: center;
                    border-left: 4px solid #6495ED;'>
            <h2 style='margin: 0; color: #6495ED;'>{source_count}</h2>
            <p style='margin: 5px 0 0 0; color: #888; font-size: 14px;'>Active Sources</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ═══════════════════════════════════════════════════════════════════
    # SOURCE AGREEMENT VISUALIZATION
    # ═══════════════════════════════════════════════════════════════════

    st.markdown("### 📊 Source Agreement")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("🟢 Bullish Sources", result['bullish_sources'])
    with col2:
        st.metric("🔴 Bearish Sources", result['bearish_sources'])
    with col3:
        st.metric("🟡 Neutral Sources", result['neutral_sources'])

    # Progress bar for source distribution
    total = result['source_count']
    if total > 0:
        bullish_pct = (result['bullish_sources'] / total) * 100
        bearish_pct = (result['bearish_sources'] / total) * 100
        neutral_pct = (result['neutral_sources'] / total) * 100

        st.markdown(f"""
        <div style='background: #1e1e1e; border-radius: 10px; padding: 10px; margin: 10px 0;'>
            <div style='display: flex; height: 30px; border-radius: 5px; overflow: hidden;'>
                <div style='width: {bullish_pct}%; background: #00ff88; display: flex; align-items: center;
                            justify-content: center; color: black; font-weight: bold;'>
                    {bullish_pct:.0f}%
                </div>
                <div style='width: {bearish_pct}%; background: #ff4444; display: flex; align-items: center;
                            justify-content: center; color: white; font-weight: bold;'>
                    {bearish_pct:.0f}%
                </div>
                <div style='width: {neutral_pct}%; background: #ffa500; display: flex; align-items: center;
                            justify-content: center; color: white; font-weight: bold;'>
                    {neutral_pct:.0f}%
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ═══════════════════════════════════════════════════════════════════
    # DETAILED ANALYSIS BY SOURCE - WITH TABLES
    # ═══════════════════════════════════════════════════════════════════

    st.markdown("### 📈 Detailed Analysis by Source")

    sources = result['sources']

    # ─────────────────────────────────────────────────────────────────
    # 1. STOCK PERFORMANCE TABLE
    # ─────────────────────────────────────────────────────────────────
    if 'Stock Performance' in sources:
        source_data = sources['Stock Performance']
        with st.expander("**📊 Stock Performance (Market Breadth)**", expanded=True):
            bias = source_data.get('bias', 'NEUTRAL')
            score = source_data.get('score', 0)
            confidence = source_data.get('confidence', 0)

            # Color based on bias
            if bias == 'BULLISH':
                bg_color = '#00ff88'
                text_color = 'black'
                icon = '🐂'
            elif bias == 'BEARISH':
                bg_color = '#ff4444'
                text_color = 'white'
                icon = '🐻'
            else:
                bg_color = '#ffa500'
                text_color = 'white'
                icon = '⚖️'

            # Display source card
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                st.markdown(f"""
                <div style='background: {bg_color}; padding: 15px; border-radius: 10px;'>
                    <h3 style='margin: 0; color: {text_color};'>{icon} {bias}</h3>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                st.metric("Score", f"{score:+.1f}")

            with col3:
                st.metric("Confidence", f"{confidence:.1f}%")

            st.markdown(f"""
            **Market Breadth:** {source_data.get('breadth_pct', 0):.1f}%
            **Avg Weighted Change:** {source_data.get('avg_change', 0):+.2f}%
            **Bullish Stocks:** {source_data.get('bullish_stocks', 0)} | **Bearish:** {source_data.get('bearish_stocks', 0)} | **Neutral:** {source_data.get('neutral_stocks', 0)}
            """)

            # Stock Performance Table
            stock_details = source_data.get('stock_details', [])
            if stock_details:
                # Create DataFrame
                stock_df = pd.DataFrame(stock_details)
                stock_df['symbol'] = stock_df['symbol'].str.replace('.NS', '')
                stock_df['change_pct'] = stock_df['change_pct'].apply(lambda x: f"{x:.2f}%")
                stock_df['weight'] = stock_df['weight'].apply(lambda x: f"{x:.2f}%")

                # Add bias column
                def get_stock_bias(row):
                    change = float(row['change_pct'].replace('%', ''))
                    if change > 0.5:
                        return "🐂 BULLISH"
                    elif change < -0.5:
                        return "🐻 BEARISH"
                    else:
                        return "⚖️ NEUTRAL"

                stock_df['bias'] = stock_df.apply(get_stock_bias, axis=1)

                # Rename columns
                stock_df = stock_df.rename(columns={
                    'symbol': 'Symbol',
                    'change_pct': 'Change %',
                    'weight': 'Weight',
                    'bias': 'Bias'
                })

                st.dataframe(stock_df, use_container_width=True, hide_index=True)

    # ─────────────────────────────────────────────────────────────────
    # 2. TECHNICAL INDICATORS TABLE
    # ─────────────────────────────────────────────────────────────────
    if 'Technical Indicators' in sources:
        source_data = sources['Technical Indicators']
        with st.expander("**📊 Technical Indicators (Bias Analysis Pro)**", expanded=True):
            bias = source_data.get('bias', 'NEUTRAL')
            score = source_data.get('score', 0)
            confidence = source_data.get('confidence', 0)

            # Color based on bias
            if bias == 'BULLISH':
                bg_color = '#00ff88'
                text_color = 'black'
                icon = '🐂'
            elif bias == 'BEARISH':
                bg_color = '#ff4444'
                text_color = 'white'
                icon = '🐻'
            else:
                bg_color = '#ffa500'
                text_color = 'white'
                icon = '⚖️'

            # Display source card
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                st.markdown(f"""
                <div style='background: {bg_color}; padding: 15px; border-radius: 10px;'>
                    <h3 style='margin: 0; color: {text_color};'>{icon} {bias}</h3>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                st.metric("Score", f"{score:+.1f}")

            with col3:
                st.metric("Confidence", f"{confidence:.1f}%")

            st.markdown(f"""
            **Bullish Indicators:** {source_data.get('bullish_count', 0)} | **Bearish:** {source_data.get('bearish_count', 0)} | **Neutral:** {source_data.get('neutral_count', 0)}
            **Total Analyzed:** {source_data.get('total_count', 0)}
            """)

            # Technical Indicators Table
            indicator_details = source_data.get('indicator_details', [])
            if indicator_details:
                # Create DataFrame
                tech_df = pd.DataFrame(indicator_details)

                # Add emoji to bias
                def get_bias_emoji(bias):
                    bias_upper = str(bias).upper()
                    if 'BULLISH' in bias_upper or 'STRONG BUY' in bias_upper or 'STABLE' in bias_upper:
                        return f"🐂 {bias}"
                    elif 'BEARISH' in bias_upper or 'WEAK' in bias_upper or 'HIGH RISK' in bias_upper:
                        return f"🐻 {bias}"
                    else:
                        return f"⚖️ {bias}"

                tech_df['bias'] = tech_df['bias'].apply(get_bias_emoji)
                tech_df['score'] = tech_df['score'].apply(lambda x: f"{x:.2f}")
                tech_df['weight'] = tech_df['weight'].apply(lambda x: f"{x:.1f}")

                # Rename columns
                tech_df = tech_df.rename(columns={
                    'indicator': 'Indicator',
                    'value': 'Value',
                    'bias': 'Bias',
                    'score': 'Score',
                    'weight': 'Weight'
                })

                st.dataframe(tech_df, use_container_width=True, hide_index=True)

    # ─────────────────────────────────────────────────────────────────
    # 3. PCR ANALYSIS TABLE
    # ─────────────────────────────────────────────────────────────────
    if 'PCR Analysis' in sources:
        source_data = sources['PCR Analysis']
        with st.expander("**📊 PCR Analysis (Put-Call Ratio)**", expanded=True):
            bias = source_data.get('bias', 'NEUTRAL')
            score = source_data.get('score', 0)
            confidence = source_data.get('confidence', 0)

            # Color based on bias
            if bias == 'BULLISH':
                bg_color = '#00ff88'
                text_color = 'black'
                icon = '🐂'
            elif bias == 'BEARISH':
                bg_color = '#ff4444'
                text_color = 'white'
                icon = '🐻'
            else:
                bg_color = '#ffa500'
                text_color = 'white'
                icon = '⚖️'

            # Display source card
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                st.markdown(f"""
                <div style='background: {bg_color}; padding: 15px; border-radius: 10px;'>
                    <h3 style='margin: 0; color: {text_color};'>{icon} {bias}</h3>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                st.metric("Score", f"{score:+.1f}")

            with col3:
                st.metric("Confidence", f"{confidence:.1f}%")

            st.markdown(f"""
            **Bullish Instruments:** {source_data.get('bullish_instruments', 0)} | **Bearish:** {source_data.get('bearish_instruments', 0)} | **Neutral:** {source_data.get('neutral_instruments', 0)}
            **Total Analyzed:** {source_data.get('total_instruments', 0)}
            """)

            # PCR Details Table
            pcr_details = source_data.get('pcr_details', [])
            if pcr_details:
                pcr_df = pd.DataFrame(pcr_details)
                st.dataframe(pcr_df, use_container_width=True, hide_index=True)

    # ─────────────────────────────────────────────────────────────────
    # 4. OPTION CHAIN ANALYSIS TABLE
    # ─────────────────────────────────────────────────────────────────
    if 'Option Chain Analysis' in sources:
        source_data = sources['Option Chain Analysis']
        with st.expander("**📊 Option Chain ATM Zone Analysis**", expanded=True):
            bias = source_data.get('bias', 'NEUTRAL')
            score = source_data.get('score', 0)
            confidence = source_data.get('confidence', 0)

            # Color based on bias
            if bias == 'BULLISH':
                bg_color = '#00ff88'
                text_color = 'black'
                icon = '🐂'
            elif bias == 'BEARISH':
                bg_color = '#ff4444'
                text_color = 'white'
                icon = '🐻'
            else:
                bg_color = '#ffa500'
                text_color = 'white'
                icon = '⚖️'

            # Display source card
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                st.markdown(f"""
                <div style='background: {bg_color}; padding: 15px; border-radius: 10px;'>
                    <h3 style='margin: 0; color: {text_color};'>{icon} {bias}</h3>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                st.metric("Score", f"{score:+.1f}")

            with col3:
                st.metric("Confidence", f"{confidence:.1f}%")

            st.markdown(f"""
            **Bullish Instruments:** {source_data.get('bullish_instruments', 0)} | **Bearish:** {source_data.get('bearish_instruments', 0)} | **Neutral:** {source_data.get('neutral_instruments', 0)}
            **Total Analyzed:** {source_data.get('total_instruments', 0)}
            """)

            # Display ATM Details Summary Table
            atm_details = source_data.get('atm_details', [])
            if atm_details:
                st.markdown("#### 📊 ATM Zone Summary - All Bias Metrics")

                # Create DataFrame from atm_details
                atm_df = pd.DataFrame(atm_details)

                # Add emoji indicators for all bias columns
                bias_columns = [
                    'OI_Bias', 'ChgOI_Bias', 'Volume_Bias', 'Delta_Bias', 'Gamma_Bias',
                    'Premium_Bias', 'AskQty_Bias', 'BidQty_Bias', 'IV_Bias', 'DVP_Bias',
                    'Delta_Exposure_Bias', 'Gamma_Exposure_Bias', 'IV_Skew_Bias',
                    'OI_Change_Bias', 'Verdict'
                ]

                for col in bias_columns:
                    if col in atm_df.columns:
                        atm_df[col] = atm_df[col].apply(lambda x:
                            f"🐂 {x}" if 'BULLISH' in str(x).upper() else
                            f"🐻 {x}" if 'BEARISH' in str(x).upper() else
                            f"⚖️ {x}" if 'NEUTRAL' in str(x).upper() else
                            str(x)
                        )

                st.dataframe(atm_df, use_container_width=True, hide_index=True)

                st.markdown("---")
                st.markdown("#### 📋 Detailed ATM Zone Bias Tables")

            # Display detailed ATM Zone tables for each instrument
            instruments = ['NIFTY', 'SENSEX', 'FINNIFTY', 'MIDCPNIFTY']

            atm_data_available = False
            for instrument in instruments:
                if f'{instrument}_atm_zone_bias' in st.session_state:
                    atm_data_available = True
                    df_atm = st.session_state[f'{instrument}_atm_zone_bias']

                    st.markdown(f"##### {instrument} ATM Zone Bias")

                    # Add emoji indicators for bias columns
                    df_display = df_atm.copy()
                    bias_columns = [col for col in df_display.columns if '_Bias' in col or col == 'Verdict']

                    for col in bias_columns:
                        df_display[col] = df_display[col].apply(lambda x:
                            f"🐂 {x}" if 'BULLISH' in str(x).upper() else
                            f"🐻 {x}" if 'BEARISH' in str(x).upper() else
                            f"⚖️ {x}" if 'NEUTRAL' in str(x).upper() else
                            str(x)
                        )

                    st.dataframe(df_display, use_container_width=True, hide_index=True)

            if not atm_data_available:
                st.info("ℹ️ ATM Zone analysis data will be displayed here when available. Please run bias analysis from individual instrument tabs (NIFTY, BANKNIFTY, SENSEX, etc.) first.")

    st.markdown("---")

    # ═══════════════════════════════════════════════════════════════════
    # INTERPRETATION & RECOMMENDATIONS
    # ═══════════════════════════════════════════════════════════════════

    st.markdown("### 💡 Interpretation & Recommendations")

    sentiment = result['overall_sentiment']
    confidence = result['confidence']
    score = result['overall_score']

    # Generate interpretation
    if sentiment == 'BULLISH':
        if confidence > 70:
            interpretation = "🚀 **Strong Bullish Signal**: Multiple analysis sources align towards a bullish market sentiment. High confidence suggests this is a reliable signal."
            recommendation = "✅ **Recommendation**: Consider bullish strategies. Look for long positions, call options, or bull spreads. Focus on support levels for entry points."
        else:
            interpretation = "📈 **Moderate Bullish Signal**: Overall sentiment is bullish, but confidence is moderate. Some indicators may be conflicting."
            recommendation = "⚠️ **Recommendation**: Bullish bias with caution. Consider smaller position sizes or wait for higher confirmation. Monitor key support levels."

    elif sentiment == 'BEARISH':
        if confidence > 70:
            interpretation = "📉 **Strong Bearish Signal**: Multiple analysis sources align towards a bearish market sentiment. High confidence suggests this is a reliable signal."
            recommendation = "✅ **Recommendation**: Consider bearish strategies. Look for short positions, put options, or bear spreads. Focus on resistance levels for entry points."
        else:
            interpretation = "🔻 **Moderate Bearish Signal**: Overall sentiment is bearish, but confidence is moderate. Some indicators may be conflicting."
            recommendation = "⚠️ **Recommendation**: Bearish bias with caution. Consider smaller position sizes or wait for higher confirmation. Monitor key resistance levels."

    else:
        interpretation = "⚖️ **Neutral/Consolidation**: Market indicators show no clear directional bias. This could indicate a ranging market or conflicting signals."
        recommendation = "🔄 **Recommendation**: Stay on the sidelines or use neutral strategies. Consider iron condors, straddles, or range-bound trading."

    st.info(interpretation)
    st.success(recommendation)

    # Risk Warning
    st.warning("""
    **⚠️ Risk Warning**:
    - This sentiment analysis is based on technical indicators and historical data
    - Past performance does not guarantee future results
    - Always use proper risk management and position sizing
    - Combine this analysis with your own research and market understanding
    - Consider fundamental factors, news events, and market conditions
    """)

    # Last Updated and Next Refresh
    st.markdown("---")

    # Calculate time until next refresh
    time_since_refresh = time.time() - st.session_state.sentiment_last_refresh
    time_until_refresh = max(0, 60 - time_since_refresh)

    col1, col2 = st.columns(2)

    with col1:
        last_update_time = datetime.fromtimestamp(st.session_state.sentiment_last_refresh)
        st.caption(f"📅 Last updated: {last_update_time.strftime('%Y-%m-%d %H:%M:%S')}")

    with col2:
        if time_until_refresh > 0:
            st.caption(f"⏱️ Next refresh in: {int(time_until_refresh)} seconds")
        else:
            st.caption(f"⏱️ Refreshing now...")

    # Action buttons
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔄 Refresh Now", use_container_width=True):
            st.session_state.sentiment_last_refresh = 0  # Force immediate refresh
            st.rerun()

    with col2:
        if NSE_INSTRUMENTS is not None:
            if st.button("🎯 Re-run All Analyses", type="primary", use_container_width=True, key="rerun_bias_button"):
                success, errors = run_all_analyses(NSE_INSTRUMENTS)
                st.session_state.sentiment_last_refresh = time.time()

                if success:
                    st.balloons()
                    st.success("🎉 All analyses completed successfully! Refreshing results...")
                    st.rerun()
                else:
                    st.error("❌ Some analyses failed:")
                    for error in errors:
                        st.error(f"  - {error}")

    # Use st.empty() to trigger rerun for countdown
    if time_until_refresh > 0:
        time.sleep(min(1, time_until_refresh))
        st.rerun()
