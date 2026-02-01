"""
Stock Pulse Email Builder - Gmail Compatible (Biweekly Edition)
Matches the Stock Pulse design with TABLE-based layout and inline styles.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Safely convert a value to float."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def build_email_html(analysis_result: Dict[str, Any], history: Dict[str, Any] = None, email_context: Dict[str, Any] = None) -> str:
    """
    Build Gmail-compatible HTML email matching the Stock Pulse design.
    """
    if history is None:
        history = {}
    if email_context is None:
        email_context = {}
    
    # Extract data from various possible structures
    market_overview = analysis_result.get("market_overview", {})
    holdings_analysis = analysis_result.get("holdings_analysis", [])
    recommendations = analysis_result.get("recommendations", analysis_result.get("new_recommendations", []))
    market_signals = analysis_result.get("market_signals", {})
    news_sentiment = email_context.get("news_sentiment", {})  # Get from email_context, not analysis_result
    sentiment_summary = email_context.get("sentiment_summary", {})
    politicians = analysis_result.get("politician_trades", [])
    
    # Extract new context data
    triggered_alerts = email_context.get("triggered_alerts", [])
    dividend_calendar = email_context.get("dividend_calendar", {})
    is_first_run = email_context.get("is_first_run", False)
    
    # Also check for alternative data structures
    if not recommendations:
        recommendations = analysis_result.get("portfolio_review", [])
    
    # Get allocation summary
    allocation = analysis_result.get("allocation_summary", {})
    
    # Get current date
    current_date = datetime.now().strftime("%B %d, %Y")
    
    # Calculate portfolio value for position sizing
    starting_capital = _safe_float(history.get('metadata', {}).get('starting_capital', 100000))
    monthly = history.get('monthly_history', [])
    current_value = monthly[-1].get('ending_value', starting_capital) if monthly else starting_capital
    
    # Get current portfolio for attribution
    current_portfolio = history.get('current_portfolio', [])
    this_month_return = monthly[-1].get('portfolio_return_pct', 0) if monthly else 0
    
    # Build all sections
    header_html = _build_header(current_date)
    welcome_html = _build_welcome_section(is_first_run, len(recommendations))
    urgent_alerts_html = _build_urgent_alerts_section(triggered_alerts, current_value)
    market_pulse_html = _build_market_pulse(market_overview, email_context)
    news_sentiment_html = _build_news_sentiment_section(news_sentiment, sentiment_summary)
    performance_attribution_html = _build_performance_attribution_section(current_portfolio, this_month_return, current_value)
    holdings_analysis_html = _build_holdings_analysis_section(current_portfolio, current_value)
    action_plan_html = _build_action_plan(recommendations, allocation, analysis_result)
    stock_picks_html = _build_stock_picks(recommendations, analysis_result, current_value)
    dividend_calendar_html = _build_dividend_calendar_section(dividend_calendar, current_portfolio, current_value)
    retail_insights_html = _build_retail_investor_section(email_context.get('retail_analysis', {}), current_value)
    politicians_html = _build_politicians_section(politicians)
    tracker_html = _build_recommendation_tracker(history, current_value)
    comparison_html = _build_sp500_comparison(history)
    footer_html = _build_footer()
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stock Pulse | Biweekly Advisor</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0a0a0f; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #0a0a0f;">
        <tr>
            <td align="center" style="padding: 0;">
                <!-- Main Container -->
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="700" style="max-width: 700px; background-color: #12121a; border-left: 1px solid rgba(255,255,255,0.08); border-right: 1px solid rgba(255,255,255,0.08);">
                    
                    {header_html}
                    
                    {welcome_html}
                    
                    {urgent_alerts_html}
                    
                    {market_pulse_html}
                    
                    {news_sentiment_html}
                    
                    {performance_attribution_html}
                    
                    {holdings_analysis_html}
                    
                    {action_plan_html}
                    
                    {stock_picks_html}
                    
                    {dividend_calendar_html}
                    
                    {retail_insights_html}
                    
                    {politicians_html}
                    
                    {tracker_html}
                    
                    {comparison_html}
                    
                    {footer_html}
                    
                </table>
            </td>
        </tr>
    </table>
</body>
</html>'''
    
    return html


def _build_header(current_date: str) -> str:
    """Build the header section with logo and title."""
    return f'''
                    <!-- Header -->
                    <tr>
                        <td style="padding: 40px 32px; border-bottom: 1px solid rgba(255,255,255,0.08); background: linear-gradient(180deg, rgba(212,175,55,0.05) 0%, transparent 100%);">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td>
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td style="vertical-align: middle;">
                                                    <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                                                        <tr>
                                                            <td style="width: 44px; height: 44px; background: linear-gradient(135deg, #d4af37 0%, #f4d03f 50%, #d4af37 100%); border-radius: 10px; text-align: center; vertical-align: middle;">
                                                                <span style="font-family: Georgia, serif; font-weight: 700; font-size: 22px; color: #0a0a0f;">SP</span>
                                                            </td>
                                                            <td style="padding-left: 12px;">
                                                                <span style="font-family: Georgia, serif; font-size: 26px; font-weight: 600; color: #f5f5f7; letter-spacing: -0.5px;">Stock Pulse</span>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>
                                                <td align="right" style="vertical-align: middle;">
                                                    <span style="font-size: 11px; font-weight: 600; letter-spacing: 1.5px; text-transform: uppercase; color: #d4af37; background: rgba(212,175,55,0.15); padding: 6px 12px; border-radius: 4px;">Biweekly Edition</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding-top: 24px;">
                                        <span style="font-family: Georgia, serif; font-size: 36px; font-weight: 700; color: #f5f5f7; letter-spacing: -1px; display: block;">Market Intelligence Report</span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding-top: 8px;">
                                        <span style="color: #d4af37; font-weight: 500; font-size: 15px;">{current_date}</span>
                                        <span style="color: #a0a0b0; font-size: 15px;"> · Your biweekly edge in the market</span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>'''


def _build_welcome_section(is_first_run: bool, num_recommendations: int) -> str:
    """Build welcome section for first-time users."""
    if not is_first_run:
        return ""
    
    return f'''
                    <!-- Welcome Section for First Run -->
                    <tr>
                        <td style="padding: 32px; border-bottom: 1px solid rgba(255,255,255,0.08); background: linear-gradient(135deg, rgba(212,175,55,0.1) 0%, rgba(0,212,170,0.05) 100%);">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td align="center">
                                        <span style="font-size: 48px;">🎉</span>
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="padding-top: 16px;">
                                        <span style="font-family: Georgia, serif; font-size: 28px; font-weight: 700; color: #f5f5f7;">Welcome to Stock Pulse!</span>
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="padding-top: 12px; padding-left: 40px; padding-right: 40px;">
                                        <span style="font-size: 15px; color: #a0a0b0; line-height: 1.7;">This is your first portfolio analysis. We've analyzed 1,500+ stocks across all sectors and identified <strong style="color: #00d4aa;">{num_recommendations} opportunities</strong> to build your diversified portfolio.</span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding-top: 24px;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td width="33%" style="padding: 0 8px;">
                                                    <div style="background: #1a1a24; border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 16px; text-align: center;">
                                                        <span style="display: block; font-size: 24px;">📊</span>
                                                        <span style="display: block; font-size: 12px; color: #d4af37; font-weight: 600; padding-top: 8px;">STEP 1</span>
                                                        <span style="display: block; font-size: 13px; color: #f5f5f7; padding-top: 4px;">Review the picks below</span>
                                                    </div>
                                                </td>
                                                <td width="33%" style="padding: 0 8px;">
                                                    <div style="background: #1a1a24; border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 16px; text-align: center;">
                                                        <span style="display: block; font-size: 24px;">💰</span>
                                                        <span style="display: block; font-size: 12px; color: #d4af37; font-weight: 600; padding-top: 8px;">STEP 2</span>
                                                        <span style="display: block; font-size: 13px; color: #f5f5f7; padding-top: 4px;">Invest per allocation %</span>
                                                    </div>
                                                </td>
                                                <td width="33%" style="padding: 0 8px;">
                                                    <div style="background: #1a1a24; border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 16px; text-align: center;">
                                                        <span style="display: block; font-size: 24px;">📈</span>
                                                        <span style="display: block; font-size: 12px; color: #d4af37; font-weight: 600; padding-top: 8px;">STEP 3</span>
                                                        <span style="display: block; font-size: 13px; color: #f5f5f7; padding-top: 4px;">Check back in 2 weeks</span>
                                                    </div>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="padding-top: 20px;">
                                        <div style="background: rgba(212,175,55,0.1); border: 1px solid rgba(212,175,55,0.3); border-radius: 8px; padding: 12px 20px; display: inline-block;">
                                            <span style="font-size: 13px; color: #d4af37;">💡 <strong>Pro tip:</strong> Start with a small amount to get comfortable, then scale up</span>
                                        </div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>'''


def _build_news_sentiment_section(news_sentiment: Dict, sentiment_summary: Dict) -> str:
    """Build the news sentiment summary section."""
    if not news_sentiment and not sentiment_summary:
        return ""
    
    # Get overall market sentiment
    overall_bullish = sentiment_summary.get('overall_bullish_pct', 50)
    overall_label = sentiment_summary.get('overall_label', 'NEUTRAL')
    analyzed_count = len(news_sentiment) if news_sentiment else 0
    
    if analyzed_count == 0:
        return ""
    
    # Determine sentiment styling
    if overall_bullish >= 60:
        sentiment_color = "#00d4aa"
        sentiment_bg = "rgba(0,212,170,0.12)"
        sentiment_emoji = "🟢"
        sentiment_text = "Bullish"
    elif overall_bullish <= 40:
        sentiment_color = "#ff6b6b"
        sentiment_bg = "rgba(255,107,107,0.12)"
        sentiment_emoji = "🔴"
        sentiment_text = "Bearish"
    else:
        sentiment_color = "#ffd93d"
        sentiment_bg = "rgba(255,217,61,0.12)"
        sentiment_emoji = "⚪"
        sentiment_text = "Neutral"
    
    # Build individual stock sentiment badges
    stock_badges = ""
    sorted_sentiment = sorted(news_sentiment.items(), key=lambda x: x[1].get('bullish_pct', 50), reverse=True)
    
    for ticker, data in sorted_sentiment[:8]:
        bullish = data.get('bullish_pct', 50)
        emoji = data.get('emoji', '⚪')
        
        if bullish >= 60:
            badge_color = "#00d4aa"
            badge_bg = "rgba(0,212,170,0.15)"
        elif bullish <= 40:
            badge_color = "#ff6b6b"
            badge_bg = "rgba(255,107,107,0.15)"
        else:
            badge_color = "#a0a0b0"
            badge_bg = "rgba(255,255,255,0.08)"
        
        stock_badges += f'''
                                            <td style="padding: 4px;">
                                                <div style="background: {badge_bg}; border-radius: 6px; padding: 8px 12px; text-align: center; white-space: nowrap;">
                                                    <span style="font-family: 'Consolas', monospace; font-size: 12px; font-weight: 600; color: {badge_color};">{ticker}</span>
                                                    <span style="font-size: 12px; color: {badge_color}; padding-left: 4px;">{emoji} {bullish:.0f}%</span>
                                                </div>
                                            </td>'''
    
    return f'''
                    <!-- News Sentiment Section -->
                    <tr>
                        <td style="padding: 24px 32px; border-bottom: 1px solid rgba(255,255,255,0.08); background: {sentiment_bg};">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td>
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td>
                                                    <span style="display: inline-block; width: 32px; height: 32px; background-color: #22222e; border-radius: 8px; text-align: center; line-height: 32px; font-size: 16px; vertical-align: middle;">📰</span>
                                                    <span style="font-family: Georgia, serif; font-size: 18px; font-weight: 600; color: #f5f5f7; padding-left: 10px; vertical-align: middle;">News Sentiment</span>
                                                </td>
                                                <td align="right">
                                                    <span style="font-size: 24px; vertical-align: middle;">{sentiment_emoji}</span>
                                                    <span style="font-size: 14px; font-weight: 600; color: {sentiment_color}; padding-left: 8px; vertical-align: middle;">{sentiment_text} ({overall_bullish:.0f}% Bullish)</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding-top: 12px;">
                                        <span style="font-size: 12px; color: #6b6b7b;">AI-analyzed sentiment from {analyzed_count} stocks based on recent news coverage:</span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding-top: 12px;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                                            <tr>
                                                {stock_badges}
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>'''


def _build_holdings_analysis_section(current_portfolio: List[Dict], current_value: float) -> str:
    """Build detailed holdings analysis section showing each position's status."""
    if not current_portfolio:
        return ""
    
    holdings_rows = ""
    total_invested = 0
    total_gain_loss = 0
    
    for holding in current_portfolio:
        ticker = holding.get('ticker', 'N/A')
        company = holding.get('company_name', ticker)
        entry_price = _safe_float(holding.get('recommended_price', holding.get('entry_price', 0)))
        current_price = _safe_float(holding.get('current_price', 0))
        gain_loss_pct = _safe_float(holding.get('gain_loss_pct', 0))
        allocation = _safe_float(holding.get('allocation_pct', 0))
        stop_loss = _safe_float(holding.get('stop_loss', 0))
        price_target = _safe_float(holding.get('price_target', 0))
        
        # FIXED: Calculate dollar P&L correctly
        # Original investment = current_value * allocation / (1 + gain_loss_pct/100)
        # This gives us what we originally put in, not inflated by gains
        # Alternatively: dollar_gain = original_investment * gain_loss_pct / 100
        if gain_loss_pct != 0 and allocation > 0:
            # Current position value
            position_value = current_value * (allocation / 100)
            # Work backwards to find original investment
            # current_value_of_position = original_investment * (1 + gain/100)
            # original_investment = current_value_of_position / (1 + gain/100)
            original_investment = position_value / (1 + gain_loss_pct / 100)
            # Dollar gain = current - original
            dollar_gain = position_value - original_investment
        else:
            position_value = current_value * (allocation / 100) if allocation > 0 else 0
            original_investment = position_value
            dollar_gain = 0
        
        total_invested += original_investment
        total_gain_loss += dollar_gain
        
        # Determine status
        if current_price > 0 and stop_loss > 0 and current_price <= stop_loss * 1.05:
            status = "⚠️ Near Stop"
            status_color = "#ff6b6b"
        elif current_price > 0 and price_target > 0 and current_price >= price_target * 0.95:
            status = "🎯 Near Target"
            status_color = "#00d4aa"
        elif gain_loss_pct >= 20:
            status = "🚀 Strong"
            status_color = "#00d4aa"
        elif gain_loss_pct >= 5:
            status = "✅ Healthy"
            status_color = "#00d4aa"
        elif gain_loss_pct <= -15:
            status = "🔴 Review"
            status_color = "#ff6b6b"
        elif gain_loss_pct <= -5:
            status = "⚠️ Watch"
            status_color = "#ffd93d"
        else:
            status = "➖ Flat"
            status_color = "#a0a0b0"
        
        # P&L styling
        pnl_color = "#00d4aa" if gain_loss_pct >= 0 else "#ff6b6b"
        pnl_sign = "+" if gain_loss_pct >= 0 else ""
        dollar_sign = "+" if dollar_gain >= 0 else "-"
        
        holdings_rows += f'''
                                    <tr>
                                        <td style="padding: 14px 12px; border-bottom: 1px solid rgba(255,255,255,0.06);">
                                            <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                                                <tr>
                                                    <td>
                                                        <span style="font-family: 'Consolas', monospace; font-weight: 600; font-size: 14px; color: #f5f5f7;">{ticker}</span>
                                                        <span style="display: block; font-size: 11px; color: #6b6b7b; padding-top: 2px;">{company[:20]}</span>
                                                    </td>
                                                </tr>
                                            </table>
                                        </td>
                                        <td style="padding: 14px 12px; border-bottom: 1px solid rgba(255,255,255,0.06); text-align: center;">
                                            <span style="font-family: 'Consolas', monospace; font-size: 13px; color: #a0a0b0;">${entry_price:.2f}</span>
                                        </td>
                                        <td style="padding: 14px 12px; border-bottom: 1px solid rgba(255,255,255,0.06); text-align: center;">
                                            <span style="font-family: 'Consolas', monospace; font-size: 13px; color: #f5f5f7;">${current_price:.2f}</span>
                                        </td>
                                        <td style="padding: 14px 12px; border-bottom: 1px solid rgba(255,255,255,0.06); text-align: center;">
                                            <span style="font-family: 'Consolas', monospace; font-size: 13px; font-weight: 600; color: {pnl_color};">{pnl_sign}{gain_loss_pct:.1f}%</span>
                                            <span style="display: block; font-size: 11px; color: {pnl_color};">{dollar_sign}${abs(dollar_gain):,.0f}</span>
                                        </td>
                                        <td style="padding: 14px 12px; border-bottom: 1px solid rgba(255,255,255,0.06); text-align: center;">
                                            <span style="font-size: 12px; color: {status_color};">{status}</span>
                                        </td>
                                        <td style="padding: 14px 12px; border-bottom: 1px solid rgba(255,255,255,0.06); text-align: right;">
                                            <span style="font-size: 12px; color: #6b6b7b;">Stop: ${stop_loss:.2f}</span>
                                            <span style="display: block; font-size: 12px; color: #6b6b7b;">Target: ${price_target:.2f}</span>
                                        </td>
                                    </tr>'''
    
    # Summary styling
    total_pnl_color = "#00d4aa" if total_gain_loss >= 0 else "#ff6b6b"
    total_sign = "+" if total_gain_loss >= 0 else "-"
    
    return f'''
                    <!-- Holdings Analysis Section -->
                    <tr>
                        <td style="padding: 32px; border-bottom: 1px solid rgba(255,255,255,0.08);">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td>
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td>
                                                    <span style="display: inline-block; width: 32px; height: 32px; background-color: #22222e; border-radius: 8px; text-align: center; line-height: 32px; font-size: 16px; vertical-align: middle;">💼</span>
                                                    <span style="font-family: Georgia, serif; font-size: 22px; font-weight: 600; color: #f5f5f7; padding-left: 10px; vertical-align: middle;">Current Holdings</span>
                                                </td>
                                                <td align="right">
                                                    <span style="font-size: 11px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; color: #6b6b7b; background-color: #22222e; padding: 6px 10px; border-radius: 4px;">{len(current_portfolio)} Positions</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding-top: 20px;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background: #1a1a24; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; overflow: hidden;">
                                            <tr style="background: rgba(0,0,0,0.3);">
                                                <th style="padding: 12px; text-align: left; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #6b6b7b;">Stock</th>
                                                <th style="padding: 12px; text-align: center; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #6b6b7b;">Entry</th>
                                                <th style="padding: 12px; text-align: center; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #6b6b7b;">Current</th>
                                                <th style="padding: 12px; text-align: center; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #6b6b7b;">P&L</th>
                                                <th style="padding: 12px; text-align: center; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #6b6b7b;">Status</th>
                                                <th style="padding: 12px; text-align: right; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #6b6b7b;">Levels</th>
                                            </tr>
                                            {holdings_rows}
                                        </table>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding-top: 16px;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background: #22222e; border-radius: 8px; padding: 12px 16px;">
                                            <tr>
                                                <td>
                                                    <span style="font-size: 13px; color: #6b6b7b;">Total Unrealized P&L:</span>
                                                </td>
                                                <td align="right">
                                                    <span style="font-family: 'Consolas', monospace; font-size: 18px; font-weight: 700; color: {total_pnl_color};">{total_sign}${abs(total_gain_loss):,.0f}</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>'''


