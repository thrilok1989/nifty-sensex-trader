# 📈 NIFTY SENSEX Trader - LITE VERSION

## 🚀 Overview

The **Lite Version** is a streamlined, high-performance trading app focused on essential bias indicators for NIFTY, SENSEX, and Bank Nifty. Built for speed and efficiency, it provides all critical bias analysis without the overhead of advanced features.

## ✨ Features

### ✅ Included (Essential Biases)

1. **Technical Bias (8 Indicators)**
   - Volume Delta
   - High Volume Pivots (HVP)
   - Volume Order Blocks (VOB)
   - Order Blocks
   - RSI (Relative Strength Index)
   - DMI (Directional Movement Index)
   - VIDYA (Variable Index Dynamic Average)
   - MFI (Money Flow Index)

2. **PCR Analysis (Put-Call Ratio)**
   - PCR (OI) - Open Interest based
   - PCR (OI Change) - OI change based
   - PCR (Volume) - Volume based
   - Total CE/PE Open Interest
   - Total CE/PE Volume

3. **Option Chain Overall Bias**
   - Aggregated option chain metrics
   - Full chain PCR analysis
   - Call vs Put dominance

4. **ATM Zone Bias (ATM ±5 Strikes)**
   - Strike-wise PCR analysis
   - 11 strikes around ATM (5 above, ATM, 5 below)
   - CE/PE OI, Volume, and OI Change
   - Individual strike bias (Bullish/Bearish/Neutral)
   - Zone-level bias summary

5. **Overall Market Bias**
   - Aggregates all bias sources
   - Consensus bias calculation
   - Bias source breakdown

### ❌ Removed (For Speed)

- Advanced Chart Analysis (6 custom indicators)
- Trade Setup and Position Tracking
- Active Signal Monitoring (VOB/HTF S/R)
- Enhanced Market Data (VIX, Sectors, Global Markets)
- Supabase Database Integration
- Multiple Tabs Interface
- Heavy Plotly Charts
- Stock Breadth Analysis (10 stocks)
- Signal Management System

## 📦 Files Structure

```
Lite Version Files:
├── app_lite.py                    # Main lite application (600 lines)
├── lite_helpers.py                # Minimal helper functions (380 lines)
│
Supporting Files (from main app):
├── config.py                      # Configuration and secrets
├── bias_analysis.py               # Technical bias calculations
├── dhan_option_chain_analyzer.py  # PCR calculations (optional)
├── market_hours_scheduler.py      # Trading hours check
└── requirements.txt               # Dependencies
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository (if not already done)
git clone <repository-url>
cd nifty-sensex-trader

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Ensure `config.py` has your credentials:

```python
# Dhan API credentials (required for option chain data)
DHAN_CLIENT_ID = "your_client_id"
DHAN_ACCESS_TOKEN = "your_access_token"

# Timezone
IST = pytz.timezone('Asia/Kolkata')
```

### 3. Run the Lite App

```bash
streamlit run app_lite.py
```

The app will open in your browser at `http://localhost:8501`

## 📊 Usage

### Main Interface

1. **Market Status**: Shows if the market is open or closed
2. **Overall Market Bias**: Aggregated bias from all sources at the top
3. **Technical Bias**: 8-indicator technical analysis
4. **PCR Analysis**: Put-Call Ratio metrics
5. **ATM Zone Bias**: Strike-wise analysis around ATM

### Settings (Sidebar)

- **Select Index**: Choose between NIFTY 50, SENSEX, or BANK NIFTY
- **Auto Refresh**: Enable/disable automatic data refresh
- **Refresh Interval**: Set refresh interval (60-300 seconds)

### Refresh Data

- Click **"🔄 Refresh Data"** button to manually update
- Enable **Auto Refresh** for automatic updates

## 🎯 Bias Interpretation

### Technical Bias

- **BULLISH**: 60%+ bullish indicators (5+ out of 8)
- **BEARISH**: 60%+ bearish indicators (5+ out of 8)
- **NEUTRAL**: Neither bullish nor bearish dominance

### PCR Bias

- **PCR > 1.2**: BULLISH (More puts = support building)
- **PCR < 0.8**: BEARISH (More calls = resistance building)
- **PCR 0.8-1.2**: NEUTRAL (Balanced market)

### ATM Zone Bias

- Analyzes 11 strikes around ATM (±5 strikes)
- Each strike gets individual bias based on PCR
- Zone bias: Majority + Zone PCR direction

### Overall Market Bias

- **BULLISH**: 60%+ sources bullish (2+ out of 3)
- **BEARISH**: 60%+ sources bearish (2+ out of 3)
- **NEUTRAL**: No clear dominance

## 🔧 Performance Optimizations

### What Makes It "Lite"?

1. **Reduced File Size**
   - Main app: ~600 lines (vs 3,286 lines in full version)
   - Total code: ~150KB (vs ~600KB in full version)
   - 2-3 files vs 30+ files

2. **Removed Heavy Dependencies**
   - No Plotly charts (50MB+ dependency)
   - No Supabase database
   - No complex UI components
   - Minimal pandas operations

