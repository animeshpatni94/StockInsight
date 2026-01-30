"""
Claude Opus integration for stock analysis.
Handles API calls and response parsing.
"""

import os
import json
from typing import Dict, Any, Optional
from anthropic import Anthropic

from config import CLAUDE_MODEL, CLAUDE_MAX_TOKENS, CLAUDE_THINKING_BUDGET, ALLOCATION_RULES


SYSTEM_PROMPT = """
You are a seasoned portfolio manager and investment strategist with 20+ years of experience managing wealth for high-net-worth clients. Your approach combines rigorous fundamental analysis, technical awareness, and macro insight to deliver institutional-quality advice.

## 🔴 CRITICAL: USE REAL MARKET PRICES ONLY
The market data provided to you contains REAL-TIME PRICES from Yahoo Finance (yfinance).
- YOUR TRAINING DATA PRICES ARE OUTDATED. Do NOT use prices from memory.
- ALWAYS use the prices shown in the screen results (e.g., "AAPL: $195.50")
- Your entry_zone, price_target, and stop_loss MUST be relative to the REAL price shown
- Example: If GLD shows $313.45, use that price - NOT a stale $268 from training data

## YOUR INVESTMENT PHILOSOPHY
- **Preservation First**: Capital preservation is paramount. Avoid catastrophic losses.
- **Asymmetric Risk/Reward**: Seek opportunities where upside significantly exceeds downside.
- **Contrarian When Warranted**: Be greedy when others are fearful, but only with conviction.
- **Diversification is Non-Negotiable**: No single bet should threaten the portfolio.
- **Catalysts Matter**: Don't buy hopes — buy stocks with identifiable near-term catalysts.
- **Cut Losers, Let Winners Run**: Honor stop-losses ruthlessly, but give winners room.
- **Intellectual Honesty**: Admit mistakes, learn from them, and adapt.

## DATA YOU WILL ANALYZE
You have access to comprehensive market intelligence:

1. **Portfolio State**: Current holdings, entry prices, unrealized P&L, time held
2. **Historical Performance**: Past recommendations, win rate, lessons learned
3. **Market Screens** (ranked by quantitative scores):
   - Momentum leaders across market caps
   - Undervalued stocks (P/E, P/B, PEG screens)
   - Dividend aristocrats and income plays
   - Technical setups (oversold RSI, golden crosses, breakouts)
4. **Sector Analysis**: All 11 GICS sectors with relative strength
5. **Macro Indicators**: VIX, yield curve, sector rotation signals
6. **Commodities & Metals**: Gold, silver, copper, oil trends
7. **Politician Trading**: Congressional trades with committee correlation flags
8. **Earnings Calendar**: Upcoming catalysts for watchlist stocks
9. **5-Year Historical Context**: Long-term sector performance, market cycles

## DECISION FRAMEWORK

### For Existing Holdings:
**HOLD** — Thesis intact, catalysts still ahead, within risk parameters
**ADD** — Conviction increased, price attractive, allocation below target
**TRIM** — Take partial profits, reduce concentration, rebalance
**SELL** — Thesis broken, stop-loss hit, better opportunities elsewhere

### For New Recommendations:
Before recommending ANY stock, answer these questions:
1. **Why this stock?** What's the edge? What does the market miss?
2. **Why now?** What's the catalyst in the next 1-6 months?
3. **What's the risk/reward?** Quantify upside vs downside.
4. **What would prove me wrong?** Define the invalidation thesis.
5. **How does it fit the portfolio?** Diversification check.

### Position Sizing Principles:
- **High Conviction + Low Risk**: 8-15% allocation
- **Medium Conviction**: 5-8% allocation
- **Speculative/High Risk**: 2-5% allocation
- **Never exceed 20%** in any single position

## OUTPUT REQUIREMENTS

### For EACH Current Holding, Provide:
- Current price and % gain/loss since entry
- **Action**: HOLD | ADD | TRIM | SELL
- **Rationale**: 2-3 sentences explaining the decision
- Updated allocation % if changed

### For NEW Recommendations, Provide:
- **Ticker** and company name
- **Asset Class**: us_stock | international_stock | etf | commodity_etf | bond_etf | reit
- **Sector**: GICS sector or special category (Metals, Commodities, Fixed Income)
- **Investment Style**: growth | value | dividend | garp | speculative | hedge
- **Risk Level**: conservative | moderate | aggressive
- **Time Horizon**: short_term (1-3mo) | medium_term (3-12mo) | long_term (1-3yr)
- **Allocation %**: Recommended portfolio weight
- **Entry Zone**: Specific price range (e.g., $145-152)
- **Price Target**: 12-month target with rationale
- **Stop Loss**: Specific price level (typically -12% to -18%)
- **Thesis**: 3-5 sentences — the investment case
- **Key Catalyst**: What will move the stock (earnings, product launch, etc.)
- **Primary Risk**: The biggest concern

### Diversification Rules (MUST Follow):
- Maximum 20% in any single stock
- Maximum 35% in any single sector
- 5-15 total positions
- Keep 5-15% in cash/short-term treasuries

**Asset Class Ranges:**
- US Stocks: 40-70%
- International/EM: 5-20%
- Metals/Commodities: 5-15%
- Bonds/Cash: 10-25%
- REITs: 0-10%

**Style Ranges:**
- Growth: 20-40%
- Value: 20-40%
- Dividend/Income: 10-30%
- Speculative: 0-10%
- Hedges: 5-15%

**Risk Level Ranges:**
- Conservative: 30-40%
- Moderate: 40-50%
- Aggressive: 10-30%

### Macro Regime Framework
Identify the current regime and tilt accordingly:
- **Risk-On**: Favor growth, cyclicals, EM; reduce bonds
- **Risk-Off**: Favor quality, dividend, gold; increase bonds/cash
- **Inflationary**: Favor commodities, TIPS, miners, real assets
- **Deflationary**: Favor long bonds, quality growth, cash
- **Stagflation**: Favor gold, energy, defensives; avoid growth

### Politician Trading Analysis
- Flag trades that correlate with committee assignments
- Note unusual timing (before legislation, earnings, etc.)
- Identify overlap with your portfolio or watchlist
- Maintain appropriate skepticism about conflicts of interest

### Output Format
Structure your response as valid JSON:
{
  "macro_assessment": {
    "regime": "risk-on | risk-off | inflationary | etc",
    "summary": "2-3 sentence assessment",
    "implications": ["implication 1", "implication 2"]
  },
  "portfolio_review": [
    {
      "ticker": "GOOGL",
      "current_price": 196.20,
      "gain_loss_pct": 9.9,
      "action": "HOLD | SELL | TRIM",
      "new_allocation_pct": 15,
      "rationale": "Thesis intact because..."
    }
  ],
  "sells": [
    {
      "ticker": "INTC",
      "reason": "Stop-loss hit, turnaround thesis failed",
      "loss_pct": -13.2,
      "lesson_learned": "Don't bottom-fish structurally challenged businesses"
    }
  ],
  "new_recommendations": [
    {
      "ticker": "AMGN",
      "company_name": "Amgen Inc.",
      "asset_class": "us_stock",
      "sector": "Healthcare",
      "investment_style": "value",
      "risk_level": "conservative",
      "time_horizon": "long_term",
      "allocation_pct": 12,
      "entry_zone": {"low": 285, "high": 295},
      "price_target": 340,
      "stop_loss": 255,
      "thesis": "Defensive biotech with strong cash flow...",
      "risks": "Pipeline failures, Medicare price negotiations",
      "catalyst": "Obesity drug data readout Q2"
    }
  ],
  "metals_commodities_outlook": {
    "gold": {"stance": "bullish", "rationale": "..."},
    "silver": {"stance": "neutral", "rationale": "..."},
    "copper": {"stance": "bullish", "rationale": "..."},
    "oil": {"stance": "neutral", "rationale": "..."}
  },
  "politician_trade_analysis": {
    "summary": "Brief 1-2 sentence overview of congressional trading patterns this month",
    "notable_trades": [
      {
        "politician": "Nancy Pelosi",
        "party": "D",
        "ticker": "NVDA",
        "transaction_type": "Purchase",
        "amount": "$1M-$5M",
        "insight": "Bought ahead of AI chip legislation vote"
      }
    ],
    "suspicious_patterns": [
      {
        "politician": "Name",
        "party": "R or D",
        "ticker": "SYMBOL",
        "transaction_type": "Purchase/Sale",
        "company": "Company Name",
        "reason": "Why this is suspicious - committee connection, timing, etc."
      }
    ],
    "overlap_with_portfolio": [
      {
        "ticker": "AAPL",
        "politician": "Multiple members bought",
        "implication": "Bullish signal - insiders see value"
      }
    ]
  },
  "allocation_summary": {
    "by_asset_class": {...},
    "by_sector": {...},
    "by_style": {...},
    "by_horizon": {...},
    "by_risk": {...},
    "validation": "All within rules | VIOLATION: ..."
  },
  "risks_to_portfolio": [
    {
      "risk": "Tech correction 10-15%",
      "impact": "GOOGL, NVDA affected",
      "exposure_pct": 28,
      "mitigation": "Trimmed NVDA, diversified into value"
    }
  ],
  "watchlist": [
    {
      "ticker": "COST",
      "why_watching": "Best-in-class retail",
      "entry_trigger": "Pullback to $850"
    }
  ]
}

## IMPORTANT REMINDERS
- This is analysis, not financial advice. End with a standard disclaimer.
- Be concise but substantive. No fluff.
- Every recommendation needs a clear thesis AND risks.
- If you don't have conviction, say so. Cash is a valid position.
- Challenge your own assumptions. What would prove you wrong?
"""


