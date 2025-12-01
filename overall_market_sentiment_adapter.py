"""
overall_market_sentiment_adapter.py

This adapter provides a stable interface between the main app
(overall_market_sentiment.py, app.py, etc.) and the AI Market Engine.

It prevents ModuleNotFoundError by exposing:
- run_ai_analysis(data)
- shutdown_ai_engine()

The AI engine is fully encapsulated here.
"""

from ai_market_engine import AIMarketEngine

# Initialize globally so the engine loads once
_ai_engine = AIMarketEngine()


def run_ai_analysis(data: dict) -> dict:
    """
    Run AI analysis on aggregated market data.

    Parameters:
        data (dict): data containing weighted bias, news sentiment,
                     technical indicators, option chain data, etc.

    Returns:
        dict: AI-generated structured output
    """
    return _ai_engine.run_analysis(data)


def shutdown_ai_engine():
    """
    Properly stop or release AI engine resources if needed.
    (Some engines require cleanup; Groq LLaMA does not,
    but we keep this for future expansion.)
    """
    _ai_engine.shutdown()
