# NIFTY/SENSEX Manual Trader

VOB-Based Trading System with Manual Signal Entry

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Secrets

Create `.streamlit/secrets.toml`:
```toml
[DHAN]
CLIENT_ID = "your_client_id"
ACCESS_TOKEN = "your_access_token"

[TELEGRAM]
BOT_TOKEN = "your_bot_token"
CHAT_ID = "your_chat_id"
```

### 3. Run App
```bash
streamlit run app.py
```

## Usage

1. **Create Signal Setup**
   - Select Index (NIFTY/SENSEX)
   - Select Direction (CALL/PUT)
   - Enter VOB Support & Resistance levels
   - Click "Create Signal Setup"

2. **Add Signals**
   - Go to "Active Signals" tab
   - Click "Add Signal" button 3 times
   - App shows "Ready" when 3 signals received

3. **Execute Trade**
   - Wait for price to touch VOB level
   - App shows "EXECUTE TRADE NOW" button
   - Click to place Super Order via DhanHQ

4. **Monitor Positions**
   - Go to "Positions" tab
   - View active trades
   - Exit positions manually if needed

## Features

- ✅ Manual signal tracking (persistent storage)
- ✅ Live NIFTY price from NSE
- ✅ Automatic strike selection (ATM/ITM)
- ✅ Super Order placement (Entry + SL + Target)
- ✅ Telegram alerts
- ✅ Position monitoring
- ✅ Demo mode for testing

## Configuration

Edit `config.py` to customize:
- Lot sizes
- Stop loss offset
- VOB touch tolerance
- Auto-refresh interval

## Demo Mode

Set `DEMO_MODE = True` in `config.py` to test without real orders.
```

---

## **🎉 ALL FILES COMPLETE!**

### **File Structure:**
```
📁 nifty-sensex-trader/
├── 📄 app.py                    # Main Streamlit app
├── 📄 config.py                 # Configuration
├── 📄 market_data.py            # NSE data fetcher
├── 📄 signal_manager.py         # Signal tracking
├── 📄 strike_calculator.py      # Strike calculation
├── 📄 dhan_api.py               # DhanHQ integration
├── 📄 telegram_alerts.py        # Telegram bot
├── 📄 trade_executor.py         # Trade execution
├── 📄 requirements.txt          # Dependencies
├── 📄 README.md                 # Documentation
├── 📄 trading_signals.json      # Auto-created signal storage
└── 📁 .streamlit/
    └── 📄 secrets.toml          # Your credentials
