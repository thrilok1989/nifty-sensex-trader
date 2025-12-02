# 🎯 Triple Alignment Telegram Alert - Complete Guide

## Overview

When **ALL 3 bias indicators** align (all BULLISH or all BEARISH), the app sends a **Telegram alert**. This is considered the **strongest signal** in the entire system.

---

## 🔔 What Triggers the Alert?

### 3 Indicators That Must Align:

1. **📊 Technical Indicators** (from Bias Analysis Pro)
   - 13 total indicators (Fast, Medium, Slow)
   - Must show BULLISH or BEARISH bias
   - Source: `bias_analysis_results` in session state

2. **📈 PCR Analysis** (Put-Call Ratio)
   - Analyzes NIFTY, SENSEX, FINNIFTY, MIDCPNIFTY
   - Must show BULLISH or BEARISH bias
   - Source: `calculate_option_chain_pcr_sentiment()`

3. **⚡ ATM Option Chain** (At-The-Money Zone)
   - Analyzes 13 bias metrics for each instrument
   - Must show BULLISH or BEARISH bias
   - Source: `calculate_option_chain_atm_sentiment()`

---

## ✅ Exact Trigger Conditions

### File: `overall_market_sentiment.py` (lines 1377-1434)

```python
# Step 1: Check alignment
alignment_status = check_bias_alignment()

# Step 2: Verify all 3 are aligned
if alignment_status and alignment_status['aligned']:
    # aligned = True only if:
    # (technical == BULLISH AND pcr == BULLISH AND atm == BULLISH)
    # OR
    # (technical == BEARISH AND pcr == BEARISH AND atm == BEARISH)

    direction = alignment_status['direction']  # 'BULLISH' or 'BEARISH'
    confidence = alignment_status['confidence']  # 0-100

    # Step 3: Check if should send Telegram alert
    should_send_alert = (
        # Condition 1: Alignment alerts are enabled (checkbox in UI)
        st.session_state.get('enable_alignment_alerts', True) and

        # Condition 2: Never sent before OR direction changed
        (st.session_state.last_alignment_alert != current_alert_key or
         st.session_state.last_alignment_direction != direction)
    )

    # Step 4: Send alert if conditions met
    if should_send_alert:
        from telegram_alerts import TelegramBot
        telegram_bot = TelegramBot()

        alignment_data = {
            'direction': direction,
            'technical_bias': alignment_status['technical_bias'],
            'technical_score': alignment_status['technical_score'],
            'pcr_bias': alignment_status['pcr_bias'],
            'pcr_score': alignment_status['pcr_score'],
            'atm_bias': alignment_status['atm_bias'],
            'atm_score': alignment_status['atm_score'],
            'confidence': confidence
        }

        telegram_bot.send_bias_alignment_alert(alignment_data)
```

---

## 📋 Detailed Trigger Logic

### Step 1: Check Each Bias Individually

**Technical Indicators Bias**:
```python
# From bias_analysis_results
technical_bias = analysis.get('overall_bias', 'NEUTRAL')
# Values: 'BULLISH', 'BEARISH', or 'NEUTRAL'

# Threshold: 60% of indicators must agree
# Example: 8+ of 13 indicators bullish → BULLISH
```

**PCR Analysis Bias**:
```python
# From calculate_option_chain_pcr_sentiment()
pcr_bias = pcr_sentiment.get('bias', 'NEUTRAL')
# Values: 'BULLISH', 'BEARISH', or 'NEUTRAL'

# Threshold: overall_score > 10 → BULLISH
#            overall_score < -10 → BEARISH
```

**ATM Option Chain Bias**:
```python
# From calculate_option_chain_atm_sentiment()
atm_bias = atm_sentiment.get('bias', 'NEUTRAL')
# Values: 'BULLISH', 'BEARISH', or 'NEUTRAL'

# Threshold: overall_score > 30 → BULLISH
#            overall_score < -30 → BEARISH
```

---

### Step 2: Check for Alignment

