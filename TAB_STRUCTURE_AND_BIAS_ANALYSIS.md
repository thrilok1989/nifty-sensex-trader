# NIFTY/SENSEX Trader - Tab Structure & Bias Calculation Analysis

## 1. APPLICATION ENTRY POINTS

### Main Streamlit Application
**File:** `/home/user/nifty-sensex-trader/app.py` (1,686 lines)
- Main web application using Streamlit
- Manages 7 tabs with persistent session state
- Auto-refresh every 30 seconds
- Initializes all analyzers: SmartTradingDashboard, BiasAnalysisPro, OptionChainAnalyzer, AdvancedChartAnalysis

### CLI Dashboard Runner
**File:** `/home/user/nifty-sensex-trader/run_dashboard.py`
- CLI entry point for running SmartTradingDashboard analysis
- Supports custom symbols (^NSEI, ^BSESN, ^DJI)
- Can run with custom configuration via `run_custom_analysis()`

---

## 2. ALL TABS IN THE APPLICATION

### Tab 1: 🎯 Trade Setup
**Purpose:** Create new manual trade setups with VOB support/resistance levels
**Location:** `app.py` lines 234-330
**Key Features:**
- Select index (NIFTY/SENSEX) and direction (CALL/PUT)
- Set VOB (Volume Order Blocks) support and resistance levels
- Preview calculated trade levels:
  - Entry level
  - Stop loss level
  - Target level
  - Risk:Reward ratio
- Select appropriate strike based on spot price
- Create signal setup with unique ID
**Data Stored in Session State:**
- `st.session_state.signal_manager` - Manages all signal setups
- Setup contains: index, direction, vob_support, vob_resistance, status, signal_count

### Tab 2: 📊 Active Signals
**Purpose:** View and manage active signal setups, track signal count, execute trades
**Location:** `app.py` lines 336-434
**Key Features:**
- Display all active setups with signal count (⭐⭐⭐ visualization)
- Add/remove signals to setups (max 3 signals per setup)
- Monitor VOB touch for automatic trade execution
- Execute trades when VOB level is touched
- Send Telegram alerts when signal is ready
- Display detailed order information after execution
**Bias-Related Features:**
- Tracks when to execute (waits for VOB touch)
- Integrates with trade management system

### Tab 3: 📈 Positions
**Purpose:** View active trading positions and manage exits
**Location:** `app.py` lines 440-494
**Key Features:**
- Demo mode support (no real positions)
- Real mode integrates with DhanHQ API
- Display active positions with:
  - Trading symbol
  - Quantity
  - Unrealized P&L
- Exit positions with one click
- Color-coded P&L (green for profit, red for loss)
**Integration:**
- Uses `TradeExecutor` class for position management
- Integrates with DhanAPI for real trading

### Tab 4: 📊 Smart Trading Dashboard
**Purpose:** Analyze market with adaptive 3-tier bias system and comprehensive indicators
**Location:** `app.py` lines 500-765
**Class:** `SmartTradingDashboard` from `smart_trading_dashboard.py`
**Key Features:**
- **Adaptive Market Analysis** with 3-tier signal system:
  - Fast signals (technical indicators) - weights: 2.0 (normal), 5.0 (reversal)
  - Medium signals (price vs VWAP) - weights: 3.0 (normal), 3.0 (reversal)
  - Slow signals (stock performance) - weights: 5.0 (normal), 2.0 (reversal)
- **Volume Order Blocks (VOB)** - EMA-based detection
- **Range Detection** - Identifies range-bound vs trending markets
- **Technical Indicators:**
  - RSI, MFI, DMI (+DI/-DI), VWAP, VIDYA, ATR
  - Volume trend analysis
- **Multi-Stock Analysis** - Top 9 NSE stocks with weighted bias
- **Divergence Detection** - Identifies reversal signals
- **Reversal Mode** - Adapts weights when divergence detected
- **Trading Signals** - BULLISH, BEARISH, or NEUTRAL

**Display Elements:**
- Current price and market condition
- Market bias percentage (bullish vs bearish)
- Signal breakdown by tier
- Technical indicator values
- Range detection data (if range-bound)
- Top stocks performance
- Market averages (daily, 15m, 1h)
- Trading recommendations

