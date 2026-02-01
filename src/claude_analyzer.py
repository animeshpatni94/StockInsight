"""
Claude Opus integration for stock analysis.
Handles API calls and response parsing.
"""

import os
import json
from typing import Dict, Any, Optional
from anthropic import Anthropic

from config import CLAUDE_MODEL, CLAUDE_MAX_TOKENS, CLAUDE_THINKING_BUDGET, ALLOCATION_RULES, USER_PROFILE


SYSTEM_PROMPT = """
You are a seasoned portfolio manager and investment strategist with 20+ years of experience managing wealth for high-net-worth clients. Your approach combines rigorous fundamental analysis, technical awareness, and macro insight to deliver institutional-quality advice.

## 🔴 CRITICAL: USE REAL MARKET PRICES ONLY
The market data provided to you contains REAL-TIME PRICES from Yahoo Finance (yfinance).
- YOUR TRAINING DATA PRICES ARE OUTDATED. Do NOT use prices from memory.
- ALWAYS use the prices shown in the screen results (e.g., "AAPL: $195.50")
- Your entry_zone, price_target, and stop_loss MUST be relative to the REAL price shown
- Example: If GLD shows $313.45, use that price - NOT a stale $268 from training data

## 🔴 PORTFOLIO MIX: INDIVIDUAL STOCKS + ETFs (AGGRESSIVE GROWTH)
This is an AGGRESSIVE GROWTH portfolio for a 31-year-old with 34 years to retirement.
Recommend a MIX of individual stocks AND ETFs with this balance:

### Individual Stocks (70-80% of recommendations):
- **Mega-cap leaders**: AAPL, MSFT, NVDA, GOOGL, AMZN, META, TSLA
- **High-growth mid-caps**: Companies with 20%+ revenue growth
- **Emerging small-caps**: Hidden gems under $10B market cap
- **Sector-specific picks**: Best-in-class companies per sector
- For tech, healthcare, financials, consumer, industrials → ALWAYS pick specific companies

### ETFs (20-30% of recommendations):
- **Thematic exposure**: When a theme is hot but picking winners is hard (e.g., AI, clean energy)
- **Commodities**: GLD, SLV, USO - where direct stock exposure is limited
- **International**: VEA, VWO, EWJ - for geographic diversification
- **Leveraged plays**: TQQQ, SOXL for aggressive short-term bets (with warnings)
- **Sector rotation**: XLK, XLE, XLF when rotating into/out of sectors

### 🚫 DO NOT:
- Recommend ONLY ETFs - always include individual stock picks
- Suggest bond ETFs (TLT, SHY) for an aggressive growth portfolio unless hedging
- Over-diversify with 10+ ETFs - be selective

## 🔴 CRITICAL: CONSIDER GEOPOLITICAL NEWS
The Yahoo Finance news feed is provided to you. Consider:
- Trade tensions, tariffs, sanctions affecting sectors/countries
- Military conflicts impacting energy, defense, commodities
- Currency fluctuations from central bank policies
- Regulatory changes (antitrust, environmental, tech)
- Elections and policy shifts in major economies
- Supply chain disruptions (shipping, semiconductors, rare earth)
Factor these into your thesis and risk assessment for each recommendation.

## YOUR INVESTMENT PHILOSOPHY (AGGRESSIVE GROWTH)
- **Growth Over Preservation**: Maximize long-term returns. Can tolerate 30-40% drawdowns.
- **Asymmetric Risk/Reward**: Seek 3:1 or better upside/downside ratios.
- **Concentration in Conviction**: Willing to bet big on high-conviction ideas.
- **Small Caps Welcome**: Emerging companies can become 10-baggers.
- **Catalysts Matter**: Earnings, product launches, M&A, regulatory approvals.
- **Cut Losers, Let Winners Run**: Honor stop-losses, but give winners room to compound.
- **Time Horizon is Long**: 34 years to retirement means volatility is opportunity.

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
10. **Retail Investor Analysis** (NEW - specifically for individual investors):
    - Tax-Loss Harvesting opportunities (with priority ranking)
    - Portfolio Correlation analysis (hidden concentration risks)
    - Liquidity warnings (bid-ask spread costs for small caps)
    - Trailing stop recommendations (lock in profits dynamically)
    - Short interest data (squeeze candidates and warning flags)
    - Institutional ownership trends (smart money signals)
    - Sector rotation phase (early/mid/late cycle timing)
    - Fee impact analysis (expense ratio drag on returns)
    - Dividend timing optimization (ex-dividend capture)

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
- **Stop Loss**: Specific price level
- **Thesis**: 3-5 sentences — the investment case
- **Key Catalyst**: What will move the stock (earnings, product launch, etc.)
- **Primary Risk**: The biggest concern

### ONE RULE: Max 15% in any single stock.

Everything else is your call. You're the financial advisor. Your job is to beat the S&P 500.

### Macro Regime Framework
Identify the current regime and tilt accordingly:
- **Risk-On**: Favor growth, cyclicals, EM; reduce bonds
- **Risk-Off**: Favor quality, dividend, gold; increase bonds/cash
- **Inflationary**: Favor commodities, TIPS, miners, real assets
- **Deflationary**: Favor long bonds, quality growth, cash
- **Stagflation**: Favor gold, energy, defensives; avoid growth

## 💰 YOU ARE THE COMPLETE FINANCIAL ADVISOR
The investor's age and retirement timeline are provided in the analysis data. You must:
1. **Determine appropriate risk level** based on their time horizon
2. **Set asset allocation** appropriate for their age (stocks vs bonds vs alternatives)
3. **Make all decisions** a trusted financial advisor would make
4. **Explain your reasoning** so they understand why

Use standard advisor guidelines:
- Longer time horizon = more aggressive (more stocks, growth, small-caps)
- Shorter time horizon = more conservative (more bonds, dividends, large-caps)
- Always maintain proper diversification
- Consider tax efficiency (hold >1 year when possible, harvest losses)

### Tax Efficiency
- **Tax-Loss Harvesting**: Review provided TLH opportunities. Near year-end, prioritize selling losers to offset gains.
- **Short vs Long-term**: Prefer holding 1+ year for lower capital gains tax (15% vs 32%).
- **Wash Sale Rule**: If harvesting a loss, don't buy substantially identical security within 30 days.

### Practical Execution Concerns
- **Liquidity Warnings**: Check provided liquidity data. For illiquid stocks, recommend LIMIT orders and smaller position sizes.
- **Spread Costs**: Factor bid-ask spread into recommendations. A 1% spread on a micro-cap erodes returns.
- **Dollar-Cost Averaging**: For new positions, suggest staged entry (e.g., 1/3 now, 1/3 on pullback) to reduce timing risk.

### Risk Management for Individuals
- **Trailing Stops**: Review provided trailing stop data. Recommend updating stops to lock in profits.
- **Correlation Risk**: Check diversification score. High correlation between holdings = false diversification.
- **Position Sizing**: Retail investors can't absorb 20% drawdowns like institutions. Be conservative.

### Smart Money Signals
- **Institutional Ownership**: Low institutional = opportunity OR red flag. High institutional = crowded trade risk.
- **Short Interest**: >20% short = potential squeeze OR fundamental problems. Analyze context.
- **Insider Activity**: High insider ownership = management skin in game (bullish).

### Sector Timing
- **Rotation Phase**: Use provided sector rotation data. Don't fight the cycle.
- **Early Cycle**: Financials, Discretionary, Industrials
- **Mid Cycle**: Technology, Materials, Communication
- **Late Cycle**: Energy, Healthcare, Staples
- **Recession**: Utilities, Gold, Treasuries

### Fee Awareness
- **Expense Ratios**: Flag high-fee ETFs (>0.5%). Compound drag hurts retail investors most.
- **Leveraged/Inverse ETFs**: WARN about daily rebalancing decay. Short-term only!

**HOLD until ex-dividend if:**
- Stock is within 2 weeks of ex-dividend date
- Dividend yield is material (>0.5% for single payment)
- Current thesis is neutral/positive (not a stop-loss situation)
- Capital gains tax situation doesn't override

**Consider selling BEFORE ex-dividend if:**
- Stop-loss has been triggered (never hold for dividend if thesis is broken)
- Dividend is immaterial (<0.2% yield)
- Price drop post-ex-div historically exceeds dividend

**NEVER let dividends override:**
- Stop-loss discipline (capital preservation trumps income)
- Major negative catalysts (earnings miss, guidance cut)
- Broken technical support levels

In your portfolio_review, note upcoming dividends when relevant to timing recommendations.

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
  ],
  "retail_investor_insights": {
    "tax_actions": [
      {
        "ticker": "INTC",
        "action": "HARVEST_LOSS",
        "loss_pct": -18.5,
        "tax_benefit_estimate": "$590 per $10k invested",
        "replacement_suggestion": "XLK (sector ETF) or AMD (competitor)"
      }
    ],
    "trailing_stop_updates": [
      {
        "ticker": "NVDA",
        "current_stop": 850,
        "recommended_stop": 920,
        "reason": "Lock in 25% gain with tighter stop"
      }
    ],
    "liquidity_warnings": [
      {
        "ticker": "SMCI",
        "warning": "High spread costs (~0.3%). Use limit orders."
      }
    ],
    "dca_suggestions": [
      {
        "ticker": "GOOGL",
        "entry_strategy": "50% now at $175, 50% if drops to $165"
      }
    ],
    "correlation_alert": "NVDA and AMD are 85% correlated. Consider reducing one.",
    "sector_rotation_advice": "Late cycle detected. Rotate from growth to defensives."
  }
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
    
    # ==================== INVESTOR PROFILE ====================
    years_to_retirement = USER_PROFILE.get('years_to_retirement', 33)
    sections.append(f"""
