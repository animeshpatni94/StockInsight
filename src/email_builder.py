"""
HTML email builder for stock analysis reports.
Constructs professional email content from analysis results.
"""

from datetime import datetime
from typing import Dict, List, Any
from jinja2 import Template


def build_email_html(analysis_result: Dict, history: Dict, email_context: Dict = None) -> str:
    """
    Build complete HTML email from analysis results.
    
    Args:
        analysis_result: Claude's analysis output
        history: Portfolio history data
        email_context: Additional context (VIX, earnings, sentiment)
    
    Returns:
        Complete HTML email string
    """
    # Extract additional context
    email_context = email_context or {}
    vix_data = email_context.get('vix_data', {})
    earnings_calendar = email_context.get('earnings_calendar', {})
    news_sentiment = email_context.get('news_sentiment', {})
    
    # Extract data
    macro = analysis_result.get('macro_assessment', {})
    portfolio_review = analysis_result.get('portfolio_review', [])
    sells = analysis_result.get('sells', [])
    new_recs = analysis_result.get('new_recommendations', [])
    metals = analysis_result.get('metals_commodities_outlook', {})
    politician_analysis = analysis_result.get('politician_trade_analysis', {})
    allocation = analysis_result.get('allocation_summary', {})
    risks = analysis_result.get('risks_to_portfolio', [])
    watchlist = analysis_result.get('watchlist', [])
    
    perf = history.get('performance_summary', {}) or {}
    monthly = history.get('monthly_history', []) or []
    current_portfolio = history.get('current_portfolio', []) or []
    cash = history.get('cash', {}) or {}
    total_months = history.get('metadata', {}).get('total_months', 0)
    
    # Calculate current month returns safely
    this_month_return = _safe_float(monthly[-1].get('portfolio_return_pct') if monthly else 0)
    sp500_return = _safe_float(monthly[-1].get('sp500_return_pct') if monthly else 0)
    total_return = _safe_float(perf.get('total_return_pct'))
    win_rate = _safe_float(perf.get('win_rate_pct'))
    win_count = int(_safe_float(perf.get('win_count')))
    loss_count = int(_safe_float(perf.get('loss_count')))
    
    # Determine if this is the first report (no history yet)
    is_first_report = total_months <= 1 and not monthly
    
    # Build HTML - Modern dark-mode friendly design
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="color-scheme" content="light dark">
    <meta name="supported-color-schemes" content="light dark">
    <title>Stock Insight Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            background-color: #0d1117;
            color: #e6edf3;
            padding: 16px;
        }}
        .container {{
            max-width: 680px;
            margin: 0 auto;
            background: #161b22;
            border-radius: 16px;
            border: 1px solid #30363d;
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #238636 0%, #1f6feb 100%);
            padding: 32px 24px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 28px;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 8px;
        }}
        .header .subtitle {{
            color: rgba(255,255,255,0.85);
            font-size: 14px;
        }}
        .section {{
            padding: 28px;
            border-bottom: 1px solid #30363d;
        }}
        .section:last-child {{ border-bottom: none; }}
        .section-title {{
            font-size: 20px;
            font-weight: 700;
            color: #58a6ff;
            margin-bottom: 20px;
            letter-spacing: -0.3px;
        }}
        .card {{
            background: #21262d;
            border: 1px solid #30363d;
            border-radius: 14px;
            padding: 20px;
            margin-bottom: 16px;
        }}
        .scorecard {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 16px;
        }}
        .score-box {{
            background: #21262d;
            border: 1px solid #30363d;
            border-radius: 14px;
            padding: 20px;
            text-align: center;
        }}
        .score-box.positive {{ border-left: 5px solid #238636; }}
        .score-box.negative {{ border-left: 5px solid #f85149; }}
        .score-box.neutral {{ border-left: 5px solid #d29922; }}
        .score-value {{
            font-size: 32px;
            font-weight: 800;
            color: #ffffff;
            letter-spacing: -1px;
            margin-bottom: 6px;
        }}
        .score-label {{
            font-size: 12px;
            color: #8b949e;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            font-weight: 500;
        }}
        .regime-badge {{
            display: inline-block;
            background: #238636;
            color: white;
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            margin-bottom: 12px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px 8px;
            text-align: left;
            border-bottom: 1px solid #30363d;
        }}
        th {{
            font-size: 11px;
            font-weight: 600;
            color: #8b949e;
            text-transform: uppercase;
        }}
        td {{ color: #e6edf3; }}
        .gain {{ color: #3fb950; font-weight: 600; }}
        .loss {{ color: #f85149; font-weight: 600; }}
        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
        }}
        .badge-buy {{ background: #238636; color: white; }}
        .badge-sell {{ background: #f85149; color: white; }}
        .badge-hold {{ background: #1f6feb; color: white; }}
        .badge-trim {{ background: #d29922; color: white; }}
        .rec-card {{
            background: #21262d;
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 16px;
        }}
        .rec-ticker {{
            font-size: 24px;
            font-weight: 700;
            color: #58a6ff;
        }}
        .rec-company {{
            color: #8b949e;
            font-size: 14px;
        }}
        .tag {{
            display: inline-block;
            background: #30363d;
            color: #e6edf3;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 11px;
            margin-right: 6px;
            margin-bottom: 6px;
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            background: #161b22;
            border-radius: 8px;
            padding: 12px;
            margin: 12px 0;
        }}
        .metric {{ text-align: center; }}
        .metric-label {{
            font-size: 10px;
            color: #8b949e;
            text-transform: uppercase;
        }}
        .metric-value {{
            font-size: 16px;
            font-weight: 700;
            color: #e6edf3;
        }}
        .thesis-box {{
            background: #0d419d;
            border-radius: 8px;
            padding: 12px;
            margin: 12px 0;
            color: #e6edf3;
            font-size: 14px;
        }}
        .risk-box {{
            background: #5d1f1f;
            border-radius: 8px;
            padding: 12px;
            color: #ffa198;
            font-size: 13px;
        }}
        .footer {{
            padding: 24px;
            text-align: center;
            color: #8b949e;
            font-size: 12px;
        }}
        .disclaimer {{
            background: #3d2a00;
            border: 1px solid #d29922;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 16px;
            color: #e6edf3;
            font-size: 11px;
        }}
        @media (max-width: 600px) {{
            body {{ padding: 8px; }}
            .header {{ padding: 20px 16px; }}
            .header h1 {{ font-size: 22px; }}
            .section {{ padding: 16px; }}
            .scorecard {{ grid-template-columns: 1fr 1fr; gap: 8px; }}
            .score-value {{ font-size: 22px; }}
            .metrics {{ grid-template-columns: 1fr; }}
        }}
        .vix-banner {{
            background: linear-gradient(135deg, #5d1f1f 0%, #8b2500 100%);
            padding: 12px 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            color: #ffa198;
            font-weight: 600;
            font-size: 14px;
        }}
        .vix-banner.elevated {{
            background: linear-gradient(135deg, #5d4a1f 0%, #8b6914 100%);
            color: #ffd666;
        }}
        .vix-banner.extreme {{
            background: linear-gradient(135deg, #5d1f1f 0%, #8b2500 100%);
            color: #ffa198;
        }}
        .badge {{
            display: inline-block;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 600;
            vertical-align: middle;
            margin-left: 4px;
        }}
        .badge-earnings {{
            background: #5d4a1f;
            color: #ffd666;
        }}
        .badge-sentiment-bullish {{
            background: #1f4a3d;
            color: #3fb950;
        }}
        .badge-sentiment-bearish {{
            background: #5d1f1f;
            color: #ffa198;
        }}
        .badge-sentiment-neutral {{
            background: #30363d;
            color: #8b949e;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>📊 Stock Insight</h1>
            <div class="subtitle">{datetime.now().strftime('%B %d, %Y')} • Bi-Weekly Report #{history.get('metadata', {}).get('total_months', 1)}</div>
        </div>
        
        {_build_vix_banner(vix_data)}
        
        <!-- Performance Scorecard -->
        <div class="section">
            <div class="section-title">📈 Performance</div>
            {f'''<div class="card" style="text-align: center; padding: 24px;">
                <div style="font-size: 40px; margin-bottom: 8px;">🚀</div>
                <div style="font-size: 16px; font-weight: 600; color: #3fb950;">Welcome to Your First Report!</div>
                <div style="color: #8b949e; font-size: 13px; margin-top: 8px;">Performance tracking begins next period after positions are established.</div>
            </div>''' if is_first_report else f'''
            <div class="scorecard">
                <div class="score-box {'positive' if this_month_return > 0 else 'negative' if this_month_return < 0 else 'neutral'}">
                    <div class="score-value">{this_month_return:+.1f}%</div>
                    <div class="score-label">This Period</div>
                </div>
                <div class="score-box {'positive' if sp500_return > 0 else 'negative' if sp500_return < 0 else 'neutral'}">
                    <div class="score-value">{sp500_return:+.1f}%</div>
                    <div class="score-label">S&P 500</div>
                </div>
                <div class="score-box {'positive' if total_return > 0 else 'negative' if total_return < 0 else 'neutral'}">
                    <div class="score-value">{total_return:+.1f}%</div>
                    <div class="score-label">Total Return</div>
                </div>
                <div class="score-box neutral">
                    <div class="score-value">{win_rate:.0f}%</div>
                    <div class="score-label">Win Rate ({win_count}W/{loss_count}L)</div>
                </div>
            </div>'''}
        </div>
        
        <!-- Macro Assessment -->
        <div class="section">
            <div class="section-title">🌍 Market Regime</div>
            <div class="card">
                <div class="regime-badge">{(macro.get('regime', 'Unknown') or 'Unknown').upper()}</div>
                <p style="color: #e6edf3; margin-bottom: 12px;">{macro.get('summary', 'No assessment available.') or 'No assessment available.'}</p>
                <div style="font-size: 13px; color: #8b949e;">
                    <strong style="color: #e6edf3;">Key Implications:</strong>
                    <ul style="margin-left: 20px; margin-top: 8px; color: #e6edf3;">
                        {''.join(f'<li style="margin-bottom: 4px;">{imp}</li>' for imp in (macro.get('implications', []) or []))}
                    </ul>
                </div>
            </div>
        </div>
        
        <!-- Current Holdings Review -->
        <div class="section">
            <div class="section-title">📋 Current Holdings</div>
            {_build_holdings_table(current_portfolio, portfolio_review, earnings_calendar, news_sentiment)}
        </div>
        
        <!-- Sells This Month -->
        {_build_sells_section(sells) if sells else ''}
        
        <!-- New Recommendations -->
        <div class="section">
            <div class="section-title">✨ New Recommendations</div>
            {_build_recommendations_section(new_recs)}
        </div>
        
        <!-- Metals & Commodities -->
        <div class="section">
            <div class="section-title">🥇 Commodities</div>
            {_build_metals_section(metals)}
        </div>
        
        <!-- Allocation Summary -->
        <div class="section">
            <div class="section-title">📊 Allocation</div>
            {_build_allocation_section(allocation, current_portfolio, cash)}
        </div>
        
        <!-- Politician Trades -->
        {_build_politician_section(politician_analysis)}
        
        <!-- Risks -->
        <div class="section">
            <div class="section-title">⚠️ Risks</div>
            {_build_risks_table(risks)}
        </div>
        
        <!-- Watchlist -->
        <div class="section">
            <div class="section-title">👀 Watchlist</div>
            {_build_watchlist_section(watchlist)}
        </div>
        
        <!-- Action Summary -->
        <div class="section">
            <div class="section-title">📝 Actions</div>
            {_build_action_summary(sells, portfolio_review, new_recs, cash)}
        </div>
        
        <!-- Footer -->
        <div class="footer">
            <div class="disclaimer">
                ⚠️ <strong>DISCLAIMER:</strong> This is not financial advice. For educational purposes only. 
                Past performance does not guarantee future results. Consult a licensed financial advisor.
            </div>
            <p>Next report: {_get_next_report_date()}</p>
            <p style="margin-top: 8px; color: #6e7681;">Generated by Stock Insight Agent</p>
        </div>
    </div>
</body>
</html>
"""
    
    return html


def _safe_float(val, default=0):
    """Safely convert value to float."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _build_vix_banner(vix_data: Dict) -> str:
    """Build VIX warning banner if volatility is elevated."""
    if not vix_data:
        return ''
    
    vix_level = _safe_float(vix_data.get('level'))
    warning_level = vix_data.get('warning_level', 'normal')
    
    if warning_level == 'normal' or vix_level < 25:
        return ''
    
    # Determine banner class and message
    if warning_level == 'extreme' or vix_level >= 30:
        banner_class = 'extreme'
        emoji = '🚨'
        message = f'HIGH FEAR: VIX at {vix_level:.1f} (Extreme volatility - consider defensive positioning)'
    else:
        banner_class = 'elevated'
        emoji = '⚠️'
        message = f'ELEVATED VIX: {vix_level:.1f} (Above average volatility - exercise caution)'
    
    return f'''
        <div class="vix-banner {banner_class}">
            <span>{emoji}</span>
            <span>{message}</span>
        </div>
    '''


def _build_holdings_table(holdings: List[Dict], reviews: List[Dict], earnings_calendar: Dict = None, news_sentiment: Dict = None) -> str:
    """Build HTML table for current holdings with earnings and sentiment badges."""
    # Filter out new BUY recommendations - only show existing positions
    existing_holdings = [h for h in holdings if h.get('status', '').upper() != 'BUY']
    earnings_calendar = earnings_calendar or {}
    news_sentiment = news_sentiment or {}
    
    if not existing_holdings:
        return '''<div class="card" style="text-align: center; padding: 24px;">
            <div style="font-size: 40px; margin-bottom: 8px;">🚀</div>
            <div style="font-size: 16px; font-weight: 600; color: #3fb950;">Portfolio Starting Fresh!</div>
            <div style="color: #8b949e; font-size: 13px; margin-top: 8px;">New recommendations below will establish your initial positions.</div>
        </div>'''
    
    # Create lookup for review actions
    review_lookup = {r.get('ticker'): r for r in reviews}
    
    rows = []
    for h in existing_holdings:
        ticker = h.get('ticker', '') or ''
        review = review_lookup.get(ticker, {})
        action = review.get('action', h.get('status', 'HOLD')) or 'HOLD'
        gain = _safe_float(h.get('gain_loss_pct'))
        rec_price = _safe_float(h.get('recommended_price'))
        cur_price = _safe_float(h.get('current_price'))
        alloc = _safe_float(h.get('allocation_pct'))
        
        # Build badges for ticker cell
        badges = ''
        
        # Earnings badge
        if ticker in earnings_calendar:
            earnings_info = earnings_calendar[ticker]
            earnings_date = earnings_info.get('earnings_date', 'Soon')
            badges += f'<span class="badge badge-earnings" title="Earnings: {earnings_date}">⚠️ EARNINGS</span>'
        
        # Sentiment badge
        if ticker in news_sentiment:
            sentiment_info = news_sentiment[ticker]
            sentiment_status = sentiment_info.get('status', 'neutral')
            sentiment_emoji = sentiment_info.get('emoji', '⚪')
            if sentiment_status == 'bullish':
                badges += f'<span class="badge badge-sentiment-bullish">{sentiment_emoji}</span>'
            elif sentiment_status == 'bearish':
                badges += f'<span class="badge badge-sentiment-bearish">{sentiment_emoji}</span>'
            elif sentiment_status in ['neutral', 'mixed']:
                badges += f'<span class="badge badge-sentiment-neutral">{sentiment_emoji}</span>'
        
        # Badge styling for action
        badge_bg = '#1f6feb'  # hold
        if action == 'SELL':
            badge_bg = '#f85149'
        elif action == 'TRIM':
            badge_bg = '#d29922'
        elif action == 'ADD':
            badge_bg = '#238636'
        
        gain_color = '#3fb950' if gain > 0 else '#f85149' if gain < 0 else '#8b949e'
        
        rows.append(f'''
            <tr>
                <td style="color: #58a6ff; font-weight: 600;">{ticker}{badges}</td>
                <td style="color: #e6edf3;">${rec_price:.2f}</td>
                <td style="color: #e6edf3;">${cur_price:.2f}</td>
                <td style="color: {gain_color}; font-weight: 600;">{gain:+.2f}%</td>
                <td style="color: #e6edf3;">{alloc:.1f}%</td>
                <td><span style="background: {badge_bg}; color: white; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 600;">{action}</span></td>
            </tr>
        ''')
    
    return f'''
        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr style="border-bottom: 1px solid #30363d;">
                    <th style="padding: 12px 8px; text-align: left; font-size: 11px; color: #8b949e; text-transform: uppercase;">Ticker</th>
                    <th style="padding: 12px 8px; text-align: left; font-size: 11px; color: #8b949e; text-transform: uppercase;">Entry</th>
                    <th style="padding: 12px 8px; text-align: left; font-size: 11px; color: #8b949e; text-transform: uppercase;">Current</th>
                    <th style="padding: 12px 8px; text-align: left; font-size: 11px; color: #8b949e; text-transform: uppercase;">P&L</th>
                    <th style="padding: 12px 8px; text-align: left; font-size: 11px; color: #8b949e; text-transform: uppercase;">Weight</th>
                    <th style="padding: 12px 8px; text-align: left; font-size: 11px; color: #8b949e; text-transform: uppercase;">Action</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
    '''


def _build_sells_section(sells: List[Dict]) -> str:
    """Build sells section HTML."""
    if not sells:
        return ''
    
    rows = []
    for s in sells:
        loss_pct = _safe_float(s.get('loss_pct'))
        rows.append(f"""
            <tr>
                <td><strong>{s.get('ticker', '') or ''}</strong></td>
                <td class="loss">{loss_pct:+.2f}%</td>
                <td>{s.get('reason', 'N/A') or 'N/A'}</td>
                <td style="font-style: italic; color: #666;">{s.get('lesson_learned', '') or ''}</td>
            </tr>
        """)
    
    return f"""
        <div class="section">
            <div class="section-title">🚨 Sells This Period</div>
            <table>
                <thead>
                    <tr>
                        <th>Ticker</th>
                        <th>Return</th>
                        <th>Reason</th>
                        <th>Lesson</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
    """


def _build_recommendations_section(recs: List[Dict]) -> str:
    """Build new recommendations section HTML."""
    if not recs:
        return '<p style="color: #8b949e; font-style: italic;">No new recommendations this period. Maintaining current positions.</p>'
    
    # Group by time horizon
    short_term = [r for r in recs if r.get('time_horizon') == 'short_term']
    medium_term = [r for r in recs if r.get('time_horizon') == 'medium_term']
    long_term = [r for r in recs if r.get('time_horizon') == 'long_term']
    
    sections = []
    
    if short_term:
        sections.append(_build_horizon_section('⚡ Short-term (1-3mo)', short_term))
    if medium_term:
        sections.append(_build_horizon_section('📊 Medium-term (3-12mo)', medium_term))
    if long_term:
        sections.append(_build_horizon_section('🏔️ Long-term (1-3yr)', long_term))
    
    return ''.join(sections)


def _build_horizon_section(title: str, recs: List[Dict]) -> str:
    """Build recommendation cards for a time horizon using table-based layouts for email compatibility."""
    cards = []
    for r in recs:
        entry = r.get('entry_zone', {}) or {}
        
        entry_low = _safe_float(entry.get('low'))
        entry_high = _safe_float(entry.get('high'))
        price_target = _safe_float(r.get('price_target'))
        stop_loss = _safe_float(r.get('stop_loss'))
        allocation = _safe_float(r.get('allocation_pct'))
        
        # Calculate upside potential
        if entry_low > 0 and price_target > 0:
            upside = ((price_target - entry_low) / entry_low) * 100
        else:
            upside = 0
        
        # Risk level colors
        risk = (r.get('risk_level', 'moderate') or 'moderate').lower()
        risk_bg = '#238636' if risk == 'conservative' else '#d29922' if risk == 'moderate' else '#f85149'
        
        # Email-compatible table-based card layout
        cards.append(f'''
            <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background: #21262d; border: 1px solid #30363d; border-radius: 16px; margin-bottom: 20px;">
                <tr>
                    <td style="padding: 24px;">
                        <!-- Header with ticker and allocation -->
                        <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-bottom: 16px;">
                            <tr>
                                <td style="vertical-align: top;">
                                    <div style="font-size: 28px; font-weight: 800; color: #58a6ff; letter-spacing: -0.5px;">{r.get('ticker', '') or ''}</div>
                                    <div style="color: #8b949e; font-size: 14px; margin-top: 4px;">{r.get('company_name', '') or ''}</div>
                                </td>
                                <td style="vertical-align: top; text-align: right; width: 80px;">
                                    <div style="background: #238636; color: white; padding: 10px 18px; border-radius: 10px; font-size: 18px; font-weight: 800; display: inline-block;">{allocation:.0f}%</div>
                                </td>
                            </tr>
                        </table>
                        
                        <!-- Tags row -->
                        <div style="margin-bottom: 20px;">
                            <span style="background: #30363d; color: #e6edf3; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 500; display: inline-block; margin-right: 8px; margin-bottom: 8px;">{r.get('sector', '') or ''}</span>
                            <span style="background: #30363d; color: #e6edf3; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 500; display: inline-block; margin-right: 8px; margin-bottom: 8px;">{(r.get('investment_style', '') or '').title()}</span>
                            <span style="background: {risk_bg}; color: white; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 600; display: inline-block; margin-bottom: 8px;">{risk.title()} Risk</span>
                        </div>
                        
                        <!-- Price metrics table -->
                        <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background: #161b22; border-radius: 12px; margin-bottom: 20px;">
                            <tr>
                                <td style="padding: 20px;">
                                    <table cellpadding="0" cellspacing="0" border="0" width="100%">
                                        <tr>
                                            <td style="font-size: 12px; color: #8b949e; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px; padding-bottom: 14px; border-bottom: 1px solid #30363d;">Buy Zone</td>
                                            <td style="font-size: 20px; font-weight: 700; color: #e6edf3; text-align: right; padding-bottom: 14px; border-bottom: 1px solid #30363d;">${entry_low:.0f} – ${entry_high:.0f}</td>
                                        </tr>
                                        <tr>
                                            <td style="font-size: 12px; color: #8b949e; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px; padding: 14px 0; border-bottom: 1px solid #30363d;">Target</td>
                                            <td style="font-size: 20px; font-weight: 700; color: #3fb950; text-align: right; padding: 14px 0; border-bottom: 1px solid #30363d;">${price_target:.0f} <span style="font-size: 14px; font-weight: 500; opacity: 0.8;">(+{upside:.0f}%)</span></td>
                                        </tr>
                                        <tr>
                                            <td style="font-size: 12px; color: #8b949e; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px; padding-top: 14px;">Stop Loss</td>
                                            <td style="font-size: 20px; font-weight: 700; color: #f85149; text-align: right; padding-top: 14px;">${stop_loss:.0f}</td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                        </table>
                        
                        <!-- Thesis -->
                        <div style="background: #0d419d; border-radius: 12px; padding: 16px; margin-bottom: 12px; color: #e6edf3; font-size: 14px; line-height: 1.6;">
                            <div style="font-weight: 600; margin-bottom: 6px;">💡 Investment Thesis</div>
                            {r.get('thesis', 'N/A') or 'N/A'}
                        </div>
                        
                        <!-- Risks -->
                        <div style="background: #5d1f1f; border-radius: 12px; padding: 16px; color: #ffa198; font-size: 14px; line-height: 1.6;">
                            <div style="font-weight: 600; margin-bottom: 6px;">⚠️ Key Risks</div>
                            {r.get('risks', 'N/A') or 'N/A'}
                        </div>
                    </td>
                </tr>
            </table>
        ''')
    
    return f'''
        <div style="margin-bottom: 20px;">
            <div style="font-size: 14px; font-weight: 600; color: #8b949e; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #30363d;">{title}</div>
            {''.join(cards)}
        </div>
    '''


def _build_metals_section(metals: Dict) -> str:
    """Build metals/commodities outlook section."""
    if not metals:
        return '<p style="color: #8b949e;">No commodities outlook available.</p>'
    
    items = []
    emojis = {'gold': '🥇', 'silver': '🥈', 'copper': '🟤', 'oil': '🛢️'}
    
    for commodity, data in metals.items():
        # Handle both dict and string formats
        if isinstance(data, str):
            items.append(f'''
                <div style="padding: 12px; background: #21262d; border: 1px solid #30363d; border-radius: 8px; margin: 8px 0;">
                    <strong style="color: #e6edf3;">{commodity.title()}</strong>: <span style="color: #8b949e;">{data}</span>
                </div>
            ''')
        else:
            stance = (data.get('stance', 'neutral') or 'neutral')
            color = '#3fb950' if stance == 'bullish' else '#f85149' if stance == 'bearish' else '#d29922'
            emoji = emojis.get(commodity.lower(), '📊')
            rationale = data.get('rationale', '') or ''
            
            items.append(f'''
                <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background: #21262d; border: 1px solid #30363d; border-radius: 8px; margin: 8px 0;">
                    <tr>
                        <td style="padding: 12px;">
                            <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-bottom: 8px;">
                                <tr>
                                    <td style="color: #e6edf3;">{emoji} <strong>{commodity.title()}</strong></td>
                                    <td style="text-align: right;"><span style="color: {color}; font-weight: 600; background: #161b22; padding: 4px 12px; border-radius: 20px; font-size: 12px;">{stance.upper()}</span></td>
                                </tr>
                            </table>
                            <p style="font-size: 13px; color: #8b949e; margin: 0;">{rationale}</p>
                        </td>
                    </tr>
                </table>
            ''')
    
    return ''.join(items)


def _build_allocation_section(allocation: Dict, holdings: List[Dict], cash: Dict) -> str:
    """Build allocation visualization section using email-compatible tables."""
    # If no holdings, show a simplified message
    if not holdings:
        return '<p style="color: #8b949e; font-style: italic;">Allocation will be tracked after first recommendations are executed.</p>'
    
    # Sector allocation from holdings
    sectors = {}
    for h in holdings:
        sector = h.get('sector', 'Other')
        sectors[sector] = sectors.get(sector, 0) + h.get('allocation_pct', 0)
    
    # Add cash
    cash_pct = cash.get('allocation_pct', 0)
    if cash_pct > 0:
        sectors['Cash'] = cash_pct
    
    # Color palette for dark mode
    colors = ['#238636', '#1f6feb', '#8957e5', '#d29922', '#f85149', '#58a6ff', '#3fb950', '#db61a2', '#79c0ff', '#7ee787']
    
    bars = []
    for i, (sector, pct) in enumerate(sorted(sectors.items(), key=lambda x: x[1], reverse=True)):
        color = colors[i % len(colors)]
        # Use table for email compatibility instead of flexbox
        bars.append(f'''
            <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background: #21262d; border: 1px solid #30363d; border-radius: 10px; margin-bottom: 12px;">
                <tr>
                    <td style="padding: 16px;">
                        <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-bottom: 10px;">
                            <tr>
                                <td style="color: #e6edf3; font-size: 14px; font-weight: 500;">{sector}</td>
                                <td style="text-align: right;"><span style="font-weight: 700; color: #ffffff; font-size: 16px; background: #30363d; padding: 4px 12px; border-radius: 6px;">{pct:.1f}%</span></td>
                            </tr>
                        </table>
                        <div style="height: 10px; background: #30363d; border-radius: 6px; overflow: hidden;">
                            <div style="height: 100%; width: {min(pct, 100)}%; background: {color}; border-radius: 6px;"></div>
                        </div>
                    </td>
                </tr>
            </table>
        ''')
    
    validation = allocation.get('validation', 'Unknown')
    validation_color = '#3fb950' if 'All within' in validation else '#f85149'
    
    return f'''
        <div style="margin-bottom: 20px;">
            {''.join(bars)}
        </div>
        <div style="background: #21262d; border: 1px solid #30363d; padding: 12px; border-radius: 8px; font-size: 13px;">
            <strong style="color: #8b949e;">Validation:</strong> <span style="color: {validation_color};">{validation}</span>
        </div>
    '''


def _build_politician_section(analysis: Dict) -> str:
    """Build politician trades section with improved UI."""
    if not analysis:
        return ''
    
    notable = analysis.get('notable_trades', [])
    suspicious = analysis.get('suspicious_patterns', [])
    overlap = analysis.get('overlap_with_portfolio', [])
    summary = analysis.get('summary', '')
    
    # Ensure these are lists, not strings
    if isinstance(notable, str):
        notable = [notable] if notable else []
    if isinstance(suspicious, str):
        suspicious = [suspicious] if suspicious else []
    if isinstance(overlap, str):
        overlap = [overlap] if overlap else []
    
    content = []
    
    # Summary section if available
    if summary and isinstance(summary, str) and len(summary) > 10:
        content.append(f'''
            <div style="background: #21262d; border: 1px solid #30363d; border-radius: 8px; padding: 16px; margin-bottom: 16px;">
                <p style="margin: 0; color: #e6edf3; font-size: 14px; line-height: 1.5;">{summary}</p>
            </div>
        ''')
    
    # Suspicious patterns - high priority alerts
    if suspicious and isinstance(suspicious, list):
        for s in suspicious[:5]:
            if isinstance(s, dict):
                politician = s.get('politician', 'Unknown')
                party = s.get('party', '')
                ticker = s.get('ticker', '')
                transaction = s.get('transaction_type', '')
                company = s.get('company', '')
                reason = s.get('correlation_reason', s.get('reason', ''))
                
                party_color = '#1f6feb' if 'D' in party else '#f85149' if 'R' in party else '#8b949e'
                
                content.append(f'''
                    <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background: #3d1f1f; border: 1px solid #f85149; border-radius: 12px; margin-bottom: 12px;">
                        <tr>
                            <td style="padding: 16px;">
                                <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-bottom: 10px;">
                                    <tr>
                                        <td>
                                            <span style="font-weight: 700; font-size: 16px; color: #f85149;">🚨 {politician}</span>
                                            <span style="background: {party_color}; color: white; padding: 2px 10px; border-radius: 12px; font-size: 11px; margin-left: 8px;">{party}</span>
                                        </td>
                                        <td style="text-align: right;">
                                            <span style="background: #f85149; color: white; padding: 4px 12px; border-radius: 6px; font-size: 12px; font-weight: 600;">{transaction}</span>
                                        </td>
                                    </tr>
                                </table>
                                <div style="font-size: 16px; font-weight: 600; color: #58a6ff; margin-bottom: 8px;">{ticker} — <span style="color: #8b949e; font-weight: 400;">{company}</span></div>
                                <div style="font-size: 13px; color: #ffa198; background: #2d1515; padding: 10px; border-radius: 6px;">{reason}</div>
                            </td>
                        </tr>
                    </table>
                ''')
            elif isinstance(s, str) and len(s) > 5:
                content.append(f'''
                    <div style="background: #3d1f1f; border: 1px solid #f85149; border-radius: 8px; padding: 12px; margin-bottom: 10px;">
                        <span style="color: #ffa198;">🚨 {s}</span>
                    </div>
                ''')
    
    # Notable trades
    if notable and isinstance(notable, list):
        for n in notable[:5]:
            if isinstance(n, dict):
                politician = n.get('politician', 'Unknown')
                party = n.get('party', '')
                ticker = n.get('ticker', '')
                transaction = n.get('transaction_type', '')
                amount = n.get('amount', '')
                insight = n.get('insight', n.get('implication', ''))
                
                party_color = '#1f6feb' if 'D' in party else '#f85149' if 'R' in party else '#8b949e'
                txn_color = '#238636' if 'buy' in transaction.lower() or 'purchase' in transaction.lower() else '#f85149'
                
                content.append(f'''
                    <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background: #21262d; border: 1px solid #30363d; border-radius: 12px; margin-bottom: 12px;">
                        <tr>
                            <td style="padding: 16px;">
                                <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-bottom: 10px;">
                                    <tr>
                                        <td>
                                            <span style="font-weight: 600; font-size: 15px; color: #e6edf3;">👤 {politician}</span>
                                            <span style="background: {party_color}; color: white; padding: 2px 10px; border-radius: 12px; font-size: 11px; margin-left: 8px;">{party}</span>
                                        </td>
                                        <td style="text-align: right;">
                                            <span style="background: {txn_color}; color: white; padding: 4px 12px; border-radius: 6px; font-size: 12px; font-weight: 600;">{transaction}</span>
                                        </td>
                                    </tr>
                                </table>
                                <div style="font-size: 18px; font-weight: 700; color: #58a6ff; margin-bottom: 6px;">{ticker}</div>
                                {f'<div style="font-size: 13px; color: #8b949e; margin-bottom: 8px;">Amount: {amount}</div>' if amount else ''}
                                {f'<div style="font-size: 13px; color: #e6edf3; background: #161b22; padding: 10px; border-radius: 6px;">{insight}</div>' if insight else ''}
                            </td>
                        </tr>
                    </table>
                ''')
            elif isinstance(n, str) and len(n) > 5:
                content.append(f'''
                    <div style="background: #21262d; border: 1px solid #30363d; border-radius: 8px; padding: 12px; margin-bottom: 10px;">
                        <span style="color: #e6edf3;">📋 {n}</span>
                    </div>
                ''')
    
    # Overlap with portfolio
    if overlap and isinstance(overlap, list):
        overlap_items = []
        for o in overlap[:5]:
            if isinstance(o, dict):
                ticker = o.get('ticker', '')
                politician = o.get('politician', '')
                implication = o.get('implication', '')
                overlap_items.append(f'''
                    <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background: #161b22; border-radius: 6px; margin-bottom: 8px;">
                        <tr>
                            <td style="padding: 10px; width: 60px; font-weight: 700; color: #58a6ff;">{ticker}</td>
                            <td style="padding: 10px; color: #e6edf3; font-size: 13px;">{politician} — {implication}</td>
                        </tr>
                    </table>
                ''')
            elif isinstance(o, str) and len(o) > 5:
                overlap_items.append(f'''
                    <div style="padding: 10px; background: #161b22; border-radius: 6px; margin-bottom: 6px; font-size: 13px; color: #e6edf3;">{o}</div>
                ''')
        
        if overlap_items:
            content.append(f'''
                <div style="background: #0d2d49; border: 1px solid #1f6feb; border-radius: 12px; padding: 16px; margin-top: 15px;">
                    <div style="font-weight: 600; color: #58a6ff; margin-bottom: 12px;">🔗 Overlap with Your Portfolio</div>
                    {''.join(overlap_items)}
                </div>
            ''')
    
    if not content:
        content.append('''
            <div style="text-align: center; padding: 24px; background: #21262d; border: 1px solid #30363d; border-radius: 8px;">
                <div style="font-size: 32px; margin-bottom: 8px;">✅</div>
                <div style="color: #8b949e; font-size: 14px;">No notable politician trades affecting portfolio this period.</div>
            </div>
        ''')
    
    return f'''
        <div class="section">
            <div class="section-title">🏛️ Congressional Trading</div>
            {''.join(content)}
        </div>
    '''


def _build_risks_table(risks: List[Dict]) -> str:
    """Build risks table."""
    if not risks:
        return '<p style="color: #8b949e;">No significant risks identified.</p>'
    
    rows = []
    for r in risks:
        # Handle both dict and string risk formats
        if isinstance(r, str):
            rows.append(f"""
                <tr>
                    <td colspan="4" style="padding: 12px; color: #e6edf3; border-bottom: 1px solid #30363d;">{r}</td>
                </tr>
            """)
        else:
            exposure = _safe_float(r.get('exposure_pct'))
            rows.append(f"""
                <tr>
                    <td style="padding: 12px; color: #e6edf3; border-bottom: 1px solid #30363d;"><strong>{r.get('risk', '') or ''}</strong></td>
                    <td style="padding: 12px; color: #8b949e; border-bottom: 1px solid #30363d;">{r.get('impact', '') or ''}</td>
                    <td style="padding: 12px; color: #ffa198; border-bottom: 1px solid #30363d; font-weight: 600;">{exposure:.0f}%</td>
                    <td style="padding: 12px; color: #8b949e; border-bottom: 1px solid #30363d;">{r.get('mitigation', '') or ''}</td>
                </tr>
            """)
    
    return f"""
        <table style="width: 100%; border-collapse: collapse; background: #161b22; border-radius: 8px; overflow: hidden;">
            <thead>
                <tr style="background: #21262d;">
                    <th style="padding: 12px; text-align: left; color: #e6edf3; font-weight: 600; border-bottom: 2px solid #30363d;">Risk</th>
                    <th style="padding: 12px; text-align: left; color: #e6edf3; font-weight: 600; border-bottom: 2px solid #30363d;">Impact</th>
                    <th style="padding: 12px; text-align: left; color: #e6edf3; font-weight: 600; border-bottom: 2px solid #30363d;">Exposure</th>
                    <th style="padding: 12px; text-align: left; color: #e6edf3; font-weight: 600; border-bottom: 2px solid #30363d;">Mitigation</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
    """


def _build_watchlist_section(watchlist: List[Dict]) -> str:
    """Build watchlist section."""
    if not watchlist:
        return '<p style="color: #8b949e;">No stocks on watchlist currently.</p>'
    
    items = []
    for w in watchlist:
        # Handle both dict and string formats
        if isinstance(w, str):
            items.append(f"""
                <div style="background: #161b22; border-radius: 8px; padding: 15px; margin-bottom: 10px; border-left: 3px solid #58a6ff;">
                    <div style="color: #e6edf3;">{w}</div>
                </div>
            """)
        else:
            items.append(f"""
                <div style="background: #161b22; border-radius: 8px; padding: 15px; margin-bottom: 10px; border-left: 3px solid #58a6ff;">
                    <div>
                        <strong style="color: #e6edf3; font-size: 16px;">{w.get('ticker', '') or ''}</strong>
                        <span style="color: #8b949e; margin-left: 10px;">{w.get('why_watching', '') or ''}</span>
                    </div>
                    <div style="color: #58a6ff; font-size: 12px; margin-top: 8px;">
                        🎯 Trigger: {w.get('entry_trigger', '') or ''}
                    </div>
                </div>
            """)
    
    return ''.join(items)


def _build_action_summary(sells: List[Dict], reviews: List[Dict], 
                          new_recs: List[Dict], cash: Dict) -> str:
    """Build action summary box."""
    sell_tickers = [s.get('ticker', '') for s in sells if s.get('ticker')]
    trim_items = [(r.get('ticker', ''), _safe_float(r.get('new_allocation_pct'))) 
                  for r in reviews if r.get('action') == 'TRIM']
    buy_items = [(r.get('ticker', ''), _safe_float(r.get('allocation_pct'))) for r in new_recs if r.get('ticker')]
    
    # Calculate cash from allocation - it's 100% minus all buy allocations
    total_buy_alloc = sum(_safe_float(r.get('allocation_pct')) for r in new_recs)
    cash_pct = _safe_float(cash.get('allocation_pct') if cash else max(0, 100 - total_buy_alloc))
    if cash_pct <= 0:
        cash_pct = max(0, 100 - total_buy_alloc)
    cash_vehicle = (cash.get('vehicle', 'SGOV') if cash else 'SGOV') or 'SGOV'
    
    # Build action items - dark theme friendly colors
    action_items = []
    
    if sell_tickers:
        action_items.append(f'''
            <div style="background: #3d1f1f; border-radius: 8px; padding: 12px; margin-bottom: 10px; border-left: 4px solid #f85149;">
                <div style="font-weight: 600; color: #ffa198; margin-bottom: 5px;">🔴 SELL</div>
                <div style="color: #e6edf3;">{', '.join(sell_tickers)}</div>
            </div>
        ''')
    
    if trim_items:
        trim_str = ', '.join(f'{t} → {p:.0f}%' for t, p in trim_items if t)
        action_items.append(f'''
            <div style="background: #3d2e1f; border-radius: 8px; padding: 12px; margin-bottom: 10px; border-left: 4px solid #d29922;">
                <div style="font-weight: 600; color: #e3b341; margin-bottom: 5px;">🟡 TRIM</div>
                <div style="color: #e6edf3;">{trim_str}</div>
            </div>
        ''')
    
    if buy_items:
        buy_str = ', '.join(f'{t} ({p:.0f}%)' for t, p in buy_items if t)
        action_items.append(f'''
            <div style="background: #1f3d1f; border-radius: 8px; padding: 12px; margin-bottom: 10px; border-left: 4px solid #3fb950;">
                <div style="font-weight: 600; color: #3fb950; margin-bottom: 5px;">🟢 BUY</div>
                <div style="color: #e6edf3;">{buy_str}</div>
            </div>
        ''')
    
    action_items.append(f'''
        <div style="background: #1a3a4f; border-radius: 8px; padding: 12px; border-left: 4px solid #58a6ff;">
            <div style="font-weight: 600; color: #58a6ff; margin-bottom: 5px;">💵 CASH RESERVE</div>
            <div style="color: #e6edf3;">{cash_pct:.0f}% in {cash_vehicle}</div>
        </div>
    ''')
    
    return f'''
        <div style="background: #161b22; border-radius: 12px; padding: 20px;">
            {''.join(action_items)}
        </div>
    '''


def _get_next_report_date() -> str:
    """Get the date two weeks from now for next bi-weekly report."""
    from datetime import timedelta
    next_report = datetime.now() + timedelta(weeks=2)
    return next_report.strftime('%B %d, %Y')