def _build_urgent_alerts_section(triggered_alerts: List[Dict], current_value: float) -> str:
    """
    Build the URGENT ALERTS section for stop-loss and target hits.
    This appears at the TOP of the email for immediate visibility.
    """
    if not triggered_alerts:
        return ""
    
    stop_losses = [a for a in triggered_alerts if a.get('alert_type') == 'STOP_LOSS']
    targets_hit = [a for a in triggered_alerts if a.get('alert_type') == 'TARGET_HIT']
    
    alerts_html = ""
    
    # Build stop-loss alerts (urgent/red)
    for alert in stop_losses:
        ticker = alert.get('ticker', 'N/A')
        company = alert.get('company_name', ticker)
        current_price = _safe_float(alert.get('current_price'))
        entry_price = _safe_float(alert.get('entry_price'))
        trigger_price = _safe_float(alert.get('trigger_price'))
        loss_pct = _safe_float(alert.get('gain_loss_pct'))
        allocation = _safe_float(alert.get('allocation_pct'))
        
        # Calculate dollar loss
        position_value = current_value * (allocation / 100) if allocation > 0 else 0
        dollar_loss = position_value * (loss_pct / 100) if loss_pct != 0 else 0
        
        alerts_html += f'''
                                <tr>
                                    <td style="padding: 12px 0;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background: linear-gradient(90deg, rgba(255,107,107,0.15) 0%, #1a1a24 100%); border-left: 4px solid #ff6b6b; border-radius: 8px;">
                                            <tr>
                                                <td style="padding: 16px;">
                                                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                                        <tr>
                                                            <td width="40" style="vertical-align: top; font-size: 28px;">🔴</td>
                                                            <td style="padding-left: 12px;">
                                                                <span style="display: block; font-weight: 700; font-size: 16px; color: #ff6b6b;">{ticker} - STOP-LOSS TRIGGERED</span>
                                                                <span style="display: block; font-size: 14px; color: #a0a0b0; padding-top: 4px;">{company} dropped to ${current_price:.2f} (entry: ${entry_price:.2f})</span>
                                                                <span style="display: block; font-size: 14px; color: #ff6b6b; padding-top: 4px;">Loss: {loss_pct:.1f}% (${abs(dollar_loss):,.0f})</span>
                                                                <span style="display: inline-block; margin-top: 8px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; padding: 6px 12px; border-radius: 4px; color: #ff6b6b; background: rgba(255,107,107,0.12); border: 1px solid rgba(255,107,107,0.3);">⚡ SELL to limit losses</span>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>'''
    
    # Build target-hit alerts (green/celebration)
    for alert in targets_hit:
        ticker = alert.get('ticker', 'N/A')
        company = alert.get('company_name', ticker)
        current_price = _safe_float(alert.get('current_price'))
        entry_price = _safe_float(alert.get('entry_price'))
        trigger_price = _safe_float(alert.get('trigger_price'))
        gain_pct = _safe_float(alert.get('gain_loss_pct'))
        allocation = _safe_float(alert.get('allocation_pct'))
        
        # Calculate dollar gain
        position_value = current_value * (allocation / 100) if allocation > 0 else 0
        dollar_gain = position_value * (gain_pct / 100) if gain_pct != 0 else 0
        
        alerts_html += f'''
                                <tr>
                                    <td style="padding: 12px 0;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background: linear-gradient(90deg, rgba(0,212,170,0.15) 0%, #1a1a24 100%); border-left: 4px solid #00d4aa; border-radius: 8px;">
                                            <tr>
                                                <td style="padding: 16px;">
                                                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                                        <tr>
                                                            <td width="40" style="vertical-align: top; font-size: 28px;">🎯</td>
                                                            <td style="padding-left: 12px;">
                                                                <span style="display: block; font-weight: 700; font-size: 16px; color: #00d4aa;">{ticker} - TARGET REACHED! 🎉</span>
                                                                <span style="display: block; font-size: 14px; color: #a0a0b0; padding-top: 4px;">{company} hit ${current_price:.2f} (target was ${trigger_price:.2f})</span>
                                                                <span style="display: block; font-size: 14px; color: #00d4aa; padding-top: 4px;">Profit: +{gain_pct:.1f}% (+${dollar_gain:,.0f})</span>
                                                                <span style="display: inline-block; margin-top: 8px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; padding: 6px 12px; border-radius: 4px; color: #00d4aa; background: rgba(0,212,170,0.12); border: 1px solid rgba(0,212,170,0.3);">🎯 Consider taking profits</span>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>'''
    
    alert_count = len(triggered_alerts)
    badge_color = "#ff6b6b" if stop_losses else "#00d4aa"
    badge_bg = "rgba(255,107,107,0.12)" if stop_losses else "rgba(0,212,170,0.12)"
    
    return f'''
                    <!-- URGENT ALERTS Section -->
                    <tr>
                        <td style="padding: 32px; border-bottom: 1px solid rgba(255,255,255,0.08); background: linear-gradient(135deg, rgba(255,107,107,0.08) 0%, rgba(255,217,61,0.05) 100%); border-left: 4px solid {badge_color};">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td>
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td>
                                                    <span style="display: inline-block; width: 32px; height: 32px; background-color: #22222e; border-radius: 8px; text-align: center; line-height: 32px; font-size: 16px; vertical-align: middle;">🚨</span>
                                                    <span style="font-family: Georgia, serif; font-size: 22px; font-weight: 600; color: #f5f5f7; padding-left: 10px; vertical-align: middle;">Urgent Alerts</span>
                                                </td>
                                                <td align="right">
                                                    <span style="font-size: 11px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; color: {badge_color}; background: {badge_bg}; padding: 6px 10px; border-radius: 4px; border: 1px solid {badge_color};">{alert_count} Alert{"s" if alert_count != 1 else ""}</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                {alerts_html}
                                <tr>
                                    <td style="padding-top: 12px;">
                                        <div style="font-size: 13px; color: #6b6b7b; padding: 12px 16px; background: #22222e; border-radius: 8px;">
                                            💡 <strong>What this means:</strong> These positions have hit pre-set price levels. Review and take action to protect your portfolio.
                                        </div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>'''


