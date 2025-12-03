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
            'SENSEX': '51',
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

    def calculate_atm_zone_bias(self, symbol, atm_range=5):
        """
        Calculate ATM zone bias with strike-wise PCR for ATM ±5 strikes

        Args:
            symbol: Trading symbol (NIFTY, BANKNIFTY, etc.)
            atm_range: Number of strikes above and below ATM (default 5)

        Returns:
            Dictionary with ATM zone bias data
        """
        oc_data = self.fetch_option_chain(symbol)

        if not oc_data['success']:
            return oc_data

        try:
            records = oc_data['records']
            spot_price = oc_data['spot_price']
            current_expiry = oc_data['current_expiry']

            # Strike interval based on symbol
            strike_intervals = {
                'NIFTY': 50,
                'BANKNIFTY': 100,
                'FINNIFTY': 50,
                'SENSEX': 100
            }
            strike_interval = strike_intervals.get(symbol, 50)

            # Find ATM strike (round spot price to nearest strike interval)
            atm_strike = round(spot_price / strike_interval) * strike_interval

            # Generate ATM ±5 strikes
            target_strikes = [
                atm_strike + (i * strike_interval)
                for i in range(-atm_range, atm_range + 1)
            ]

            # Parse option chain data and extract strike-wise data
            strike_data_map = {}

            # Handle list format
            if isinstance(records, list):
                for record in records:
                    strike_price = record.get('strike_price', record.get('strikePrice', 0))

                    if strike_price in target_strikes:
                        ce_data = record.get('call_options', record.get('CE', {}))
                        pe_data = record.get('put_options', record.get('PE', {}))

                        strike_data_map[strike_price] = {
                            'ce_oi': ce_data.get('oi', ce_data.get('openInterest', 0)),
                            'ce_oi_change': ce_data.get('oi_change', ce_data.get('changeinOpenInterest', 0)),
                            'ce_volume': ce_data.get('volume', ce_data.get('totalTradedVolume', 0)),
                            'pe_oi': pe_data.get('oi', pe_data.get('openInterest', 0)),
                            'pe_oi_change': pe_data.get('oi_change', pe_data.get('changeinOpenInterest', 0)),
                            'pe_volume': pe_data.get('volume', pe_data.get('totalTradedVolume', 0))
                        }

            # Handle dict format
            elif isinstance(records, dict):
                for strike_key, strike_record in records.items():
                    if isinstance(strike_record, dict):
                        strike_price = strike_record.get('strike_price', strike_record.get('strikePrice', 0))

                        if strike_price in target_strikes:
                            ce_data = strike_record.get('CE', {})
                            pe_data = strike_record.get('PE', {})

                            strike_data_map[strike_price] = {
                                'ce_oi': ce_data.get('openInterest', ce_data.get('oi', 0)),
                                'ce_oi_change': ce_data.get('changeinOpenInterest', ce_data.get('oi_change', 0)),
                                'ce_volume': ce_data.get('volume', ce_data.get('totalTradedVolume', 0)),
                                'pe_oi': pe_data.get('openInterest', pe_data.get('oi', 0)),
                                'pe_oi_change': pe_data.get('changeinOpenInterest', pe_data.get('oi_change', 0)),
                                'pe_volume': pe_data.get('volume', pe_data.get('totalTradedVolume', 0))
                            }

            # Calculate PCR for each strike and prepare result
            atm_zone_data = []

            for strike_price in target_strikes:
                strike_offset = int((strike_price - atm_strike) / strike_interval)

                if strike_price in strike_data_map:
                    data = strike_data_map[strike_price]

                    # Calculate strike-wise PCR
                    pcr_oi = data['pe_oi'] / data['ce_oi'] if data['ce_oi'] > 0 else 0
                    pcr_oi_change = data['pe_oi_change'] / data['ce_oi_change'] if data['ce_oi_change'] != 0 else 0
                    pcr_volume = data['pe_volume'] / data['ce_volume'] if data['ce_volume'] > 0 else 0

                    # Determine strike bias
                    def get_strike_bias(pcr_oi, pcr_oi_change):
                        # Weighted bias calculation
                        score = 0
                        if pcr_oi > 1.2:
                            score += 3
                        elif pcr_oi < 0.8:
                            score -= 3

                        if pcr_oi_change > 1.2:
                            score += 5
                        elif pcr_oi_change < 0.8:
                            score -= 5

                        if score >= 5:
                            return "BULLISH"
                        elif score <= -5:
                            return "BEARISH"
                        else:
                            return "NEUTRAL"

                    strike_bias = get_strike_bias(pcr_oi, pcr_oi_change)

                    atm_zone_data.append({
                        'strike_price': strike_price,
                        'strike_offset': strike_offset,
                        'ce_oi': data['ce_oi'],
                        'pe_oi': data['pe_oi'],
                        'ce_oi_change': data['ce_oi_change'],
                        'pe_oi_change': data['pe_oi_change'],
                        'ce_volume': data['ce_volume'],
                        'pe_volume': data['pe_volume'],
                        'pcr_oi': round(pcr_oi, 4),
                        'pcr_oi_change': round(pcr_oi_change, 4),
                        'pcr_volume': round(pcr_volume, 4),
                        'strike_bias': strike_bias
                    })
                else:
                    # No data for this strike
                    atm_zone_data.append({
                        'strike_price': strike_price,
                        'strike_offset': strike_offset,
                        'ce_oi': 0,
                        'pe_oi': 0,
                        'ce_oi_change': 0,
                        'pe_oi_change': 0,
                        'ce_volume': 0,
                        'pe_volume': 0,
                        'pcr_oi': 0,
                        'pcr_oi_change': 0,
                        'pcr_volume': 0,
                        'strike_bias': 'NEUTRAL'
                    })

            # Sort by strike offset
            atm_zone_data.sort(key=lambda x: x['strike_offset'])

            return {
                'success': True,
                'symbol': symbol,
                'spot_price': spot_price,
                'atm_strike': atm_strike,
                'expiry': current_expiry,
                'strike_interval': strike_interval,
                'atm_zone_data': atm_zone_data,
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
