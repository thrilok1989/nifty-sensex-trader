"""
Smart Trading Dashboard - Adaptive + VOB (Volume Order Blocks)
Pine Script to Python Conversion
Analyzes market sentiment and provides comprehensive bias data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from tabulate import tabulate
import yfinance as yf
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

class SmartTradingDashboard:
    """
    Complete trading dashboard with adaptive bias calculation,
    volume order blocks, range detection, and multi-timeframe analysis
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialize the dashboard with configuration"""
        self.config = config or self._default_config()
        self.data = {}
        self.indicators = {}
        self.bias_data = {}
        self.market_condition = "NEUTRAL"

    def _default_config(self) -> Dict:
        """Default configuration matching Pine Script settings"""
        return {
            # Timeframes
            'tf1': '15m',
            'tf2': '1h',
            'daily': '1d',

            # Stocks configuration
            'stocks': {
                'RELIANCE.NS': {'weight': 9.98, 'name': 'Reliance'},
                'HDFCBANK.NS': {'weight': 9.67, 'name': 'HDFC Bank'},
                'BHARTIARTL.NS': {'weight': 9.97, 'name': 'Bharti Airtel'},
                'TCS.NS': {'weight': 8.54, 'name': 'TCS'},
                'ICICIBANK.NS': {'weight': 8.01, 'name': 'ICICI Bank'},
                'INFY.NS': {'weight': 8.55, 'name': 'Infosys'},
                'HINDUNILVR.NS': {'weight': 1.98, 'name': 'Hind. Unilever'},
                'ITC.NS': {'weight': 2.44, 'name': 'ITC'},
                'MARUTI.NS': {'weight': 0.0, 'name': 'Maruti Suzuki'}
            },

            # Market data
            'us_market': '^DJI',  # Dow Jones
            'forex': 'USDINR=X',

            # Indicator parameters
            'rsi_period': 14,
            'mfi_period': 10,
            'dmi_period': 13,
            'dmi_smoothing': 8,
            'atr_period': 14,

            # VIDYA parameters
            'vidya_length': 10,
            'vidya_momentum': 20,
            'band_distance': 2.0,

            # Order Block parameters
            'ob_sensitivity': 5,
            'vob_sensitivity': 5,

            # Range detection
            'range_pct_threshold': 2.0,
            'range_min_bars': 20,
            'ema_spread_threshold': 0.5,

            # Bias parameters
            'bias_strength': 60,
            'divergence_threshold': 60,

            # Adaptive weights - Normal mode
            'normal_fast_weight': 2.0,
            'normal_medium_weight': 3.0,
            'normal_slow_weight': 5.0,

            # Adaptive weights - Reversal mode
            'reversal_fast_weight': 5.0,
            'reversal_medium_weight': 3.0,
            'reversal_slow_weight': 2.0,

            # Trade management
            'atr_multiplier': 1.5,
            'risk_reward_ratio': 2.0,
            'pivot_touch_tolerance': 0.15,
            'pivot_exit_tolerance': 0.2,

            # Data period
            'lookback_days': 60
        }

    def fetch_data(self, symbol: str, period: str = '7d', interval: str = '5m') -> pd.DataFrame:
        """Fetch data from Yahoo Finance
        Note: Yahoo Finance limits intraday data - use 7d max for 5m interval
        """
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            if df.empty:
                print(f"Warning: No data for {symbol}")
                return pd.DataFrame()
            return df
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            return pd.DataFrame()

    def calculate_rsi(self, data: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
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

    def calculate_dmi(self, df: pd.DataFrame, period: int = 13, smoothing: int = 8) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate DMI (Directional Movement Index) indicators"""
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

    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        high = df['High']
        low = df['Low']
        close = df['Close']

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr

    def calculate_vwap(self, df: pd.DataFrame) -> pd.Series:
        """Calculate VWAP (Volume Weighted Average Price)"""
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        vwap = (typical_price * df['Volume']).cumsum() / df['Volume'].cumsum()
        return vwap

    def calculate_vidya(self, data: pd.Series, length: int = 10, momentum: int = 20) -> pd.Series:
        """Calculate VIDYA (Variable Index Dynamic Average)"""
        m = data.diff()
        p = m.where(m >= 0, 0).rolling(window=momentum).sum()
        n = (-m.where(m < 0, 0)).rolling(window=momentum).sum()

        abs_cmo = abs(100 * (p - n) / (p + n))
        alpha = 2 / (length + 1)

        vidya = pd.Series(index=data.index, dtype=float)
        vidya.iloc[0] = data.iloc[0]

        for i in range(1, len(data)):
            if pd.notna(abs_cmo.iloc[i]):
                vidya.iloc[i] = alpha * abs_cmo.iloc[i] / 100 * data.iloc[i] + \
                               (1 - alpha * abs_cmo.iloc[i] / 100) * vidya.iloc[i-1]
            else:
                vidya.iloc[i] = vidya.iloc[i-1]

        return vidya.rolling(window=15).mean()

    def calculate_ema(self, data: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return data.ewm(span=period, adjust=False).mean()

    def detect_order_blocks(self, df: pd.DataFrame, sensitivity: int = 5) -> Dict:
        """Detect Order Blocks based on EMA crossovers"""
        ema1 = self.calculate_ema(df['Close'], sensitivity)
        ema2 = self.calculate_ema(df['Close'], sensitivity + 13)

        cross_up = (ema1 > ema2) & (ema1.shift(1) <= ema2.shift(1))
        cross_down = (ema1 < ema2) & (ema1.shift(1) >= ema2.shift(1))

        return {
            'bullish_signal': cross_up.iloc[-1] if len(cross_up) > 0 else False,
            'bearish_signal': cross_down.iloc[-1] if len(cross_down) > 0 else False,
            'ema1': ema1.iloc[-1] if len(ema1) > 0 else np.nan,
            'ema2': ema2.iloc[-1] if len(ema2) > 0 else np.nan
        }

    def detect_range_bound(self, df: pd.DataFrame) -> Dict:
        """Detect if market is range-bound"""
        lookback = self.config['range_min_bars']

        rolling_high = df['High'].tail(lookback).max()
        rolling_low = df['Low'].tail(lookback).min()
        current_close = df['Close'].iloc[-1]

        rolling_range = rolling_high - rolling_low
        rolling_range_pct = (rolling_range / current_close) * 100

        # EMA spread
        ob_data = self.detect_order_blocks(df, self.config['ob_sensitivity'])
        if pd.notna(ob_data['ema1']) and pd.notna(ob_data['ema2']):
            ema_spread_pct = abs(ob_data['ema1'] - ob_data['ema2']) / current_close * 100
        else:
            ema_spread_pct = 0

        # ATR analysis
        atr = self.calculate_atr(df, self.config['atr_period'])
        atr_avg = atr.tail(50).mean()
        current_atr = atr.iloc[-1]

        tight_range = rolling_range_pct < self.config['range_pct_threshold']
        low_ema_spread = ema_spread_pct < self.config['ema_spread_threshold']
        low_volatility = current_atr < atr_avg

        is_range_bound = tight_range and low_ema_spread and low_volatility

        # Determine market condition
        if is_range_bound:
            condition = "RANGE-BOUND"
        elif ob_data['ema1'] > ob_data['ema2'] and ema_spread_pct > 1.0:
            condition = "TRENDING UP"
        elif ob_data['ema1'] < ob_data['ema2'] and ema_spread_pct > 1.0:
            condition = "TRENDING DOWN"
        else:
            condition = "TRANSITION"

        movement_strength = ema_spread_pct * 10
        if movement_strength > 5:
            movement_quality = "STRONG"
        elif movement_strength > 2:
            movement_quality = "MODERATE"
        elif movement_strength > 0.5:
            movement_quality = "WEAK"
        else:
            movement_quality = "CHOPPY"

        return {
            'condition': condition,
            'is_range_bound': is_range_bound,
            'range_high': rolling_high if is_range_bound else np.nan,
            'range_low': rolling_low if is_range_bound else np.nan,
            'range_mid': (rolling_high + rolling_low) / 2 if is_range_bound else np.nan,
            'range_pct': rolling_range_pct,
            'ema_spread_pct': ema_spread_pct,
            'movement_quality': movement_quality,
            'movement_strength': movement_strength
        }

    def calculate_stock_metrics(self, symbol: str) -> Dict:
        """Calculate metrics for a single stock"""
        try:
            # Fetch data for different timeframes
            # Use 5m interval (Yahoo Finance limitation for intraday data)
            df_5m = self.fetch_data(symbol, period='5d', interval='5m')
            df_daily = self.fetch_data(symbol, period='60d', interval='1d')

            if df_5m.empty or df_daily.empty:
                return None

            # Current values
            current_price = df_5m['Close'].iloc[-1]
            prev_close_daily = df_daily['Close'].iloc[-2]

            # Daily change
            daily_change = current_price - prev_close_daily
            daily_change_pct = (daily_change / prev_close_daily) * 100

            # TF1 (15m) and TF2 (1h) changes
            tf1_interval = '15m'
            tf2_interval = '60m'

            df_tf1 = self.fetch_data(symbol, period='5d', interval=tf1_interval)
            df_tf2 = self.fetch_data(symbol, period='10d', interval=tf2_interval)

            if not df_tf1.empty and len(df_tf1) > 1:
                tf1_prev = df_tf1['Close'].iloc[-2]
                tf1_change_pct = ((current_price - tf1_prev) / tf1_prev) * 100
            else:
                tf1_change_pct = 0

            if not df_tf2.empty and len(df_tf2) > 1:
                tf2_prev = df_tf2['Close'].iloc[-2]
                tf2_change_pct = ((current_price - tf2_prev) / tf2_prev) * 100
            else:
                tf2_change_pct = 0

            return {
                'symbol': symbol,
                'ltp': current_price,
                'change': daily_change,
                'change_pct': daily_change_pct,
                'tf1_change_pct': tf1_change_pct,
                'tf2_change_pct': tf2_change_pct,
                'df': df_5m
            }
        except Exception as e:
            print(f"Error calculating metrics for {symbol}: {e}")
            return None

    def calculate_market_indicators(self, df: pd.DataFrame) -> Dict:
        """Calculate all market indicators for bias determination"""
        indicators = {}

        # Basic indicators
        indicators['rsi'] = self.calculate_rsi(df['Close'], self.config['rsi_period'])
        indicators['mfi'] = self.calculate_mfi(df, self.config['mfi_period'])
        indicators['vwap'] = self.calculate_vwap(df)
        indicators['atr'] = self.calculate_atr(df, self.config['atr_period'])

        # DMI
        plus_di, minus_di, adx = self.calculate_dmi(df, self.config['dmi_period'], self.config['dmi_smoothing'])
        indicators['plus_di'] = plus_di
        indicators['minus_di'] = minus_di
        indicators['adx'] = adx

        # VIDYA
        indicators['vidya'] = self.calculate_vidya(df['Close'],
                                                    self.config['vidya_length'],
                                                    self.config['vidya_momentum'])

        # Order blocks
        indicators['order_blocks'] = self.detect_order_blocks(df, self.config['ob_sensitivity'])

        # Range detection
        indicators['range_data'] = self.detect_range_bound(df)

        # Volume analysis
        volume_sma = df['Volume'].rolling(window=20).mean()
        indicators['volume_trend'] = df['Volume'].iloc[-1] > volume_sma.iloc[-1] * 1.2

        return indicators

    def calculate_bias_signals(self, df: pd.DataFrame, indicators: Dict, stock_metrics: List[Dict]) -> Dict:
        """Calculate comprehensive market bias"""

        # Fast signals (technical indicators)
        fast_bull = 0
        fast_bear = 0
        fast_total = 0

        current_close = df['Close'].iloc[-1]
        current_rsi = indicators['rsi'].iloc[-1]
        current_mfi = indicators['mfi'].iloc[-1]
        current_vwap = indicators['vwap'].iloc[-1]
        current_plus_di = indicators['plus_di'].iloc[-1]
        current_minus_di = indicators['minus_di'].iloc[-1]

        # RSI signal
        if current_rsi > 50:
            fast_bull += 1
        else:
            fast_bear += 1
        fast_total += 1

        # MFI signal
        if current_mfi > 50:
            fast_bull += 1
        else:
            fast_bear += 1
        fast_total += 1

        # DMI signal
        if current_plus_di > current_minus_di:
            fast_bull += 1
        else:
            fast_bear += 1
        fast_total += 1

        # VWAP signal
        if current_close > current_vwap:
            fast_bull += 1
        else:
            fast_bear += 1
        fast_total += 1

        # Order block signal
        if indicators['order_blocks']['bullish_signal']:
            fast_bull += 1
        if indicators['order_blocks']['bearish_signal']:
            fast_bear += 1
        fast_total += 1

        # VIDYA trend
        atr_val = indicators['atr'].iloc[-1]
        vidya_val = indicators['vidya'].iloc[-1]
        upper_band = vidya_val + atr_val * self.config['band_distance']
        lower_band = vidya_val - atr_val * self.config['band_distance']

        if current_close > upper_band:
            fast_bull += 1
        elif current_close < lower_band:
            fast_bear += 1
        fast_total += 1

        # Volume signal
        if indicators['volume_trend']:
            fast_bull += 1
        else:
            fast_bear += 1
        fast_total += 1

        fast_bull_pct = (fast_bull / fast_total) * 100 if fast_total > 0 else 0
        fast_bear_pct = (fast_bear / fast_total) * 100 if fast_total > 0 else 0

        # Medium signals (price vs VWAP)
        medium_bull = 0
        medium_bear = 0
        medium_total = 0

        if current_close > current_vwap:
            medium_bull += 1
        else:
            medium_bear += 1
        medium_total += 1

        medium_bull_pct = (medium_bull / medium_total) * 100 if medium_total > 0 else 0
        medium_bear_pct = (medium_bear / medium_total) * 100 if medium_total > 0 else 0

        # Slow signals (stock performance)
        slow_bull = 0
        slow_bear = 0
        slow_total = 0

        total_weight = sum([s['change_pct'] for s in stock_metrics if s is not None])
        weighted_avg_daily = total_weight / len([s for s in stock_metrics if s is not None]) if stock_metrics else 0

        total_tf1 = sum([s['tf1_change_pct'] for s in stock_metrics if s is not None])
        weighted_avg_tf1 = total_tf1 / len([s for s in stock_metrics if s is not None]) if stock_metrics else 0

        total_tf2 = sum([s['tf2_change_pct'] for s in stock_metrics if s is not None])
        weighted_avg_tf2 = total_tf2 / len([s for s in stock_metrics if s is not None]) if stock_metrics else 0

        if weighted_avg_daily > 0:
            slow_bull += 1
        else:
            slow_bear += 1
        slow_total += 1

        if weighted_avg_tf1 > 0:
            slow_bull += 1
        else:
            slow_bear += 1
        slow_total += 1

        if weighted_avg_tf2 > 0:
            slow_bull += 1
        else:
            slow_bear += 1
        slow_total += 1

        slow_bull_pct = (slow_bull / slow_total) * 100 if slow_total > 0 else 0
        slow_bear_pct = (slow_bear / slow_total) * 100 if slow_total > 0 else 0

        # Divergence detection
        bullish_divergence = slow_bull_pct >= 66 and fast_bear_pct >= self.config['divergence_threshold']
        bearish_divergence = slow_bear_pct >= 66 and fast_bull_pct >= self.config['divergence_threshold']
        divergence_detected = bullish_divergence or bearish_divergence

        # Adaptive mode
        reversal_mode = divergence_detected

        if reversal_mode:
            fast_weight = self.config['reversal_fast_weight']
            medium_weight = self.config['reversal_medium_weight']
            slow_weight = self.config['reversal_slow_weight']
        else:
            fast_weight = self.config['normal_fast_weight']
            medium_weight = self.config['normal_medium_weight']
            slow_weight = self.config['normal_slow_weight']

        # Calculate weighted bias
        bullish_signals = (fast_bull * fast_weight) + (medium_bull * medium_weight) + (slow_bull * slow_weight)
        bearish_signals = (fast_bear * fast_weight) + (medium_bear * medium_weight) + (slow_bear * slow_weight)
        total_signals = (fast_total * fast_weight) + (medium_total * medium_weight) + (slow_total * slow_weight)

        bullish_bias_pct = (bullish_signals / total_signals) * 100 if total_signals > 0 else 0
        bearish_bias_pct = (bearish_signals / total_signals) * 100 if total_signals > 0 else 0

        # Adjust bias strength for range-bound markets
        adjusted_bias_strength = self.config['bias_strength']
        if indicators['range_data']['condition'] == "RANGE-BOUND":
            adjusted_bias_strength += 10

        # Determine market bias
        if bullish_bias_pct >= adjusted_bias_strength:
            market_bias = "BULLISH"
        elif bearish_bias_pct >= adjusted_bias_strength:
            market_bias = "BEARISH"
        else:
            market_bias = "NEUTRAL"

        return {
            'fast_bull_pct': fast_bull_pct,
            'fast_bear_pct': fast_bear_pct,
            'medium_bull_pct': medium_bull_pct,
            'medium_bear_pct': medium_bear_pct,
            'slow_bull_pct': slow_bull_pct,
            'slow_bear_pct': slow_bear_pct,
            'bullish_bias_pct': bullish_bias_pct,
            'bearish_bias_pct': bearish_bias_pct,
            'market_bias': market_bias,
            'reversal_mode': reversal_mode,
            'divergence_detected': divergence_detected,
            'bullish_divergence': bullish_divergence,
            'bearish_divergence': bearish_divergence,
            'weighted_avg_daily': weighted_avg_daily,
            'weighted_avg_tf1': weighted_avg_tf1,
            'weighted_avg_tf2': weighted_avg_tf2
        }

    def analyze_market(self, symbol: str = '^NSEI') -> Dict:
        """Main analysis function - analyzes market and returns all data"""
        print(f"\n{'='*80}")
        print(f"SMART TRADING DASHBOARD - MARKET ANALYSIS")
        print(f"{'='*80}")
        print(f"Analyzing: {symbol}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")

        # Fetch main market data
        print("📊 Fetching market data...")
        # Use 5m interval (Yahoo Finance limitation for intraday data)
        df = self.fetch_data(symbol, period='5d', interval='5m')

        if df.empty:
            print("❌ No data available for analysis")
            return {}

        # Calculate stock metrics
        print("📈 Analyzing stocks...")
        stock_metrics = []
        stock_data_table = []

        for sym, info in self.config['stocks'].items():
            if info['weight'] > 0:  # Only analyze stocks with weight
                print(f"  • {info['name']}...", end=' ')
                metrics = self.calculate_stock_metrics(sym)
                if metrics:
                    stock_metrics.append(metrics)
                    stock_data_table.append([
                        info['name'],
                        f"{metrics['ltp']:.2f}",
                        f"{metrics['change']:.2f}",
                        f"{metrics['change_pct']:.2f}%",
                        f"{metrics['tf1_change_pct']:.2f}%",
                        f"{metrics['tf2_change_pct']:.2f}%",
                        '🟢' if metrics['change_pct'] >= 0 else '🔴'
                    ])
                    print("✓")
                else:
                    print("✗")

        # Fetch US market data
        print("\n🌎 Fetching global market data...")
        us_market = self.calculate_stock_metrics(self.config['us_market'])
        forex = self.calculate_stock_metrics(self.config['forex'])

        # Calculate indicators
        print("\n🔧 Calculating indicators...")
        indicators = self.calculate_market_indicators(df)

        # Calculate bias
        print("🎯 Calculating market bias...")
        bias_data = self.calculate_bias_signals(df, indicators, stock_metrics)

        # Get current values
        current_close = df['Close'].iloc[-1]
        current_rsi = indicators['rsi'].iloc[-1]
        current_mfi = indicators['mfi'].iloc[-1]
        current_adx = indicators['adx'].iloc[-1]
        current_plus_di = indicators['plus_di'].iloc[-1]
        current_minus_di = indicators['minus_di'].iloc[-1]
        current_vwap = indicators['vwap'].iloc[-1]

        # Store results
        self.data = df
        self.indicators = indicators
        self.bias_data = bias_data
        self.market_condition = indicators['range_data']['condition']

        # Prepare comprehensive results
        results = {
            'timestamp': datetime.now(),
            'symbol': symbol,
            'current_price': current_close,
            'market_condition': self.market_condition,
            'market_bias': bias_data['market_bias'],
            'bias_data': bias_data,
            'indicators': {
                'rsi': current_rsi,
                'mfi': current_mfi,
                'adx': current_adx,
                'plus_di': current_plus_di,
                'minus_di': current_minus_di,
                'vwap': current_vwap
            },
            'range_data': indicators['range_data'],
            'stock_metrics': stock_metrics,
            'stock_data_table': stock_data_table,
            'us_market': us_market,
            'forex': forex
        }

        return results

    def display_results(self, results: Dict):
        """Display all results in formatted tables"""
        if not results:
            print("❌ No results to display")
            return

        print("\n" + "="*80)
        print("📊 STOCKS DASHBOARD")
        print("="*80)

        # Stocks table
        headers = ["Symbol", "LTP", "Change", "Change%", "15m%", "1h%", "Status"]
        print(tabulate(results['stock_data_table'], headers=headers, tablefmt="fancy_grid"))

        # Market averages
        print("\n" + "="*80)
        print("📈 MARKET AVERAGES")
        print("="*80)

        avg_table = [[
            "Market Avg",
            f"{results['bias_data']['weighted_avg_daily']:.2f}%",
            f"{results['bias_data']['weighted_avg_tf1']:.2f}%",
            f"{results['bias_data']['weighted_avg_tf2']:.2f}%"
        ]]

        if results.get('us_market'):
            avg_table.append([
                "US Market (DOW)",
                f"{results['us_market']['change_pct']:.2f}%",
                f"{results['us_market']['tf1_change_pct']:.2f}%",
                f"{results['us_market']['tf2_change_pct']:.2f}%"
            ])

        if results.get('forex'):
            avg_table.append([
                "USD/INR",
                f"{results['forex']['change_pct']:.2f}%",
                f"{results['forex']['tf1_change_pct']:.2f}%",
                f"{results['forex']['tf2_change_pct']:.2f}%"
            ])

        headers = ["Metric", "Daily", "15m", "1h"]
        print(tabulate(avg_table, headers=headers, tablefmt="fancy_grid"))

        # Indicators table
        print("\n" + "="*80)
        print("🔧 TECHNICAL INDICATORS")
        print("="*80)

        ind = results['indicators']

        # ADX interpretation
        adx_text = ""
        adx_val = ind['adx']
        if adx_val >= 25 and ind['plus_di'] > ind['minus_di']:
            adx_text = "Strong UP"
        elif adx_val >= 25 and ind['plus_di'] < ind['minus_di']:
            adx_text = "Strong Down"
        elif adx_val >= 20 and ind['plus_di'] > ind['minus_di']:
            adx_text = "UP"
        elif adx_val >= 20 and ind['plus_di'] < ind['minus_di']:
            adx_text = "Down"
        else:
            adx_text = "Neutral"

        # DI+ interpretation
        di_plus_text = "UP" if ind['plus_di'] >= 25 and ind['plus_di'] > ind['minus_di'] else "-"

        # DI- interpretation
        di_minus_text = "Down" if ind['minus_di'] >= 25 and ind['plus_di'] < ind['minus_di'] else "-"

        indicators_table = [
            ["VWAP", f"{ind['vwap']:.2f}", "▲" if results['current_price'] > ind['vwap'] else "▼"],
            ["RSI", f"{ind['rsi']:.2f}", "▲" if ind['rsi'] > 50 else "▼"],
            ["MFI", f"{ind['mfi']:.2f}", "▲" if ind['mfi'] > 50 else "▼"],
            ["ADX", f"{ind['adx']:.2f}", adx_text],
            ["DI+", f"{ind['plus_di']:.2f}", di_plus_text],
            ["DI-", f"{ind['minus_di']:.2f}", di_minus_text],
        ]

        headers = ["Indicator", "Value", "Signal"]
        print(tabulate(indicators_table, headers=headers, tablefmt="fancy_grid"))

        # Market condition
        print("\n" + "="*80)
        print("🎯 MARKET CONDITION")
        print("="*80)

        range_data = results['range_data']
        condition_table = [
            ["Condition", results['market_condition']],
            ["Movement Quality", range_data['movement_quality']],
            ["Range %", f"{range_data['range_pct']:.2f}%"],
            ["EMA Spread %", f"{range_data['ema_spread_pct']:.2f}%"],
            ["Movement Strength", f"{range_data['movement_strength']:.2f}"]
        ]

        if results['market_condition'] == "RANGE-BOUND":
            condition_table.extend([
                ["Range High", f"{range_data['range_high']:.2f}"],
                ["Range Low", f"{range_data['range_low']:.2f}"],
                ["Range Mid", f"{range_data['range_mid']:.2f}"]
            ])

        headers = ["Metric", "Value"]
        print(tabulate(condition_table, headers=headers, tablefmt="fancy_grid"))

        # Market bias - comprehensive
        print("\n" + "="*80)
        print("🎯 MARKET BIAS ANALYSIS")
        print("="*80)

        bias = results['bias_data']

        # Mode
        mode_text = "⚡ REVERSAL MODE" if bias['reversal_mode'] else "📊 NORMAL MODE"
        mode_emoji = "⚡" if bias['reversal_mode'] else "📊"

        bias_table = [
            ["Mode", mode_text],
            ["Market Bias", f"{bias['market_bias']} {self._get_bias_emoji(bias['market_bias'])}"],
            ["Bullish Bias %", f"{bias['bullish_bias_pct']:.1f}%"],
            ["Bearish Bias %", f"{bias['bearish_bias_pct']:.1f}%"],
            ["", ""],
            ["Fast Signals (Technical)", ""],
            ["  • Bullish %", f"{bias['fast_bull_pct']:.1f}%"],
            ["  • Bearish %", f"{bias['fast_bear_pct']:.1f}%"],
            ["", ""],
            ["Medium Signals (Price)", ""],
            ["  • Bullish %", f"{bias['medium_bull_pct']:.1f}%"],
            ["  • Bearish %", f"{bias['medium_bear_pct']:.1f}%"],
            ["", ""],
            ["Slow Signals (Stocks)", ""],
            ["  • Bullish %", f"{bias['slow_bull_pct']:.1f}%"],
            ["  • Bearish %", f"{bias['slow_bear_pct']:.1f}%"],
        ]

        if bias['divergence_detected']:
            bias_table.append(["", ""])
            if bias['bullish_divergence']:
                bias_table.append(["⚠️ ALERT", "BULLISH DIVERGENCE - REVERSAL UP POSSIBLE"])
            if bias['bearish_divergence']:
                bias_table.append(["⚠️ ALERT", "BEARISH DIVERGENCE - REVERSAL DOWN POSSIBLE"])

        headers = ["Metric", "Value"]
        print(tabulate(bias_table, headers=headers, tablefmt="fancy_grid"))

        # Trading signal
        print("\n" + "="*80)
        print("🎯 TRADING SIGNAL")
        print("="*80)

        self._display_trading_signal(results)

        print("\n" + "="*80)
        print(f"Analysis completed at: {results['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")

    def _get_bias_emoji(self, bias: str) -> str:
        """Get emoji for bias"""
        if bias == "BULLISH":
            return "🐂"
        elif bias == "BEARISH":
            return "🐻"
        else:
            return "⏸"

    def _display_trading_signal(self, results: Dict):
        """Display current trading signal"""
        bias = results['bias_data']['market_bias']
        condition = results['market_condition']

        if bias == "BULLISH":
            print("🐂 BULLISH SIGNAL")
            print("   Strategy: Wait for support level touch for LONG entry")
            if condition == "RANGE-BOUND":
                print(f"   Entry Zone: Near Range Low {results['range_data']['range_low']:.2f}")
                print(f"   Target: Range High {results['range_data']['range_high']:.2f}")
            else:
                print("   Entry: Wait for pivot support level")

        elif bias == "BEARISH":
            print("🐻 BEARISH SIGNAL")
            print("   Strategy: Wait for resistance level touch for SHORT entry")
            if condition == "RANGE-BOUND":
                print(f"   Entry Zone: Near Range High {results['range_data']['range_high']:.2f}")
                print(f"   Target: Range Low {results['range_data']['range_low']:.2f}")
            else:
                print("   Entry: Wait for pivot resistance level")

        else:
            print("⏸ NEUTRAL - NO CLEAR SIGNAL")
            print("   Strategy: Wait for clear bias formation")

        if results['bias_data']['divergence_detected']:
            print("\n   ⚠️ WARNING: Divergence detected - Reversal possible!")

        if condition == "RANGE-BOUND":
            print(f"\n   📦 Market is RANGE-BOUND")
            print(f"   Range trading recommended")


def main():
    """Main execution function"""
    # Initialize dashboard
    dashboard = SmartTradingDashboard()

    # Analyze Nifty 50
    print("\n🚀 Starting Smart Trading Dashboard Analysis...")
    results = dashboard.analyze_market('^NSEI')

    if results:
        # Display comprehensive results
        dashboard.display_results(results)

        # Return results for further processing
        return results
    else:
        print("❌ Analysis failed - no results")
        return None


if __name__ == "__main__":
    results = main()