def _build_performance_attribution_section(current_portfolio: List[Dict], this_month_return: float, current_value: float) -> str:
    """
    Build the Performance Attribution section showing what moved your portfolio.
    Shows contributors and detractors with dollar amounts.
    """
    if not current_portfolio:
        return ""
    
    # Calculate dollar return for portfolio
    portfolio_dollar_change = current_value * (this_month_return / 100) if this_month_return != 0 else 0
    
    # Sort positions by contribution (gain_loss_pct * allocation_pct = weighted contribution)
    positions_with_contrib = []
    for pos in current_portfolio:
        ticker = pos.get('ticker', '')
        gain_pct = _safe_float(pos.get('gain_loss_pct', 0))
        allocation = _safe_float(pos.get('allocation_pct', 0))
        
        # FIXED: Calculate dollar change correctly from original investment
        # Current position value
        current_position_value = current_value * (allocation / 100) if allocation > 0 else 0
        
        if gain_pct != 0 and gain_pct != -100:
            # Work backwards: original * (1 + gain/100) = current
            original_investment = current_position_value / (1 + gain_pct / 100)
            dollar_change = current_position_value - original_investment
        else:
            dollar_change = 0
        
        positions_with_contrib.append({
            'ticker': ticker,
            'gain_pct': gain_pct,
            'dollar_change': dollar_change,
            'allocation': allocation
        })
    
    # Sort by dollar contribution
    positions_with_contrib.sort(key=lambda x: x['dollar_change'], reverse=True)
    
    # Top contributors (positive) and detractors (negative)
    contributors = [p for p in positions_with_contrib if p['dollar_change'] > 0][:3]
    detractors = [p for p in positions_with_contrib if p['dollar_change'] < 0][:3]
    
    # Build contributors HTML
    contributors_html = ""
    for pos in contributors:
        contributors_html += f'''
                                            <tr>
                                                <td style="padding: 8px 0; border-bottom: 1px dashed rgba(255,255,255,0.08);">
                                                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                                        <tr>
                                                            <td><span style="font-family: 'Consolas', monospace; font-weight: 600; font-size: 14px; color: #f5f5f7;">{pos['ticker']}</span></td>
                                                            <td align="right">
                                                                <span style="font-family: 'Consolas', monospace; font-weight: 600; font-size: 14px; color: #00d4aa;">+${pos['dollar_change']:,.0f}</span>
                                                                <span style="font-size: 12px; color: #6b6b7b; padding-left: 6px;">({pos['gain_pct']:+.1f}%)</span>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>'''
    
    if not contributors_html:
        contributors_html = '<tr><td style="padding: 12px 0; font-size: 13px; color: #6b6b7b; font-style: italic;">No positive contributors this period</td></tr>'
    
    # Build detractors HTML
    detractors_html = ""
    for pos in detractors:
        detractors_html += f'''
                                            <tr>
                                                <td style="padding: 8px 0; border-bottom: 1px dashed rgba(255,255,255,0.08);">
                                                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                                        <tr>
                                                            <td><span style="font-family: 'Consolas', monospace; font-weight: 600; font-size: 14px; color: #f5f5f7;">{pos['ticker']}</span></td>
                                                            <td align="right">
                                                                <span style="font-family: 'Consolas', monospace; font-weight: 600; font-size: 14px; color: #ff6b6b;">-${abs(pos['dollar_change']):,.0f}</span>
                                                                <span style="font-size: 12px; color: #6b6b7b; padding-left: 6px;">({pos['gain_pct']:+.1f}%)</span>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>'''
    
    if not detractors_html:
        detractors_html = '<tr><td style="padding: 12px 0; font-size: 13px; color: #6b6b7b; font-style: italic;">No detractors this period 🎉</td></tr>'
    
    # Determine overall color
    return_color = "#00d4aa" if this_month_return >= 0 else "#ff6b6b"
    dollar_sign = "+" if portfolio_dollar_change >= 0 else "-"
    
    return f'''
                    <!-- Performance Attribution Section -->
                    <tr>
                        <td style="padding: 32px; border-bottom: 1px solid rgba(255,255,255,0.08);">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td>
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td>
                                                    <span style="display: inline-block; width: 32px; height: 32px; background-color: #22222e; border-radius: 8px; text-align: center; line-height: 32px; font-size: 16px; vertical-align: middle;">📊</span>
                                                    <span style="font-family: Georgia, serif; font-size: 22px; font-weight: 600; color: #f5f5f7; padding-left: 10px; vertical-align: middle;">What Moved Your Portfolio</span>
                                                </td>
                                                <td align="right">
                                                    <span style="font-size: 11px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; color: #6b6b7b; background-color: #22222e; padding: 6px 10px; border-radius: 4px;">This Period</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                <!-- Summary Card -->
                                <tr>
                                    <td style="padding-top: 20px;" align="center">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="background: #1a1a24; border: 1px solid {'rgba(0,212,170,0.3)' if this_month_return >= 0 else 'rgba(255,107,107,0.3)'}; border-radius: 12px; padding: 20px 40px;">
                                            <tr>
                                                <td align="center">
                                                    <span style="display: block; font-family: 'Consolas', monospace; font-size: 32px; font-weight: 700; color: {return_color};">{this_month_return:+.1f}%</span>
                                                    <span style="display: block; font-size: 12px; color: #6b6b7b; text-transform: uppercase; letter-spacing: 0.5px; padding-top: 4px;">This Period Return</span>
                                                    <span style="display: block; font-family: 'Consolas', monospace; font-size: 16px; color: {return_color}; padding-top: 8px;">{dollar_sign}${abs(portfolio_dollar_change):,.0f}</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                <!-- Two Column Grid -->
                                <tr>
                                    <td style="padding-top: 20px;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td width="48%" style="vertical-align: top;">
                                                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background: #1a1a24; border: 1px solid rgba(255,255,255,0.08); border-top: 3px solid #00d4aa; border-radius: 10px; padding: 16px;">
                                                        <tr>
                                                            <td style="font-weight: 600; font-size: 14px; color: #00d4aa; padding-bottom: 12px; border-bottom: 1px solid rgba(255,255,255,0.08);">📈 Top Contributors</td>
                                                        </tr>
                                                        {contributors_html}
                                                    </table>
                                                </td>
                                                <td width="4%"></td>
                                                <td width="48%" style="vertical-align: top;">
                                                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background: #1a1a24; border: 1px solid rgba(255,255,255,0.08); border-top: 3px solid #ff6b6b; border-radius: 10px; padding: 16px;">
                                                        <tr>
                                                            <td style="font-weight: 600; font-size: 14px; color: #ff6b6b; padding-bottom: 12px; border-bottom: 1px solid rgba(255,255,255,0.08);">📉 Detractors</td>
                                                        </tr>
                                                        {detractors_html}
                                                    </table>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>'''


def _build_dividend_calendar_section(dividend_calendar: Dict, current_portfolio: List[Dict], current_value: float) -> str:
    """
    Build the Dividend Calendar section showing upcoming ex-dividend dates.
    """
    if not dividend_calendar:
        return ""
    
    # Build portfolio allocation lookup
    allocation_lookup = {pos.get('ticker', ''): _safe_float(pos.get('allocation_pct', 0)) for pos in current_portfolio}
    
    rows_html = ""
    total_expected_income = 0
    
    for ticker, div_data in dividend_calendar.items():
        ex_date = div_data.get('ex_dividend_display', 'TBD')
        days_until = div_data.get('days_until', '?')
        div_per_share = _safe_float(div_data.get('dividend_per_share', 0))
        yield_pct = _safe_float(div_data.get('dividend_yield_pct', 0))
        
        # Get allocation and calculate expected income
        allocation = allocation_lookup.get(ticker, 0)
        position_value = current_value * (allocation / 100) if allocation > 0 else 0
        
        # Estimate shares (rough - need price for exact)
        current_price = div_data.get('current_price', 100)  # Fallback
        shares = int(position_value / current_price) if current_price > 0 else 0
        expected_income = shares * div_per_share
        total_expected_income += expected_income
        
        # Urgency styling
        is_urgent = isinstance(days_until, int) and days_until <= 3
        row_bg = "rgba(255,217,61,0.08)" if is_urgent else "transparent"
        urgent_badge = '<span style="font-size: 10px; font-weight: 600; color: #ffd93d; background: rgba(255,217,61,0.12); padding: 2px 6px; border-radius: 3px; margin-left: 8px;">SOON</span>' if is_urgent else ""
        
        rows_html += f'''
                                <tr style="background: {row_bg};">
                                    <td style="padding: 12px 8px; border-bottom: 1px solid rgba(255,255,255,0.08);">
                                        <span style="font-family: 'Consolas', monospace; font-weight: 600; color: #f5f5f7;">{ticker}</span>
                                        {urgent_badge}
                                    </td>
                                    <td style="padding: 12px 8px; border-bottom: 1px solid rgba(255,255,255,0.08); color: #a0a0b0;">{ex_date}</td>
                                    <td style="padding: 12px 8px; border-bottom: 1px solid rgba(255,255,255,0.08); color: #6b6b7b;">{days_until} days</td>
                                    <td style="padding: 12px 8px; border-bottom: 1px solid rgba(255,255,255,0.08); font-family: 'Consolas', monospace; color: #a0a0b0;">${div_per_share:.2f}</td>
                                    <td style="padding: 12px 8px; border-bottom: 1px solid rgba(255,255,255,0.08); font-family: 'Consolas', monospace; font-weight: 600; color: #00d4aa;">${expected_income:.0f}</td>
                                </tr>'''
    
    return f'''
                    <!-- Dividend Calendar Section -->
                    <tr>
                        <td style="padding: 32px; border-bottom: 1px solid rgba(255,255,255,0.08);">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td>
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td>
                                                    <span style="display: inline-block; width: 32px; height: 32px; background-color: #22222e; border-radius: 8px; text-align: center; line-height: 32px; font-size: 16px; vertical-align: middle;">📅</span>
                                                    <span style="font-family: Georgia, serif; font-size: 22px; font-weight: 600; color: #f5f5f7; padding-left: 10px; vertical-align: middle;">Dividend Calendar</span>
                                                </td>
                                                <td align="right">
                                                    <span style="font-size: 11px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; color: #6b6b7b; background-color: #22222e; padding: 6px 10px; border-radius: 4px;">Next 14 Days</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding-top: 20px;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="font-size: 14px;">
                                            <tr style="background: #1a1a24;">
                                                <th style="text-align: left; padding: 12px 8px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #6b6b7b; border-bottom: 1px solid rgba(255,255,255,0.08);">Stock</th>
                                                <th style="text-align: left; padding: 12px 8px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #6b6b7b; border-bottom: 1px solid rgba(255,255,255,0.08);">Ex-Date</th>
                                                <th style="text-align: left; padding: 12px 8px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #6b6b7b; border-bottom: 1px solid rgba(255,255,255,0.08);">Days</th>
                                                <th style="text-align: left; padding: 12px 8px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #6b6b7b; border-bottom: 1px solid rgba(255,255,255,0.08);">Per Share</th>
                                                <th style="text-align: left; padding: 12px 8px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #6b6b7b; border-bottom: 1px solid rgba(255,255,255,0.08);">Expected</th>
                                            </tr>
                                            {rows_html}
                                        </table>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding-top: 16px;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background: #22222e; border-radius: 8px; padding: 12px 16px;">
                                            <tr>
                                                <td>
                                                    <span style="font-size: 13px; color: #6b6b7b;">Total Expected Dividend Income:</span>
                                                </td>
                                                <td align="right">
                                                    <span style="font-family: 'Consolas', monospace; font-size: 18px; font-weight: 700; color: #00d4aa;">${total_expected_income:,.0f}</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding-top: 12px;">
                                        <span style="font-size: 12px; color: #6b6b7b; line-height: 1.5;">💡 <strong>Tip:</strong> You must own shares BEFORE the ex-dividend date to receive the dividend. Consider holding these positions until after the ex-date.</span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>'''