### Tab 5: 🎯 Bias Analysis Pro
**Purpose:** Comprehensive 15+ bias indicator analysis with weighted scoring
**Location:** `app.py` lines 771-1149
**Class:** `BiasAnalysisPro` from `bias_analysis.py`
**Key Features:**
- Analyzes 15+ individual bias indicators
- Each indicator has:
  - Value (indicator reading)
  - Bias (BULLISH/BEARISH/NEUTRAL variants)
  - Score (-100 to +100)
  - Weight (importance factor)
- **15 Bias Indicators:**
  1. RSI (Relative Strength Index) - weight: 1.5
  2. MFI (Money Flow Index) - weight: 1.5
  3. DMI/ADX (Directional Movement) - weight: 2.0
  4. VWAP (Volume Weighted Average Price) - weight: 1.5
  5. Volatility Ratio - weight: 1.0
  6. Volume ROC (Rate of Change) - weight: 1.5
  7. OBV (On Balance Volume) - weight: 2.0
  8. Force Index - weight: 1.5
  9. Price Momentum (ROC) - weight: 1.5
  10. Market Breadth - weight: 3.0
  11. RSI Divergence - weight: 2.5
  12. Choppiness Index - weight: 1.5
  13. EMA Crossover (5/18) - weight: 2.0
  14. ATR Trend - weight: 1.0
  15. Volume Trend - weight: 1.5

- **Overall Bias Calculation:**
  - Weighted score = SUM(indicator_score * weight) / SUM(weights)
  - BULLISH if score > 30, BEARISH if score < -30, else NEUTRAL
  - Confidence = min(100, |score|) or 100 - |score|

- **Display Elements:**
  - Overall bias with emoji and color coding
  - Overall score and confidence percentage
  - Bullish/Bearish/Neutral signal counts
  - Detailed breakdown table with all indicators
  - Visual bar charts of weighted contributions
  - Categorized breakdown (Technical, Volume, Momentum, Market-Wide)
  - Top stocks performance
  - Trading recommendations based on confidence levels

### Tab 6: 📊 Option Chain Analysis
**Purpose:** NSE options analysis with bias detection and support/resistance zones
**Location:** `app.py` lines 1153-1193
**Class:** `OptionChainAnalyzer` from `option_chain_analysis.py`
**Nested Tabs:**
- **Indices Tab:**
  - NIFTY analysis
  - BANKNIFTY analysis
  - NIFTY IT analysis
  - NIFTY AUTO analysis
- **Stocks Tab:**
  - TCS analysis
  - RELIANCE analysis
  - HDFCBANK analysis
- **Overall Market Analysis Tab:**
  - PCR (Put-Call Ratio) analysis
  - Market-wide sentiment

**Features:**
- Bias detection from option chain
- Support/resistance zone identification
- Trade signal generation
- Call and put log tracking per instrument
- Overall option chain data aggregation

### Tab 7: 📈 Advanced Chart Analysis
**Purpose:** TradingView-style charting with 5 advanced indicators
**Location:** `app.py` lines 1199-1400+
**Class:** `AdvancedChartAnalysis` from `advanced_chart_analysis.py`
**5 Advanced Indicators:**
1. **Volume Order Blocks (VOB)** - EMA-based order block detection
2. **HTF Support/Resistance** - Multi-timeframe support/resistance (3m, 5m, 10m, 15m)
3. **Volume Footprint** - 1D timeframe with 10 bins, dynamic POC
4. **Ultimate RSI** - Enhanced RSI indicator
5. **OM Indicator** - Order Flow & Momentum

**Features:**
- Symbol selection (^NSEI, ^BSESN, ^DJI)
- Configurable period (1d, 5d, 1mo) and interval (1m, 5m, 15m, 1h)
- Individual indicator toggles and settings
- Configurable sensitivity and display options per indicator

---

## 3. BIAS CALCULATION METHODS

### Method 1: SmartTradingDashboard (3-Tier Adaptive System)

**Location:** `/home/user/nifty-sensex-trader/smart_trading_dashboard.py` (870 lines)

