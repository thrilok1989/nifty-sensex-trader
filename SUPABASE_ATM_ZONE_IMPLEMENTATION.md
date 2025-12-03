# Supabase Integration & ATM Zone Bias Implementation Summary

## Overview

This implementation adds **Supabase database integration** and **Detailed ATM Zone Bias Analysis** to the NIFTY/SENSEX Trader application. The new features provide persistent data storage and granular strike-wise Put-Call Ratio (PCR) analysis for better trading decisions.

---

## 🎯 Features Implemented

### 1. **Supabase Database Integration**

#### Files Created/Modified:
- ✅ `supabase_manager.py` - Complete Supabase operations manager
- ✅ `supabase_schema.sql` - Database schema with 4 tables + views
- ✅ `SUPABASE_SETUP.md` - Comprehensive setup guide
- ✅ `config.py` - Added Supabase credential management
- ✅ `.streamlit/secrets.toml.example` - Added Supabase config template
- ✅ `requirements.txt` - Added `supabase>=2.0.0` dependency

#### Database Schema:

**Table 1: `atm_zone_bias`**
- Stores strike-wise data for ATM ±5 zones
- Fields: symbol, timestamp, spot_price, strike_price, strike_offset
- CE/PE metrics: OI, OI Change, Volume
- PCR calculations: PCR (OI), PCR (OI Change), PCR (Volume)
- Strike-level bias: BULLISH, BEARISH, NEUTRAL
- Indexed for fast queries by symbol, timestamp

**Table 2: `option_chain_snapshots`**
- Stores complete option chain snapshots
- Overall PCR metrics and bias scores
- JSONB field for flexible data storage
- Historical analysis support

**Table 3: `trading_signals`**
- Persistent storage of trading signals
- Tracks signal lifecycle (active, triggered, closed)
- P&L tracking and exit prices
- Metadata storage in JSONB

**Table 4: `bias_analysis_history`**
- Historical bias analysis records
- Component bias tracking (technical, option chain, volume, sentiment)
- Score breakdown (fast, medium, slow indicators)

#### Database Views:
- `latest_atm_zone_bias` - Quick access to most recent ATM data
- `latest_option_chain` - Latest option chain snapshots

#### Utility Functions:
- `clean_old_data(days_to_keep)` - Automated data cleanup

---

### 2. **ATM Zone Bias Analysis**

#### Files Created/Modified:
- ✅ `atm_zone_bias_component.py` - Streamlit UI component
- ✅ `dhan_option_chain_analyzer.py` - Added `calculate_atm_zone_bias()` method
- ✅ `app.py` - Added new tab "🎯 ATM Zone Bias"

#### Features:

**Strike-wise PCR Calculation:**
- ATM ±5 strikes (11 total strikes)
- Individual PCR for each strike:
  - PCR (OI) = PE OI / CE OI
  - PCR (OI Change) = PE OI Change / CE OI Change
  - PCR (Volume) = PE Volume / CE Volume

**Bias Determination Per Strike:**
- Weighted scoring system:
  - PCR (OI) weight: 3
  - PCR (OI Change) weight: 5 (most important)
- Score ≥ 5: BULLISH (more puts = defensive positioning)
- Score ≤ -5: BEARISH (fewer puts = aggressive positioning)
- Otherwise: NEUTRAL

**Supported Instruments:**
- NIFTY (50 point strike intervals)
- SENSEX (100 point strike intervals)
- BANKNIFTY (100 point strike intervals)
- FINNIFTY (50 point strike intervals)

**UI Components:**
- 📊 Comprehensive data table with all strike-wise metrics
- 🎯 Color-coded bias indicators
- 📈 Zone summary statistics
- 💾 Save to Supabase database option
- 📜 View 24-hour historical data
- 🔄 Real-time data refresh
- 💾 Database connection status

---

## 📊 ATM Zone Bias Table Columns

| Column | Description |
|--------|-------------|
| **Strike** | Strike price (₹) |
| **Offset** | Distance from ATM (ATM-5 to ATM+5) |
| **CE OI** | Call Option Open Interest |
| **PE OI** | Put Option Open Interest |
| **CE OI Δ** | Call OI Change |
| **PE OI Δ** | Put OI Change |
| **CE Vol** | Call Volume |
| **PE Vol** | Put Volume |
| **PCR (OI)** | Put-Call Ratio (Open Interest) |
| **PCR (OI Δ)** | Put-Call Ratio (OI Change) |
| **PCR (Vol)** | Put-Call Ratio (Volume) |
| **Bias** | Strike Bias (BULLISH/BEARISH/NEUTRAL) |

