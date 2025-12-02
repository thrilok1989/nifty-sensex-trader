# 📊 Overall Market Bias Calculation - Complete Breakdown

## Overview

The **Overall Market Bias** is calculated by combining **6 different sentiment sources** with **weighted scoring**. Each source analyzes different aspects of the market, and they're combined to give a final BULLISH/BEARISH/NEUTRAL verdict.

---

## 🎯 6 Sentiment Sources

### 1. 📈 Stock Performance (Weight: 2.0)
**File**: `overall_market_sentiment.py` - `calculate_stock_performance_sentiment()`

**Data Source**: 10 weighted stocks from bias analysis
- RELIANCE.NS (9.98)
- HDFCBANK.NS (9.67)
- BHARTIARTL.NS (9.97)
- TCS.NS (8.54)
- ICICIBANK.NS (8.01)
- INFY.NS (8.55)
- And more...

**Calculation**:
```python
# For each stock:
weighted_change = stock_change_pct * stock_weight
total_weighted_change = sum(all weighted changes)
average_change = total_weighted_change / total_weight

# Score calculation:
if average_change > 1.0:
    score = +50 (Strong Bullish)
elif average_change > 0:
    score = +25 (Bullish)
elif average_change < -1.0:
    score = -50 (Strong Bearish)
elif average_change < 0:
    score = -25 (Bearish)
else:
    score = 0 (Neutral)
```

**Bias Determination**:
- `score > 15` → BULLISH
- `score < -15` → BEARISH
- Otherwise → NEUTRAL

---

### 2. 🎯 Technical Indicators (Weight: 3.0)
**File**: `overall_market_sentiment.py` - `calculate_technical_indicators_sentiment()`

**Data Source**: 13 bias indicators from BiasAnalysisPro

**Fast Indicators (8)**: Volume Delta, HVP, VOB, Order Blocks, RSI, DMI, VIDYA, MFI
**Medium Indicators (2)**: Close vs VWAP, Price vs VWAP
**Slow Indicators (3)**: Weighted stocks (Daily, TF1, TF2)

**Calculation**:
```python
# For each indicator:
weighted_score = indicator_score * indicator_weight
total_weighted_score = sum(all weighted scores)
average_score = total_weighted_score / total_weight

# Count bullish/bearish indicators
bullish_pct = (bullish_count / total_count) * 100
bearish_pct = (bearish_count / total_count) * 100

# Final score:
if bullish_pct > 60:
    score = +bullish_pct
elif bearish_pct > 60:
    score = -bearish_pct
else:
    score = average_score (from -100 to +100)
```

**Bias Determination**:
- `score > 20` → BULLISH
- `score < -20` → BEARISH
- Otherwise → NEUTRAL

---

### 3. 📊 PCR Analysis (Weight: 2.5)
**File**: `overall_market_sentiment.py` - `calculate_option_chain_pcr_sentiment()`

**Data Source**: Put-Call Ratio from NIFTY, SENSEX, FINNIFTY, MIDCPNIFTY

**PCR Metrics**:
- **PCR (OI)**: Put OI / Call OI
- **PCR (Δ OI)**: Put Change in OI / Call Change in OI

**Calculation for each instrument**:
```python
# OI Bias scoring:
pcr_oi = total_pe_oi / total_ce_oi

if pcr_oi > 1.2:
    oi_score = +20 (Bullish - More puts, hedging)
elif pcr_oi < 0.8:
    oi_score = -20 (Bearish - More calls, hedging)
else:
    oi_score = 0 (Neutral)

# Change in OI Bias scoring:
pcr_change_oi = abs(total_pe_change) / abs(total_ce_change)

if pcr_change_oi > 1.2 and total_pe_change > 0:
    change_score = +20 (Bullish - Put buying)
elif pcr_change_oi < 0.8 and total_ce_change > 0:
    change_score = -20 (Bearish - Call buying)
else:
    change_score = 0

# Combined score for instrument:
instrument_score = (oi_score + change_score) / 2

# Overall:
overall_score = average of all instrument scores
```

**Bias Determination**:
- `overall_score > 10` → BULLISH
- `overall_score < -10` → BEARISH
- Otherwise → NEUTRAL

---

### 4. ⚡ Option Chain ATM Analysis (Weight: 2.0)
**File**: `overall_market_sentiment.py` - `calculate_option_chain_atm_sentiment()`

