"""
Intraday Snapshot Manager for Option Chain Data
================================================

Tracks option chain snapshots at regular intervals to detect:
- Recent momentum changes (last 15 mins, 30 mins, 1 hour)
- Morning vs Afternoon bias shifts
- Intraday reversals
- Fresh OI building vs cumulative changes

Key Features:
- Stores snapshots every 15-30 minutes
- Calculates delta changes between snapshots
- Detects when recent momentum differs from full day trend
- Segments data by time periods (morning/afternoon)
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
from config import get_current_time_ist
import logging

logger = logging.getLogger(__name__)


class IntradaySnapshotManager:
    """Manages intraday snapshots of option chain data for momentum analysis"""

    # Session state keys
    SESSION_KEY_SNAPSHOTS = 'option_chain_intraday_snapshots'
    SESSION_KEY_LATEST = 'option_chain_latest_snapshot'

    # Snapshot intervals (in minutes)
    SNAPSHOT_INTERVAL = 15  # Store snapshot every 15 minutes

    # Time periods for segmentation
    MORNING_START = 9 * 60 + 15  # 9:15 AM in minutes
    MORNING_END = 12 * 60        # 12:00 PM
    AFTERNOON_START = 12 * 60    # 12:00 PM
    AFTERNOON_END = 15 * 60 + 30 # 3:30 PM

    def __init__(self):
        """Initialize the snapshot manager"""
        self._initialize_session_state()

    @staticmethod
    def _initialize_session_state():
        """Initialize session state for snapshots"""
        if IntradaySnapshotManager.SESSION_KEY_SNAPSHOTS not in st.session_state:
            st.session_state[IntradaySnapshotManager.SESSION_KEY_SNAPSHOTS] = {}

        if IntradaySnapshotManager.SESSION_KEY_LATEST not in st.session_state:
            st.session_state[IntradaySnapshotManager.SESSION_KEY_LATEST] = None

    def _get_time_period(self, timestamp: datetime) -> str:
        """
        Get time period for a timestamp

        Args:
            timestamp: Datetime object

        Returns:
            'morning' or 'afternoon'
        """
        minutes = timestamp.hour * 60 + timestamp.minute

        if self.MORNING_START <= minutes < self.MORNING_END:
            return 'morning'
        elif self.AFTERNOON_START <= minutes <= self.AFTERNOON_END:
            return 'afternoon'
        else:
            return 'other'

    def should_take_snapshot(self) -> bool:
        """
        Check if it's time to take a new snapshot

        Returns:
            True if snapshot should be taken
        """
        latest = st.session_state[self.SESSION_KEY_LATEST]

        if latest is None:
            return True

        # Check if enough time has passed since last snapshot
        if isinstance(latest, str):
            try:
                latest = datetime.fromisoformat(latest)
            except:
                return True

        now = datetime.now()
        time_diff = (now - latest).total_seconds() / 60  # Minutes

        return time_diff >= self.SNAPSHOT_INTERVAL

    def save_snapshot(self, symbol: str, option_chain_data: Dict):
        """
        Save an option chain snapshot

        Args:
            symbol: Trading symbol (NIFTY, SENSEX, etc.)
            option_chain_data: Raw option chain data with records
        """
        if not option_chain_data or not option_chain_data.get('success'):
            return

        try:
            now = datetime.now()
            time_period = self._get_time_period(now)

            # Extract key data from option chain
            records = option_chain_data.get('records', {})
            spot_price = option_chain_data.get('spot_price', 0)

            # Create snapshot structure
            snapshot = {
                'timestamp': now,
                'time_period': time_period,
                'spot_price': spot_price,
                'strikes': {}
            }

            # Store strike-wise data
            if isinstance(records, dict):
                for strike_key, strike_data in records.items():
                    if isinstance(strike_data, dict):
                        strike_price = strike_data.get('strikePrice', strike_data.get('strike_price', 0))

                        ce_data = strike_data.get('CE', {})
                        pe_data = strike_data.get('PE', {})

                        snapshot['strikes'][strike_price] = {
                            'ce_oi': ce_data.get('openInterest', 0),
                            'pe_oi': pe_data.get('openInterest', 0),
                            'ce_oi_change': ce_data.get('changeinOpenInterest', 0),
                            'pe_oi_change': pe_data.get('changeinOpenInterest', 0),
                            'ce_volume': ce_data.get('totalTradedVolume', 0),
                            'pe_volume': ce_data.get('totalTradedVolume', 0),
                            'ce_ltp': ce_data.get('lastPrice', 0),
                            'pe_ltp': pe_data.get('lastPrice', 0)
                        }

            # Store in session state
            if symbol not in st.session_state[self.SESSION_KEY_SNAPSHOTS]:
                st.session_state[self.SESSION_KEY_SNAPSHOTS][symbol] = []

            st.session_state[self.SESSION_KEY_SNAPSHOTS][symbol].append(snapshot)

            # Update latest snapshot time
            st.session_state[self.SESSION_KEY_LATEST] = now

            # Keep only last 50 snapshots (12+ hours of data at 15-min intervals)
            if len(st.session_state[self.SESSION_KEY_SNAPSHOTS][symbol]) > 50:
                st.session_state[self.SESSION_KEY_SNAPSHOTS][symbol] = \
                    st.session_state[self.SESSION_KEY_SNAPSHOTS][symbol][-50:]

            logger.info(f"Snapshot saved for {symbol} at {now.strftime('%H:%M:%S')}")

        except Exception as e:
            logger.error(f"Error saving snapshot for {symbol}: {str(e)}")

    def get_recent_change(self, symbol: str, minutes: int = 15) -> Optional[Dict]:
        """
        Calculate OI/Volume changes in the last N minutes

        Args:
            symbol: Trading symbol
            minutes: Lookback period in minutes (default: 15)

        Returns:
            Dictionary with recent changes or None
        """
        snapshots = st.session_state[self.SESSION_KEY_SNAPSHOTS].get(symbol, [])

        if len(snapshots) < 2:
            return None

        try:
            now = datetime.now()
            current_snapshot = snapshots[-1]

            # Find snapshot from N minutes ago
            target_time = now - timedelta(minutes=minutes)
            previous_snapshot = None

            for snapshot in reversed(snapshots[:-1]):
                snap_time = snapshot['timestamp']
                if isinstance(snap_time, str):
                    snap_time = datetime.fromisoformat(snap_time)

                if snap_time <= target_time:
                    previous_snapshot = snapshot
                    break

            if not previous_snapshot:
                # Use oldest available snapshot
                previous_snapshot = snapshots[0]

            # Calculate changes
            changes = {
                'period_minutes': minutes,
                'spot_change': current_snapshot['spot_price'] - previous_snapshot['spot_price'],
                'strikes': {}
            }

            # Calculate strike-wise changes
            for strike_price in current_snapshot['strikes'].keys():
                if strike_price in previous_snapshot['strikes']:
                    curr = current_snapshot['strikes'][strike_price]
                    prev = previous_snapshot['strikes'][strike_price]

                    changes['strikes'][strike_price] = {
                        'ce_oi_change': curr['ce_oi'] - prev['ce_oi'],
                        'pe_oi_change': curr['pe_oi'] - prev['pe_oi'],
                        'ce_volume_change': curr['ce_volume'] - prev['ce_volume'],
                        'pe_volume_change': curr['pe_volume'] - prev['pe_volume'],
                        'ce_price_change': curr['ce_ltp'] - prev['ce_ltp'],
                        'pe_price_change': curr['pe_ltp'] - prev['pe_ltp']
                    }

            return changes

        except Exception as e:
            logger.error(f"Error calculating recent change for {symbol}: {str(e)}")
            return None

    def get_period_bias(self, symbol: str, period: str = 'morning') -> Optional[Dict]:
        """
        Get bias for a specific time period (morning/afternoon)

        Args:
            symbol: Trading symbol
            period: 'morning' or 'afternoon'

        Returns:
            Dictionary with period bias data
        """
        snapshots = st.session_state[self.SESSION_KEY_SNAPSHOTS].get(symbol, [])

        if not snapshots:
            return None

        # Filter snapshots by period
        period_snapshots = [s for s in snapshots if s['time_period'] == period]

        if len(period_snapshots) < 2:
            return None

        try:
            first_snapshot = period_snapshots[0]
            last_snapshot = period_snapshots[-1]

            # Calculate aggregated changes for the period
            total_ce_oi_change = 0
            total_pe_oi_change = 0
            total_ce_volume = 0
            total_pe_volume = 0

            for strike_price in last_snapshot['strikes'].keys():
                if strike_price in first_snapshot['strikes']:
                    curr = last_snapshot['strikes'][strike_price]
                    prev = first_snapshot['strikes'][strike_price]

                    total_ce_oi_change += (curr['ce_oi'] - prev['ce_oi'])
                    total_pe_oi_change += (curr['pe_oi'] - prev['pe_oi'])
                    total_ce_volume += curr['ce_volume']
                    total_pe_volume += curr['pe_volume']

            # Determine bias
            bias_score = 0

            # OI Change bias
            if total_pe_oi_change > total_ce_oi_change:
                bias_score += 3  # Bullish
            elif total_ce_oi_change > total_pe_oi_change:
                bias_score -= 3  # Bearish

            # Volume bias
            if total_pe_volume > total_ce_volume:
                bias_score += 2
            elif total_ce_volume > total_pe_volume:
                bias_score -= 2

            if bias_score >= 3:
                bias = "BULLISH"
            elif bias_score <= -3:
                bias = "BEARISH"
            else:
                bias = "NEUTRAL"

            return {
                'period': period,
                'bias': bias,
                'bias_score': bias_score,
                'ce_oi_change': total_ce_oi_change,
                'pe_oi_change': total_pe_oi_change,
                'ce_volume': total_ce_volume,
                'pe_volume': total_pe_volume,
                'spot_change': last_snapshot['spot_price'] - first_snapshot['spot_price'],
                'start_time': first_snapshot['timestamp'],
                'end_time': last_snapshot['timestamp']
            }

        except Exception as e:
            logger.error(f"Error calculating period bias for {symbol}: {str(e)}")
            return None

    def detect_reversal(self, symbol: str) -> Optional[Dict]:
        """
        Detect if recent momentum differs from full day trend (reversal signal)

        Args:
            symbol: Trading symbol

        Returns:
            Dictionary with reversal detection data
        """
        # Get recent 15-min change
        recent_change = self.get_recent_change(symbol, minutes=15)

        # Get full session change
        full_change = self.get_recent_change(symbol, minutes=360)  # 6 hours

        if not recent_change or not full_change:
            return None

        try:
            # Calculate ATM strikes for focused analysis
            snapshots = st.session_state[self.SESSION_KEY_SNAPSHOTS].get(symbol, [])
            if not snapshots:
                return None

            spot_price = snapshots[-1]['spot_price']

            # Find ATM strike
            strike_intervals = {'NIFTY': 50, 'BANKNIFTY': 100, 'FINNIFTY': 50, 'SENSEX': 100}
            strike_interval = strike_intervals.get(symbol, 50)
            atm_strike = round(spot_price / strike_interval) * strike_interval

            # Get ATM ±2 strikes
            atm_strikes = [atm_strike + (i * strike_interval) for i in range(-2, 3)]

            # Calculate recent vs full day momentum
            recent_ce_oi = sum(recent_change['strikes'].get(s, {}).get('ce_oi_change', 0) for s in atm_strikes)
            recent_pe_oi = sum(recent_change['strikes'].get(s, {}).get('pe_oi_change', 0) for s in atm_strikes)

            full_ce_oi = sum(full_change['strikes'].get(s, {}).get('ce_oi_change', 0) for s in atm_strikes)
            full_pe_oi = sum(full_change['strikes'].get(s, {}).get('pe_oi_change', 0) for s in atm_strikes)

            # Determine trends
            recent_trend = "BULLISH" if recent_pe_oi > recent_ce_oi else "BEARISH" if recent_ce_oi > recent_pe_oi else "NEUTRAL"
            full_trend = "BULLISH" if full_pe_oi > full_ce_oi else "BEARISH" if full_ce_oi > full_pe_oi else "NEUTRAL"

            # Detect reversal
            is_reversal = (recent_trend != full_trend) and (recent_trend != "NEUTRAL") and (full_trend != "NEUTRAL")

            return {
                'is_reversal': is_reversal,
                'recent_trend': recent_trend,
                'full_day_trend': full_trend,
                'recent_ce_oi': recent_ce_oi,
                'recent_pe_oi': recent_pe_oi,
                'full_ce_oi': full_ce_oi,
                'full_pe_oi': full_pe_oi,
                'atm_strike': atm_strike
            }

        except Exception as e:
            logger.error(f"Error detecting reversal for {symbol}: {str(e)}")
            return None

    def get_snapshot_count(self, symbol: str) -> int:
        """Get number of stored snapshots for a symbol"""
        return len(st.session_state[self.SESSION_KEY_SNAPSHOTS].get(symbol, []))

    def clear_old_snapshots(self, hours: int = 24):
        """
        Clear snapshots older than specified hours

        Args:
            hours: Age threshold in hours
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)

        for symbol in st.session_state[self.SESSION_KEY_SNAPSHOTS].keys():
            snapshots = st.session_state[self.SESSION_KEY_SNAPSHOTS][symbol]

            # Filter out old snapshots
            st.session_state[self.SESSION_KEY_SNAPSHOTS][symbol] = [
                s for s in snapshots
                if (s['timestamp'] if isinstance(s['timestamp'], datetime)
                    else datetime.fromisoformat(s['timestamp'])) > cutoff_time
            ]

        logger.info(f"Cleared snapshots older than {hours} hours")

    def _get_latest_snapshot_time(self) -> Optional[datetime]:
        """Get the latest snapshot time across all symbols"""
        latest = st.session_state.get(self.SESSION_KEY_LATEST)
        if isinstance(latest, str):
            try:
                return datetime.fromisoformat(latest)
            except:
                return None
        return latest


# Global instance
def get_snapshot_manager() -> IntradaySnapshotManager:
    """
    Get or create global snapshot manager instance

    Returns:
        IntradaySnapshotManager instance
    """
    if 'global_snapshot_manager' not in st.session_state:
        st.session_state.global_snapshot_manager = IntradaySnapshotManager()

    return st.session_state.global_snapshot_manager
