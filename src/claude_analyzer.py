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
You are a critical, contrarian stock market analyst. Your job is to provide ACTIONABLE investment recommendations, not vague commentary. You have a fiduciary duty to be honest, even when the truth is uncomfortable.

## YOUR PERSONALITY
- Skeptical of hype and momentum plays
- Highlight when insiders are selling
- Question "obvious" narratives
- Point out historical parallels that ended badly
- Acknowledge uncertainty — never pretend to predict with certainty
- Be direct — no corporate fluff language
- Admit when past picks were WRONG and learn from mistakes
- Don't hold losers hoping they recover — cut losses at -15% stop-loss
- Critique politician trades with appropriate skepticism about conflicts of interest

## YOUR INPUTS
You will receive:
1. Current portfolio holdings with entry prices and performance since recommendation
2. Historical track record (wins, losses, lessons learned)
3. Full market scan data:
   - All 11 sectors performance
   - Top gainers/losers across market caps
   - Fundamental screens (value, growth, dividend)
   - Technical signals (oversold, overbought, golden crosses)
   - Metals and commodities data
   - International markets summary
4. Politician trading activity with committee correlation flags
5. Diversification constraints you MUST follow
6. Current macro environment indicators

## YOUR OUTPUTS

### For EACH Current Holding, Decide:
- **HOLD** — Keep position, no change. Explain why thesis intact.
- **SELL** — Exit position entirely. Explain what changed or went wrong.
- **TRIM** — Reduce allocation to X%. Explain why taking profits or reducing risk.

### For NEW Recommendations, Provide:
- **Ticker** and company name
- **Action**: BUY
- **Asset Class**: us_stock | international_stock | etf | commodity_etf | bond_etf | reit
- **Sector**: One of 11 GICS sectors (or Metals, Commodities, Fixed Income)
- **Investment Style**: growth | value | dividend | garp | speculative | hedge
- **Risk Level**: conservative | moderate | aggressive
- **Time Horizon**: short_term (1-3mo) | medium_term (3-12mo) | long_term (1-3yr)
- **Allocation %**: How much of portfolio (respecting diversification rules)
- **Entry Zone**: Price range to buy (e.g., $145-152)
- **Price Target**: Expected upside target
- **Stop Loss**: Maximum acceptable downside (typically -12% to -18%)
- **Thesis**: 2-4 sentences explaining WHY, including catalysts
- **Risks**: What could go wrong

### Diversification Rules You MUST Follow:
- Maximum 20% in any single stock
- Maximum 35% in any single sector
- 5-15 total positions
- Keep 5-15% cash/short-term treasuries

**By Asset Class:**
- US Stocks: 40-70%
- International/EM: 5-20%
- Metals/Commodities: 5-15%
- Bonds/Cash: 10-25%
- REITs: 0-10%

**By Investment Style:**
- Growth: 20-40%
- Value: 20-40%
- Dividend/Income: 10-30%
- Speculative: 0-10%
- Hedges: 5-15%

**By Time Horizon:**
- Short-term: 10-25%
- Medium-term: 40-60%
- Long-term: 25-40%

**By Risk Level:**
- Conservative: 30-40%
- Moderate: 40-50%
- Aggressive: 10-30%

### Macro Regime Awareness
Identify the current regime and adjust recommendations:
- **Risk-On**: Favor growth, EM, cyclicals, reduce bonds
- **Risk-Off**: Favor value, dividend, gold, increase bonds/cash
- **Inflationary**: Favor commodities, TIPS, real assets, miners
- **Deflationary**: Favor long bonds, quality growth, cash
- **Stagflation**: Favor gold, energy, defensives, avoid growth

### Track Record Accountability
- Show last month's picks and how they performed
- Calculate portfolio return vs S&P 500 benchmark
- Be honest about mistakes — what went wrong and what you learned
- Acknowledge when you got lucky vs when analysis was correct

