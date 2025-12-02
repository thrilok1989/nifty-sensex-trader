# 📱 Telegram Alerts Guide

## Overview

The app sends Telegram messages **ONLY** for specific high-confidence trading conditions. This guide explains when and what messages you'll receive.

---

## ✅ When Telegram Messages Are Sent

The app has **CONDITIONAL MESSAGING** - it only sends alerts when specific criteria are met. There are **3 main alert types**:

### 1. 🎯 Technical Indicators Alignment Alert

**File**: `bias_analysis.py` (line 984-1008)

**Trigger Conditions**:
- ✅ Overall bias is NOT neutral (must be BULLISH or BEARISH)
- ✅ At least **6 out of 8 fast indicators** align in the same direction

**Fast Indicators Monitored** (8 total):
1. Volume Delta
2. High Volume Pivots (HVP)
3. Volume Order Blocks (VOB)
4. Order Blocks (EMA 5/18)
5. RSI (Relative Strength Index)
6. DMI (Directional Movement Index)
7. VIDYA (Variable Index Dynamic Average)
8. MFI (Money Flow Index)

**Message Format**:
```
🎯 TECHNICAL INDICATORS ALIGNMENT 🎯

Symbol: NIFTY/SENSEX
Current Price: ₹XX,XXX.XX
Overall Bias: BULLISH/BEARISH
Bias Score: XX.X%
Confidence: XX.X%

Fast Indicators (8):
  🐂 Bullish: 6/8  (or)  🐻 Bearish: 6/8

Indicator Details:
  • Volume Delta: BULLISH (XX.XX)
  • HVP: BULLISH (X)
  • VOB: BULLISH
  • Order Blocks: BULLISH
  • RSI: BULLISH (XX.XX)
  • DMI: BULLISH (X.XX)
  • VIDYA: BULLISH
  • MFI: BULLISH (XX.XX)

Time: HH:MM:SS AM/PM
```

**What This Means**:
- Strong technical alignment across multiple indicators
- High probability directional move
- Good time to look for entry setups

---

### 2. 📊 PCR Analysis Alert

**File**: `overall_market_sentiment.py` (line 474-509)

**Trigger Conditions**:
- ✅ Overall PCR bias is NOT neutral (must be BULLISH or BEARISH)
- ✅ At least **2 indices** are analyzed (typically NIFTY & SENSEX)
- ✅ **Both indices show same bias** (both bullish OR both bearish)

**PCR Metrics Analyzed**:
- **PCR (OI)**: Put-Call Ratio based on Total Open Interest
  - > 1.0 = More puts than calls (Bullish)
  - < 1.0 = More calls than puts (Bearish)
- **PCR (Δ OI)**: Put-Call Ratio based on Change in Open Interest
  - Shows where new positions are being added

**Message Format**:
```
📊 PCR ANALYSIS ALERT 📊

Overall Bias: BULLISH/BEARISH 🐂/🐻
Score: ±XX.X
Confidence: XX.X%

Instruments Analyzed: 2
  🐂 Bullish: 2  (or)  🐻 Bearish: 2

PCR Details:

  NIFTY:
    • Spot: ₹ XX,XXX.XX
    • PCR (OI): X.XX - BULLISH 🐂
    • PCR (Δ OI): X.XX - BULLISH 🐂

  SENSEX:
    • Spot: ₹ XX,XXX.XX
    • PCR (OI): X.XX - BULLISH 🐂
    • PCR (Δ OI): X.XX - BULLISH 🐂

Time: HH:MM:SS AM/PM
```

**What This Means**:
- Both major indices show same directional bias
- Options market positioning confirms the trend
- Strong institutional/smart money signal

---

### 3. ⚡ ATM Option Chain Alert

**File**: `nse_options_helpers.py` (line 627-654)

**Trigger Conditions**:
- ✅ **Bias Score ≥ 4** (for bullish CALL signals)
- ✅ **Bias Score ≤ -4** (for bearish PUT signals)
- ✅ Market view matches bias (e.g., "Bullish" for CALL signals)
- ✅ Current price is in support/resistance zone
- ✅ Strike is at ATM ±2 strikes

