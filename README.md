# 📊 Stock Insight Agent

AI-powered **bi-weekly** stock analysis with portfolio memory, politician trade tracking, risk management, and actionable recommendations designed specifically for **retail investors**.

## 💰 Biweekly Fresh Budget System

Every time the agent runs, you invest **$1,000 fresh money** on top of your existing holdings:

| Category | Budget | Actions |
|----------|--------|---------|
| **Existing Holdings** | Already invested | HOLD / SELL / TRIM / ADD |
| **New Picks** | Fresh $1,000 | BUY new positions |

### How It Works

1. **Fresh Money Each Run**: You add $1,000 new capital every 2 weeks
2. **Review Existing Holdings**: Claude analyzes your current positions and recommends:
   - **HOLD** — Keep the position as-is
   - **SELL** — Exit completely (take profits or cut losses)
   - **TRIM** — Reduce position size (e.g., sell 50%)
   - **ADD** — Double down using fresh budget money
3. **Allocate New Budget**: The fresh $1,000 is distributed across:
   - New stock picks (never owned before)
   - Adding to existing winners (ADD action)
4. **10-15 Stock Recommendations**: Claude provides diversified picks across sectors and risk levels

### Example Allocation

```
Fresh Budget: $1,000 (spread across 10-15 positions)
├── NVDA (Core position): $150
├── GOOGL (Core position): $125
├── PLTR (Growth play): $100
├── AMD (Growth play): $100
├── SOFI (Mid-cap momentum): $75
├── XLK (Sector ETF): $75
├── MSTR (Speculative): $75
├── CELH (Speculative): $75
├── IONQ (Speculative AI): $50
├── RKLB (Small-cap growth): $50
├── ARKG (Thematic ETF): $50
└── DNA (Moonshot): $75
```

### ADD (Double Down) Support

When Claude recommends "ADD" on an existing position:
- Uses money from your fresh $1,000 budget
- Tracks weighted average cost basis
- Maintains complete add history with dates and amounts

### Configuration

Set your biweekly budget in `src/config.py`:

```python
BIWEEKLY_INVESTMENT_BUDGET = 1000  # Fresh money to invest each run
```

## ✨ Features

### Core Analysis
- **100% Dynamic Stock Universe**: Zero hardcoded stock lists - Yahoo Finance EquityQuery API screens 1,500+ stocks in real-time by market cap and sector
- **Dynamic ETF Detection**: ETFs automatically identified via yfinance `quoteType` - no hardcoded ETF lists
- **Full Market Coverage**: All 11 GICS sectors, mega-to-nano cap ($100M+), commodities, fixed income, international markets
- **Real-Time Prices**: All prices sourced from yfinance - never uses stale training data
- **10-15 Recommendations Per Run**: Diversified picks across sectors, risk levels, and market caps
- **Portfolio Memory**: Tracks recommendations over time, calculates performance, learns from past trades
- **Risk Management**: Industry-standard drawdown protection with automatic defensive modes
- **Stop-Loss & Target Alerts**: Automatic detection when positions hit stop-loss or price targets
- **Allocation Validation**: Auto-validates Claude's recommendations against allocation rules
- **API Resilience**: Automatic retry with exponential backoff (3 retries) for network reliability

### Retail Investor Focus 💰
- **Tax-Loss Harvesting Detection**: Identifies positions for tax-efficient selling with replacement suggestions
- **Portfolio Correlation Analysis**: Detects hidden concentration risks between correlated holdings
- **Liquidity Warnings**: Flags illiquid stocks with high bid-ask spreads
- **Trailing Stop Management**: Dynamic stop-loss recommendations to lock in profits
- **Short Squeeze Detection**: Identifies potential squeeze candidates with high short interest
- **Position Sizing Guidance**: Clear dollar amounts and share counts based on portfolio size
- **Sector Rotation Timing**: Phase-aware sector recommendations (early/mid/late cycle)
- **Fee Impact Analysis**: Warns about high expense ratio ETFs

### Market Intelligence
- **Dividend Calendar**: Tracks ex-dividend dates for portfolio holdings (14-day lookahead)
- **Earnings Calendar**: Tracks upcoming earnings for portfolio and watchlist stocks
- **Politician Tracking**: Monitors congressional trades from Capitol Trades (90-day lookback), flags suspicious timing
- **News Sentiment**: AI-analyzed sentiment via Alpha Vantage - fetched AFTER stock selection to avoid bias
- **Geopolitical News Integration**: Factors trade tensions, sanctions, and policy changes into analysis

