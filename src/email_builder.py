"""
HTML email builder for stock analysis reports.
Constructs professional email content from analysis results.
"""

from datetime import datetime
from typing import Dict, List, Any
from jinja2 import Template


def build_email_html(analysis_result: Dict, history: Dict) -> str:
    """
    Build complete HTML email from analysis results.
    
    Args:
        analysis_result: Claude's analysis output
        history: Portfolio history data
    
    Returns:
        Complete HTML email string
    """
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
    
    perf = history.get('performance_summary', {})
    monthly = history.get('monthly_history', [])
    current_portfolio = history.get('current_portfolio', [])
    cash = history.get('cash', {})
    
    # Calculate current month returns
    this_month_return = monthly[-1].get('portfolio_return_pct', 0) if monthly else 0
    sp500_return = monthly[-1].get('sp500_return_pct', 0) if monthly else 0
    
    # Build HTML
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monthly Stock Analysis Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            color: #1a1a1a;
            background-color: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 28px;
            margin-bottom: 5px;
        }}
        .header .subtitle {{
            opacity: 0.9;
            font-size: 14px;
        }}
        .section {{
            padding: 25px 30px;
            border-bottom: 1px solid #eee;
        }}
        .section:last-child {{
            border-bottom: none;
        }}
        .section-title {{
            font-size: 18px;
            font-weight: 600;
            color: #1e3a5f;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .scorecard {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }}
        .score-box {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }}
        .score-box.positive {{
            background: #e8f5e9;
            border-left: 4px solid #4caf50;
        }}
        .score-box.negative {{
            background: #ffebee;
            border-left: 4px solid #f44336;
        }}
        .score-box.neutral {{
            background: #fff3e0;
            border-left: 4px solid #ff9800;
        }}
        .score-value {{
            font-size: 28px;
            font-weight: 700;
            color: #1e3a5f;
        }}
        .score-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
        }}
        .macro-box {{
            background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
            border-radius: 8px;
            padding: 20px;
        }}
        .regime-badge {{
            display: inline-block;
            background: #1e3a5f;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }}
        th, td {{
            padding: 12px 10px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #1e3a5f;
            font-size: 12px;
            text-transform: uppercase;
        }}
        .gain {{
            color: #4caf50;
            font-weight: 600;
        }}
        .loss {{
            color: #f44336;
            font-weight: 600;
        }}
        .action-badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
        }}
        .action-hold {{
            background: #e3f2fd;
            color: #1976d2;
        }}
        .action-sell {{
            background: #ffebee;
            color: #c62828;
        }}
        .action-buy {{
            background: #e8f5e9;
            color: #2e7d32;
        }}
        .action-trim {{
            background: #fff3e0;
            color: #ef6c00;
        }}
        .rec-card {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            border-left: 4px solid #1e3a5f;
        }}
        .rec-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .rec-ticker {{
            font-size: 18px;
            font-weight: 700;
            color: #1e3a5f;
        }}
        .rec-company {{
            font-size: 13px;
            color: #666;
        }}
        .rec-meta {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 10px;
        }}
        .meta-tag {{
            background: #e0e0e0;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            color: #424242;
        }}
        .rec-details {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            font-size: 13px;
            margin-bottom: 10px;
        }}
        .detail-item {{
            text-align: center;
        }}
        .detail-label {{
            font-size: 10px;
            color: #666;
            text-transform: uppercase;
        }}
        .detail-value {{
            font-weight: 600;
            color: #1e3a5f;
        }}
        .rec-thesis {{
            font-size: 13px;
            color: #333;
            padding: 10px;
            background: white;
            border-radius: 4px;
            margin-bottom: 8px;
        }}
        .rec-risks {{
            font-size: 12px;
            color: #c62828;
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        .horizon-section {{
            margin-bottom: 25px;
        }}
        .horizon-title {{
            font-size: 14px;
            font-weight: 600;
            color: #666;
            margin-bottom: 10px;
            padding-bottom: 5px;
            border-bottom: 2px solid #eee;
        }}
        .allocation-bar {{
            height: 24px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin: 8px 0;
        }}
        .allocation-fill {{
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            padding-right: 8px;
            font-size: 11px;
            font-weight: 600;
            color: white;
        }}
        .allocation-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 5px 0;
        }}
        .allocation-label {{
            font-size: 13px;
        }}
        .politician-alert {{
            background: #fff8e1;
            border: 1px solid #ffca28;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
        }}
        .politician-alert.suspicious {{
            background: #ffebee;
            border-color: #ef5350;
        }}
        .risk-table td:first-child {{
            width: 30%;
        }}
        .watchlist-item {{
            display: flex;
            justify-content: space-between;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 4px;
            margin: 8px 0;
        }}
        .action-summary {{
            background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
            color: white;
            border-radius: 8px;
            padding: 20px;
        }}
        .action-row {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.2);
        }}
        .action-row:last-child {{
            border-bottom: none;
        }}
        .footer {{
            background: #f5f5f5;
            padding: 20px 30px;
            font-size: 11px;
            color: #666;
            text-align: center;
        }}
        .disclaimer {{
            background: #fff3e0;
            border: 1px solid #ffb74d;
            border-radius: 4px;
            padding: 10px;
            margin-bottom: 15px;
            font-size: 11px;
        }}
        @media (max-width: 600px) {{
            .scorecard {{
                grid-template-columns: 1fr;
            }}
            .rec-details {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>📊 Monthly Stock Analysis</h1>
            <div class="subtitle">{datetime.now().strftime('%B %Y')} | Month #{history.get('metadata', {}).get('total_months', 1)} | Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
        </div>
        
        <!-- Performance Scorecard -->
        <div class="section">
            <div class="section-title">📈 Performance Scorecard</div>
            <div class="scorecard">
                <div class="score-box {'positive' if this_month_return > 0 else 'negative' if this_month_return < 0 else 'neutral'}">
                    <div class="score-value">{this_month_return:+.2f}%</div>
                    <div class="score-label">Our Return (This Month)</div>
                </div>
                <div class="score-box {'positive' if sp500_return > 0 else 'negative' if sp500_return < 0 else 'neutral'}">
                    <div class="score-value">{sp500_return:+.2f}%</div>
                    <div class="score-label">S&P 500 (This Month)</div>
                </div>
                <div class="score-box {'positive' if perf.get('total_return_pct', 0) > 0 else 'negative'}">
                    <div class="score-value">{perf.get('total_return_pct', 0):+.2f}%</div>
                    <div class="score-label">Total Return (Cumulative)</div>
                </div>
                <div class="score-box neutral">
                    <div class="score-value">{perf.get('win_rate_pct', 0):.0f}%</div>
                    <div class="score-label">Win Rate ({perf.get('win_count', 0)}W / {perf.get('loss_count', 0)}L)</div>
                </div>
            </div>
        </div>
        
        <!-- Macro Assessment -->
        <div class="section">
            <div class="section-title">🌍 Macro Regime Assessment</div>
            <div class="macro-box">
                <div class="regime-badge">{macro.get('regime', 'Unknown').upper()}</div>
                <p style="margin-bottom: 10px;">{macro.get('summary', 'No assessment available.')}</p>
                <div style="font-size: 13px;">
                    <strong>Implications:</strong>
                    <ul style="margin-left: 20px; margin-top: 5px;">
                        {''.join(f'<li>{imp}</li>' for imp in macro.get('implications', []))}
                    </ul>
                </div>
            </div>
        </div>
        
        <!-- Current Holdings Review -->
        <div class="section">
            <div class="section-title">📋 Current Holdings Review</div>
            {_build_holdings_table(current_portfolio, portfolio_review)}
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
            <div class="section-title">🥇 Metals & Commodities Outlook</div>
            {_build_metals_section(metals)}
        </div>
        
        <!-- Allocation Summary -->
        <div class="section">
            <div class="section-title">📊 Portfolio Allocation</div>
            {_build_allocation_section(allocation, current_portfolio, cash)}
        </div>
        
        <!-- Politician Trades -->
        {_build_politician_section(politician_analysis)}
        
        <!-- Risks -->
        <div class="section">
            <div class="section-title">⚠️ Risks to Portfolio</div>
            {_build_risks_table(risks)}
        </div>
        
        <!-- Watchlist -->
        <div class="section">
            <div class="section-title">👀 Watchlist</div>
            {_build_watchlist_section(watchlist)}
        </div>
        
        <!-- Action Summary -->
        <div class="section">
            <div class="section-title">📝 Action Summary</div>
            {_build_action_summary(sells, portfolio_review, new_recs, cash)}
        </div>
        
        <!-- Footer -->
        <div class="footer">
            <div class="disclaimer">
                ⚠️ <strong>DISCLAIMER:</strong> This is not financial advice. This report is for educational and informational purposes only. 
                Past performance does not guarantee future results. Always do your own research and consult with a licensed 
                financial advisor before making investment decisions.
            </div>
            <p>Next report: {_get_next_report_date()}</p>
            <p style="margin-top: 10px; color: #999;">Generated by Stock Insight Agent</p>
        </div>
    </div>
</body>
</html>
"""
    
    return html


def _build_holdings_table(holdings: List[Dict], reviews: List[Dict]) -> str:
    """Build HTML table for current holdings."""
    if not holdings:
        return '<p style="color: #666; font-style: italic;">No current holdings. Portfolio is 100% cash.</p>'
    
    # Create lookup for review actions
    review_lookup = {r.get('ticker'): r for r in reviews}
    
    rows = []
    for h in holdings:
        ticker = h.get('ticker', '')
        review = review_lookup.get(ticker, {})
        action = review.get('action', h.get('status', 'HOLD'))
        gain = h.get('gain_loss_pct', 0)
        
        action_class = 'action-hold'
        if action == 'SELL':
            action_class = 'action-sell'
        elif action == 'BUY':
            action_class = 'action-buy'
        elif action == 'TRIM':
            action_class = 'action-trim'
        
        rows.append(f"""
            <tr>
                <td><strong>{ticker}</strong></td>
                <td>${h.get('recommended_price', 0):.2f}</td>
                <td>${h.get('current_price', 0):.2f}</td>
                <td class="{'gain' if gain > 0 else 'loss'}">{gain:+.2f}%</td>
                <td>{h.get('allocation_pct', 0):.1f}%</td>
                <td><span class="{action_class} action-badge">{action}</span></td>
            </tr>
        """)
    
    return f"""
        <table>
            <thead>
                <tr>
                    <th>Ticker</th>
                    <th>Entry</th>
                    <th>Current</th>
                    <th>Gain/Loss</th>
                    <th>Weight</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
    """


def _build_sells_section(sells: List[Dict]) -> str:
    """Build sells section HTML."""
    if not sells:
        return ''
    
    rows = []
    for s in sells:
        rows.append(f"""
            <tr>
                <td><strong>{s.get('ticker', '')}</strong></td>
                <td class="loss">{s.get('loss_pct', 0):+.2f}%</td>
                <td>{s.get('reason', 'N/A')}</td>
                <td style="font-style: italic; color: #666;">{s.get('lesson_learned', '')}</td>
            </tr>
        """)
    
    return f"""
        <div class="section">
            <div class="section-title">🚨 Sells This Month</div>
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
        return '<p style="color: #666; font-style: italic;">No new recommendations this month. Maintaining current positions.</p>'
    
    # Group by time horizon
    short_term = [r for r in recs if r.get('time_horizon') == 'short_term']
    medium_term = [r for r in recs if r.get('time_horizon') == 'medium_term']
    long_term = [r for r in recs if r.get('time_horizon') == 'long_term']
    
    sections = []
    
    if short_term:
        sections.append(_build_horizon_section('⚡ Short-term Tactical (1-3mo)', short_term))
    if medium_term:
        sections.append(_build_horizon_section('📊 Medium-term Core (3-12mo)', medium_term))
    if long_term:
        sections.append(_build_horizon_section('🏔️ Long-term Compounders (1-3yr)', long_term))
    
    return ''.join(sections)


def _build_horizon_section(title: str, recs: List[Dict]) -> str:
    """Build recommendation cards for a time horizon."""
    cards = []
    for r in recs:
        entry = r.get('entry_zone', {})
        cards.append(f"""
            <div class="rec-card">
                <div class="rec-header">
                    <div>
                        <span class="rec-ticker">{r.get('ticker', '')}</span>
                        <span class="rec-company">— {r.get('company_name', '')}</span>
                    </div>
                    <span class="action-badge action-buy">{r.get('allocation_pct', 0):.0f}% Allocation</span>
                </div>
                <div class="rec-meta">
                    <span class="meta-tag">{r.get('sector', '')}</span>
                    <span class="meta-tag">{r.get('investment_style', '').title()}</span>
                    <span class="meta-tag">{r.get('risk_level', '').title()} Risk</span>
                    <span class="meta-tag">{r.get('asset_class', '').replace('_', ' ').title()}</span>
                </div>
                <div class="rec-details">
                    <div class="detail-item">
                        <div class="detail-label">Entry Zone</div>
                        <div class="detail-value">${entry.get('low', 0):.0f} - ${entry.get('high', 0):.0f}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Price Target</div>
                        <div class="detail-value" style="color: #4caf50;">${r.get('price_target', 0):.0f}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Stop Loss</div>
                        <div class="detail-value" style="color: #f44336;">${r.get('stop_loss', 0):.0f}</div>
                    </div>
                </div>
                <div class="rec-thesis">💡 <strong>Thesis:</strong> {r.get('thesis', 'N/A')}</div>
                <div class="rec-risks">⚠️ <strong>Risks:</strong> {r.get('risks', 'N/A')}</div>
            </div>
        """)
    
    return f"""
        <div class="horizon-section">
            <div class="horizon-title">{title}</div>
            {''.join(cards)}
        </div>
    """


def _build_metals_section(metals: Dict) -> str:
    """Build metals/commodities outlook section."""
    if not metals:
        return '<p style="color: #666;">No commodities outlook available.</p>'
    
    items = []
    emojis = {'gold': '🥇', 'silver': '🥈', 'copper': '🟤', 'oil': '🛢️'}
    
    for commodity, data in metals.items():
        stance = data.get('stance', 'neutral')
        color = '#4caf50' if stance == 'bullish' else '#f44336' if stance == 'bearish' else '#ff9800'
        emoji = emojis.get(commodity.lower(), '📊')
        
        items.append(f"""
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px; background: #f8f9fa; border-radius: 4px; margin: 8px 0;">
                <span>{emoji} <strong>{commodity.title()}</strong></span>
                <span style="color: {color}; font-weight: 600;">{stance.upper()}</span>
            </div>
            <p style="font-size: 12px; color: #666; margin-left: 30px; margin-bottom: 10px;">{data.get('rationale', '')}</p>
        """)
    
    return ''.join(items)


def _build_allocation_section(allocation: Dict, holdings: List[Dict], cash: Dict) -> str:
    """Build allocation visualization section."""
    # Sector allocation from holdings
    sectors = {}
    for h in holdings:
        sector = h.get('sector', 'Other')
        sectors[sector] = sectors.get(sector, 0) + h.get('allocation_pct', 0)
    
    # Add cash
    cash_pct = cash.get('allocation_pct', 0)
    if cash_pct > 0:
        sectors['Cash'] = cash_pct
    
    # Color palette
    colors = ['#1e3a5f', '#2d5a87', '#4a90a4', '#6db3c9', '#90cce0', '#b3e0f2', '#d6f0ff', '#e8f5fa', '#f0f9ff', '#fafafa', '#f5f5f5']
    
    bars = []
    for i, (sector, pct) in enumerate(sorted(sectors.items(), key=lambda x: x[1], reverse=True)):
        color = colors[i % len(colors)]
        bars.append(f"""
            <div class="allocation-row">
                <span class="allocation-label">{sector}</span>
                <span style="font-weight: 600;">{pct:.1f}%</span>
            </div>
            <div class="allocation-bar">
                <div class="allocation-fill" style="width: {pct}%; background: {color};">{pct:.0f}%</div>
            </div>
        """)
    
    validation = allocation.get('validation', 'Unknown')
    validation_style = 'color: #4caf50;' if 'All within' in validation else 'color: #f44336;'
    
    return f"""
        <div style="margin-bottom: 20px;">
            <h4 style="margin-bottom: 10px; color: #666;">By Sector</h4>
            {''.join(bars)}
        </div>
        <div style="background: #f8f9fa; padding: 10px; border-radius: 4px; font-size: 13px;">
            <strong>Validation:</strong> <span style="{validation_style}">{validation}</span>
        </div>
    """


def _build_politician_section(analysis: Dict) -> str:
    """Build politician trades section."""
    if not analysis:
        return ''
    
    notable = analysis.get('notable_trades', [])
    suspicious = analysis.get('suspicious_patterns', [])
    overlap = analysis.get('overlap_with_portfolio', [])
    
    content = []
    
    if suspicious:
        for s in suspicious[:5]:
            content.append(f"""
                <div class="politician-alert suspicious">
                    <strong>🚨 {s.get('politician', 'Unknown')}</strong> ({s.get('party', '')})<br>
                    {s.get('transaction_type', '')} {s.get('ticker', '')} — {s.get('company', '')}<br>
                    <span style="color: #c62828;">{s.get('correlation_reason', '')}</span>
                </div>
            """)
    
    if overlap:
        for o in overlap[:5]:
            content.append(f"""
                <div class="politician-alert">
                    <strong>{o.get('politician', '')}</strong> {o.get('transaction_type', '').lower()} {o.get('ticker', '')}<br>
                    <em>{o.get('implication', '')}</em>
                </div>
            """)
    
    if not content:
        content.append('<p style="color: #666;">No notable politician trades affecting portfolio this month.</p>')
    
    return f"""
        <div class="section">
            <div class="section-title">🏛️ Politician Trade Alerts</div>
            {''.join(content)}
        </div>
    """


def _build_risks_table(risks: List[Dict]) -> str:
    """Build risks table."""
    if not risks:
        return '<p style="color: #666;">No significant risks identified.</p>'
    
    rows = []
    for r in risks:
        rows.append(f"""
            <tr>
                <td><strong>{r.get('risk', '')}</strong></td>
                <td>{r.get('impact', '')}</td>
                <td>{r.get('exposure_pct', 0):.0f}%</td>
                <td>{r.get('mitigation', '')}</td>
            </tr>
        """)
    
    return f"""
        <table class="risk-table">
            <thead>
                <tr>
                    <th>Risk</th>
                    <th>Impact</th>
                    <th>Exposure</th>
                    <th>Mitigation</th>
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
        return '<p style="color: #666;">No stocks on watchlist currently.</p>'
    
    items = []
    for w in watchlist:
        items.append(f"""
            <div class="watchlist-item">
                <div>
                    <strong>{w.get('ticker', '')}</strong>
                    <span style="color: #666; margin-left: 10px;">{w.get('why_watching', '')}</span>
                </div>
                <div style="color: #1976d2; font-size: 12px;">
                    Trigger: {w.get('entry_trigger', '')}
                </div>
            </div>
        """)
    
    return ''.join(items)


def _build_action_summary(sells: List[Dict], reviews: List[Dict], 
                          new_recs: List[Dict], cash: Dict) -> str:
    """Build action summary box."""
    sell_tickers = [s.get('ticker') for s in sells]
    trim_items = [(r.get('ticker'), r.get('new_allocation_pct')) 
                  for r in reviews if r.get('action') == 'TRIM']
    buy_items = [(r.get('ticker'), r.get('allocation_pct')) for r in new_recs]
    
    return f"""
        <div class="action-summary">
            <div class="action-row">
                <span>🔴 SELL:</span>
                <span>{', '.join(sell_tickers) if sell_tickers else 'None'}</span>
            </div>
            <div class="action-row">
                <span>🟡 TRIM:</span>
                <span>{', '.join(f'{t} → {p:.0f}%' for t, p in trim_items) if trim_items else 'None'}</span>
            </div>
            <div class="action-row">
                <span>🟢 BUY:</span>
                <span>{', '.join(f'{t} ({p:.0f}%)' for t, p in buy_items) if buy_items else 'None'}</span>
            </div>
            <div class="action-row">
                <span>💵 CASH:</span>
                <span>{cash.get('allocation_pct', 0):.1f}% ({cash.get('vehicle', 'SGOV')})</span>
            </div>
        </div>
    """


def _get_next_report_date() -> str:
    """Get the first of next month for next report date."""
    today = datetime.now()
    if today.month == 12:
        next_month = datetime(today.year + 1, 1, 1)
    else:
        next_month = datetime(today.year, today.month + 1, 1)
    return next_month.strftime('%B 1, %Y')