**13 Bias Metrics Analyzed**:
1. Change in OI (ChgOI) Bias
2. Volume Bias
3. Gamma Bias
4. Ask Qty Bias
5. Bid Qty Bias
6. IV (Implied Volatility) Bias
7. DVP (Delta-Volume-Price) Bias
8. Price Action Bias
9. Vanna Bias
10. Charm Bias
11. Vomma Bias
12. Color Bias
13. Speed Bias

**Message Format**:
```
📍 NIFTY Spot: XX,XXX.XX
🔹 CALL Entry (Bias Based at Support)
   OR
🔹 PUT Entry (Bias Based at Resistance)

Strike: XXXXX CE/PE @ ₹XXX.XX | 🎯 Target: ₹XXX.XX | 🛑 SL: ₹XXX.XX
Bias Score (ATM ±2): +X (Bullish) or -X (Bearish)
Level: Support/Resistance

📉 Support Zone: XX,XXX to XX,XXX
📈 Resistance Zone: XX,XXX to XX,XXX

Biases:
Strike: XXXXX
ChgOI: BULLISH, Volume: BULLISH, Gamma: BULLISH,
AskQty: BULLISH, BidQty: BULLISH, IV: BULLISH, DVP: BULLISH
```

**What This Means**:
- Specific strike price entry signal
- Clear target and stop-loss levels
- Strong option chain bias at key support/resistance

---

### 4. 🤖 AI Market Analysis Alert

**File**: `integrations/ai_market_engine.py` (line 246-248)

**Trigger Conditions**:
- ✅ AI analysis is enabled (API keys configured)
- ✅ Market sentiment is **directional** (BULLISH or BEARISH, not NEUTRAL)
- ✅ **Confidence ≥ 60%** (default threshold, configurable via `AI_TELEGRAM_CONFIDENCE` env variable)
- ✅ `telegram_send=True` parameter is passed

**AI Analysis Process**:
1. **Technical Score** (60% weight): Aggregates all 13 technical indicators
2. **News Score** (30% weight): LLaMA AI analyzes real-time market news
3. **Meta Score** (10% weight): Volatility, volume changes, market metrics
4. **Final Reasoning**: LLaMA AI provides verdict with reasoning

**Message Format**:
```
🟢/🔴 🤖 AI MARKET REPORT

Market: Indian Stock Market
Bias: 🟢 BULLISH / 🔴 BEARISH
Recommendation: BUY / SELL / HOLD

📊 SCORES
Confidence: 0.XX (XX%)
AI Score: +X.XXX
Technical Score: +X.XXX
News Score: +X.XXX

⚙️ TECHNICAL SUMMARY
htf_sr: Bullish (+X.XXX)
vob: Bullish (+X.XXX)
overall_sentiment: Bullish (+X.XXX)
option_chain: Bullish (+X.XXX)
proximity_alerts: Bullish (+X.XXX)

📰 NEWS SUMMARY
[AI-generated summary of top market news headlines]

🧠 AI REASONING
1. [First key reason]
2. [Second key reason]
3. [Third key reason]
4. [Fourth key reason]

📋 SUMMARY
[AI-generated comprehensive market summary and recommendation]

⏰ Time (IST): YYYY-MM-DD HH:MM:SS IST
```

**What This Means**:
- AI has analyzed technical indicators + news + market data
- High confidence directional prediction
- Comprehensive reasoning provided
- Actionable BUY/SELL/HOLD recommendation

---

## ❌ What Does NOT Trigger Alerts

The app **DOES NOT** send messages for:
- ❌ Normal price updates
- ❌ Data refresh cycles
- ❌ Neutral market conditions
- ❌ Partial indicator alignment (< 6 indicators)
- ❌ Single index bias (need both NIFTY & SENSEX for PCR alerts)
- ❌ Low bias scores (< ±4 for ATM alerts)
- ❌ Low AI confidence (< 60%)
- ❌ Errors or warnings
- ❌ General market updates

