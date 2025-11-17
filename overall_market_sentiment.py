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
from nse_options_helpers import fetch_option_chain_data


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
        weight = stock.get('weight', 0)

        # Weighted contribution
        total_weighted_change += change_pct * weight
        total_weight += weight

        # Count bias
        if change_pct > 0.5:
            bullish_stocks += 1
        elif change_pct < -0.5:
            bearish_stocks += 1
        else:
            neutral_stocks += 1

    # Calculate weighted average change
    avg_change = total_weighted_change / total_weight if total_weight > 0 else 0

    # Convert to score (-100 to +100)
    score = min(100, max(-100, avg_change * 10))

    # Determine bias
    if score > 20:
        bias = "BULLISH"
    elif score < -20:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    # Calculate breadth percentage
    total_stocks = bullish_stocks + bearish_stocks + neutral_stocks
    breadth_pct = (bullish_stocks / total_stocks * 100) if total_stocks > 0 else 50

    return {
        'bias': bias,
        'score': score,
        'avg_change': avg_change,
        'breadth_pct': breadth_pct,
        'bullish_stocks': bullish_stocks,
        'bearish_stocks': bearish_stocks,
        'neutral_stocks': neutral_stocks,
        'total_stocks': total_stocks,
        'confidence': min(100, abs(score) * 1.5)
    }


