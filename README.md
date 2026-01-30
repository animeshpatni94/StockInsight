# 📊 Stock Insight Agent

AI-powered **bi-weekly** stock analysis with portfolio memory, politician trade tracking, risk management, and actionable recommendations.

## Features

- **Full Market Coverage**: All 11 S&P sectors, all market caps, international, metals, commodities (1000+ stocks screened)
- **Real-Time Prices**: All prices sourced from yfinance - never uses stale training data
- **Portfolio Memory**: Tracks recommendations over time, calculates performance, learns from past trades
- **Risk Management**: Industry-standard drawdown protection with automatic defensive modes
- **Politician Tracking**: Monitors congressional trades from Capitol Trades (90-day lookback), flags suspicious timing
- **News Sentiment**: AI-analyzed sentiment via Alpha Vantage - fetched AFTER stock selection to avoid bias
- **Earnings Calendar**: Tracks upcoming earnings for portfolio and watchlist stocks
- **Diversification**: Enforces allocation rules across asset class, sector, style, horizon
- **Actionable Output**: Clear BUY/SELL/HOLD with entry zones, targets, stop-losses
- **Critical Analysis**: Contrarian, skeptical, admits mistakes
- **Dark Mode Email**: Professional HTML reports optimized for both light and dark mode email clients

## Project Structure

```
StockInsight/
├── .github/
│   └── workflows/
│       └── biweekly-analysis.yml    # Runs every 2 weeks
├── data/
│   └── portfolio_history.json    # Portfolio state & history
├── output/
│   └── *.html                    # Generated email previews
├── src/
│   ├── __init__.py
│   ├── main.py                   # Entry point
│   ├── config.py                 # Configuration and constants
│   ├── data_fetcher.py           # Market data via yfinance
│   ├── market_scanner.py         # Full market screening (1000+ stocks)
│   ├── politician_tracker.py     # Capitol Trades scraper
│   ├── history_manager.py        # Portfolio memory & risk management
│   ├── news_sentiment.py         # Alpha Vantage sentiment analysis
│   ├── claude_analyzer.py        # Claude Opus 4.5 integration
│   ├── email_builder.py          # Dark-mode HTML email builder
│   └── email_sender.py           # Resend API integration
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

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

### 3. Configure GitHub Secrets

Go to your repo → Settings → Secrets and variables → Actions → New repository secret

| Secret Name | Value |
|-------------|-------|
| `ANTHROPIC_API_KEY` | Your Claude API key from console.anthropic.com |
| `RESEND_API_KEY` | Your API key from resend.com/api-keys |
| `RESEND_FROM_EMAIL` | Your verified sender email (e.g., reports@yourdomain.com) |
| `RECIPIENT_EMAIL` | Where to send the monthly report |
| `QUIVER_API_KEY` | Optional: Quiver Quantitative API key |
| `ALPHAVANTAGE_API_KEY` | Optional: Alpha Vantage API key for news sentiment |

### 4. Deploy

Push to GitHub — the action runs automatically every 2 weeks (1st and 15th of each month at 9:00 AM UTC).

## Manual Run

```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run analysis
python src/main.py
```

## How It Works

### Bi-Weekly Workflow

1. **Load Portfolio History** - Reads previous recommendations and performance
2. **Fetch Market Data** - Gets current prices for all holdings and market indexes (yfinance)
3. **Run Market Screens** - Executes momentum, fundamental, and technical screens on 1000+ stocks
4. **Fetch Politician Trades** - Scrapes Capitol Trades for recent congressional trading activity (90-day lookback)
5. **Check Earnings Calendar** - Identifies upcoming earnings catalysts
6. **Calculate Risk Metrics** - Determines if defensive mode should be activated
7. **Analyze with Claude** - AI analyzes data and generates recommendations (with real prices, respects risk mode rules)
8. **Verify Prices** - Safety net to ensure all recommendations use real yfinance prices
9. **Fetch Sentiment** - Gets news sentiment ONLY for recommended stocks (no selection bias)
10. **Update History** - Saves new portfolio state and performance metrics
11. **Build Email** - Creates professional HTML report with sentiment badges
12. **Send Email** - Delivers via Resend
13. **Commit Changes** - Updates portfolio_history.json in the repo

### Data Flow (No Selection Bias)

```
yfinance screens 1000+ stocks (with real prices)
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