**Data Source**: ATM Zone analysis from NIFTY, SENSEX, FINNIFTY, MIDCPNIFTY

**ATM Zone Bias Metrics (13 total)**:
- ChgOI, Volume, Gamma, Ask/Bid Qty, IV, DVP
- Delta Exposure, Gamma Exposure, IV Skew
- And more...

**Calculation**:
```python
# For each instrument, get ATM zone verdict:
verdict = ATM_zone_verdict  # From nse_options_helpers.py

# Score assignment:
if verdict == "STRONG BULLISH":
    score = +75
elif verdict == "BULLISH":
    score = +40
elif verdict == "STRONG BEARISH":
    score = -75
elif verdict == "BEARISH":
    score = -40
else:
    score = 0 (Neutral)

# Overall:
overall_score = average of all instrument scores
```

**Bias Determination**:
- `overall_score > 30` → BULLISH
- `overall_score < -30` → BEARISH
- Otherwise → NEUTRAL

---

### 5. 📐 NIFTY Advanced Metrics (Weight: 2.5)
**File**: `overall_market_sentiment.py` - `calculate_nifty_advanced_metrics_sentiment()`

**Data Source**: Advanced option chain metrics for NIFTY

**Metrics Analyzed**:
1. **ATM Buildup Pattern** (Weight: 25 points)
   - Short Buildup/Put Writing/Short Covering → +25 (Bullish)
   - Long Buildup/Call Writing/Long Unwinding → -25 (Bearish)

2. **Total Vega Bias** (Weight: 15 points)
   - Bullish (Put Heavy) → +15
   - Bearish (Call Heavy) → -15

3. **Distance from Call Resistance/Put Support** (Weight: 10 points)
   - Near Call Resistance (< 50 pts) → -10 (Bearish)
   - Near Put Support (< 50 pts) → +10 (Bullish)

4. **Display-Only Metrics** (Not scored):
   - Synthetic Future Bias
   - ATM Vega Bias
   - Distance from Max Pain

**Calculation**:
```python
score = 0

# ATM Buildup (max ±25)
if "SHORT BUILDUP" or "PUT WRITING" in buildup:
    score += 25
elif "LONG BUILDUP" or "CALL WRITING" in buildup:
    score -= 25

# Total Vega (max ±15)
if total_vega == "BULLISH":
    score += 15
elif total_vega == "BEARISH":
    score -= 15

# Resistance/Support proximity (max ±10)
if near_call_resistance:
    score -= 10
elif near_put_support:
    score += 10

# Final score range: -50 to +50
```

**Bias Determination**:
- `score > 30` → BULLISH
- `score < -30` → BEARISH
- Otherwise → NEUTRAL

---

### 6. 🤖 AI Market Analysis (Weight: 4.0) ⭐ HIGHEST
**File**: `overall_market_sentiment.py` - `calculate_ai_analysis_sentiment()`

**Data Source**: AI-powered analysis combining technical + news + market metadata

**AI Analysis Process**:
1. **Technical Score (60%)**: All 13 technical indicators
2. **News Score (30%)**: LLaMA AI analysis of market news
3. **Meta Score (10%)**: Volatility, volume changes

**Calculation**:
```python
ai_report = run_ai_analysis(...)

# Extract AI score (range: -1.0 to +1.0)
ai_score = ai_report.get('ai_score', 0)
confidence = ai_report.get('confidence', 0)  # 0 to 1

# Convert to 0-100 scale
score = ai_score * 100  # Now -100 to +100

# Apply confidence weighting
final_score = score * confidence

# Example:
# ai_score = 0.65 (bullish)
# confidence = 0.75 (75%)
# score = 0.65 * 100 = 65
# final_score = 65 * 0.75 = 48.75
```

**Bias Determination**:
- `final_score > 20` → BULLISH
- `final_score < -20` → BEARISH
- Otherwise → NEUTRAL

---

## 🧮 Final Overall Bias Calculation

### Step 1: Weighted Score Calculation

