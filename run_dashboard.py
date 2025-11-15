#!/usr/bin/env python3
"""
Smart Trading Dashboard Runner
Run this script to analyze the market and get comprehensive bias data
"""

from smart_trading_dashboard import SmartTradingDashboard
import sys

def run_analysis(symbol='^NSEI'):
    """
    Run market analysis for given symbol

    Args:
        symbol: Yahoo Finance symbol (default: ^NSEI for Nifty 50)
                Other options: ^BSESN (Sensex), ^DJI (Dow Jones)
    """
    try:
        # Create dashboard instance
        dashboard = SmartTradingDashboard()

        # Run analysis
        print(f"\n{'='*80}")
        print("SMART TRADING DASHBOARD - ADAPTIVE + VOB")
        print("Market Sentiment Analysis with Comprehensive Bias Data")
        print(f"{'='*80}\n")

        results = dashboard.analyze_market(symbol)

        if results:
            # Display all results in tabulated format
            dashboard.display_results(results)

            # Additional summary
            print("\n" + "="*80)
            print("📋 QUICK SUMMARY")
            print("="*80)

            summary_data = [
                ["Symbol", results['symbol']],
                ["Current Price", f"{results['current_price']:.2f}"],
                ["Market Condition", results['market_condition']],
                ["Market Bias", f"{results['market_bias']} ({results['bias_data']['bullish_bias_pct']:.1f}% Bull / {results['bias_data']['bearish_bias_pct']:.1f}% Bear)"],
                ["Mode", "REVERSAL" if results['bias_data']['reversal_mode'] else "NORMAL"],
                ["RSI", f"{results['indicators']['rsi']:.2f}"],
                ["ADX", f"{results['indicators']['adx']:.2f}"],
                ["VWAP", f"{results['indicators']['vwap']:.2f}"],
            ]

            from tabulate import tabulate
            print(tabulate(summary_data, tablefmt="fancy_grid"))

            # Trading recommendation
            print("\n" + "="*80)
            print("💡 RECOMMENDATION")
            print("="*80)

            bias = results['market_bias']
            condition = results['market_condition']

            if bias == "BULLISH" and condition != "RANGE-BOUND":
                print("✅ Look for LONG opportunities at support levels")
                print("📍 Wait for price to touch pivot support (3m/5m/15m)")
                print("🎯 Target: Next resistance level")

            elif bias == "BEARISH" and condition != "RANGE-BOUND":
                print("✅ Look for SHORT opportunities at resistance levels")
                print("📍 Wait for price to touch pivot resistance (3m/5m/15m)")
                print("🎯 Target: Next support level")

            elif condition == "RANGE-BOUND":
                print("📦 Market is RANGE-BOUND - Use range trading strategy")
                print(f"   • BUY near: {results['range_data']['range_low']:.2f}")
                print(f"   • SELL near: {results['range_data']['range_high']:.2f}")
                print(f"   • Pivot: {results['range_data']['range_mid']:.2f}")

            else:
                print("⏸ WAIT - No clear signal. Market bias is NEUTRAL")
                print("💡 Wait for clearer market direction before entering trades")

            if results['bias_data']['divergence_detected']:
                print("\n⚠️ CRITICAL: Divergence detected!")
                if results['bias_data']['bullish_divergence']:
                    print("   🔄 Bullish divergence - Potential reversal to UPSIDE")
                if results['bias_data']['bearish_divergence']:
                    print("   🔄 Bearish divergence - Potential reversal to DOWNSIDE")

            print("\n" + "="*80 + "\n")

            return results
        else:
            print("❌ Analysis failed - no data available")
            return None

    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_custom_analysis():
    """Run analysis with custom configuration"""

    # Create custom config
    custom_config = {
        'bias_strength': 55,  # Lower threshold for bias (50-90)
        'divergence_threshold': 65,  # Divergence sensitivity
        'range_pct_threshold': 2.5,  # Range detection sensitivity
        # Add more custom parameters as needed
    }

    dashboard = SmartTradingDashboard(config=custom_config)
    results = dashboard.analyze_market('^NSEI')

    if results:
        dashboard.display_results(results)
        return results

    return None


if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) > 1:
        symbol = sys.argv[1]
        print(f"Analyzing {symbol}...")
        results = run_analysis(symbol)
    else:
        # Default: Analyze Nifty 50
        results = run_analysis('^NSEI')

    # Uncomment below to run with custom configuration
    # results = run_custom_analysis()