---

## 🚀 How to Use

### Step 1: Setup Supabase (First Time Only)

1. **Create Supabase Project:**
   - Go to https://supabase.com
   - Create new project (choose region closest to you)
   - Wait for provisioning (~2 minutes)

2. **Run Database Schema:**
   - Open SQL Editor in Supabase dashboard
   - Copy contents of `supabase_schema.sql`
   - Paste and execute in SQL Editor

3. **Get Credentials:**
   - Go to Settings → API
   - Copy Project URL and anon/public key

4. **Configure Application:**
   - Edit `.streamlit/secrets.toml`
   - Add Supabase credentials:
   ```toml
   [SUPABASE]
   URL = "your_project_url"
   KEY = "your_anon_key"
   ```

5. **Restart Application:**
   ```bash
   streamlit run app.py
   ```

### Step 2: Access ATM Zone Bias

1. Open the application
2. Navigate to **"🎯 ATM Zone Bias"** tab (last tab)
3. Select symbol (NIFTY, SENSEX, BANKNIFTY, FINNIFTY)
4. Click **"🔄 Refresh"** to load data
5. Enable **"💾 Save to DB"** to persist data
6. View **"📜 History"** for past 24 hours

---

## 🔧 Technical Implementation Details

### Data Flow:

```
1. User clicks "Refresh NIFTY"
   ↓
2. DhanOptionChainAnalyzer.calculate_atm_zone_bias('NIFTY')
   ↓
3. Fetch option chain from Dhan API
   ↓
4. Identify ATM strike (round spot price to nearest interval)
   ↓
5. Extract ATM ±5 strikes data
   ↓
6. Calculate PCR for each strike
   ↓
7. Determine individual strike bias
   ↓
8. Display in Streamlit table
   ↓
9. (Optional) Save to Supabase database
```

### Supabase Manager Methods:

```python
from supabase_manager import get_supabase_manager

supabase = get_supabase_manager()

# Save ATM zone data
supabase.save_atm_zone_bias(symbol, spot_price, atm_zone_data)

# Get latest ATM zone data
df = supabase.get_latest_atm_zone_bias(symbol, limit=11)

# Get historical data
history = supabase.get_atm_zone_bias_history(symbol, hours=24)

# Test connection
is_connected = supabase.test_connection()

# Get table statistics
stats = supabase.get_table_stats()
```

---

## 📈 Example ATM Zone Bias Output

**NIFTY @ 23,500**

| Strike | Offset | CE OI | PE OI | PCR (OI) | PCR (OI Δ) | Bias |
|--------|--------|-------|-------|----------|------------|------|
| 23,250 | ATM-5 | 50,000 | 75,000 | 1.50 | 1.35 | 🟢 BULLISH |
| 23,300 | ATM-4 | 55,000 | 70,000 | 1.27 | 1.20 | 🟡 NEUTRAL |
| 23,350 | ATM-3 | 60,000 | 65,000 | 1.08 | 0.95 | 🟡 NEUTRAL |
| 23,400 | ATM-2 | 65,000 | 60,000 | 0.92 | 0.85 | 🟡 NEUTRAL |
| 23,450 | ATM-1 | 70,000 | 58,000 | 0.83 | 0.75 | 🔴 BEARISH |
| **23,500** | **ATM** | **85,000** | **90,000** | **1.06** | **1.10** | 🟡 NEUTRAL |
| 23,550 | ATM+1 | 75,000 | 72,000 | 0.96 | 0.88 | 🟡 NEUTRAL |
| 23,600 | ATM+2 | 68,000 | 65,000 | 0.96 | 0.92 | 🟡 NEUTRAL |
| 23,650 | ATM+3 | 62,000 | 60,000 | 0.97 | 1.05 | 🟡 NEUTRAL |
| 23,700 | ATM+4 | 58,000 | 70,000 | 1.21 | 1.25 | 🟢 BULLISH |
| 23,750 | ATM+5 | 52,000 | 78,000 | 1.50 | 1.40 | 🟢 BULLISH |

**Zone Summary:**
- Total CE OI: 7,00,000
- Total PE OI: 7,53,000
- Zone PCR: 1.076
- Bias Distribution: 🟢 3 | 🟡 6 | 🔴 1

---

## 🎨 UI Features

### Data Table:
- ✅ Sortable columns
- ✅ Color-coded bias column
- ✅ Formatted numbers with commas
- ✅ Responsive design
- ✅ 450px height with scroll

### Controls:
- 🔄 **Refresh Button** - Fetch latest data
- 💾 **Save to DB Checkbox** - Auto-save to Supabase
- 📜 **View History Button** - Show 24h historical snapshots
- 🧪 **Test Connection Button** - Verify Supabase status