def _build_market_pulse(market_overview: Dict[str, Any], email_context: Dict[str, Any]) -> str:
    """Build the market pulse strip with major indices."""
    indices = market_overview.get("indices", {})
    
    # Try to get from email_context if not in market_overview
    if not indices and email_context:
        market_data = email_context.get("market_data", {})
        indices = market_data.get("indexes", {})
    
    # Get VIX data
    vix_data = email_context.get("vix_data", {})
    vix_value = vix_data.get("current", "N/A")
    vix_change = vix_data.get("change_pct", 0)
    
    # Default indices if not provided
    default_indices = [
        ("S&P 500", 5847.21, 1.24),
        ("NASDAQ", 18392.44, 1.87),
        ("DOW", 43284.12, -0.32),
    ]
    
    pulse_cells = ""
    
    # Process provided indices or use defaults
    if indices:
        for name, data in list(indices.items())[:3]:
            if isinstance(data, dict):
                value = data.get("value", data.get("price", data.get("current", "N/A")))
                change_pct = data.get("change_pct", data.get("change_percent", 0))
            else:
                value = data
                change_pct = 0
            
            pulse_cells += _create_pulse_item(name, value, change_pct)
    else:
        for name, value, change_pct in default_indices:
            pulse_cells += _create_pulse_item(name, value, change_pct)
    
    # Add VIX
    pulse_cells += _create_pulse_item("VIX", vix_value, vix_change if vix_change else 0)
    
    return f'''
                    <!-- Market Pulse Strip -->
                    <tr>
                        <td style="background-color: #0a0a0f; border-bottom: 1px solid rgba(255,255,255,0.08); padding: 16px 32px;">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    {pulse_cells}
                                </tr>
                            </table>
                        </td>
                    </tr>'''


def _create_pulse_item(name: str, value: Any, change_pct: float) -> str:
    """Create a single pulse item cell."""
    # Format value
    if isinstance(value, (int, float)):
        if value > 100:
            value_str = f"{value:,.2f}"
        else:
            value_str = f"{value:.2f}"
    else:
        value_str = str(value)
    
    # Determine color and direction
    if isinstance(change_pct, (int, float)):
        is_positive = change_pct >= 0
        color = "#00d4aa" if is_positive else "#ff6b6b"
        bg_color = "rgba(0,212,170,0.12)" if is_positive else "rgba(255,107,107,0.12)"
        sign = "+" if is_positive else ""
        change_str = f"{sign}{change_pct:.2f}%"
    else:
        color = "#a0a0b0"
        bg_color = "rgba(255,255,255,0.08)"
        change_str = str(change_pct)
    
    return f'''
                                    <td width="25%" style="padding: 0 8px;">
                                        <span style="display: block; font-size: 12px; color: #6b6b7b; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;">{name}</span>
                                        <span style="display: block; font-family: 'Consolas', monospace; font-size: 14px; font-weight: 500; color: #f5f5f7; padding-top: 4px;">{value_str}</span>
                                        <span style="display: inline-block; font-family: 'Consolas', monospace; font-size: 12px; color: {color}; background: {bg_color}; padding: 2px 6px; border-radius: 3px; margin-top: 4px;">{change_str}</span>
                                    </td>'''


def _build_action_plan(recommendations: List[Dict], allocation: Dict, analysis_result: Dict) -> str:
    """Build the This Week's Action Plan section with allocation bar."""
    
    # Calculate allocations from recommendations
    buy_stocks = []
    hold_stocks = []
    sell_stocks = []
    trim_stocks = []  # New: separate list for TRIM actions
    cash_pct = allocation.get("cash_pct", allocation.get("cash", {}).get("allocation_pct", 15))
    
    for rec in recommendations:
        # Check multiple possible field names for action (status is used in new_recommendations)
        action = rec.get("action", rec.get("recommendation", rec.get("status", rec.get("type", "BUY")))).upper()
        ticker = rec.get("symbol", rec.get("ticker", ""))
        company = rec.get("company", rec.get("company_name", ticker))
        alloc = rec.get("allocation_pct", rec.get("allocation", 10))
        new_alloc = rec.get("new_allocation_pct", alloc)
        
        if "BUY" in action or "STRONG" in action or "ADD" in action:
            buy_stocks.append({"ticker": ticker, "company": company, "allocation": alloc})
        elif "SELL" in action:
            sell_stocks.append({"ticker": ticker, "company": company, "allocation": alloc})
        elif "TRIM" in action:
            # Calculate trim percentage
            old_alloc = rec.get("current_allocation_pct", alloc)
            trim_pct = old_alloc - new_alloc if old_alloc > new_alloc else 0
            trim_stocks.append({
                "ticker": ticker,
                "company": company,
                "old_allocation": old_alloc,
                "new_allocation": new_alloc,
                "trim_pct": trim_pct
            })
        else:
            hold_stocks.append({"ticker": ticker, "company": company, "allocation": alloc})
    
    # Also check portfolio_review for holds, trims, and sells
    portfolio_review = analysis_result.get("portfolio_review", [])
    for holding in portfolio_review:
        action = holding.get("recommendation", holding.get("action", "HOLD")).upper()
        ticker = holding.get("ticker", holding.get("symbol", ""))
        
        if "TRIM" in action:
            old_alloc = holding.get("allocation_pct", holding.get("current_allocation_pct", 15))
            new_alloc = holding.get("new_allocation_pct", old_alloc)
            if not any(t["ticker"] == ticker for t in trim_stocks):
                trim_stocks.append({
                    "ticker": ticker,
                    "company": holding.get("company_name", ticker),
                    "old_allocation": old_alloc,
                    "new_allocation": new_alloc,
                    "trim_pct": old_alloc - new_alloc
                })
        elif "SELL" in action:
            # Add sells from portfolio_review
            if not any(s["ticker"] == ticker for s in sell_stocks):
                sell_stocks.append({
                    "ticker": ticker,
                    "company": holding.get("company_name", ticker),
                    "allocation": holding.get("allocation_pct", 15)
                })
        elif "HOLD" in action:
            # Don't add to hold if already in buy_stocks (prevents duplicates)
            if not any(h["ticker"] == ticker for h in hold_stocks) and not any(b["ticker"] == ticker for b in buy_stocks):
                hold_stocks.append({
                    "ticker": ticker,
                    "company": holding.get("company_name", ticker),
                    "allocation": holding.get("allocation_pct", 15)
                })
    
    # Calculate percentages - use 0 as default when no stocks in category
    buy_total = sum(s["allocation"] for s in buy_stocks) if buy_stocks else 0
    hold_total = sum(s["allocation"] for s in hold_stocks) if hold_stocks else 0
    sell_total = sum(s["allocation"] for s in sell_stocks) if sell_stocks else 0
    
    # Normalize if needed
    total = buy_total + hold_total + sell_total + cash_pct
    if total > 0 and total != 100:
        factor = 100 / total
        buy_total = int(buy_total * factor)
        hold_total = int(hold_total * factor)
        sell_total = int(sell_total * factor)
        cash_pct = 100 - buy_total - hold_total - sell_total
    
    # Build allocation bar - only show sections with > 0%
    bar_cells = ""
    if buy_total > 0:
        bar_cells += f'''<td width="{buy_total}%" style="background: linear-gradient(135deg, #00d4aa 0%, #00b894 100%); padding: 14px 0; text-align: center;">
                                                            <span style="display: block; font-size: 11px; font-weight: 600; text-transform: uppercase; color: rgba(0,0,0,0.7);">Buy</span>
                                                            <span style="display: block; font-size: 14px; font-weight: 700; color: rgba(0,0,0,0.85);">{buy_total}%</span>
                                                        </td>'''
    if hold_total > 0:
        bar_cells += f'''<td width="{hold_total}%" style="background: linear-gradient(135deg, #ffd93d 0%, #f4c430 100%); padding: 14px 0; text-align: center;">
                                                            <span style="display: block; font-size: 11px; font-weight: 600; text-transform: uppercase; color: rgba(0,0,0,0.7);">Hold</span>
                                                            <span style="display: block; font-size: 14px; font-weight: 700; color: rgba(0,0,0,0.85);">{hold_total}%</span>
                                                        </td>'''
    if cash_pct > 0:
        bar_cells += f'''<td width="{cash_pct}%" style="background: linear-gradient(135deg, #6b6b7b 0%, #505060 100%); padding: 14px 0; text-align: center;">
                                                            <span style="display: block; font-size: 11px; font-weight: 600; text-transform: uppercase; color: rgba(255,255,255,0.7);">Cash</span>
                                                            <span style="display: block; font-size: 14px; font-weight: 700; color: rgba(255,255,255,0.85);">{cash_pct}%</span>
                                                        </td>'''
    if sell_total > 0:
        bar_cells += f'''<td width="{sell_total}%" style="background: linear-gradient(135deg, #ff6b6b 0%, #ee5a5a 100%); padding: 14px 0; text-align: center;">
                                                            <span style="display: block; font-size: 11px; font-weight: 600; text-transform: uppercase; color: rgba(0,0,0,0.7);">Sell</span>
                                                            <span style="display: block; font-size: 14px; font-weight: 700; color: rgba(0,0,0,0.85);">{sell_total}%</span>
                                                        </td>'''
    
    allocation_bar = f'''
                                        <tr>
                                            <td style="padding: 0;">
                                                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="border-radius: 10px; overflow: hidden;">
                                                    <tr>
                                                        {bar_cells}
                                                    </tr>
                                                </table>
                                            </td>
                                        </tr>'''
    
    # Build action cards
    action_cards = ""
    
    # BUY card
    if buy_stocks:
        buy_rows = ""
        for stock in buy_stocks:
            buy_rows += f'''
                                                    <tr>
                                                        <td style="padding: 12px 16px; background-color: #22222e; border-radius: 8px; margin-bottom: 8px;">
                                                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                                                <tr>
                                                                    <td width="40%" style="font-weight: 600; font-size: 14px; color: #f5f5f7;">{stock["ticker"]} ({stock["company"][:15]})</td>
                                                                    <td width="30%" style="font-family: 'Consolas', monospace; font-size: 13px; color: #d4af37;">{stock["allocation"]}% of your money</td>
                                                                    <td width="30%" align="right" style="font-size: 12px; color: #6b6b7b;">= ${stock["allocation"] * 10} of every $1,000</td>
                                                                </tr>
                                                            </table>
                                                        </td>
                                                    </tr>
                                                    <tr><td style="height: 8px;"></td></tr>'''
        
        action_cards += f'''
                                        <tr><td style="height: 16px;"></td></tr>
                                        <tr>
                                            <td style="background-color: #1a1a24; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 20px; border-left: 4px solid #00d4aa;">
                                                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                                    <tr>
                                                        <td style="padding-bottom: 16px;">
                                                            <span style="font-size: 20px; vertical-align: middle;">🟢</span>
                                                            <span style="font-weight: 700; font-size: 16px; color: #f5f5f7; padding-left: 10px;">BUY — Put {buy_total}% Here</span>
                                                        </td>
                                                    </tr>
                                                    {buy_rows}
                                                </table>
                                            </td>
                                        </tr>'''
    
    # HOLD card
    if hold_stocks:
        hold_rows = ""
        for stock in hold_stocks:
            hold_rows += f'''
                                                    <tr>
                                                        <td style="padding: 12px 16px; background-color: #22222e; border-radius: 8px; margin-bottom: 8px;">
                                                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                                                <tr>
                                                                    <td width="40%" style="font-weight: 600; font-size: 14px; color: #f5f5f7;">{stock["ticker"]} ({stock["company"][:15]})</td>
                                                                    <td width="30%" style="font-family: 'Consolas', monospace; font-size: 13px; color: #d4af37;">{stock["allocation"]}% of your money</td>
                                                                    <td width="30%" align="right" style="font-size: 12px; color: #6b6b7b;">Don't buy more, keep what you have</td>
                                                                </tr>
                                                            </table>
                                                        </td>
                                                    </tr>
                                                    <tr><td style="height: 8px;"></td></tr>'''
        
        action_cards += f'''
                                        <tr><td style="height: 16px;"></td></tr>
                                        <tr>
                                            <td style="background-color: #1a1a24; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 20px; border-left: 4px solid #ffd93d;">
                                                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                                    <tr>
                                                        <td style="padding-bottom: 16px;">
                                                            <span style="font-size: 20px; vertical-align: middle;">🟡</span>
                                                            <span style="font-weight: 700; font-size: 16px; color: #f5f5f7; padding-left: 10px;">HOLD — Keep {hold_total}% In These</span>
                                                        </td>
                                                    </tr>
                                                    {hold_rows}
                                                </table>
                                            </td>
                                        </tr>'''
    
    # TRIM card (new: shows specific trim percentages)
    if trim_stocks:
        trim_rows = ""
        total_trim_freed = 0
        for stock in trim_stocks:
            trim_pct = stock.get("trim_pct", 0)
            total_trim_freed += trim_pct
            trim_rows += f'''
                                                    <tr>
                                                        <td style="padding: 12px 16px; background-color: #22222e; border-radius: 8px; margin-bottom: 8px;">
                                                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                                                <tr>
                                                                    <td width="40%" style="font-weight: 600; font-size: 14px; color: #f5f5f7;">{stock["ticker"]} ({stock["company"][:15]})</td>
                                                                    <td width="30%" style="font-family: 'Consolas', monospace; font-size: 13px; color: #ff9f43;">Sell {trim_pct:.0f}% of position</td>
                                                                    <td width="30%" align="right" style="font-size: 12px; color: #6b6b7b;">{stock["old_allocation"]:.0f}% → {stock["new_allocation"]:.0f}%</td>
                                                                </tr>
                                                            </table>
                                                        </td>
                                                    </tr>
                                                    <tr><td style="height: 8px;"></td></tr>'''
        
        action_cards += f'''
                                        <tr><td style="height: 16px;"></td></tr>
                                        <tr>
                                            <td style="background-color: #1a1a24; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 20px; border-left: 4px solid #ff9f43;">
                                                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                                    <tr>
                                                        <td style="padding-bottom: 16px;">
                                                            <span style="font-size: 20px; vertical-align: middle;">✂️</span>
                                                            <span style="font-weight: 700; font-size: 16px; color: #f5f5f7; padding-left: 10px;">TRIM — Reduce These Positions (Take {total_trim_freed:.0f}% profits)</span>
                                                        </td>
                                                    </tr>
                                                    <tr>
                                                        <td style="padding: 8px 16px; background-color: rgba(255,159,67,0.1); border-radius: 8px; margin-bottom: 12px;">
                                                            <span style="font-size: 13px; color: #ff9f43; line-height: 1.5;">💡 Trimming means selling a portion to lock in profits while keeping exposure. The freed cash goes to your cash reserve.</span>
                                                        </td>
                                                    </tr>
                                                    <tr><td style="height: 8px;"></td></tr>
                                                    {trim_rows}
                                                </table>
                                            </td>
                                        </tr>'''
    
    # CASH card
    action_cards += f'''
                                        <tr><td style="height: 16px;"></td></tr>
                                        <tr>
                                            <td style="background-color: #1a1a24; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 20px; border-left: 4px solid #6b6b7b;">
                                                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                                    <tr>
                                                        <td style="padding-bottom: 16px;">
                                                            <span style="font-size: 20px; vertical-align: middle;">💵</span>
                                                            <span style="font-weight: 700; font-size: 16px; color: #f5f5f7; padding-left: 10px;">CASH — Keep {cash_pct}% Safe</span>
                                                        </td>
                                                    </tr>
                                                    <tr>
                                                        <td style="padding: 12px 16px; background-color: #22222e; border-radius: 8px;">
                                                            <span style="font-size: 14px; color: #a0a0b0; line-height: 1.6;">Keep this in your bank or a high-yield savings account. This is your safety net and lets you buy quickly when opportunities appear.</span>
                                                        </td>
                                                    </tr>
                                                </table>
                                            </td>
                                        </tr>'''
    
    # SELL card
    if sell_stocks:
        sell_rows = ""
        for stock in sell_stocks:
            sell_rows += f'''
                                                    <tr>
                                                        <td style="padding: 12px 16px; background-color: #22222e; border-radius: 8px; margin-bottom: 8px;">
                                                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                                                <tr>
                                                                    <td width="40%" style="font-weight: 600; font-size: 14px; color: #f5f5f7;">{stock["ticker"]} ({stock["company"][:15]})</td>
                                                                    <td width="60%" align="right" style="font-family: 'Consolas', monospace; font-size: 13px; color: #ff6b6b;">Sell — exit position</td>
                                                                </tr>
                                                            </table>
                                                        </td>
                                                    </tr>
                                                    <tr><td style="height: 8px;"></td></tr>'''
        
        action_cards += f'''
                                        <tr><td style="height: 16px;"></td></tr>
                                        <tr>
                                            <td style="background-color: #1a1a24; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 20px; border-left: 4px solid #ff6b6b;">
                                                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                                    <tr>
                                                        <td style="padding-bottom: 16px;">
                                                            <span style="font-size: 20px; vertical-align: middle;">🔴</span>
                                                            <span style="font-weight: 700; font-size: 16px; color: #f5f5f7; padding-left: 10px;">SELL — Remove {sell_total}% From These</span>
                                                        </td>
                                                    </tr>
                                                    {sell_rows}
                                                </table>
                                            </td>
                                        </tr>'''
    
    return f'''
                    <!-- This Week's Action Plan -->
                    <tr>
                        <td style="padding: 32px; border-bottom: 1px solid rgba(255,255,255,0.08); background-color: #0a0a0f;">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td>
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td>
                                                    <span style="display: inline-block; width: 32px; height: 32px; background-color: #22222e; border-radius: 8px; text-align: center; line-height: 32px; font-size: 16px; vertical-align: middle;">🎯</span>
                                                    <span style="font-family: Georgia, serif; font-size: 22px; font-weight: 600; color: #f5f5f7; padding-left: 10px; vertical-align: middle;">This Week's Action Plan</span>
                                                </td>
                                                <td align="right">
                                                    <span style="font-size: 11px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; color: #6b6b7b; background-color: #22222e; padding: 6px 10px; border-radius: 4px;">What To Do With Your Money</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding-top: 20px; padding-bottom: 24px;">
                                        <span style="font-size: 16px; color: #a0a0b0; line-height: 1.6;">If you have <strong style="color: #f5f5f7;">$1,000 to invest</strong> (or any amount), here's exactly how we recommend splitting it up this week:</span>
                                    </td>
                                </tr>
                                {allocation_bar}
                                {action_cards}
                            </table>
                        </td>
                    </tr>'''