```python
# Alignment check (overall_market_sentiment.py:966-971)
aligned = False
direction = None

# ALL BULLISH
if technical_bias == 'BULLISH' and pcr_bias == 'BULLISH' and atm_bias == 'BULLISH':
    aligned = True
    direction = 'BULLISH'

# ALL BEARISH
elif technical_bias == 'BEARISH' and pcr_bias == 'BEARISH' and atm_bias == 'BEARISH':
    aligned = True
    direction = 'BEARISH'

# ANY OTHER COMBINATION = NOT ALIGNED
# Examples that DON'T trigger:
# - Technical: BULLISH, PCR: BULLISH, ATM: NEUTRAL ❌
# - Technical: BULLISH, PCR: BEARISH, ATM: BULLISH ❌
# - Technical: NEUTRAL, PCR: NEUTRAL, ATM: NEUTRAL ❌
```

---

### Step 3: Calculate Confidence

```python
# If aligned, calculate confidence
if aligned:
    # Average the absolute scores
    avg_score = (abs(technical_score) + abs(pcr_score) + abs(atm_score)) / 3
    confidence = min(100, avg_score)

# Example:
# technical_score = 65
# pcr_score = 15
# atm_score = 40
# avg_score = (65 + 15 + 40) / 3 = 40
# confidence = 40%
```

---

### Step 4: Prevent Duplicate Alerts

```python
# Create unique alert key
current_alert_key = f"{direction}_{int(confidence)}"
# Example: "BULLISH_40"

# Only send if:
# 1. Checkbox is enabled (default: True)
# 2. First time OR direction changed

should_send_alert = (
    st.session_state.get('enable_alignment_alerts', True) and
    (
        # Never sent before
        st.session_state.last_alignment_alert != current_alert_key or

        # Direction changed (was BEARISH, now BULLISH)
        st.session_state.last_alignment_direction != direction
    )
)

# After sending, update state to prevent duplicates
st.session_state.last_alignment_alert = current_alert_key
st.session_state.last_alignment_direction = direction
```

---

## 📱 Telegram Message Format

### File: `telegram_alerts.py:407-479` (`send_bias_alignment_alert()`)

```
🚀 BIAS ALIGNMENT ALERT 🚀

🟢 BULLISH ALIGNMENT 🟢

━━━━━━━━━━━━━━━━━━━━

ALL 3 INDICATORS ALIGNED!

📊 TECHNICAL INDICATORS
  Bias: BULLISH
  Score: +65.00

📈 PCR ANALYSIS
  Bias: BULLISH
  Score: +15.00

⚡ ATM OPTION CHAIN
  Bias: BULLISH
  Score: +40.00

━━━━━━━━━━━━━━━━━━━━

Confidence: 40.0%

⏰ Time (IST): 2025-12-02 10:35:42 IST

🚀 This is a strong BULLISH signal!
```

---

## 🎯 Important Notes

### 1. **Symbol/Index Scope**

**Question**: Is this for NIFTY only or SENSEX too?

**Answer**: The alignment is based on **aggregated data across all indices**:

- **Technical Indicators**: Analyzes NIFTY (^NSEI) data
- **PCR Analysis**: Aggregates NIFTY, SENSEX, FINNIFTY, MIDCPNIFTY
- **ATM Option Chain**: Aggregates NIFTY, SENSEX, FINNIFTY, MIDCPNIFTY

So the alert represents **overall market alignment**, not just NIFTY or SENSEX individually.

However, **PCR and ATM require at least 2 indices to agree** (typically NIFTY + SENSEX).

---

### 2. **Alignment ≠ Overall Market Bias**

**Important Distinction**:

- **Triple Alignment**: Only checks if these 3 specific indicators agree
- **Overall Market Bias**: Combines 6 sources with weighted scoring

**Example**:
```
Technical: BULLISH (+65)
PCR: BULLISH (+15)
ATM: BULLISH (+40)
→ ALIGNED ✅ (Telegram alert sent)

But Overall Market Bias might still be NEUTRAL if:
- Stock Performance: BEARISH (-30)
- NIFTY Advanced: BEARISH (-35)
- AI Analysis: NEUTRAL (0)

Weighted average could be near 0 → NEUTRAL
```