#### Architecture:
```
Fast Signals (Technical) → Fast Bull/Bear Counts + Weight
Medium Signals (Price)   → Medium Bull/Bear Counts + Weight
Slow Signals (Stocks)    → Slow Bull/Bear Counts + Weight
                              ↓
                    Aggregate with Adaptive Weights
                              ↓
                    Calculate Weighted Percentages
                              ↓
                    Determine Overall Bias
                              ↓
                    Check for Divergences (Reversal Mode)
```

#### Fast Signals (7 signals):
1. RSI > 50 = Bullish
2. MFI > 50 = Bullish
3. +DI > -DI = Bullish
4. Price > VWAP = Bullish
5. Order block bullish signal = Bullish
6. Close > VIDYA+Band = Bullish
7. Volume trend = Bullish

#### Medium Signals (1 signal):
- Price > VWAP = Bullish

#### Slow Signals (3 signals):
- Weighted avg daily change > 0 = Bullish
- Weighted avg 15m change > 0 = Bullish
- Weighted avg 1h change > 0 = Bullish

#### Adaptive Weights:
```
Normal Mode:
  - Fast weight:   2.0
  - Medium weight: 3.0
  - Slow weight:   5.0

Reversal Mode (when divergence detected):
  - Fast weight:   5.0
  - Medium weight: 3.0
  - Slow weight:   2.0
```

#### Bias Determination:
```
Bullish Bias % = (bullish_signals * weight) / total_signals * 100
Bearish Bias % = (bearish_signals * weight) / total_signals * 100

if bullish_bias_pct >= bias_strength (60):
    market_bias = "BULLISH"
elif bearish_bias_pct >= bias_strength (60):
    market_bias = "BEARISH"
else:
    market_bias = "NEUTRAL"
```

#### Divergence Detection:
```
Bullish Divergence:
  - slow_bull_pct >= 66% AND fast_bear_pct >= 60% → Price making lower lows but momentum rising
  
Bearish Divergence:
  - slow_bear_pct >= 66% AND fast_bull_pct >= 60% → Price making higher highs but momentum falling
  
Effect: Triggers REVERSAL MODE with swapped weights
```

#### Range Detection:
- Tight range (rolling range pct < 2.0%)
- Low EMA spread (< 0.5%)
- Low volatility (ATR < 50-bar average)
- Result: Condition = "RANGE-BOUND" or "TRENDING UP/DOWN" or "TRANSITION"

#### Return Data Structure:
```python
{
    'market_bias': "BULLISH|BEARISH|NEUTRAL",
    'bullish_bias_pct': 75.0,
    'bearish_bias_pct': 25.0,
    'fast_bull_pct': 85.7,
    'fast_bear_pct': 14.3,
    'medium_bull_pct': 100.0,
    'medium_bear_pct': 0.0,
    'slow_bull_pct': 66.7,
    'slow_bear_pct': 33.3,
    'reversal_mode': False,
    'divergence_detected': False,
    'bullish_divergence': False,
    'bearish_divergence': False,
    'weighted_avg_daily': 0.75,
    'weighted_avg_tf1': 0.25,  # 15m
    'weighted_avg_tf2': 0.45,  # 1h
    'market_condition': "RANGE-BOUND|TRENDING UP|TRENDING DOWN|TRANSITION"
}
```

### Method 2: BiasAnalysisPro (15+ Indicator Scoring System)

**Location:** `/home/user/nifty-sensex-trader/bias_analysis.py` (790 lines)

#### Architecture:
```
15 Individual Indicators
         ↓
Calculate Score & Bias for Each
         ↓
Apply Weights to Each Indicator
         ↓
Aggregate: SUM(score * weight) / SUM(weights)
         ↓
Determine Overall Bias Based on Score
         ↓
Calculate Confidence Level
```

#### Scoring System for Each Indicator:

```python
# Example: RSI Indicator
rsi_value = 65
if rsi_value > 60:
    rsi_bias = "BULLISH"
    rsi_score = min(100, (rsi_value - 50) * 2) = 30
elif rsi_value < 40:
    rsi_bias = "BEARISH"
    rsi_score = -min(100, (50 - rsi_value) * 2)
else:
    rsi_bias = "NEUTRAL"
    rsi_score = 0
```

#### Bias Result Entry Structure:
```python
{
    'indicator': 'RSI',
    'value': '65.00',
    'bias': 'BULLISH',
    'score': 30.0,
    'weight': 1.5
}
```