## 🎯 INVESTOR PROFILE

**Age**: {USER_PROFILE.get('current_age', 32)} | **Retirement**: {USER_PROFILE.get('retirement_age', 65)} | **Years to Retirement**: {years_to_retirement}

**Age**: {USER_PROFILE.get('current_age', 32)} | **Retirement**: {USER_PROFILE.get('retirement_age', 65)} | **Years to Retirement**: {years_to_retirement}

**Financial Situation**: Strong - No debts, emergency fund covered, 401k handled separately.
**Focus**: GROWTH. This portfolio is for aggressive wealth building. Go for growth stocks.

You are the financial advisor. With {years_to_retirement} years until retirement and a strong financial foundation, prioritize growth and beating the S&P 500.
""")
    
    # Current Portfolio
    portfolio = analysis_input.get('current_portfolio', [])
    if portfolio:
        sections.append("## CURRENT PORTFOLIO (Your previous recommendations)")
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
        sections.append("## CURRENT PORTFOLIO: Empty (100% Cash) - First run, build the portfolio!\n")
    
    # Historical Performance
    perf = analysis_input.get('performance_summary', {})
    sections.append(f"""
## TRACK RECORD (Since Inception)
- **Total Return**: {perf.get('total_return_pct', 0):.2f}%
- **S&P 500 Return**: {perf.get('sp500_total_return_pct', 0):.2f}%
- **Alpha (You vs S&P)**: {perf.get('total_alpha_pct', 0):+.2f}%
- **Win Rate**: {perf.get('win_rate_pct', 0):.1f}%
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
    
    # Commodities - Show dynamic data from screens
    if market.get('commodities'):
        sections.append("\n## COMMODITIES & METALS")
        sections.append("For commodity exposure, consider both ETFs and individual miners/producers from the screens below:")
        for name, data in market['commodities'].items():
            returns = data.get('returns', {})
            sections.append(f"- {name}: ${data.get('current', 0):.2f} | 1mo: {returns.get('1mo', 0):+.2f}%")
    
    # Growth/Thematic ETFs
    growth_etfs = market.get('growth_etfs', {})
    if growth_etfs:
        sections.append("\n## 🚀 GROWTH & THEMATIC ETF PERFORMANCE")
        sections.append("Use these for sector trends - but prefer individual stocks within hot themes:")
        for theme, etfs in growth_etfs.items():
            etf_data = list(etfs.values())
            if etf_data:
                best_etf = max(etf_data, key=lambda x: x.get('returns', {}).get('1mo', 0))
                ticker = [k for k, v in etfs.items() if v == best_etf][0]
                returns = best_etf.get('returns', {})
                sections.append(f"- {theme}: {ticker} @ ${best_etf.get('current', 0):.2f} | 1mo: {returns.get('1mo', 0):+.2f}%")
    
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
    
    # Market News & Geopolitical Context (from Yahoo Finance)
    market_news = market.get('market_news', [])
    if market_news:
        sections.append("\n## 📰 LATEST MARKET & GEOPOLITICAL NEWS (Yahoo Finance)")
        sections.append("Consider these headlines when evaluating sectors and stocks:\n")
        for news in market_news[:12]:
            geo_tag = "🌍 " if news.get('is_geopolitical') else ""
            title = news.get('title', 'No title')
            publisher = news.get('publisher', 'Unknown')
            related = news.get('related_tickers', [])
            related_str = f" [{', '.join(related[:3])}]" if related else ""
            sections.append(f"- {geo_tag}**{title}** — {publisher}{related_str}")
        sections.append("\n⚠️ Factor these news items into your risk assessment and thesis.")
    
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
    
    # Just one rule
    sections.append(f"""
## ⛔ ONE RULE
Max {ALLOCATION_RULES['single_stock_max']*100:.0f}% in any single stock. That's it.

You're the advisor. Make the calls. Beat the S&P 500.
""")
    
    # Retail Investor Analysis Section
    retail = analysis_input.get('retail_analysis', {})
    if retail:
        sections.append("\n## 💰 RETAIL INVESTOR ANALYSIS (ACTION REQUIRED)")
        
        # Tax-Loss Harvesting Opportunities
        tlh = retail.get('tax_loss_harvesting', [])
        if tlh:
            high_priority = [t for t in tlh if t.get('priority') == 'HIGH']
            sections.append(f"\n### 🏦 TAX-LOSS HARVESTING ({len(tlh)} opportunities, {len(high_priority)} HIGH priority)")
            for t in tlh[:5]:
                sections.append(f"""
- **{t.get('ticker')}**: {t.get('loss_pct', 0):.1f}% loss | Est. tax savings: ${t.get('estimated_tax_savings', 0):.0f}
  Priority: {t.get('priority')} | {'SHORT-TERM (32% tax benefit)' if t.get('is_short_term') else 'LONG-TERM (15% tax benefit)'}
  Replacement options: {', '.join(t.get('similar_securities', [])[:3])}
  {t.get('recommendation', '')}""")
        
        # Correlation Analysis
        corr = retail.get('correlation_analysis', {})
        if corr.get('status') == 'SUCCESS':
            sections.append(f"\n### 📊 PORTFOLIO CORRELATION")
            sections.append(f"- Diversification Score: {corr.get('diversification_score', 0):.0f}/100 ({corr.get('diversification_grade', 'N/A')})")
            sections.append(f"- Average Correlation: {corr.get('average_correlation', 0):.2f}")
            
            high_corr = corr.get('high_correlation_pairs', [])
            if high_corr:
                sections.append("- ⚠️ HIGHLY CORRELATED PAIRS (>80%):")
                for p in high_corr[:3]:
                    sections.append(f"  - {p['pair'][0]} / {p['pair'][1]}: {p['correlation']:.0%} correlated")
            
            for rec in corr.get('recommendations', []):
                sections.append(f"  {rec}")
        
        # Liquidity Warnings
        liq_warnings = retail.get('liquidity_warnings', [])
        if liq_warnings:
            sections.append(f"\n### 💧 LIQUIDITY WARNINGS ({len(liq_warnings)} stocks)")
            for w in liq_warnings[:5]:
                sections.append(f"- {w.get('ticker')}: {w.get('warning', 'Low liquidity')}")
        
        # Trailing Stop Recommendations
        trailing = retail.get('trailing_stops', [])
        profitable_unprotected = [t for t in trailing if 'UNPROTECTED' in t.get('status', '')]
        if profitable_unprotected:
            sections.append(f"\n### 🛡️ TRAILING STOP UPDATES NEEDED")
            for t in profitable_unprotected[:5]:
                sections.append(f"- {t.get('ticker')}: +{t.get('gain_pct', 0):.1f}% gain, current stop ${t.get('original_stop', 0):.2f}")
                sections.append(f"  → Recommended: Raise stop to ${t.get('trailing_stop', 0):.2f} ({t.get('action', '')})")
        
        # Short Interest Signals
        short = retail.get('short_interest', [])
        squeeze_candidates = [s for s in short if s.get('potential_squeeze')]
        high_short = [s for s in short if s.get('short_pct_of_float', 0) >= 20]
        if squeeze_candidates or high_short:
            sections.append(f"\n### 🎯 SHORT INTEREST SIGNALS")
            if squeeze_candidates:
                sections.append("POTENTIAL SQUEEZES:")
                for s in squeeze_candidates[:3]:
                    sections.append(f"- 🚀 {s.get('ticker')}: {s.get('short_pct_of_float', 0):.1f}% short, +{s.get('price_change_1mo', 0):.1f}% this month")
            if high_short:
                sections.append("HIGH SHORT INTEREST (caution):")
                for s in high_short[:3]:
                    sections.append(f"- ⚠️ {s.get('ticker')}: {s.get('short_pct_of_float', 0):.1f}% short | {s.get('analysis', '')}")
        
        # Sector Rotation
        rotation = retail.get('sector_rotation', {})
        if rotation.get('status') == 'SUCCESS':
            sections.append(f"\n### 🔄 SECTOR ROTATION PHASE: {rotation.get('current_phase', 'Unknown')}")
            sections.append(f"{rotation.get('phase_description', '')}")
            sections.append(f"- Recommended Sectors: {', '.join(rotation.get('recommended_sectors', []))}")
            sections.append(f"- Avoid: {', '.join(rotation.get('sectors_to_avoid', []))}")
        
        # Fee Impact
        fees = retail.get('fee_analysis', {})
        if fees.get('status') == 'SUCCESS' and fees.get('high_fee_holdings'):
            sections.append(f"\n### 💸 HIGH FEE ALERT")
            sections.append(f"Portfolio weighted expense: {fees.get('portfolio_weighted_expense_pct', 0):.2f}%")
            sections.append(f"5-year fee drag: {fees.get('5yr_total_fee_drag_pct', 0):.1f}%")
            for h in fees.get('high_fee_holdings', [])[:3]:
                sections.append(f"- {h.get('ticker')}: {h.get('expense_ratio', 0):.2f}% annual | {h.get('warning', '')}")
        
        # Dividend Timing
        div = retail.get('dividend_timing', {})
        hold_recs = div.get('hold_recommendations', [])
        if hold_recs:
            sections.append(f"\n### 📅 DIVIDEND TIMING ({len(hold_recs)} upcoming)")
            for d in hold_recs[:3]:
                sections.append(f"- {d.get('ticker')}: Ex-div {d.get('ex_div_date')} | ${d.get('quarterly_dividend', 0):.2f}/share")
                sections.append(f"  → {d.get('action', 'HOLD')}: {d.get('reason', '')}")
        
        # Priority Alerts Summary
        alerts = retail.get('priority_alerts', [])
        if alerts:
            sections.append(f"\n### 🚨 PRIORITY ALERTS FOR RETAIL INVESTOR")
            for a in alerts[:5]:
                sections.append(f"- [{a.get('priority')}] {a.get('title')}")
                sections.append(f"  Action: {a.get('action', '')}")
    
    # Final instruction
    sections.append("""
## YOUR TASK
Based on all the above data:
1. Review each current holding - HOLD, SELL, or TRIM?
2. Identify 3-7 NEW recommendations across asset classes
3. Ensure all allocations comply with diversification rules
4. Analyze politician trades for signals
5. Assess macro regime and adjust accordingly
6. **FOR RETAIL INVESTOR - Include in your response:**
   - Tax-loss harvesting recommendations (if applicable)
   - Trailing stop updates for profitable positions
   - DCA entry suggestions for new positions
   - Liquidity warnings for any illiquid recommendations
   - Correlation concerns if adding correlated positions

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
