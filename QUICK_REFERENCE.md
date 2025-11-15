# QUICK REFERENCE - File Paths & Classes

## Main Entry Points

1. **Main Streamlit Web App:**
   - File: `/home/user/nifty-sensex-trader/app.py`
   - Command: `streamlit run app.py`
   - Size: 1,686 lines

2. **CLI Dashboard:**
   - File: `/home/user/nifty-sensex-trader/run_dashboard.py`
   - Command: `python run_dashboard.py [symbol]`
   - Default: `^NSEI` (Nifty 50)

## Core Bias Analysis Classes

### 1. SmartTradingDashboard (3-Tier Adaptive Bias)
- **File:** `/home/user/nifty-sensex-trader/smart_trading_dashboard.py` (870 lines)
- **Class:** `SmartTradingDashboard`
- **Main Method:** `analyze_market(symbol)`
- **Returns:** dict with market_bias, condition, indicators, bias_data
- **Key Features:**
  - 3-tier signal system (Fast/Medium/Slow)
  - Adaptive weighting (Normal vs Reversal mode)
  - Range detection
  - Divergence detection

### 2. BiasAnalysisPro (15+ Indicator Scoring)
- **File:** `/home/user/nifty-sensex-trader/bias_analysis.py` (790 lines)
- **Class:** `BiasAnalysisPro`
- **Main Method:** `analyze_all_bias_indicators(symbol)`
- **Returns:** dict with overall_bias, overall_score, confidence, bias_results
- **Key Features:**
  - 15 individual indicators
  - Weighted scoring system
  - Market breadth analysis
  - Divergence detection

### 3. OptionChainAnalyzer
- **File:** `/home/user/nifty-sensex-trader/option_chain_analysis.py`
- **Class:** `OptionChainAnalyzer`
- **Purpose:** NSE options analysis with bias detection

### 4. AdvancedChartAnalysis
- **File:** `/home/user/nifty-sensex-trader/advanced_chart_analysis.py`
- **Purpose:** TradingView-style charts with 5 advanced indicators

### 5. SignalManager
- **File:** `/home/user/nifty-sensex-trader/signal_manager.py`
- **Purpose:** Manage trade signal setups

## Supporting Files

- **TradeExecutor:** `/home/user/nifty-sensex-trader/trade_executor.py`
- **DhanAPI:** `/home/user/nifty-sensex-trader/dhan_api.py`
- **TelegramBot:** `/home/user/nifty-sensex-trader/telegram_alerts.py`
- **Configuration:** `/home/user/nifty-sensex-trader/config.py`

## Tab-to-File Mapping

| Tab | File | Class/Module | Lines |
|-----|------|--------------|-------|
| Trade Setup | app.py | SignalManager | 234-330 |
| Active Signals | app.py | SignalManager | 336-434 |
| Positions | app.py | TradeExecutor, DhanAPI | 440-494 |
| Smart Trading | smart_trading_dashboard.py | SmartTradingDashboard | 500-765 |
| Bias Pro | bias_analysis.py | BiasAnalysisPro | 771-1149 |
| Option Chain | option_chain_analysis.py | OptionChainAnalyzer | 1153-1193 |
| Advanced Charts | advanced_chart_analysis.py | AdvancedChartAnalysis | 1199-1400+ |

## Indicators Module

**Directory:** `/home/user/nifty-sensex-trader/indicators/`

Files:
- `__init__.py`
- `om_indicator.py` - Order Flow & Momentum
- `htf_volume_footprint.py` - Higher Timeframe Volume Footprint
- `htf_support_resistance.py` - HTF Support/Resistance
- `volume_order_blocks.py` - Volume Order Blocks
- `ultimate_rsi.py` - Enhanced RSI

## Key Concepts

### Bias Score Ranges
- BULLISH: score > 30
- BEARISH: score < -30
- NEUTRAL: -30 to +30

### Bias Strength Threshold
- Default: 60% (bullish_bias_pct >= 60 for BULLISH signal)

### Adaptive Weights (SmartTradingDashboard)

**Normal Mode:**
```
Fast weight = 2.0, Medium = 3.0, Slow = 5.0
Favors longer-term trends
```

**Reversal Mode:**
```
Fast weight = 5.0, Medium = 3.0, Slow = 2.0
Triggers when divergence detected
Favors short-term reversal signals
```

### 15 Bias Indicators (BiasAnalysisPro)

Grouped by category:

**Technical (5):**
1. RSI - weight 1.5
2. MFI - weight 1.5
3. DMI/ADX - weight 2.0
4. VWAP - weight 1.5
5. EMA Crossover - weight 2.0

**Volume (4):**
6. Volume ROC - weight 1.5
7. OBV - weight 2.0
8. Force Index - weight 1.5
9. Volume Trend - weight 1.5

**Momentum (3):**
10. Price Momentum (ROC) - weight 1.5
11. RSI Divergence - weight 2.5
12. Choppiness Index - weight 1.5

**Market-Wide (3):**
13. Market Breadth - weight 3.0
14. Volatility Ratio - weight 1.0
15. ATR Trend - weight 1.0

## Configuration

Default timeframes:
- TF1: 15 minutes
- TF2: 1 hour
- Daily: 1 day

Default stocks analyzed (9):
1. RELIANCE.NS (9.98%)
2. HDFCBANK.NS (9.67%)
3. BHARTIARTL.NS (9.97%)
4. TCS.NS (8.54%)
5. ICICIBANK.NS (8.01%)
6. INFY.NS (8.55%)
7. HINDUNILVR.NS (1.98%)
8. ITC.NS (2.44%)
9. MARUTI.NS (0.0%)

## Data Fetching

- **Source:** Yahoo Finance API (yfinance)
- **Intraday Data:** 5-day history with 5-minute interval (Yahoo Finance limitation)
- **Daily Data:** 60-day or 7-day history with 1-day interval

## Session State Auto-Refresh

- **Interval:** 30 seconds (AUTO_REFRESH_INTERVAL)
- **Mechanism:** Streamlit rerun() function
- **Triggered by:** time.time() - last_refresh > threshold
