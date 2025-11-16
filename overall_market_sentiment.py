"""
Overall Market Sentiment Analysis
Aggregates bias data from all tabs in the application to provide a unified market sentiment view
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from nse_options_helpers import fetch_option_chain_data


def calculate_overall_sentiment():
    """
    Aggregates bias data from all sources with equal weighting
    Returns overall sentiment, score, and breakdown
    """
    sentiment_sources = []
    sentiment_scores = []
    sentiment_details = {}

    # Source 1: Smart Trading Dashboard
    if 'dashboard_results' in st.session_state and st.session_state.dashboard_results:
        try:
            dashboard_data = st.session_state.dashboard_results
            bias = dashboard_data.get('market_bias', 'NEUTRAL')
            bullish_pct = dashboard_data.get('bullish_bias_pct', 0)
            bearish_pct = dashboard_data.get('bearish_bias_pct', 0)

            # Convert to score: -100 to +100
            if bias == 'BULLISH':
                score = bullish_pct
            elif bias == 'BEARISH':
                score = -bearish_pct
            else:
                score = bullish_pct - bearish_pct

            sentiment_sources.append('Smart Trading Dashboard')
            sentiment_scores.append(score)
            sentiment_details['Smart Trading Dashboard'] = {
                'bias': bias,
                'score': score,
                'bullish_pct': bullish_pct,
                'bearish_pct': bearish_pct,
                'reversal_mode': dashboard_data.get('reversal_mode', False)
            }
        except Exception as e:
            st.warning(f"Could not load Smart Trading Dashboard data: {e}")

    # Source 2: Bias Analysis Pro
    if 'bias_analysis_results' in st.session_state and st.session_state.bias_analysis_results:
        try:
            bias_data = st.session_state.bias_analysis_results
            overall_score = bias_data.get('overall_score', 0)
            overall_bias = bias_data.get('overall_bias', 'NEUTRAL')
            confidence = bias_data.get('overall_confidence', 0)

            sentiment_sources.append('Bias Analysis Pro')
            sentiment_scores.append(overall_score)
            sentiment_details['Bias Analysis Pro'] = {
                'bias': overall_bias,
                'score': overall_score,
                'confidence': confidence,
                'bullish_count': bias_data.get('bullish_count', 0),
                'bearish_count': bias_data.get('bearish_count', 0),
                'neutral_count': bias_data.get('neutral_count', 0)
            }
        except Exception as e:
            st.warning(f"Could not load Bias Analysis Pro data: {e}")

    # Source 3: Option Chain Analysis
    if 'overall_option_data' in st.session_state and st.session_state.overall_option_data:
        try:
            option_data = st.session_state.overall_option_data

            # Calculate aggregate score from all instruments
            total_bias_score = 0
            instrument_count = 0
            bullish_instruments = 0
            bearish_instruments = 0
            neutral_instruments = 0

            instruments = ['NIFTY', 'BANKNIFTY', 'NIFTYIT', 'NIFTYAUTO', 'TCS', 'RELIANCE', 'HDFCBANK']

            for instrument in instruments:
                if instrument in option_data:
                    inst_data = option_data[instrument]
                    bias = inst_data.get('overall_bias', 'NEUTRAL')
                    bias_score = inst_data.get('overall_bias_score', 0)

                    # Normalize bias score to -100 to +100 scale
                    normalized_score = (bias_score / 10) * 100
                    total_bias_score += normalized_score
                    instrument_count += 1

                    if bias == 'BULLISH' or bias == 'STRONG_BULLISH':
                        bullish_instruments += 1
                    elif bias == 'BEARISH' or bias == 'STRONG_BEARISH':
                        bearish_instruments += 1
                    else:
                        neutral_instruments += 1

            if instrument_count > 0:
                avg_option_score = total_bias_score / instrument_count

                # Determine overall bias from options
                if avg_option_score > 30:
                    option_bias = 'BULLISH'
                elif avg_option_score < -30:
                    option_bias = 'BEARISH'
                else:
                    option_bias = 'NEUTRAL'

                sentiment_sources.append('Option Chain Analysis')
                sentiment_scores.append(avg_option_score)
                sentiment_details['Option Chain Analysis'] = {
                    'bias': option_bias,
                    'score': avg_option_score,
                    'bullish_instruments': bullish_instruments,
                    'bearish_instruments': bearish_instruments,
                    'neutral_instruments': neutral_instruments,
                    'total_instruments': instrument_count
                }
        except Exception as e:
            st.warning(f"Could not load Option Chain Analysis data: {e}")

    # Calculate overall sentiment with equal weighting
    if len(sentiment_scores) == 0:
        return {
            'overall_sentiment': 'NO DATA',
            'overall_score': 0,
            'confidence': 0,
            'sources': sentiment_sources,
            'details': sentiment_details,
            'data_available': False
        }

    # Equal weight for all sources
    overall_score = sum(sentiment_scores) / len(sentiment_scores)

    # Determine overall sentiment
    if overall_score > 30:
        overall_sentiment = 'BULLISH'
    elif overall_score < -30:
        overall_sentiment = 'BEARISH'
    else:
        overall_sentiment = 'NEUTRAL'

    # Calculate confidence based on score magnitude and source agreement
    score_confidence = min(100, abs(overall_score))

    # Check source agreement
    bullish_sources = sum(1 for s in sentiment_scores if s > 30)
    bearish_sources = sum(1 for s in sentiment_scores if s < -30)
    neutral_sources = len(sentiment_scores) - bullish_sources - bearish_sources

    # Agreement factor (0 to 1)
    if len(sentiment_scores) > 1:
        if overall_sentiment == 'BULLISH':
            agreement = bullish_sources / len(sentiment_scores)
        elif overall_sentiment == 'BEARISH':
            agreement = bearish_sources / len(sentiment_scores)
        else:
            agreement = neutral_sources / len(sentiment_scores)
    else:
        agreement = 1.0

    final_confidence = score_confidence * agreement

    return {
        'overall_sentiment': overall_sentiment,
        'overall_score': overall_score,
        'confidence': final_confidence,
        'sources': sentiment_sources,
        'details': sentiment_details,
        'data_available': True,
        'bullish_sources': bullish_sources,
        'bearish_sources': bearish_sources,
        'neutral_sources': neutral_sources,
        'source_count': len(sentiment_scores)
    }


def run_all_analyses(NSE_INSTRUMENTS):
    """
    Runs all three analyses and stores results in session state:
    1. Smart Trading Dashboard
    2. Bias Analysis Pro
    3. Option Chain Analysis
    """
    success = True
    errors = []

    try:
        # 1. Run Smart Trading Dashboard Analysis
        with st.spinner("📊 Running Smart Trading Dashboard analysis..."):
            try:
                symbol = "^NSEI"  # NIFTY 50
                results = st.session_state.smart_dashboard.analyze_market(symbol)
                st.session_state.dashboard_results = results
                st.success("✅ Smart Trading Dashboard analysis completed!")
            except Exception as e:
                errors.append(f"Smart Trading Dashboard: {str(e)}")
                success = False

        # 2. Run Bias Analysis Pro
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

        # 3. Run Option Chain Analysis for all instruments
        with st.spinner("📊 Running Option Chain Analysis for all instruments..."):
            try:
                overall_data = {}
                all_instruments = list(NSE_INSTRUMENTS['indices'].keys()) + list(NSE_INSTRUMENTS['stocks'].keys())

                # Create a progress bar
                progress_bar = st.progress(0)
                progress_text = st.empty()

                for idx, instrument in enumerate(all_instruments):
                    progress_text.text(f"Analyzing {instrument}... ({idx + 1}/{len(all_instruments)})")
                    data = fetch_option_chain_data(instrument, NSE_INSTRUMENTS)
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
    Renders the Overall Market Sentiment tab
    """
    st.markdown("## 🌟 Overall Market Sentiment")
    st.markdown("---")

    # Calculate overall sentiment
    result = calculate_overall_sentiment()

    if not result['data_available']:
        st.warning("⚠️ No data available. Please navigate to other tabs to generate bias data first.")

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
        1. Visit the **Smart Trading Dashboard** tab to generate trading signals
        2. Visit the **Bias Analysis Pro** tab to analyze technical indicators
        3. Visit the **Option Chain Analysis** tab to analyze options data
        4. Return to this tab to see the aggregated overall market sentiment
        """)
        return

    # Header metrics
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

    # Source Agreement Visualization
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

    # Detailed Breakdown by Source
    st.markdown("### 📈 Detailed Analysis by Source")

    details = result['details']

    # Create columns for each source
    source_cols = st.columns(len(details))

    for idx, (source_name, source_data) in enumerate(details.items()):
        with source_cols[idx]:
            bias = source_data['bias']
            score = source_data['score']

            # Color based on bias
            if bias == 'BULLISH' or bias == 'STRONG_BULLISH':
                bg_color = '#00ff88'
                text_color = 'black'
            elif bias == 'BEARISH' or bias == 'STRONG_BEARISH':
                bg_color = '#ff4444'
                text_color = 'white'
            else:
                bg_color = '#ffa500'
                text_color = 'white'

            st.markdown(f"""
            <div style='background: {bg_color}; padding: 15px; border-radius: 10px; margin-bottom: 10px;'>
                <h4 style='margin: 0; color: {text_color};'>{source_name}</h4>
                <p style='margin: 5px 0; color: {text_color}; font-weight: bold;'>{bias}</p>
                <p style='margin: 0; color: {text_color}; font-size: 20px;'>{score:+.1f}</p>
            </div>
            """, unsafe_allow_html=True)

            # Additional details based on source
            if source_name == 'Smart Trading Dashboard':
                st.markdown(f"""
                **Bullish:** {source_data['bullish_pct']:.1f}%
                **Bearish:** {source_data['bearish_pct']:.1f}%
                **Reversal Mode:** {'🔄 Yes' if source_data['reversal_mode'] else '❌ No'}
                """)

            elif source_name == 'Bias Analysis Pro':
                st.markdown(f"""
                **Confidence:** {source_data['confidence']:.1f}%
                **Bullish Indicators:** {source_data['bullish_count']}
                **Bearish Indicators:** {source_data['bearish_count']}
                **Neutral Indicators:** {source_data['neutral_count']}
                """)

            elif source_name == 'Option Chain Analysis':
                st.markdown(f"""
                **Bullish Instruments:** {source_data['bullish_instruments']}
                **Bearish Instruments:** {source_data['bearish_instruments']}
                **Neutral Instruments:** {source_data['neutral_instruments']}
                **Total Analyzed:** {source_data['total_instruments']}
                """)

    st.markdown("---")

    # Interpretation and Recommendations
    st.markdown("### 💡 Interpretation & Recommendations")

    sentiment = result['overall_sentiment']
    confidence = result['confidence']
    score = result['overall_score']

    # Generate interpretation
    if sentiment == 'BULLISH':
        if confidence > 70:
            interpretation = "🚀 **Strong Bullish Signal**: All major indicators align towards a bullish market sentiment. High confidence suggests this is a reliable signal."
            recommendation = "✅ **Recommendation**: Consider bullish strategies. Look for long positions, call options, or bull spreads."
        else:
            interpretation = "📈 **Moderate Bullish Signal**: Overall sentiment is bullish, but confidence is moderate. Some indicators may be conflicting."
            recommendation = "⚠️ **Recommendation**: Bullish bias with caution. Consider smaller position sizes or wait for higher confirmation."

    elif sentiment == 'BEARISH':
        if confidence > 70:
            interpretation = "📉 **Strong Bearish Signal**: All major indicators align towards a bearish market sentiment. High confidence suggests this is a reliable signal."
            recommendation = "✅ **Recommendation**: Consider bearish strategies. Look for short positions, put options, or bear spreads."
        else:
            interpretation = "🔻 **Moderate Bearish Signal**: Overall sentiment is bearish, but confidence is moderate. Some indicators may be conflicting."
            recommendation = "⚠️ **Recommendation**: Bearish bias with caution. Consider smaller position sizes or wait for higher confirmation."

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