### Screens Included

**Momentum Screens**
- Top gainers/losers by sector
- 52-week high breakouts
- 52-week low bounces
- Unusual volume spikes

**Fundamental Screens**
- Value stocks (P/E < 15, earnings growth > 10%)
- Growth stocks (revenue growth > 20%)
- Dividend stocks (yield > 3%, payout < 60%)
- Insider buying clusters
- Earnings surprises

**Technical Screens**
- Golden/Death crosses
- Oversold (RSI < 30)
- Overbought (RSI > 70)

**Sector Analysis**
- Relative performance
- Rotation signals
- Strength vs S&P 500

### Diversification Rules

The agent enforces strict allocation limits:

- **Single stock**: Max 20%
- **Single sector**: Max 35%
- **Positions**: 5-15 total

**By Asset Class:**
- US Stocks: 40-70%
- International: 5-20%
- Metals/Commodities: 5-15%
- Bonds/Cash: 10-25%

**By Style:**
- Growth: 20-40%
- Value: 20-40%
- Dividend: 10-30%
- Speculative: 0-10%

## 🛡️ Risk Management (Industry-Standard Drawdown Protection)

The agent includes **automatic risk management** that adjusts strategy based on portfolio performance:

### Risk Status Levels

| Status | Trigger | Actions |
|--------|---------|---------|
| 🟢 **NORMAL** | Default state | Standard allocation rules apply |
| 🟡 **CAUTION** | Drawdown ≥10% OR 3 consecutive losses OR win rate <40% | Reduce position sizes, avoid speculative plays, increase cash to 15%+ |
| 🟠 **DEFENSIVE** | Drawdown ≥15% OR 4+ consecutive losses OR win rate <30% | Max 7% positions, 25%+ cash, conservative picks only, halt aggressive trades |
| 🔴 **CRITICAL** | Drawdown ≥20% | Emergency mode: 40%+ cash, max 5% positions, treasuries/dividend aristocrats only |

### Key Metrics Tracked

- **Drawdown from Peak**: Measures decline from highest portfolio value
- **Consecutive Losses**: Tracks losing streaks across periods
- **Win Rate**: Success rate after 5+ trades
- **Alpha vs S&P 500**: Performance relative to benchmark

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

This ensures the AI automatically becomes more conservative when the portfolio is struggling, protecting against catastrophic losses.

## Cost Estimate

| Service | Monthly Cost |
|---------|--------------|
| Claude Opus API | ~$5-10 |
| Resend (100 emails/day free) | $0 |
| GitHub Actions | $0 |
| **Total** | **~$5-10/month** |

## Email Report Sections

The email uses a **dark-theme-first design** that looks great in both light and dark mode email clients.

1. Performance Scorecard (This Period / S&P 500 / Total Return)
2. Macro Regime Assessment
3. Current Holdings Review with status indicators
4. Sells This Period
5. New Recommendations (grouped by time horizon)
6. Metals & Commodities Outlook
7. Portfolio Allocation Summary
8. Politician Trade Alerts (Notable trades, Suspicious patterns, Portfolio overlap)
9. Risks to Portfolio
10. Watchlist
11. Action Summary (BUY/SELL/TRIM/CASH)

## Disclaimer

⚠️ **This is not financial advice.** This project is for educational and informational purposes only. 

- Past performance does not guarantee future results
- Always do your own research before investing
- Consult a licensed financial advisor for personalized advice
- The authors are not responsible for any investment decisions made based on this tool's output

## License

MIT License - feel free to use, modify, and distribute.