```python
source_weights = {
    'Stock Performance': 2.0,
    'Technical Indicators': 3.0,
    'PCR Analysis': 2.5,
    'Option Chain Analysis': 2.0,
    'NIFTY Advanced Metrics': 2.5,
    '🤖 AI Market Analysis': 4.0  # HIGHEST WEIGHT
}

total_weighted_score = 0
total_weight = 0

for each source:
    weighted_score = source_score * source_weight
    total_weighted_score += weighted_score
    total_weight += source_weight

overall_score = total_weighted_score / total_weight
```

### Step 2: Overall Sentiment Determination

```python
if overall_score > 25:
    overall_sentiment = "BULLISH"
elif overall_score < -25:
    overall_sentiment = "BEARISH"
else:
    overall_sentiment = "NEUTRAL"
```

### Step 3: Confidence Calculation

```python
# Base confidence from score magnitude
score_magnitude = min(100, abs(overall_score))

# Calculate source agreement
if overall_sentiment == "BULLISH":
    source_agreement = bullish_sources / total_sources
elif overall_sentiment == "BEARISH":
    source_agreement = bearish_sources / total_sources
else:
    source_agreement = neutral_sources / total_sources

# Final confidence
final_confidence = score_magnitude * source_agreement

# Example:
# overall_score = 45 (bullish)
# score_magnitude = 45
# 4 sources bullish, 1 bearish, 1 neutral (6 total)
# source_agreement = 4/6 = 0.667
# final_confidence = 45 * 0.667 = 30%
```

---

## 📊 Example Calculation

Let's walk through a real example:

### Input Data:
```
Stock Performance: BULLISH (+30)
Technical Indicators: BULLISH (+65)
PCR Analysis: BULLISH (+15)
Option Chain ATM: BULLISH (+40)
NIFTY Advanced: NEUTRAL (0)
AI Analysis: BULLISH (+48.75)
```

### Step 1: Weighted Scoring
```
Stock Performance:    30 * 2.0 = 60
Technical Indicators: 65 * 3.0 = 195
PCR Analysis:         15 * 2.5 = 37.5
Option Chain ATM:     40 * 2.0 = 80
NIFTY Advanced:        0 * 2.5 = 0
AI Analysis:       48.75 * 4.0 = 195

Total Weighted Score = 567.5
Total Weight = 16.0

Overall Score = 567.5 / 16.0 = 35.47
```

### Step 2: Overall Sentiment
```
overall_score = 35.47
35.47 > 25 → BULLISH ✅
```

### Step 3: Confidence
```
score_magnitude = min(100, 35.47) = 35.47

Bullish sources: 5 (Stock, Tech, PCR, ATM, AI)
Bearish sources: 0
Neutral sources: 1 (NIFTY Advanced)
Total sources: 6

source_agreement = 5/6 = 0.833

final_confidence = 35.47 * 0.833 = 29.5%
```

### Final Result:
```
Overall Sentiment: BULLISH
Overall Score: +35.47
Confidence: 29.5%
```

---

## 🎯 Key Thresholds Summary

| Source | Bullish Threshold | Bearish Threshold | Weight |
|--------|------------------|-------------------|--------|
| Stock Performance | > +15 | < -15 | 2.0 |
| Technical Indicators | > +20 | < -20 | 3.0 |
| PCR Analysis | > +10 | < -10 | 2.5 |
| Option Chain ATM | > +30 | < -30 | 2.0 |
| NIFTY Advanced | > +30 | < -30 | 2.5 |
| AI Analysis | > +20 | < -20 | **4.0** ⭐ |
| **OVERALL** | **> +25** | **< -25** | **16.0** |

---

## 🔍 Important Notes

### 1. **AI Has Highest Weight (4.0)**
The AI analysis has the highest weight because it combines:
- All technical indicators (60%)
- Real-time news sentiment (30%)
- Market metadata (10%)
- LLaMA AI reasoning

This makes it the most comprehensive single source.

### 2. **Neutral Zone is Wide (-25 to +25)**
The overall sentiment only becomes BULLISH/BEARISH when the score exceeds ±25. This prevents false signals during choppy/sideways markets.

### 3. **Confidence Depends on Agreement**
High confidence requires:
- ✅ High score magnitude (far from 0)
- ✅ Most sources agreeing (5-6 out of 6)

Low confidence occurs when:
- ❌ Score is near neutral zone (close to 0)
- ❌ Sources are mixed (3 bullish, 3 bearish)