def analyze_with_claude(analysis_input: Dict, 
                        system_prompt: str = SYSTEM_PROMPT,
                        model: str = CLAUDE_MODEL,
                        max_tokens: int = CLAUDE_MAX_TOKENS) -> Dict:
    """
    Send analysis request to Claude and parse response.
    
    Args:
        analysis_input: Dictionary with all analysis data
        system_prompt: System prompt for Claude
        model: Claude model to use
        max_tokens: Maximum response tokens
    
    Returns:
        Parsed analysis result dictionary
    """
    api_key = os.getenv('ANTHROPIC_API_KEY')
    
    if not api_key:
        print("  ❌ ANTHROPIC_API_KEY not set")
        print("  ⚠️  Returning safe fallback - existing portfolio will be preserved")
        return _get_fallback_analysis()
    
    client = Anthropic(api_key=api_key)
    
    # Format the user message with all analysis data
    user_message = _format_analysis_prompt(analysis_input)
    
    try:
        print(f"  Sending request to {model} with extended thinking enabled (streaming)...")
        
        # Use streaming for long requests with extended thinking
        response_text = ""
        thinking_text = ""
        
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            thinking={
                "type": "enabled",
                "budget_tokens": CLAUDE_THINKING_BUDGET
            },
            messages=[
                {"role": "user", "content": system_prompt + "\n\n" + user_message}
            ]
        ) as stream:
            for event in stream:
                # Handle different event types
                if hasattr(event, 'type'):
                    if event.type == 'content_block_start':
                        if hasattr(event, 'content_block'):
                            if event.content_block.type == 'thinking':
                                print("  Claude is thinking...")
                            elif event.content_block.type == 'text':
                                print("  Claude is writing response...")
                    elif event.type == 'content_block_delta':
                        if hasattr(event, 'delta'):
                            if hasattr(event.delta, 'thinking'):
                                thinking_text += event.delta.thinking
                            elif hasattr(event.delta, 'text'):
                                response_text += event.delta.text
        
        print(f"  Thinking complete ({len(thinking_text)} chars)")
        print(f"  Response received ({len(response_text)} chars)")
        
        # Parse JSON from response
        analysis_result = _parse_claude_response(response_text)
        
        print("  Analysis received and parsed successfully")
        return analysis_result
        
    except Exception as e:
        print(f"  ❌ Error calling Claude API: {str(e)}")
        print(f"  ⚠️  Returning safe fallback - existing portfolio will be preserved")
        return _get_fallback_analysis()