---

## 📋 Alert Frequency

### Normal Market Conditions:
- **0-2 alerts per hour** (only when conditions are met)
- Most of the time: **NO alerts** (waiting for high-confidence setups)

### High Volatility / Strong Trending Market:
- **3-5 alerts per hour** (multiple confirmations)
- Alerts come in clusters when all 3 conditions align

### Typical Day:
- **Morning**: 1-2 alerts (market opening momentum)
- **Mid-day**: 0-1 alerts (consolidation)
- **Afternoon**: 1-2 alerts (directional moves)
- **Total**: 2-5 alerts per trading session

---

## 🔔 Alert Priority Levels

### 🔥 Highest Priority (Triple Alignment):
When you receive **all 3 alerts within 5-10 minutes**:
1. ✅ Technical Indicators Aligned (6+ of 8)
2. ✅ PCR Analysis Aligned (both indices)
3. ✅ ATM Option Chain Signal (bias score ±4+)

**Action**: This is a very strong signal - consider taking position

---

### ⚡ High Priority (Double Alignment):
When you receive **any 2 of the 3 alerts**:
- Technical + PCR
- Technical + ATM
- PCR + ATM

**Action**: Strong signal - wait for third confirmation or enter with caution

---

### ⚠️ Medium Priority (Single Alert):
When you receive **only 1 alert**:
- Technical OR PCR OR ATM alone

**Action**: Potential signal - wait for more confirmation

---

### 🤖 AI Enhancement:
When **AI alert** is received:
- Adds comprehensive analysis with reasoning
- Confirms or questions the technical signals
- Provides news context

**Action**: Use AI reasoning to validate other signals

---

## 🛠️ Configuration

### Telegram Bot Setup

Credentials are stored in `.streamlit/secrets.toml`:

```toml
[TELEGRAM]
BOT_TOKEN = "your_telegram_bot_token"
CHAT_ID = "your_telegram_chat_id"
```

### AI Alert Threshold

To change AI confidence threshold for Telegram alerts:

```bash
# Default: 60% (0.60)
export AI_TELEGRAM_CONFIDENCE=0.70  # Only send if AI confidence > 70%
```

---

## 📊 Alert Types Summary Table

| Alert Type | Trigger Condition | Frequency | Priority |
|------------|------------------|-----------|----------|
| **Technical Indicators** | 6+ of 8 fast indicators aligned | Low (0-2/hour) | High ⚡ |
| **PCR Analysis** | Both NIFTY & SENSEX aligned | Low (0-2/hour) | High ⚡ |
| **ATM Option Chain** | Bias score ±4+ at key levels | Medium (0-3/hour) | Medium ⚠️ |
| **AI Market Report** | Confidence ≥ 60%, directional | Very Low (0-1/hour) | Highest 🔥 |

---

## 📝 Alert Log Example

**Typical alert sequence during a strong bullish move**:

```
09:35 AM - 🎯 TECHNICAL INDICATORS ALIGNMENT (NIFTY: BULLISH, 7/8 indicators)
09:37 AM - 📊 PCR ANALYSIS ALERT (Both NIFTY & SENSEX: BULLISH)
09:40 AM - ⚡ ATM OPTION CHAIN (NIFTY 25000 CE @ ₹120, Target: ₹140, SL: ₹96)
09:42 AM - 🤖 AI MARKET REPORT (BULLISH, 75% confidence, BUY recommendation)

[No more alerts for 45-60 minutes unless market reverses or new setup forms]
```

---

## 🎯 Best Practices

1. **Wait for Multiple Confirmations**:
   - Don't act on single alerts
   - Look for 2-3 confirmations within 10-15 minutes

2. **Check Alert Timing**:
   - First 15 min of market: High volatility, wait for stability
   - Last 30 min of market: Squaring off, ignore new entries

