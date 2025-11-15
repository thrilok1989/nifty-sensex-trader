"""
Comprehensive Bias Analysis Module
Converts Pine Script "Smart Trading Dashboard - Enhanced Pro" to Python
Provides 15+ bias indicators with scoring and overall market bias calculation
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import yfinance as yf
import warnings
warnings.filterwarnings('ignore')


class BiasAnalysisPro:
    """
    Comprehensive Bias Analysis matching Pine Script indicator
    Analyzes 15+ different bias indicators and provides overall market bias
    """

    def __init__(self):
        """Initialize bias analysis with default configuration"""
        self.config = self._default_config()
        self.all_bias_results = []
        self.overall_bias = "NEUTRAL"
        self.overall_score = 0

    def _default_config(self) -> Dict:
        """Default configuration from Pine Script"""
        return {
            # Timeframes
            'tf1': '15m',
            'tf2': '1h',

            # Indicator periods
            'rsi_period': 14,
            'mfi_period': 10,
            'dmi_period': 13,
            'dmi_smoothing': 8,
            'atr_period': 14,

            # Volume
            'volume_roc_length': 14,
            'volume_threshold': 1.2,

            # Volatility
            'volatility_ratio_length': 14,
            'volatility_threshold': 1.5,

            # OBV
            'obv_smoothing': 21,

            # Force Index
            'force_index_length': 13,
            'force_index_smoothing': 2,

            # Price ROC
            'price_roc_length': 12,

            # Market Breadth
            'breadth_threshold': 60,

            # Divergence
            'divergence_lookback': 30,
            'rsi_overbought': 70,
            'rsi_oversold': 30,

            # Choppiness Index
            'ci_length': 14,
            'ci_high_threshold': 61.8,
            'ci_low_threshold': 38.2,

            # Bias parameters
            'bias_strength': 60,
            'divergence_threshold': 60,

            # Adaptive weights
            'normal_fast_weight': 2.0,
            'normal_medium_weight': 3.0,
            'normal_slow_weight': 5.0,
            'reversal_fast_weight': 5.0,
            'reversal_medium_weight': 3.0,
            'reversal_slow_weight': 2.0,

            # Stocks with weights
            'stocks': {
                'RELIANCE.NS': 9.98,
                'HDFCBANK.NS': 9.67,
                'BHARTIARTL.NS': 9.97,
                'TCS.NS': 8.54,
                'ICICIBANK.NS': 8.01,
                'INFY.NS': 8.55,
                'HINDUNILVR.NS': 1.98,
                'ITC.NS': 2.44,
                'MARUTI.NS': 0.0
            }
        }

    # =========================================================================
    # DATA FETCHING
    # =========================================================================

    def fetch_data(self, symbol: str, period: str = '60d', interval: str = '1m') -> pd.DataFrame:
        """Fetch data from Yahoo Finance"""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            if df.empty:
                print(f"Warning: No data for {symbol}")
            return df
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            return pd.DataFrame()

    # =========================================================================
    # TECHNICAL INDICATORS
    # =========================================================================

    def calculate_rsi(self, data: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_mfi(self, df: pd.DataFrame, period: int = 10) -> pd.Series:
        """Calculate Money Flow Index"""
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        money_flow = typical_price * df['Volume']

        positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0)
        negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0)

        positive_mf = positive_flow.rolling(window=period).sum()
        negative_mf = negative_flow.rolling(window=period).sum()

        mfi_ratio = positive_mf / negative_mf
        mfi = 100 - (100 / (1 + mfi_ratio))
        return mfi

    def calculate_dmi(self, df: pd.DataFrame, period: int = 13, smoothing: int = 8):
        """Calculate DMI indicators"""
        high = df['High']
        low = df['Low']
        close = df['Close']

        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        # Directional Movement
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low

        plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0)
        minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0)

        # Directional Indicators
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

        # ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=smoothing).mean()

        return plus_di, minus_di, adx

    def calculate_vwap(self, df: pd.DataFrame) -> pd.Series:
        """Calculate VWAP"""
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        vwap = (typical_price * df['Volume']).cumsum() / df['Volume'].cumsum()
        return vwap

    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate ATR"""
        high = df['High']
        low = df['Low']
        close = df['Close']

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr

    def calculate_ema(self, data: pd.Series, period: int) -> pd.Series:
        """Calculate EMA"""
        return data.ewm(span=period, adjust=False).mean()

    # =========================================================================
    # ENHANCED INDICATORS
    # =========================================================================

    def calculate_volatility_ratio(self, df: pd.DataFrame, length: int = 14) -> Tuple[pd.Series, bool, bool]:
        """Calculate Volatility Ratio"""
        atr = self.calculate_atr(df, length)
        stdev = df['Close'].rolling(window=length).std()
        volatility_ratio = (stdev / atr) * 100

        high_volatility = volatility_ratio.iloc[-1] > self.config['volatility_threshold']
        low_volatility = volatility_ratio.iloc[-1] < (self.config['volatility_threshold'] * 0.5)

        return volatility_ratio, high_volatility, low_volatility

    def calculate_volume_roc(self, df: pd.DataFrame, length: int = 14) -> Tuple[pd.Series, bool, bool]:
        """Calculate Volume Rate of Change"""
        volume_roc = ((df['Volume'] - df['Volume'].shift(length)) / df['Volume'].shift(length)) * 100

        strong_volume = volume_roc.iloc[-1] > self.config['volume_threshold']
        weak_volume = volume_roc.iloc[-1] < -self.config['volume_threshold']

        return volume_roc, strong_volume, weak_volume

    def calculate_obv(self, df: pd.DataFrame, smoothing: int = 21):
        """Calculate On Balance Volume"""
        obv = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
        obv_ma = obv.rolling(window=smoothing).mean()

        obv_rising = obv.iloc[-1] > obv.iloc[-2]
        obv_falling = obv.iloc[-1] < obv.iloc[-2]
        obv_bullish = obv.iloc[-1] > obv_ma.iloc[-1] and obv_rising
        obv_bearish = obv.iloc[-1] < obv_ma.iloc[-1] and obv_falling

        return obv, obv_ma, obv_bullish, obv_bearish

    def calculate_force_index(self, df: pd.DataFrame, length: int = 13, smoothing: int = 2):
        """Calculate Force Index"""
        force_index = (df['Close'] - df['Close'].shift(1)) * df['Volume']
        force_index_ma = force_index.ewm(span=length, adjust=False).mean()
        force_index_smoothed = force_index_ma.ewm(span=smoothing, adjust=False).mean()

        force_rising = force_index_smoothed.iloc[-1] > force_index_smoothed.iloc[-2]
        force_falling = force_index_smoothed.iloc[-1] < force_index_smoothed.iloc[-2]
        force_bullish = force_index_smoothed.iloc[-1] > 0 and force_rising
        force_bearish = force_index_smoothed.iloc[-1] < 0 and force_falling

        return force_index_smoothed, force_bullish, force_bearish

    def calculate_price_roc(self, df: pd.DataFrame, length: int = 12):
        """Calculate Price Rate of Change"""
        price_roc = ((df['Close'] - df['Close'].shift(length)) / df['Close'].shift(length)) * 100

        price_momentum_bullish = price_roc.iloc[-1] > 0
        price_momentum_bearish = price_roc.iloc[-1] < 0

        return price_roc, price_momentum_bullish, price_momentum_bearish

    def calculate_choppiness_index(self, df: pd.DataFrame, period: int = 14):
        """Calculate Choppiness Index"""
        high_low = df['High'] - df['Low']
        high_close = abs(df['High'] - df['Close'].shift(1))
        low_close = abs(df['Low'] - df['Close'].shift(1))

        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        sum_true_range = true_range.rolling(window=period).sum()
        highest_high = df['High'].rolling(window=period).max()
        lowest_low = df['Low'].rolling(window=period).min()

        ci = 100 * np.log10(sum_true_range / (highest_high - lowest_low)) / np.log10(period)

        market_chopping = ci.iloc[-1] > self.config['ci_high_threshold']
        market_trending = ci.iloc[-1] < self.config['ci_low_threshold']

        return ci, market_chopping, market_trending

    def detect_divergence(self, df: pd.DataFrame, lookback: int = 30):
        """Detect RSI/MACD Divergences"""
        rsi = self.calculate_rsi(df['Close'], 14)

        # MACD
        macd_line = df['Close'].ewm(span=12).mean() - df['Close'].ewm(span=26).mean()

        close_series = df['Close'].tail(lookback)
        rsi_series = rsi.tail(lookback)
        macd_series = macd_line.tail(lookback)

        # Bullish divergence
        lowest_close_idx = close_series.idxmin()
        lowest_rsi_idx = rsi_series.idxmin()
        bullish_rsi_divergence = (lowest_close_idx == close_series.index[-1] and
                                  rsi_series.iloc[-1] > rsi_series.loc[lowest_rsi_idx] and
                                  rsi_series.iloc[-1] < self.config['rsi_oversold'])

        # Bearish divergence
        highest_close_idx = close_series.idxmax()
        highest_rsi_idx = rsi_series.idxmax()
        bearish_rsi_divergence = (highest_close_idx == close_series.index[-1] and
                                  rsi_series.iloc[-1] < rsi_series.loc[highest_rsi_idx] and
                                  rsi_series.iloc[-1] > self.config['rsi_overbought'])

        return bullish_rsi_divergence, bearish_rsi_divergence

    # =========================================================================
    # MARKET BREADTH & STOCKS ANALYSIS
    # =========================================================================

    def calculate_market_breadth(self):
        """Calculate market breadth from top stocks"""
        bullish_stocks = 0
        total_stocks = 0
        stock_data = []

        for symbol, weight in self.config['stocks'].items():
            try:
                df = self.fetch_data(symbol, period='5d', interval='1m')
                if df.empty or len(df) < 2:
                    continue

                current_price = df['Close'].iloc[-1]
                prev_price = df['Close'].iloc[0]
                change_pct = ((current_price - prev_price) / prev_price) * 100

                if change_pct > 0:
                    bullish_stocks += 1

                total_stocks += 1

                stock_data.append({
                    'symbol': symbol.replace('.NS', ''),
                    'change_pct': change_pct,
                    'weight': weight
                })
            except Exception as e:
                print(f"Error processing {symbol}: {e}")
                continue

        if total_stocks > 0:
            market_breadth = (bullish_stocks / total_stocks) * 100
        else:
            market_breadth = 50

        breadth_bullish = market_breadth > self.config['breadth_threshold']
        breadth_bearish = market_breadth < (100 - self.config['breadth_threshold'])

        return market_breadth, breadth_bullish, breadth_bearish, bullish_stocks, total_stocks, stock_data

    # =========================================================================
    # COMPREHENSIVE BIAS ANALYSIS
    # =========================================================================

    def analyze_all_bias_indicators(self, symbol: str = "^NSEI") -> Dict:
        """
        Analyze all 15+ bias indicators and return comprehensive results
        """

        print(f"Fetching data for {symbol}...")
        df = self.fetch_data(symbol, period='60d', interval='1m')

        if df.empty or len(df) < 100:
            return {
                'success': False,
                'error': 'Insufficient data'
            }

        current_price = df['Close'].iloc[-1]

        # Initialize bias results list
        bias_results = []

        # =====================================================================
        # 1. RSI BIAS
        # =====================================================================
        rsi = self.calculate_rsi(df['Close'], self.config['rsi_period'])
        rsi_value = rsi.iloc[-1]
        if rsi_value > 60:
            rsi_bias = "BULLISH"
            rsi_score = min(100, (rsi_value - 50) * 2)
        elif rsi_value < 40:
            rsi_bias = "BEARISH"
            rsi_score = -min(100, (50 - rsi_value) * 2)
        else:
            rsi_bias = "NEUTRAL"
            rsi_score = 0

        bias_results.append({
            'indicator': 'RSI',
            'value': f"{rsi_value:.2f}",
            'bias': rsi_bias,
            'score': rsi_score,
            'weight': 1.5
        })

        # =====================================================================
        # 2. MFI BIAS
        # =====================================================================
        mfi = self.calculate_mfi(df, self.config['mfi_period'])
        mfi_value = mfi.iloc[-1]
        if mfi_value > 60:
            mfi_bias = "BULLISH"
            mfi_score = min(100, (mfi_value - 50) * 2)
        elif mfi_value < 40:
            mfi_bias = "BEARISH"
            mfi_score = -min(100, (50 - mfi_value) * 2)
        else:
            mfi_bias = "NEUTRAL"
            mfi_score = 0

        bias_results.append({
            'indicator': 'MFI (Money Flow)',
            'value': f"{mfi_value:.2f}",
            'bias': mfi_bias,
            'score': mfi_score,
            'weight': 1.5
        })

        # =====================================================================
        # 3. DMI/ADX BIAS
        # =====================================================================
        plus_di, minus_di, adx = self.calculate_dmi(df, self.config['dmi_period'], self.config['dmi_smoothing'])
        plus_di_value = plus_di.iloc[-1]
        minus_di_value = minus_di.iloc[-1]
        adx_value = adx.iloc[-1]

        if plus_di_value > minus_di_value and adx_value > 25:
            dmi_bias = "BULLISH"
            dmi_score = min(100, adx_value * 2)
        elif minus_di_value > plus_di_value and adx_value > 25:
            dmi_bias = "BEARISH"
            dmi_score = -min(100, adx_value * 2)
        else:
            dmi_bias = "NEUTRAL"
            dmi_score = 0

        bias_results.append({
            'indicator': 'DMI/ADX',
            'value': f"+DI:{plus_di_value:.1f} -DI:{minus_di_value:.1f} ADX:{adx_value:.1f}",
            'bias': dmi_bias,
            'score': dmi_score,
            'weight': 2.0
        })

        # =====================================================================
        # 4. VWAP BIAS
        # =====================================================================
        vwap = self.calculate_vwap(df)
        vwap_value = vwap.iloc[-1]

        if current_price > vwap_value:
            vwap_bias = "BULLISH"
            vwap_score = min(100, ((current_price - vwap_value) / vwap_value) * 1000)
        elif current_price < vwap_value:
            vwap_bias = "BEARISH"
            vwap_score = -min(100, ((vwap_value - current_price) / vwap_value) * 1000)
        else:
            vwap_bias = "NEUTRAL"
            vwap_score = 0

        bias_results.append({
            'indicator': 'VWAP',
            'value': f"Price: {current_price:.2f} | VWAP: {vwap_value:.2f}",
            'bias': vwap_bias,
            'score': vwap_score,
            'weight': 1.5
        })

        # =====================================================================
        # 5. VOLATILITY RATIO BIAS
        # =====================================================================
        volatility_ratio, high_volatility, low_volatility = self.calculate_volatility_ratio(
            df, self.config['volatility_ratio_length']
        )
        vol_ratio_value = volatility_ratio.iloc[-1]

        if low_volatility:
            vol_bias = "STABLE"
            vol_score = 30
        elif high_volatility:
            vol_bias = "HIGH RISK"
            vol_score = -30
        else:
            vol_bias = "NORMAL"
            vol_score = 0

        bias_results.append({
            'indicator': 'Volatility Ratio',
            'value': f"{vol_ratio_value:.2f}",
            'bias': vol_bias,
            'score': vol_score,
            'weight': 1.0
        })

        # =====================================================================
        # 6. VOLUME ROC BIAS
        # =====================================================================
        volume_roc, strong_volume, weak_volume = self.calculate_volume_roc(
            df, self.config['volume_roc_length']
        )
        vol_roc_value = volume_roc.iloc[-1]

        if strong_volume:
            vol_roc_bias = "STRONG BUY/SELL"
            vol_roc_score = 70
        elif weak_volume:
            vol_roc_bias = "WEAK"
            vol_roc_score = -30
        else:
            vol_roc_bias = "NORMAL"
            vol_roc_score = 0

        bias_results.append({
            'indicator': 'Volume ROC',
            'value': f"{vol_roc_value:.2f}%",
            'bias': vol_roc_bias,
            'score': vol_roc_score,
            'weight': 1.5
        })

        # =====================================================================
        # 7. OBV BIAS
        # =====================================================================
        obv, obv_ma, obv_bullish, obv_bearish = self.calculate_obv(df, self.config['obv_smoothing'])
        obv_value = obv.iloc[-1]

        if obv_bullish:
            obv_bias = "BULLISH"
            obv_score = 75
        elif obv_bearish:
            obv_bias = "BEARISH"
            obv_score = -75
        else:
            obv_bias = "NEUTRAL"
            obv_score = 0

        bias_results.append({
            'indicator': 'OBV (On Balance Volume)',
            'value': f"{obv_value:.0f}",
            'bias': obv_bias,
            'score': obv_score,
            'weight': 2.0
        })

        # =====================================================================
        # 8. FORCE INDEX BIAS
        # =====================================================================
        force_index, force_bullish, force_bearish = self.calculate_force_index(
            df, self.config['force_index_length'], self.config['force_index_smoothing']
        )
        force_value = force_index.iloc[-1]

        if force_bullish:
            force_bias = "BULLISH"
            force_score = 70
        elif force_bearish:
            force_bias = "BEARISH"
            force_score = -70
        else:
            force_bias = "NEUTRAL"
            force_score = 0

        bias_results.append({
            'indicator': 'Force Index',
            'value': f"{force_value:.0f}",
            'bias': force_bias,
            'score': force_score,
            'weight': 1.5
        })

        # =====================================================================
        # 9. PRICE ROC BIAS
        # =====================================================================
        price_roc, price_momentum_bullish, price_momentum_bearish = self.calculate_price_roc(
            df, self.config['price_roc_length']
        )
        price_roc_value = price_roc.iloc[-1]

        if price_momentum_bullish:
            price_roc_bias = "BULLISH"
            price_roc_score = min(100, price_roc_value * 10)
        elif price_momentum_bearish:
            price_roc_bias = "BEARISH"
            price_roc_score = max(-100, price_roc_value * 10)
        else:
            price_roc_bias = "NEUTRAL"
            price_roc_score = 0

        bias_results.append({
            'indicator': 'Price Momentum (ROC)',
            'value': f"{price_roc_value:.2f}%",
            'bias': price_roc_bias,
            'score': price_roc_score,
            'weight': 1.5
        })

        # =====================================================================
        # 10. MARKET BREADTH BIAS
        # =====================================================================
        print("Calculating market breadth...")
        market_breadth, breadth_bullish, breadth_bearish, bull_stocks, total_stocks, stock_data = self.calculate_market_breadth()

        if breadth_bullish:
            breadth_bias = "BULLISH"
            breadth_score = market_breadth
        elif breadth_bearish:
            breadth_bias = "BEARISH"
            breadth_score = -(100 - market_breadth)
        else:
            breadth_bias = "NEUTRAL"
            breadth_score = 0

        bias_results.append({
            'indicator': 'Market Breadth',
            'value': f"{market_breadth:.1f}% ({bull_stocks}/{total_stocks} stocks UP)",
            'bias': breadth_bias,
            'score': breadth_score,
            'weight': 3.0
        })

        # =====================================================================
        # 11. DIVERGENCE BIAS
        # =====================================================================
        bullish_rsi_div, bearish_rsi_div = self.detect_divergence(df, self.config['divergence_lookback'])

        if bullish_rsi_div:
            div_bias = "BULLISH REVERSAL"
            div_score = 85
        elif bearish_rsi_div:
            div_bias = "BEARISH REVERSAL"
            div_score = -85
        else:
            div_bias = "NO DIVERGENCE"
            div_score = 0

        bias_results.append({
            'indicator': 'RSI Divergence',
            'value': "Bullish" if bullish_rsi_div else "Bearish" if bearish_rsi_div else "None",
            'bias': div_bias,
            'score': div_score,
            'weight': 2.5
        })

        # =====================================================================
        # 12. CHOPPINESS INDEX BIAS
        # =====================================================================
        ci, market_chopping, market_trending = self.calculate_choppiness_index(
            df, self.config['ci_length']
        )
        ci_value = ci.iloc[-1]

        if market_trending:
            ci_bias = "TRENDING"
            ci_score = 60
        elif market_chopping:
            ci_bias = "CHOPPY/RANGING"
            ci_score = -40
        else:
            ci_bias = "BALANCED"
            ci_score = 0

        bias_results.append({
            'indicator': 'Choppiness Index',
            'value': f"{ci_value:.2f}",
            'bias': ci_bias,
            'score': ci_score,
            'weight': 1.5
        })

        # =====================================================================
        # 13. EMA CROSSOVER BIAS (Order Blocks)
        # =====================================================================
        ema5 = self.calculate_ema(df['Close'], 5)
        ema18 = self.calculate_ema(df['Close'], 18)

        ema5_value = ema5.iloc[-1]
        ema18_value = ema18.iloc[-1]

        if ema5_value > ema18_value:
            ema_bias = "BULLISH"
            ema_score = min(100, ((ema5_value - ema18_value) / ema18_value) * 500)
        elif ema5_value < ema18_value:
            ema_bias = "BEARISH"
            ema_score = -min(100, ((ema18_value - ema5_value) / ema18_value) * 500)
        else:
            ema_bias = "NEUTRAL"
            ema_score = 0

        bias_results.append({
            'indicator': 'EMA Crossover (5/18)',
            'value': f"EMA5: {ema5_value:.2f} | EMA18: {ema18_value:.2f}",
            'bias': ema_bias,
            'score': ema_score,
            'weight': 2.0
        })

        # =====================================================================
        # 14. ATR TREND BIAS
        # =====================================================================
        atr = self.calculate_atr(df, self.config['atr_period'])
        atr_value = atr.iloc[-1]
        atr_sma = atr.rolling(window=20).mean().iloc[-1]

        if atr_value > atr_sma:
            atr_bias = "EXPANDING"
            atr_score = 40
        else:
            atr_bias = "CONTRACTING"
            atr_score = -20

        bias_results.append({
            'indicator': 'ATR Trend',
            'value': f"ATR: {atr_value:.2f} | SMA: {atr_sma:.2f}",
            'bias': atr_bias,
            'score': atr_score,
            'weight': 1.0
        })

        # =====================================================================
        # 15. VOLUME TREND BIAS
        # =====================================================================
        volume_sma = df['Volume'].rolling(window=20).mean()
        current_volume = df['Volume'].iloc[-1]
        volume_sma_value = volume_sma.iloc[-1]

        if current_volume > volume_sma_value * 1.5:
            volume_trend_bias = "HIGH VOLUME"
            volume_trend_score = 60
        elif current_volume < volume_sma_value * 0.5:
            volume_trend_bias = "LOW VOLUME"
            volume_trend_score = -30
        else:
            volume_trend_bias = "NORMAL"
            volume_trend_score = 0

        bias_results.append({
            'indicator': 'Volume Trend',
            'value': f"Current: {current_volume:.0f} | Avg: {volume_sma_value:.0f}",
            'bias': volume_trend_bias,
            'score': volume_trend_score,
            'weight': 1.5
        })

        # =====================================================================
        # CALCULATE OVERALL BIAS
        # =====================================================================
        total_weighted_score = 0
        total_weight = 0
        bullish_count = 0
        bearish_count = 0
        neutral_count = 0

        for bias in bias_results:
            total_weighted_score += bias['score'] * bias['weight']
            total_weight += bias['weight']

            if 'BULLISH' in bias['bias']:
                bullish_count += 1
            elif 'BEARISH' in bias['bias']:
                bearish_count += 1
            else:
                neutral_count += 1

        # Overall score (normalized to -100 to +100)
        overall_score = total_weighted_score / total_weight if total_weight > 0 else 0

        # Determine overall bias
        if overall_score > 30:
            overall_bias = "BULLISH"
            overall_confidence = min(100, overall_score)
        elif overall_score < -30:
            overall_bias = "BEARISH"
            overall_confidence = min(100, abs(overall_score))
        else:
            overall_bias = "NEUTRAL"
            overall_confidence = 100 - abs(overall_score)

        return {
            'success': True,
            'symbol': symbol,
            'current_price': current_price,
            'timestamp': datetime.now(),
            'bias_results': bias_results,
            'overall_bias': overall_bias,
            'overall_score': overall_score,
            'overall_confidence': overall_confidence,
            'bullish_count': bullish_count,
            'bearish_count': bearish_count,
            'neutral_count': neutral_count,
            'total_indicators': len(bias_results),
            'stock_data': stock_data
        }