#### Overall Bias Calculation:
```python
# Iterate through all 15 indicators
total_weighted_score = 0
total_weight = 0
bullish_count = 0
bearish_count = 0
neutral_count = 0

for indicator in bias_results:
    total_weighted_score += indicator['score'] * indicator['weight']
    total_weight += indicator['weight']
    
    if 'BULLISH' in indicator['bias']:
        bullish_count += 1
    elif 'BEARISH' in indicator['bias']:
        bearish_count += 1
    else:
        neutral_count += 1

# Calculate overall score (normalized)
overall_score = total_weighted_score / total_weight

# Determine bias
if overall_score > 30:
    overall_bias = "BULLISH"
    overall_confidence = min(100, overall_score)
elif overall_score < -30:
    overall_bias = "BEARISH"
    overall_confidence = min(100, abs(overall_score))
else:
    overall_bias = "NEUTRAL"
    overall_confidence = 100 - abs(overall_score)
```

#### Return Data Structure:
```python
{
    'success': True,
    'symbol': '^NSEI',
    'current_price': 18500.50,
    'timestamp': datetime.now(),
    'bias_results': [
        {
            'indicator': 'RSI',
            'value': '65.00',
            'bias': 'BULLISH',
            'score': 30.0,
            'weight': 1.5
        },
        # ... 14 more indicators
    ],
    'overall_bias': 'BULLISH',
    'overall_score': 35.5,
    'overall_confidence': 35.5,
    'bullish_count': 12,
    'bearish_count': 2,
    'neutral_count': 1,
    'total_indicators': 15,
    'stock_data': [
        {
            'symbol': 'RELIANCE',
            'change_pct': 0.75,
            'weight': 9.98
        },
        # ... more stocks
    ]
}
```

---

## 4. KEY DATA STRUCTURES

### Session State Variables (in app.py):

```python
st.session_state {
    'signal_manager': SignalManager(),
    'last_refresh': time.time(),
    'active_setup_id': str,
    'smart_dashboard': SmartTradingDashboard(),
    'dashboard_results': dict,
    'bias_analyzer': BiasAnalysisPro(),
    'bias_analysis_results': dict,
    'option_chain_analyzer': OptionChainAnalyzer(),
    'option_chain_results': dict,
    'active_tab': int,
    'advanced_chart_analyzer': AdvancedChartAnalysis(),
    'chart_data': DataFrame,
    
    # NSE Instruments Data
    'NIFTY_price_data': DataFrame,
    'NIFTY_trade_log': list,
    'NIFTY_call_log_book': list,
    'NIFTY_support_zone': tuple,
    'NIFTY_resistance_zone': tuple,
    # ... same for BANKNIFTY, NIFTY IT, NIFTY AUTO, TCS, RELIANCE, HDFCBANK
    
    'overall_option_data': dict
}
```

### BiasAnalysisPro Instance Variables:

```python
class BiasAnalysisPro:
    def __init__(self):
        self.config = {
            'tf1': '15m',
            'tf2': '1h',
            'rsi_period': 14,
            'mfi_period': 10,
            'dmi_period': 13,
            'dmi_smoothing': 8,
            'atr_period': 14,
            'volume_roc_length': 14,
            'volume_threshold': 1.2,
            'volatility_ratio_length': 14,
            'volatility_threshold': 1.5,
            'obv_smoothing': 21,
            'force_index_length': 13,
            'force_index_smoothing': 2,
            'price_roc_length': 12,
            'breadth_threshold': 60,
            'divergence_lookback': 30,
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'ci_length': 14,
            'ci_high_threshold': 61.8,
            'ci_low_threshold': 38.2,
            'bias_strength': 60,
            'divergence_threshold': 60,
            'stocks': {
                'RELIANCE.NS': 9.98,
                'HDFCBANK.NS': 9.67,
                # ... 7 more stocks
            }
        }
        self.all_bias_results = []
        self.overall_bias = "NEUTRAL"
        self.overall_score = 0
```

### SmartTradingDashboard Instance Variables:

```python
class SmartTradingDashboard:
    def __init__(self, config=None):
        self.config = config or self._default_config()
        self.data = {}
        self.indicators = {}
        self.bias_data = {}
        self.market_condition = "NEUTRAL"
```

