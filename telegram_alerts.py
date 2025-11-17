import requests
import streamlit as st
from config import get_telegram_credentials
from datetime import datetime

class TelegramBot:
    def __init__(self):
        """Initialize Telegram bot"""
        creds = get_telegram_credentials()
        self.enabled = creds['enabled']
        
        if self.enabled:
            self.bot_token = creds['bot_token']
            self.chat_id = creds['chat_id']
            self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def send_message(self, message: str, parse_mode: str = "HTML"):
        """Send Telegram message"""
        if not self.enabled:
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode
            }
            response = requests.post(url, json=payload, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def send_signal_ready(self, setup: dict):
        """Send signal ready alert"""
        message = f"""
🎯 <b>SIGNAL READY - 3/3 Received</b>

<b>Index:</b> {setup['index']}
<b>Direction:</b> {setup['direction']}

<b>VOB Support:</b> {setup['vob_support']}
<b>VOB Resistance:</b> {setup['vob_resistance']}

<b>Status:</b> ✅ Ready to Trade
<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📱 Open app to execute trade
        """
        return self.send_message(message.strip())
    
    def send_vob_touch_alert(self, setup: dict, current_price: float):
        """Send VOB touch alert"""
        vob_level = setup['vob_support'] if setup['direction'] == 'CALL' else setup['vob_resistance']
        vob_type = "Support" if setup['direction'] == 'CALL' else "Resistance"
        
        message = f"""
🔥 <b>VOB TOUCHED - ENTRY SIGNAL!</b>

<b>Index:</b> {setup['index']}
<b>Direction:</b> {setup['direction']}

<b>Current Price:</b> {current_price}
<b>VOB {vob_type}:</b> {vob_level}

<b>Status:</b> 🚀 Ready to Execute
<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

⚡ Execute trade NOW!
        """
        return self.send_message(message.strip())
    
    def send_order_placed(self, setup: dict, order_id: str, strike: int, 
                         sl: float, target: float):
        """Send order placed confirmation"""
        message = f"""
✅ <b>ORDER PLACED SUCCESSFULLY</b>

<b>Order ID:</b> {order_id}

<b>Index:</b> {setup['index']}
<b>Direction:</b> {setup['direction']}
<b>Strike:</b> {strike}

<b>Stop Loss:</b> {sl}
<b>Target:</b> {target}

<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 Monitor position in app
        """
        return self.send_message(message.strip())
    
    def send_order_failed(self, setup: dict, error: str):
        """Send order failure alert"""
        message = f"""
❌ <b>ORDER PLACEMENT FAILED</b>

<b>Index:</b> {setup['index']}
<b>Direction:</b> {setup['direction']}

<b>Error:</b> {error}

<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

⚠️ Check app for details
        """
        return self.send_message(message.strip())
    
    def send_position_exit(self, order_id: str, pnl: float):
        """Send position exit alert"""
        pnl_emoji = "💰" if pnl > 0 else "📉"
        message = f"""
{pnl_emoji} <b>POSITION EXITED</b>

<b>Order ID:</b> {order_id}
<b>P&L:</b> ₹{pnl:,.2f}

<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        return self.send_message(message.strip())

    def send_vob_entry_signal(self, signal: dict):
        """Send VOB-based entry signal alert"""
        signal_emoji = "🟢" if signal['direction'] == 'CALL' else "🔴"
        direction_label = "BULLISH" if signal['direction'] == 'CALL' else "BEARISH"

        message = f"""
{signal_emoji} <b>VOB ENTRY SIGNAL - {direction_label}</b>

<b>Index:</b> {signal['index']}
<b>Direction:</b> {signal['direction']}
<b>Market Sentiment:</b> {signal['market_sentiment']}

💰 <b>ENTRY LEVELS</b>
<b>Entry Price:</b> {signal['entry_price']}
<b>Stop Loss:</b> {signal['stop_loss']}
<b>Target:</b> {signal['target']}
<b>Risk:Reward:</b> {signal['risk_reward']}

📊 <b>VOB DETAILS</b>
<b>VOB Level:</b> {signal['vob_level']}
<b>Distance from VOB:</b> {signal['distance_from_vob']} points
<b>VOB Volume:</b> {signal['vob_volume']:,.0f}

<b>Time:</b> {signal['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}

⚡ <b>Execute trade NOW!</b>
        """
        return self.send_message(message.strip())

    def send_htf_sr_entry_signal(self, signal: dict):
        """Send HTF Support/Resistance entry signal alert"""
        signal_emoji = "🟢" if signal['direction'] == 'CALL' else "🔴"
        direction_label = "BULLISH" if signal['direction'] == 'CALL' else "BEARISH"

        # Format timeframe for display
        timeframe_display = {
            '5T': '5 Min',
            '10T': '10 Min',
            '15T': '15 Min'
        }.get(signal.get('timeframe', ''), signal.get('timeframe', 'N/A'))

        # Determine if it's support or resistance signal
        if signal['direction'] == 'CALL':
            level_type = "Support"
            level_value = signal['support_level']
        else:
            level_type = "Resistance"
            level_value = signal['resistance_level']

        message = f"""
{signal_emoji} <b>HTF S/R ENTRY SIGNAL - {direction_label}</b>

<b>Index:</b> {signal['index']}
<b>Direction:</b> {signal['direction']}
<b>Market Sentiment:</b> {signal['market_sentiment']}

💰 <b>ENTRY LEVELS</b>
<b>Entry Price:</b> {signal['entry_price']}
<b>Stop Loss:</b> {signal['stop_loss']}
<b>Target:</b> {signal['target']}
<b>Risk:Reward:</b> {signal['risk_reward']}

📊 <b>HTF S/R DETAILS</b>
<b>Timeframe:</b> {timeframe_display}
<b>{level_type} Level:</b> {level_value}
<b>Distance from Level:</b> {signal['distance_from_level']} points

<b>Time:</b> {signal['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}

⚡ <b>Execute trade NOW!</b>
        """
        return self.send_message(message.strip())


def send_test_message():
    """Send test message to verify Telegram setup"""
    bot = TelegramBot()
    if bot.enabled:
        message = """
✅ <b>Telegram Connected!</b>

Your trading alerts are now active.

<b>Test Time:</b> """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return bot.send_message(message.strip())
    return False
