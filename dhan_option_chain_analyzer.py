"""
Dhan API Option Chain Analysis Module
Fetches option chain data from Dhan API and calculates PCR ratios and overall bias
"""

import pandas as pd
from datetime import datetime
from pytz import timezone
from dhan_data_fetcher import DhanDataFetcher
from config import get_current_time_ist

class DhanOptionChainAnalyzer:
    """Analyzes Dhan option chain data for multiple instruments"""

    def __init__(self):
        self.fetcher = DhanDataFetcher()
        self.instruments = {
            'NIFTY': '13',
            'BANKNIFTY': '25',
            'FINNIFTY': '27',
        }

    def fetch_option_chain(self, symbol):
        """Fetch option chain data from Dhan API"""
        try:
            # Get expiry list first
            expiry_result = self.fetcher.fetch_expiry_list(symbol)

            if not expiry_result.get('success'):
                return {
                    'success': False,
                    'error': f'Failed to fetch expiry list: {expiry_result.get("error")}'
                }

            expiry_dates = expiry_result.get('expiry_dates', [])
            if not expiry_dates:
                return {
                    'success': False,
                    'error': 'No expiry dates available'
                }

            current_expiry = expiry_dates[0]

            # Fetch option chain for current expiry
            oc_result = self.fetcher.fetch_option_chain(symbol, current_expiry)

            if not oc_result.get('success'):
                return {
                    'success': False,
                    'error': f'Failed to fetch option chain: {oc_result.get("error")}'
                }

            # Get spot price from OHLC
            ohlc_result = self.fetcher.fetch_ohlc_data([symbol])
            spot_price = 0

            if symbol in ohlc_result and ohlc_result[symbol].get('success'):
                spot_price = ohlc_result[symbol].get('last_price', 0)

            # Parse option chain data
            option_chain_data = oc_result.get('data', {})

            return {
                'success': True,
                'symbol': symbol,
                'spot_price': spot_price,
                'records': option_chain_data,
                'expiry_dates': expiry_dates,
                'current_expiry': current_expiry
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def calculate_pcr(self, symbol):
        """Calculate Put-Call Ratio for a symbol using Dhan API"""
        oc_data = self.fetch_option_chain(symbol)

        if not oc_data['success']:
            return oc_data

        try:
            records = oc_data['records']
            current_expiry = oc_data['current_expiry']
            spot_price = oc_data['spot_price']

            # Dhan API returns option chain in a different format
            # Parse the data structure from Dhan API

            total_ce_oi = 0
            total_pe_oi = 0
            total_ce_change = 0
            total_pe_change = 0
            total_ce_volume = 0
            total_pe_volume = 0

            # Dhan option chain structure: list of strikes with CE and PE data
            if isinstance(records, list):
                for record in records:
                    # CE data
                    if 'call_options' in record:
                        ce_data = record.get('call_options', {})
                        total_ce_oi += ce_data.get('oi', 0)
                        total_ce_change += ce_data.get('oi_change', 0)
                        total_ce_volume += ce_data.get('volume', 0)

                    # PE data
                    if 'put_options' in record:
                        pe_data = record.get('put_options', {})
                        total_pe_oi += pe_data.get('oi', 0)
                        total_pe_change += pe_data.get('oi_change', 0)
                        total_pe_volume += pe_data.get('volume', 0)

            # If records is a dict with different structure
            elif isinstance(records, dict):
                # Handle different possible structures
                for strike_key, strike_data in records.items():
                    if isinstance(strike_data, dict):
                        # Check for CE data
                        if 'CE' in strike_data:
                            ce = strike_data['CE']
                            total_ce_oi += ce.get('openInterest', ce.get('oi', 0))
                            total_ce_change += ce.get('changeinOpenInterest', ce.get('oi_change', 0))
                            total_ce_volume += ce.get('volume', ce.get('totalTradedVolume', 0))

                        # Check for PE data
                        if 'PE' in strike_data:
                            pe = strike_data['PE']
                            total_pe_oi += pe.get('openInterest', pe.get('oi', 0))
                            total_pe_change += pe.get('changeinOpenInterest', pe.get('oi_change', 0))
                            total_pe_volume += pe.get('volume', pe.get('totalTradedVolume', 0))

            # Calculate PCR ratios
            pcr_oi = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 0
            pcr_change_oi = total_pe_change / total_ce_change if total_ce_change > 0 else 0
            pcr_volume = total_pe_volume / total_ce_volume if total_ce_volume > 0 else 0

            # Determine bias based on PCR
            def get_pcr_bias(pcr_value):
                if pcr_value > 1.2:
                    return "BULLISH"
                elif pcr_value < 0.8:
                    return "BEARISH"
                else:
                    return "NEUTRAL"

            oi_bias = get_pcr_bias(pcr_oi)
            change_oi_bias = get_pcr_bias(pcr_change_oi)
            volume_bias = get_pcr_bias(pcr_volume)

            # Calculate overall bias score
            bias_score = 0

            # OI bias weight: 3
            if oi_bias == "BULLISH":
                bias_score += 3
            elif oi_bias == "BEARISH":
                bias_score -= 3

            # Change in OI bias weight: 5 (more important)
            if change_oi_bias == "BULLISH":
                bias_score += 5
            elif change_oi_bias == "BEARISH":
                bias_score -= 5

            # Volume bias weight: 2
            if volume_bias == "BULLISH":
                bias_score += 2
            elif volume_bias == "BEARISH":
                bias_score -= 2

            # Determine overall bias
            if bias_score >= 5:
                overall_bias = "BULLISH"
            elif bias_score <= -5:
                overall_bias = "BEARISH"
            else:
                overall_bias = "NEUTRAL"

            return {
                'success': True,
                'symbol': symbol,
                'spot_price': spot_price,
                'expiry': current_expiry,
                'total_ce_oi': total_ce_oi,
                'total_pe_oi': total_pe_oi,
                'total_ce_change': total_ce_change,
                'total_pe_change': total_pe_change,
                'total_ce_volume': total_ce_volume,
                'total_pe_volume': total_pe_volume,
                'pcr_oi': pcr_oi,
                'pcr_change_oi': pcr_change_oi,
                'pcr_volume': pcr_volume,
                'oi_bias': oi_bias,
                'change_oi_bias': change_oi_bias,
                'volume_bias': volume_bias,
                'overall_bias': overall_bias,
                'bias_score': bias_score,
                'timestamp': get_current_time_ist()
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def analyze_all_instruments(self):
        """Analyze all configured instruments"""
        results = []

        for symbol in self.instruments.keys():
            pcr_data = self.calculate_pcr(symbol)
            if pcr_data['success']:
                results.append(pcr_data)

        if not results:
            return {
                'success': False,
                'error': 'No data available for any instrument'
            }

        # Calculate overall market bias
        bullish_count = sum(1 for r in results if r['overall_bias'] == 'BULLISH')
        bearish_count = sum(1 for r in results if r['overall_bias'] == 'BEARISH')
        neutral_count = sum(1 for r in results if r['overall_bias'] == 'NEUTRAL')

        total_instruments = len(results)

        # Overall market bias
        if bullish_count > bearish_count:
            market_bias = "BULLISH"
        elif bearish_count > bullish_count:
            market_bias = "BEARISH"
        else:
            market_bias = "NEUTRAL"

        # Calculate confidence
        dominant_count = max(bullish_count, bearish_count, neutral_count)
        confidence = (dominant_count / total_instruments) * 100 if total_instruments > 0 else 0

        return {
            'success': True,
            'instruments': results,
            'market_bias': market_bias,
            'bullish_count': bullish_count,
            'bearish_count': bearish_count,
            'neutral_count': neutral_count,
            'total_instruments': total_instruments,
            'confidence': confidence,
            'timestamp': get_current_time_ist()
        }
