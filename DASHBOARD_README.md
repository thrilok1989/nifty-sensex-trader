# Smart Trading Dashboard - Pine Script to Python

Complete conversion of the Pine Script "Smart Trading Dashboard - Adaptive + VOB" to Python.

## Features

### 📊 Multi-Stock Analysis
- Tracks 9 major NSE stocks with weighted analysis
- Reliance, HDFC Bank, Bharti Airtel, TCS, ICICI Bank, Infosys, Hindustan Unilever, ITC, Maruti Suzuki
- Real-time price data with multiple timeframe analysis (Daily, 15m, 1h)
- Weighted average calculation for overall market sentiment

### 🌍 Global Market Integration
- US Market (Dow Jones) tracking
- USD/INR forex analysis
- Correlation with Nifty/Sensex movement

### 🔧 Technical Indicators
- **RSI** (Relative Strength Index) - Momentum indicator
- **MFI** (Money Flow Index) - Volume-weighted RSI
- **DMI** (Directional Movement Index) - Trend strength
  - ADX (Average Directional Index)
  - +DI (Positive Directional Indicator)
  - -DI (Negative Directional Indicator)
- **VWAP** (Volume Weighted Average Price)
- **VIDYA** (Variable Index Dynamic Average) - Adaptive moving average
- **ATR** (Average True Range) - Volatility measure

### 📦 Advanced Market Analysis

#### Range Detection
- Automatically detects range-bound markets
- Identifies trending vs. choppy conditions
- Movement quality assessment (STRONG/MODERATE/WEAK/CHOPPY)
- Range breakout detection

#### Order Blocks
- EMA-based order block detection
- Bullish and bearish signal generation
- Volume Order Blocks (VOB) integration

### 🎯 Adaptive Market Bias System

The dashboard uses a sophisticated 3-tier bias calculation:

1. **Fast Signals** (Technical Indicators)
   - RSI, MFI, DMI, VWAP, VIDYA, Volume
   - Weight: 2.0 (Normal) / 5.0 (Reversal)

2. **Medium Signals** (Price Action)
   - Price vs VWAP
   - Weight: 3.0 (Normal) / 3.0 (Reversal)

3. **Slow Signals** (Stock Performance)
   - Weighted stock portfolio performance
   - Weight: 5.0 (Normal) / 2.0 (Reversal)

#### Reversal Mode
- Automatically detects divergence between fast and slow signals
- Switches weight preferences to favor fast signals
- Helps catch market reversals early

### 📈 Market Bias Categories
- **BULLISH** - High probability long setup (≥60% bias)
- **BEARISH** - High probability short setup (≥60% bias)
- **NEUTRAL** - No clear direction, wait for setup

## Installation

### Prerequisites
- Python 3.8 or higher
- Internet connection for fetching market data

### Install Dependencies

```bash
pip install -r requirements_dashboard.txt
```

Or manually:
```bash
pip install pandas numpy yfinance tabulate python-dateutil
```

## Usage

### Basic Usage

```bash
python run_dashboard.py
```

This will analyze Nifty 50 (^NSEI) by default.

### Analyze Different Symbols

```bash
# Analyze Sensex
python run_dashboard.py ^BSESN

# Analyze Dow Jones
python run_dashboard.py ^DJI

# Analyze Bank Nifty
python run_dashboard.py ^NSEBANK
```

### Use as Python Module

```python
from smart_trading_dashboard import SmartTradingDashboard

# Create dashboard
dashboard = SmartTradingDashboard()

# Analyze market
results = dashboard.analyze_market('^NSEI')

# Display results
dashboard.display_results(results)

# Access specific data
print(f"Market Bias: {results['market_bias']}")
print(f"Bullish %: {results['bias_data']['bullish_bias_pct']:.1f}%")
print(f"Condition: {results['market_condition']}")
```

### Custom Configuration

```python
from smart_trading_dashboard import SmartTradingDashboard

# Custom config
config = {
    'bias_strength': 55,  # Lower threshold (more sensitive)
    'divergence_threshold': 65,
    'range_pct_threshold': 2.5,
    'normal_fast_weight': 3.0,  # Increase fast signal weight
    'atr_multiplier': 2.0,  # Wider stop loss
}

dashboard = SmartTradingDashboard(config=config)
results = dashboard.analyze_market('^NSEI')
dashboard.display_results(results)
```

## Output Tables

### 1. Stocks Dashboard
Shows all tracked stocks with:
- Current LTP (Last Traded Price)
- Daily change and %
- 15-minute timeframe %
- 1-hour timeframe %
- Status indicator (🟢/🔴)

### 2. Market Averages
- Weighted average of all stocks
- US Market (Dow Jones) performance
- USD/INR forex movement

### 3. Technical Indicators
Current values and signals for:
- VWAP, RSI, MFI, ADX, DI+, DI-

### 4. Market Condition
- Current condition (TRENDING UP/DOWN, RANGE-BOUND, TRANSITION)
- Movement quality and strength
- Range levels (if range-bound)
- EMA spread percentage