def _build_stock_picks(recommendations: List[Dict], analysis_result: Dict, current_value: float = 100000) -> str:
    """Build the This Week's Picks section with detailed stock cards."""
    
    # Combine recommendations from different sources
    all_recs = list(recommendations)
    new_recs = analysis_result.get("new_recommendations", [])
    for rec in new_recs:
        ticker = rec.get("ticker", rec.get("symbol", ""))
        if not any(r.get("ticker", r.get("symbol", "")) == ticker for r in all_recs):
            all_recs.append(rec)
    
    if not all_recs:
        return ""
    
    stock_cards = ""
    for rec in all_recs[:5]:  # Limit to 5 picks
        stock_cards += _build_stock_card(rec, current_value)
    
    return f'''
                    <!-- This Week's Picks -->
                    <tr>
                        <td style="padding: 32px; border-bottom: 1px solid rgba(255,255,255,0.08);">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td>
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td>
                                                    <span style="display: inline-block; width: 32px; height: 32px; background-color: #22222e; border-radius: 8px; text-align: center; line-height: 32px; font-size: 16px; vertical-align: middle;">📊</span>
                                                    <span style="font-family: Georgia, serif; font-size: 22px; font-weight: 600; color: #f5f5f7; padding-left: 10px; vertical-align: middle;">This Week's Picks</span>
                                                </td>
                                                <td align="right">
                                                    <span style="font-size: 11px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; color: #6b6b7b; background-color: #22222e; padding: 6px 10px; border-radius: 4px;">{len(all_recs)} Calls</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                {stock_cards}
                            </table>
                        </td>
                    </tr>'''


def _build_stock_card(rec: Dict, current_value: float = 100000) -> str:
    """Build a single stock card with position sizing guidance."""
    ticker = rec.get("ticker", rec.get("symbol", "N/A"))
    company = rec.get("company_name", rec.get("company", rec.get("name", ticker)))
    # Check multiple possible field names - status is used in new_recommendations, default to BUY
    action = rec.get("action", rec.get("recommendation", rec.get("status", rec.get("type", "BUY")))).upper()
    price = rec.get("current_market_price", rec.get("current_price", rec.get("price", 0)))
    target = rec.get("price_target", rec.get("target_price", rec.get("target", None)))
    stop_loss = rec.get("stop_loss", None)
    thesis = rec.get("thesis", rec.get("reason", rec.get("rationale", rec.get("summary", ""))))
    allocation = rec.get("allocation_pct", rec.get("allocation", 10))
    pe_ratio = rec.get("pe_ratio", rec.get("pe", "N/A"))
    market_cap = rec.get("market_cap", rec.get("marketCap", "N/A"))
    ytd_return = rec.get("ytd_return", rec.get("ytd", rec.get("change_pct", 0)))
    
    # Badge styling based on action
    if "BUY" in action or "STRONG" in action:
        badge_color = "#00d4aa"
        badge_bg = "rgba(0,212,170,0.12)"
        badge_border = "rgba(0,212,170,0.3)"
        badge_text = "Strong Buy" if "STRONG" in action else "Buy"
        tag_text = f"Recommended allocation: <strong>{allocation}% of your investment money</strong>"
    elif "SELL" in action:
        badge_color = "#ff6b6b"
        badge_bg = "rgba(255,107,107,0.12)"
        badge_border = "rgba(255,107,107,0.3)"
        badge_text = "Sell"
        tag_text = "Action: <strong>Sell — exit this stock completely</strong>"
    else:
        badge_color = "#ffd93d"
        badge_bg = "rgba(255,217,61,0.12)"
        badge_border = "rgba(255,217,61,0.3)"
        badge_text = "Hold"
        tag_text = f"If you already own it: <strong>Keep your {allocation}% position, don't add more</strong>"
    
    # Format price
    price_str = f"${price:,.2f}" if isinstance(price, (int, float)) and price > 0 else "N/A"
    
    # Format target
    if target and isinstance(target, (int, float)):
        target_str = f"${target:,.2f}"
        if price and isinstance(price, (int, float)) and price > 0:
            potential = ((target - price) / price) * 100
            potential_str = f"+{potential:.1f}%" if potential >= 0 else f"{potential:.1f}%"
            potential_color = "#00d4aa" if potential >= 0 else "#ff6b6b"
        else:
            potential_str = "N/A"
            potential_color = "#a0a0b0"
    else:
        target_str = "N/A"
        potential_str = "N/A"
        potential_color = "#a0a0b0"
    
    # Format stop loss
    stop_loss_str = f"${stop_loss:,.2f}" if stop_loss and isinstance(stop_loss, (int, float)) else None
    
    # Position sizing calculations
    position_sizing_box = ""
    if "BUY" in action and price and isinstance(price, (int, float)) and price > 0:
        investment_amount = current_value * (allocation / 100)
        shares_to_buy = int(investment_amount / price)
        actual_investment = shares_to_buy * price
        
        # Calculate potential profit if target hit
        if target and isinstance(target, (int, float)) and target > 0:
            profit_if_target = (target - price) * shares_to_buy
            profit_str = f"${profit_if_target:,.0f}"
        else:
            profit_str = "N/A"
        
        # Calculate max loss at stop-loss
        if stop_loss and isinstance(stop_loss, (int, float)) and stop_loss > 0:
            max_loss = (price - stop_loss) * shares_to_buy
            loss_str = f"${max_loss:,.0f}"
        else:
            loss_str = "N/A"
        
        position_sizing_box = f'''
                                            <!-- Position Sizing Guidance -->
                                            <tr>
                                                <td style="padding-top: 16px;">
                                                    <div style="background-color: rgba(212,175,55,0.08); border: 1px solid rgba(212,175,55,0.25); border-radius: 8px; padding: 16px;">
                                                        <span style="display: block; font-size: 13px; font-weight: 600; color: #d4af37; margin-bottom: 12px;">🎯 Position Sizing (Based on ${current_value:,.0f} Portfolio)</span>
                                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                                            <tr>
                                                                <td width="25%">
                                                                    <span style="display: block; font-size: 11px; color: #6b6b7b; text-transform: uppercase;">Invest</span>
                                                                    <span style="display: block; font-family: 'Consolas', monospace; font-size: 14px; font-weight: 600; color: #f5f5f7; padding-top: 2px;">${actual_investment:,.0f}</span>
                                                                </td>
                                                                <td width="25%">
                                                                    <span style="display: block; font-size: 11px; color: #6b6b7b; text-transform: uppercase;">Buy Shares</span>
                                                                    <span style="display: block; font-family: 'Consolas', monospace; font-size: 14px; font-weight: 600; color: #f5f5f7; padding-top: 2px;">{shares_to_buy:,}</span>
                                                                </td>
                                                                <td width="25%">
                                                                    <span style="display: block; font-size: 11px; color: #6b6b7b; text-transform: uppercase;">If Target Hit</span>
                                                                    <span style="display: block; font-family: 'Consolas', monospace; font-size: 14px; font-weight: 600; color: #00d4aa; padding-top: 2px;">+{profit_str}</span>
                                                                </td>
                                                                <td width="25%">
                                                                    <span style="display: block; font-size: 11px; color: #6b6b7b; text-transform: uppercase;">Max Loss</span>
                                                                    <span style="display: block; font-family: 'Consolas', monospace; font-size: 14px; font-weight: 600; color: #ff6b6b; padding-top: 2px;">-{loss_str}</span>
                                                                </td>
                                                            </tr>
                                                        </table>
                                                    </div>
                                                </td>
                                            </tr>'''
    
    # Format YTD
    if isinstance(ytd_return, (int, float)):
        ytd_color = "#00d4aa" if ytd_return >= 0 else "#ff6b6b"
        ytd_str = f"+{ytd_return:.1f}%" if ytd_return >= 0 else f"{ytd_return:.1f}%"
    else:
        ytd_color = "#a0a0b0"
        ytd_str = str(ytd_return)
    
    # Build target row
    target_row = f'''
                                            <tr>
                                                <td style="padding-top: 16px; border-top: 1px dashed rgba(255,255,255,0.08);">
                                                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                                        <tr>
                                                            <td width="33%">
                                                                <span style="display: block; font-size: 12px; color: #6b6b7b;">We think it will reach:</span>
                                                                <span style="display: block; font-family: 'Consolas', monospace; font-size: 14px; font-weight: 600; color: {potential_color}; padding-top: 2px;">{target_str}</span>
                                                            </td>
                                                            <td width="33%">
                                                                <span style="display: block; font-size: 12px; color: #6b6b7b;">Potential profit:</span>
                                                                <span style="display: block; font-family: 'Consolas', monospace; font-size: 14px; font-weight: 600; color: {potential_color}; padding-top: 2px;">{potential_str}</span>
                                                            </td>'''
    
    if stop_loss_str:
        target_row += f'''
                                                            <td width="33%">
                                                                <span style="display: block; font-size: 12px; color: #6b6b7b;">Stop loss:</span>
                                                                <span style="display: block; font-family: 'Consolas', monospace; font-size: 14px; font-weight: 600; color: #ff6b6b; padding-top: 2px;">{stop_loss_str}</span>
                                                            </td>'''
    
    target_row += '''
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>'''
    
    return f'''
                                <tr><td style="height: 16px;"></td></tr>
                                <tr>
                                    <td style="background-color: #1a1a24; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 20px;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <!-- Stock Header -->
                                            <tr>
                                                <td style="padding-bottom: 16px;">
                                                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                                        <tr>
                                                            <td width="48" style="vertical-align: top;">
                                                                <div style="width: 48px; height: 48px; background-color: #22222e; border-radius: 10px; border: 1px solid rgba(255,255,255,0.08); text-align: center; line-height: 48px; font-weight: 700; font-size: 14px; color: #d4af37;">{ticker[:4]}</div>
                                                            </td>
                                                            <td style="padding-left: 14px; vertical-align: top;">
                                                                <span style="display: block; font-weight: 600; font-size: 16px; color: #f5f5f7;">{company}</span>
                                                                <span style="display: block; font-family: 'Consolas', monospace; font-size: 13px; color: #6b6b7b; padding-top: 2px;">{ticker}</span>
                                                            </td>
                                                            <td align="right" style="vertical-align: top;">
                                                                <span style="display: inline-block; font-size: 12px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; padding: 8px 16px; border-radius: 6px; color: {badge_color}; background: {badge_bg}; border: 1px solid {badge_border};">{badge_text}</span>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>
                                            <!-- Metrics -->
                                            <tr>
                                                <td style="padding: 16px 0; border-top: 1px solid rgba(255,255,255,0.08); border-bottom: 1px solid rgba(255,255,255,0.08);">
                                                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                                        <tr>
                                                            <td width="25%" align="center">
                                                                <span style="display: block; font-family: 'Consolas', monospace; font-size: 15px; font-weight: 600; color: #f5f5f7;">{price_str}</span>
                                                                <span style="display: block; font-size: 11px; color: #6b6b7b; text-transform: uppercase; letter-spacing: 0.5px; padding-top: 2px;">Current Price</span>
                                                            </td>
                                                            <td width="25%" align="center">
                                                                <span style="display: block; font-family: 'Consolas', monospace; font-size: 15px; font-weight: 600; color: #f5f5f7;">{pe_ratio}</span>
                                                                <span style="display: block; font-size: 11px; color: #6b6b7b; text-transform: uppercase; letter-spacing: 0.5px; padding-top: 2px;">P/E Ratio</span>
                                                            </td>
                                                            <td width="25%" align="center">
                                                                <span style="display: block; font-family: 'Consolas', monospace; font-size: 15px; font-weight: 600; color: #f5f5f7;">{market_cap}</span>
                                                                <span style="display: block; font-size: 11px; color: #6b6b7b; text-transform: uppercase; letter-spacing: 0.5px; padding-top: 2px;">Market Cap</span>
                                                            </td>
                                                            <td width="25%" align="center">
                                                                <span style="display: block; font-family: 'Consolas', monospace; font-size: 15px; font-weight: 600; color: {ytd_color};">{ytd_str}</span>
                                                                <span style="display: block; font-size: 11px; color: #6b6b7b; text-transform: uppercase; letter-spacing: 0.5px; padding-top: 2px;">YTD Return</span>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>
                                            <!-- Thesis -->
                                            <tr>
                                                <td style="padding-top: 16px;">
                                                    <span style="display: block; font-size: 13px; font-weight: 600; color: #a0a0b0; margin-bottom: 8px;">💡 Why we {"like it" if "BUY" in action else "say " + badge_text.lower()} (in plain English):</span>
                                                    <span style="display: block; font-size: 14px; color: #a0a0b0; line-height: 1.7;">{thesis[:400] if thesis else "Analysis pending."}</span>
                                                </td>
                                            </tr>
                                            {target_row}
                                            {position_sizing_box}
                                            <!-- Allocation Tag -->
                                            <tr>
                                                <td style="padding-top: 16px;">
                                                    <div style="background: {badge_bg}; border: 1px solid {badge_border}; border-radius: 8px; padding: 12px 16px; font-size: 14px; color: {badge_color};">
                                                        📊 {tag_text}
                                                    </div>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>'''