### Email Report
- **Dark Mode Design**: Professional HTML reports optimized for both light and dark mode email clients
- **First-Run Welcome**: Special onboarding section for new users
- **Current Holdings Dashboard**: Real-time P&L with status indicators for each position
- **Action Plan with Dollar Amounts**: Clear "invest $X in Y shares" guidance
- **Performance Attribution**: Shows which positions moved your portfolio
- **Recent Closed Positions**: Shows last 10 trades (sells & trims) with returns, hold period, reasons, and lessons learned

## 📁 Project Structure

```
StockInsight/
├── .github/
│   └── workflows/
│       └── biweekly-analysis.yml    # Runs every 2 weeks
├── data/
│   └── portfolio_history.json       # Portfolio state & history
├── output/
│   └── *.html                       # Generated email previews
├── src/
│   ├── __init__.py
│   ├── main.py                      # Entry point & orchestration
│   ├── config.py                    # Configuration and constants
│   ├── data_fetcher.py              # Market data via yfinance
│   ├── market_scanner.py            # Full market screening (1500+ stocks)
│   ├── politician_tracker.py        # Capitol Trades scraper
│   ├── history_manager.py           # Portfolio memory & risk management
│   ├── news_sentiment.py            # Alpha Vantage sentiment analysis
│   ├── retail_advisor.py            # Retail-specific analysis (NEW)
│   ├── claude_analyzer.py           # Claude Opus 4.5 integration
│   ├── email_builder.py             # Dark-mode HTML email builder
│   └── email_sender.py              # Resend API integration
├── templates/
│   └── email_template.html          # Legacy template (unused)
├── requirements.txt
├── .env.example
└── README.md
```

## 🚀 Setup

### 1. Clone and Install

```bash
# Clone this repo
git clone <your-repo-url>
cd stock-insight-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your API keys
```

**Required Environment Variables:**
| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Claude API key from console.anthropic.com |
| `RESEND_API_KEY` | Email API key from resend.com |
| `RESEND_FROM_EMAIL` | Verified sender email |
| `RECIPIENT_EMAIL` | Where to send reports |

**Optional Environment Variables:**
| Variable | Description |
|----------|-------------|
| `QUIVER_API_KEY` | Quiver Quantitative API for politician trades |
| `ALPHAVANTAGE_API_KEY` | Alpha Vantage API for news sentiment |

### 3. Configure GitHub Secrets (for automated runs)

Go to your repo → Settings → Secrets and variables → Actions → New repository secret

Add all the environment variables listed above.

### 4. Deploy

Push to GitHub — the action runs automatically every 2 weeks (1st and 3rd Wednesday of each month at 8:17 AM MST / 15:17 UTC).

## 💻 Manual Run

```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run analysis
python src/main.py

# Options
python src/main.py --dry-run      # Don't save history or send email
python src/main.py --skip-email   # Save history but don't email
python src/main.py --verbose      # Detailed output
python src/main.py --check-config # Verify configuration
```

## 🔄 How It Works

### Bi-Weekly Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│  1. Load Portfolio History                                       │
│     └─ Previous recommendations, performance, lessons learned    │
├─────────────────────────────────────────────────────────────────┤
│  2. Fetch Market Data (yfinance)                                │
│     └─ Current prices, indexes, sectors, commodities            │
├─────────────────────────────────────────────────────────────────┤
│  3. Calculate Performance                                        │
│     └─ P&L, detect stop-loss/target hits, generate alerts       │
├─────────────────────────────────────────────────────────────────┤
│  4. Run Market Screens (1500+ stocks)                           │
│     └─ Momentum, fundamental, technical screens                  │
├─────────────────────────────────────────────────────────────────┤
│  5. Fetch External Data                                          │
│     ├─ Politician trades (Capitol Trades, 90 days)              │
│     ├─ Earnings calendar (14-day lookahead)                     │
│     └─ Dividend calendar (14-day lookahead)                     │
├─────────────────────────────────────────────────────────────────┤
│  6. Run Retail Investor Analysis                                 │
│     ├─ Tax-loss harvesting opportunities                        │
│     ├─ Portfolio correlation analysis                           │
│     ├─ Liquidity warnings                                       │
│     ├─ Trailing stop recommendations                            │
│     ├─ Short interest / squeeze detection                       │
│     └─ Sector rotation phase                                    │
├─────────────────────────────────────────────────────────────────┤
│  7. Calculate Risk Metrics                                       │
│     └─ Drawdown, win rate, consecutive losses → Risk Mode       │
├─────────────────────────────────────────────────────────────────┤
│  8. Analyze with Claude Opus 4.5                                │
│     └─ Extended thinking, respects risk mode, real prices       │
├─────────────────────────────────────────────────────────────────┤
│  9. Validate & Verify                                            │
│     ├─ Check allocations against rules                          │
│     └─ Verify prices with yfinance (safety net)                 │
├─────────────────────────────────────────────────────────────────┤
│ 10. Fetch Sentiment (Alpha Vantage)                             │
│     └─ ONLY for selected stocks (no selection bias)             │
├─────────────────────────────────────────────────────────────────┤
│ 11. Build & Send Email                                           │
│     └─ Dark-mode HTML with all insights                         │
├─────────────────────────────────────────────────────────────────┤
│ 12. Save History & Commit                                        │
│     └─ Update portfolio_history.json                            │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow (No Selection Bias)

