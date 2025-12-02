# AI Market Analysis Setup Guide

## Overview
The AI Market Analysis feature integrates news data and LLaMA AI model to provide enhanced market analysis with reasoning.

## Requirements

### 1. API Keys
You need two API keys to enable AI analysis:

#### NewsData API
- **Purpose**: Fetches real-time market news headlines
- **Get API Key**: https://newsdata.io/
- **Free Tier**: 200 requests/day
- **Pricing**: https://newsdata.io/pricing

#### Groq API
- **Purpose**: Provides LLaMA AI model for analysis
- **Get API Key**: https://console.groq.com/
- **Free Tier**: Available
- **Pricing**: https://console.groq.com/pricing

### 2. Python Dependencies
The AI engine requires the following Python package:

```bash
pip install groq
```

This is already included in the project's `requirements.txt`.

## Configuration

### ✅ Streamlit Secrets (Required)

Add the following to your `.streamlit/secrets.toml` file:

```toml
# AI + NEWS ENGINE KEYS (REQUIRED FOR AI ANALYSIS)
# These MUST be top-level keys (not nested)
NEWSDATA_API_KEY = "your_newsdata_api_key_here"
GROQ_API_KEY = "your_groq_api_key_here"
```

**Important Notes**:
- ✅ **Use top-level keys** (NEWSDATA_API_KEY, GROQ_API_KEY) - this is the recommended format
- ✅ The app loads these keys from `st.secrets` and passes them to the AI engine
- ✅ **No environment variables (.env) needed** - everything works through secrets.toml
- ✅ Alternative nested format is also supported:
  ```toml
  [NEWSDATA]
  API_KEY = "your_key"

  [GROQ]
  API_KEY = "your_key"
  MODEL = "llama3-70b-8192"  # Optional
  ```
- ❌ **DO NOT** use a `.env` file - it's not needed for this setup
- ✅ The `.streamlit/secrets.toml` file is already in `.gitignore` to prevent committing sensitive data

### Available Models

The default model is `llama3-70b-8192`. To use a different model, you can:

1. **Via Streamlit Secrets** (Recommended):
   ```toml
   [GROQ]
   API_KEY = "your_key"
   MODEL = "llama3-8b-8192"  # Faster, less accurate
   ```

2. **Via Environment Variable** (Alternative):
   ```bash
   export GROQ_MODEL=llama3-8b-8192   # Faster, less accurate
   export GROQ_MODEL=mixtral-8x7b-32768  # Alternative model
   ```

**Available models**:
- `llama3-70b-8192` (default) - Best accuracy, recommended
- `llama3-8b-8192` - Faster, less accurate
- `mixtral-8x7b-32768` - Alternative model

## How It Works

### 1. Data Collection
The AI engine collects data from multiple sources:
- **Technical Indicators**: Bias analysis from 13 technical indicators (RSI, MACD, EMA, etc.)
- **Option Chain Analysis**: ATM zone analysis with 13 bias metrics
- **PCR Analysis**: Put-Call Ratio for NIFTY and SENSEX
- **News Headlines**: Real-time market news from NewsData API
- **Market Metadata**: Volatility, volume changes, and other market metrics

### 2. AI Analysis
The AI engine processes this data through multiple stages:

1. **Technical Score**: Aggregates all technical indicators with weighted bias
2. **News Analysis**: LLaMA AI analyzes market news headlines and generates a news sentiment score
3. **Combined Score**: Merges technical (60%), news (30%), and metadata (10%) scores
4. **Final Reasoning**: LLaMA AI provides final verdict with reasoning

### 3. Trigger Conditions
AI analysis is triggered only when:
- **Technical indicators show strong alignment** (e.g., 6+ of 8 fast indicators align)
- **Overall market sentiment is directional** (BULLISH or BEARISH, not NEUTRAL)
- **PCR analysis shows clear bias** (both NIFTY and SENSEX PCR align)

### 4. Output
The AI engine generates:
- **AI Score**: Numerical score from -1 (Bearish) to +1 (Bullish)
- **Label**: BULLISH, BEARISH, or NEUTRAL
- **Confidence**: Percentage confidence in the prediction (0-100%)
- **Reasoning**: List of key factors influencing the decision
- **Recommendation**: BUY, SELL, or HOLD
- **Report**: Saved to `ai_reports/ai_report_<timestamp>.json`
- **Telegram Alert**: Sent if confidence exceeds threshold (default 60%)

## Usage

### In Streamlit App (app.py)

The AI analysis is automatically integrated into the Overall Market Sentiment section:

```python
# API keys are loaded from st.secrets
NEWSDATA_API_KEY = st.secrets.get("NEWSDATA_API_KEY", "")
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")

# AI analysis is called automatically when conditions are met
ai_result = run_ai_analysis(
    overall_market="Indian Stock Market",
    module_biases={
        'htf_sr': htf_sr_bias,
        'vob': vob_bias,
        'overall_sentiment': overall_sentiment_bias,
        'option_chain': option_chain_bias,
    },
    market_meta={
        'volatility': volatility,
        'volume_change': volume_change,
    },
    save_report=True,
    telegram_send=True
)
```