def _format_analysis_prompt(analysis_input: Dict) -> str:
    """
    Format all analysis data into a structured prompt.
    
    Args:
        analysis_input: Raw analysis data
    
    Returns:
        Formatted prompt string
    """
    sections = []
    
    # Current date
    sections.append(f"## ANALYSIS DATE: {analysis_input.get('current_date', 'Unknown')}\n")
    
    # Current Portfolio
    portfolio = analysis_input.get('current_portfolio', [])
    if portfolio:
        sections.append("## CURRENT PORTFOLIO HOLDINGS")
        for h in portfolio:
            sections.append(f"""
**{h.get('ticker')}** - {h.get('company_name') or 'Unknown'}
- Sector: {h.get('sector') or 'Unknown'}
- Entry Price: ${(h.get('recommended_price') or 0):.2f}
- Current Price: ${(h.get('current_price') or 0):.2f}
- Gain/Loss: {(h.get('gain_loss_pct') or 0):+.2f}%
- Allocation: {(h.get('allocation_pct') or 0):.1f}%
- Price Target: ${(h.get('price_target') or 0):.2f}
- Stop Loss: ${(h.get('stop_loss') or 0):.2f}
- Thesis: {h.get('thesis') or 'N/A'}
- Status: {h.get('status') or 'HOLD'}
""")
    else:
        sections.append("## CURRENT PORTFOLIO: Empty (100% Cash)\n")
    
    # Historical Performance
    perf = analysis_input.get('performance_summary', {})
    sections.append(f"""
## HISTORICAL PERFORMANCE
- Total Return: {perf.get('total_return_pct', 0):.2f}%
- vs S&P 500: {perf.get('total_alpha_pct', 0):+.2f}%
- Win Rate: {perf.get('win_rate_pct', 0):.1f}%
- Average Win: {perf.get('average_win_pct', 0):+.2f}%
- Average Loss: {perf.get('average_loss_pct', 0):.2f}%
""")
    
    # Risk Management Status (industry-standard drawdown protection)
    risk_metrics = analysis_input.get('risk_metrics', {})
    if risk_metrics:
        status = risk_metrics.get('risk_status', 'NORMAL')
        metrics = risk_metrics.get('metrics', {})
        rules = risk_metrics.get('rules', {})
        recommendations = risk_metrics.get('recommendations', [])
        reasons = risk_metrics.get('risk_reasons', [])
        
        status_emoji = {
            'NORMAL': '🟢',
            'CAUTION': '🟡', 
            'DEFENSIVE': '🟠',
            'CRITICAL': '🔴'
        }.get(status, '⚪')
        
        sections.append(f"""
## ⚠️ RISK MANAGEMENT STATUS: {status_emoji} {status}

### Current Metrics
- Portfolio Value: ${metrics.get('current_value', 100000):,.2f}
- Peak Value: ${metrics.get('peak_value', 100000):,.2f}
- Drawdown from Peak: {metrics.get('drawdown_pct', 0):.1f}%
- Consecutive Losses: {metrics.get('consecutive_losses', 0)}
- Win Rate: {metrics.get('win_rate_pct', 0):.1f}%
- Alpha vs S&P 500: {metrics.get('alpha_vs_sp500', 0):+.1f}%
""")
        
        if reasons:
            sections.append("### Risk Triggers Active")
            for reason in reasons:
                sections.append(f"- ⚠️ {reason}")
        
        sections.append(f"""
### MANDATORY RULES FOR {status} MODE
- Maximum position size: {rules.get('max_position_size', 15)}%
- Minimum cash allocation: {rules.get('min_cash', 5)}%
- Aggressive positions allowed: {'Yes' if rules.get('aggressive_allowed', True) else 'NO'}
- Speculative positions allowed: {'Yes' if rules.get('speculative_allowed', True) else 'NO'}
- Maximum new positions this period: {rules.get('max_new_positions', 5)}

### Required Actions
""")
        for rec in recommendations:
            sections.append(f"- {rec}")
        
        sections.append("")  # Empty line
    
    # Closed Positions (lessons learned)
    closed = analysis_input.get('closed_positions', [])
    if closed:
        sections.append("## RECENT CLOSED POSITIONS (Learn from these)")
        for c in closed[-5:]:  # Last 5
            sections.append(f"- {c.get('ticker')}: {c.get('return_pct', 0):+.2f}% | Reason: {c.get('reason', 'N/A')}")
    
    # Market Data
    market = analysis_input.get('market_data', {})
    
    # Indexes
    if market.get('indexes'):
        sections.append("\n## MARKET INDEXES")
        for name, data in market['indexes'].items():
            returns = data.get('returns', {})
            sections.append(f"- {name}: {data.get('current', 0):.2f} | 1mo: {returns.get('1mo', 0):+.2f}% | YTD: {returns.get('ytd', 0):+.2f}%")
    
    # Sectors
    if market.get('sectors'):
        sections.append("\n## SECTOR PERFORMANCE")
        for sector, data in market['sectors'].items():
            returns = data.get('returns', {})
            rs = data.get('relative_strength_3mo', 0)
            sections.append(f"- {sector} ({data.get('etf')}): 1mo {returns.get('1mo', 0):+.2f}% | RS: {rs:+.2f}")
    
    # Commodities
    if market.get('commodities'):
        sections.append("\n## COMMODITIES & METALS")
        for name, data in market['commodities'].items():
            returns = data.get('returns', {})
            sections.append(f"- {name}: ${data.get('current', 0):.2f} | 1mo: {returns.get('1mo', 0):+.2f}%")
    
    # Macro indicators
    macro = market.get('macro', {})
    if macro:
        vix = macro.get('vix', {})
        sections.append(f"""
## MACRO INDICATORS & VOLATILITY CONTEXT
### VIX (Fear Index)
- Current: {vix.get('current', 'N/A')}
- 30-day Average: {vix.get('avg_30d', 'N/A')}
- 1-year Average: {vix.get('avg_1y', 'N/A')}
- 1-year Range: {vix.get('low_1y', 'N/A')} - {vix.get('high_1y', 'N/A')}
- Alert Level: {vix.get('alert_level', 'NORMAL')} {vix.get('alert_emoji', '')}
- Recommendation: {vix.get('recommendation', 'Normal conditions')}

### Dollar & Yields
- Dollar (UUP): {macro.get('dollar', {}).get('trend', 'N/A')}
""")
    
    # Historical context (5-year perspective to reduce recency bias)
    historical = market.get('historical_context', {})
    if historical:
        sections.append("\n## 5-YEAR HISTORICAL CONTEXT (Reduce Recency Bias)")
        
        # P/E context
        pe_context = historical.get('sp500_pe_context', {})
        if pe_context.get('current_pe'):
            sections.append(f"""
### S&P 500 Valuation
- Current P/E: {pe_context.get('current_pe', 'N/A')}
- Historical Average P/E: {pe_context.get('historical_avg', 17)}
- Deviation from Average: {pe_context.get('deviation_from_avg', 0):+.1f}%
- Assessment: {pe_context.get('assessment', 'unknown').upper()}
""")
        
        # 5-year sector performance
        sector_5yr = historical.get('sector_5yr_performance', {})
        if sector_5yr:
            sections.append("### 5-Year Sector Performance (Annualized)")
            sorted_sectors = sorted(sector_5yr.items(), key=lambda x: x[1].get('avg_annual_5y', 0), reverse=True)
            for sector, data in sorted_sectors[:5]:
                sections.append(f"- {sector}: {data.get('avg_annual_5y', 0):+.1f}%/yr (5yr total: {data.get('return_5y', 0):+.1f}%)")
            sections.append("... (Top 5 shown)")
        
        # Historical VIX
        hist_vix = historical.get('historical_vix', {})
        if hist_vix:
            sections.append(f"""
### Historical VIX Context
- 5-year Average: {hist_vix.get('avg_5y', 'N/A')}
- 5-year Range: {hist_vix.get('min_5y', 'N/A')} - {hist_vix.get('max_5y', 'N/A')}
- Current vs 5yr Avg: {hist_vix.get('current_vs_5y_avg', 0):+.1f}%
""")
    
    # Earnings Calendar Warnings
    earnings = analysis_input.get('earnings_calendar', {})
    if earnings:
        sections.append(f"\n## ⚠️ UPCOMING EARNINGS ({len(earnings)} stocks)")
        sections.append("Be cautious recommending these stocks - earnings volatility risk:")
        for ticker, data in list(earnings.items())[:10]:
            sections.append(f"- {ticker}: Earnings in {data.get('days_until', '?')} days ({data.get('earnings_date', 'TBD')})")
    
    # Screen Results - WITH REAL PRICES (yfinance is source of truth)
    screens = analysis_input.get('screen_results', {})
    
    sections.append("""
## 🔴 CRITICAL: REAL-TIME PRICE DATA
The prices shown below are REAL MARKET PRICES from Yahoo Finance (yfinance).
YOU MUST USE THESE EXACT PRICES when making recommendations.
DO NOT use prices from your training data - they are outdated.
Your entry_zone, price_target, and stop_loss MUST be based on these real prices.
""")
    
    if screens.get('momentum'):
        sections.append("\n## MOMENTUM SCREENS")
        
        gainers = screens['momentum'].get('top_gainers', [])[:50]
        if gainers:
            sections.append("Top Gainers (1mo):")
            for g in gainers:
                price = g.get('current_price', 0)
                sections.append(f"  - {g.get('ticker')}: ${price:.2f} | Return: {g.get('return_pct', 0):+.2f}%")
        
        losers = screens['momentum'].get('top_losers', [])[:50]
        if losers:
            sections.append("Top Losers (potential value):")
            for l in losers:
                price = l.get('current_price', 0)
                sections.append(f"  - {l.get('ticker')}: ${price:.2f} | Return: {l.get('return_pct', 0):+.2f}%")
        
        breakouts = screens['momentum'].get('52w_high_breakouts', [])[:45]
        if breakouts:
            sections.append("52-Week High Breakouts:")
            for b in breakouts:
                price = b.get('current_price', 0)
                sections.append(f"  - {b.get('ticker')}: ${price:.2f}")
        
        bounces = screens['momentum'].get('52w_low_bounces', [])[:45]
        if bounces:
            sections.append("52-Week Low Bounces:")
            for b in bounces:
                price = b.get('current_price', 0)
                sections.append(f"  - {b.get('ticker')}: ${price:.2f}")
        
        volume = screens['momentum'].get('unusual_volume', [])[:45]
        if volume:
            sections.append("Unusual Volume:")
            for v in volume:
                price = v.get('current_price', 0)
                sections.append(f"  - {v.get('ticker')}: ${price:.2f} | Vol ratio: {v.get('volume_ratio', 0):.1f}x")
    
    if screens.get('fundamental'):
        sections.append("\n## FUNDAMENTAL SCREENS")
        
        value = screens['fundamental'].get('value_stocks', [])[:50]
        if value:
            sections.append("Value Stocks (P/E<15, EPS growth>10%):")
            for v in value:
                price = v.get('current_price', 0)
                sections.append(f"  - {v.get('ticker')}: ${price:.2f} | P/E {v.get('pe_ratio', 0):.1f}, EPS growth {v.get('earnings_growth', 0):.1f}%")
        
        growth = screens['fundamental'].get('growth_stocks', [])[:50]
        if growth:
            sections.append("Growth Stocks:")
            for g in growth:
                price = g.get('current_price', 0)
                sections.append(f"  - {g.get('ticker')}: ${price:.2f} | Revenue growth {g.get('revenue_growth', 0):.1f}%")
        
        dividend = screens['fundamental'].get('dividend_stocks', [])[:45]
        if dividend:
            sections.append("Dividend Stocks (>3% yield):")
            for d in dividend:
                price = d.get('current_price', 0)
                sections.append(f"  - {d.get('ticker')}: ${price:.2f} | Yield: {d.get('dividend_yield', 0):.2f}%")
    
    if screens.get('technical'):
        sections.append("\n## TECHNICAL SCREENS")
        
        oversold = screens['technical'].get('oversold', [])[:45]
        if oversold:
            sections.append("Oversold (RSI < 30):")
            for o in oversold:
                price = o.get('current_price', 0)
                sections.append(f"  - {o.get('ticker')}: ${price:.2f} | RSI {o.get('rsi', 0):.1f}")
        
        overbought = screens['technical'].get('overbought', [])[:45]
        if overbought:
            sections.append("Overbought (RSI > 70):")
            for o in overbought:
                price = o.get('current_price', 0)
                sections.append(f"  - {o.get('ticker')}: ${price:.2f} | RSI {o.get('rsi', 0):.1f}")
        
        golden = screens['technical'].get('golden_crosses', [])[:35]
        if golden:
            sections.append("Golden Crosses:")
            for g in golden:
                price = g.get('current_price', 0)
                sections.append(f"  - {g.get('ticker')}: ${price:.2f}")
        
        death = screens['technical'].get('death_crosses', [])[:35]
        if death:
            sections.append("Death Crosses (avoid or short):")
            for d in death:
                price = d.get('current_price', 0)
                sections.append(f"  - {d.get('ticker')}: ${price:.2f}")
    
    # Politician Trades
    pol_trades = analysis_input.get('politician_trades', [])
    flagged = analysis_input.get('flagged_trades', [])
    
    if pol_trades:
        sections.append(f"\n## POLITICIAN TRADES ({len(pol_trades)} recent trades)")
        
        # Show all trades to Claude
        sections.append("Recent congressional stock transactions:")
        for t in pol_trades[:20]:  # Show up to 20 trades
            sections.append(f"""
- {t.get('politician', 'Unknown')} ({t.get('party', 'Unknown')}, {t.get('chamber', 'Unknown')})
  {t.get('transaction_type', 'Unknown')} {t.get('ticker', 'N/A')} ({t.get('company', 'N/A')})
  Amount: {t.get('amount', 'N/A')} | Date: {t.get('trade_date', 'N/A')}""")
        
        if flagged:
            sections.append(f"\n⚠️ SUSPICIOUS TRADES ({len(flagged)} flagged for committee correlation):")
            for f in flagged[:5]:
                sections.append(f"""
- {f.get('politician')} ({f.get('party')})
  {f.get('transaction_type')} {f.get('ticker')} ({f.get('company')})
  Amount: {f.get('amount')}
  🚨 {f.get('correlation_reason')}
""")
    
    # Diversification Rules Reminder
    sections.append(f"""
## DIVERSIFICATION RULES (MUST FOLLOW)
- Single stock max: {ALLOCATION_RULES['single_stock_max']*100:.0f}%
- Single sector max: {ALLOCATION_RULES['single_sector_max']*100:.0f}%
- Positions: {ALLOCATION_RULES['min_positions']}-{ALLOCATION_RULES['max_positions']}
- US Stocks: {ALLOCATION_RULES['us_stocks']['min']*100:.0f}-{ALLOCATION_RULES['us_stocks']['max']*100:.0f}%
- International: {ALLOCATION_RULES['international']['min']*100:.0f}-{ALLOCATION_RULES['international']['max']*100:.0f}%
- Metals/Commodities: {ALLOCATION_RULES['metals_commodities']['min']*100:.0f}-{ALLOCATION_RULES['metals_commodities']['max']*100:.0f}%
- Bonds/Cash: {ALLOCATION_RULES['bonds_cash']['min']*100:.0f}-{ALLOCATION_RULES['bonds_cash']['max']*100:.0f}%
""")
    
    # Final instruction
    sections.append("""
## YOUR TASK
Based on all the above data:
1. Review each current holding - HOLD, SELL, or TRIM?
2. Identify 3-7 NEW recommendations across asset classes
3. Ensure all allocations comply with diversification rules
4. Analyze politician trades for signals
5. Assess macro regime and adjust accordingly

Respond with valid JSON following the output format specified in your instructions.
""")
    
    return "\n".join(sections)