```
yfinance screens 1500+ stocks (with real prices)
           ↓
Claude selects stocks purely on fundamentals/technicals
           ↓
Verify prices with yfinance (safety net)
           ↓
Fetch sentiment ONLY for selected stocks (Alpha Vantage)
           ↓
Display sentiment as supplementary info in email
```

**Why this order?** Fetching sentiment BEFORE Claude would bias stock selection toward stocks with sentiment data. By fetching AFTER, Claude makes unbiased decisions based purely on market data.

## 📧 Email Report Sections

The email uses a **dark-theme-first design** that looks great in both light and dark mode email clients.

| Section | Description |
|---------|-------------|
| 🎉 **Welcome** (First Run) | Onboarding guide for new users |
| 💰 **Portfolio Summary** | Starting capital → Current value → Total P&L (green/red) → vs S&P 500 |
| 🚨 **Urgent Alerts** | Stop-loss triggers and target hits |
| 📊 **Market Pulse** | Major indices with % changes |
| 📰 **News Sentiment** | AI-analyzed sentiment for recommended stocks |
| 📊 **Performance Attribution** | What moved your portfolio this period |
| 💼 **Existing Holdings** | Real-time P&L with HOLD/SELL/TRIM/ADD status |
| 🎯 **Action Plan** | Fresh budget allocation with BUY/ADD actions |
| 💰 **New Picks** | Fresh $1,000 budget allocation (5-7 diversified stocks) |
| 📅 **Dividend Calendar** | Upcoming ex-dividend dates |
| 💰 **Retail Insights** | Tax harvesting, correlation, stops, squeezes |
| 🏛️ **Politician Trades** | Congressional trading with Claude's insights (up to 10 trades) |
| 📈 **Recommendation Tracker** | Live prices, P&L, HOLD/SELL status for all positions |
| ⚡ **S&P 500 Comparison** | Portfolio vs benchmark performance since inception |

### Screens Included

The agent runs **17 different screens** across the entire market:

### Stock Universe (Dynamic)
| Category | Count | Market Cap Range |
|----------|-------|------------------|
| Mega Cap | ~60 | > $500B |
| Large Cap | ~200 | $50B - $500B |
| Mid Cap | ~250 | $10B - $50B |
| Small Cap | ~250 | $2B - $10B |
| Micro Cap | ~200 | $500M - $2B |
| Nano Cap | ~100 | $100M - $500M |
| **+ 11 Sector Screens** | ~950 | Varies |
| **Total (deduplicated)** | **~1,500+** | |

### Momentum Screens
- Top gainers/losers by sector
- 52-week high breakouts
- 52-week low bounces
- Unusual volume spikes (3x+ average)

### Fundamental Screens
- Value stocks (P/E < 15, earnings growth > 10%)
- Growth stocks (revenue growth > 20%)
- Dividend stocks (yield > 3%, payout < 60%)
- Insider buying clusters

### Technical Screens
- Golden/Death crosses (50/200 SMA)
- Oversold (RSI < 30)
- Overbought (RSI > 70)

### Growth Screens
- High growth stocks (revenue growth > 20%, EPS growth)
- GARP stocks (Growth at Reasonable Price - PEG ratio analysis)
- Growth scoring (0-100 based on revenue, EPS, PEG, ROE)