def _build_politicians_section(politicians: List[Dict]) -> str:
    """Build the Politicians' Stock Trades section."""
    if not politicians:
        return ""
    
    trade_rows = ""
    for trade in politicians[:5]:
        name = trade.get("politician", trade.get("name", "Unknown"))
        role = trade.get("role", trade.get("position", "Representative"))
        party = trade.get("party", "")
        symbol = trade.get("symbol", trade.get("ticker", "N/A"))
        action = trade.get("action", trade.get("type", "Unknown")).upper()
        amount = trade.get("amount", trade.get("value", "N/A"))
        date = trade.get("date", trade.get("trade_date", "N/A"))
        
        # Party styling
        if party and party.upper().startswith("D"):
            party_bg = "rgba(100,149,237,0.15)"
            party_color = "#7db3ff"
            party_text = "D"
        elif party and party.upper().startswith("R"):
            party_bg = "rgba(255,107,107,0.15)"
            party_color = "#ff8888"
            party_text = "R"
        else:
            party_bg = "rgba(255,255,255,0.1)"
            party_color = "#a0a0b0"
            party_text = ""
        
        # Action styling
        if "BUY" in action or "PURCHASE" in action:
            action_color = "#00d4aa"
            action_text = "Purchased"
        else:
            action_color = "#ff6b6b"
            action_text = "Sold"
        
        # Format amount
        if isinstance(amount, (int, float)):
            if amount >= 1000000:
                amount_str = f"${amount/1000000:.1f}M"
            elif amount >= 1000:
                amount_str = f"${amount/1000:.0f}K"
            else:
                amount_str = f"${amount:,.0f}"
        else:
            amount_str = str(amount)
        
        party_html = f'<span style="background: {party_bg}; color: {party_color}; padding: 2px 6px; border-radius: 3px; font-weight: 500; margin-left: 6px;">{party_text}</span>' if party_text else ""
        
        trade_rows += f'''
                                <tr><td style="height: 12px;"></td></tr>
                                <tr>
                                    <td style="background-color: #1a1a24; border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 16px 20px;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td width="60%" style="vertical-align: middle;">
                                                    <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                                                        <tr>
                                                            <td width="44" style="vertical-align: middle;">
                                                                <div style="width: 44px; height: 44px; background: linear-gradient(135deg, #3b3b4f 0%, #2a2a3a 100%); border-radius: 50%; border: 2px solid rgba(255,255,255,0.08); text-align: center; line-height: 44px; font-size: 18px;">👤</div>
                                                            </td>
                                                            <td style="padding-left: 14px; vertical-align: middle;">
                                                                <span style="display: block; font-weight: 600; font-size: 15px; color: #f5f5f7;">{name}</span>
                                                                <span style="display: block; font-size: 12px; color: #6b6b7b; padding-top: 2px;">{role}{party_html}</span>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>
                                                <td width="40%" align="right" style="vertical-align: middle;">
                                                    <span style="display: block; font-size: 11px; font-weight: 600; letter-spacing: 0.5px; text-transform: uppercase; color: {action_color};">{action_text}</span>
                                                    <span style="display: block; font-family: 'Consolas', monospace; font-size: 14px; font-weight: 600; color: #f5f5f7; padding-top: 4px;">{symbol}</span>
                                                    <span style="display: block; font-size: 12px; color: #6b6b7b; padding-top: 2px;">{amount_str} · {date}</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>'''
    
    return f'''
                    <!-- Politicians Trades -->
                    <tr>
                        <td style="padding: 32px; border-bottom: 1px solid rgba(255,255,255,0.08);">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td>
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td>
                                                    <span style="display: inline-block; width: 32px; height: 32px; background-color: #22222e; border-radius: 8px; text-align: center; line-height: 32px; font-size: 16px; vertical-align: middle;">🏛️</span>
                                                    <span style="font-family: Georgia, serif; font-size: 22px; font-weight: 600; color: #f5f5f7; padding-left: 10px; vertical-align: middle;">Politicians' Stock Trades</span>
                                                </td>
                                                <td align="right">
                                                    <span style="font-size: 11px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; color: #6b6b7b; background-color: #22222e; padding: 6px 10px; border-radius: 4px;">Latest Filings</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding-top: 20px;">
                                        <div style="background-color: #1a1a24; border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 16px 20px;">
                                            <span style="display: block; font-weight: 600; font-size: 14px; color: #f5f5f7; margin-bottom: 8px;">🤔 Why does this matter?</span>
                                            <span style="display: block; font-size: 14px; color: #a0a0b0; line-height: 1.6;">Members of Congress are required by law to report their stock trades. Some investors watch these trades because politicians may have access to information before the public does.</span>
                                        </div>
                                    </td>
                                </tr>
                                {trade_rows}
                            </table>
                        </td>
                    </tr>'''