def _parse_claude_response(response_text: str) -> Dict:
    """
    Parse Claude's response to extract JSON.
    
    Args:
        response_text: Raw response from Claude
    
    Returns:
        Parsed JSON dictionary
    """
    try:
        # Try to find JSON in the response
        # Look for JSON block markers
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            json_str = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            json_str = response_text[start:end].strip()
        else:
            # Try to find JSON object directly
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            json_str = response_text[start:end]
        
        return json.loads(json_str)
        
    except json.JSONDecodeError as e:
        print(f"  Warning: Could not parse JSON from response: {e}")
        # Return a minimal valid structure
        return {
            "macro_assessment": {
                "regime": "unknown",
                "summary": "Unable to parse response",
                "implications": []
            },
            "portfolio_review": [],
            "sells": [],
            "new_recommendations": [],
            "metals_commodities_outlook": {},
            "politician_trade_analysis": {},
            "allocation_summary": {},
            "risks_to_portfolio": [],
            "watchlist": [],
            "raw_response": response_text[:2000]  # Include partial raw response
        }


def _get_fallback_analysis() -> Dict:
    """
    Return safe fallback analysis when API fails.
    Does NOT recommend new stocks - preserves existing portfolio.
    
    Returns:
        Safe fallback analysis dictionary with failure flag
    """
    return {
        "_api_failed": True,  # Flag to indicate API failure
        "macro_assessment": {
            "regime": "unknown",
            "summary": "Claude API unavailable - no analysis performed. Existing portfolio preserved.",
            "implications": ["Review manually before making changes"]
        },
        "portfolio_review": [],  # Empty - will preserve existing holdings
        "sells": [],  # No sells - preserve everything
        "new_recommendations": [],  # No new recs - don't add random stocks
        "metals_commodities_outlook": {},
        "politician_trade_analysis": {
            "notable_trades": [],
            "suspicious_patterns": [],
            "overlap_with_portfolio": []
        },
        "allocation_summary": {},
        "risks_to_portfolio": [],
        "watchlist": []
    }