3. **Cross-Verify in App**:
   - Always check the Streamlit app dashboard
   - Look at charts and detailed analysis
   - Verify current price and levels

4. **Use AI Reasoning**:
   - Read AI reasoning to understand WHY
   - Check if news supports technical signals
   - Don't trade against high-confidence AI alerts

5. **Manage Risk**:
   - Alerts are signals, not guarantees
   - Always use stop-loss levels provided
   - Position size according to your risk tolerance

---

## 🚫 Disabled Alerts

The following alerts are **DISABLED** to reduce noise:

- ❌ General errors/warnings
- ❌ Data refresh notifications
- ❌ Single indicator bias changes
- ❌ Weak signals (< 6 indicators, < ±4 bias score)
- ❌ Neutral conditions
- ❌ Status updates

**Philosophy**: Only send high-confidence, actionable signals. Quality > Quantity.

---

## 📱 Sample Telegram Alert

Here's what you'll actually see on your phone:

```
🎯 TECHNICAL INDICATORS ALIGNMENT 🎯

Symbol: NIFTY
Current Price: ₹24,850.35
Overall Bias: BULLISH
Bias Score: 75.0%
Confidence: 75.0%

Fast Indicators (8):
  🐂 Bullish: 7/8
  🐻 Bearish: 1/8

Indicator Details:
  • Volume Delta: BULLISH (1500.50)
  • HVP: BULLISH (2)
  • VOB: BULLISH
  • Order Blocks: BULLISH
  • RSI: BULLISH (65.30)
  • DMI: BULLISH (25.80)
  • VIDYA: BULLISH
  • MFI: BEARISH (45.20)

Time: 09:35:42 AM
```

---

## 🔍 Troubleshooting

### Not Receiving Alerts?

**Possible reasons**:
1. ✅ **Working as intended** - conditions not met (most likely)
   - Check app dashboard to see current bias
   - Verify indicator counts (need 6+ for technical, both indices for PCR)

2. ❌ Telegram credentials not configured
   - Check `.streamlit/secrets.toml`
   - Test with Settings → Test Telegram Connection

3. ❌ Bot blocked or chat ID incorrect
   - Message the bot first: `/start`
   - Verify chat ID is correct

4. ❌ Market hours
   - Alerts only during trading hours (9:15 AM - 3:30 PM IST)
   - Check `is_within_trading_hours()` status in app

### Receiving Too Many Alerts?

**This should NOT happen** with the conditional messaging system. If you are:
1. Check if alerts are duplicates (same content, different timestamps)
2. Verify auto-refresh interval (should be 60-120 seconds)
3. Check if multiple instances of the app are running

### AI Alerts Not Working?

1. ✅ Verify API keys are configured:
   - `NEWSDATA_API_KEY` in `.streamlit/secrets.toml`
   - `GROQ_API_KEY` in `.streamlit/secrets.toml`

2. ✅ Check AI engine status in app:
   - Look for "AI Analysis" section
   - Should show "AI Available: ✅"

3. ✅ Verify trigger conditions:
   - Market must be directional (not NEUTRAL)
   - Confidence must be ≥ 60%
   - Check console logs for AI analysis attempts

---

## 📚 Related Documentation

- **AI Setup Guide**: See `AI_SETUP.md` for AI engine configuration
- **AI Fix Summary**: See `AI_FIX_SUMMARY.md` for technical details
- **Bias Analysis**: See `BIAS_ANALYSIS_QUICK_START.md` for indicator details

---

## 💡 Key Takeaway

**The app uses SMART, CONDITIONAL alerting**:
- ✅ Only sends alerts for high-confidence setups
- ✅ Multiple confirmation required before alert
- ✅ Quality over quantity approach
- ✅ Reduces noise, increases signal

**If you're not getting alerts** = Market is not showing strong directional bias yet. This is GOOD - wait for high-quality setups!

---

**Last Updated**: 2025-12-02
**Version**: 2.0 (Conditional Messaging Implementation)