### Sector Analysis
- Relative performance vs S&P 500
- Rotation signals
- All 11 GICS sectors

### Asset Class Tracking (100% Dynamic)
| Asset Class | Discovery Method |
|-------------|------------------|
| Commodities | ETF keyword search: "gold", "silver", "oil", "copper", "agriculture" |
| Fixed Income | ETF keyword search: "treasury", "corporate bond", "municipal" |
| International | ETF keyword search: "emerging market", "europe", "japan", "china" |
| Thematic | ETF keyword search: "AI", "clean energy", "semiconductor", "biotech" |

All ETFs are discovered dynamically via Yahoo Finance - no hardcoded ticker lists.

## 📊 Comprehensive Stock Data (60+ Fields)

Claude receives extensive fundamental data for every stock analyzed. Here's the complete data set:

### Per-Stock Data Points

| Category | Fields |
|----------|--------|
| **Basic Info** | ticker, name, sector, industry |
| **Price Data** | current_price, 52w_high, 52w_low, 50_day_avg, 200_day_avg, 52w_change, sp500_52w_change |
| **Valuation** | market_cap, enterprise_value, pe_ratio, forward_pe, peg_ratio, price_to_book, price_to_sales, ev_to_revenue, ev_to_ebitda |
| **Profitability** | profit_margin, gross_margins, ebitda_margins, operating_margins, roe, roa |
| **Financial Health** | total_cash, total_debt, debt_to_equity, current_ratio, quick_ratio, free_cashflow, operating_cashflow |
| **Growth** | revenue_growth, earnings_growth, earnings_quarterly_growth, revenue_quarterly_growth |
| **Analyst Data** | analyst_recommendation, analyst_rating_score, num_analyst_opinions, target_mean_price, target_high_price, target_low_price |
| **Short Interest** | short_ratio, shares_short, short_percent_of_float, shares_short_prior_month |
| **Ownership** | insider_ownership, institutional_ownership, float_shares, shares_outstanding |
| **Dividends** | dividend_yield, dividend_rate, payout_ratio, ex_dividend_date |
| **Trading** | avg_volume, avg_volume_10day, beta |
| **Earnings** | trailing_eps, forward_eps, book_value, revenue_per_share |

### 4-Year Historical Financials

For portfolio holdings and top 50 screen candidates, Claude also receives **4 years of annual financial data**:

| Metric | Description |
|--------|-------------|
| **Revenue History** | 4-year revenue trend (in billions) |
| **Net Income History** | 4-year profitability trend |
| **EPS History** | Earnings per share (diluted) over 4 years |
| **Free Cash Flow History** | FCF generation trend |
| **Gross Profit History** | Margin consistency over time |
| **EBITDA History** | Operating earnings power |
| **Revenue Growth Trend** | Year-over-year growth rates |

### Example: NVDA Historical Data

```
Periods: 2022 → 2023 → 2024 → 2025
Revenue:      $26.9B → $27.0B → $60.9B → $130.5B
Net Income:   $9.8B  → $4.4B  → $29.8B → $72.9B
EPS:          $0.39  → $0.18  → $1.21  → $2.97
FCF:          $8.1B  → $3.8B  → $27.0B → $60.9B
Growth:       -      → 0.2%   → 125.9% → 114.2%
```

This historical data allows Claude to:
- ✅ Validate growth claims with actual multi-year trends
- ✅ Identify companies with consistent vs erratic growth
- ✅ Spot margin expansion/compression over time
- ✅ Detect companies transitioning from losses to profits
- ✅ Avoid "one-hit wonders" with unsustainable growth

## 📐 Diversification Rules

Claude Opus 4.5 acts as the **sole advisor** with minimal guardrails:

| Rule | Limit | Purpose |
|------|-------|---------|
| Single stock | Max 15% | Prevent single-stock blowup |

**Everything else is Claude's decision** - asset allocation, sector weights, number of positions, investment style. The AI has full discretion based on:
- Your user profile (age, risk tolerance, financial situation)
- Current market conditions
- Portfolio history and past performance
- Real-time market data

## 🛡️ Risk Management

The agent includes **automatic risk management** that adjusts strategy based on portfolio performance:

### Risk Status Levels