def _get_mock_analysis() -> Dict:
    """
    Return mock analysis for LOCAL TESTING ONLY when API key not set.
    WARNING: This adds hardcoded stocks - only for development testing.
    
    Returns:
        Mock analysis dictionary
    """
    return {
        "macro_assessment": {
            "regime": "risk-on",
            "summary": "Markets showing resilience with strong employment data and easing inflation. Fed likely to hold rates steady.",
            "implications": [
                "Favor quality growth and cyclicals",
                "Maintain modest commodity exposure as hedge"
            ]
        },
        "portfolio_review": [],
        "sells": [],
        "new_recommendations": [
            {
                "ticker": "GOOGL",
                "company_name": "Alphabet Inc.",
                "asset_class": "us_stock",
                "sector": "Technology",
                "investment_style": "garp",
                "risk_level": "moderate",
                "time_horizon": "long_term",
                "allocation_pct": 12,
                "entry_zone": {"low": 175, "high": 185},
                "price_target": 220,
                "stop_loss": 155,
                "thesis": "Cheapest mega-cap tech name. AI search integration progressing well. Strong FCF generation.",
                "risks": "Regulatory headwinds, AI competition from OpenAI",
                "catalyst": "Gemini adoption metrics in Q2 earnings"
            },
            {
                "ticker": "XOM",
                "company_name": "Exxon Mobil Corp",
                "asset_class": "us_stock",
                "sector": "Energy",
                "investment_style": "value",
                "risk_level": "moderate",
                "time_horizon": "medium_term",
                "allocation_pct": 8,
                "entry_zone": {"low": 105, "high": 112},
                "price_target": 130,
                "stop_loss": 95,
                "thesis": "Best-in-class operator with strong dividend. Pioneer acquisition adds Permian scale.",
                "risks": "Oil price volatility, energy transition long-term",
                "catalyst": "Synergy realization from Pioneer deal"
            },
            {
                "ticker": "GLD",
                "company_name": "SPDR Gold Trust",
                "asset_class": "commodity_etf",
                "sector": "Metals",
                "investment_style": "hedge",
                "risk_level": "conservative",
                "time_horizon": "long_term",
                "allocation_pct": 7,
                "entry_zone": {"low": 240, "high": 250},
                "price_target": 280,
                "stop_loss": 220,
                "thesis": "Portfolio insurance against tail risks. Central bank buying remains strong.",
                "risks": "Real rates spike, dollar strength",
                "catalyst": "Continued central bank accumulation"
            }
        ],
        "metals_commodities_outlook": {
            "gold": {"stance": "bullish", "rationale": "Real rates falling, central bank buying"},
            "silver": {"stance": "neutral", "rationale": "Industrial demand mixed"},
            "copper": {"stance": "bullish", "rationale": "Electrification demand, supply constraints"},
            "oil": {"stance": "neutral", "rationale": "OPEC+ discipline vs demand concerns"}
        },
        "politician_trade_analysis": {
            "notable_trades": [],
            "suspicious_patterns": [],
            "overlap_with_portfolio": []
        },
        "allocation_summary": {
            "by_asset_class": {"us_stock": 20, "commodity_etf": 7, "cash": 73},
            "by_sector": {"Technology": 12, "Energy": 8, "Metals": 7},
            "by_style": {"garp": 12, "value": 8, "hedge": 7},
            "by_horizon": {"long_term": 19, "medium_term": 8},
            "by_risk": {"moderate": 20, "conservative": 7},
            "validation": "All within rules"
        },
        "risks_to_portfolio": [
            {
                "risk": "Tech correction",
                "impact": "GOOGL position affected",
                "exposure_pct": 12,
                "mitigation": "Diversified across sectors, stop-loss in place"
            }
        ],
        "watchlist": [
            {
                "ticker": "COST",
                "why_watching": "Best-in-class retail execution",
                "entry_trigger": "Pullback to $850 or below"
            },
            {
                "ticker": "AMGN",
                "why_watching": "Obesity drug optionality underappreciated",
                "entry_trigger": "FDA catalyst or pullback to $280"
            }
        ]
    }
