"""
Configuration and constants for the Stock Insight Agent.
"""

from datetime import datetime

# =============================================================================
# USER PROFILE - AGGRESSIVE GROWTH INVESTOR
# =============================================================================

_BIRTH_YEAR = 1994
_CURRENT_YEAR = datetime.now().year
_CURRENT_AGE = _CURRENT_YEAR - _BIRTH_YEAR
_RETIREMENT_AGE = 65

USER_PROFILE = {
    "current_age": _CURRENT_AGE,
    "retirement_age": _RETIREMENT_AGE,
    "years_to_retirement": max(1, _RETIREMENT_AGE - _CURRENT_AGE),
    
    # Financial situation - debt-free, ready to invest aggressively
    "financial_situation": "strong",   # no debts, emergency fund covered, 401k separate
    "focus": "aggressive_growth",      # maximize long-term returns, can tolerate volatility
    "risk_tolerance": "high",          # comfortable with 30-40% drawdowns
    "investment_style": "growth",      # growth stocks over value/dividend
    
    # Portfolio preferences
    "prefer_individual_stocks": True,  # prioritize stock picks over ETFs
    "stock_to_etf_ratio": "70:30",     # 70% individual stocks, 30% ETFs
    "include_small_caps": True,        # open to emerging companies
    "include_international": True,     # global diversification welcome
}

# API Configuration
CLAUDE_MODEL = "claude-opus-4-5-20251101"  # Claude Opus 4.5 - maximum intelligence
CLAUDE_MAX_TOKENS = 32000  # Must be greater than thinking budget
CLAUDE_THINKING_BUDGET = 20000  # Extended thinking budget for deeper analysis of 500+ stocks
# Market Indexes to Track (using ETFs for better data availability)
INDEXES = {
    "S&P 500 (SPY)": "SPY",
    "S&P 500 (VOO)": "VOO",       # Added - most popular retail ETF
    "Total Market": "VTI",        # Added - Vanguard Total Stock Market
    "Nasdaq 100": "QQQ",
    "Dow Jones": "DIA",
    "Russell 2000": "IWM",
    "S&P 400 Mid Cap": "MDY",
    "S&P 600 Small Cap": "IJR"
}

# All 11 GICS Sectors with ETF proxies
SECTORS = {
    "Technology": {"etf": "XLK", "keywords": ["software", "semiconductor", "hardware", "IT"]},
    "Healthcare": {"etf": "XLV", "keywords": ["pharma", "biotech", "medical", "hospital"]},
    "Financials": {"etf": "XLF", "keywords": ["bank", "insurance", "asset management"]},
    "Energy": {"etf": "XLE", "keywords": ["oil", "gas", "pipeline", "refiner"]},
    "Consumer Discretionary": {"etf": "XLY", "keywords": ["retail", "auto", "restaurant", "travel"]},
    "Consumer Staples": {"etf": "XLP", "keywords": ["food", "beverage", "household"]},
    "Industrials": {"etf": "XLI", "keywords": ["aerospace", "defense", "machinery", "transport"]},
    "Materials": {"etf": "XLB", "keywords": ["chemical", "mining", "steel", "paper"]},
    "Utilities": {"etf": "XLU", "keywords": ["electric", "gas utility", "water"]},
    "Real Estate": {"etf": "XLRE", "keywords": ["REIT", "property"]},
    "Communication Services": {"etf": "XLC", "keywords": ["telecom", "media", "entertainment"]}
}

# =============================================================================
# ASSET CLASS TRACKING
# =============================================================================
# Stock Universe: 100% DYNAMIC via Yahoo Finance EquityQuery API
#   - Screens 1,500+ stocks by market cap and sector in real-time
#   - No hardcoded stock lists
#
# ETF Detection: DYNAMIC via yfinance quoteType
#   - yfinance Ticker.info['quoteType'] returns 'ETF' or 'EQUITY'
#   - No hardcoded ETF lists needed
#   - ETFs are automatically filtered out from earnings calendar

# =============================================================================
# BIWEEKLY INVESTMENT BUDGET
# =============================================================================
# This is the fresh money available to invest each biweekly run.
# It represents NEW capital on top of existing investments.
# Existing holdings should be evaluated for HOLD/SELL.
# New recommendations should only spend this fresh budget.
BIWEEKLY_INVESTMENT_BUDGET = 1000  # $1,000 fresh investment each run

# =============================================================================
# GUARDRAILS - Minimal. Let Claude be the advisor.
# =============================================================================
ALLOCATION_RULES = {
    "single_stock_max": 0.15,    # Max 15% in one stock (prevent single-stock blowup)
}

# Politician Committee Mappings (for conflict of interest detection)
COMMITTEE_SECTOR_MAP = {
    "Armed Services": ["Industrials", "Aerospace", "Defense"],
    "Finance": ["Financials", "Banking", "Insurance"],
    "Banking": ["Financials", "Banking", "Fintech"],
    "Health": ["Healthcare", "Pharma", "Biotech"],
    "Energy": ["Energy", "Oil", "Gas", "Renewables"],
    "Commerce": ["Technology", "Consumer", "Telecom"],
    "Judiciary": ["Technology", "Big Tech"],
    "Agriculture": ["Agriculture", "Food", "Consumer Staples"],
    "Transportation": ["Industrials", "Airlines", "Shipping"],
    "Science": ["Technology", "Aerospace", "Biotech"],
    "Intelligence": ["Defense", "Technology", "Cybersecurity"],
    "Ways and Means": ["Financials", "Healthcare", "All Sectors"],
    "Appropriations": ["All Sectors"]
}

# Stock Universe is now fetched DYNAMICALLY from ETF holdings
# See data_fetcher.get_dynamic_stock_universe() for implementation
# This ensures we always have current, valid tickers without manual updates

# =============================================================================
# TECHNICAL ANALYSIS PARAMETERS
# =============================================================================
# These are standard technical indicator settings (RSI periods, moving averages)
# NOT investment decisions - Claude uses these for calculations only
TECHNICAL_PARAMS = {
    "rsi_oversold": 30,
    "rsi_overbought": 70,
    "rsi_period": 14,
    "sma_short": 50,
    "sma_long": 200,
    "volume_spike_threshold": 3.0,  # 3x average volume
    "atr_period": 14
}

# Fundamental Screening Thresholds
FUNDAMENTAL_PARAMS = {
    "value_pe_max": 15,
    "value_earnings_growth_min": 0.10,
    "growth_revenue_growth_min": 0.20,
    "dividend_yield_min": 0.03,
    "dividend_payout_max": 0.60,
    "insider_buying_min_transactions": 3,
    "insider_buying_window_days": 30,
    "earnings_surprise_threshold": 0.10
}

# Email Configuration
EMAIL_CONFIG = {
    "subject_prefix": "📊 Monthly Stock Recommendations",
    "max_retries": 3,
    "retry_delay_seconds": 5,
    "initial_backoff_seconds": 5,
    "max_backoff_seconds": 60
}

# File Paths
PATHS = {
    "portfolio_history": "data/portfolio_history.json",
    "email_template": "templates/email_template.html"
}


