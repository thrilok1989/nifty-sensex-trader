"""
Auto Trade Manager

Manages automatic trade execution with risk management and safety controls.

Features:
- Trade validation and filtering
- Position tracking and duplicate prevention
- Risk management (max trades, max loss, position limits)
- Trade cooldown management
- Comprehensive logging
- Demo mode support
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import os
from config import (
    AUTO_TRADE_ENABLED, AUTO_TRADE_CONFIG, AUTO_TRADE_SIGNALS,
    AUTO_TRADE_SAFETY, IST, get_current_time_ist, LOT_SIZES
)
from trade_executor import TradeExecutor
from telegram_alerts import TelegramBot
import streamlit as st


class AutoTradeManager:
    """Manages automatic trade execution with comprehensive risk controls"""

    def __init__(self):
        """Initialize Auto Trade Manager"""
        self.executor = TradeExecutor()
        self.telegram = TelegramBot()

        # Initialize session state for tracking
        if 'auto_trade_state' not in st.session_state:
            st.session_state.auto_trade_state = {
                'trades_today': [],
                'active_positions': [],
                'daily_pnl': 0.0,
                'last_trade_time': {},
                'total_trades': 0,
                'successful_trades': 0,
                'failed_trades': 0,
                'skipped_signals': 0,
                'errors': [],
                'is_enabled': False,
                'last_reset_date': get_current_time_ist().date()
            }

        # Reset daily counters if new day
        self._check_daily_reset()

    def _check_daily_reset(self):
        """Reset daily counters at start of new trading day"""
        current_date = get_current_time_ist().date()
        if st.session_state.auto_trade_state['last_reset_date'] != current_date:
            st.session_state.auto_trade_state['trades_today'] = []
            st.session_state.auto_trade_state['daily_pnl'] = 0.0
            st.session_state.auto_trade_state['last_trade_time'] = {}
            st.session_state.auto_trade_state['last_reset_date'] = current_date

    def is_enabled(self) -> bool:
        """Check if auto-trading is enabled"""
        return (AUTO_TRADE_ENABLED and
                st.session_state.auto_trade_state.get('is_enabled', False))

    def enable(self):
        """Enable auto-trading"""
        st.session_state.auto_trade_state['is_enabled'] = True
        self._log_decision("AUTO_TRADE_ENABLED", "Auto-trading enabled by user")

    def disable(self, reason: str = "User disabled"):
        """Disable auto-trading"""
        st.session_state.auto_trade_state['is_enabled'] = False
        self._log_decision("AUTO_TRADE_DISABLED", f"Auto-trading disabled: {reason}")

    def process_signal(self, signal: Dict, nifty_price: float, expiry_date: str,
                      signal_source: str = "VOB") -> Dict:
        """
        Process a trading signal and decide whether to execute

        Args:
            signal: Signal dictionary from signal generator
            nifty_price: Current NIFTY price
            expiry_date: Current expiry date
            signal_source: Source of signal (VOB, HTF_SR, MANUAL)

        Returns:
            Result dictionary with decision and action taken
        """

        # Check if auto-trading is enabled
        if not self.is_enabled():
            return self._skip_signal(signal, "Auto-trading disabled")

        # Check if this signal source is enabled
        source_key = f"{signal_source.lower()}_signals"
        if not AUTO_TRADE_SIGNALS.get(source_key, False):
            return self._skip_signal(signal, f"{signal_source} signals disabled in config")

        # Run validation checks
        validation_result = self._validate_signal(signal, signal_source)
        if not validation_result['valid']:
            return self._skip_signal(signal, validation_result['reason'])

        # Check risk management rules
        risk_check = self._check_risk_management(signal)
        if not risk_check['passed']:
            return self._skip_signal(signal, risk_check['reason'])

        # Check trade cooldown
        cooldown_check = self._check_cooldown(signal)
        if not cooldown_check['passed']:
            return self._skip_signal(signal, cooldown_check['reason'])

        # All checks passed - prepare to execute trade
        self._log_decision("TRADE_APPROVED", f"Signal approved for execution: {signal['index']} {signal['direction']}")

        # Convert signal to setup format for trade executor
        setup = self._signal_to_setup(signal)

        # Execute trade
        return self._execute_trade(setup, signal, nifty_price, expiry_date, signal_source)

    def _validate_signal(self, signal: Dict, signal_source: str) -> Dict:
        """
        Validate signal quality and requirements

        Returns:
            Dict with 'valid' boolean and 'reason' string
        """

        # Check required fields
        required_fields = ['index', 'direction', 'entry_price', 'stop_loss', 'target']
        for field in required_fields:
            if field not in signal:
                return {'valid': False, 'reason': f"Missing required field: {field}"}

        # Check risk-reward ratio
        entry = signal['entry_price']
        sl = signal['stop_loss']
        target = signal['target']

        if signal['direction'] == 'CALL':
            risk = entry - sl
            reward = target - entry
        else:  # PUT
            risk = sl - entry
            reward = entry - target

        if risk <= 0:
            return {'valid': False, 'reason': "Invalid risk calculation (risk <= 0)"}

        rr_ratio = reward / risk if risk > 0 else 0
        min_rr = AUTO_TRADE_CONFIG.get('min_risk_reward_ratio', 1.5)

        if rr_ratio < min_rr:
            return {'valid': False, 'reason': f"R:R ratio {rr_ratio:.2f} below minimum {min_rr}"}

        # Check sentiment confirmation if required
        if AUTO_TRADE_CONFIG.get('require_sentiment_confirmation', True):
            signal_sentiment = signal.get('market_sentiment', 'NEUTRAL')
            signal_direction = signal['direction']

            if signal_direction == 'CALL' and signal_sentiment != 'BULLISH':
                return {'valid': False, 'reason': f"CALL signal requires BULLISH sentiment (got {signal_sentiment})"}
            elif signal_direction == 'PUT' and signal_sentiment != 'BEARISH':
                return {'valid': False, 'reason': f"PUT signal requires BEARISH sentiment (got {signal_sentiment})"}

        return {'valid': True, 'reason': 'Signal validated successfully'}

    def _check_risk_management(self, signal: Dict) -> Dict:
        """
        Check risk management rules

        Returns:
            Dict with 'passed' boolean and 'reason' string
        """

        # Check max trades per day
        max_trades = AUTO_TRADE_CONFIG.get('max_trades_per_day', 5)
        trades_today = len(st.session_state.auto_trade_state['trades_today'])

        if trades_today >= max_trades:
            return {'passed': False, 'reason': f"Max trades per day reached ({max_trades})"}

        # Check max concurrent positions
        max_positions = AUTO_TRADE_CONFIG.get('max_concurrent_positions', 2)
        active_positions = len(st.session_state.auto_trade_state['active_positions'])

        if active_positions >= max_positions:
            return {'passed': False, 'reason': f"Max concurrent positions reached ({max_positions})"}

        # Check max daily loss
        max_loss = AUTO_TRADE_CONFIG.get('max_daily_loss', 5000)
        daily_pnl = st.session_state.auto_trade_state['daily_pnl']

        if daily_pnl <= -max_loss:
            self.disable("Max daily loss limit reached")
            return {'passed': False, 'reason': f"Daily loss limit reached (₹{max_loss})"}

        # Check for duplicate strikes if not allowed
        if not AUTO_TRADE_CONFIG.get('allow_duplicate_strikes', False):
            # Calculate strike for this signal
            from strike_calculator import calculate_strike
            strike_info = calculate_strike(
                signal['index'],
                signal['entry_price'],
                signal['direction'],
                ""  # Expiry not needed for strike calculation
            )
            new_strike = strike_info['strike']

            # Check if we already have this strike
            for position in st.session_state.auto_trade_state['active_positions']:
                if position.get('strike') == new_strike and position.get('index') == signal['index']:
                    return {'passed': False, 'reason': f"Duplicate strike position exists: {new_strike}"}

        return {'passed': True, 'reason': 'Risk management checks passed'}

    def _check_cooldown(self, signal: Dict) -> Dict:
        """
        Check trade cooldown period

        Returns:
            Dict with 'passed' boolean and 'reason' string
        """
        cooldown_minutes = AUTO_TRADE_CONFIG.get('trade_cooldown_minutes', 15)
        if cooldown_minutes <= 0:
            return {'passed': True, 'reason': 'No cooldown configured'}

        # Create key for this index and direction
        cooldown_key = f"{signal['index']}_{signal['direction']}"
        last_trade_times = st.session_state.auto_trade_state['last_trade_time']

        if cooldown_key in last_trade_times:
            last_trade_time = last_trade_times[cooldown_key]
            time_since_last = (get_current_time_ist() - last_trade_time).total_seconds() / 60

            if time_since_last < cooldown_minutes:
                remaining = cooldown_minutes - time_since_last
                return {'passed': False, 'reason': f"Cooldown active: {remaining:.1f} min remaining"}

        return {'passed': True, 'reason': 'Cooldown check passed'}

    def _signal_to_setup(self, signal: Dict) -> Dict:
        """Convert signal format to setup format for trade executor"""
        return {
            'index': signal['index'],
            'direction': signal['direction'],
            'vob_support': signal.get('vob_lower', signal.get('entry_price', 0)),
            'vob_resistance': signal.get('vob_upper', signal.get('target', 0)),
            'signal_type': signal.get('signal_type', 'AUTO'),
            'entry_price': signal['entry_price'],
            'stop_loss': signal['stop_loss'],
            'target': signal['target']
        }

    def _execute_trade(self, setup: Dict, signal: Dict, nifty_price: float,
                      expiry_date: str, signal_source: str) -> Dict:
        """
        Execute the trade and track results

        Returns:
            Dict with execution results
        """

        # Demo mode check
        if AUTO_TRADE_SAFETY.get('demo_mode', True):
            result = {
                'success': True,
                'order_id': f"AUTO_DEMO_{signal['index']}_{signal['direction']}_{int(get_current_time_ist().timestamp())}",
                'message': 'DEMO MODE - Trade simulated (auto-trade)',
                'order_details': {
                    'index': signal['index'],
                    'direction': signal['direction'],
                    'entry_price': signal['entry_price'],
                    'stop_loss': signal['stop_loss'],
                    'target': signal['target']
                }
            }
        else:
            # Execute real trade
            try:
                result = self.executor.execute_trade(setup, nifty_price, expiry_date)
            except Exception as e:
                result = {
                    'success': False,
                    'error': str(e),
                    'message': 'Trade execution failed'
                }

                # Stop on error if configured
                if AUTO_TRADE_SAFETY.get('stop_on_error', True):
                    self.disable(f"Error occurred: {str(e)}")

        # Track the trade
        if result['success']:
            self._track_successful_trade(signal, result, signal_source)

            # Send Telegram notification
            if AUTO_TRADE_SAFETY.get('telegram_notifications', True):
                self._send_auto_trade_notification(signal, result, signal_source)
        else:
            self._track_failed_trade(signal, result, signal_source)

        return result

    def _track_successful_trade(self, signal: Dict, result: Dict, signal_source: str):
        """Track successful trade execution"""
        trade_record = {
            'timestamp': get_current_time_ist(),
            'index': signal['index'],
            'direction': signal['direction'],
            'entry_price': signal['entry_price'],
            'stop_loss': signal['stop_loss'],
            'target': signal['target'],
            'order_id': result['order_id'],
            'signal_source': signal_source,
            'status': 'ACTIVE',
            'strike': result.get('order_details', {}).get('strike'),
            'quantity': result.get('order_details', {}).get('quantity')
        }

        # Add to trades today
        st.session_state.auto_trade_state['trades_today'].append(trade_record)

        # Add to active positions
        st.session_state.auto_trade_state['active_positions'].append(trade_record)

        # Update counters
        st.session_state.auto_trade_state['total_trades'] += 1
        st.session_state.auto_trade_state['successful_trades'] += 1

        # Update last trade time for cooldown
        cooldown_key = f"{signal['index']}_{signal['direction']}"
        st.session_state.auto_trade_state['last_trade_time'][cooldown_key] = get_current_time_ist()

        # Log decision
        self._log_decision("TRADE_EXECUTED", f"Auto-trade executed: {signal['index']} {signal['direction']} at {signal['entry_price']}")

    def _track_failed_trade(self, signal: Dict, result: Dict, signal_source: str):
        """Track failed trade attempt"""
        error_record = {
            'timestamp': get_current_time_ist(),
            'index': signal['index'],
            'direction': signal['direction'],
            'error': result.get('error', 'Unknown error'),
            'signal_source': signal_source
        }

        # Add to errors
        st.session_state.auto_trade_state['errors'].append(error_record)

        # Keep only last 20 errors
        if len(st.session_state.auto_trade_state['errors']) > 20:
            st.session_state.auto_trade_state['errors'] = st.session_state.auto_trade_state['errors'][-20:]

        # Update counter
        st.session_state.auto_trade_state['failed_trades'] += 1

        # Log decision
        self._log_decision("TRADE_FAILED", f"Auto-trade failed: {signal['index']} {signal['direction']} - {result.get('error')}")

    def _skip_signal(self, signal: Dict, reason: str) -> Dict:
        """Record skipped signal"""
        st.session_state.auto_trade_state['skipped_signals'] += 1

        if AUTO_TRADE_SAFETY.get('log_all_decisions', True):
            self._log_decision("SIGNAL_SKIPPED", f"{signal.get('index')} {signal.get('direction')} - {reason}")

        return {
            'success': False,
            'skipped': True,
            'reason': reason,
            'signal': signal
        }

    def _send_auto_trade_notification(self, signal: Dict, result: Dict, signal_source: str):
        """Send Telegram notification for auto-trade"""
        try:
            message = f"""