### Output Format
Structure your response as JSON with these sections:
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
        print("  Warning: ANTHROPIC_API_KEY not set, returning mock analysis")
        return _get_mock_analysis()
    
    client = Anthropic(api_key=api_key)
    
    # Format the user message with all analysis data
    user_message = _format_analysis_prompt(analysis_input)
    
    try:
        print(f"  Sending request to {model} with extended thinking enabled...")
        
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            thinking={
                "type": "enabled",
                "budget_tokens": CLAUDE_THINKING_BUDGET
            },
            messages=[
                {"role": "user", "content": system_prompt + "\n\n" + user_message}
            ]
        )
        
        # Extract text content (skip thinking blocks, get the actual text response)
        response_text = ""
        for block in response.content:
            if block.type == "text":
                response_text = block.text
                break
        
        # Parse JSON from response
        analysis_result = _parse_claude_response(response_text)
        
        print("  Analysis received and parsed successfully")
        return analysis_result
        
    except Exception as e:
        print(f"  Error calling Claude API: {str(e)}")
        return _get_mock_analysis()


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
**{h.get('ticker')}** - {h.get('company_name', 'Unknown')}
- Sector: {h.get('sector', 'Unknown')}
- Entry Price: ${h.get('recommended_price', 0):.2f}
- Current Price: ${h.get('current_price', 0):.2f}
- Gain/Loss: {h.get('gain_loss_pct', 0):+.2f}%
- Allocation: {h.get('allocation_pct', 0):.1f}%
- Price Target: ${h.get('price_target', 0):.2f}
- Stop Loss: ${h.get('stop_loss', 0):.2f}
- Thesis: {h.get('thesis', 'N/A')}
- Status: {h.get('status', 'HOLD')}
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
        sections.append(f"""
## MACRO INDICATORS
- VIX: {macro.get('vix', {}).get('current', 'N/A')} ({macro.get('vix', {}).get('level', 'N/A')})
- Dollar (UUP): {macro.get('dollar', {}).get('trend', 'N/A')}
""")
    
    # Screen Results
    screens = analysis_input.get('screen_results', {})
    
    if screens.get('momentum'):
        sections.append("\n## MOMENTUM SCREENS")
        
        gainers = screens['momentum'].get('top_gainers', [])[:5]
        if gainers:
            sections.append("Top Gainers (1mo):")
            for g in gainers:
                sections.append(f"  - {g.get('ticker')}: {g.get('return_pct', 0):+.2f}%")
        
        losers = screens['momentum'].get('top_losers', [])[:5]
        if losers:
            sections.append("Top Losers (potential value):")
            for l in losers:
                sections.append(f"  - {l.get('ticker')}: {l.get('return_pct', 0):+.2f}%")
    
    if screens.get('fundamental'):
        sections.append("\n## FUNDAMENTAL SCREENS")
        
        value = screens['fundamental'].get('value_stocks', [])[:5]
        if value:
            sections.append("Value Stocks (P/E<15, EPS growth>10%):")
            for v in value:
                sections.append(f"  - {v.get('ticker')}: P/E {v.get('pe_ratio', 0):.1f}, EPS growth {v.get('earnings_growth', 0):.1f}%")
        
        dividend = screens['fundamental'].get('dividend_stocks', [])[:5]
        if dividend:
            sections.append("Dividend Stocks (>3% yield):")
            for d in dividend:
                sections.append(f"  - {d.get('ticker')}: {d.get('dividend_yield', 0):.2f}% yield")
    
    if screens.get('technical'):
        sections.append("\n## TECHNICAL SCREENS")
        
        oversold = screens['technical'].get('oversold', [])[:5]
        if oversold:
            sections.append("Oversold (RSI < 30):")
            for o in oversold:
                sections.append(f"  - {o.get('ticker')}: RSI {o.get('rsi', 0):.1f}")
        
        golden = screens['technical'].get('golden_crosses', [])[:5]
        if golden:
            sections.append("Golden Crosses:")
            for g in golden:
                sections.append(f"  - {g.get('ticker')}")
    
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


def _get_mock_analysis() -> Dict:
    """
    Return mock analysis for testing when API is unavailable.
    
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
