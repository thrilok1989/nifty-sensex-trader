"""
Advanced Proximity Alert System
Monitors price proximity to VOB and HTF levels and sends Telegram notifications
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
from notification_rate_limiter import get_rate_limiter
from telegram_alerts import TelegramBot

class ProximityAlert:
    """Represents a single proximity alert"""

    def __init__(self, symbol: str, alert_type: str, level: float,
                 level_type: str, distance: float, timeframe: str = None):
        """
        Initialize proximity alert

        Args:
            symbol: Trading symbol (NIFTY/SENSEX)
            alert_type: 'VOB' or 'HTF'
            level: Price level (support/resistance)
            level_type: 'Bull', 'Bear', 'Support', 'Resistance'
            distance: Points away from level
            timeframe: For HTF alerts (10T, 15T)
        """
        self.symbol = symbol
        self.alert_type = alert_type
        self.level = level
        self.level_type = level_type
        self.distance = distance
        self.timeframe = timeframe
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'symbol': self.symbol,
            'alert_type': self.alert_type,
            'level': self.level,
            'level_type': self.level_type,
            'distance': self.distance,
            'timeframe': self.timeframe,
            'timestamp': self.timestamp.isoformat()
        }


class AdvancedProximityAlertSystem:
    """
    Advanced alert system for monitoring price proximity to key levels
    - VOB levels: 7 points threshold
    - HTF S/R levels: 5 points threshold (10min & 15min only)
    - Rate limited: 10 minutes between notifications
    """

    # Thresholds
    VOB_PROXIMITY_THRESHOLD = 7.0  # Points
    HTF_PROXIMITY_THRESHOLD = 5.0  # Points

    # Monitored HTF timeframes
    HTF_MONITORED_TIMEFRAMES = ['10T', '15T']

    def __init__(self, cooldown_minutes: int = 10):
        """
        Initialize the alert system

        Args:
            cooldown_minutes: Cooldown period between notifications
        """
        self.rate_limiter = get_rate_limiter(cooldown_minutes=cooldown_minutes)
        self.telegram = TelegramBot()

        # Track active alerts
        self.active_alerts: List[ProximityAlert] = []

    def check_vob_proximity(self, symbol: str, current_price: float,
                           vob_data: Dict) -> List[ProximityAlert]:
        """
        Check if current price is near any VOB levels (within 7 points)

        Args:
            symbol: Trading symbol
            current_price: Current market price
            vob_data: VOB data from volume_order_blocks.py

        Returns:
            List of proximity alerts detected
        """
        alerts = []

        if not vob_data:
            return alerts

        # Check bullish VOB blocks
        for block in vob_data.get('bullish_blocks', []):
            if not block.get('active', True):
                continue

            # Check proximity to upper, mid, and lower levels
            levels = {
                'upper': block['upper'],
                'mid': block['mid'],
                'lower': block['lower']
            }

            for level_name, level_value in levels.items():
                distance = abs(current_price - level_value)

                if distance <= self.VOB_PROXIMITY_THRESHOLD:
                    alert = ProximityAlert(
                        symbol=symbol,
                        alert_type='VOB',
                        level=level_value,
                        level_type=f'Bull ({level_name})',
                        distance=distance
                    )
                    alerts.append(alert)

        # Check bearish VOB blocks
        for block in vob_data.get('bearish_blocks', []):
            if not block.get('active', True):
                continue

            levels = {
                'upper': block['upper'],
                'mid': block['mid'],
                'lower': block['lower']
            }

            for level_name, level_value in levels.items():
                distance = abs(current_price - level_value)

                if distance <= self.VOB_PROXIMITY_THRESHOLD:
                    alert = ProximityAlert(
                        symbol=symbol,
                        alert_type='VOB',
                        level=level_value,
                        level_type=f'Bear ({level_name})',
                        distance=distance
                    )
                    alerts.append(alert)

        return alerts

    def check_htf_proximity(self, symbol: str, current_price: float,
                           htf_data: List[Dict]) -> List[ProximityAlert]:
        """
        Check if current price is near HTF support/resistance (within 5 points)
        Only monitors 10min and 15min timeframes

        Args:
            symbol: Trading symbol
            current_price: Current market price
            htf_data: HTF S/R data from htf_support_resistance.py

        Returns:
            List of proximity alerts detected
        """
        alerts = []

        if not htf_data:
            return alerts

        for level_data in htf_data:
            timeframe = level_data.get('timeframe', '')

            # Only monitor 10T and 15T timeframes
            if timeframe not in self.HTF_MONITORED_TIMEFRAMES:
                continue

            # Check resistance (pivot high)
            if 'pivot_high' in level_data and level_data['pivot_high'] is not None:
                resistance = level_data['pivot_high']
                distance = abs(current_price - resistance)

                if distance <= self.HTF_PROXIMITY_THRESHOLD:
                    alert = ProximityAlert(
                        symbol=symbol,
                        alert_type='HTF',
                        level=resistance,
                        level_type='Resistance',
                        distance=distance,
                        timeframe=timeframe
                    )
                    alerts.append(alert)

            # Check support (pivot low)
            if 'pivot_low' in level_data and level_data['pivot_low'] is not None:
                support = level_data['pivot_low']
                distance = abs(current_price - support)

                if distance <= self.HTF_PROXIMITY_THRESHOLD:
                    alert = ProximityAlert(
                        symbol=symbol,
                        alert_type='HTF',
                        level=support,
                        level_type='Support',
                        distance=distance,
                        timeframe=timeframe
                    )
                    alerts.append(alert)

        return alerts

    def send_proximity_alert(self, alert: ProximityAlert, current_price: float) -> bool:
        """
        Send Telegram notification for proximity alert (if rate limit allows)

        Args:
            alert: ProximityAlert object
            current_price: Current market price

        Returns:
            True if notification was sent, False if rate limited
        """
        if not self.telegram.enabled:
            return False

        # Create alert key for rate limiting
        alert_key = f"{alert.alert_type.lower()}_proximity"

        # Check rate limit
        if not self.rate_limiter.can_send_notification(
            alert_type=alert_key,
            symbol=alert.symbol,
            level=alert.level
        ):
            # Get time remaining
            seconds_remaining = self.rate_limiter.get_time_until_next_notification(
                alert_type=alert_key,
                symbol=alert.symbol,
                level=alert.level
            )

            if seconds_remaining:
                minutes_remaining = seconds_remaining // 60
                print(f"Rate limited: {alert.symbol} {alert.alert_type} @ {alert.level:.2f} "
                      f"(next notification in {minutes_remaining} min)")

            return False

        # Build notification message
        message = self._build_alert_message(alert, current_price)

        # Send Telegram notification
        try:
            success = self.telegram.send_message(message)

            if success:
                # Record notification
                self.rate_limiter.record_notification(
                    alert_type=alert_key,
                    symbol=alert.symbol,
                    level=alert.level
                )
                print(f"Sent proximity alert: {alert.symbol} {alert.alert_type} @ {alert.level:.2f}")
                return True
            else:
                print(f"Failed to send proximity alert: {alert.symbol} {alert.alert_type}")
                return False

        except Exception as e:
            print(f"Error sending proximity alert: {e}")
            return False

    def _build_alert_message(self, alert: ProximityAlert, current_price: float) -> str:
        """
        Build formatted Telegram message for proximity alert

        Args:
            alert: ProximityAlert object
            current_price: Current market price

        Returns:
            Formatted HTML message
        """
        # Determine emoji based on alert type
        if alert.alert_type == 'VOB':
            if 'Bull' in alert.level_type:
                emoji = "🟢"
                direction = "BULLISH VOB"
            else:
                emoji = "🔴"
                direction = "BEARISH VOB"
        else:  # HTF
            if alert.level_type == 'Support':
                emoji = "🟢"
                direction = "HTF SUPPORT"
            else:
                emoji = "🔴"
                direction = "HTF RESISTANCE"

        # Build message
        lines = [
            f"{emoji} <b>PROXIMITY ALERT</b> {emoji}",
            "",
            f"<b>Symbol:</b> {alert.symbol}",
            f"<b>Type:</b> {direction}",
            f"<b>Level:</b> {alert.level:.2f}",
            f"<b>Current Price:</b> {current_price:.2f}",
            f"<b>Distance:</b> {alert.distance:.2f} points",
        ]

        if alert.timeframe:
            # Convert timeframe to readable format
            tf_readable = alert.timeframe.replace('T', 'm')
            lines.append(f"<b>Timeframe:</b> {tf_readable}")

        if alert.alert_type == 'VOB':
            lines.append(f"<b>Level Type:</b> {alert.level_type}")

        lines.extend([
            "",
            f"<i>Time: {alert.timestamp.strftime('%I:%M:%S %p')}</i>"
        ])

        return "\n".join(lines)

    def process_market_data(self, symbol: str, current_price: float,
                           vob_data: Dict, htf_data: List[Dict]) -> Tuple[List[ProximityAlert], int]:
        """
        Process market data and check for proximity alerts

        Args:
            symbol: Trading symbol
            current_price: Current market price
            vob_data: VOB block data
            htf_data: HTF support/resistance data

        Returns:
            Tuple of (all_alerts, notifications_sent)
        """
        all_alerts = []
        notifications_sent = 0

        # Check VOB proximity
        vob_alerts = self.check_vob_proximity(symbol, current_price, vob_data)
        all_alerts.extend(vob_alerts)

        # Check HTF proximity
        htf_alerts = self.check_htf_proximity(symbol, current_price, htf_data)
        all_alerts.extend(htf_alerts)

        # Send notifications (rate limited)
        for alert in all_alerts:
            if self.send_proximity_alert(alert, current_price):
                notifications_sent += 1

        return all_alerts, notifications_sent

    def get_alert_summary(self, alerts: List[ProximityAlert]) -> str:
        """
        Get summary of active alerts

        Args:
            alerts: List of proximity alerts

        Returns:
            Summary string
        """
        if not alerts:
            return "No proximity alerts"

        vob_count = sum(1 for a in alerts if a.alert_type == 'VOB')
        htf_count = sum(1 for a in alerts if a.alert_type == 'HTF')

        return f"Active: {len(alerts)} alerts (VOB: {vob_count}, HTF: {htf_count})"

    def clear_old_rate_limit_entries(self, days: int = 7):
        """
        Clear old rate limit entries

        Args:
            days: Clear entries older than this many days
        """
        self.rate_limiter.clear_old_entries(days_old=days)


# Global instance
_proximity_alert_system = None

def get_proximity_alert_system(cooldown_minutes: int = 10) -> AdvancedProximityAlertSystem:
    """
    Get or create global proximity alert system

    Args:
        cooldown_minutes: Cooldown period between notifications

    Returns:
        AdvancedProximityAlertSystem instance
    """
    global _proximity_alert_system
    if _proximity_alert_system is None:
        _proximity_alert_system = AdvancedProximityAlertSystem(cooldown_minutes=cooldown_minutes)
    return _proximity_alert_system
