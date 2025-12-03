"""
Overall Market Sentiment Analysis

Aggregates bias data from all sources to provide a comprehensive market sentiment view

Data Sources:
1. Stock Performance (Market Breadth)
2. Technical Indicators (Bias Analysis Pro - 13 indicators matching Pine Script)
3. Option Chain ATM Zone Analysis (Multiple bias metrics)
4. PCR Analysis (Put-Call Ratio for indices)
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import time
import asyncio
import os
from typing import Dict, Any, Optional
from market_hours_scheduler import is_within_trading_hours, scheduler
import requests

# === Telegram Config ===
TELEGRAM_BOT_TOKEN = "8133685842:AAGdHCpi9QRIsS-fWW5Y1AJvS95QL9xU"
TELEGRAM_CHAT_ID = "57096584"

def send_telegram_message(message):
    """Send Telegram message for PCR analysis alerts"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            print(f"✅ Telegram message sent successfully")
        else:
            print(f"⚠️ Telegram message failed with status {response.status_code}")
    except Exception as e:
        print(f"❌ Telegram error: {e}")


# ============================================================================
# SENTIMENT ANALYSIS FUNCTIONS
# ============================================================================

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

    # PCR Analysis Telegram alert removed - only Bias Alignment Alert is sent

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


def calculate_nifty_advanced_metrics_sentiment():
    """
    Calculate sentiment from NIFTY advanced metrics:
    - Synthetic Future Bias
    - ATM Buildup Pattern
    - ATM Vega Bias
    - Distance from Max Pain
    - Call Resistance / Put Support positioning
    - Total Vega Bias

    Returns: dict with sentiment, score, and details
    """
    if 'NIFTY_comprehensive_metrics' not in st.session_state:
        return None

    metrics = st.session_state['NIFTY_comprehensive_metrics']

    # Initialize score
    score = 0
    details = []

    # 1. Synthetic Future Bias (Display Only - Not used in scoring)
    synthetic_bias = metrics.get('Synthetic Future Bias', 'Neutral')
    synthetic_diff = metrics.get('synthetic_diff', 0)
    if 'BULLISH' in str(synthetic_bias).upper():
        # score += 20  # Removed from scoring
        details.append(f"Synthetic Future: Bullish (+{synthetic_diff:.2f})")
    elif 'BEARISH' in str(synthetic_bias).upper():
        # score -= 20  # Removed from scoring
        details.append(f"Synthetic Future: Bearish ({synthetic_diff:.2f})")
    else:
        details.append(f"Synthetic Future: Neutral")

    # 2. ATM Buildup Pattern (Weight: 2.5)
    atm_buildup = metrics.get('ATM Buildup Pattern', 'Neutral')
    if 'SHORT BUILDUP' in str(atm_buildup).upper() or 'PUT WRITING' in str(atm_buildup).upper() or 'SHORT COVERING' in str(atm_buildup).upper():
        score += 25
        details.append(f"ATM Buildup: Bullish ({atm_buildup})")
    elif 'LONG BUILDUP' in str(atm_buildup).upper() or 'CALL WRITING' in str(atm_buildup).upper() or 'LONG UNWINDING' in str(atm_buildup).upper():
        score -= 25
        details.append(f"ATM Buildup: Bearish ({atm_buildup})")
    else:
        details.append(f"ATM Buildup: Neutral")

    # 3. ATM Vega Bias (Display Only - Not used in scoring)
    atm_vega_bias = metrics.get('ATM Vega Bias', 'Neutral')
    if 'BULLISH' in str(atm_vega_bias).upper():
        # score += 15  # Removed from scoring
        details.append(f"ATM Vega: Bullish (High Put Vega)")
    elif 'BEARISH' in str(atm_vega_bias).upper():
        # score -= 15  # Removed from scoring
        details.append(f"ATM Vega: Bearish (High Call Vega)")
    else:
        details.append(f"ATM Vega: Neutral")

    # 4. Distance from Max Pain (Display Only - Not used in scoring)
    distance_from_max_pain = metrics.get('distance_from_max_pain_value', 0)
    if distance_from_max_pain > 50:
        # score -= 20  # Removed from scoring - Above max pain suggests downward pull
        details.append(f"Max Pain Distance: Bearish (+{distance_from_max_pain:.2f}, above max pain)")
    elif distance_from_max_pain < -50:
        # score += 20  # Removed from scoring - Below max pain suggests upward pull
        details.append(f"Max Pain Distance: Bullish ({distance_from_max_pain:.2f}, below max pain)")
    else:
        details.append(f"Max Pain Distance: Neutral ({distance_from_max_pain:+.2f})")

    # 5. Total Vega Bias (Weight: 1.5)
    total_vega_bias = metrics.get('Total Vega Bias', 'Neutral')
    if 'BULLISH' in str(total_vega_bias).upper():
        score += 15
        details.append(f"Total Vega: Bullish (Put Heavy)")
    elif 'BEARISH' in str(total_vega_bias).upper():
        score -= 15
        details.append(f"Total Vega: Bearish (Call Heavy)")
    else:
        details.append(f"Total Vega: Neutral")

    # 6. Call Resistance / Put Support Distance (Weight: 1.0)
    call_resistance_distance = metrics.get('call_resistance_distance', 0)
    put_support_distance = metrics.get('put_support_distance', 0)

    # If close to call resistance, bearish; if close to put support, bullish
    if call_resistance_distance < 50 and call_resistance_distance > 0:
        score -= 10
        details.append(f"Near Call Resistance: Bearish ({call_resistance_distance:.2f} pts)")
    elif put_support_distance < 50 and put_support_distance > 0:
        score += 10
        details.append(f"Near Put Support: Bullish ({put_support_distance:.2f} pts)")

    # Determine overall bias
    if score > 30:
        bias = "BULLISH"
    elif score < -30:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    # Calculate confidence based on score magnitude
    confidence = min(100, abs(score))

    return {
        'bias': bias,
        'score': score,
        'confidence': confidence,
        'details': details,
        'metrics': metrics
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

    # 5. NIFTY Advanced Metrics Sentiment
    nifty_advanced_sentiment = calculate_nifty_advanced_metrics_sentiment()
    if nifty_advanced_sentiment:
        sentiment_sources['NIFTY Advanced Metrics'] = nifty_advanced_sentiment

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
        'Option Chain Analysis': 2.0,
        'NIFTY Advanced Metrics': 2.5
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


def check_bias_alignment():
    """
    Check if all three bias indicators (Technical, PCR, ATM) are aligned for NIFTY (all bullish or all bearish)

    Returns:
        dict: Alignment status with details, or None if data not available
            {
                'aligned': bool,
                'direction': 'BULLISH' or 'BEARISH',
                'instrument': 'NIFTY',
                'technical_bias': str,
                'technical_score': float,
                'pcr_bias': str,
                'pcr_score': float,
                'atm_bias': str,
                'atm_score': float,
                'confidence': float
            }
    """
    # Get Technical Indicators bias for NIFTY
    technical_bias = None
    technical_score = 0
    if 'bias_analysis_results' in st.session_state and st.session_state.bias_analysis_results:
        analysis = st.session_state.bias_analysis_results
        if analysis.get('success'):
            technical_bias = analysis.get('overall_bias', 'NEUTRAL')
            technical_score = analysis.get('overall_score', 0)

    # Get PCR Analysis bias for NIFTY specifically
    pcr_bias = None
    pcr_score = 0
    if 'overall_option_data' in st.session_state and st.session_state.overall_option_data:
        nifty_data = st.session_state.overall_option_data.get('NIFTY', {})
        if nifty_data.get('success'):
            # Calculate PCR for NIFTY
            total_ce_oi = nifty_data.get('total_ce_oi', 0)
            total_pe_oi = nifty_data.get('total_pe_oi', 0)
            pcr_oi = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 1

            total_ce_change = nifty_data.get('total_ce_change', 0)
            total_pe_change = nifty_data.get('total_pe_change', 0)
            pcr_change_oi = abs(total_pe_change) / abs(total_ce_change) if abs(total_ce_change) > 0 else 1

            # Calculate bias score (weighted: OI=30%, Change OI=70%)
            oi_score = 0
            if pcr_oi > 1.2:
                oi_score = min(50, (pcr_oi - 1) * 50)
            elif pcr_oi < 0.8:
                oi_score = -min(50, (1 - pcr_oi) * 50)

            change_score = 0
            if pcr_change_oi > 1.2:
                change_score = min(50, (pcr_change_oi - 1) * 50)
            elif pcr_change_oi < 0.8:
                change_score = -min(50, (1 - pcr_change_oi) * 50)

            pcr_score = (oi_score * 0.3 + change_score * 0.7)

            # Determine bias
            if pcr_score > 10:
                pcr_bias = "BULLISH"
            elif pcr_score < -10:
                pcr_bias = "BEARISH"
            else:
                pcr_bias = "NEUTRAL"

    # Get ATM Option Chain bias for NIFTY specifically
    atm_bias = None
    atm_score = 0
    if 'NIFTY_atm_zone_bias' in st.session_state:
        atm_data = st.session_state.NIFTY_atm_zone_bias
        if atm_data and atm_data.get('success'):
            atm_bias = atm_data.get('verdict', 'NEUTRAL')
            atm_score = atm_data.get('score', 0)

            # Normalize bias string
            if 'Bullish' in atm_bias:
                atm_bias = 'BULLISH'
            elif 'Bearish' in atm_bias:
                atm_bias = 'BEARISH'
            else:
                atm_bias = 'NEUTRAL'

    # Check if all data is available
    if technical_bias is None or pcr_bias is None or atm_bias is None:
        return None

    # Check for alignment (all bullish or all bearish)
    aligned = False
    direction = None

    if technical_bias == 'BULLISH' and pcr_bias == 'BULLISH' and atm_bias == 'BULLISH':
        aligned = True
        direction = 'BULLISH'
    elif technical_bias == 'BEARISH' and pcr_bias == 'BEARISH' and atm_bias == 'BEARISH':
        aligned = True
        direction = 'BEARISH'

    # Calculate overall confidence based on the strength of each bias
    confidence = 0
    if aligned:
        # Average the absolute scores and normalize to 0-100
        avg_score = (abs(technical_score) + abs(pcr_score) + abs(atm_score)) / 3
        confidence = min(100, avg_score)

    return {
        'aligned': aligned,
        'direction': direction,
        'instrument': 'NIFTY',
        'technical_bias': technical_bias,
        'technical_score': technical_score,
        'pcr_bias': pcr_bias,
        'pcr_score': pcr_score,
        'atm_bias': atm_bias,
        'atm_score': atm_score,
        'confidence': confidence
    }


def _run_bias_analysis():
    """
    Helper function to run bias analysis for NIFTY
    Returns: (success, errors)
    """
    errors = []
    try:
        # Initialize bias_analyzer if not exists
        if 'bias_analyzer' not in st.session_state:
            from bias_analysis import BiasAnalysisPro
            st.session_state.bias_analyzer = BiasAnalysisPro()

        symbol = "^NSEI"  # NIFTY 50
        results = st.session_state.bias_analyzer.analyze_all_bias_indicators(symbol)
        st.session_state.bias_analysis_results = results
        if results.get('success'):
            return True, []
        else:
            errors.append(f"Bias Analysis Pro: {results.get('error', 'Unknown error')}")
            return False, errors
    except Exception as e:
        errors.append(f"Bias Analysis Pro: {str(e)}")
        return False, errors


def _run_option_chain_analysis(NSE_INSTRUMENTS, show_progress=True):
    """
    Helper function to run option chain analysis
    Returns: (success, errors)
    """
    errors = []
    progress_bar = None
    progress_text = None

    try:
        from nse_options_helpers import calculate_and_store_atm_zone_bias_silent
        from nse_options_analyzer import fetch_option_chain_data as fetch_oc

        overall_data = {}
        all_instruments = list(NSE_INSTRUMENTS['indices'].keys())

        # Create progress indicators only if show_progress is True
        if show_progress:
            progress_bar = st.progress(0)
            progress_text = st.empty()

        for idx, instrument in enumerate(all_instruments):
            if show_progress:
                progress_text.text(f"Analyzing {instrument}... ({idx + 1}/{len(all_instruments)})")

            # Fetch basic option chain data
            data = fetch_oc(instrument)
            overall_data[instrument] = data

            # Calculate and store ATM zone bias data silently
            calculate_and_store_atm_zone_bias_silent(instrument, NSE_INSTRUMENTS)

            if show_progress:
                progress_bar.progress((idx + 1) / len(all_instruments))

        st.session_state['overall_option_data'] = overall_data

        if show_progress:
            progress_bar.progress(1.0)
            progress_text.empty()

        return True, []
    except Exception as e:
        # Clean up progress indicators if they were created
        if progress_bar is not None:
            progress_bar.empty()
        if progress_text is not None:
            progress_text.empty()
        errors.append(f"Option Chain Analysis: {str(e)}")
        return False, errors


async def run_all_analyses(NSE_INSTRUMENTS, show_progress=True):
    """
    Runs all analyses and stores results in session state:
    1. Bias Analysis Pro (includes stock data and technical indicators)
    2. Option Chain Analysis (includes PCR and ATM zone analysis)

    Args:
        NSE_INSTRUMENTS: Instrument configuration
        show_progress: Whether to show progress bars (default True, set False for silent auto-refresh)
    """
    success = True
    errors = []

    try:
        # 1. Run Bias Analysis Pro
        spinner_text = "🎯 Running Bias Analysis Pro..."
        if show_progress:
            with st.spinner(spinner_text):
                success_bias, errors_bias = _run_bias_analysis()
                success = success and success_bias
                errors.extend(errors_bias)
        else:
            success_bias, errors_bias = _run_bias_analysis()
            success = success and success_bias
            errors.extend(errors_bias)

        # 2. Run Option Chain Analysis for all instruments (only during trading hours for performance)
        if is_within_trading_hours():
            spinner_text = "📊 Running Option Chain Analysis for all instruments..."
            if show_progress:
                with st.spinner(spinner_text):
                    success_oc, errors_oc = _run_option_chain_analysis(NSE_INSTRUMENTS, show_progress)
                    success = success and success_oc
                    errors.extend(errors_oc)
            else:
                success_oc, errors_oc = _run_option_chain_analysis(NSE_INSTRUMENTS, show_progress)
                success = success and success_oc
                errors.extend(errors_oc)
        else:
            # When market is closed, skip option chain analysis to save API quota
            if show_progress:
                st.info("ℹ️ Option chain analysis skipped (market closed). Using cached data.")

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

    # Show refresh interval based on market session
    market_session = scheduler.get_market_session()
    refresh_interval = scheduler.get_refresh_interval(market_session)

    # Add UI controls row
    col1, col2 = st.columns([3, 1])
    with col1:
        if is_within_trading_hours():
            st.caption(f"🔄 Auto-refreshing every {refresh_interval} seconds during trading hours")
        else:
            st.caption("⏸️ Auto-refresh paused (market closed). Using cached data.")
    with col2:
        # Initialize alignment alerts setting in session state
        if 'enable_alignment_alerts' not in st.session_state:
            st.session_state.enable_alignment_alerts = True

        # Toggle for alignment alerts
        enable_alerts = st.checkbox(
            "🔔 Alignment Alerts",
            value=st.session_state.enable_alignment_alerts,
            help="Send Telegram alerts when Technical Indicators, PCR Analysis, and ATM Option Chain all align (bullish or bearish)"
        )
        st.session_state.enable_alignment_alerts = enable_alerts

    st.markdown("---")

    # ═══════════════════════════════════════════════════════════════════
    # ENHANCED MARKET ANALYSIS SUMMARY CARD
    # ═══════════════════════════════════════════════════════════════════
    # This will be populated after we calculate overall sentiment

    # Initialize auto-refresh timestamp
    if 'sentiment_last_refresh' not in st.session_state:
        st.session_state.sentiment_last_refresh = 0

    # Initialize auto-run flag
    if 'sentiment_auto_run_done' not in st.session_state:
        st.session_state.sentiment_auto_run_done = False

    # Auto-run analyses on first load - FIXED: Now properly uses asyncio.run()
    if not st.session_state.sentiment_auto_run_done and NSE_INSTRUMENTS is not None:
        with st.spinner("🔄 Running initial analyses..."):
            success, errors = asyncio.run(run_all_analyses(NSE_INSTRUMENTS))
            st.session_state.sentiment_auto_run_done = True
            st.session_state.sentiment_last_refresh = time.time()
            if not success:
                for error in errors:
                    st.warning(f"⚠️ {error}")

    # Auto-refresh based on market session (skip when market is closed for performance)
    current_time = time.time()
    time_since_refresh = current_time - st.session_state.sentiment_last_refresh

    # Get recommended refresh interval based on market session
    market_session = scheduler.get_market_session()
    refresh_interval = scheduler.get_refresh_interval(market_session)

    # Only auto-refresh during trading hours to conserve resources
    if time_since_refresh >= refresh_interval and NSE_INSTRUMENTS is not None and is_within_trading_hours():
        # Use show_progress=False for faster background refresh
        success, errors = asyncio.run(run_all_analyses(NSE_INSTRUMENTS, show_progress=False))
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
                success, errors = asyncio.run(run_all_analyses(NSE_INSTRUMENTS))

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
    # ENHANCED MARKET ANALYSIS SUMMARY
    # ═══════════════════════════════════════════════════════════════════

    # Get last updated time
    last_update_time = datetime.fromtimestamp(st.session_state.sentiment_last_refresh)
    last_updated_str = last_update_time.strftime('%Y-%m-%d %H:%M:%S')

    # Get sentiment data
    sentiment = result['overall_sentiment']
    score = result['overall_score']
    data_points = result['source_count']
    bullish_count = result['bullish_sources']
    bearish_count = result['bearish_sources']
    neutral_count = result['neutral_sources']

    # Determine sentiment icon and color
    if sentiment == 'BULLISH':
        sentiment_icon = '📈'
        sentiment_color = '#00ff88'
    elif sentiment == 'BEARISH':
        sentiment_icon = '📉'
        sentiment_color = '#ff4444'
    else:
        sentiment_icon = '⚖️'
        sentiment_color = '#ffa500'

    # Enhanced Summary Card
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, #1e1e1e 0%, #2d2d2d 100%);
                padding: 25px; border-radius: 15px; margin-bottom: 20px;
                border: 1px solid #3d3d3d;'>
        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;'>
            <h3 style='margin: 0; color: #ffffff; font-size: 24px;'>📊 Enhanced Market Analysis</h3>
            <span style='color: #888; font-size: 14px;'>📅 Last Updated: {last_updated_str}</span>
        </div>
        <div style='display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px;'>
            <div style='background: {sentiment_color}; padding: 20px; border-radius: 10px; text-align: center;'>
                <div style='font-size: 32px; margin-bottom: 5px;'>{sentiment_icon}</div>
                <div style='font-size: 20px; font-weight: bold; color: white; margin-bottom: 5px;'>{sentiment}</div>
                <div style='font-size: 12px; color: rgba(255,255,255,0.8);'>Overall Sentiment</div>
            </div>
            <div style='background: #2d2d2d; padding: 20px; border-radius: 10px; text-align: center;
                        border-left: 4px solid {sentiment_color};'>
                <div style='font-size: 32px; color: {sentiment_color}; font-weight: bold; margin-bottom: 5px;'>{score:+.1f}</div>
                <div style='font-size: 12px; color: #888;'>Average Score</div>
            </div>
            <div style='background: #2d2d2d; padding: 20px; border-radius: 10px; text-align: center;
                        border-left: 4px solid #6495ED;'>
                <div style='font-size: 32px; color: #6495ED; font-weight: bold; margin-bottom: 5px;'>{data_points}</div>
                <div style='font-size: 12px; color: #888;'>Data Points</div>
            </div>
            <div style='background: #2d2d2d; padding: 20px; border-radius: 10px; text-align: center;'>
                <div style='font-size: 16px; color: #ffffff; font-weight: bold; margin-bottom: 5px;'>
                    🟢{bullish_count} | 🔴{bearish_count} | 🟡{neutral_count}
                </div>
                <div style='font-size: 12px; color: #888;'>Bullish | Bearish | Neutral</div>
            </div>
        </div>
        <div style='background: #252525; padding: 15px; border-radius: 10px;'>
            <div style='color: #888; font-size: 14px; margin-bottom: 10px; font-weight: bold;'>📊 Summary</div>
            <div style='display: grid; grid-template-columns: repeat(6, 1fr); gap: 10px;'>
                <div style='text-align: center; padding: 10px; background: #1e1e1e; border-radius: 8px;'>
                    <div style='font-size: 24px; margin-bottom: 5px;'>⚡</div>
                    <div style='font-size: 11px; color: #888;'>India VIX</div>
                </div>
                <div style='text-align: center; padding: 10px; background: #1e1e1e; border-radius: 8px;'>
                    <div style='font-size: 24px; margin-bottom: 5px;'>🏢</div>
                    <div style='font-size: 11px; color: #888;'>Sector Rotation</div>
                </div>
                <div style='text-align: center; padding: 10px; background: #1e1e1e; border-radius: 8px;'>
                    <div style='font-size: 24px; margin-bottom: 5px;'>🌍</div>
                    <div style='font-size: 11px; color: #888;'>Global Markets</div>
                </div>
                <div style='text-align: center; padding: 10px; background: #1e1e1e; border-radius: 8px;'>
                    <div style='font-size: 24px; margin-bottom: 5px;'>💰</div>
                    <div style='font-size: 11px; color: #888;'>Intermarket</div>
                </div>
                <div style='text-align: center; padding: 10px; background: #1e1e1e; border-radius: 8px;'>
                    <div style='font-size: 24px; margin-bottom: 5px;'>🎯</div>
                    <div style='font-size: 11px; color: #888;'>Gamma Squeeze</div>
                </div>
                <div style='text-align: center; padding: 10px; background: #1e1e1e; border-radius: 8px;'>
                    <div style='font-size: 24px; margin-bottom: 5px;'>⏰</div>
                    <div style='font-size: 11px; color: #888;'>Intraday Timing</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ═══════════════════════════════════════════════════════════════════
    # BIAS ALIGNMENT CHECK & TELEGRAM ALERT
    # ═══════════════════════════════════════════════════════════════════

    # Initialize alignment tracking in session state
    if 'last_alignment_alert' not in st.session_state:
        st.session_state.last_alignment_alert = None
    if 'last_alignment_direction' not in st.session_state:
        st.session_state.last_alignment_direction = None

    # Check for bias alignment
    alignment_status = check_bias_alignment()

    if alignment_status and alignment_status['aligned']:
        # Show alignment indicator in UI
        direction = alignment_status['direction']
        confidence = alignment_status['confidence']

        if direction == 'BULLISH':
            alert_color = '#00ff88'
            alert_icon = '🚀'
            alert_emoji = '🟢'
        else:  # BEARISH
            alert_color = '#ff4444'
            alert_icon = '⚠️'
            alert_emoji = '🔴'

        st.markdown(f"""
        <div style='background: linear-gradient(135deg, {alert_color}22 0%, {alert_color}11 100%);
                    padding: 20px; border-radius: 10px; margin-bottom: 20px;
                    border: 2px solid {alert_color};'>
            <div style='text-align: center;'>
                <div style='font-size: 32px; margin-bottom: 10px;'>{alert_icon}</div>
                <h3 style='margin: 0; color: {alert_color}; font-size: 24px;'>
                    {alert_emoji} ALL 3 INDICATORS ALIGNED {alert_emoji}
                </h3>
                <p style='margin: 10px 0 0 0; color: #888; font-size: 16px;'>
                    {direction} - Confidence: {confidence:.1f}%
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Send Telegram alert if:
        # 1. Alignment alerts are enabled, AND
        # 2. Never sent before OR direction has changed since last alert
        current_alert_key = f"{direction}_{int(confidence)}"
        should_send_alert = (
            st.session_state.get('enable_alignment_alerts', True) and
            (st.session_state.last_alignment_alert != current_alert_key or
             st.session_state.last_alignment_direction != direction)
        )

        if should_send_alert:
            try:
                from telegram_alerts import TelegramBot
                bot = TelegramBot()
                if bot.enabled:
                    success = bot.send_bias_alignment_alert(alignment_status)
                    if success:
                        st.session_state.last_alignment_alert = current_alert_key
                        st.session_state.last_alignment_direction = direction
                        st.success(f"✅ Telegram alert sent for {direction} alignment!")
            except Exception as e:
                st.warning(f"⚠️ Could not send Telegram alert: {str(e)}")

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
    # 3.5 NIFTY ADVANCED METRICS (NEW SECTION)
    # ─────────────────────────────────────────────────────────────────
    if 'NIFTY Advanced Metrics' in sources:
        source_data = sources['NIFTY Advanced Metrics']
        with st.expander("**🌐 NIFTY Advanced Metrics (ATM Zone & Market Analysis)**", expanded=True):
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

            # Get metrics
            metrics = source_data.get('metrics', {})

            # ═══════════════════════════════════════════════════════════════════
            # NIFTY ATM ZONE SUMMARY
            # ═══════════════════════════════════════════════════════════════════
            st.markdown("#### 📍 NIFTY ATM Zone Summary")

            atm_strike = metrics.get('ATM Strike', 'N/A')
            st.markdown(f"**Strike: {atm_strike}**")

            col1, col2, col3, col4 = st.columns(4)

            # 1. Synthetic Future Bias
            with col1:
                synthetic_bias = metrics.get('Synthetic Future Bias', 'Neutral')
                synthetic_future = metrics.get('synthetic_future', 0)
                synthetic_diff = metrics.get('synthetic_diff', 0)

                if 'BULLISH' in str(synthetic_bias).upper():
                    st.markdown(f"""
                    <div style='padding: 15px; background: #1e1e1e; border-radius: 10px; border-left: 4px solid #00ff88;'>
                        <p style='margin: 0; color: #888; font-size: 12px;'>Synthetic Future Bias</p>
                        <h4 style='margin: 5px 0; color: #00ff88;'>🟢 Bullish</h4>
                        <p style='margin: 0; color: #ccc; font-size: 14px;'>Synth: {synthetic_future:.2f} | Diff: {synthetic_diff:+.2f}</p>
                    </div>
                    """, unsafe_allow_html=True)
                elif 'BEARISH' in str(synthetic_bias).upper():
                    st.markdown(f"""
                    <div style='padding: 15px; background: #1e1e1e; border-radius: 10px; border-left: 4px solid #ff4444;'>
                        <p style='margin: 0; color: #888; font-size: 12px;'>Synthetic Future Bias</p>
                        <h4 style='margin: 5px 0; color: #ff4444;'>🔴 Bearish</h4>
                        <p style='margin: 0; color: #ccc; font-size: 14px;'>Synth: {synthetic_future:.2f} | Diff: {synthetic_diff:+.2f}</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style='padding: 15px; background: #1e1e1e; border-radius: 10px; border-left: 4px solid #ffa500;'>
                        <p style='margin: 0; color: #888; font-size: 12px;'>Synthetic Future Bias</p>
                        <h4 style='margin: 5px 0; color: #ffa500;'>🟡 Neutral</h4>
                        <p style='margin: 0; color: #ccc; font-size: 14px;'>Synth: {synthetic_future:.2f} | Diff: {synthetic_diff:+.2f}</p>
                    </div>
                    """, unsafe_allow_html=True)

            # 2. ATM Buildup Pattern
            with col2:
                atm_buildup = metrics.get('ATM Buildup Pattern', 'Neutral')

                if 'SHORT BUILDUP' in str(atm_buildup).upper() or 'PUT WRITING' in str(atm_buildup).upper():
                    st.markdown(f"""
                    <div style='padding: 15px; background: #1e1e1e; border-radius: 10px; border-left: 4px solid #00ff88;'>
                        <p style='margin: 0; color: #888; font-size: 12px;'>ATM Buildup Pattern</p>
                        <h4 style='margin: 5px 0; color: #00ff88;'>🟢</h4>
                        <p style='margin: 0; color: #ccc; font-size: 14px;'>{atm_buildup}</p>
                    </div>
                    """, unsafe_allow_html=True)
                elif 'LONG BUILDUP' in str(atm_buildup).upper() or 'CALL WRITING' in str(atm_buildup).upper():
                    st.markdown(f"""
                    <div style='padding: 15px; background: #1e1e1e; border-radius: 10px; border-left: 4px solid #ff4444;'>
                        <p style='margin: 0; color: #888; font-size: 12px;'>ATM Buildup Pattern</p>
                        <h4 style='margin: 5px 0; color: #ff4444;'>🔴</h4>
                        <p style='margin: 0; color: #ccc; font-size: 14px;'>{atm_buildup}</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style='padding: 15px; background: #1e1e1e; border-radius: 10px; border-left: 4px solid #ffa500;'>
                        <p style='margin: 0; color: #888; font-size: 12px;'>ATM Buildup Pattern</p>
                        <h4 style='margin: 5px 0; color: #ffa500;'>🟡</h4>
                        <p style='margin: 0; color: #ccc; font-size: 14px;'>{atm_buildup}</p>
                    </div>
                    """, unsafe_allow_html=True)

            # 3. ATM Vega Bias
            with col3:
                atm_vega_bias = metrics.get('ATM Vega Bias', 'Neutral')
                atm_vega_exposure = metrics.get('atm_vega_exposure', 0)

                if 'BULLISH' in str(atm_vega_bias).upper():
                    st.markdown(f"""
                    <div style='padding: 15px; background: #1e1e1e; border-radius: 10px; border-left: 4px solid #00ff88;'>
                        <p style='margin: 0; color: #888; font-size: 12px;'>ATM Vega Bias</p>
                        <h4 style='margin: 5px 0; color: #00ff88;'>🟢 Bullish</h4>
                        <p style='margin: 0; color: #ccc; font-size: 14px;'>High Put Vega | Exp: {atm_vega_exposure:,.2f}</p>
                    </div>
                    """, unsafe_allow_html=True)
                elif 'BEARISH' in str(atm_vega_bias).upper():
                    st.markdown(f"""
                    <div style='padding: 15px; background: #1e1e1e; border-radius: 10px; border-left: 4px solid #ff4444;'>
                        <p style='margin: 0; color: #888; font-size: 12px;'>ATM Vega Bias</p>
                        <h4 style='margin: 5px 0; color: #ff4444;'>🔴 Bearish</h4>
                        <p style='margin: 0; color: #ccc; font-size: 14px;'>High Call Vega | Exp: {atm_vega_exposure:,.2f}</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style='padding: 15px; background: #1e1e1e; border-radius: 10px; border-left: 4px solid #ffa500;'>
                        <p style='margin: 0; color: #888; font-size: 12px;'>ATM Vega Bias</p>
                        <h4 style='margin: 5px 0; color: #ffa500;'>🟡 Neutral</h4>
                        <p style='margin: 0; color: #ccc; font-size: 14px;'>Exp: {atm_vega_exposure:,.2f}</p>
                    </div>
                    """, unsafe_allow_html=True)

            # 4. Distance from Max Pain
            with col4:
                distance_from_max_pain = metrics.get('distance_from_max_pain_value', 0)
                max_pain_strike = metrics.get('Max Pain Strike', 'N/A')

                if distance_from_max_pain > 50:
                    st.markdown(f"""
                    <div style='padding: 15px; background: #1e1e1e; border-radius: 10px; border-left: 4px solid #ff4444;'>
                        <p style='margin: 0; color: #888; font-size: 12px;'>Distance from Max Pain</p>
                        <h4 style='margin: 5px 0; color: #ff4444;'>🔴 {distance_from_max_pain:+.2f}</h4>
                        <p style='margin: 0; color: #ccc; font-size: 14px;'>Max Pain: {max_pain_strike}</p>
                    </div>
                    """, unsafe_allow_html=True)
                elif distance_from_max_pain < -50:
                    st.markdown(f"""
                    <div style='padding: 15px; background: #1e1e1e; border-radius: 10px; border-left: 4px solid #00ff88;'>
                        <p style='margin: 0; color: #888; font-size: 12px;'>Distance from Max Pain</p>
                        <h4 style='margin: 5px 0; color: #00ff88;'>🟢 {distance_from_max_pain:+.2f}</h4>
                        <p style='margin: 0; color: #ccc; font-size: 14px;'>Max Pain: {max_pain_strike}</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style='padding: 15px; background: #1e1e1e; border-radius: 10px; border-left: 4px solid #ffa500;'>
                        <p style='margin: 0; color: #888; font-size: 12px;'>Distance from Max Pain</p>
                        <h4 style='margin: 5px 0; color: #ffa500;'>🟡 {distance_from_max_pain:+.2f}</h4>
                        <p style='margin: 0; color: #ccc; font-size: 14px;'>Max Pain: {max_pain_strike}</p>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("---")

            # ═══════════════════════════════════════════════════════════════════
            # NIFTY OVERALL MARKET ANALYSIS
            # ═══════════════════════════════════════════════════════════════════
            st.markdown("#### 🌐 NIFTY Overall Market Analysis")

            col1, col2, col3, col4 = st.columns(4)

            # 1. Max Pain Strike
            with col1:
                max_pain_strike = metrics.get('Max Pain Strike', 'N/A')
                distance_from_max_pain = metrics.get('distance_from_max_pain_value', 0)

                if distance_from_max_pain > 0:
                    color = '#00ff88'
                    icon = '🟢'
                else:
                    color = '#ff4444'
                    icon = '🔴'

                st.markdown(f"""
                <div style='padding: 15px; background: #1e1e1e; border-radius: 10px; border-left: 4px solid {color};'>
                    <p style='margin: 0; color: #888; font-size: 12px;'>Max Pain Strike</p>
                    <h4 style='margin: 5px 0; color: {color};'>{max_pain_strike}</h4>
                    <p style='margin: 0; color: #ccc; font-size: 14px;'>{icon} Distance: {distance_from_max_pain:+.2f}</p>
                </div>
                """, unsafe_allow_html=True)

            # 2. Call Resistance (OI)
            with col2:
                call_resistance = metrics.get('Call Resistance', 'N/A')
                call_resistance_distance = metrics.get('call_resistance_distance', 0)

                st.markdown(f"""
                <div style='padding: 15px; background: #1e1e1e; border-radius: 10px; border-left: 4px solid #6495ED;'>
                    <p style='margin: 0; color: #888; font-size: 12px;'>Call Resistance (OI)</p>
                    <h4 style='margin: 5px 0; color: #6495ED;'>{call_resistance}</h4>
                    <p style='margin: 0; color: #ccc; font-size: 14px;'>📈 +{call_resistance_distance:.2f} points away</p>
                </div>
                """, unsafe_allow_html=True)

            # 3. Put Support (OI)
            with col3:
                put_support = metrics.get('Put Support', 'N/A')
                put_support_distance = metrics.get('put_support_distance', 0)

                st.markdown(f"""
                <div style='padding: 15px; background: #1e1e1e; border-radius: 10px; border-left: 4px solid #6495ED;'>
                    <p style='margin: 0; color: #888; font-size: 12px;'>Put Support (OI)</p>
                    <h4 style='margin: 5px 0; color: #6495ED;'>{put_support}</h4>
                    <p style='margin: 0; color: #ccc; font-size: 14px;'>📉 -{put_support_distance:.2f} points away</p>
                </div>
                """, unsafe_allow_html=True)

            # 4. Total Vega Bias
            with col4:
                total_vega_bias = metrics.get('Total Vega Bias', 'Neutral')

                if 'BULLISH' in str(total_vega_bias).upper():
                    st.markdown(f"""
                    <div style='padding: 15px; background: #1e1e1e; border-radius: 10px; border-left: 4px solid #00ff88;'>
                        <p style='margin: 0; color: #888; font-size: 12px;'>Total Vega Bias</p>
                        <h4 style='margin: 5px 0; color: #00ff88;'>🟢 Bullish</h4>
                        <p style='margin: 0; color: #ccc; font-size: 14px;'>Put Heavy</p>
                    </div>
                    """, unsafe_allow_html=True)
                elif 'BEARISH' in str(total_vega_bias).upper():
                    st.markdown(f"""
                    <div style='padding: 15px; background: #1e1e1e; border-radius: 10px; border-left: 4px solid #ff4444;'>
                        <p style='margin: 0; color: #888; font-size: 12px;'>Total Vega Bias</p>
                        <h4 style='margin: 5px 0; color: #ff4444;'>🔴 Bearish</h4>
                        <p style='margin: 0; color: #ccc; font-size: 14px;'>Call Heavy</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style='padding: 15px; background: #1e1e1e; border-radius: 10px; border-left: 4px solid #ffa500;'>
                        <p style='margin: 0; color: #888; font-size: 12px;'>Total Vega Bias</p>
                        <h4 style='margin: 5px 0; color: #ffa500;'>🟡 Neutral</h4>
                        <p style='margin: 0; color: #ccc; font-size: 14px;'>Balanced</p>
                    </div>
                    """, unsafe_allow_html=True)

            # Display detailed breakdown
            st.markdown("---")
            st.markdown("**Sentiment Breakdown:**")
            details = source_data.get('details', [])
            for detail in details:
                st.markdown(f"- {detail}")

    # ─────────────────────────────────────────────────────────────────
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

        # ═══════════════════════════════════════════════════════════════════
        # COMPREHENSIVE OPTION CHAIN METRICS
        # ═══════════════════════════════════════════════════════════════════
        if 'Option Chain Analysis' in result.get('sources', {}):
            st.markdown("---")
            st.markdown("### 🌐 Comprehensive Option Chain Analysis")
            st.caption("Advanced metrics: Max Pain, Synthetic Future, Vega Bias, Buildup Patterns, and more")

            # Check if comprehensive metrics are available in session state
            comprehensive_metrics = []
            instruments_to_check = ['NIFTY', 'BANKNIFTY', 'SENSEX', 'FINNIFTY', 'MIDCPNIFTY']

            for instrument in instruments_to_check:
                # Check if comprehensive metrics are stored
                metrics_key = f'{instrument}_comprehensive_metrics'
                if metrics_key in st.session_state:
                    metrics = st.session_state[metrics_key]
                    comprehensive_metrics.append(metrics)

            if comprehensive_metrics:
                st.markdown("#### 📊 Comprehensive Metrics Summary")
                comp_df = pd.DataFrame(comprehensive_metrics)
                st.dataframe(comp_df, use_container_width=True, hide_index=True)

                # Expandable section with detailed explanations
                with st.expander("📖 Understanding Comprehensive Metrics"):
                    st.markdown("""
                    ### Advanced Option Chain Metrics Explained

                    **ATM-Specific Metrics:**

                    1. **Synthetic Future Bias**
                       - Calculated as: Strike + CE Premium - PE Premium
                       - Compares synthetic future price vs spot price
                       - Bullish if synthetic > spot, Bearish if synthetic < spot
                       - Indicates market expectations embedded in options pricing

                    2. **ATM Buildup Pattern**
                       - Analyzes OI changes at ATM strike
                       - Long Buildup: Rising OI + Rising Prices (Bearish)
                       - Short Buildup: Rising OI + Falling Prices (Bullish)
                       - Call Writing: CE OI rising, PE OI falling (Bearish)
                       - Put Writing: PE OI rising, CE OI falling (Bullish)

                    3. **ATM Vega Bias**
                       - Measures volatility exposure at ATM
                       - Higher Put Vega → Bullish (expecting upside volatility)
                       - Higher Call Vega → Bearish (expecting downside volatility)

                    4. **Distance from Max Pain**
                       - Shows how far current price is from Max Pain strike
                       - Price tends to gravitate toward Max Pain near expiry
                       - Positive distance: Above Max Pain (potential downward pull)
                       - Negative distance: Below Max Pain (potential upward pull)

                    **Overall Market Metrics:**

                    5. **Max Pain Strike**
                       - Strike where option writers lose least money
                       - Calculated by summing all option pain values
                       - Market tends to drift toward this level

                    6. **Call Resistance (OI)**
                       - Strike with highest Call OI above spot
                       - Major resistance level from option positioning

                    7. **Put Support (OI)**
                       - Strike with highest Put OI below spot
                       - Major support level from option positioning

                    8. **Total Vega Bias**
                       - Aggregate vega exposure across all strikes
                       - Indicates overall market volatility expectations

                    9. **Unusual Activity Alerts**
                       - Strikes with abnormally high volume/OI ratio
                       - May indicate smart money positioning

                    10. **Overall Buildup Pattern**
                        - Combined analysis of ITM, ATM, and OTM activity
                        - Identifies protective strategies and directional bets
                    """)
            else:
                st.info("ℹ️ Comprehensive option chain metrics will be displayed here. Visit individual instrument tabs in the Option Chain Analysis section to generate these metrics.")

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
    time_until_refresh = max(0, refresh_interval - time_since_refresh)

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
                success, errors = asyncio.run(run_all_analyses(NSE_INSTRUMENTS))
                st.session_state.sentiment_last_refresh = time.time()

                if success:
                    st.balloons()
                    st.success("🎉 All analyses completed successfully! Refreshing results...")
                    st.rerun()
                else:
                    st.error("❌ Some analyses failed:")
                    for error in errors:
                        st.error(f"  - {error}")

    # Auto-refresh handled by the refresh logic at the top of this function
    # No need for additional sleep/rerun here as it causes duplicate rendering


# Export functions for external use
__all__ = [
    'calculate_overall_sentiment',
    'run_all_analyses',
    'render_overall_market_sentiment'
]