### Manual Testing

You can test the AI engine directly:

```python
import asyncio
from integrations.ai_market_engine import AIMarketEngine

async def test_ai():
    engine = AIMarketEngine(
        news_api_key="your_newsdata_api_key",
        groq_api_key="your_groq_api_key"
    )

    report = await engine.analyze(
        overall_market="Indian Stock Market",
        module_biases={
            'htf_sr': 0.5,
            'vob': 0.3,
            'overall_sentiment': 0.6,
        },
        market_meta={'volatility': 0.2},
        save_report=True,
        telegram_send=False
    )

    print(report)

asyncio.run(test_ai())
```

## Troubleshooting

### Error: "NoneType object is not callable"

**Cause**: Old code was trying to import non-existent functions from `ai_market_engine.py`.

**Solution**: This has been fixed in the latest version. The code now correctly imports only the `AIMarketEngine` class.

### Error: "AI Engine not available"

**Possible causes**:
1. Missing `groq` package: Install with `pip install groq`
2. Import error in `integrations/ai_market_engine.py`

**Solution**: Check the console logs for detailed error messages.

### Error: "API keys not configured"

**Cause**: Missing API keys in `.streamlit/secrets.toml`.

**Solution**:
1. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`
2. Add your NewsData and Groq API keys
3. Restart the Streamlit app

### AI Analysis Not Triggering

**Possible causes**:
1. Market sentiment is NEUTRAL (AI only runs on directional markets)
2. Technical indicators not showing strong alignment
3. `AI_RUN_ONLY_DIRECTIONAL=1` environment variable is set (default behavior)

**Solution**: Check the console logs to see why AI analysis was not triggered.

### News Fetch Errors

**Possible causes**:
1. Invalid NewsData API key
2. API rate limit exceeded (200 requests/day on free tier)
3. Network connectivity issues

**Solution**:
- Verify your API key at https://newsdata.io/
- Check your usage at https://newsdata.io/dashboard
- Consider upgrading to a paid plan if you exceed the free tier

## Configuration Options

### Environment Variables

You can customize the AI engine behavior with these environment variables:

```bash
# Model selection
export GROQ_MODEL=llama3-70b-8192  # Default model

# AI reports directory
export AI_REPORT_DIR=ai_reports  # Default directory for saving reports

# Only run AI on directional markets (BULL/BEAR, skip NEUTRAL)
export AI_RUN_ONLY_DIRECTIONAL=1  # Default: enabled

# Telegram confidence threshold (0.0 to 1.0)
export AI_TELEGRAM_CONFIDENCE=0.60  # Default: 60%
```

### Telegram Integration

AI reports are automatically sent to Telegram when:
1. AI analysis is triggered
2. Confidence exceeds the threshold (default 60%)
3. `telegram_send=True` parameter is passed to `analyze()`

The Telegram bot credentials are loaded from `.streamlit/secrets.toml`:

```toml
[TELEGRAM]
BOT_TOKEN = "your_telegram_bot_token"
CHAT_ID = "your_telegram_chat_id"
```

## File Structure

```
nifty-sensex-trader/
├── integrations/
│   ├── ai_market_engine.py      # Main AI engine (AIMarketEngine class)
│   ├── news_fetcher.py           # NewsData API integration
│   └── __init__.py
├── overall_market_sentiment.py  # Adapter functions for Streamlit app
├── app.py                        # Main Streamlit app
├── .streamlit/
│   ├── secrets.toml              # API keys (gitignored)
│   └── secrets.toml.example      # Template for secrets
├── ai_reports/                   # AI analysis reports (auto-created)
│   └── ai_report_*.json
└── AI_SETUP.md                   # This file
```

## API Cost Estimation

### NewsData API
- **Free Tier**: 200 requests/day
- **Usage per analysis**: 1 request
- **Daily runs**: ~200 analyses (if running continuously during market hours)
- **Recommendation**: Free tier is sufficient for most users

### Groq API
- **Free Tier**: Available (check current limits at https://console.groq.com/pricing)
- **Usage per analysis**: 2-3 API calls (news analysis + final reasoning)
- **Recommendation**: Free tier should be sufficient for development and testing

## Next Steps

1. ✅ Get your API keys from NewsData and Groq
2. ✅ Add them to `.streamlit/secrets.toml`
3. ✅ Install dependencies: `pip install groq`
4. ✅ Run the Streamlit app: `streamlit run app.py`
5. ✅ Monitor the console logs for AI analysis triggers
6. ✅ Check `ai_reports/` directory for generated reports

## Support

If you encounter any issues:
1. Check the console logs for detailed error messages
2. Verify your API keys are correct
3. Check your API usage limits
4. Review the troubleshooting section above
5. Open an issue on the GitHub repository with:
   - Error message
   - Console logs
   - Steps to reproduce
