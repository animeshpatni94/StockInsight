"""
Claude Opus integration for stock analysis.
Handles API calls and response parsing.
"""

import os
import json
import time
from typing import Dict, Any, Optional
from anthropic import Anthropic

from config import CLAUDE_MODEL, CLAUDE_MAX_TOKENS, CLAUDE_THINKING_BUDGET, ALLOCATION_RULES, USER_PROFILE, BIWEEKLY_INVESTMENT_BUDGET

# Retry configuration for API resilience
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 10  # Initial delay, doubles each retry (exponential backoff)


SYSTEM_PROMPT = """
You are a seasoned portfolio manager and investment strategist with 20+ years of experience managing wealth for high-net-worth clients. Your approach combines rigorous fundamental analysis, technical awareness, and macro insight to deliver institutional-quality advice.

## 🔴 CRITICAL: BIWEEKLY FRESH INVESTMENT BUDGET
This portfolio operates on a BIWEEKLY investment schedule with FRESH money each run:
- **Fresh Budget This Period**: The user has a FIXED $1,000 (or specified amount) to invest THIS RUN
- **Existing Holdings**: The current portfolio represents ALREADY INVESTED money - review for HOLD/SELL only
- **DO NOT reallocate existing holdings** - they stay at their current dollar amounts
- **New recommendations** should ONLY spend the fresh $1,000 budget

### How to Handle:
1. **Existing Holdings**: Review each for HOLD, TRIM, or SELL based on thesis/performance
   - If HOLD: No action needed, they keep their current invested amount
   - If TRIM: Specify how much to sell (this cash goes to the fresh budget pool)
   - If SELL: Exit fully (proceeds go to fresh budget pool)
2. **New Recommendations**: Allocate the $1,000 fresh budget (plus any SELL/TRIM proceeds)
   - Express allocations as DOLLAR AMOUNTS, not portfolio percentages
   - Example: "Buy $400 of NVDA, $350 of GOOGL, $250 of XLK"

## 🔴 CRITICAL: USE REAL MARKET PRICES ONLY
The market data provided to you contains REAL-TIME PRICES from Yahoo Finance (yfinance).
- YOUR TRAINING DATA PRICES ARE OUTDATED. Do NOT use prices from memory.
- ALWAYS use the prices shown in the screen results (e.g., "AAPL: $195.50")
- Your entry_zone, price_target, and stop_loss MUST be relative to the REAL price shown
- Example: If GLD shows $313.45, use that price - NOT a stale $268 from training data

## 🔴 PORTFOLIO MIX: INDIVIDUAL STOCKS + ETFs (AGGRESSIVE GROWTH)
This is an AGGRESSIVE GROWTH portfolio for a 31-year-old with 34 years to retirement.

### 🎯 MINIMUM RECOMMENDATION COUNT: 10-15 STOCKS PER RUN
You MUST recommend at least 10 new stock picks. More is better for diversification.
Spread the $1,000 budget across many small positions rather than few large ones.

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
- Be too conservative - this is an AGGRESSIVE portfolio!

## 🔴 CRYPTOCURRENCY: INCLUDED IN YOUR UNIVERSE (DIVERSIFY!)
You have access to **150+ tradeable cryptocurrencies** alongside stocks. Crypto is provided in the CRYPTO UNIVERSE section.

### ⚠️ DIVERSIFICATION REQUIREMENT:
- **Crypto is ON TOP of stocks, NOT replacing them**
- **Allocate 10-20% of budget ($100-200) to crypto** for diversification
- **Still recommend 8-12 individual stocks** - crypto is additional exposure
- **Total recommendations: 10-15** including both stocks AND crypto

### Crypto Recommendations:
- **Treat crypto like any other asset** - recommend using the SAME format as stocks
- **Use the -USD ticker format**: BTC-USD, ETH-USD, SOL-USD, etc.
- **Include 2-4 crypto picks** in your 10-15 total recommendations
- **Crypto counts toward your $1,000 budget** - mix with stocks for diversification

### Crypto Market Sentiment (PROVIDED IN DATA):
- **Fear & Greed Index**: 0-25=Extreme Fear (cautious), 25-45=Fear, 45-55=Neutral, 55-75=Greed, 75-100=Extreme Greed (cautious)
- **BTC Dominance**: High (>60%) = Risk-off, altcoins weak. Low (<50%) = Altcoin season, more aggressive
- **50d vs 200d Average**: Price above both = bullish trend, below both = bearish trend
- **% from ATH**: Near ATH = momentum, -50%+ from ATH = potential value or continued downtrend

### Crypto-Specific Guidance:
- **Large-cap crypto (BTC, ETH, SOL, XRP)**: Can be 5-15% of speculative allocation
- **Mid-cap altcoins**: Higher risk, potential 5-10x returns
- **Consider crypto when**: Fear & Greed 20-50 (fear = opportunity), price above 200d avg
- **Reduce crypto when**: Extreme Greed (>75), price below 200d avg, BTC dominance rising fast

### For Crypto Recommendations, Use Same Format:
```json
{
  "ticker": "BTC-USD",
  "company_name": "Bitcoin",
  "action": "BUY",
  "investment_amount": 100,
  "asset_class": "crypto",
  "thesis": "Your reasoning here...",
  "entry_zone": {"low": 95000, "high": 105000},
  "price_target": 150000,
  "stop_loss": 85000,
  "risk_level": "aggressive"
}
```

## 🔴 CRITICAL: MIX OF SAFE + SPECULATIVE PICKS
For an aggressive growth portfolio, ALWAYS include a mix across 10-15 picks:

### Your $1,000 Budget Should Include (10-15 positions):
1. **2-3 Core Positions ($50-150 each)**: Blue-chip growth stocks (NVDA, GOOGL, AMZN, etc.)
2. **3-4 Growth Plays ($50-100 each)**: High-growth mid-caps with momentum
3. **2-3 Thematic/Sector Plays ($50-75 each)**: ETFs or sector leaders
4. **2-3 Crypto Plays ($25-100 each)**: BTC, ETH, or promising altcoins
5. **2-3 Speculative Bets ($25-75 each)**: High-risk/high-reward picks that could 5-10x

### Speculative Picks to Consider:
- **Emerging AI/Tech**: Small-cap AI companies, semiconductor equipment, cloud disruptors
- **Biotech**: Pre-approval drugs with upcoming catalysts
- **Clean Energy**: Solar, EV, battery tech with growth potential
- **Cryptocurrency**: BTC, ETH, SOL, or trending altcoins with momentum
- **Fintech Disruptors**: Payment tech, crypto-adjacent, DeFi plays
- **Small-Cap Gems**: Companies under $5B market cap with explosive growth
- **Turnaround Stories**: Beaten-down stocks with improving fundamentals
- **IPO/Recent Listings**: New public companies with momentum

### Risk Levels to Include:
- Conservative: 20-30% of budget (safe compounders)
- Moderate: 40-50% of budget (growth with reasonable risk)
- Aggressive/Speculative: 20-30% of budget (moonshots, including crypto)

🎯 Remember: With 33+ years to retirement, a 50% loss on a $200 speculative bet is recoverable, but missing a 10-bagger is a huge opportunity cost!

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
- **Speculative Bets Encouraged**: Allocate 20-30% to high-risk/high-reward plays.
- **Catalysts Matter**: Earnings, product launches, M&A, regulatory approvals.
- **Cut Losers, Let Winners Run**: Honor stop-losses, but give winners room to compound.
- **Time Horizon is Long**: 33+ years to retirement means volatility is opportunity.

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
10. **Retail Investor Analysis** (specifically for individual investors):
    - Tax-Loss Harvesting opportunities (with priority ranking)
    - Portfolio Correlation analysis (hidden concentration risks)
    - Liquidity warnings (bid-ask spread costs for small caps)
    - Trailing stop recommendations (lock in profits dynamically)
    - Short interest data (squeeze candidates and warning flags)
    - Institutional ownership trends (smart money signals)
    - Sector rotation phase (early/mid/late cycle timing)
    - Fee impact analysis (expense ratio drag on returns)
    - Dividend timing optimization (ex-dividend capture)

11. **Comprehensive Stock Fundamentals** (60+ data points per stock):
    - **Valuation**: P/E, Forward P/E, PEG, P/B, P/S, EV/Revenue, EV/EBITDA, Enterprise Value
    - **Profitability**: Gross Margin, EBITDA Margin, Operating Margin, Profit Margin, ROE, ROA
    - **Financial Health**: Total Cash, Total Debt, Debt/Equity, Current Ratio, Quick Ratio
    - **Cash Flow**: Free Cash Flow, Operating Cash Flow
    - **Growth**: Revenue Growth, Earnings Growth, Quarterly Revenue/Earnings Growth
    - **Analyst Consensus**: Recommendation (buy/hold/sell), Rating Score, # of Analysts, Price Targets (mean/high/low)
    - **Short Interest**: Shares Short, Short % of Float, Short Ratio, Prior Month Comparison
    - **Ownership**: Insider %, Institutional %, Float Shares, Shares Outstanding
    - **Dividends**: Yield, Rate, Payout Ratio, Ex-Dividend Date
    - **Trading**: Beta, Avg Volume (daily & 10-day), 52-Week High/Low, 50/200 DMA

12. **4-Year Historical Financials** (for portfolio + top candidates):
    - **Revenue Trend**: 4 years of annual revenue to see growth trajectory
    - **Net Income Trend**: Profitability evolution over 4 years
    - **EPS Trend**: Earnings per share history (diluted)
    - **Free Cash Flow Trend**: FCF generation over time
    - **Gross Profit Trend**: Margin consistency/expansion/contraction
    - **EBITDA Trend**: Operating earnings power over time
    - **Year-over-Year Growth Rates**: Calculated revenue growth for each period

### 🔴 USE HISTORICAL FINANCIALS FOR BETTER ANALYSIS
When analyzing stocks, especially for new recommendations:
- **Check Revenue Trend**: Is revenue consistently growing? Accelerating or decelerating?
- **Check Profitability Trend**: Is net income growing faster than revenue? (operating leverage)
- **Check FCF Trend**: Is the company generating increasing free cash flow? (quality of earnings)
- **Check EPS Trend**: Is EPS growth consistent? Any red flags from dilution?
- **Compare Multiples to Growth**: A high P/E is justified if revenue/EPS growth is consistently 20%+
- **Identify Inflection Points**: Companies transitioning from losses to profits are high-potential
- **Spot Deterioration**: Declining revenue or margins over 4 years = thesis problem

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
- **Investment Amount**: Dollar amount from the fresh $1,000 budget (e.g., $400)
- **Entry Zone**: Specific price range (e.g., $145-152)
- **Price Target**: 12-month target with rationale
- **Stop Loss**: Specific price level
- **Thesis**: 3-5 sentences — the investment case
- **Key Catalyst**: What will move the stock (earnings, product launch, etc.)
- **Primary Risk**: The biggest concern

### BUDGET ALLOCATION FOR NEW PICKS:
The fresh biweekly budget is typically $1,000. Include a MIX of risk levels:

**REQUIRED: Recommend 10-15 new stock picks per run!** Don't be lazy with just 2-3 picks.
- Diversify across different sectors and risk levels
- Mix of large-cap, mid-cap, and small-cap opportunities
- Include both ETFs and individual stocks
- Spread across multiple themes and catalysts

**Example Allocation for $1,000 budget (aggressive portfolio):**
- **$150-200**: Core large-cap growth (NVDA, GOOGL, AMZN) - moderate risk
- **$100-150**: High-growth tech leader - moderate risk  
- **$100-150**: Second tech or healthcare play - moderate risk
- **$100-150**: Mid-cap momentum play - moderate/aggressive risk
- **$75-100**: Emerging sector or thematic play - aggressive risk
- **$75-100**: International or commodity ETF - moderate risk
- **$50-75**: Small-cap growth story - aggressive risk
- **$50-75**: Speculative biotech/AI play - aggressive risk
- **$50-75**: Another speculative moonshot - aggressive risk
- **$25-50**: High-conviction micro-cap - very aggressive risk

**MUST INCLUDE at least 3-4 speculative picks!** This is an aggressive portfolio.
- Total new investments MUST equal the available budget
- Don't be boring - include multiple exciting high-upside plays
- Smaller position sizes = more diversification = better risk management

### 🔄 DOUBLING DOWN (Adding to Winners):
You CAN add more money to existing holdings if they're performing well!
- In portfolio_review, set action="ADD" with add_amount (dollar amount to add)
- Example: NVDA is up 15%, news is bullish → ADD $300 more from fresh budget
- The cost basis will be recalculated as weighted average
- This counts against the fresh $1,000 budget

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
  "fresh_budget": {
    "available_amount": 1000,
    "from_new_investment": 1000,
    "from_sells": 0,
    "from_trims": 0,
    "total_to_deploy": 1000
  },
  "portfolio_review": [
    {
      "ticker": "GOOGL",
      "current_price": 196.20,
      "current_value": 1500.00,
      "gain_loss_pct": 9.9,
      "action": "HOLD | SELL | TRIM | ADD",
      "add_amount": 0,
      "rationale": "Thesis intact because..."
    },
    {
      "ticker": "NVDA",
      "current_price": 920.00,
      "current_value": 400.00,
      "gain_loss_pct": 15.2,
      "action": "ADD",
      "add_amount": 300,
      "rationale": "Doubling down - strong earnings, AI demand accelerating"
    }
  ],
  "sells": [
    {
      "ticker": "INTC",
      "reason": "Stop-loss hit, turnaround thesis failed",
      "loss_pct": -13.2,
      "proceeds": 850.00,
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
      "investment_amount": 400,
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
    Includes automatic retry with exponential backoff for network resilience.
    
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
    
    last_error = None
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if attempt > 1:
                delay = RETRY_DELAY_SECONDS * (2 ** (attempt - 2))  # Exponential backoff
                print(f"  🔄 Retry attempt {attempt}/{MAX_RETRIES} after {delay}s delay...")
                time.sleep(delay)
            
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
            
            print("  ✅ Analysis received and parsed successfully")
            return analysis_result
            
        except Exception as e:
            last_error = e
            error_msg = str(e)
            
            # Check if it's a retryable error (network issues, timeouts, etc.)
            retryable_errors = [
                'incomplete chunked read',
                'connection',
                'timeout',
                'reset by peer',
                'temporarily unavailable',
                'overloaded',
                '529',  # Overloaded
                '503',  # Service unavailable
                '502',  # Bad gateway
            ]
            
            is_retryable = any(err in error_msg.lower() for err in retryable_errors)
            
            if is_retryable and attempt < MAX_RETRIES:
                print(f"  ⚠️ Attempt {attempt} failed: {error_msg}")
                print(f"  Will retry ({MAX_RETRIES - attempt} attempts remaining)...")
                continue
            else:
                print(f"  ❌ Error calling Claude API: {error_msg}")
                if attempt == MAX_RETRIES:
                    print(f"  ❌ All {MAX_RETRIES} retry attempts exhausted")
                break
    
    print(f"  ⚠️  Returning safe fallback - existing portfolio will be preserved")
    return _get_fallback_analysis()


def _format_analysis_prompt(analysis_input: Dict) -> str:
    """
    Format all analysis data into a structured prompt.
    OPTIMIZED: Uses compact CSV-style format to fit within 200k token limit.
    
    Args:
        analysis_input: Raw analysis data
    
    Returns:
        Formatted prompt string
    """
    sections = []
    
    # Current date - compact
    sections.append(f"DATE: {analysis_input.get('current_date', 'Unknown')}")
    
    # ==================== BIWEEKLY BUDGET - COMPACT ====================
    fresh_budget = BIWEEKLY_INVESTMENT_BUDGET
    sections.append(f"""
