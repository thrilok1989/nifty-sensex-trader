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
- **Pricing**: https://groq.com/pricing/

### 2. Configuration

Add your API keys to `.streamlit/secrets.toml`:

```toml
# AI + NEWS ENGINE KEYS (REQUIRED FOR AI ANALYSIS)
NEWSDATA_API_KEY = "your_actual_newsdata_api_key"
GROQ_API_KEY = "your_actual_groq_api_key"
```

**IMPORTANT**: Replace `"your_actual_..."` with your real API keys

## How It Works

1. **Technical Analysis**: Aggregates scores from all technical indicators
2. **News Analysis**: Fetches and analyzes recent market news using NewsData API
3. **AI Synthesis**: Uses Groq's LLaMA model to synthesize analysis with reasoning
4. **Market Recommendation**: Provides BUY/SELL/HOLD recommendation with confidence

## Features

- **Automated Analysis**: Runs automatically when market sentiment is directional (BULLISH/BEARISH)
- **News Integration**: Analyzes top 10 recent headlines for sentiment
- **AI Reasoning**: Provides detailed reasoning for recommendations
- **Report Saving**: Saves analysis reports to `ai_reports/` directory
- **Telegram Alerts**: Sends alerts when confidence >= 60%

## Configuration Options

### Environment Variables

```bash
# Run AI only for directional markets (BULL/BEAR)
AI_RUN_ONLY_DIRECTIONAL=1

# Confidence threshold for Telegram alerts (0.0 to 1.0)
AI_TELEGRAM_CONFIDENCE=0.60

# AI report directory
AI_REPORT_DIR=ai_reports

# Groq model selection
GROQ_MODEL=llama3-70b-8192
```

## Error Handling

If AI analysis is not working:

1. **Check API Keys**: Ensure both NEWSDATA_API_KEY and GROQ_API_KEY are set in secrets.toml
2. **Check Logs**: Look for error messages in the console output
3. **Check Dependencies**: Ensure `groq` package is installed: `pip install groq`
4. **Check Rate Limits**: Free tiers have request limits

## Disabling AI Analysis

If you don't want to use AI analysis, simply don't set the API keys in secrets.toml. The app will continue to work with traditional analysis only.

## Troubleshooting

### "'NoneType' object is not callable" Error
- **Cause**: Missing or incorrect imports
- **Solution**: The fix has been applied in the latest commit
- **Verify**: Check that `integrations/ai_market_engine.py` exists

### "AI Engine not available" Message
- **Cause**: Missing API keys or import failure
- **Solution**:
  1. Verify API keys are set in `.streamlit/secrets.toml`
  2. Check that `integrations/ai_market_engine.py` exists
  3. Install groq: `pip install groq`

### "API keys not configured" Error
- **Cause**: Missing NEWSDATA_API_KEY or GROQ_API_KEY
- **Solution**: Add both keys to `.streamlit/secrets.toml`

## Support

For issues or questions:
- Check the GitHub repository issues
- Review the AI Market Engine code in `integrations/ai_market_engine.py`
- Contact support through the repository

## Credits

- **NewsData.io**: News data provider
- **Groq**: AI model infrastructure
- **LLaMA**: Meta's open-source AI model