So you can have:
- ✅ Triple alignment (Telegram alert)
- ⚪ Overall bias = NEUTRAL

---

### 3. **Alert Frequency**

**Deduplication Logic**:
- Alert is sent when alignment first occurs
- If alignment persists but confidence changes slightly, **NO new alert**
- If direction changes (BULLISH → BEARISH), **NEW alert sent**
- If alignment breaks and reforms later, **NEW alert sent**

**Example Timeline**:
```
10:00 AM - Technical: BULLISH, PCR: BULLISH, ATM: BULLISH
           → Alert sent ✅

10:05 AM - Still all BULLISH, confidence changed 40% → 42%
           → No alert (duplicate)

10:10 AM - Technical: NEUTRAL, PCR: BULLISH, ATM: BULLISH
           → No longer aligned, no alert

10:15 AM - Technical: BULLISH, PCR: BULLISH, ATM: BULLISH
           → Alignment reformed, NEW alert sent ✅

10:20 AM - Technical: BEARISH, PCR: BEARISH, ATM: BEARISH
           → Direction changed, NEW alert sent ✅
```

---

### 4. **User Control**

**Checkbox in UI**:
```
Location: Overall Market Sentiment tab, top-right
Label: "🔔 Alignment Alerts"
Default: Enabled (checked)

If unchecked → No Telegram alerts for alignment
               (UI still shows "ALL 3 INDICATORS ALIGNED")
```

---

## 🔍 How Each Bias is Determined

### Technical Indicators Bias

**Source**: Bias Analysis Pro (13 indicators for NIFTY)

**Determination**:
```python
bullish_pct = (bullish_count / total_count) * 100
bearish_pct = (bearish_count / total_count) * 100

if bullish_pct >= 60:  # 8+ of 13 indicators
    bias = "BULLISH"
elif bearish_pct >= 60:
    bias = "BEARISH"
else:
    bias = "NEUTRAL"
```

**Example**:
```
Bullish indicators: 9
Bearish indicators: 3
Neutral indicators: 1
Total: 13

bullish_pct = 9/13 * 100 = 69.2%
69.2% >= 60% → BULLISH ✅
```

---

### PCR Analysis Bias

**Source**: Put-Call Ratio for NIFTY, SENSEX, FINNIFTY, MIDCPNIFTY

**Determination**:
```python
# For each index:
oi_score = +20 (PCR > 1.2) or -20 (PCR < 0.8) or 0
change_score = +20 (put buying) or -20 (call buying) or 0
instrument_score = (oi_score + change_score) / 2

overall_score = average(all instrument scores)

if overall_score > 10:
    bias = "BULLISH"
elif overall_score < -10:
    bias = "BEARISH"
else:
    bias = "NEUTRAL"
```

**Example**:
```
NIFTY: PCR = 1.3 (Bullish) → +20
SENSEX: PCR = 1.25 (Bullish) → +20
FINNIFTY: PCR = 1.1 (Neutral) → 0
MIDCPNIFTY: PCR = 1.35 (Bullish) → +20

overall_score = (20 + 20 + 0 + 20) / 4 = 15
15 > 10 → BULLISH ✅
```

---

### ATM Option Chain Bias

**Source**: ATM zone analysis (13 bias metrics) for each index

**Determination**:
```python
# For each index, get ATM zone verdict:
# Verdicts: STRONG BULLISH, BULLISH, BEARISH, STRONG BEARISH, NEUTRAL

if verdict == "STRONG BULLISH":
    score = +75
elif verdict == "BULLISH":
    score = +40
elif verdict == "STRONG BEARISH":
    score = -75
elif verdict == "BEARISH":
    score = -40
else:
    score = 0

overall_score = average(all index scores)

if overall_score > 30:
    bias = "BULLISH"
elif overall_score < -30:
    bias = "BEARISH"
else:
    bias = "NEUTRAL"
```

**Example**:
```
NIFTY: BULLISH verdict → +40
SENSEX: BULLISH verdict → +40
FINNIFTY: NEUTRAL → 0
MIDCPNIFTY: BULLISH verdict → +40

overall_score = (40 + 40 + 0 + 40) / 4 = 30
30 >= 30 → BULLISH ✅ (just barely)
```

