"""
Overall Market Sentiment Module

This module aggregates bias data from all analysis tabs:
- Smart Trading Dashboard (3-tier adaptive bias)
- Bias Analysis Pro (15+ indicator comprehensive scoring)
- Option Chain Analysis (PCR and option chain bias)

Each bias source is given equal weight to calculate the overall market sentiment.
"""

from datetime import datetime
import pandas as pd
import numpy as np


class OverallMarketSentiment:
    """
    Aggregates bias from all analysis modules to provide an overall market sentiment.
    """

    def __init__(self):
        self.sentiment_sources = []

    def convert_bias_to_score(self, bias, score=None):
        """
        Convert bias string to numerical score (-100 to +100).

        Args:
            bias (str): Bias string (BULLISH, BEARISH, NEUTRAL)
            score (float, optional): Existing score if available

        Returns:
            float: Numerical score (-100 to +100)
        """
        if score is not None:
            return score

        bias_upper = str(bias).upper()

        if 'BULLISH' in bias_upper or 'BULL' in bias_upper:
            return 100
        elif 'BEARISH' in bias_upper or 'BEAR' in bias_upper:
            return -100
        else:
            return 0

    def normalize_percentage_to_score(self, bullish_pct, bearish_pct):
        """
        Convert bullish/bearish percentages to a score (-100 to +100).

        Args:
            bullish_pct (float): Bullish percentage (0-100)
            bearish_pct (float): Bearish percentage (0-100)

        Returns:
            float: Score (-100 to +100)
        """
        # Net bias = bullish% - bearish%
        # Normalize to -100 to +100 range
        net_bias = bullish_pct - bearish_pct
        return net_bias

    def aggregate_smart_trading_dashboard_bias(self, dashboard_results):
        """
        Extract bias score from Smart Trading Dashboard results.

        Returns:
            dict: {'source': str, 'bias': str, 'score': float, 'confidence': float, 'data': dict}
        """
        if not dashboard_results:
            return None

        try:
            bias_data = dashboard_results.get('bias_data', {})

            # Get bullish and bearish percentages
            bullish_pct = bias_data.get('bullish_bias_pct', 50)
            bearish_pct = bias_data.get('bearish_bias_pct', 50)

            # Calculate score
            score = self.normalize_percentage_to_score(bullish_pct, bearish_pct)

            # Market bias
            market_bias = dashboard_results.get('market_bias', 'NEUTRAL')

            # Confidence based on divergence and reversal mode
            divergence = bias_data.get('divergence_detected', False)
            confidence = 100 - (20 if divergence else 0)

            return {
                'source': 'Smart Trading Dashboard',
                'bias': market_bias,
                'score': score,
                'confidence': confidence,
                'data': {
                    'bullish_pct': bullish_pct,
                    'bearish_pct': bearish_pct,
                    'condition': dashboard_results.get('market_condition', 'N/A'),
                    'reversal_mode': bias_data.get('reversal_mode', False),
                    'divergence_detected': divergence
                }
            }
        except Exception as e:
            print(f"Error aggregating Smart Trading Dashboard bias: {e}")
            return None

    def aggregate_bias_analysis_pro_bias(self, bias_results):
        """
        Extract bias score from Bias Analysis Pro results.

        Returns:
            dict: {'source': str, 'bias': str, 'score': float, 'confidence': float, 'data': dict}
        """
        if not bias_results or not bias_results.get('success'):
            return None

        try:
            overall_bias = bias_results.get('overall_bias', 'NEUTRAL')
            overall_score = bias_results.get('overall_score', 0)
            confidence = bias_results.get('overall_confidence', 0)

            return {
                'source': 'Bias Analysis Pro',
                'bias': overall_bias,
                'score': overall_score,
                'confidence': confidence,
                'data': {
                    'total_indicators': bias_results.get('total_indicators', 0),
                    'bullish_count': bias_results.get('bullish_count', 0),
                    'bearish_count': bias_results.get('bearish_count', 0),
                    'neutral_count': bias_results.get('neutral_count', 0)
                }
            }
        except Exception as e:
            print(f"Error aggregating Bias Analysis Pro bias: {e}")
            return None

    def aggregate_option_chain_bias(self, option_chain_results):
        """
        Extract bias score from Option Chain Analysis results.

        Returns:
            dict: {'source': str, 'bias': str, 'score': float, 'confidence': float, 'data': dict}
        """
        if not option_chain_results:
            return None

        try:
            # Option chain analysis returns bias based on PCR and volume analysis
            bias = option_chain_results.get('bias', 'NEUTRAL')
            pcr_ratio = option_chain_results.get('pcr_ratio', 1.0)

            # Convert PCR to score
            # PCR > 1.2 = Bullish (more puts than calls)
            # PCR < 0.8 = Bearish (more calls than puts)
            if pcr_ratio > 1.2:
                score = min((pcr_ratio - 1.0) * 100, 100)
                bias = 'BULLISH'
            elif pcr_ratio < 0.8:
                score = max((pcr_ratio - 1.0) * 100, -100)
                bias = 'BEARISH'
            else:
                score = (pcr_ratio - 1.0) * 50
                bias = 'NEUTRAL'

            # Confidence based on PCR strength
            confidence = min(abs(pcr_ratio - 1.0) * 100, 100)

            return {
                'source': 'Option Chain Analysis',
                'bias': bias,
                'score': score,
                'confidence': confidence,
                'data': {
                    'pcr_ratio': pcr_ratio,
                    'call_oi': option_chain_results.get('call_oi', 0),
                    'put_oi': option_chain_results.get('put_oi', 0)
                }
            }
        except Exception as e:
            print(f"Error aggregating Option Chain bias: {e}")
            return None

    def calculate_overall_sentiment(self, smart_dashboard_results=None,
                                    bias_analysis_results=None,
                                    option_chain_results=None):
        """
        Calculate overall market sentiment from all available bias sources.

        Args:
            smart_dashboard_results: Results from Smart Trading Dashboard
            bias_analysis_results: Results from Bias Analysis Pro
            option_chain_results: Results from Option Chain Analysis

        Returns:
            dict: Overall sentiment analysis with aggregated data
        """
        sentiment_sources = []

        # Aggregate Smart Trading Dashboard
        if smart_dashboard_results:
            smart_bias = self.aggregate_smart_trading_dashboard_bias(smart_dashboard_results)
            if smart_bias:
                sentiment_sources.append(smart_bias)

        # Aggregate Bias Analysis Pro
        if bias_analysis_results:
            bias_pro = self.aggregate_bias_analysis_pro_bias(bias_analysis_results)
            if bias_pro:
                sentiment_sources.append(bias_pro)

        # Aggregate Option Chain Analysis
        if option_chain_results:
            option_bias = self.aggregate_option_chain_bias(option_chain_results)
            if option_bias:
                sentiment_sources.append(option_bias)

        # If no sources available
        if not sentiment_sources:
            return {
                'success': False,
                'error': 'No bias data available from any source',
                'overall_sentiment': 'NEUTRAL',
                'overall_score': 0,
                'confidence': 0,
                'sources_count': 0,
                'sources': [],
                'timestamp': datetime.now()
            }

        # Calculate equal-weighted average
        total_score = sum(source['score'] for source in sentiment_sources)
        avg_score = total_score / len(sentiment_sources)

        # Calculate weighted confidence (based on individual confidences)
        avg_confidence = sum(source['confidence'] for source in sentiment_sources) / len(sentiment_sources)

        # Determine overall sentiment
        if avg_score > 20:
            overall_sentiment = 'BULLISH'
        elif avg_score < -20:
            overall_sentiment = 'BEARISH'
        else:
            overall_sentiment = 'NEUTRAL'

        # Count agreement
        bullish_count = sum(1 for s in sentiment_sources if 'BULL' in s['bias'].upper())
        bearish_count = sum(1 for s in sentiment_sources if 'BEAR' in s['bias'].upper())
        neutral_count = len(sentiment_sources) - bullish_count - bearish_count

        # Agreement percentage
        max_agreement = max(bullish_count, bearish_count, neutral_count)
        agreement_pct = (max_agreement / len(sentiment_sources)) * 100

        return {
            'success': True,
            'overall_sentiment': overall_sentiment,
            'overall_score': round(avg_score, 2),
            'confidence': round(avg_confidence, 2),
            'agreement_pct': round(agreement_pct, 2),
            'sources_count': len(sentiment_sources),
            'sources': sentiment_sources,
            'bullish_sources': bullish_count,
            'bearish_sources': bearish_count,
            'neutral_sources': neutral_count,
            'timestamp': datetime.now()
        }

    def get_sentiment_recommendation(self, sentiment_data):
        """
        Generate trading recommendation based on overall sentiment.

        Args:
            sentiment_data: Overall sentiment data from calculate_overall_sentiment

        Returns:
            dict: Trading recommendation
        """
        if not sentiment_data.get('success'):
            return {
                'recommendation': 'NO SIGNAL',
                'strategy': 'Wait for bias data to be available',
                'confidence_level': 'NONE'
            }

        sentiment = sentiment_data['overall_sentiment']
        score = sentiment_data['overall_score']
        confidence = sentiment_data['confidence']
        agreement = sentiment_data['agreement_pct']

        # Confidence level based on score strength and agreement
        if abs(score) > 60 and agreement >= 75:
            confidence_level = 'VERY HIGH'
        elif abs(score) > 40 and agreement >= 60:
            confidence_level = 'HIGH'
        elif abs(score) > 20 and agreement >= 50:
            confidence_level = 'MODERATE'
        else:
            confidence_level = 'LOW'

        # Generate recommendation
        if sentiment == 'BULLISH':
            if confidence_level in ['VERY HIGH', 'HIGH']:
                recommendation = 'STRONG BUY'
                strategy = 'Look for LONG entries on dips. Wait for support level touch.'
            else:
                recommendation = 'BUY (with caution)'
                strategy = 'Consider LONG entries but use tight stop losses.'

        elif sentiment == 'BEARISH':
            if confidence_level in ['VERY HIGH', 'HIGH']:
                recommendation = 'STRONG SELL'
                strategy = 'Look for SHORT entries on rallies. Wait for resistance level touch.'
            else:
                recommendation = 'SELL (with caution)'
                strategy = 'Consider SHORT entries but use tight stop losses.'

        else:
            recommendation = 'NEUTRAL / NO CLEAR SIGNAL'
            strategy = 'Stay out or use range trading. Wait for clearer bias formation.'

        return {
            'recommendation': recommendation,
            'strategy': strategy,
            'confidence_level': confidence_level,
            'risk_level': 'LOW' if confidence_level in ['VERY HIGH', 'HIGH'] else 'HIGH'
        }
