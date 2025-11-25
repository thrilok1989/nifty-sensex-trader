"""
Ultimate Trading Application with DhanHQ API Integration
Optimized for Streamlit Cloud deployment with secrets management
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta
import time
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# Page configuration
st.set_page_config(
    page_title="Ultimate Trading App",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

class TelegramNotifier:
    """Handle Telegram notifications with cooling period"""
    
    def __init__(self, bot_token: str, chat_id: str, cooling_period: int = 600):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.cooling_period = cooling_period
        
        if 'last_notification' not in st.session_state:
            st.session_state.last_notification = {}
    
    def send_message(self, message: str, alert_type: str = "general"):
        """Send Telegram message with cooling period check"""
        current_time = time.time()
        
        if alert_type in st.session_state.last_notification:
            time_diff = current_time - st.session_state.last_notification[alert_type]
            if time_diff < self.cooling_period:
                remaining = int(self.cooling_period - time_diff)
                return False, f"Cooling period active: {remaining}s remaining"
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                st.session_state.last_notification[alert_type] = current_time
                return True, "Message sent successfully"
            else:
                return False, f"Failed: {response.text}"
                
        except Exception as e:
            return False, f"Error: {str(e)}"


class DhanDataFetcher:
    """Fetch market data from DhanHQ API"""
    
    def __init__(self, access_token: str, client_id: str):
        self.access_token = access_token
        self.client_id = client_id
        self.base_url = "https://api.dhan.co/v2"
        self.headers = {
            "access-token": access_token,
            "client-id": client_id,
            "Content-Type": "application/json"
        }
    
    def get_intraday_data(self, security_id: str, exchange_segment: str = "NSE_EQ", 
                          interval: str = "1", days_back: int = 5) -> pd.DataFrame:
        """Fetch intraday historical data"""
        try:
            to_date = datetime.now()
            from_date = to_date - timedelta(days=days_back)
            
            payload = {
                "securityId": security_id,
                "exchangeSegment": exchange_segment,
                "instrument": "EQUITY",
                "interval": interval,
                "fromDate": from_date.strftime("%Y-%m-%d 09:15:00"),
                "toDate": to_date.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            response = requests.post(
                f"{self.base_url}/charts/intraday",
                headers=self.headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                df = pd.DataFrame({
                    'timestamp': pd.to_datetime(data['timestamp'], unit='s'),
                    'open': data['open'],
                    'high': data['high'],
                    'low': data['low'],
                    'close': data['close'],
                    'volume': data['volume']
                })
                df.set_index('timestamp', inplace=True)
                return df
            else:
                st.error(f"API Error: {response.status_code} - {response.text}")
                return pd.DataFrame()
                
        except Exception as e:
            st.error(f"Error fetching data: {str(e)}")
            return pd.DataFrame()
    
    def get_ltp(self, security_id: str, exchange_segment: str = "NSE_EQ") -> Optional[float]:
        """Get Last Traded Price"""
        try:
            payload = {exchange_segment: [int(security_id)]}
            
            response = requests.post(
                f"{self.base_url}/marketfeed/ltp",
                headers=self.headers,
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                return data['data'][exchange_segment][security_id]['last_price']
            return None
            
        except Exception as e:
            st.error(f"Error getting LTP: {str(e)}")
            return None


class VolumeOrderBlocks:
    """Calculate Volume Order Blocks indicator"""
    
    def __init__(self, length1: int = 5):
        self.length1 = length1
        self.length2 = length1 + 13
    
    def calculate(self, df: pd.DataFrame) -> Dict:
        """Calculate Volume Order Blocks"""
        try:
            df = df.copy()
            df['ema1'] = df['close'].ewm(span=self.length1, adjust=False).mean()
            df['ema2'] = df['close'].ewm(span=self.length2, adjust=False).mean()
            
            df['cross_up'] = (df['ema1'] > df['ema2']) & (df['ema1'].shift(1) <= df['ema2'].shift(1))
            df['cross_dn'] = (df['ema1'] < df['ema2']) & (df['ema1'].shift(1) >= df['ema2'].shift(1))
            
            df['atr'] = self._calculate_atr(df, 200)
            
            bullish_blocks = []
            bearish_blocks = []
            
            for idx in df[df['cross_up']].index:
                pos = df.index.get_loc(idx)
                if pos >= self.length2:
                    window = df.iloc[pos-self.length2:pos+1]
                    lowest = window['low'].min()
                    lowest_idx = window['low'].idxmin()
                    
                    vol = window.loc[lowest_idx:idx, 'volume'].sum()
                    candle_at_low = df.loc[lowest_idx]
                    upper = min(candle_at_low['open'], candle_at_low['close'])
                    
                    if upper - lowest >= df.loc[idx, 'atr'] * 0.5:
                        mid = (upper + lowest) / 2
                        bullish_blocks.append({
                            'start_idx': lowest_idx,
                            'upper': upper,
                            'lower': lowest,
                            'mid': mid,
                            'volume': vol
                        })
            
            for idx in df[df['cross_dn']].index:
                pos = df.index.get_loc(idx)
                if pos >= self.length2:
                    window = df.iloc[pos-self.length2:pos+1]
                    highest = window['high'].max()
                    highest_idx = window['high'].idxmax()
                    
                    vol = window.loc[highest_idx:idx, 'volume'].sum()
                    candle_at_high = df.loc[highest_idx]
                    lower = max(candle_at_high['open'], candle_at_high['close'])
                    
                    if highest - lower >= df.loc[idx, 'atr'] * 0.5:
                        mid = (highest + lower) / 2
                        bearish_blocks.append({
                            'start_idx': highest_idx,
                            'upper': highest,
                            'lower': lower,
                            'mid': mid,
                            'volume': vol
                        })
            
            bullish_blocks = self._filter_overlapping(bullish_blocks, df)
            bearish_blocks = self._filter_overlapping(bearish_blocks, df)
            
            return {
                'bullish': bullish_blocks[-15:] if bullish_blocks else [],
                'bearish': bearish_blocks[-15:] if bearish_blocks else [],
                'ema1': df['ema1'],
                'ema2': df['ema2']
            }
            
        except Exception as e:
            st.error(f"Error in VOB calculation: {str(e)}")
            return {'bullish': [], 'bearish': [], 'ema1': pd.Series(), 'ema2': pd.Series()}
    
    def _calculate_atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Average True Range"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    def _filter_overlapping(self, blocks: List[Dict], df: pd.DataFrame) -> List[Dict]:
        """Remove overlapping blocks"""
        if len(blocks) <= 1:
            return blocks
        
        filtered = []
        atr = df['atr'].iloc[-1]
        
        for block in blocks:
            is_overlapping = False
            for existing in filtered:
                if abs(block['mid'] - existing['mid']) < atr * 3:
                    is_overlapping = True
                    break
            
            if not is_overlapping:
                filtered.append(block)
        
        return filtered


class HTFSupportResistance:
    """Calculate Higher Time Frame Support and Resistance levels"""
    
    def __init__(self, pivot_length: int = 5):
        self.pivot_length = pivot_length
    
    def calculate(self, df: pd.DataFrame, timeframes: List[str] = ['10T', '15T']) -> Dict:
        """Calculate HTF Support/Resistance levels"""
        try:
            levels = {}
            
            for tf in timeframes:
                htf_df = df.resample(tf).agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).dropna()
                
                pivot_highs = []
                pivot_lows = []
                
                for i in range(self.pivot_length, len(htf_df) - self.pivot_length):
                    window = htf_df['high'].iloc[i-self.pivot_length:i+self.pivot_length+1]
                    if htf_df['high'].iloc[i] == window.max():
                        pivot_highs.append({
                            'timestamp': htf_df.index[i],
                            'price': htf_df['high'].iloc[i],
                            'type': 'resistance'
                        })
                    
                    window = htf_df['low'].iloc[i-self.pivot_length:i+self.pivot_length+1]
                    if htf_df['low'].iloc[i] == window.min():
                        pivot_lows.append({
                            'timestamp': htf_df.index[i],
                            'price': htf_df['low'].iloc[i],
                            'type': 'support'
                        })
                
                levels[tf] = {
                    'resistance': pivot_highs[-10:] if pivot_highs else [],
                    'support': pivot_lows[-10:] if pivot_lows else []
                }
            
            return levels
            
        except Exception as e:
            st.error(f"Error in HTF calculation: {str(e)}")
            return {}


class VolumaticVIDYA:
    """Calculate Volumatic Variable Index Dynamic Average"""
    
    def __init__(self, vidya_length: int = 10, vidya_momentum: int = 20, band_distance: float = 2.0):
        self.vidya_length = vidya_length
        self.vidya_momentum = vidya_momentum
        self.band_distance = band_distance
    
    def calculate(self, df: pd.DataFrame) -> Dict:
        """Calculate VIDYA indicator"""
        try:
            vidya = self._calculate_vidya(df['close'], self.vidya_length, self.vidya_momentum)
            vidya_smoothed = vidya.rolling(window=15).mean()
            
            atr = self._calculate_atr(df, 200)
            
            upper_band = vidya_smoothed + atr * self.band_distance
            lower_band = vidya_smoothed - atr * self.band_distance
            
            trend = pd.Series(index=df.index, dtype=bool)
            trend.iloc[0] = df['close'].iloc[0] > upper_band.iloc[0]
            
            for i in range(1, len(df)):
                if df['close'].iloc[i] > upper_band.iloc[i]:
                    trend.iloc[i] = True
                elif df['close'].iloc[i] < lower_band.iloc[i]:
                    trend.iloc[i] = False
                else:
                    trend.iloc[i] = trend.iloc[i-1]
            
            smoothed_value = pd.Series(index=df.index, dtype=float)
            for i in range(len(df)):
                if trend.iloc[i]:
                    smoothed_value.iloc[i] = lower_band.iloc[i]
                else:
                    smoothed_value.iloc[i] = upper_band.iloc[i]
            
            return {
                'vidya': vidya_smoothed,
                'upper_band': upper_band,
                'lower_band': lower_band,
                'smoothed_value': smoothed_value,
                'trend': trend
            }
            
        except Exception as e:
            st.error(f"Error in VIDYA calculation: {str(e)}")
            return {}
    
    def _calculate_vidya(self, src: pd.Series, length: int, momentum: int) -> pd.Series:
        """Calculate Variable Index Dynamic Average"""
        momentum_values = src.diff()
        
        sum_pos = momentum_values.clip(lower=0).rolling(window=momentum).sum()
        sum_neg = (-momentum_values.clip(upper=0)).rolling(window=momentum).sum()
        
        cmo = 100 * (sum_pos - sum_neg) / (sum_pos + sum_neg)
        abs_cmo = cmo.abs()
        
        alpha = 2 / (length + 1)
        vidya = pd.Series(index=src.index, dtype=float)
        vidya.iloc[0] = src.iloc[0]
        
        for i in range(1, len(src)):
            if pd.notna(abs_cmo.iloc[i]):
                factor = alpha * abs_cmo.iloc[i] / 100
                vidya.iloc[i] = factor * src.iloc[i] + (1 - factor) * vidya.iloc[i-1]
            else:
                vidya.iloc[i] = vidya.iloc[i-1]
        
        return vidya
    
    def _calculate_atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Average True Range"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr


class UltimateRSI:
    """Calculate Ultimate RSI indicator"""
    
    def __init__(self, length: int = 14, smooth: int = 14, method1: str = 'RMA', method2: str = 'EMA'):
        self.length = length
        self.smooth = smooth
        self.method1 = method1
        self.method2 = method2
    
    def calculate(self, df: pd.DataFrame) -> Dict:
        """Calculate Ultimate RSI"""
        try:
            src = df['close']
            
            upper = src.rolling(window=self.length).max()
            lower = src.rolling(window=self.length).min()
            r = upper - lower
            
            d = src.diff()
            diff = pd.Series(index=src.index, dtype=float)
            
            for i in range(1, len(src)):
                if upper.iloc[i] > upper.iloc[i-1]:
                    diff.iloc[i] = r.iloc[i]
                elif lower.iloc[i] < lower.iloc[i-1]:
                    diff.iloc[i] = -r.iloc[i]
                else:
                    diff.iloc[i] = d.iloc[i]
            
            num = self._moving_average(diff, self.length, self.method1)
            den = self._moving_average(diff.abs(), self.length, self.method1)
            
            arsi = num / den * 50 + 50
            signal = self._moving_average(arsi, self.smooth, self.method2)
            
            return {
                'arsi': arsi,
                'signal': signal
            }
            
        except Exception as e:
            st.error(f"Error in RSI calculation: {str(e)}")
            return {}
    
    def _moving_average(self, src: pd.Series, length: int, ma_type: str) -> pd.Series:
        """Calculate moving average based on type"""
        if ma_type == 'EMA':
            return src.ewm(span=length, adjust=False).mean()
        elif ma_type == 'SMA':
            return src.rolling(window=length).mean()
        elif ma_type == 'RMA':
            return src.ewm(alpha=1/length, adjust=False).mean()
        elif ma_type == 'TMA':
            sma1 = src.rolling(window=length).mean()
            return sma1.rolling(window=length).mean()
        else:
            return src.rolling(window=length).mean()


class AlertManager:
    """Manage price alerts and notifications"""
    
    def __init__(self, notifier: Optional[TelegramNotifier], alert_distance: float = 5.0):
        self.notifier = notifier
        self.alert_distance = alert_distance
    
    def check_vob_alerts(self, current_price: float, vob_data: Dict, symbol: str):
        """Check if price is near Volume Order Blocks"""
        if not self.notifier:
            return
        
        try:
            for block in vob_data.get('bullish', []):
                distance_to_lower = abs(current_price - block['lower'])
                distance_to_upper = abs(current_price - block['upper'])
                distance_to_mid = abs(current_price - block['mid'])
                
                min_distance = min(distance_to_lower, distance_to_upper, distance_to_mid)
                
                if min_distance <= self.alert_distance:
                    volume_str = self._format_volume(block['volume'])
                    message = (
                        f"🟢 <b>Bullish VOB Alert - {symbol}</b>\n\n"
                        f"💰 Current Price: ₹{current_price:.2f}\n"
                        f"📊 VOB Range: ₹{block['lower']:.2f} - ₹{block['upper']:.2f}\n"
                        f"📍 Distance: {min_distance:.2f} points\n"
                        f"📈 Volume: {volume_str}\n"
                        f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}"
                    )
                    success, msg = self.notifier.send_message(message, f"vob_bull_{block['lower']}")
                    if success:
                        st.success(f"✅ Alert sent: Bullish VOB")
            
            for block in vob_data.get('bearish', []):
                distance_to_lower = abs(current_price - block['lower'])
                distance_to_upper = abs(current_price - block['upper'])
                distance_to_mid = abs(current_price - block['mid'])
                
                min_distance = min(distance_to_lower, distance_to_upper, distance_to_mid)
                
                if min_distance <= self.alert_distance:
                    volume_str = self._format_volume(block['volume'])
                    message = (
                        f"🔴 <b>Bearish VOB Alert - {symbol}</b>\n\n"
                        f"💰 Current Price: ₹{current_price:.2f}\n"
                        f"📊 VOB Range: ₹{block['lower']:.2f} - ₹{block['upper']:.2f}\n"
                        f"📍 Distance: {min_distance:.2f} points\n"
                        f"📉 Volume: {volume_str}\n"
                        f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}"
                    )
                    success, msg = self.notifier.send_message(message, f"vob_bear_{block['upper']}")
                    if success:
                        st.success(f"✅ Alert sent: Bearish VOB")
                    
        except Exception as e:
            st.error(f"Error checking VOB alerts: {str(e)}")
    
    def check_htf_alerts(self, current_price: float, htf_data: Dict, symbol: str):
        """Check if price is near HTF Support/Resistance"""
        if not self.notifier:
            return
        
        try:
            for timeframe, levels in htf_data.items():
                for level in levels.get('resistance', []):
                    distance = abs(current_price - level['price'])
                    
                    if distance <= self.alert_distance:
                        message = (
                            f"🔵 <b>HTF Resistance Alert - {symbol}</b>\n\n"
                            f"💰 Current Price: ₹{current_price:.2f}\n"
                            f"🚧 Resistance: ₹{level['price']:.2f}\n"
                            f"📍 Distance: {distance:.2f} points\n"
                            f"⏱ Timeframe: {timeframe}\n"
                            f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}"
                        )
                        success, msg = self.notifier.send_message(message, f"htf_res_{timeframe}_{level['price']}")
                        if success:
                            st.success(f"✅ Alert sent: HTF Resistance")
                
                for level in levels.get('support', []):
                    distance = abs(current_price - level['price'])
                    
                    if distance <= self.alert_distance:
                        message = (
                            f"🟡 <b>HTF Support Alert - {symbol}</b>\n\n"
                            f"💰 Current Price: ₹{current_price:.2f}\n"
                            f"🛡 Support: ₹{level['price']:.2f}\n"
                            f"📍 Distance: {distance:.2f} points\n"
                            f"⏱ Timeframe: {timeframe}\n"
                            f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}"
                        )
                        success, msg = self.notifier.send_message(message, f"htf_sup_{timeframe}_{level['price']}")
                        if success:
                            st.success(f"✅ Alert sent: HTF Support")
                        
        except Exception as e:
            st.error(f"Error checking HTF alerts: {str(e)}")
    
    def _format_volume(self, volume: float) -> str:
        """Format volume for display"""
        if volume >= 10000000:
            return f"{volume/10000000:.2f}Cr"
        elif volume >= 100000:
            return f"{volume/100000:.2f}L"
        elif volume >= 1000:
            return f"{volume/1000:.2f}K"
        else:
            return f"{volume:.0f}"


def create_chart(df: pd.DataFrame, vob_data: Dict, htf_data: Dict, 
                 vidya_data: Dict, rsi_data: Dict, symbol: str) -> go.Figure:
    """Create interactive TradingView-like chart"""
    
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=(f'{symbol} Price Chart', 'Ultimate RSI'),
        row_heights=[0.7, 0.3]
    )
    
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Price',
            increasing_line_color='#26a69a',
            decreasing_line_color='#ef5350'
        ),
        row=1, col=1
    )
    
    for block in vob_data.get('bullish', []):
        fig.add_hrect(
            y0=block['lower'], y1=block['upper'],
            fillcolor='rgba(38, 166, 154, 0.2)',
            line_width=0,
            row=1, col=1
        )
        fig.add_hline(
            y=block['mid'],
            line_dash="dash",
            line_color='#26a69a',
            line_width=1,
            row=1, col=1
        )
    
    for block in vob_data.get('bearish', []):
        fig.add_hrect(
            y0=block['lower'], y1=block['upper'],
            fillcolor='rgba(102, 38, 186, 0.2)',
            line_width=0,
            row=1, col=1
        )
        fig.add_hline(
            y=block['mid'],
            line_dash="dash",
            line_color='#6626ba',
            line_width=1,
            row=1, col=1
        )
    
    colors = {'10T': '#089981', '15T': '#f23645'}
    for tf, levels in htf_data.items():
        color = colors.get(tf, '#cccccc')
        
        for level in levels.get('resistance', []):
            fig.add_hline(
                y=level['price'],
                line_dash="solid",
                line_color=color,
                line_width=2,
                annotation_text=f"{tf} R",
                row=1, col=1
            )
        
        for level in levels.get('support', []):
            fig.add_hline(
                y=level['price'],
                line_dash="solid",
                line_color=color,
                line_width=2,
                annotation_text=f"{tf} S",
                row=1, col=1
            )
    
    if 'smoothed_value' in vidya_data and not vidya_data['smoothed_value'].empty:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=vidya_data['smoothed_value'],
                mode='lines',
                name='VIDYA',
                line=dict(color='#ff9800', width=2)
            ),
            row=1, col=1
        )
    
    if 'arsi' in rsi_data and not rsi_data['arsi'].empty:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=rsi_data['arsi'],
                mode='lines',
                name='Ultimate RSI',
                line=dict(color='silver', width=2)
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=rsi_data['signal'],
                mode='lines',
                name='Signal',
                line=dict(color='#ff5d00', width=1)
            ),
            row=2, col=1
        )
        
        fig.add_hline(y=80, line_dash="dash", line_color='#089981', row=2, col=1)
        fig.add_hline(y=50, line_dash="dash", line_color='gray', row=2, col=1)
        fig.add_hline(y=20, line_dash="dash", line_color='#f23645', row=2, col=1)
        
        fig.add_hrect(y0=80, y1=100, fillcolor='rgba(8, 153, 129, 0.1)', 
                      line_width=0, row=2, col=1)
        fig.add_hrect(y0=0, y1=20, fillcolor='rgba(242, 54, 69, 0.1)', 
                      line_width=0, row=2, col=1)
    
    fig.update_layout(
        title=f'{symbol} - Ultimate Trading Analysis',
        yaxis_title='Price',
        yaxis2_title='RSI',
        template='plotly_dark',
        height=800,
        showlegend=True,
        xaxis_rangeslider_visible=False
    )
    
    fig.update_xaxes(title_text="Time", row=2, col=1)
    fig.update_yaxes(title_text="Price (₹)", row=1, col=1)
    fig.update_yaxes(title_text="RSI", range=[0, 100], row=2, col=1)
    
    return fig


def main():
    """Main Streamlit application"""
    
    st.title("📈 Ultimate Trading Application")
    st.markdown("*Powered by DhanHQ API with Volume Order Blocks, HTF Levels, VIDYA & Ultimate RSI*")
    
    # Initialize session state
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = datetime.now()
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Try to get secrets, fallback to manual input
        try:
            access_token = st.secrets["dhan"]["access_token"]
            client_id = st.secrets["dhan"]["client_id"]
            st.success("✅ API credentials loaded from secrets")
        except:
            st.subheader("🔐 API Settings")
            access_token = st.text_input("DhanHQ Access Token", type="password")
            client_id = st.text_input("Client ID")
        
        # Telegram configuration
        try:
            telegram_token = st.secrets["telegram"]["bot_token"]
            telegram_chat_id = st.secrets["telegram"]["chat_id"]
            st.success("✅ Telegram credentials loaded from secrets")
        except:
            st.subheader("📱 Telegram Settings")
            telegram_token = st.text_input("Telegram Bot Token", type="password")
            telegram_chat_id = st.text_input("Telegram Chat ID")
        
        # Trading configuration
        st.subheader("📊 Trading Settings")
        
        # Quick select for NIFTY/SENSEX
        quick_select = st.selectbox("Quick Select", 
                                     ["NIFTY 50", "SENSEX", "BANK NIFTY", "Custom"],
                                     index=0)
        
        if quick_select == "NIFTY 50":
            security_id = "13"
            symbol = "NIFTY 50"
            exchange_segment = "IDX_I"
        elif quick_select == "SENSEX":
            security_id = "51"
            symbol = "SENSEX"
            exchange_segment = "IDX_I"
        elif quick_select == "BANK NIFTY":
            security_id = "25"
            symbol = "BANK NIFTY"
            exchange_segment = "IDX_I"
        else:
            security_id = st.text_input("Security ID", value="13")
            symbol = st.text_input("Symbol", value="NIFTY 50")
            exchange_segment = st.selectbox("Exchange Segment", ["IDX_I", "NSE_EQ", "NSE_FNO", "BSE_EQ"])
        
        # Alert configuration
        st.subheader("🔔 Alert Settings")
        alert_distance = st.number_input("Alert Distance (points)", value=5.0, min_value=1.0)
        
        # Auto-refresh
        st.subheader("🔄 Auto Refresh")
        auto_refresh = st.checkbox("Enable Auto Refresh (1 minute)", value=True)
        
        refresh_button = st.button("🔄 Refresh Now", use_container_width=True)
    
    # Check configuration
    if not access_token or not client_id:
        st.warning("⚠️ Please configure your DhanHQ API credentials")
        st.info("""
        **Setup Options:**
        
        1. **Using Streamlit Secrets** (Recommended for deployment):
           - Create `.streamlit/secrets.toml`
           - Add your credentials (see documentation)
        
        2. **Manual Entry**:
           - Enter credentials in the sidebar
        """)
        return
    
    # Auto-refresh logic
    if auto_refresh:
        time_since_refresh = (datetime.now() - st.session_state.last_refresh).total_seconds()
        if time_since_refresh >= 60 or refresh_button:
            st.session_state.last_refresh = datetime.now()
            st.rerun()
    
    # Initialize components
    try:
        dhan = DhanDataFetcher(access_token, client_id)
        
        notifier = None
        if telegram_token and telegram_chat_id:
            notifier = TelegramNotifier(telegram_token, telegram_chat_id)
        
        # Fetch data
        with st.spinner("📊 Fetching market data..."):
            df = dhan.get_intraday_data(security_id, exchange_segment, interval="1", days_back=5)
            
            if df.empty:
                st.error("❌ Failed to fetch data. Please check your credentials and security ID.")
                return
            
            current_price = dhan.get_ltp(security_id, exchange_segment)
            if current_price is None:
                current_price = df['close'].iloc[-1]
        
        # Calculate indicators
        with st.spinner("🔬 Calculating indicators..."):
            vob_calculator = VolumeOrderBlocks(length1=5)
            vob_data = vob_calculator.calculate(df)
            
            htf_calculator = HTFSupportResistance(pivot_length=5)
            htf_data = htf_calculator.calculate(df, timeframes=['10T', '15T'])
            
            vidya_calculator = VolumaticVIDYA(vidya_length=10, vidya_momentum=20, band_distance=2.0)
            vidya_data = vidya_calculator.calculate(df)
            
            rsi_calculator = UltimateRSI(length=14, smooth=14, method1='RMA', method2='EMA')
            rsi_data = rsi_calculator.calculate(df)
        
        # Check alerts
        if notifier:
            alert_manager = AlertManager(notifier, alert_distance)
            alert_manager.check_vob_alerts(current_price, vob_data, symbol)
            alert_manager.check_htf_alerts(current_price, htf_data, symbol)
        
        # Display metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            change = ((current_price - df['close'].iloc[-2]) / df['close'].iloc[-2] * 100)
            st.metric("Current Price", f"₹{current_price:.2f}", f"{change:.2f}%")
        
        with col2:
            st.metric("Volume", f"{df['volume'].iloc[-1]:,.0f}")
        
        with col3:
            if 'arsi' in rsi_data and not rsi_data['arsi'].empty:
                rsi_value = rsi_data['arsi'].iloc[-1]
                st.metric("Ultimate RSI", f"{rsi_value:.2f}")
        
        with col4:
            st.metric("Bullish VOBs", len(vob_data.get('bullish', [])))
        
        with col5:
            st.metric("Bearish VOBs", len(vob_data.get('bearish', [])))
        
        # Create and display chart
        with st.spinner("📈 Creating chart..."):
            fig = create_chart(df, vob_data, htf_data, vidya_data, rsi_data, symbol)
            st.plotly_chart(fig, use_container_width=True)
        
        # Display detailed information
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🟢 Bullish Volume Order Blocks")
            if vob_data.get('bullish'):
                for i, block in enumerate(vob_data['bullish'][-5:]):
                    with st.expander(f"Block #{i+1} - ₹{block['mid']:.2f}"):
                        st.write(f"**Upper:** ₹{block['upper']:.2f}")
                        st.write(f"**Lower:** ₹{block['lower']:.2f}")
                        st.write(f"**Volume:** {block['volume']:,.0f}")
                        distance = abs(current_price - block['mid'])
                        st.write(f"**Distance:** {distance:.2f} points")
            else:
                st.info("No bullish blocks detected")
        
        with col2:
            st.subheader("🔴 Bearish Volume Order Blocks")
            if vob_data.get('bearish'):
                for i, block in enumerate(vob_data['bearish'][-5:]):
                    with st.expander(f"Block #{i+1} - ₹{block['mid']:.2f}"):
                        st.write(f"**Upper:** ₹{block['upper']:.2f}")
                        st.write(f"**Lower:** ₹{block['lower']:.2f}")
                        st.write(f"**Volume:** {block['volume']:,.0f}")
                        distance = abs(current_price - block['mid'])
                        st.write(f"**Distance:** {distance:.2f} points")
            else:
                st.info("No bearish blocks detected")
        
        # HTF Levels
        st.subheader("📊 Higher Time Frame Levels")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**10-Minute Timeframe**")
            if '10T' in htf_data:
                levels = htf_data['10T']
                if levels.get('resistance'):
                    st.write("🚧 Resistance Levels:")
                    for level in levels['resistance'][-3:]:
                        distance = abs(current_price - level['price'])
                        st.write(f"  • ₹{level['price']:.2f} (Distance: {distance:.2f})")
                
                if levels.get('support'):
                    st.write("🛡 Support Levels:")
                    for level in levels['support'][-3:]:
                        distance = abs(current_price - level['price'])
                        st.write(f"  • ₹{level['price']:.2f} (Distance: {distance:.2f})")
        
        with col2:
            st.write("**15-Minute Timeframe**")
            if '15T' in htf_data:
                levels = htf_data['15T']
                if levels.get('resistance'):
                    st.write("🚧 Resistance Levels:")
                    for level in levels['resistance'][-3:]:
                        distance = abs(current_price - level['price'])
                        st.write(f"  • ₹{level['price']:.2f} (Distance: {distance:.2f})")
                
                if levels.get('support'):
                    st.write("🛡 Support Levels:")
                    for level in levels['support'][-3:]:
                        distance = abs(current_price - level['price'])
                        st.write(f"  • ₹{level['price']:.2f} (Distance: {distance:.2f})")
        
        # Footer
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.caption(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        with col2:
            st.caption(f"Data Points: {len(df)}")
        with col3:
            if auto_refresh:
                next_refresh = st.session_state.last_refresh + timedelta(seconds=60)
                seconds_remaining = int((next_refresh - datetime.now()).total_seconds())
                st.caption(f"Next Refresh: {max(0, seconds_remaining)}s")
        
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        st.exception(e)


if __name__ == "__main__":
    main()