---

## ⚡ Real-World Example

### Scenario: Strong Bullish Setup

**10:00 AM - Market Data**:

1. **Technical Indicators** (NIFTY analysis):
   - 10 out of 13 indicators bullish
   - Bullish %: 76.9%
   - Bias: **BULLISH** ✅
   - Score: +76.9

2. **PCR Analysis** (All indices):
   - NIFTY PCR: 1.4 (Bullish)
   - SENSEX PCR: 1.3 (Bullish)
   - Average score: +18
   - Bias: **BULLISH** ✅
   - Score: +18

3. **ATM Option Chain** (All indices):
   - NIFTY ATM: STRONG BULLISH verdict
   - SENSEX ATM: BULLISH verdict
   - Average score: +42.5
   - Bias: **BULLISH** ✅
   - Score: +42.5

**Alignment Check**:
```
Technical: BULLISH ✅
PCR: BULLISH ✅
ATM: BULLISH ✅

→ ALL 3 ALIGNED! 🎯
→ Direction: BULLISH
→ Confidence: (76.9 + 18 + 42.5) / 3 = 45.8%
```

**Telegram Alert Sent**:
```
🚀 BIAS ALIGNMENT ALERT 🚀

🟢 BULLISH ALIGNMENT 🟢

━━━━━━━━━━━━━━━━━━━━

ALL 3 INDICATORS ALIGNED!

📊 TECHNICAL INDICATORS
  Bias: BULLISH
  Score: +76.90

📈 PCR ANALYSIS
  Bias: BULLISH
  Score: +18.00

⚡ ATM OPTION CHAIN
  Bias: BULLISH
  Score: +42.50

━━━━━━━━━━━━━━━━━━━━

Confidence: 45.8%

⏰ Time (IST): 2025-12-02 10:00:15 IST

🚀 This is a strong BULLISH signal!
```

---

## 💡 Trading Implications

### When You Receive This Alert:

**🟢 BULLISH Alignment**:
1. ✅ All 3 major analysis methods confirm upward bias
2. ✅ Technical indicators show momentum
3. ✅ Options market positioning (PCR) supports bulls
4. ✅ ATM option chain shows bullish activity

**Action**:
- Look for CALL entry opportunities
- Focus on support levels for entry
- Check AI analysis for additional confirmation
- Verify price is not overextended

---

**🔴 BEARISH Alignment**:
1. ✅ All 3 major analysis methods confirm downward bias
2. ✅ Technical indicators show negative momentum
3. ✅ Options market positioning (PCR) supports bears
4. ✅ ATM option chain shows bearish activity

**Action**:
- Look for PUT entry opportunities
- Focus on resistance levels for entry
- Check AI analysis for additional confirmation
- Verify price is not oversold

---

## 🎯 Summary

### Telegram Alert is Sent When:

✅ **Technical Indicators** = BULLISH/BEARISH (not NEUTRAL)
✅ **PCR Analysis** = BULLISH/BEARISH (not NEUTRAL)
✅ **ATM Option Chain** = BULLISH/BEARISH (not NEUTRAL)
✅ **All 3 show SAME direction** (all bullish OR all bearish)
✅ **Alignment alerts enabled** (checkbox checked)
✅ **First occurrence OR direction changed** (no duplicates)

### Data Scope:

- **Technical**: NIFTY (^NSEI) data
- **PCR**: NIFTY + SENSEX + FINNIFTY + MIDCPNIFTY (aggregated)
- **ATM**: NIFTY + SENSEX + FINNIFTY + MIDCPNIFTY (aggregated)

**So it represents overall market alignment, not just a single index!**

---

## 📄 Code References

- **Alignment Check**: `overall_market_sentiment.py:915-990` (`check_bias_alignment()`)
- **Telegram Sending**: `overall_market_sentiment.py:1377-1434`
- **Telegram Format**: `telegram_alerts.py:407-479` (`send_bias_alignment_alert()`)

---

**Last Updated**: 2025-12-02