## BUDGET: ${fresh_budget:,} fresh capital to deploy
Task: 1) Review holdings→HOLD/TRIM/SELL 2) Deploy ${fresh_budget:,} into best opportunities""")
    
    # ==================== INVESTOR PROFILE - COMPACT ====================
    years_to_retirement = USER_PROFILE.get('years_to_retirement', 33)
    current_age = USER_PROFILE.get('current_age', 32)
    risk_tolerance = USER_PROFILE.get('risk_tolerance', 'high')
    investment_style = USER_PROFILE.get('investment_style', 'growth')
    stock_to_etf_ratio = USER_PROFILE.get('stock_to_etf_ratio', '70:30')
    
    sections.append(f"""
## INVESTOR: Age {current_age}, {years_to_retirement}yr to retire, {risk_tolerance.upper()} risk, {investment_style.upper()} style, {stock_to_etf_ratio} stocks:ETFs""")
    
    # Current Portfolio - COMPACT CSV FORMAT
    portfolio = analysis_input.get('current_portfolio', [])
    if portfolio:
        sections.append("\n## PORTFOLIO (ticker,entry,current,gain%,invested,target,stop,status)")
        for h in portfolio:
            investment_amount = h.get('investment_amount', 0)
            current_price = h.get('current_price') or 0
            entry_price = h.get('recommended_price') or 0
            gain_loss = h.get('gain_loss_pct') or 0
            target = h.get('price_target') or 0
            stop = h.get('stop_loss') or 0
            status = h.get('status') or 'HOLD'
            sections.append(f"{h.get('ticker')},{entry_price:.2f},{current_price:.2f},{gain_loss:+.1f}%,${investment_amount:.0f},{target:.2f},{stop:.2f},{status}")
    else:
        sections.append(f"## CURRENT PORTFOLIO: Empty - First run, deploy the full ${BIWEEKLY_INVESTMENT_BUDGET:,} budget!\n")
    
    # Historical Performance - COMPACT
    perf = analysis_input.get('performance_summary', {})
    sections.append(f"""
## TRACK RECORD: Return {(perf.get('total_return_pct', 0) or 0):.1f}% | S&P {(perf.get('sp500_total_return_pct', 0) or 0):.1f}% | Alpha {(perf.get('total_alpha_pct', 0) or 0):+.1f}% | Win {(perf.get('win_rate_pct', 0) or 0):.0f}%""")
    
    # Risk Management Status - COMPACT
    risk_metrics = analysis_input.get('risk_metrics', {})
    if risk_metrics:
        status = risk_metrics.get('risk_status', 'NORMAL')
        metrics = risk_metrics.get('metrics', {})
        rules = risk_metrics.get('rules', {})
        
        sections.append(f"""
## RISK: {status} | Drawdown {(metrics.get('drawdown_pct', 0) or 0):.1f}% | MaxPos {rules.get('max_position_size', 15)}% | MinCash {rules.get('min_cash', 5)}%""")
    
    # Closed Positions - COMPACT
    closed = analysis_input.get('closed_positions', [])
    if closed:
        sections.append("\n## CLOSED: " + " | ".join([f"{c.get('ticker')}:{c.get('return_pct', 0):+.1f}%" for c in closed[-5:]]))
    
    # Market Data - COMPACT
    market = analysis_input.get('market_data', {})
    
    # Indexes - single line
    if market.get('indexes'):
        idx_str = " | ".join([f"{n.split()[0]}:{d.get('returns', {}).get('1mo', 0) or 0:+.1f}%" for n, d in list(market['indexes'].items())[:4]])
        sections.append(f"\n## INDEXES: {idx_str}")
    
    # Sectors - compact
    if market.get('sectors'):
        sect_str = " | ".join([f"{s[:4]}:{d.get('returns', {}).get('1mo', 0) or 0:+.1f}%" for s, d in market['sectors'].items()])
        sections.append(f"## SECTORS: {sect_str}")
    
    # Commodities - COMPACT
    if market.get('commodities'):
        comm_str = " | ".join([f"{n}:${d.get('current', 0) or 0:.0f}({d.get('returns', {}).get('1mo', 0) or 0:+.0f}%)" for n, d in market['commodities'].items()])
        sections.append(f"## COMMODITIES: {comm_str}")
    
    # Growth/Thematic ETFs - COMPACT
    growth_etfs = market.get('growth_etfs', {})
    if growth_etfs:
        etf_parts = []
        for theme, etfs in growth_etfs.items():
            etf_data = list(etfs.values())
            if etf_data:
                best_etf = max(etf_data, key=lambda x: x.get('returns', {}).get('1mo', 0) or 0)
                ticker = [k for k, v in etfs.items() if v == best_etf][0]
                mo1 = best_etf.get('returns', {}).get('1mo', 0) or 0
                etf_parts.append(f"{theme[:6]}:{ticker}({mo1:+.0f}%)")
        sections.append(f"## THEMATIC ETFs: {' | '.join(etf_parts)}")
    
    # Macro - COMPACT
    macro = market.get('macro', {})
    if macro:
        vix = macro.get('vix', {})
        sections.append(f"## VIX: {vix.get('current', 'N/A')} ({vix.get('alert_level', 'NORMAL')})")
    
    # Market News - COMPACT (just headlines)
    market_news = market.get('market_news', [])
    if market_news:
        sections.append("\n## NEWS (top 8):")
        for news in market_news[:8]:
            title = news.get('title', '')[:80]
            sections.append(f"- {title}")
    
    # Historical context - COMPACT
    historical = market.get('historical_context', {})
    if historical:
        pe_context = historical.get('sp500_pe_context', {})
        if pe_context.get('current_pe'):
            sections.append(f"## S&P P/E: {pe_context.get('current_pe', 'N/A')} (avg {pe_context.get('historical_avg', 17)}, {pe_context.get('assessment', 'unknown')})")
    
    # Earnings Calendar - COMPACT
    earnings = analysis_input.get('earnings_calendar', {})
    if earnings:
        earn_str = " ".join([f"{t}:{d.get('days_until', '?')}d" for t, d in list(earnings.items())[:15]])
        sections.append(f"## EARNINGS SOON: {earn_str}")
    
    # Screen Results - COMPACT CSV FORMAT
    screens = analysis_input.get('screen_results', {})
    
    sections.append("\n## SCREENS (USE THESE REAL PRICES)")
    
    if screens.get('momentum'):
        # GAINERS: ticker:$price(+ret%)
        gainers = screens['momentum'].get('top_gainers', [])
        if gainers:
            g_str = " ".join([f"{g.get('ticker')}:${g.get('current_price', 0) or 0:.0f}({g.get('return_pct', 0) or 0:+.0f}%)" for g in gainers])
            sections.append(f"GAINERS: {g_str}")
        
        # LOSERS
        losers = screens['momentum'].get('top_losers', [])
        if losers:
            l_str = " ".join([f"{l.get('ticker')}:${l.get('current_price', 0) or 0:.0f}({l.get('return_pct', 0) or 0:+.0f}%)" for l in losers])
            sections.append(f"LOSERS: {l_str}")
        
        # 52W HIGHS
        breakouts = screens['momentum'].get('52w_high_breakouts', [])
        if breakouts:
            b_str = " ".join([f"{b.get('ticker')}:${b.get('current_price', 0) or 0:.0f}" for b in breakouts])
            sections.append(f"52W_HIGHS: {b_str}")
        
        # 52W LOWS
        bounces = screens['momentum'].get('52w_low_bounces', [])
        if bounces:
            bo_str = " ".join([f"{b.get('ticker')}:${b.get('current_price', 0) or 0:.0f}" for b in bounces])
            sections.append(f"52W_LOWS: {bo_str}")
        
        # UNUSUAL VOLUME
        volume = screens['momentum'].get('unusual_volume', [])
        if volume:
            v_str = " ".join([f"{v.get('ticker')}:${v.get('current_price', 0) or 0:.0f}({v.get('volume_ratio', 0) or 0:.0f}x)" for v in volume])
            sections.append(f"HIGH_VOL: {v_str}")
    
    if screens.get('fundamental'):
        # VALUE: ticker:$price,PE,EPS%
        value = screens['fundamental'].get('value_stocks', [])
        if value:
            val_str = " ".join([f"{v.get('ticker')}:${v.get('current_price', 0) or 0:.0f},PE{v.get('pe_ratio', 0) or 0:.0f},E{v.get('earnings_growth', 0) or 0:+.0f}%" for v in value])
            sections.append(f"VALUE: {val_str}")
        
        # GROWTH: ticker:$price,Rev%,EPS%,PEG
        growth = screens['fundamental'].get('growth_stocks', [])
        if growth:
            gr_str = " ".join([f"{g.get('ticker')}:${g.get('current_price', 0) or 0:.0f},R{g.get('revenue_growth', 0) or 0:+.0f}%,E{g.get('earnings_growth', 0) or 0:+.0f}%,PEG{g.get('peg_ratio', 0) or 0:.1f}" for g in growth])
            sections.append(f"GROWTH: {gr_str}")
        
        # GARP stocks
        garp = screens['fundamental'].get('garp_stocks', [])
        if garp:
            garp_str = " ".join([f"{g.get('ticker')}:${g.get('current_price', 0) or 0:.0f},PEG{g.get('peg_ratio', 0) or 0:.1f}" for g in garp])
            sections.append(f"GARP: {garp_str}")
        
        # DIVIDEND: ticker:$price,Yield%
        dividend = screens['fundamental'].get('dividend_stocks', [])
        if dividend:
            div_str = " ".join([f"{d.get('ticker')}:${d.get('current_price', 0) or 0:.0f},Y{d.get('dividend_yield', 0) or 0:.1f}%" for d in dividend])
            sections.append(f"DIVIDEND: {div_str}")
    
    if screens.get('technical'):
        # OVERSOLD: ticker:$price,RSI
        oversold = screens['technical'].get('oversold', [])
        if oversold:
            os_str = " ".join([f"{o.get('ticker')}:${o.get('current_price', 0) or 0:.0f},RSI{o.get('rsi', 0) or 0:.0f}" for o in oversold])
            sections.append(f"OVERSOLD: {os_str}")
        
        # OVERBOUGHT
        overbought = screens['technical'].get('overbought', [])
        if overbought:
            ob_str = " ".join([f"{o.get('ticker')}:${o.get('current_price', 0) or 0:.0f},RSI{o.get('rsi', 0) or 0:.0f}" for o in overbought])
            sections.append(f"OVERBOUGHT: {ob_str}")
        
        # GOLDEN CROSSES
        golden = screens['technical'].get('golden_crosses', [])
        if golden:
            gc_str = " ".join([f"{g.get('ticker')}:${g.get('current_price', 0) or 0:.0f}" for g in golden])
            sections.append(f"GOLDEN_CROSS: {gc_str}")
        
        # DEATH CROSSES
        death = screens['technical'].get('death_crosses', [])
        if death:
            dc_str = " ".join([f"{d.get('ticker')}:${d.get('current_price', 0) or 0:.0f}" for d in death])
            sections.append(f"DEATH_CROSS: {dc_str}")
    
    # CRYPTOCURRENCY SCREENS
    if screens.get('crypto'):
        sections.append("\n## CRYPTO UNIVERSE (diversify 10-20% of budget into crypto)")
        
        # All crypto - send ALL without trimming, sorted by market cap
        # Format: ticker:$price(change%),MCap$XB - compact but complete
        all_crypto = screens['crypto'].get('all', [])
        if all_crypto:
            # Send ALL crypto - no trimming, similar to how stocks are sent
            crypto_str = " ".join([
                f"{c.get('ticker')}:${c.get('current_price', 0) or 0:.2f}({c.get('change_pct', 0) or 0:+.1f}%),M${c.get('market_cap', 0) / 1e9 if c.get('market_cap') else 0:.0f}B"
                for c in all_crypto
            ])
            sections.append(f"CRYPTO({len(all_crypto)}): {crypto_str}")
    
    # CRYPTO MARKET SENTIMENT - COMPACT
    crypto_sentiment = analysis_input.get('crypto_sentiment', {})
    if crypto_sentiment:
        parts = []
        
        # Fear & Greed Index
        fg = crypto_sentiment.get('fear_greed', {})
        if fg:
            parts.append(f"F&G:{fg.get('value', 0)}({fg.get('classification', 'Unknown')})")
        
        # BTC Dominance
        btc_dom = crypto_sentiment.get('btc_dominance')
        if btc_dom:
            parts.append(f"BTC_DOM:{btc_dom}%")
        
        # Total Market Cap
        total_mcap = crypto_sentiment.get('total_crypto_mcap', 0)
        if total_mcap:
            parts.append(f"TOTAL_MCAP:${total_mcap/1e12:.2f}T")
        
        if parts:
            sections.append(f"CRYPTO_SENTIMENT: {' | '.join(parts)}")
        
        # Top Crypto Metrics (compact: BTC:$97k,50d$88k,200d$103k,ATH$126k(-23%))
        top_metrics = crypto_sentiment.get('top_crypto_metrics', {})
        if top_metrics:
            metrics_parts = []
            for ticker, m in top_metrics.items():
                short_ticker = ticker.replace('-USD', '')
                price = m.get('price', 0)
                d50 = m.get('fifty_day_avg', 0)
                d200 = m.get('two_hundred_day_avg', 0)
                ath = m.get('all_time_high', 0)
                pct_ath = m.get('pct_from_ath', 0)
                
                # Format price smartly (k for thousands, no decimal for large)
                def fmt_price(p):
                    if p >= 1000:
                        return f"${p/1000:.0f}k"
                    elif p >= 1:
                        return f"${p:.0f}"
                    else:
                        return f"${p:.4f}"
                
                metrics_parts.append(f"{short_ticker}:{fmt_price(price)},50d{fmt_price(d50)},200d{fmt_price(d200)},ATH{fmt_price(ath)}({pct_ath:+.0f}%)")
            
            sections.append(f"CRYPTO_METRICS: {' | '.join(metrics_parts)}")
    
    # Politician Trades - COMPACT
    pol_trades = analysis_input.get('politician_trades', [])
    flagged = analysis_input.get('flagged_trades', [])
    
    if pol_trades:
        sections.append(f"\n## POLITICIAN TRADES ({len(pol_trades)} trades)")
        # Compact: Name(Party) Action TICKER $Amount
        for t in pol_trades[:15]:
            sections.append(f"{t.get('politician', '?')}({t.get('party', '?')}) {t.get('transaction_type', '?')} {t.get('ticker', '?')} {t.get('amount', '?')}")
        
        if flagged:
            sections.append(f"FLAGGED: " + " | ".join([f"{f.get('politician')} {f.get('ticker')}" for f in flagged[:5]]))
    
    # Rule - COMPACT
    sections.append(f"\n## RULE: Max {ALLOCATION_RULES['single_stock_max']*100:.0f}% per stock. Beat S&P 500.")
    
    # Retail Investor Analysis Section - COMPACT
    retail = analysis_input.get('retail_analysis', {})
    if retail:
        sections.append("\n## RETAIL ANALYSIS")
        
        # Tax-Loss Harvesting - compact
        tlh = retail.get('tax_loss_harvesting', [])
        if tlh:
            tlh_str = " | ".join([f"{t.get('ticker')}:{t.get('loss_pct', 0) or 0:.0f}%loss" for t in tlh[:5]])
            sections.append(f"TLH: {tlh_str}")
        
        # Correlation - compact
        corr = retail.get('correlation_analysis', {})
        if corr.get('status') == 'SUCCESS':
            div_score = corr.get('diversification_score', 0) or 0
            high_corr = corr.get('high_correlation_pairs', [])
            corr_str = " ".join([f"{p['pair'][0]}/{p['pair'][1]}:{p['correlation']:.0%}" for p in high_corr[:3]])
            sections.append(f"CORRELATION: DivScore {div_score:.0f}/100 | HighCorr: {corr_str}")
        
        # Liquidity Warnings - compact
        liq_warnings = retail.get('liquidity_warnings', [])
        if liq_warnings:
            liq_str = " ".join([w.get('ticker') for w in liq_warnings[:5]])
            sections.append(f"LOW_LIQUIDITY: {liq_str}")
        
        # Short Interest - compact
        short = retail.get('short_interest', [])
        squeeze_candidates = [s for s in short if s.get('potential_squeeze')]
        if squeeze_candidates:
            sq_str = " ".join([f"{s.get('ticker')}:{s.get('short_pct_of_float', 0) or 0:.0f}%short" for s in squeeze_candidates[:3]])
            sections.append(f"SQUEEZE_CANDIDATES: {sq_str}")
        
        # Sector Rotation - compact
        rotation = retail.get('sector_rotation', {})
        if rotation.get('status') == 'SUCCESS':
            sections.append(f"ROTATION: {rotation.get('current_phase', '?')} | Buy: {','.join(rotation.get('recommended_sectors', [])[:3])} | Avoid: {','.join(rotation.get('sectors_to_avoid', [])[:2])}")
    
    # Historical Financials Section - ULTRA COMPACT
    # Format: TICKER:Rev[y1,y2,y3,y4]|EPS[y1,y2,y3,y4]|Growth[g1,g2,g3]
    hist_fin = analysis_input.get('historical_financials', {})
    if hist_fin:
        sections.append(f"\n## HISTORICAL FINANCIALS ({len(hist_fin)} tickers)")
        sections.append("Format: TICKER Rev[B]→→→→ | EPS[$]→→→→ | Growth[%]→→→")
        
        for ticker, data in hist_fin.items():
            periods = data.get('periods', [])
            if not periods:
                continue
            
            # Build compact string
            parts = [ticker]
            
            # Revenue (in billions, rounded)
            rev = data.get('revenue_history', [])
            if rev and any(r is not None for r in rev):
                rev_vals = ','.join([f"{r:.0f}" if r else "-" for r in rev])
                parts.append(f"R[{rev_vals}]")
            
            # EPS
            eps = data.get('eps_history', [])
            if eps and any(e is not None for e in eps):
                eps_vals = ','.join([f"{e:.2f}" if e else "-" for e in eps])
                parts.append(f"E[{eps_vals}]")
            
            # Revenue growth
            growth = data.get('revenue_growth_trend', [])
            if growth and any(g is not None for g in growth):
                gr_vals = ','.join([f"{g:+.0f}" if g else "-" for g in growth])
                parts.append(f"G[{gr_vals}]")
            
            if len(parts) > 1:
                sections.append(" ".join(parts))
    
    # Crypto Historical Performance Section - COMPACT
    # Format: TICKER:1y%|2y%|3y%|ATH$|fromATH%
    crypto_hist = analysis_input.get('crypto_historical', {})
    if crypto_hist:
        sections.append(f"\n## CRYPTO HISTORICAL PERFORMANCE ({len(crypto_hist)} tokens)")
        sections.append("Format: TICKER 1y%|2y%|3y%|ATH$|fromATH% [yearly returns]")
        
        for ticker, data in crypto_hist.items():
            if not data:
                continue
            
            returns = data.get('returns', {})
            parts = [ticker.replace('-USD', '')]  # Shorten ticker
            
            # Period returns
            ret_parts = []
            for period in ['1y', '2y', '3y']:
                ret = returns.get(period)
                if ret is not None:
                    ret_parts.append(f"{period}:{ret:+.0f}%")
            if ret_parts:
                parts.append(" ".join(ret_parts))
            
            # ATH info
            ath = data.get('all_time_high')
            from_ath = data.get('from_ath_pct')
            if ath and from_ath is not None:
                parts.append(f"ATH${ath:.0f}({from_ath:+.0f}%)")
            
            # Yearly performance (last 3 years)
            yearly = data.get('yearly_performance', [])[:3]
            if yearly:
                yearly_str = " ".join([f"{y['year']}:{y['return_pct']:+.0f}%" for y in yearly])
                parts.append(f"[{yearly_str}]")
            
            if len(parts) > 1:
                sections.append(" ".join(parts))
    
    # Final instruction - COMPACT
    sections.append("""
## TASK: 1)Review holdings 2)10-15 new picks 3)Use real prices above 4)JSON response""")
    
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