3. **Simplified UI**
   - Single-page layout (vs 9 tabs)
   - Basic st.metric() instead of custom charts
   - Lightweight CSS styling
   - Minimal session state usage

4. **Focused Data Fetching**
   - Single index at a time (vs parallel multi-stock)
   - Minimal API calls
   - Simple caching strategy
   - No background preloading

5. **Fast Load Time**
   - Loads in 2-3 seconds (vs 10-15 seconds for full app)
   - Minimal import overhead
   - Streamlined data processing

## 🔑 Key Differences: Lite vs Full Version

| Feature | Lite Version | Full Version |
|---------|-------------|--------------|
| File Size | ~150KB | ~600KB |
| Number of Files | 2-3 | 30+ |
| Load Time | 2-3 sec | 10-15 sec |
| Tabs | 1 (single page) | 9 tabs |
| Technical Indicators | 8 (essential) | 8 + 6 advanced |
| Charts | Simple metrics | Plotly interactive |
| Database | None | Supabase |
| Trade Tracking | No | Yes |
| Signal Management | No | Yes |
| Stock Analysis | Indices only | 10+ stocks |
| Auto Refresh | Yes (60-300s) | Yes (60-300s) |

## 📝 Requirements

### Minimal Dependencies

```
streamlit>=1.28.0       # Web framework
pandas>=2.0.0           # Data manipulation
yfinance>=0.2.28        # Market data
pytz>=2023.3            # Timezone handling
requests>=2.31.0        # HTTP requests
```

### Optional (for option chain data)

```
dhanhq>=1.3.3           # Dhan broker API
```

## 🐛 Troubleshooting

### Option Chain Data Not Loading

**Issue**: PCR and ATM Zone bias showing "Unable to fetch"

**Solutions**:
1. Check Dhan API credentials in `config.py`
2. Verify API access token is valid
3. Check internet connection
4. Ensure market is open (option chain only available during market hours)

### Technical Bias Not Calculating

**Issue**: "Unable to fetch intraday data"

**Solutions**:
1. Check internet connection
2. Try different index (NIFTY/SENSEX)
3. Yahoo Finance may have rate limits - wait and retry
4. Ensure 7 days of historical data available

### App Not Loading

**Issue**: Streamlit app won't start

**Solutions**:
1. Verify all dependencies installed: `pip install -r requirements.txt`
2. Check Python version (3.8+ required)
3. Ensure `config.py` exists with required settings
4. Check for syntax errors in configuration

### Slow Performance

**Issue**: App running slowly

**Solutions**:
1. Increase refresh interval (180-300 seconds)
2. Disable auto-refresh when not needed
3. Close other browser tabs
4. Check network speed for API calls

## 🎨 Customization

### Change Refresh Interval

Edit in sidebar or modify default in code:

```python
refresh_interval = st.slider("Refresh Interval (seconds)", 60, 300, 120)
```

### Add More Indices

Edit `symbol_map` in `app_lite.py`:

```python
symbol_map = {
    'NIFTY 50': '^NSEI',
    'SENSEX': '^BSESN',
    'BANK NIFTY': '^NSEBANK',
    'NIFTY IT': '^CNXIT',      # Add custom indices
    'NIFTY PHARMA': '^CNXPHARMA'
}
```

### Customize ATM Strike Range

Change `num_strikes` parameter:

```python
data['atm_zone'] = get_atm_zone_bias(
    data['option_chain'],
    data['current_price'],
    num_strikes=10  # Change from 5 to 10 for ±10 strikes
)
```

### Modify Bias Thresholds

Edit in `lite_helpers.py`:

```python
# PCR bias thresholds
if pcr_oi > 1.5:  # Change from 1.2 to 1.5
    bias = 'BULLISH'
elif pcr_oi < 0.7:  # Change from 0.8 to 0.7
    bias = 'BEARISH'
```

## 🚀 Deployment

### Local Deployment

```bash
streamlit run app_lite.py --server.port 8501
```

### Network Access

```bash
streamlit run app_lite.py --server.address 0.0.0.0
```

### Production Deployment

For cloud deployment (Streamlit Cloud, Heroku, etc.), use:

```bash
# Create .streamlit/config.toml
mkdir .streamlit
echo "[server]" > .streamlit/config.toml
echo "headless = true" >> .streamlit/config.toml
echo "port = $PORT" >> .streamlit/config.toml
```

## 📄 License

Same as main project - refer to main README.md

## 🤝 Contributing

Contributions welcome! Focus on:
- Performance optimizations
- Additional lightweight bias indicators
- UI/UX improvements (keeping it simple)
- Bug fixes

## 📞 Support

For issues specific to the lite version:
1. Check troubleshooting section above
2. Verify all dependencies installed
3. Test with main app to isolate lite-specific issues

## 🎯 Future Enhancements

Potential additions (while keeping it lite):
- [ ] Basic price alerts
- [ ] Export bias data to CSV
- [ ] Historical bias tracking (in-memory only)
- [ ] Multiple index comparison view
- [ ] Mobile-responsive design improvements

---

**Built for speed. Focused on essentials. Powered by Python & Streamlit.**

🚀 Fast | 📊 Comprehensive | ⚡ Real-time