### 5. Market Bias Analysis
**Comprehensive bias breakdown:**
- Current mode (NORMAL/REVERSAL)
- Overall market bias (BULLISH/BEARISH/NEUTRAL)
- Bullish and Bearish bias percentages
- Fast signals breakdown
- Medium signals breakdown
- Slow signals breakdown
- Divergence alerts

### 6. Trading Signal
**Actionable trading recommendations:**
- Current signal (BULLISH/BEARISH/NEUTRAL)
- Entry strategy
- Entry zones/levels
- Target levels
- Special alerts (divergence, breakout potential)

## Understanding the Output

### Market Bias Interpretation

```
Bullish Bias: 75%  →  Strong bullish sentiment, look for LONG
Bearish Bias: 25%

Bullish Bias: 45%  →  Neutral, wait for clear signal
Bearish Bias: 55%

Bullish Bias: 30%  →  Strong bearish sentiment, look for SHORT
Bearish Bias: 70%
```

### Reversal Mode

When divergence is detected between:
- Stocks moving UP (slow signals bullish)
- But technicals showing DOWN (fast signals bearish)

The system enters REVERSAL MODE and prioritizes fast signals to catch the reversal early.

### Range-Bound Markets

When detected, the dashboard shows:
- Range High: Resistance level
- Range Low: Support level
- Range Mid: Pivot level

**Strategy:** Buy near low, sell near high, use tight stops.

### Trading Signals

**BULLISH Signal:**
- Wait for price to touch support (pivot low or range low)
- Enter LONG when price bounces
- Target: Next resistance or range high
- Stop loss: Below support

**BEARISH Signal:**
- Wait for price to touch resistance (pivot high or range high)
- Enter SHORT when price rejects
- Target: Next support or range low
- Stop loss: Above resistance

## Configuration Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `bias_strength` | 60 | 50-90 | Minimum % for directional bias |
| `divergence_threshold` | 60 | 50-80 | % for divergence detection |
| `range_pct_threshold` | 2.0 | 0.5-5.0 | % range for range-bound detection |
| `range_min_bars` | 20 | 10-100 | Minimum bars in range |
| `normal_fast_weight` | 2.0 | 1.0-5.0 | Normal mode: fast signal weight |
| `normal_medium_weight` | 3.0 | 1.0-5.0 | Normal mode: medium signal weight |
| `normal_slow_weight` | 5.0 | 1.0-10.0 | Normal mode: slow signal weight |
| `reversal_fast_weight` | 5.0 | 1.0-10.0 | Reversal mode: fast signal weight |
| `reversal_medium_weight` | 3.0 | 1.0-5.0 | Reversal mode: medium signal weight |
| `reversal_slow_weight` | 2.0 | 1.0-5.0 | Reversal mode: slow signal weight |
| `atr_multiplier` | 1.5 | 0.5-5.0 | ATR multiplier for stop loss |
| `risk_reward_ratio` | 2.0 | 1.0-5.0 | Target calculation multiplier |

## Key Differences from Pine Script

1. **Data Source**: Uses Yahoo Finance instead of TradingView data
2. **Real-time Updates**: Fetches latest data on each run (not streaming)
3. **Visualization**: Console tables instead of chart overlays
4. **Alerts**: Prints to console instead of TradingView alerts
5. **Pivots**: Calculated differently due to data granularity

## Features Implemented

✅ Multi-stock tracking with weights
✅ Multi-timeframe analysis (Daily, 15m, 1h)
✅ All technical indicators (RSI, MFI, DMI, VWAP, VIDYA, ATR)
✅ Adaptive bias calculation
✅ Reversal mode with divergence detection
✅ Range-bound market detection
✅ Order block detection
✅ Volume analysis
✅ Market condition classification
✅ Trading signal generation
✅ Comprehensive tabulated output
✅ US Market and Forex integration

## Limitations

1. **Pivot Levels**: HTF pivots (3m, 5m, 15m) require intraday data which may have limitations with free Yahoo Finance API
2. **Real-time Data**: Yahoo Finance has ~15min delay for free tier
3. **Volume Order Blocks**: Full VOB implementation requires more granular historical data
4. **Backtesting**: Not included in this version (Pine Script strategy feature)

## Future Enhancements

- [ ] Real-time streaming data integration
- [ ] Advanced pivot calculation with multiple timeframes
- [ ] VOB entry/exit signal refinement
- [ ] Email/SMS alerts
- [ ] Web dashboard with charts
- [ ] Backtesting module
- [ ] Trade logging and performance tracking
- [ ] Multi-symbol watchlist scanning

## Support

For issues, improvements, or questions about the conversion, please refer to the original Pine Script or create an issue in the repository.

## License

This is a conversion of the Pine Script indicator. Original script is subject to Mozilla Public License 2.0.

---

**Disclaimer**: This tool is for educational and informational purposes only. It is not financial advice. Always do your own research and consult with a qualified financial advisor before making trading decisions.