def calculate_technical_indicators_sentiment(bias_results):
    """
    Calculate sentiment from technical indicators
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
        'confidence': confidence
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
    main_indices = ['NIFTY', 'BANKNIFTY', 'SENSEX']

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
        inst_score = (oi_score + change_score) / 2
        total_score += inst_score
        instruments_analyzed += 1

        # Count overall bias
        if inst_score > 10:
            bullish_instruments += 1
        elif inst_score < -10:
            bearish_instruments += 1
        else:
            neutral_instruments += 1

        pcr_details.append({
            'instrument': instrument,
            'spot': data.get('spot', 0),
            'pcr_oi': pcr_oi,
            'pcr_change_oi': pcr_change_oi,
            'oi_bias': oi_bias,
            'change_bias': change_bias,
            'score': inst_score
        })

    if instruments_analyzed == 0:
        return None

    # Calculate overall score
    overall_score = total_score / instruments_analyzed

    # Determine bias
    if overall_score > 15:
        bias = "BULLISH"
    elif overall_score < -15:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    # Calculate confidence
    confidence = min(100, abs(overall_score) * 2)

    return {
        'bias': bias,
        'score': overall_score,
        'bullish_instruments': bullish_instruments,
        'bearish_instruments': bearish_instruments,
        'neutral_instruments': neutral_instruments,
        'total_instruments': instruments_analyzed,
        'pcr_details': pcr_details,
        'confidence': confidence
    }


def calculate_option_chain_atm_sentiment():
    """
    Calculate sentiment from Option Chain ATM Zone Analysis
    Returns: dict with sentiment, score, and details
    """
    # This would analyze the detailed option chain data with ATM zone bias
    # For now, we'll use the overall option data if available
    if 'overall_option_data' not in st.session_state or not st.session_state.overall_option_data:
        return None

    option_data = st.session_state.overall_option_data

    # We'll calculate a simple aggregate score based on all instruments
    total_bias_score = 0
    instrument_count = 0
    bullish_instruments = 0
    bearish_instruments = 0
    neutral_instruments = 0

    for instrument, data in option_data.items():
        if not data.get('success'):
            continue

        # Get bias score if available
        bias_score = data.get('overall_bias_score', 0)
        bias = data.get('overall_bias', 'NEUTRAL')

        # Normalize bias score to -100 to +100 scale
        normalized_score = (bias_score / 10) * 100 if bias_score else 0
        total_bias_score += normalized_score
        instrument_count += 1

        if bias in ['BULLISH', 'STRONG_BULLISH']:
            bullish_instruments += 1
        elif bias in ['BEARISH', 'STRONG_BEARISH']:
            bearish_instruments += 1
        else:
            neutral_instruments += 1

    if instrument_count == 0:
        return None

    avg_score = total_bias_score / instrument_count

    # Determine bias
    if avg_score > 20:
        bias = "BULLISH"
    elif avg_score < -20:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    # Calculate confidence
    confidence = min(100, abs(avg_score) * 1.5)

    return {
        'bias': bias,
        'score': avg_score,
        'bullish_instruments': bullish_instruments,
        'bearish_instruments': bearish_instruments,
        'neutral_instruments': neutral_instruments,
        'total_instruments': instrument_count,
        'confidence': confidence
    }


def calculate_overall_sentiment():
    """
    Aggregates bias data from all sources with weighted averaging
    Returns overall sentiment, score, and breakdown
    """
    sentiment_sources = {}
    source_weights = {
        'Stock Performance': 2.0,
        'Technical Indicators': 3.0,
        'PCR Analysis': 2.5,
        'Option Chain Analysis': 2.0
    }

    # Source 1: Stock Performance
    if 'bias_analysis_results' in st.session_state and st.session_state.bias_analysis_results:
        try:
            bias_data = st.session_state.bias_analysis_results
            stock_data = bias_data.get('stock_data', [])

            if stock_data:
                stock_sentiment = calculate_stock_performance_sentiment(stock_data)
                if stock_sentiment:
                    sentiment_sources['Stock Performance'] = stock_sentiment
        except Exception as e:
            st.warning(f"Could not load Stock Performance data: {e}")

    # Source 2: Technical Indicators (Bias Analysis Pro)
    if 'bias_analysis_results' in st.session_state and st.session_state.bias_analysis_results:
        try:
            bias_data = st.session_state.bias_analysis_results
            bias_results = bias_data.get('bias_results', [])

            if bias_results:
                tech_sentiment = calculate_technical_indicators_sentiment(bias_results)
                if tech_sentiment:
                    sentiment_sources['Technical Indicators'] = tech_sentiment
        except Exception as e:
            st.warning(f"Could not load Technical Indicators data: {e}")

    # Source 3: PCR Analysis
    try:
        pcr_sentiment = calculate_option_chain_pcr_sentiment(None)
        if pcr_sentiment:
            sentiment_sources['PCR Analysis'] = pcr_sentiment
    except Exception as e:
        st.warning(f"Could not load PCR Analysis data: {e}")

    # Source 4: Option Chain ATM Analysis
    try:
        atm_sentiment = calculate_option_chain_atm_sentiment()
        if atm_sentiment:
            sentiment_sources['Option Chain Analysis'] = atm_sentiment
    except Exception as e:
        st.warning(f"Could not load Option Chain Analysis data: {e}")

    # Calculate overall sentiment with weighted averaging
    if len(sentiment_sources) == 0:
        return {
            'overall_sentiment': 'NO DATA',
            'overall_score': 0,
            'confidence': 0,
            'sources': sentiment_sources,
            'data_available': False
        }

    # Calculate weighted score
    total_weighted_score = 0
    total_weight = 0

    for source_name, source_data in sentiment_sources.items():
        weight = source_weights.get(source_name, 1.0)
        score = source_data.get('score', 0)
        total_weighted_score += score * weight
        total_weight += weight

    overall_score = total_weighted_score / total_weight if total_weight > 0 else 0

    # Determine overall sentiment
    if overall_score > 25:
        overall_sentiment = 'BULLISH'
    elif overall_score < -25:
        overall_sentiment = 'BEARISH'
    else:
        overall_sentiment = 'NEUTRAL'

    # Calculate confidence based on score magnitude and source agreement
    score_confidence = min(100, abs(overall_score))

    # Check source agreement
    bullish_sources = sum(1 for s in sentiment_sources.values() if s.get('bias') == 'BULLISH')
    bearish_sources = sum(1 for s in sentiment_sources.values() if s.get('bias') == 'BEARISH')
    neutral_sources = len(sentiment_sources) - bullish_sources - bearish_sources

    # Agreement factor (0 to 1)
    if len(sentiment_sources) > 1:
        if overall_sentiment == 'BULLISH':
            agreement = bullish_sources / len(sentiment_sources)
        elif overall_sentiment == 'BEARISH':
            agreement = bearish_sources / len(sentiment_sources)
        else:
            agreement = neutral_sources / len(sentiment_sources)
    else:
        agreement = 1.0

    final_confidence = score_confidence * agreement

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
                overall_data = {}
                all_instruments = list(NSE_INSTRUMENTS['indices'].keys()) + list(NSE_INSTRUMENTS['stocks'].keys())

                # Create a progress bar
                progress_bar = st.progress(0)
                progress_text = st.empty()

                for idx, instrument in enumerate(all_instruments):
                    progress_text.text(f"Analyzing {instrument}... ({idx + 1}/{len(all_instruments)})")
                    data = fetch_option_chain_data(instrument)
                    overall_data[instrument] = data
                    progress_bar.progress((idx + 1) / len(all_instruments))

                st.session_state['overall_option_data'] = overall_data
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
    """
    st.markdown("## 🌟 Overall Market Sentiment")
    st.markdown("---")

    # Calculate overall sentiment
    result = calculate_overall_sentiment()

    if not result['data_available']:
        st.warning("⚠️ No data available. Please click 'Show Bias' to generate comprehensive market analysis.")

        # Add "Show Bias" button
        if NSE_INSTRUMENTS is not None:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("🎯 Show Bias", type="primary", use_container_width=True, key="show_bias_button"):
                    success, errors = run_all_analyses(NSE_INSTRUMENTS)

                    if success:
                        st.balloons()
                        st.success("🎉 All analyses completed successfully! Refreshing results...")
                        st.rerun()
                    else:
                        st.error("❌ Some analyses failed:")
                        for error in errors:
                            st.error(f"  - {error}")

        st.info("""
        **How to use this tab:**

        **Option 1 (Recommended):** Click the **"Show Bias"** button above to automatically run all analyses and display the aggregated market sentiment.

        **Option 2 (Manual):**
        1. Visit the **Bias Analysis Pro** tab to analyze technical indicators
        2. Visit the **Option Chain Analysis** tab to analyze options data
        3. Return to this tab to see the aggregated overall market sentiment
        """)
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
    # DETAILED ANALYSIS BY SOURCE
    # ═══════════════════════════════════════════════════════════════════

    st.markdown("### 📈 Detailed Analysis by Source")

    sources = result['sources']

    for source_name, source_data in sources.items():
        with st.expander(f"**{source_name}**", expanded=True):
            bias = source_data.get('bias', 'NEUTRAL')
            score = source_data.get('score', 0)
            confidence = source_data.get('confidence', 0)

            # Color based on bias
            if bias == 'BULLISH':
                bg_color = '#00ff88'
                text_color = 'black'
                icon = '🚀'
            elif bias == 'BEARISH':
                bg_color = '#ff4444'
                text_color = 'white'
                icon = '📉'
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

            # Display source-specific details
            if source_name == 'Stock Performance':
                st.markdown(f"""
                **Market Breadth:** {source_data.get('breadth_pct', 0):.1f}%
                **Avg Change:** {source_data.get('avg_change', 0):+.2f}%
                **Bullish Stocks:** {source_data.get('bullish_stocks', 0)}
                **Bearish Stocks:** {source_data.get('bearish_stocks', 0)}
                **Neutral Stocks:** {source_data.get('neutral_stocks', 0)}
                """)

            elif source_name == 'Technical Indicators':
                st.markdown(f"""
                **Bullish Indicators:** {source_data.get('bullish_count', 0)}
                **Bearish Indicators:** {source_data.get('bearish_count', 0)}
                **Neutral Indicators:** {source_data.get('neutral_count', 0)}
                **Total Analyzed:** {source_data.get('total_count', 0)}
                """)

            elif source_name == 'PCR Analysis':
                st.markdown(f"""
                **Bullish Instruments:** {source_data.get('bullish_instruments', 0)}
                **Bearish Instruments:** {source_data.get('bearish_instruments', 0)}
                **Neutral Instruments:** {source_data.get('neutral_instruments', 0)}
                **Total Analyzed:** {source_data.get('total_instruments', 0)}
                """)

                # Show PCR details for each instrument
                pcr_details = source_data.get('pcr_details', [])
                if pcr_details:
                    pcr_df = pd.DataFrame(pcr_details)
                    st.dataframe(pcr_df, use_container_width=True, hide_index=True)

            elif source_name == 'Option Chain Analysis':
                st.markdown(f"""
                **Bullish Instruments:** {source_data.get('bullish_instruments', 0)}
                **Bearish Instruments:** {source_data.get('bearish_instruments', 0)}
                **Neutral Instruments:** {source_data.get('neutral_instruments', 0)}
                **Total Analyzed:** {source_data.get('total_instruments', 0)}
                """)

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

    # Last Updated
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Action buttons
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔄 Refresh Analysis", use_container_width=True):
            st.rerun()

    with col2:
        if NSE_INSTRUMENTS is not None:
            if st.button("🎯 Re-run All Analyses", type="primary", use_container_width=True, key="rerun_bias_button"):
                success, errors = run_all_analyses(NSE_INSTRUMENTS)

                if success:
                    st.balloons()
                    st.success("🎉 All analyses completed successfully! Refreshing results...")
                    st.rerun()
                else:
                    st.error("❌ Some analyses failed:")
                    for error in errors:
                        st.error(f"  - {error}")