🤖 AUTO-TRADE EXECUTED

📊 Index: {signal['index']}
📈 Direction: {signal['direction']}
🎯 Signal Source: {signal_source}

💰 Entry: {signal['entry_price']}
🛑 Stop Loss: {signal['stop_loss']}
🎯 Target: {signal['target']}

🆔 Order ID: {result['order_id']}
⏰ Time: {get_current_time_ist().strftime('%H:%M:%S')}

{'🧪 DEMO MODE' if AUTO_TRADE_SAFETY.get('demo_mode', True) else '✅ LIVE TRADE'}
"""
            self.telegram.send_message(message)
        except Exception as e:
            print(f"Failed to send auto-trade notification: {e}")

    def _log_decision(self, decision_type: str, message: str):
        """Log trading decision"""
        if not AUTO_TRADE_SAFETY.get('log_all_decisions', True):
            return

        log_entry = {
            'timestamp': get_current_time_ist().isoformat(),
            'type': decision_type,
            'message': message
        }

        # Log to file
        try:
            log_file = "auto_trade_decisions.log"
            with open(log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            print(f"Failed to write log: {e}")

    def close_position(self, position: Dict):
        """Mark a position as closed"""
        # Remove from active positions
        active_positions = st.session_state.auto_trade_state['active_positions']
        st.session_state.auto_trade_state['active_positions'] = [
            p for p in active_positions if p.get('order_id') != position.get('order_id')
        ]

    def update_daily_pnl(self, pnl: float):
        """Update daily P&L"""
        st.session_state.auto_trade_state['daily_pnl'] += pnl

    def get_statistics(self) -> Dict:
        """Get auto-trade statistics"""
        return {
            'total_trades': st.session_state.auto_trade_state['total_trades'],
            'successful_trades': st.session_state.auto_trade_state['successful_trades'],
            'failed_trades': st.session_state.auto_trade_state['failed_trades'],
            'skipped_signals': st.session_state.auto_trade_state['skipped_signals'],
            'trades_today': len(st.session_state.auto_trade_state['trades_today']),
            'active_positions': len(st.session_state.auto_trade_state['active_positions']),
            'daily_pnl': st.session_state.auto_trade_state['daily_pnl'],
            'is_enabled': st.session_state.auto_trade_state['is_enabled'],
            'recent_errors': st.session_state.auto_trade_state['errors'][-5:]
        }

    def reset_statistics(self):
        """Reset all statistics"""
        st.session_state.auto_trade_state = {
            'trades_today': [],
            'active_positions': [],
            'daily_pnl': 0.0,
            'last_trade_time': {},
            'total_trades': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'skipped_signals': 0,
            'errors': [],
            'is_enabled': st.session_state.auto_trade_state.get('is_enabled', False),
            'last_reset_date': get_current_time_ist().date()
        }
