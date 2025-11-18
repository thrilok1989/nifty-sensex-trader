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

---

## 🚀 Cloud Deployment (Streamlit Cloud)

Deploy your app to Streamlit Cloud for 24/7 access from any device (mobile/desktop):

### Step 1: Prepare Your Repository
1. Ensure your code is pushed to GitHub
2. Make sure `requirements.txt` is up to date
3. Verify `.streamlit/config.toml` is present

### Step 2: Deploy to Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io/)
2. Sign in with your GitHub account
3. Click "New app"
4. Select your repository: `thrilok1989/nifty-sensex-trader`
5. Main file path: `app.py`
6. Click "Deploy"

### Step 3: Configure Secrets
1. In Streamlit Cloud dashboard, click on your app
2. Click "Settings" → "Secrets"
3. Copy the content from `.streamlit/secrets.toml.example`
4. Paste and update with your actual credentials:
```toml
[DHAN]
CLIENT_ID = "your_actual_client_id"
ACCESS_TOKEN = "your_actual_access_token"
API_KEY = "your_actual_api_key"
API_SECRET = "your_actual_api_secret"

[TELEGRAM]
BOT_TOKEN = "your_actual_bot_token"
CHAT_ID = "your_actual_chat_id"
```
5. Click "Save"

### Step 4: Access Your App
- Your app will be available at: `https://your-app-name.streamlit.app`
- Access from any device (mobile, tablet, desktop)
- Auto-refresh works automatically every 60 seconds
- App stays synced across all your devices

### Benefits of Cloud Deployment
✅ **24/7 Availability** - Access from anywhere, anytime
✅ **Auto-Refresh** - Market data updates automatically
✅ **Mobile Friendly** - Responsive design for phones and tablets
✅ **No Setup** - No need to run locally
✅ **Free Hosting** - Streamlit Community Cloud is free
✅ **Always Updated** - Push to GitHub to auto-deploy updates

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