def _build_recommendation_tracker(history: Dict, current_value: float = 100000) -> str:
    """Build the Recommendation Tracker section with dollar amounts."""
    if not history:
        return ""
    
    # Get performance data
    perf = history.get("performance_summary", {})
    win_rate = perf.get("win_rate_pct", perf.get("win_rate", 0))
    avg_return = perf.get("avg_return_pct", perf.get("total_return_pct", 0))
    win_count = perf.get("win_count", 0)
    loss_count = perf.get("loss_count", 0)
    total_trades = win_count + loss_count
    
    # Calculate dollar returns
    total_dollar_gain = current_value * (avg_return / 100) if avg_return else 0
    
    # Get current portfolio for tracking
    current_portfolio = history.get("current_portfolio", [])
    monthly_history = history.get("monthly_history", [])
    
    active_positions = len(current_portfolio)
    
    # Build portfolio rows with dollar amounts
    portfolio_rows = ""
    for holding in current_portfolio[:5]:
        ticker = holding.get("ticker", holding.get("symbol", "N/A"))
        company = holding.get("company_name", holding.get("company", ticker))
        rec_price = holding.get("recommended_price", holding.get("entry_price", 0))
        current_price = holding.get("current_price", holding.get("price", 0))
        gain_loss = holding.get("gain_loss_pct", 0)
        allocation = holding.get("allocation_pct", holding.get("allocation", 10))
        rec_type = holding.get("recommendation", holding.get("action", "Buy"))
        rec_date = holding.get("date", holding.get("entry_date", ""))
        
        # FIXED: Calculate dollar gain/loss correctly from original investment
        # Current position value in the portfolio
        current_position_value = current_value * (allocation / 100)
        
        if isinstance(gain_loss, (int, float)) and isinstance(rec_price, (int, float)) and rec_price > 0 and isinstance(current_price, (int, float)):
            # Work backwards to find original investment
            # original_investment * (1 + gain/100) = current_position_value
            original_investment = current_position_value / (1 + gain_loss / 100) if gain_loss != -100 else current_position_value
            # Dollar gain = current value - original investment
            dollar_gain_loss = current_position_value - original_investment
            dollar_str = f"+${dollar_gain_loss:,.0f}" if dollar_gain_loss >= 0 else f"-${abs(dollar_gain_loss):,.0f}"
        else:
            dollar_str = "N/A"
        
        # Format prices
        rec_price_str = f"${rec_price:,.2f}" if isinstance(rec_price, (int, float)) and rec_price > 0 else "N/A"
        current_price_str = f"${current_price:,.2f}" if isinstance(current_price, (int, float)) and current_price > 0 else "N/A"
        
        # Return styling
        if isinstance(gain_loss, (int, float)):
            return_color = "#00d4aa" if gain_loss >= 0 else "#ff6b6b"
            return_str = f"+{gain_loss:.1f}%" if gain_loss >= 0 else f"{gain_loss:.1f}%"
        else:
            return_color = "#a0a0b0"
            return_str = str(gain_loss)
        
        # Recommendation badge
        rec_upper = rec_type.upper() if isinstance(rec_type, str) else "HOLD"
        if "BUY" in rec_upper:
            rec_bg = "rgba(0,212,170,0.12)"
            rec_color = "#00d4aa"
        elif "SELL" in rec_upper:
            rec_bg = "rgba(255,107,107,0.12)"
            rec_color = "#ff6b6b"
        else:
            rec_bg = "rgba(255,217,61,0.12)"
            rec_color = "#ffd93d"
        
        portfolio_rows += f'''
                                    <tr>
                                        <td style="padding: 16px; border-bottom: 1px solid rgba(255,255,255,0.08);">
                                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                                <tr>
                                                    <td width="30%">
                                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                                                            <tr>
                                                                <td width="36" style="vertical-align: middle;">
                                                                    <div style="width: 36px; height: 36px; background-color: #22222e; border-radius: 8px; text-align: center; line-height: 36px; font-size: 11px; font-weight: 700; color: #d4af37;">{ticker[:4]}</div>
                                                                </td>
                                                                <td style="padding-left: 12px; vertical-align: middle;">
                                                                    <span style="display: block; font-weight: 600; font-size: 14px; color: #f5f5f7;">{company[:18]}</span>
                                                                    <span style="display: block; font-family: 'Consolas', monospace; font-size: 12px; color: #6b6b7b;">{rec_date}</span>
                                                                </td>
                                                            </tr>
                                                        </table>
                                                    </td>
                                                    <td width="12%" align="center">
                                                        <span style="font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.5px; color: {rec_color}; background: {rec_bg};">{rec_upper[:4]}</span>
                                                    </td>
                                                    <td width="13%" align="center">
                                                        <span style="font-family: 'Consolas', monospace; font-size: 13px; color: #f5f5f7;">{rec_price_str}</span>
                                                    </td>
                                                    <td width="13%" align="center">
                                                        <span style="font-family: 'Consolas', monospace; font-size: 13px; color: #f5f5f7;">{current_price_str}</span>
                                                    </td>
                                                    <td width="15%" align="center">
                                                        <span style="font-family: 'Consolas', monospace; font-size: 13px; font-weight: 600; color: {return_color};">{return_str}</span>
                                                    </td>
                                                    <td width="17%" align="right">
                                                        <span style="font-family: 'Consolas', monospace; font-size: 13px; font-weight: 600; color: {return_color};">{dollar_str}</span>
                                                    </td>
                                                </tr>
                                            </table>
                                        </td>
                                    </tr>'''
    
    return f'''
                    <!-- Recommendation Tracker -->
                    <tr>
                        <td style="padding: 32px; border-bottom: 1px solid rgba(255,255,255,0.08);">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td>
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td>
                                                    <span style="display: inline-block; width: 32px; height: 32px; background-color: #22222e; border-radius: 8px; text-align: center; line-height: 32px; font-size: 16px; vertical-align: middle;">📈</span>
                                                    <span style="font-family: Georgia, serif; font-size: 22px; font-weight: 600; color: #f5f5f7; padding-left: 10px; vertical-align: middle;">Recommendation Tracker</span>
                                                </td>
                                                <td align="right">
                                                    <span style="font-size: 11px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; color: #6b6b7b; background-color: #22222e; padding: 6px 10px; border-radius: 4px;">Past 90 Days</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                <!-- Performance Summary -->
                                <tr>
                                    <td style="padding-top: 24px;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td width="33%" style="padding: 0 8px 0 0;">
                                                    <div style="background-color: #1a1a24; border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 20px; text-align: center;">
                                                        <span style="display: block; font-family: Georgia, serif; font-size: 32px; font-weight: 700; color: #00d4aa;">{win_rate:.0f}%</span>
                                                        <span style="display: block; font-size: 12px; color: #6b6b7b; text-transform: uppercase; letter-spacing: 0.5px; padding-top: 4px;">Win Rate ({win_count}/{total_trades})</span>
                                                    </div>
                                                </td>
                                                <td width="33%" style="padding: 0 8px;">
                                                    <div style="background-color: #1a1a24; border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 20px; text-align: center;">
                                                        <span style="display: block; font-family: Georgia, serif; font-size: 32px; font-weight: 700; color: #00d4aa;">+{avg_return:.1f}%</span>
                                                        <span style="display: block; font-size: 12px; color: #6b6b7b; text-transform: uppercase; letter-spacing: 0.5px; padding-top: 4px;">Avg Return</span>
                                                    </div>
                                                </td>
                                                <td width="33%" style="padding: 0 0 0 8px;">
                                                    <div style="background-color: #1a1a24; border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 20px; text-align: center;">
                                                        <span style="display: block; font-family: Georgia, serif; font-size: 32px; font-weight: 700; color: #d4af37;">{active_positions}</span>
                                                        <span style="display: block; font-size: 12px; color: #6b6b7b; text-transform: uppercase; letter-spacing: 0.5px; padding-top: 4px;">Active Positions</span>
                                                    </div>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                <!-- Tracking Table -->
                                <tr>
                                    <td style="padding-top: 24px;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #1a1a24; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; overflow: hidden;">
                                            <tr>
                                                <td style="padding: 12px 16px; background-color: #1a1a24; border-bottom: 1px solid rgba(255,255,255,0.08);">
                                                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                                        <tr>
                                                            <td width="30%" style="font-size: 11px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; color: #6b6b7b;">Stock</td>
                                                            <td width="12%" align="center" style="font-size: 11px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; color: #6b6b7b;">Call</td>
                                                            <td width="13%" align="center" style="font-size: 11px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; color: #6b6b7b;">Entry</td>
                                                            <td width="13%" align="center" style="font-size: 11px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; color: #6b6b7b;">Current</td>
                                                            <td width="15%" align="center" style="font-size: 11px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; color: #6b6b7b;">Return</td>
                                                            <td width="17%" align="right" style="font-size: 11px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; color: #6b6b7b;">$ P/L</td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>
                                            {portfolio_rows}
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>'''


def _build_sp500_comparison(history: Dict) -> str:
    """Build the S&P 500 comparison section."""
    if not history:
        return ""
    
    perf = history.get("performance_summary", {})
    our_return = perf.get("total_return_pct", 0)
    sp500_return = perf.get("sp500_total_return_pct", perf.get("benchmark_return_pct", 0))
    
    if our_return == 0 and sp500_return == 0:
        return ""
    
    outperformance = our_return - sp500_return
    
    return f'''
                    <!-- S&P 500 Comparison -->
                    <tr>
                        <td style="padding: 32px; border-bottom: 1px solid rgba(255,255,255,0.08); background: linear-gradient(180deg, rgba(212,175,55,0.03) 0%, transparent 100%);">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td>
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td>
                                                    <span style="display: inline-block; width: 32px; height: 32px; background-color: #22222e; border-radius: 8px; text-align: center; line-height: 32px; font-size: 16px; vertical-align: middle;">⚡</span>
                                                    <span style="font-family: Georgia, serif; font-size: 22px; font-weight: 600; color: #f5f5f7; padding-left: 10px; vertical-align: middle;">How We Compare to the Market</span>
                                                </td>
                                                <td align="right">
                                                    <span style="font-size: 11px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; color: #6b6b7b; background-color: #22222e; padding: 6px 10px; border-radius: 4px;">Since We Started</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                <!-- Comparison Cards -->
                                <tr>
                                    <td style="padding-top: 24px;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td width="45%" style="background: linear-gradient(135deg, rgba(212,175,55,0.1) 0%, #1a1a24 100%); border: 1px solid rgba(212,175,55,0.4); border-radius: 16px; padding: 28px 20px; text-align: center;">
                                                    <span style="display: block; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; color: #d4af37;">Stock Pulse Picks</span>
                                                    <span style="display: block; font-family: Georgia, serif; font-size: 42px; font-weight: 700; color: #00d4aa; padding-top: 8px;">+{our_return:.1f}%</span>
                                                    <span style="display: block; font-size: 12px; color: #6b6b7b; padding-top: 4px;">Total Return</span>
                                                </td>
                                                <td width="10%" align="center">
                                                    <span style="display: inline-block; font-family: Georgia, serif; font-size: 18px; font-weight: 600; color: #6b6b7b; background-color: #22222e; width: 48px; height: 48px; line-height: 48px; border-radius: 50%; text-align: center;">VS</span>
                                                </td>
                                                <td width="45%" style="background-color: #1a1a24; border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 28px 20px; text-align: center;">
                                                    <span style="display: block; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; color: #6b6b7b;">S&P 500 (Market)</span>
                                                    <span style="display: block; font-family: Georgia, serif; font-size: 42px; font-weight: 700; color: #a0a0b0; padding-top: 8px;">+{sp500_return:.1f}%</span>
                                                    <span style="display: block; font-size: 12px; color: #6b6b7b; padding-top: 4px;">Total Return</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                <!-- Outperformance Banner -->
                                <tr>
                                    <td style="padding-top: 24px;">
                                        <div style="background: linear-gradient(135deg, rgba(0,212,170,0.12) 0%, rgba(212,175,55,0.12) 100%); border: 1px solid rgba(0,212,170,0.3); border-radius: 10px; padding: 16px 24px; text-align: center;">
                                            <span style="font-size: 24px; vertical-align: middle;">🏆</span>
                                            <span style="font-size: 16px; color: #f5f5f7; padding-left: 12px; vertical-align: middle;">We've made <strong style="color: #00d4aa; font-weight: 700;">+{outperformance:.1f}% more</strong> than if you just bought the market average</span>
                                        </div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>'''


