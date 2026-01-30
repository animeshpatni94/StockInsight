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
from data_fetcher import fetch_all_market_data, fetch_historical_context, get_earnings_calendar
from market_scanner import run_all_screens
from politician_tracker import fetch_recent_trades, analyze_committee_correlation
from history_manager import (
    load_history, save_history, calculate_performance,
    update_history_with_month, get_portfolio_summary, calculate_risk_metrics
)
from claude_analyzer import analyze_with_claude, SYSTEM_PROMPT
from email_builder import build_email_html
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
    portfolio_performance = calculate_performance(current_portfolio, market_data)
    
    if portfolio_performance:
        total_gain = sum(p.get('gain_loss_pct', 0) * p.get('allocation_pct', 0) 
                        for p in portfolio_performance) / max(1, sum(p.get('allocation_pct', 0) 
                        for p in portfolio_performance))
        print(f"       Portfolio weighted return: {total_gain:+.2f}%")
    else:
        print("       No positions to calculate (100% cash)")
    
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
    
    # Step 5b: Fetch news sentiment (if Alpha Vantage configured)
    print("  Fetching news sentiment...")
    news_sentiment = {}
    sentiment_summary = {}
    if is_alphavantage_configured():
        # Get tickers from screens - prioritize TOP performers from each screen type
        # This ensures sentiment aligns with stocks most likely to be recommended
        screen_tickers = []
        
        # Take top stocks from each screen type proportionally
        for screen_type in ['momentum', 'fundamental', 'technical']:
            screen_data = screen_results.get(screen_type, {})
            type_tickers = []
            for key, items in screen_data.items():
                if isinstance(items, list):
                    # Take top 3 from each sub-screen (these are ranked by score)
                    type_tickers.extend([item.get('ticker') for item in items[:3] if item.get('ticker')])
            screen_tickers.extend(type_tickers[:7])  # Max 7 per screen type = 21 total
        
        # Dedupe while preserving order (top performers first)
        seen = set()
        unique_tickers = []
        for t in screen_tickers:
            if t not in seen:
                seen.add(t)
                unique_tickers.append(t)
        screen_tickers = unique_tickers[:20]  # Cap at 20 for API limits
        
        if screen_tickers:
            print(f"    Fetching sentiment for {len(screen_tickers)} tickers: {', '.join(screen_tickers[:5])}...")
            news_sentiment = fetch_multiple_sentiments(screen_tickers)
            sentiment_summary = get_market_sentiment_summary(news_sentiment)
            print(f"    ✓ Got sentiment for {len(news_sentiment)} stocks")
            if sentiment_summary:
                print(f"    Market mood: {sentiment_summary.get('overall_sentiment', 'N/A')} (Bullish: {len(sentiment_summary.get('bullish_tickers', []))}, Bearish: {len(sentiment_summary.get('bearish_tickers', []))})")
        else:
            print("    No tickers available for sentiment analysis")
    else:
        print("    ⚠ Alpha Vantage API not configured - skipping sentiment")
    
    # Step 5c: Get earnings calendar for portfolio and potential picks
    print("  Fetching earnings calendar...")
    all_tickers = [h.get('ticker') for h in current_portfolio if h.get('ticker')]
    # Add tickers from top screens
    for screen_type in ['momentum', 'fundamental']:
        screen_data = screen_results.get(screen_type, {})
        for key, items in screen_data.items():
            if isinstance(items, list):
                all_tickers.extend([item.get('ticker') for item in items[:10] if item.get('ticker')])
    all_tickers = list(set(all_tickers))
    
    print(f"    Checking earnings for {len(all_tickers)} tickers...")
    earnings_calendar = get_earnings_calendar(all_tickers, days_ahead=14)
    upcoming_count = len(earnings_calendar.get('upcoming', []))
    print(f"    ✓ Found {upcoming_count} stocks with earnings in next 14 days")
    if upcoming_count > 0:
        upcoming = earnings_calendar.get('upcoming', [])[:5]
        upcoming_str = ', '.join([f"{e.get('ticker')} ({e.get('earnings_date', 'TBD')})" for e in upcoming])
        print(f"    Upcoming: {upcoming_str}")
    
    # Step 5d: Calculate risk metrics (drawdown protection)
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
    
    # Step 6: Prepare analysis input
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
        "news_sentiment": news_sentiment,
        "sentiment_summary": sentiment_summary,
        "earnings_calendar": earnings_calendar,
        "current_date": datetime.now().isoformat()
    }
    
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
    
    new_recs = analysis_result.get('new_recommendations', [])
    sells = analysis_result.get('sells', [])
    print(f"       Generated {len(new_recs)} new recommendations")
    print(f"       Generated {len(sells)} sell signals")
    
    # Step 7b: Inject real current prices into recommendations
    # Claude doesn't know current prices, so we fetch and add them
    if new_recs:
        rec_tickers = [r.get('ticker') for r in new_recs if r.get('ticker')]
        if rec_tickers:
            print(f"       Fetching real prices for {len(rec_tickers)} recommended tickers...")
            from data_fetcher import get_current_prices
            real_prices = get_current_prices(rec_tickers)
            
            for rec in new_recs:
                ticker = rec.get('ticker')
                if ticker and ticker in real_prices:
                    real_price = real_prices[ticker]
                    rec['current_market_price'] = round(real_price, 2)
                    
                    # Update entry_zone if Claude's prices are way off (>30% different)
                    entry = rec.get('entry_zone', {})
                    if entry:
                        entry_mid = (entry.get('low', 0) + entry.get('high', 0)) / 2
                        if entry_mid > 0:
                            diff_pct = abs(real_price - entry_mid) / entry_mid * 100
                            if diff_pct > 30:
                                # Claude's price is stale, adjust to realistic zone
                                print(f"       ⚠️ {ticker}: Adjusting entry zone from ${entry_mid:.0f} to ${real_price:.0f} (was {diff_pct:.0f}% off)")
                                rec['entry_zone'] = {
                                    'low': round(real_price * 0.97, 2),  # -3% from current
                                    'high': round(real_price * 1.02, 2)  # +2% from current
                                }
                                # Also adjust price target proportionally if it exists
                                old_target = rec.get('price_target', 0)
                                if old_target > 0 and entry_mid > 0:
                                    target_upside = (old_target / entry_mid) - 1  # Original upside %
                                    rec['price_target'] = round(real_price * (1 + target_upside), 2)
                                # Adjust stop loss
                                old_stop = rec.get('stop_loss', 0)
                                if old_stop > 0 and entry_mid > 0:
                                    stop_downside = 1 - (old_stop / entry_mid)  # Original downside %
                                    rec['stop_loss'] = round(real_price * (1 - stop_downside), 2)
            
            print(f"       ✓ Prices validated for {len(real_prices)} tickers")
    
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
    
    # Pass additional context for email badges
    email_context = {
        'vix_data': vix_data,
        'earnings_calendar': earnings_calendar,
        'news_sentiment': news_sentiment,
        'sentiment_summary': sentiment_summary,
        'historical_context': historical_context
    }
    
    email_html = build_email_html(analysis_result, updated_history, email_context)
    
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
            subject = f"📊 Stock Insight Report - {datetime.now().strftime('%B %d, %Y')}"
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
