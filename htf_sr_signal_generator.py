"""
HTF Support/Resistance Signal Generator

Generates trading signals based on:
1. Overall market sentiment (BULLISH/BEARISH)
2. Spot price proximity to HTF support/resistance levels (within 8 points)
3. Multiple timeframes: 5min, 10min, 15min
4. Automatic entry and stop loss calculation
"""

from datetime import datetime
from typing import Dict, List, Optional


class HTFSRSignalGenerator:
    """
    Generates trading signals based on HTF Support/Resistance levels and market sentiment
    """

    def __init__(self, proximity_threshold: float = 8.0):
        """
        Initialize HTF S/R Signal Generator

        Args:
            proximity_threshold: Distance from S/R level to trigger signal (default 8 points)
        """
        self.proximity_threshold = proximity_threshold
        self.last_signal = None
        self.signal_history = []
        # Timeframes to monitor
        self.monitored_timeframes = ['5T', '10T', '15T']

    def check_for_signal(self,
                        spot_price: float,
                        market_sentiment: str,
                        htf_levels: List[Dict],
                        index: str = "NIFTY") -> Optional[Dict]:
        """
        Check if conditions are met for a trading signal based on HTF S/R levels

        Args:
            spot_price: Current spot price
            market_sentiment: Overall market sentiment ("BULLISH", "BEARISH", "NEUTRAL")
            htf_levels: List of HTF S/R levels from multiple timeframes
            index: Index name (NIFTY or SENSEX)

        Returns:
            Signal dictionary if conditions met, None otherwise
        """
        signal = None

        # Filter to only monitored timeframes (5min, 10min, 15min)
        filtered_levels = [
            level for level in htf_levels
            if level.get('timeframe') in self.monitored_timeframes
        ]

        # Check for BULLISH signal (price above and near support)
        if market_sentiment == "BULLISH":
            signal = self._check_bullish_signal(spot_price, filtered_levels, index)

        # Check for BEARISH signal (price below and near resistance)
        elif market_sentiment == "BEARISH":
            signal = self._check_bearish_signal(spot_price, filtered_levels, index)

        # Store signal if generated
        if signal:
            self.last_signal = signal
            self.signal_history.append(signal)
            # Keep only last 50 signals
            if len(self.signal_history) > 50:
                self.signal_history = self.signal_history[-50:]

        return signal

    def _check_bullish_signal(self, spot_price: float, htf_levels: List[Dict], index: str) -> Optional[Dict]:
        """
        Check for bullish entry signal

        Conditions:
        - Spot price is above and within 8 points of HTF support (pivot_low)
        - Market sentiment is BULLISH

        Returns:
            Signal dict with entry, stop loss, and target levels
        """
        for level in reversed(htf_levels):  # Check most recent timeframes first
            pivot_low = level.get('pivot_low')

            if pivot_low is None or pivot_low == 0:
                continue

            # Check if price is above support and within proximity threshold
            distance_from_support = spot_price - pivot_low

            # Signal condition: Price is above support and within 8 points
            if 0 <= distance_from_support <= self.proximity_threshold:
                # Calculate levels
                entry_price = spot_price
                stop_loss = pivot_low - self.proximity_threshold

                # Target is 1.5x the risk (simple R:R of 1:1.5)
                risk = entry_price - stop_loss
                target = entry_price + (risk * 1.5)

                signal = {
                    'index': index,
                    'direction': 'CALL',
                    'signal_type': 'HTF_SR_BULL_ENTRY',
                    'entry_price': round(entry_price, 2),
                    'stop_loss': round(stop_loss, 2),
                    'target': round(target, 2),
                    'support_level': round(pivot_low, 2),
                    'resistance_level': round(level.get('pivot_high', 0), 2) if level.get('pivot_high') else None,
                    'timeframe': level.get('timeframe'),
                    'distance_from_level': round(distance_from_support, 2),
                    'risk_reward': '1:1.5',
                    'market_sentiment': 'BULLISH',
                    'timestamp': datetime.now(),
                    'status': 'ACTIVE'
                }

                return signal

        return None

    def _check_bearish_signal(self, spot_price: float, htf_levels: List[Dict], index: str) -> Optional[Dict]:
        """
        Check for bearish entry signal

        Conditions:
        - Spot price is below and within 8 points of HTF resistance (pivot_high)
        - Market sentiment is BEARISH

        Returns:
            Signal dict with entry, stop loss, and target levels
        """
        for level in reversed(htf_levels):  # Check most recent timeframes first
            pivot_high = level.get('pivot_high')

            if pivot_high is None or pivot_high == 0:
                continue

            # Check if price is below resistance and within proximity threshold
            distance_from_resistance = pivot_high - spot_price

            # Signal condition: Price is below resistance and within 8 points
            if 0 <= distance_from_resistance <= self.proximity_threshold:
                # Calculate levels
                entry_price = spot_price
                stop_loss = pivot_high + self.proximity_threshold

                # Target is 1.5x the risk (simple R:R of 1:1.5)
                risk = stop_loss - entry_price
                target = entry_price - (risk * 1.5)

                signal = {
                    'index': index,
                    'direction': 'PUT',
                    'signal_type': 'HTF_SR_BEAR_ENTRY',
                    'entry_price': round(entry_price, 2),
                    'stop_loss': round(stop_loss, 2),
                    'target': round(target, 2),
                    'resistance_level': round(pivot_high, 2),
                    'support_level': round(level.get('pivot_low', 0), 2) if level.get('pivot_low') else None,
                    'timeframe': level.get('timeframe'),
                    'distance_from_level': round(distance_from_resistance, 2),
                    'risk_reward': '1:1.5',
                    'market_sentiment': 'BEARISH',
                    'timestamp': datetime.now(),
                    'status': 'ACTIVE'
                }

                return signal

        return None

    def get_last_signal(self) -> Optional[Dict]:
        """Get the last generated signal"""
        return self.last_signal

    def get_signal_history(self, limit: int = 10) -> List[Dict]:
        """
        Get recent signal history

        Args:
            limit: Number of recent signals to return

        Returns:
            List of recent signals
        """
        return self.signal_history[-limit:]

    def clear_history(self):
        """Clear signal history"""
        self.signal_history = []
        self.last_signal = None