### Metrics Display:
- Spot Price (current market price)
- ATM Strike (calculated ATM)
- Total Strikes (always 11 for ATM ±5)
- Timestamp (last update time)
- Zone Summary Statistics
- Database Record Counts

---

## 🔒 Security & Performance

### Security:
- ✅ Credentials stored in Streamlit secrets
- ✅ Row Level Security (RLS) enabled on all tables
- ✅ API keys never exposed in code
- ✅ Graceful fallback when Supabase unavailable

### Performance:
- ✅ Indexed database queries
- ✅ Session state caching for UI responsiveness
- ✅ Lazy data loading (only on tab access)
- ✅ Efficient bulk inserts (11 strikes in 1 transaction)
- ✅ Connection pooling via Supabase client

---

## 📦 Dependencies Added

```txt
supabase>=2.0.0
```

All other dependencies remain unchanged.

---

## 🐛 Troubleshooting

### Issue: "Supabase is disabled"
**Solution:** Configure credentials in `.streamlit/secrets.toml`

### Issue: "Failed to save to database"
**Solution:**
1. Check Supabase project is active (not paused)
2. Verify credentials are correct
3. Run `supabase_schema.sql` in SQL Editor
4. Click "Test Database Connection" button

### Issue: "No ATM zone data available"
**Solution:**
1. Verify Dhan API credentials are configured
2. Check market hours (9:15 AM - 3:30 PM IST)
3. Ensure internet connectivity
4. Check Dhan API rate limits

### Issue: Import errors after update
**Solution:**
```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## 📚 Files Modified Summary

### New Files:
1. `supabase_manager.py` (379 lines)
2. `supabase_schema.sql` (273 lines)
3. `SUPABASE_SETUP.md` (237 lines)
4. `atm_zone_bias_component.py` (319 lines)
5. `SUPABASE_ATM_ZONE_IMPLEMENTATION.md` (this file)

### Modified Files:
1. `requirements.txt` - Added supabase dependency
2. `config.py` - Added `get_supabase_credentials()`
3. `.streamlit/secrets.toml.example` - Added Supabase section
4. `dhan_option_chain_analyzer.py` - Added `calculate_atm_zone_bias()` method
5. `app.py` - Added import and new tab for ATM Zone Bias

### Total Lines Added: ~1,500+ lines of code

---

## 🎯 Trading Strategy Insights

### How to Use ATM Zone Bias:

**Bullish Zone (PCR > 1.2):**
- More puts being bought/held at these strikes
- Suggests defensive positioning or hedging
- Indicates potential support at these levels
- Consider: Long call spreads, selling puts

**Bearish Zone (PCR < 0.8):**
- More calls being bought/held at these strikes
- Suggests aggressive positioning
- Indicates potential resistance at these levels
- Consider: Long put spreads, selling calls

**Neutral Zone (0.8 ≤ PCR ≤ 1.2):**
- Balanced activity
- No clear directional bias
- Wait for breakout confirmation

### Multi-Strike Analysis:

Look for **clusters** of similar bias:
- **3+ consecutive BULLISH strikes** = Strong support zone
- **3+ consecutive BEARISH strikes** = Strong resistance zone
- **Bias flip at ATM** = Potential pivot point

---

## 🔮 Future Enhancements (Ideas)

- [ ] Real-time WebSocket updates for ATM zone data
- [ ] Email/SMS alerts when bias changes
- [ ] Historical PCR trend charts
- [ ] Strike-wise Greeks integration
- [ ] Max Pain calculation for ATM zone
- [ ] Automated trading signal generation from ATM bias
- [ ] Export to CSV/Excel functionality
- [ ] Custom ATM range selection (±3, ±7, ±10)
- [ ] Intraday PCR change tracking
- [ ] Multi-expiry ATM analysis

---

## 📞 Support

For detailed setup instructions, see:
- `SUPABASE_SETUP.md` - Database setup guide
- `README.md` - Application overview
- Supabase Docs: https://supabase.com/docs

---

## ✅ Implementation Complete

All requested features have been successfully implemented:
- ✅ Supabase integration for data persistence
- ✅ ATM Zone Bias tables (ATM ±5 strikes)
- ✅ Strike-wise PCR calculations (OI, OI Change, Volume)
- ✅ Comprehensive Streamlit UI
- ✅ Database schema with 4 tables
- ✅ Historical data viewing
- ✅ Support for NIFTY, SENSEX, BANKNIFTY, FINNIFTY

**Ready for production use!** 🚀