| Status | Trigger | Actions |
|--------|---------|---------|
| 🟢 **NORMAL** | Default state | Standard allocation rules apply |
| 🟡 **CAUTION** | Drawdown ≥10% OR 3 consecutive losses OR win rate <40% | Reduce position sizes, avoid speculative plays, increase cash to 15%+ |
| 🟠 **DEFENSIVE** | Drawdown ≥15% OR 4+ consecutive losses OR win rate <30% | Max 7% positions, 25%+ cash, conservative picks only, halt aggressive trades |
| 🔴 **CRITICAL** | Drawdown ≥20% | Emergency mode: 40%+ cash, max 5% positions, treasuries/dividend aristocrats only |

### How It Works

Each run calculates risk metrics and Claude receives **mandatory rules** based on the current status:

```
⚠️ RISK MANAGEMENT STATUS: 🟠 DEFENSIVE

Metrics:
- Drawdown from Peak: -16.2%
- Consecutive Losses: 4
- Win Rate: 28.5%

MANDATORY RULES FOR DEFENSIVE MODE:
- Maximum position size: 7%
- Minimum cash allocation: 25%
- Aggressive positions allowed: NO
- Speculative positions allowed: NO
- Maximum new positions this period: 2
```

## 💵 Cost Estimate

| Service | Monthly Cost |
|---------|--------------|
| Claude Opus 4.5 API | ~$5-15 |
| Resend (100 emails/day free) | $0 |
| GitHub Actions | $0 |
| Alpha Vantage (free tier) | $0 |
| **Total** | **~$5-15/month** |

## 🔧 Troubleshooting

### Common Issues

**Claude API timeout/network error:**
- The system automatically retries 3 times with exponential backoff (10s, 20s delays)
- If all retries fail, a safe fallback preserves your existing portfolio
- Check GitHub Actions logs for details

**Empty email sections:**
- First run will show welcome section instead of performance data
- Portfolio builds over time with each run

**No politician trades:**
- Verify Claude is returning `politician_trade_analysis.notable_trades` in response
- Capitol Trades may have rate limits

**S&P 500 showing 0%:**
- Fixed in latest version - now correctly uses "S&P 500 (SPY)" key
- Historical data won't be retroactively fixed, but new runs will be accurate

**No news sentiment:**
- Check `ALPHAVANTAGE_API_KEY` is set
- Free tier: 25 calls/day limit

**Prices showing N/A or $0:**
- All prices should come from yfinance via `portfolio_performance`
- Check that `calculate_performance()` is being called in main.py

### Logs

Check the console output for detailed progress:
```
[1/10] Loading portfolio history...
[2/10] Fetching market data...
[3/10] Calculating portfolio performance...
...
```

## ⚠️ Disclaimer

**This is not financial advice.** This project is for educational and informational purposes only. 

- Past performance does not guarantee future results
- Always do your own research before investing
- Consult a licensed financial advisor for personalized advice
- The authors are not responsible for any investment decisions made based on this tool's output

---

Built with ❤️ for retail investors who want institutional-quality insights.

## 📝 Recent Updates

### February 2026 (Latest)
- **60+ Stock Data Fields**: Comprehensive fundamentals including analyst ratings, EV/EBITDA, cash/debt, margins, short interest, and more
- **4-Year Historical Financials**: Revenue, Net Income, EPS, FCF, EBITDA trends for portfolio + top 50 candidates
- **Enhanced Claude Prompt**: Updated to leverage historical data for better growth validation
- **Earnings Calendar Section**: New email section showing upcoming earnings for watchlist stocks
- **Light Theme Email Design**: Professional light theme with solid colors for dark mode compatibility
- **Entry Price Fix**: Stock cards now correctly show entry prices in "How to Execute" section

### January 2026
- **Portfolio Summary Section**: New prominent section showing Starting Capital → Current Value → Total P&L (green/red) → vs S&P 500
- **S&P 500 Tracking Fix**: Fixed benchmark comparison (was showing 0%)
- **Live Prices Everywhere**: Recommendation Tracker now shows real-time prices from yfinance
- **Politician Trades Fix**: Now correctly displays congressional trades with Claude's analysis insights
- **5-7 Stock Recommendations**: Claude now provides more diversified picks (was 2-3)
- **API Retry Logic**: Automatic 3x retry with exponential backoff for network resilience
- **Status Badges**: Recommendation Tracker shows HOLD (blue), ADD (green), TRIM (orange), SELL (red)
