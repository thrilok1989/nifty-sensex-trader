"""
Higher Time Frame Support/Resistance Indicator
Converted from Pine Script by BigBeluga
"""

import pandas as pd
import numpy as np


class HTFSupportResistance:
    """
    Higher Time Frame Support/Resistance indicator that detects
    pivot highs and lows from multiple timeframes
    """

    def __init__(self):
        """Initialize HTF Support/Resistance indicator"""
        self.levels = []

    def calculate_pivots(self, df, timeframe, pivot_length, style='Solid', color='green'):
        """
        Calculate pivot levels for a specific timeframe

        Args:
            df: DataFrame with OHLCV data (should be resampled to target timeframe)
            timeframe: Timeframe string (e.g., '4H', 'D', 'W')
            pivot_length: Length for pivot detection
            style: Line style
            color: Level color

        Returns:
            dict: Dictionary containing pivot high and low levels
        """
        df = df.copy()

        # Calculate pivot highs and lows
        df['pivot_high'] = df['high'].rolling(window=pivot_length*2+1, center=True).apply(
            lambda x: x[pivot_length] if (len(x) == pivot_length*2+1 and
                                          x[pivot_length] == max(x)) else np.nan,
            raw=True
        )

        df['pivot_low'] = df['low'].rolling(window=pivot_length*2+1, center=True).apply(
            lambda x: x[pivot_length] if (len(x) == pivot_length*2+1 and
                                         x[pivot_length] == min(x)) else np.nan,
            raw=True
        )

        # Get the most recent pivot levels
        pivot_high_levels = df[df['pivot_high'].notna()]['pivot_high']
        pivot_low_levels = df[df['pivot_low'].notna()]['pivot_low']

        pivot_high = pivot_high_levels.iloc[-1] if len(pivot_high_levels) > 0 else None
        pivot_low = pivot_low_levels.iloc[-1] if len(pivot_low_levels) > 0 else None

        # Find the index where price last touched these levels
        pivot_high_touch_idx = None
        pivot_low_touch_idx = None

        if pivot_high is not None:
            # Find where price touched pivot high
            touches = df[(df['high'] >= pivot_high * 0.9999) & (df['high'] <= pivot_high * 1.0009)]
            if len(touches) > 0:
                pivot_high_touch_idx = touches.index[-1]

        if pivot_low is not None:
            # Find where price touched pivot low
            touches = df[(df['low'] >= pivot_low * 0.999) & (df['low'] <= pivot_low * 1.0009)]
            if len(touches) > 0:
                pivot_low_touch_idx = touches.index[-1]

        return {
            'timeframe': timeframe,
            'pivot_high': pivot_high,
            'pivot_low': pivot_low,
            'pivot_high_touch_idx': pivot_high_touch_idx,
            'pivot_low_touch_idx': pivot_low_touch_idx,
            'style': style,
            'color': color
        }

    def calculate_multi_timeframe(self, df_1min, levels_config):
        """
        Calculate support/resistance levels for multiple timeframes

        Args:
            df_1min: DataFrame with 1-minute OHLCV data
            levels_config: List of dicts with configuration for each level
                          [{'timeframe': '4H', 'length': 4, 'style': 'Solid', 'color': 'green'}, ...]

        Returns:
            list: List of pivot level dictionaries for all timeframes
        """
        all_levels = []

        for config in levels_config:
            timeframe = config['timeframe']
            pivot_length = config['length']
            style = config.get('style', 'Solid')
            color = config.get('color', 'green')

            # Resample data to target timeframe
            df_resampled = self._resample_dataframe(df_1min, timeframe)

            # Calculate pivots for this timeframe
            levels = self.calculate_pivots(df_resampled, timeframe, pivot_length, style, color)
            all_levels.append(levels)

        return all_levels

    def _resample_dataframe(self, df, timeframe):
        """
        Resample dataframe to target timeframe

        Args:
            df: DataFrame with datetime index
            timeframe: Target timeframe (e.g., '4H', 'D', 'W')

        Returns:
            DataFrame: Resampled dataframe
        """
        # Make a copy to avoid modifying original
        df = df.copy()

        # Ensure datetime index
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'timestamp' in df.columns:
                df = df.set_index('timestamp')
            elif 'datetime' in df.columns:
                df = df.set_index('datetime')
            else:
                # Try to convert index to datetime
                try:
                    df.index = pd.to_datetime(df.index)
                except Exception:
                    pass

        # Map Pine Script timeframes to pandas resample strings
        timeframe_map = {
            '240': '4H',
            '720': '12H',
            'D': 'D',
            'W': 'W',
            '1H': '1H',
            '4H': '4H',
            '12H': '12H',
            '3T': '3T',   # 3 minutes
            '5T': '5T',   # 5 minutes
            '10T': '10T', # 10 minutes
            '15T': '15T'  # 15 minutes
        }

        resample_freq = timeframe_map.get(timeframe, timeframe)

        # Resample
        df_resampled = df.resample(resample_freq).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()

        return df_resampled