def _build_retail_investor_section(retail_analysis: Dict[str, Any], portfolio_value: float) -> str:
    """Build the retail investor insights section."""
    if not retail_analysis:
        return ''
    
    sections_html = []
    
    # Tax-Loss Harvesting
    tlh = retail_analysis.get('tax_loss_harvesting', [])
    high_priority_tlh = [t for t in tlh if t.get('priority') == 'HIGH']
    
    # Correlation Analysis
    corr = retail_analysis.get('correlation_analysis', {})
    div_score = corr.get('diversification_score', 0)
    high_corr_pairs = corr.get('high_correlation_pairs', [])
    
    # Trailing Stops
    trailing = retail_analysis.get('trailing_stops', [])
    needs_update = [t for t in trailing if 'UNPROTECTED' in t.get('status', '') or 'TIGHTEN' in t.get('action', '')]
    
    # Short Interest
    short = retail_analysis.get('short_interest', [])
    squeeze_candidates = [s for s in short if s.get('potential_squeeze')]
    
    # Sector Rotation
    rotation = retail_analysis.get('sector_rotation', {})
    
    # Fee Analysis
    fees = retail_analysis.get('fee_analysis', {})
    
    # Priority Alerts
    alerts = retail_analysis.get('priority_alerts', [])
    
    # Only show section if there's meaningful content
    has_content = (high_priority_tlh or high_corr_pairs or needs_update or 
                   squeeze_candidates or alerts)
    
    if not has_content:
        return ''
    
    # Build Tax-Loss Harvesting subsection
    tlh_html = ''
    if high_priority_tlh:
        tlh_rows = ''
        for t in high_priority_tlh[:4]:
            tax_benefit = _safe_float(t.get('estimated_tax_savings', 0))
            loss_pct = _safe_float(t.get('loss_pct', 0))
            similar = t.get('similar_securities', [])[:2]
            similar_str = ', '.join(similar) if similar else 'SPY'
            
            tlh_rows += f'''
                <tr>
                    <td style="padding: 8px 12px; border-bottom: 1px solid rgba(255,255,255,0.06);">
                        <span style="font-weight: 600; color: #f5f5f7;">{t.get('ticker', 'N/A')}</span>
                    </td>
                    <td style="padding: 8px 12px; border-bottom: 1px solid rgba(255,255,255,0.06); color: #ff6b6b;">
                        {loss_pct:.1f}%
                    </td>
                    <td style="padding: 8px 12px; border-bottom: 1px solid rgba(255,255,255,0.06); color: #4ade80;">
                        ~${tax_benefit:.0f}
                    </td>
                    <td style="padding: 8px 12px; border-bottom: 1px solid rgba(255,255,255,0.06); color: #8b8b8e; font-size: 12px;">
                        {similar_str}
                    </td>
                </tr>'''
        
        tlh_html = f'''
            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 20px;">
                <tr>
                    <td style="padding: 12px 16px; background: rgba(255,107,107,0.1); border-radius: 8px; border-left: 3px solid #ff6b6b;">
                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                            <tr>
                                <td>
                                    <span style="font-size: 14px; font-weight: 600; color: #ff6b6b;">🏦 TAX-LOSS HARVESTING ({len(high_priority_tlh)} High Priority)</span>
                                    <p style="margin: 8px 0 12px 0; font-size: 12px; color: #8b8b8e;">Sell losers to offset capital gains. Estimated savings per $100K portfolio.</p>
                                </td>
                            </tr>
                            <tr>
                                <td>
                                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="font-size: 13px;">
                                        <tr style="background: rgba(0,0,0,0.2);">
                                            <td style="padding: 6px 12px; color: #8b8b8e; font-weight: 500;">Ticker</td>
                                            <td style="padding: 6px 12px; color: #8b8b8e; font-weight: 500;">Loss</td>
                                            <td style="padding: 6px 12px; color: #8b8b8e; font-weight: 500;">Tax Benefit</td>
                                            <td style="padding: 6px 12px; color: #8b8b8e; font-weight: 500;">Alternatives</td>
                                        </tr>
                                        {tlh_rows}
                                    </table>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>'''
    
    # Build Correlation Warning subsection
    corr_html = ''
    if high_corr_pairs:
        pairs_list = ''
        for p in high_corr_pairs[:3]:
            corr_val = _safe_float(p.get('correlation', 0))
            pairs_list += f'''
                <tr>
                    <td style="padding: 6px 12px; border-bottom: 1px solid rgba(255,255,255,0.06);">
                        <span style="color: #f5f5f7;">{p['pair'][0]}</span> / <span style="color: #f5f5f7;">{p['pair'][1]}</span>
                    </td>
                    <td style="padding: 6px 12px; border-bottom: 1px solid rgba(255,255,255,0.06); color: #fbbf24;">
                        {corr_val:.0%}
                    </td>
                </tr>'''
        
        grade = corr.get('diversification_grade', 'N/A')
        corr_html = f'''
            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 20px;">
                <tr>
                    <td style="padding: 12px 16px; background: rgba(251,191,36,0.1); border-radius: 8px; border-left: 3px solid #fbbf24;">
                        <span style="font-size: 14px; font-weight: 600; color: #fbbf24;">📊 CORRELATION WARNING</span>
                        <p style="margin: 8px 0; font-size: 12px; color: #8b8b8e;">Diversification Score: {div_score:.0f}/100 ({grade})</p>
                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="font-size: 13px; margin-top: 8px;">
                            <tr style="background: rgba(0,0,0,0.2);">
                                <td style="padding: 6px 12px; color: #8b8b8e;">Correlated Pairs</td>
                                <td style="padding: 6px 12px; color: #8b8b8e;">Correlation</td>
                            </tr>
                            {pairs_list}
                        </table>
                        <p style="margin: 8px 0 0 0; font-size: 11px; color: #fbbf24;">⚠️ Consider reducing one position in each highly correlated pair</p>
                    </td>
                </tr>
            </table>'''
    
    # Build Trailing Stop Updates subsection
    stop_html = ''
    if needs_update:
        stop_rows = ''
        for t in needs_update[:4]:
            ticker = t.get('ticker', 'N/A')
            gain = _safe_float(t.get('gain_pct', 0))
            old_stop = _safe_float(t.get('original_stop', 0))
            new_stop = _safe_float(t.get('trailing_stop', 0))
            
            stop_rows += f'''
                <tr>
                    <td style="padding: 6px 12px; border-bottom: 1px solid rgba(255,255,255,0.06);">
                        <span style="font-weight: 600; color: #f5f5f7;">{ticker}</span>
                    </td>
                    <td style="padding: 6px 12px; border-bottom: 1px solid rgba(255,255,255,0.06); color: #4ade80;">
                        +{gain:.1f}%
                    </td>
                    <td style="padding: 6px 12px; border-bottom: 1px solid rgba(255,255,255,0.06); color: #8b8b8e;">
                        ${old_stop:.2f}
                    </td>
                    <td style="padding: 6px 12px; border-bottom: 1px solid rgba(255,255,255,0.06); color: #4ade80; font-weight: 600;">
                        ${new_stop:.2f}
                    </td>
                </tr>'''
        
        stop_html = f'''
            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 20px;">
                <tr>
                    <td style="padding: 12px 16px; background: rgba(74,222,128,0.1); border-radius: 8px; border-left: 3px solid #4ade80;">
                        <span style="font-size: 14px; font-weight: 600; color: #4ade80;">🛡️ TRAILING STOP UPDATES</span>
                        <p style="margin: 8px 0 12px 0; font-size: 12px; color: #8b8b8e;">Lock in profits by raising stop-loss levels</p>
                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="font-size: 13px;">
                            <tr style="background: rgba(0,0,0,0.2);">
                                <td style="padding: 6px 12px; color: #8b8b8e;">Ticker</td>
                                <td style="padding: 6px 12px; color: #8b8b8e;">Gain</td>
                                <td style="padding: 6px 12px; color: #8b8b8e;">Current Stop</td>
                                <td style="padding: 6px 12px; color: #8b8b8e;">New Stop</td>
                            </tr>
                            {stop_rows}
                        </table>
                    </td>
                </tr>
            </table>'''
    
    # Build Short Squeeze subsection
    squeeze_html = ''
    if squeeze_candidates:
        squeeze_rows = ''
        for s in squeeze_candidates[:3]:
            ticker = s.get('ticker', 'N/A')
            short_pct = _safe_float(s.get('short_pct_of_float', 0))
            price_chg = _safe_float(s.get('price_change_1mo', 0))
            
            squeeze_rows += f'''
                <tr>
                    <td style="padding: 6px 12px; border-bottom: 1px solid rgba(255,255,255,0.06);">
                        <span style="font-weight: 600; color: #f5f5f7;">{ticker}</span>
                    </td>
                    <td style="padding: 6px 12px; border-bottom: 1px solid rgba(255,255,255,0.06); color: #ff6b6b;">
                        {short_pct:.1f}%
                    </td>
                    <td style="padding: 6px 12px; border-bottom: 1px solid rgba(255,255,255,0.06); color: #4ade80;">
                        +{price_chg:.1f}%
                    </td>
                </tr>'''
        
        squeeze_html = f'''
            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 20px;">
                <tr>
                    <td style="padding: 12px 16px; background: rgba(139,92,246,0.1); border-radius: 8px; border-left: 3px solid #8b5cf6;">
                        <span style="font-size: 14px; font-weight: 600; color: #8b5cf6;">🚀 POTENTIAL SHORT SQUEEZES</span>
                        <p style="margin: 8px 0 12px 0; font-size: 12px; color: #8b8b8e;">High short interest + rising price = shorts covering</p>
                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="font-size: 13px;">
                            <tr style="background: rgba(0,0,0,0.2);">
                                <td style="padding: 6px 12px; color: #8b8b8e;">Ticker</td>
                                <td style="padding: 6px 12px; color: #8b8b8e;">Short %</td>
                                <td style="padding: 6px 12px; color: #8b8b8e;">1mo Change</td>
                            </tr>
                            {squeeze_rows}
                        </table>
                        <p style="margin: 8px 0 0 0; font-size: 11px; color: #ff6b6b;">⚠️ High risk/reward. Use tight stops if trading squeezes.</p>
                    </td>
                </tr>
            </table>'''
    
    # Build Sector Rotation subsection
    rotation_html = ''
    if rotation.get('status') == 'SUCCESS':
        phase = rotation.get('current_phase', 'Unknown')
        rec_sectors = ', '.join(rotation.get('recommended_sectors', [])[:3])
        avoid_sectors = ', '.join(rotation.get('sectors_to_avoid', [])[:2])
        
        rotation_html = f'''
            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 20px;">
                <tr>
                    <td style="padding: 12px 16px; background: rgba(96,165,250,0.1); border-radius: 8px; border-left: 3px solid #60a5fa;">
                        <span style="font-size: 14px; font-weight: 600; color: #60a5fa;">🔄 SECTOR ROTATION: {phase}</span>
                        <p style="margin: 8px 0; font-size: 12px; color: #8b8b8e;">{rotation.get('phase_description', '')}</p>
                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="font-size: 12px; margin-top: 8px;">
                            <tr>
                                <td style="padding: 4px 0;"><span style="color: #4ade80;">✓ Favor:</span> <span style="color: #f5f5f7;">{rec_sectors}</span></td>
                            </tr>
                            <tr>
                                <td style="padding: 4px 0;"><span style="color: #ff6b6b;">✗ Avoid:</span> <span style="color: #f5f5f7;">{avoid_sectors}</span></td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>'''
    
    # Combine all subsections
    return f'''
                    <!-- Retail Investor Insights -->
                    <tr>
                        <td style="padding: 32px;">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td>
                                        <span style="font-family: Georgia, serif; font-size: 22px; font-weight: 600; color: #f5f5f7;">💰 Retail Investor Insights</span>
                                        <p style="margin: 8px 0 24px 0; font-size: 13px; color: #8b8b8e;">Actionable intelligence specifically for individual investors</p>
                                    </td>
                                </tr>
                                <tr>
                                    <td>
                                        {tlh_html}
                                        {corr_html}
                                        {stop_html}
                                        {squeeze_html}
                                        {rotation_html}
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>'''


def _build_footer() -> str:
    """Build the footer section."""
    return '''
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 32px; background-color: #0a0a0f; text-align: center;">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td align="center">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                                            <tr>
                                                <td style="width: 32px; height: 32px; background: linear-gradient(135deg, #d4af37 0%, #f4d03f 50%, #d4af37 100%); border-radius: 6px; text-align: center; vertical-align: middle;">
                                                    <span style="font-family: Georgia, serif; font-weight: 700; font-size: 16px; color: #0a0a0f;">SP</span>
                                                </td>
                                                <td style="padding-left: 10px;">
                                                    <span style="font-family: Georgia, serif; font-size: 18px; font-weight: 600; color: #f5f5f7;">Stock Pulse</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="padding-top: 20px;">
                                        <span style="font-size: 11px; color: #6b6b7b; line-height: 1.6; max-width: 500px; display: inline-block;">This newsletter is for informational purposes only and should not be considered financial advice. Past performance does not guarantee future results. Always conduct your own research before making investment decisions.</span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>'''


# For testing
if __name__ == "__main__":
    sample_data = {
        "market_overview": {
            "indices": {
                "S&P 500": {"value": 5847.21, "change_pct": 1.24},
                "NASDAQ": {"value": 18392.44, "change_pct": 1.87},
                "DOW": {"value": 43284.12, "change_pct": -0.32}
            }
        },
        "new_recommendations": [
            {
                "ticker": "NVDA",
                "company_name": "NVIDIA Corporation",
                "action": "STRONG BUY",
                "current_market_price": 892.45,
                "price_target": 1050.00,
                "stop_loss": 780.00,
                "allocation_pct": 25,
                "pe_ratio": "32.4x",
                "market_cap": "$2.2T",
                "ytd_return": 127,
                "thesis": "NVIDIA makes the computer chips that power artificial intelligence. Every major tech company needs their products, and demand is growing fast."
            },
            {
                "ticker": "AAPL",
                "company_name": "Apple Inc.",
                "action": "HOLD",
                "current_market_price": 227.63,
                "price_target": 240.00,
                "allocation_pct": 20,
                "pe_ratio": "29.1x",
                "market_cap": "$3.5T",
                "ytd_return": 18,
                "thesis": "Apple is a great company, but the stock price already reflects expectations for the new iPhone."
            }
        ],
        "politician_trades": [
            {"politician": "Nancy Pelosi", "role": "Representative, CA-11", "party": "D", "symbol": "GOOGL", "action": "BUY", "amount": 750000, "date": "Jan 24"},
            {"politician": "Tommy Tuberville", "role": "Senator, Alabama", "party": "R", "symbol": "RTX", "action": "SELL", "amount": 175000, "date": "Jan 22"}
        ]
    }
    
    sample_history = {
        "performance_summary": {
            "total_return_pct": 142.8,
            "sp500_total_return_pct": 67.4,
            "win_rate_pct": 78
        },
        "current_portfolio": [
            {"ticker": "META", "company_name": "Meta Platforms", "recommended_price": 485.20, "current_price": 612.45, "gain_loss_pct": 26.2, "recommendation": "BUY", "date": "Dec 15, 2025"},
            {"ticker": "MSFT", "company_name": "Microsoft", "recommended_price": 380.00, "current_price": 420.50, "gain_loss_pct": 10.7, "recommendation": "BUY", "date": "Nov 1, 2025"}
        ]
    }
    
    sample_context = {
        "vix_data": {"current": 14.82, "change_pct": -8.4}
    }
    
    html = build_email_html(sample_data, sample_history, sample_context)
    print(f"Generated HTML length: {len(html)} characters")
    
    with open("../output/test_biweekly_email.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Saved to output/test_biweekly_email.html")
