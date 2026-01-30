"""
Configuration and constants for the Stock Insight Agent.
"""

# API Configuration
CLAUDE_MODEL = "claude-opus-4-5-20251101"  # Claude Opus 4.5 - maximum intelligence
CLAUDE_MAX_TOKENS = 16000
CLAUDE_THINKING_BUDGET = 10000  # Extended thinking budget for deeper analysis

# Market Indexes to Track (using ETFs for better data availability)
INDEXES = {
    "S&P 500": "SPY",
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

# Commodity & Metal ETFs
COMMODITIES = {
    "Gold": ["GLD", "IAU", "GDX", "NEM", "GOLD", "AEM"],
    "Silver": ["SLV", "AG", "WPM", "PAAS"],
    "Copper": ["COPX", "FCX"],
    "Platinum": ["PPLT"],
    "Oil": ["USO", "XLE", "XOM", "CVX", "OXY"],
    "Natural Gas": ["UNG", "BOIL"],
    "Agriculture": ["DBA", "MOO", "DE", "ADM", "MOS"]
}

# Fixed Income ETFs
FIXED_INCOME = {
    "Short Treasury": ["SHY", "BIL", "SGOV"],
    "Long Treasury": ["TLT", "ZROZ"],
    "Corporate": ["LQD", "VCIT"],
    "High Yield": ["HYG", "JNK"],
    "TIPS": ["TIP", "SCHP"]
}

# International ETFs
INTERNATIONAL = {
    "Developed": ["VEA", "EFA", "IEFA"],
    "Emerging": ["VWO", "EEM", "IEMG"],
    "Europe": ["VGK", "EZU"],
    "Japan": ["EWJ"],
    "China": ["FXI", "MCHI", "KWEB"]
}

# Diversification Rules (MUST ENFORCE)
ALLOCATION_RULES = {
    "single_stock_max": 0.20,          # 20% max any single stock
    "single_sector_max": 0.35,         # 35% max any single sector
    "min_positions": 5,
    "max_positions": 15,
    
    # By Asset Class
    "us_stocks": {"min": 0.40, "max": 0.70},
    "international": {"min": 0.05, "max": 0.20},
    "metals_commodities": {"min": 0.05, "max": 0.15},
    "bonds_cash": {"min": 0.10, "max": 0.25},
    "reits": {"min": 0.00, "max": 0.10},
    "crypto": {"min": 0.00, "max": 0.05},
    
    # By Investment Style
    "growth": {"min": 0.20, "max": 0.40},
    "value": {"min": 0.20, "max": 0.40},
    "dividend": {"min": 0.10, "max": 0.30},
    "speculative": {"min": 0.00, "max": 0.10},
    "hedge": {"min": 0.05, "max": 0.15},
    
    # By Time Horizon
    "short_term": {"min": 0.10, "max": 0.25},
    "medium_term": {"min": 0.40, "max": 0.60},
    "long_term": {"min": 0.25, "max": 0.40},
    
    # By Risk Level
    "conservative": {"min": 0.30, "max": 0.40},
    "moderate": {"min": 0.40, "max": 0.50},
    "aggressive": {"min": 0.10, "max": 0.30},
    
    # By Geography
    "us": {"min": 0.60, "max": 0.80},
    "developed_intl": {"min": 0.10, "max": 0.25},
    "emerging": {"min": 0.05, "max": 0.15}
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

# Risk Levels for Position Sizing
RISK_LEVELS = {
    "conservative": {
        "max_position_size": 0.12,
        "stop_loss_pct": 0.10,
        "target_gain_pct": 0.15
    },
    "moderate": {
        "max_position_size": 0.15,
        "stop_loss_pct": 0.15,
        "target_gain_pct": 0.25
    },
    "aggressive": {
        "max_position_size": 0.20,
        "stop_loss_pct": 0.20,
        "target_gain_pct": 0.40
    }
}

# Technical Analysis Parameters
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

# Data Sources
DATA_SOURCES = {
    "market_data": "yfinance",
    "politician_trades": "quiver_quantitative",
    "fundamentals": "yfinance",
    "news": "yfinance"
}

# Email Configuration
EMAIL_CONFIG = {
    "subject_prefix": "📊 Monthly Stock Recommendations",
    "max_retries": 3,
    "retry_delay_seconds": 5
}

# File Paths
PATHS = {
    "portfolio_history": "data/portfolio_history.json",
    "email_template": "templates/email_template.html"
}
