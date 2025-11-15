"""
Option Chain Analysis Module
Fetches NSE option chain data and calculates PCR ratios and overall bias
"""

import requests
import pandas as pd
from datetime import datetime
from pytz import timezone

class OptionChainAnalyzer:
    """Analyzes NSE option chain data for multiple instruments"""

    def __init__(self):
        self.instruments = {
            'NIFTY': 'https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY',
            'BANKNIFTY': 'https://www.nseindia.com/api/option-chain-indices?symbol=BANKNIFTY',
            'FINNIFTY': 'https://www.nseindia.com/api/option-chain-indices?symbol=FINNIFTY',
        }

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
        }

    def fetch_option_chain(self, symbol):
        """Fetch option chain data from NSE"""
        try:
            # Create session and get cookies
            session = requests.Session()
            session.headers.update(self.headers)

            # First request to get cookies
            session.get("https://www.nseindia.com", timeout=5)

            # Get option chain data
            if symbol in self.instruments:
                url = self.instruments[symbol]
            else:
                # For stocks
                url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"

            response = session.get(url, timeout=10)

            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f'API returned status code {response.status_code}'
                }

            data = response.json()

            # Extract relevant data
            records = data['records']['data']
            expiry_dates = data['records']['expiryDates']
            underlying_value = data['records']['underlyingValue']

            return {
                'success': True,
                'symbol': symbol,
                'spot_price': underlying_value,
                'records': records,
                'expiry_dates': expiry_dates,
                'current_expiry': expiry_dates[0] if expiry_dates else None
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def calculate_pcr(self, symbol):
        """Calculate Put-Call Ratio for a symbol"""
        oc_data = self.fetch_option_chain(symbol)

        if not oc_data['success']:
            return oc_data

        try:
            records = oc_data['records']
            current_expiry = oc_data['current_expiry']

            # Filter records for current expiry
            expiry_records = []
            for record in records:
                if 'CE' in record and 'PE' in record:
                    if record['CE'].get('expiryDate') == current_expiry:
                        expiry_records.append(record)

            # Calculate totals
            total_ce_oi = sum(record['CE']['openInterest'] for record in expiry_records if 'CE' in record)
            total_pe_oi = sum(record['PE']['openInterest'] for record in expiry_records if 'PE' in record)

            total_ce_change = sum(record['CE']['changeinOpenInterest'] for record in expiry_records if 'CE' in record)
            total_pe_change = sum(record['PE']['changeinOpenInterest'] for record in expiry_records if 'PE' in record)

            total_ce_volume = sum(record['CE']['totalTradedVolume'] for record in expiry_records if 'CE' in record)
            total_pe_volume = sum(record['PE']['totalTradedVolume'] for record in expiry_records if 'PE' in record)

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
                'spot_price': oc_data['spot_price'],
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
                'timestamp': datetime.now(timezone('Asia/Kolkata'))
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
            'timestamp': datetime.now(timezone('Asia/Kolkata'))
        }
