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
from data_fetcher import fetch_all_market_data
from market_scanner import run_all_screens
from politician_tracker import fetch_recent_trades, analyze_committee_correlation
from history_manager import (
    load_history, save_history, calculate_performance,
    update_history_with_month, get_portfolio_summary
)
from claude_analyzer import analyze_with_claude, SYSTEM_PROMPT
from email_builder import build_email_html
from email_sender import send_email, validate_email_config


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
    
    # Step 5: Fetch politician trades
    print("\n[5/10] Fetching politician trades...")
    politician_trades = fetch_recent_trades(days=45)
    flagged_trades = analyze_committee_correlation(politician_trades)
    print(f"       Found {len(politician_trades)} recent trades")
    print(f"       Flagged {len(flagged_trades)} suspicious trades")
    
    # Step 6: Prepare analysis input
    print("\n[6/10] Preparing analysis input...")
    analysis_input = {
        "current_portfolio": portfolio_performance,
        "portfolio_history": history.get('monthly_history', []),
        "closed_positions": history.get('closed_positions', []),
        "performance_summary": history.get('performance_summary', {}),
        "market_data": market_data,
        "screen_results": screen_results,
        "politician_trades": politician_trades,
        "flagged_trades": flagged_trades,
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
    email_html = build_email_html(analysis_result, updated_history)
    
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
            subject = f"📊 Monthly Stock Recommendations - {datetime.now().strftime('%B %Y')}"
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
        print(f"   🟡 TRIM: {', '.join(f\"{t.get('ticker')} → {t.get('new_allocation_pct'):.0f}%\" for t in trims)}")
    
    if new_recs:
        print(f"   🟢 BUY:  {', '.join(f\"{r.get('ticker')} ({r.get('allocation_pct'):.0f}%)\" for r in new_recs)}")
    
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