### 4. **Source Agreement is Critical**
Even if one source shows a strong signal (e.g., AI at +80), if other sources disagree (e.g., PCR at -15, ATM at -20), the overall score will be pulled toward neutral and confidence will drop.

### 5. **All Sources Must Be Directional for Strong Signal**
Best setups occur when:
- ✅ All 6 sources are BULLISH → High overall score + high confidence
- ✅ All 6 sources are BEARISH → Low overall score + high confidence

Worst setups occur when:
- ❌ 3 sources bullish, 3 bearish → Near-zero overall score + low confidence

---

## 📈 Score Ranges Explained

### Overall Score Interpretation:
- **+75 to +100**: Extremely Bullish (rare, all sources strongly aligned)
- **+50 to +75**: Very Bullish (most sources aligned)
- **+25 to +50**: Bullish (above threshold)
- **-25 to +25**: Neutral (below threshold)
- **-50 to -25**: Bearish (below threshold)
- **-75 to -50**: Very Bearish (most sources aligned)
- **-100 to -75**: Extremely Bearish (rare, all sources strongly aligned)

---

## 🎯 Visual Flow

```
┌─────────────────────────────────────────────────────────┐
│            6 SENTIMENT SOURCES                          │
└─────────────────────────────────────────────────────────┘
         │
         ├─► Stock Performance (Weight: 2.0) ─────► Score: -100 to +100
         │
         ├─► Technical Indicators (Weight: 3.0) ──► Score: -100 to +100
         │
         ├─► PCR Analysis (Weight: 2.5) ─────────► Score: -100 to +100
         │
         ├─► Option Chain ATM (Weight: 2.0) ─────► Score: -100 to +100
         │
         ├─► NIFTY Advanced (Weight: 2.5) ───────► Score: -100 to +100
         │
         └─► AI Analysis (Weight: 4.0) ⭐ ────────► Score: -100 to +100
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│         WEIGHTED SCORE CALCULATION                      │
│                                                          │
│  overall_score = Σ(source_score × weight) / Σ(weight)  │
│                                                          │
│  Total Weight = 16.0                                    │
└─────────────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│         OVERALL SENTIMENT DETERMINATION                 │
│                                                          │
│  if overall_score > 25:  → BULLISH                      │
│  if overall_score < -25: → BEARISH                      │
│  else:                   → NEUTRAL                      │
└─────────────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│         CONFIDENCE CALCULATION                          │
│                                                          │
│  score_magnitude = min(100, abs(overall_score))        │
│  source_agreement = aligned_sources / total_sources     │
│  final_confidence = score_magnitude × source_agreement  │
└─────────────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│              FINAL OUTPUT                               │
│                                                          │
│  Overall Sentiment: BULLISH / BEARISH / NEUTRAL        │
│  Overall Score: +XX.XX or -XX.XX                        │
│  Confidence: XX.X%                                      │
└─────────────────────────────────────────────────────────┘
```

---

## 🔧 How to Interpret the Overall Bias

### 🟢 BULLISH Signal
**Requirements**:
- Overall score > +25
- Most sources are bullish
- Higher confidence = stronger signal

**Action**:
- Look for CALL entry opportunities
- Focus on support levels
- Check AI reasoning for confirmation

---

### 🔴 BEARISH Signal
**Requirements**:
- Overall score < -25
- Most sources are bearish
- Higher confidence = stronger signal

**Action**:
- Look for PUT entry opportunities
- Focus on resistance levels
- Check AI reasoning for confirmation

---

### ⚪ NEUTRAL Signal
**Requirements**:
- Overall score between -25 and +25
- Sources are mixed or near zero
- Stay on sidelines

**Action**:
- Wait for clearer signal
- Don't force trades
- Monitor for breakout

---

## 💡 Pro Tips

1. **Wait for High Confidence**: Don't act on BULLISH/BEARISH signals with <20% confidence

2. **Check Source Agreement**: Best trades occur when 5-6 sources agree

3. **Use AI Reasoning**: Always read the AI reasoning to understand WHY

4. **Cross-Verify with Price Action**: Even with strong bias, check if price is at a good entry level

5. **Respect Neutral Signals**: The market is often neutral - don't force trades

---

**File Location**: `overall_market_sentiment.py:784-912` (`calculate_overall_sentiment()`)

**Last Updated**: 2025-12-02
