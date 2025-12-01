"""
overall_market_sentiment_adapter.py

This adapter provides a stable interface between the main app
(overall_market_sentiment.py, app.py, etc.) and the AI Market Engine.

It prevents ModuleNotFoundError by exposing:
- async run_ai_analysis(...)
- async shutdown_ai_engine()

The AI engine is fully encapsulated here.
"""

import asyncio
from integrations.ai_market_engine import AIMarketEngine

# Initialize globally so the engine loads once
_ai_engine = AIMarketEngine()


async def run_ai_analysis(overall_market: str,
                          module_biases: dict,
                          market_meta: dict = None,
                          save_report: bool = True,
                          telegram_send: bool = True) -> dict:
    """
    Run AI analysis on aggregated market data.

    Parameters:
        overall_market (str): The overall market sentiment string
        module_biases (dict): Dictionary containing module biases/weights
        market_meta (dict): Additional market metadata
        save_report (bool): Whether to save the AI report to file
        telegram_send (bool): Whether to send the report via Telegram

    Returns:
        dict: AI-generated structured output
    """
    return await _ai_engine.analyze(
        overall_market=overall_market,
        module_biases=module_biases,
        market_meta=market_meta,
        save_report=save_report,
        telegram_send=telegram_send
    )


async def shutdown_ai_engine():
    """
    Properly stop or release AI engine resources.
    """
    await _ai_engine.close()


# Optional synchronous wrapper for backward compatibility
def run_ai_analysis_sync(overall_market: str,
                        module_biases: dict,
                        market_meta: dict = None,
                        save_report: bool = True,
                        telegram_send: bool = True) -> dict:
    """
    Synchronous wrapper for run_ai_analysis.
    Useful for scripts that cannot use async/await.
    """
    return asyncio.run(run_ai_analysis(
        overall_market=overall_market,
        module_biases=module_biases,
        market_meta=market_meta,
        save_report=save_report,
        telegram_send=telegram_send
    ))
