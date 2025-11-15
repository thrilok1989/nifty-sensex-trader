#!/usr/bin/env python3
"""
Example Usage of Smart Trading Dashboard
Demonstrates various ways to use the dashboard
"""

from smart_trading_dashboard import SmartTradingDashboard
from tabulate import tabulate


def example_1_basic_analysis():
    """Example 1: Basic market analysis"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Analysis")
    print("="*80)

    dashboard = SmartTradingDashboard()
    results = dashboard.analyze_market('^NSEI')

    if results:
        dashboard.display_results(results)


def example_2_custom_config():
    """Example 2: Custom configuration for more sensitive analysis"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Custom Configuration (More Sensitive)")
    print("="*80)

    custom_config = {
        'bias_strength': 55,  # Lower threshold = more sensitive
        'divergence_threshold': 65,
        'range_pct_threshold': 1.5,  # Detect tighter ranges
        'normal_fast_weight': 3.0,  # Give more weight to fast signals
    }

    dashboard = SmartTradingDashboard(config=custom_config)
    results = dashboard.analyze_market('^NSEI')

    if results:
        dashboard.display_results(results)


def example_3_access_specific_data():
    """Example 3: Access specific data from results"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Accessing Specific Data")
    print("="*80)

    dashboard = SmartTradingDashboard()
    results = dashboard.analyze_market('^NSEI')

    if results:
        print("\n📊 KEY METRICS:")
        print(f"  • Symbol: {results['symbol']}")
        print(f"  • Current Price: ₹{results['current_price']:.2f}")
        print(f"  • Market Bias: {results['market_bias']}")
        print(f"  • Market Condition: {results['market_condition']}")
        print(f"  • Bullish Bias: {results['bias_data']['bullish_bias_pct']:.1f}%")
        print(f"  • Bearish Bias: {results['bias_data']['bearish_bias_pct']:.1f}%")

        print("\n🔧 INDICATORS:")
        print(f"  • RSI: {results['indicators']['rsi']:.2f}")
        print(f"  • MFI: {results['indicators']['mfi']:.2f}")
        print(f"  • ADX: {results['indicators']['adx']:.2f}")
        print(f"  • VWAP: ₹{results['indicators']['vwap']:.2f}")

        print("\n📈 STOCKS PERFORMANCE:")
        for stock in results['stock_metrics']:
            symbol = stock['symbol'].replace('.NS', '')
            print(f"  • {symbol}: ₹{stock['ltp']:.2f} ({stock['change_pct']:+.2f}%)")

        if results['bias_data']['divergence_detected']:
            print("\n⚠️  DIVERGENCE ALERT!")
            if results['bias_data']['bullish_divergence']:
                print("  🔄 Bullish Divergence - Reversal UP possible")
            if results['bias_data']['bearish_divergence']:
                print("  🔄 Bearish Divergence - Reversal DOWN possible")


def example_4_multiple_symbols():
    """Example 4: Analyze multiple symbols"""
    print("\n" + "="*80)
    print("EXAMPLE 4: Multiple Symbol Analysis")
    print("="*80)

    symbols = {
        '^NSEI': 'Nifty 50',
        '^BSESN': 'Sensex',
        '^NSEBANK': 'Bank Nifty'
    }

    dashboard = SmartTradingDashboard()

    summary_table = []

    for symbol, name in symbols.items():
        print(f"\n📊 Analyzing {name} ({symbol})...")

        results = dashboard.analyze_market(symbol)

        if results:
            summary_table.append([
                name,
                f"₹{results['current_price']:.2f}",
                results['market_bias'],
                results['market_condition'],
                f"{results['bias_data']['bullish_bias_pct']:.1f}%",
                f"{results['bias_data']['bearish_bias_pct']:.1f}%",
                "⚡" if results['bias_data']['reversal_mode'] else "📊"
            ])

    print("\n" + "="*80)
    print("SUMMARY - ALL SYMBOLS")
    print("="*80)

    headers = ["Index", "Price", "Bias", "Condition", "Bull%", "Bear%", "Mode"]
    print(tabulate(summary_table, headers=headers, tablefmt="fancy_grid"))


def example_5_trading_decision():
    """Example 5: Get trading decision"""
    print("\n" + "="*80)
    print("EXAMPLE 5: Trading Decision Logic")
    print("="*80)

    dashboard = SmartTradingDashboard()
    results = dashboard.analyze_market('^NSEI')

    if results:
        bias = results['market_bias']
        condition = results['market_condition']
        bullish_pct = results['bias_data']['bullish_bias_pct']
        bearish_pct = results['bias_data']['bearish_bias_pct']

        print("\n🎯 TRADING DECISION:")
        print(f"  Market Bias: {bias}")
        print(f"  Condition: {condition}")
        print(f"  Bull Strength: {bullish_pct:.1f}%")
        print(f"  Bear Strength: {bearish_pct:.1f}%")

        print("\n💡 RECOMMENDATION:")

        if bias == "BULLISH" and bullish_pct >= 70:
            print("  ✅ STRONG BULLISH - Actively look for LONG setups")
            print("  📍 Strategy: Buy on dips to support")
            print("  🎯 Risk: MODERATE")

        elif bias == "BULLISH" and bullish_pct >= 60:
            print("  ✅ BULLISH - Look for LONG setups at key levels")
            print("  📍 Strategy: Wait for support confirmation")
            print("  🎯 Risk: MODERATE-HIGH")

        elif bias == "BEARISH" and bearish_pct >= 70:
            print("  ❌ STRONG BEARISH - Actively look for SHORT setups")
            print("  📍 Strategy: Sell on rallies to resistance")
            print("  🎯 Risk: MODERATE")

        elif bias == "BEARISH" and bearish_pct >= 60:
            print("  ❌ BEARISH - Look for SHORT setups at key levels")
            print("  📍 Strategy: Wait for resistance confirmation")
            print("  🎯 Risk: MODERATE-HIGH")

        else:
            print("  ⏸ NEUTRAL - NO TRADE")
            print("  📍 Strategy: Wait for clearer bias")
            print("  🎯 Risk: HIGH (choppy market)")

        if condition == "RANGE-BOUND":
            print("\n  📦 RANGE TRADING MODE:")
            print(f"     • Buy Zone: {results['range_data']['range_low']:.2f}")
            print(f"     • Sell Zone: {results['range_data']['range_high']:.2f}")
            print(f"     • Pivot: {results['range_data']['range_mid']:.2f}")

        if results['bias_data']['divergence_detected']:
            print("\n  ⚠️  CRITICAL ALERT: DIVERGENCE DETECTED")
            print("     • Reversal possible - Reduce position size")
            print("     • Tighten stop losses")
            print("     • Watch for reversal confirmation")


def example_6_continuous_monitoring():
    """Example 6: Continuous monitoring setup"""
    print("\n" + "="*80)
    print("EXAMPLE 6: Continuous Monitoring (Demo)")
    print("="*80)
    print("\nThis example shows how to set up continuous monitoring.")
    print("In production, you would run this in a loop with time delays.\n")

    import time

    dashboard = SmartTradingDashboard()

    # Simulated monitoring (run once for demo)
    print("📊 Running analysis...")
    results = dashboard.analyze_market('^NSEI')

    if results:
        # Quick summary for monitoring
        print("\n" + "="*80)
        print(f"🕐 {results['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📈 {results['symbol']}: ₹{results['current_price']:.2f}")
        print(f"🎯 Bias: {results['market_bias']} ({results['bias_data']['bullish_bias_pct']:.0f}% Bull)")
        print(f"📊 Condition: {results['market_condition']}")

        if results['bias_data']['divergence_detected']:
            print("⚠️  ALERT: Divergence detected!")

        print("="*80)

        # In production, you would:
        # while True:
        #     results = dashboard.analyze_market('^NSEI')
        #     # Check conditions and send alerts
        #     time.sleep(300)  # Run every 5 minutes


def main():
    """Run all examples"""
    print("\n" + "="*80)
    print("SMART TRADING DASHBOARD - USAGE EXAMPLES")
    print("="*80)

    # Uncomment the example you want to run:

    # Basic analysis
    example_1_basic_analysis()

    # Custom configuration
    # example_2_custom_config()

    # Access specific data
    # example_3_access_specific_data()

    # Multiple symbols
    # example_4_multiple_symbols()

    # Trading decision
    # example_5_trading_decision()

    # Continuous monitoring
    # example_6_continuous_monitoring()


if __name__ == "__main__":
    main()
