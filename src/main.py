"""
Main entry point for the monthly stock analysis agent.
Orchestrates all modules to generate and send monthly reports.
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

from config import CLAUDE_MODEL, CLAUDE_MAX_TOKENS, PATHS
from data_fetcher import fetch_all_market_data, fetch_historical_context, get_earnings_calendar, get_dividend_calendar
from market_scanner import run_all_screens
from politician_tracker import fetch_recent_trades, analyze_committee_correlation
from history_manager import (
    load_history, save_history, calculate_performance,
    update_history_with_month, get_portfolio_summary, calculate_risk_metrics,
    validate_allocation_rules, auto_generate_sells_from_alerts, get_actual_portfolio_value
)
from claude_analyzer import analyze_with_claude, SYSTEM_PROMPT
from email_builder import build_email_html
from retail_advisor import run_retail_investor_analysis, generate_dca_plan
from email_sender import send_email, validate_email_config
from news_sentiment import fetch_multiple_sentiments, get_market_sentiment_summary, is_alphavantage_configured


def main(dry_run: bool = False, skip_email: bool = False, verbose: bool = False):
    """
    Main entry point for the monthly analysis.
    
    Args:
        dry_run: If True, don't save history or send email
        skip_email: If True, skip sending email (but still generate report)
        verbose: If True, print detailed progress
    """
    # Load environment variables
    load_dotenv()
    
    start_time = datetime.now()
    print("=" * 60)
    print(f"📊 STOCK INSIGHT AGENT - Monthly Analysis")
    print(f"   Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Step 1: Load portfolio history
    print("\n[1/10] Loading portfolio history...")
    history = load_history()
    current_portfolio = history.get('current_portfolio', [])
    print(f"       Found {len(current_portfolio)} existing positions")
    
    if verbose:
        print(get_portfolio_summary(history))
    
    # Step 2: Fetch market data
    print("\n[2/10] Fetching market data...")
    market_data = fetch_all_market_data()
    print(f"       Fetched data for {len(market_data.get('indexes', {}))} indexes")
    print(f"       Fetched data for {len(market_data.get('sectors', {}))} sectors")
    
    # Step 2b: Fetch historical context (5-year data for reduced recency bias)
    historical_context = fetch_historical_context()
    market_data['historical_context'] = historical_context
    
    # Display VIX alert if elevated
    vix_data = market_data.get('macro', {}).get('vix', {})
    if vix_data.get('alert_level') in ['ELEVATED', 'HIGH_FEAR']:
        print(f"       {vix_data.get('alert_emoji', '⚠️')} VIX ALERT: {vix_data.get('current', 'N/A')} ({vix_data.get('alert_level')})")
        print(f"       → {vix_data.get('recommendation', '')}")
    
    # Step 3: Calculate portfolio performance
    print("\n[3/10] Calculating portfolio performance...")
    portfolio_performance, triggered_alerts = calculate_performance(current_portfolio, market_data)
    
    if portfolio_performance:
        total_gain = sum(p.get('gain_loss_pct', 0) * p.get('allocation_pct', 0) 
                        for p in portfolio_performance) / max(1, sum(p.get('allocation_pct', 0) 
                        for p in portfolio_performance))
        print(f"       Portfolio weighted return: {total_gain:+.2f}%")
    else:
        print("       No positions to calculate (100% cash)")
    
    # Handle triggered alerts (auto-sell stop losses)
    auto_sells = []
    if triggered_alerts:
        print(f"\n       ⚠️ ALERT: {len(triggered_alerts)} positions triggered stop-loss/target!")
        auto_sells = auto_generate_sells_from_alerts(triggered_alerts, portfolio_performance)
    
    # Step 4: Run market screens
    print("\n[4/10] Running market screens...")
    screen_results = run_all_screens()
    
    momentum = screen_results.get('momentum', {})
    print(f"       Found {len(momentum.get('top_gainers', []))} top gainers")
    print(f"       Found {len(momentum.get('unusual_volume', []))} volume spikes")
    
    # Step 5: Fetch politician trades (90 days to get more data for bi-weekly reports)
    print("\n[5/10] Fetching politician trades...")
    politician_trades = fetch_recent_trades(days=90)
    flagged_trades = analyze_committee_correlation(politician_trades)
    print(f"       Found {len(politician_trades)} recent trades")
    print(f"       Flagged {len(flagged_trades)} suspicious trades")
    
    # Step 5b: Get earnings calendar for portfolio and potential picks
    print("  Fetching earnings calendar...")
    all_tickers = [h.get('ticker') for h in current_portfolio if h.get('ticker')]
    # Add tickers from top screens
    for screen_type in ['momentum', 'fundamental']:
        screen_data = screen_results.get(screen_type, {})
        for key, items in screen_data.items():
            if isinstance(items, list):
                all_tickers.extend([item.get('ticker') for item in items[:10] if item.get('ticker')])
    all_tickers = list(set(all_tickers))
    
    earnings_calendar = get_earnings_calendar(all_tickers, days_ahead=14)
    # earnings_calendar is a flat dict {ticker: earnings_info}
    upcoming_count = len(earnings_calendar)
    print(f"    ✓ Found {upcoming_count} stocks with earnings in next 14 days")
    if upcoming_count > 0:
        # Convert flat dict to list for display
        upcoming_list = [{'ticker': t, **info} for t, info in list(earnings_calendar.items())[:5]]
        upcoming_str = ', '.join([f"{e['ticker']} ({e.get('earnings_date', 'TBD')})" for e in upcoming_list])
        print(f"    Upcoming: {upcoming_str}")
    
    # Step 5d: Fetch dividend calendar for portfolio
    print("  Fetching dividend calendar...")
    dividend_calendar = get_dividend_calendar(all_tickers, days_ahead=14)
    # dividend_calendar is a dict keyed by ticker, e.g. {'AAPL': {'ex_dividend_date': ..., 'days_until': ...}}
    div_count = len(dividend_calendar)
    print(f"    ✓ Found {div_count} stocks with ex-dividend dates in next 14 days")
    if div_count > 0:
        upcoming_divs = list(dividend_calendar.items())[:5]
        div_str = ', '.join([f"{ticker} ({data.get('ex_dividend_display', 'TBD')}: ${data.get('dividend_per_share', 0):.2f})" for ticker, data in upcoming_divs])
        print(f"    Upcoming: {div_str}")
    
    # Step 5c: Calculate risk metrics (drawdown protection)
    print("  Calculating risk metrics...")
    risk_metrics = calculate_risk_metrics(history)
    risk_status = risk_metrics.get('risk_status', 'NORMAL')
    status_emoji = {'NORMAL': '🟢', 'CAUTION': '🟡', 'DEFENSIVE': '🟠', 'CRITICAL': '🔴'}.get(risk_status, '⚪')
    print(f"    {status_emoji} Risk Status: {risk_status}")
    
    if risk_metrics.get('risk_reasons'):
        for reason in risk_metrics['risk_reasons']:
            print(f"    ⚠️ {reason}")
    
    metrics = risk_metrics.get('metrics', {})
    print(f"    Drawdown: {metrics.get('drawdown_pct', 0):.1f}% | Consecutive Losses: {metrics.get('consecutive_losses', 0)}")
    
    rules = risk_metrics.get('rules', {})
    print(f"    Mode Rules: Max position {rules.get('max_position_size', 15)}%, Min cash {rules.get('min_cash', 5)}%")
    
    # Step 5d: Run retail investor analysis (tax harvesting, correlation, liquidity, etc.)
    print("\n  Running retail investor analysis...")
    # Get current prices for retail analysis
    all_portfolio_tickers = [h.get('ticker') for h in current_portfolio if h.get('ticker')]
    from data_fetcher import get_current_prices
    current_prices_for_retail = get_current_prices(all_portfolio_tickers) if all_portfolio_tickers else {}
    
    retail_analysis = run_retail_investor_analysis(
        portfolio=current_portfolio,
        current_prices=current_prices_for_retail,
        watchlist=all_tickers[:30]  # Top watchlist tickers
    )
    
    # Display retail investor alerts
    priority_alerts = retail_analysis.get('priority_alerts', [])
    if priority_alerts:
        print(f"    📊 RETAIL INVESTOR ALERTS ({len(priority_alerts)}):")
        for alert in priority_alerts[:5]:  # Show top 5
            print(f"       {alert.get('title', 'Alert')}")
    
    # Tax-loss harvesting summary
    tlh = retail_analysis.get('tax_loss_harvesting', [])
    if tlh:
        high_priority = [t for t in tlh if t.get('priority') == 'HIGH']
        if high_priority:
            print(f"    🏦 TAX-LOSS HARVESTING: {len(high_priority)} high-priority opportunities")
    
    # Correlation warnings
    corr = retail_analysis.get('correlation_analysis', {})
    div_score = corr.get('diversification_score', 0)
    if div_score > 0:
        print(f"    📊 Diversification Score: {div_score:.0f}/100 ({corr.get('diversification_grade', 'N/A')})")
    
    # Step 6: Prepare analysis input (NO sentiment - Claude decides purely on fundamentals)
    print("\n[6/10] Preparing analysis input...")
    analysis_input = {
        "current_portfolio": portfolio_performance,
        "portfolio_history": history.get('monthly_history', []),
        "closed_positions": history.get('closed_positions', []),
        "performance_summary": history.get('performance_summary', {}),
        "risk_metrics": risk_metrics,
        "market_data": market_data,
        "screen_results": screen_results,
        "politician_trades": politician_trades,
        "flagged_trades": flagged_trades,
        "earnings_calendar": earnings_calendar,
        "dividend_calendar": dividend_calendar,
        "triggered_alerts": triggered_alerts,
        "auto_sells": auto_sells,
        "current_date": datetime.now().isoformat(),
        # Retail investor specific data
        "retail_analysis": {
            "tax_loss_harvesting": retail_analysis.get('tax_loss_harvesting', []),
            "correlation_analysis": retail_analysis.get('correlation_analysis', {}),
            "liquidity_warnings": retail_analysis.get('liquidity_analysis', {}).get('warnings', []),
            "trailing_stops": retail_analysis.get('trailing_stops', []),
            "short_interest": retail_analysis.get('short_interest', []),
            "institutional_ownership": retail_analysis.get('institutional_ownership', []),
            "sector_rotation": retail_analysis.get('sector_rotation', {}),
            "fee_analysis": retail_analysis.get('fee_analysis', {}),
            "dividend_timing": retail_analysis.get('dividend_timing', {}),
            "priority_alerts": retail_analysis.get('priority_alerts', [])
        }
    }
    
    # === LOG DATA BEING SENT TO CLAUDE ===
    print("\n" + "=" * 70)
    print("📊 DATA SUMMARY BEING SENT TO CLAUDE FOR ANALYSIS")
    print("=" * 70)
    
    # Log screen results summary
    momentum = screen_results.get('momentum', {})
    fundamental = screen_results.get('fundamental', {})
    technical = screen_results.get('technical', {})
    
    print(f"\n📈 MOMENTUM SCREENS:")
    print(f"   Top Gainers ({len(momentum.get('top_gainers', []))}): {', '.join([s['ticker'] for s in momentum.get('top_gainers', [])[:15]])}...")
    print(f"   Top Losers ({len(momentum.get('top_losers', []))}): {', '.join([s['ticker'] for s in momentum.get('top_losers', [])[:15]])}...")
    print(f"   52W High Breakouts ({len(momentum.get('52w_high_breakouts', []))}): {', '.join([s['ticker'] for s in momentum.get('52w_high_breakouts', [])[:10]])}...")
    print(f"   Unusual Volume ({len(momentum.get('unusual_volume', []))}): {', '.join([s['ticker'] for s in momentum.get('unusual_volume', [])[:10]])}...")
    
    print(f"\n📊 FUNDAMENTAL SCREENS:")
    print(f"   Growth Stocks ({len(fundamental.get('growth_stocks', []))}): {', '.join([s['ticker'] for s in fundamental.get('growth_stocks', [])[:15]])}...")
    print(f"   Value Stocks ({len(fundamental.get('value_stocks', []))}): {', '.join([s['ticker'] for s in fundamental.get('value_stocks', [])[:15]])}...")
    print(f"   GARP Stocks ({len(fundamental.get('garp_stocks', []))}): {', '.join([s['ticker'] for s in fundamental.get('garp_stocks', [])[:10]])}...")
    print(f"   Dividend Stocks ({len(fundamental.get('dividend_stocks', []))}): {', '.join([s['ticker'] for s in fundamental.get('dividend_stocks', [])[:10]])}...")
    print(f"   Insider Buying ({len(fundamental.get('insider_buying', []))}): {', '.join([s['ticker'] for s in fundamental.get('insider_buying', [])[:10]])}...")
    
    print(f"\n📉 TECHNICAL SCREENS:")
    print(f"   Golden Crosses ({len(technical.get('golden_crosses', []))}): {', '.join([s['ticker'] for s in technical.get('golden_crosses', [])[:10]])}...")
    print(f"   Oversold RSI ({len(technical.get('oversold', []))}): {', '.join([s['ticker'] for s in technical.get('oversold', [])[:10]])}...")
    print(f"   Overbought RSI ({len(technical.get('overbought', []))}): {', '.join([s['ticker'] for s in technical.get('overbought', [])[:10]])}...")
    
    # Log market data summary
    print(f"\n🌍 MARKET DATA:")
    print(f"   Indexes: {', '.join(market_data.get('indexes', {}).keys())}")
    print(f"   Sectors: {', '.join(market_data.get('sectors', {}).keys())}")
    commodities = market_data.get('commodities', {})
    commodity_list = [k + "(" + v.get('ticker', 'N/A') + ")" for k, v in list(commodities.items())[:5]]
    print(f"   Commodities: {', '.join(commodity_list)}...")
    
    # Log ETF data
    growth_etfs = market_data.get('growth_etfs', {})
    print(f"\n📊 ETF DATA:")
    for theme, etfs in list(growth_etfs.items())[:5]:
        tickers = list(etfs.keys()) if isinstance(etfs, dict) else []
        print(f"   {theme}: {', '.join(tickers[:3])}...")
    
    # Total unique tickers being analyzed
    all_analyzed_tickers = set()
    for screen_type in [momentum, fundamental, technical]:
        for key, items in screen_type.items():
            if isinstance(items, list):
                all_analyzed_tickers.update([s.get('ticker', '') for s in items if s.get('ticker')])
    
    print(f"\n✅ TOTAL UNIQUE STOCKS IN SCREENS: {len(all_analyzed_tickers)}")
    print("=" * 70 + "\n")
    
    # Step 7: Analyze with Claude
    print("\n[7/10] Analyzing with Claude Opus...")
    print(f"       Model: {CLAUDE_MODEL}")
    print(f"       Max tokens: {CLAUDE_MAX_TOKENS}")
    
    analysis_result = analyze_with_claude(
        analysis_input,
        system_prompt=SYSTEM_PROMPT,
        model=CLAUDE_MODEL,
        max_tokens=CLAUDE_MAX_TOKENS
    )
    
    # Check if Claude API failed
    api_failed = analysis_result.get('_api_failed', False)
    if api_failed:
        print("\n" + "=" * 60)
        print("❌ CLAUDE API FAILED - ABORTING RUN")
        print("=" * 60)
        print("   • Existing portfolio preserved (no changes made)")
        print("   • No email sent")
        print("   • Please check your API key and try again")
        print("=" * 60)
        return
    
    new_recs = analysis_result.get('new_recommendations', [])
    sells = analysis_result.get('sells', [])
    
    # Merge auto-generated sells with Claude's sells
    if auto_sells:
        existing_sell_tickers = {s.get('ticker') for s in sells}
        for auto_sell in auto_sells:
            if auto_sell['ticker'] not in existing_sell_tickers:
                sells.append(auto_sell)
                print(f"       + Added auto-sell for {auto_sell['ticker']} (stop-loss triggered)")
        analysis_result['sells'] = sells
    
    print(f"       Generated {len(new_recs)} new recommendations")
    print(f"       Generated {len(sells)} sell signals")
    
    # Validate allocation rules
    validation = validate_allocation_rules(analysis_result, history)
    if not validation['valid']:
        print(f"\n       ⚠️ ALLOCATION ISSUES:")
        for issue in validation['issues']:
            print(f"         - {issue}")
    if validation['warnings']:
        for warning in validation['warnings']:
            print(f"         ⚠️ {warning}")
    if validation['corrections']:
        print(f"       ✓ Auto-corrections applied:")
        for correction in validation['corrections']:
            print(f"         - {correction}")
    
    # Step 7b: VERIFY real yfinance prices - failsafe in case Claude ignored our instructions
    # We sent real prices TO Claude in the prompt, but this is a safety net
    # yfinance is ALWAYS the source of truth for all price data
    if new_recs:
        rec_tickers = [r.get('ticker') for r in new_recs if r.get('ticker')]
        if rec_tickers:
            print(f"       Verifying prices for {len(rec_tickers)} recommended tickers...")
            from data_fetcher import get_current_prices
            real_prices = get_current_prices(rec_tickers)
            
            for rec in new_recs:
                ticker = rec.get('ticker')
                if ticker and ticker in real_prices:
                    real_price = real_prices[ticker]
                    rec['current_market_price'] = round(real_price, 2)
                    
                    # Get Claude's suggested upside/downside percentages (these are still valid)
                    entry = rec.get('entry_zone', {})
                    old_entry_mid = (entry.get('low', 0) + entry.get('high', 0)) / 2 if entry else 0
                    old_target = rec.get('price_target', 0)
                    old_stop = rec.get('stop_loss', 0)
                    
                    # Calculate Claude's intended risk/reward percentages
                    if old_entry_mid > 0 and old_target > 0:
                        target_upside_pct = (old_target / old_entry_mid) - 1  # e.g., 0.15 = 15% upside
                    else:
                        target_upside_pct = 0.15  # Default 15% upside
                    
                    if old_entry_mid > 0 and old_stop > 0:
                        stop_downside_pct = 1 - (old_stop / old_entry_mid)  # e.g., 0.12 = 12% downside
                    else:
                        stop_downside_pct = 0.12  # Default 12% stop loss
                    
                    # ALWAYS recalculate prices based on REAL yfinance price
                    rec['entry_zone'] = {
                        'low': round(real_price * 0.97, 2),   # -3% from current (buy zone)
                        'high': round(real_price * 1.02, 2)   # +2% from current
                    }
                    rec['price_target'] = round(real_price * (1 + target_upside_pct), 2)
                    rec['stop_loss'] = round(real_price * (1 - stop_downside_pct), 2)
                    rec['recommended_price'] = round(real_price, 2)  # Use real price as entry
                    
                    print(f"       ✓ {ticker}: ${real_price:.2f} | Target: ${rec['price_target']:.2f} (+{target_upside_pct*100:.0f}%) | Stop: ${rec['stop_loss']:.2f} (-{stop_downside_pct*100:.0f}%)")
            
            print(f"       ✓ All {len(real_prices)} tickers using real yfinance prices")
    
    # Step 7c: Fetch sentiment ONLY for Claude's recommended stocks (no bias)
    news_sentiment = {}
    sentiment_summary = {}
    if new_recs and is_alphavantage_configured():
        rec_tickers = [r.get('ticker') for r in new_recs if r.get('ticker')]
        if rec_tickers:
            print(f"       Fetching sentiment for {len(rec_tickers)} recommended stocks...")
            news_sentiment = fetch_multiple_sentiments(rec_tickers)
            sentiment_summary = get_market_sentiment_summary(news_sentiment)
            print(f"       ✓ Got sentiment for {len(news_sentiment)} stocks")
            
            # Add sentiment to each recommendation for display
            for rec in new_recs:
                ticker = rec.get('ticker')
                if ticker and ticker in news_sentiment:
                    sentiment_data = news_sentiment[ticker]
                    rec['sentiment'] = {
                        'label': sentiment_data.get('label', 'NEUTRAL'),
                        'bullish_pct': sentiment_data.get('bullish_pct', 50),
                        'emoji': sentiment_data.get('emoji', '⚪')
                    }
                    print(f"       {ticker}: {sentiment_data.get('emoji', '')} {sentiment_data.get('label', 'N/A')} ({sentiment_data.get('bullish_pct', 50):.0f}% bullish)")
    
    # Step 8: Update portfolio history
    print("\n[8/10] Updating portfolio history...")
    if not dry_run:
        updated_history = update_history_with_month(history, analysis_result, market_data)
        save_history(updated_history)
        print("       History saved successfully")
    else:
        updated_history = history
        print("       [DRY RUN] Skipping history save")
    
    # Step 9: Build email report
    print("\n[9/10] Building email report...")
    
    # Transform dividend calendar data structure for email builder
    # email_builder expects: {'AAPL': {'ex_dividend_display': '...', 'days_until': N, ...}}
    # get_dividend_calendar returns: {ticker: {'ex_dividend_date': '...', 'days_until': N, ...}}
    dividend_calendar_for_email = {}
    for ticker, div_data in dividend_calendar.items():
        dividend_calendar_for_email[ticker] = {
            'ex_dividend_display': div_data.get('ex_dividend_display', 'TBD'),
            'days_until': div_data.get('days_until', '?'),
            'dividend_per_share': div_data.get('dividend_per_share', 0),
            'dividend_yield_pct': div_data.get('dividend_yield_pct', 0),
            'current_price': div_data.get('current_price', 0)
        }
    
    # Detect first-run scenario for special handling in email
    is_first_run = len(current_portfolio) == 0 and len(history.get('monthly_history', [])) == 0
    if is_first_run:
        print("       📌 First run detected - email will include welcome guidance")
    
    # Pass additional context for email badges
    email_context = {
        'vix_data': vix_data,
        'earnings_calendar': earnings_calendar,
        'dividend_calendar': dividend_calendar_for_email,
        'triggered_alerts': triggered_alerts,
        'news_sentiment': news_sentiment,  # Now contains sentiment for recommended stocks only
        'sentiment_summary': sentiment_summary,
        'historical_context': historical_context,
        'portfolio_performance': portfolio_performance,  # With live current_price data
        'is_first_run': is_first_run,
        # Retail investor insights
        'retail_analysis': retail_analysis
    }
    
    # Pass ORIGINAL history so Current Holdings shows actual existing positions,
    # not the newly added recommendations (which should appear in Stock Picks section)
    email_html = build_email_html(analysis_result, history, email_context)
    
    # Save report locally regardless
    output_dir = Path(__file__).parent.parent / 'output'
    output_dir.mkdir(exist_ok=True)
    report_path = output_dir / f"report_{datetime.now().strftime('%Y%m')}.html"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(email_html)
    print(f"       Report saved to: {report_path}")
    
    # Step 10: Send email
    print("\n[10/10] Sending email report...")
    
    if skip_email or dry_run:
        print("       [SKIP] Email sending disabled")
    else:
        recipient = os.getenv('RECIPIENT_EMAIL')
        if recipient:
            subject = f"📊 Stock Pulse Report - {datetime.now().strftime('%B %d, %Y')}"
            success = send_email(
                to_email=recipient,
                subject=subject,
                html_content=email_html
            )
            if success:
                print(f"       ✓ Email sent to {recipient}")
            else:
                print(f"       ✗ Email delivery failed (report saved locally)")
        else:
            print("       ✗ RECIPIENT_EMAIL not configured")
    
    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 60)
    print("✅ ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"   Duration: {duration:.1f} seconds")
    print(f"   Report: {report_path}")
    
    # Print action summary
    print("\n📋 ACTION SUMMARY:")
    
    if sells:
        print(f"   🔴 SELL: {', '.join(s.get('ticker', '') for s in sells)}")
    
    trims = [r for r in analysis_result.get('portfolio_review', []) if r.get('action') == 'TRIM']
    if trims:
        trim_strs = [f"{t.get('ticker')} → {t.get('new_allocation_pct', 0):.0f}%" for t in trims]
        print(f"   🟡 TRIM: {', '.join(trim_strs)}")
    
    if new_recs:
        buy_strs = [f"{r.get('ticker')} ({r.get('allocation_pct', 0):.0f}%)" for r in new_recs]
        print(f"   🟢 BUY:  {', '.join(buy_strs)}")
    
    cash_pct = updated_history.get('cash', {}).get('allocation_pct', 0)
    print(f"   💵 CASH: {cash_pct:.1f}%")
    
    print("\n" + "=" * 60)
    
    return analysis_result


def check_config():
    """Check and display current configuration."""
    print("=" * 60)
    print("CONFIGURATION CHECK")
    print("=" * 60)
    
    # API Keys
    print("\n📌 API Keys:")
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    quiver_key = os.getenv('QUIVER_API_KEY')
    
    print(f"   ANTHROPIC_API_KEY: {'✓ Set' if anthropic_key else '✗ Not set'}")
    print(f"   QUIVER_API_KEY: {'✓ Set' if quiver_key else '○ Optional (mock data will be used)'}")
    
    # Email Config
    print("\n📧 Email Configuration:")
    email_config = validate_email_config()
    print(f"   AZURE_COMM_CONNECTION_STRING: {'✓ Set' if email_config['connection_string'] else '✗ Not set'}")
    print(f"   AZURE_COMM_SENDER: {'✓ Set' if email_config['sender_address'] else '✗ Not set'}")
    print(f"   RECIPIENT_EMAIL: {'✓ Set' if email_config['recipient_email'] else '✗ Not set'}")
    
    # Portfolio History
    print("\n📁 Data Files:")
    history_path = Path(__file__).parent.parent / PATHS['portfolio_history']
    print(f"   Portfolio history: {'✓ Exists' if history_path.exists() else '○ Will be created'}")
    
    # Summary
    print("\n" + "-" * 60)
    if anthropic_key and email_config['is_configured']:
        print("✅ All required configuration is set!")
    else:
        print("⚠️  Missing required configuration:")
        if not anthropic_key:
            print("   - Set ANTHROPIC_API_KEY for Claude analysis")
        if not email_config['is_configured']:
            print("   - Set Azure email variables for report delivery")
    
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Stock Insight Agent - Monthly Market Analysis"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Run analysis without saving history or sending email"
    )
    parser.add_argument(
        '--skip-email',
        action='store_true',
        help="Skip sending email (report will still be saved locally)"
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help="Print detailed progress information"
    )
    parser.add_argument(
        '--check-config',
        action='store_true',
        help="Check configuration and exit"
    )
    
    args = parser.parse_args()
    
    if args.check_config:
        check_config()
    else:
        main(
            dry_run=args.dry_run,
            skip_email=args.skip_email,
            verbose=args.verbose
        )