---

## 5. BIAS AGGREGATION LOGIC

### SmartTradingDashboard Flow:

```
analyze_market(symbol)
    ↓
fetch_data(symbol, period='5d', interval='5m')
    ↓
calculate_stock_metrics() for each stock
    ↓
calculate_market_indicators(df)
    ├─ RSI, MFI, VWAP, ATR, DMI, VIDYA
    ├─ Order blocks detection
    ├─ Range detection
    └─ Volume trend
    ↓
calculate_bias_signals(df, indicators, stock_metrics)
    ├─ Fast signals (7): RSI, MFI, DMI, VWAP, OB, VIDYA, Volume
    ├─ Medium signals (1): Price vs VWAP
    ├─ Slow signals (3): Daily avg, TF1 avg, TF2 avg
    ├─ Divergence detection
    ├─ Reversal mode check
    └─ Return aggregated bias
    ↓
Final Result: market_bias, condition, indicators, bias_data
```

### BiasAnalysisPro Flow:

```
analyze_all_bias_indicators(symbol)
    ↓
fetch_data(symbol, period='7d', interval='5m')
    ↓
Calculate 15 Indicators:
    ├─ RSI
    ├─ MFI
    ├─ DMI/ADX
    ├─ VWAP
    ├─ Volatility Ratio
    ├─ Volume ROC
    ├─ OBV
    ├─ Force Index
    ├─ Price Momentum
    ├─ Market Breadth
    ├─ RSI Divergence
    ├─ Choppiness Index
    ├─ EMA Crossover
    ├─ ATR Trend
    └─ Volume Trend
    ↓
For each indicator:
    ├─ Get indicator value
    ├─ Determine BULLISH/BEARISH/NEUTRAL bias
    ├─ Calculate score (-100 to +100)
    ├─ Assign weight
    └─ Append to bias_results
    ↓
Aggregate:
    ├─ Sum all weighted scores
    ├─ Divide by total weight
    ├─ Count bullish/bearish/neutral
    └─ Generate overall_score, overall_bias, overall_confidence
    ↓
Final Result: overall_bias, overall_score, confidence, bias_results
```

---

## 6. HOW BIAS IS USED IN EACH TAB

| Tab | Bias Type | Purpose | Usage |
|-----|-----------|---------|-------|
| Trade Setup | Manual | Setup entry/exit levels | Sets VOB support/resistance |
| Active Signals | Smart Dashboard | Track signals | Waiting for execution trigger |
| Positions | N/A | Position management | P&L tracking |
| Smart Trading | 3-Tier Adaptive | Market analysis | Display bias %, signals, condition |
| Bias Pro | 15-Indicator | Deep analysis | Score each indicator individually |
| Option Chain | Custom | Option bias | PCR, put/call ratios |
| Advanced Charts | Indicator-based | Visual analysis | Volume order blocks, HTF levels |

---

## 7. DATA FLOW DIAGRAM

```
User Input (Symbol, Period, Interval)
         ↓
[SmartTradingDashboard / BiasAnalysisPro / OptionChainAnalyzer]
         ↓
Fetch Market Data (Yahoo Finance)
         ↓
Calculate Technical Indicators
    ├─ RSI, MFI, DMI, VWAP, ATR, VIDYA
    ├─ Volume indicators
    ├─ Momentum indicators
    └─ Divergence detection
         ↓
Determine Bias for Each Indicator/Signal
         ↓
Aggregate Bias Scores with Weights
         ↓
Determine Overall Market Bias
         ↓
Display Results in Tab UI
         ↓
Storeresults in Session State
         ↓
Refresh Every 30 Seconds (Auto-refresh)
```

---

## SUMMARY

The application has a sophisticated two-pronged approach to bias analysis:

1. **SmartTradingDashboard (3-Tier Adaptive):** Real-time market sentiment with adaptive weighting for normal vs reversal modes, quick decisions
2. **BiasAnalysisPro (15-Indicator Scoring):** Deep analysis of individual indicators with comprehensive scoring and weighting system

Both systems aggregate their results into clear BULLISH, BEARISH, or NEUTRAL signals with confidence levels, which feed into the trading decision-making process through the tabs and ultimately to trade execution.
