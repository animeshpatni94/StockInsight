# 📊 Stock Insight Agent

AI-powered monthly stock analysis with portfolio memory, politician trade tracking, and actionable recommendations.

## Features

- **Full Market Coverage**: All 11 S&P sectors, all market caps, international, metals, commodities
- **Portfolio Memory**: Tracks recommendations month-over-month, calculates performance
- **Politician Tracking**: Monitors congressional trades, flags suspicious timing
- **Diversification**: Enforces allocation rules across asset class, sector, style, horizon
- **Actionable Output**: Clear BUY/SELL/HOLD with entry zones, targets, stop-losses
- **Critical Analysis**: Contrarian, skeptical, admits mistakes

## Project Structure

```
stock-insight-agent/
├── .github/
│   └── workflows/
│       └── monthly-analysis.yml
├── data/
│   └── portfolio_history.json
├── src/
│   ├── __init__.py
│   ├── main.py                    # Entry point
│   ├── config.py                  # Configuration and constants
│   ├── data_fetcher.py            # Market data + politician trades
│   ├── market_scanner.py          # Full market screening logic
│   ├── politician_tracker.py      # Congress trade analysis
│   ├── history_manager.py         # Portfolio memory management
│   ├── claude_analyzer.py         # Claude Opus integration
│   ├── email_builder.py           # HTML email construction
│   └── email_sender.py            # Azure Communication Services
├── templates/
│   └── email_template.html        # Base email template
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

### 4. Deploy

Push to GitHub — the action runs automatically on the 1st of each month at 9:00 AM UTC.

## Manual Run

```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run analysis
python src/main.py
```

## How It Works

### Monthly Workflow

1. **Load Portfolio History** - Reads previous recommendations and performance
2. **Fetch Market Data** - Gets current prices for all holdings and market indexes
3. **Run Market Screens** - Executes momentum, fundamental, and technical screens
4. **Fetch Politician Trades** - Gets recent congressional trading activity
5. **Analyze with Claude** - AI analyzes data and generates recommendations
6. **Update History** - Saves new portfolio state and performance metrics
7. **Build Email** - Creates professional HTML report
8. **Send Email** - Delivers via Resend
9. **Commit Changes** - Updates portfolio_history.json in the repo

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

## Cost Estimate

| Service | Monthly Cost |
|---------|--------------|
| Claude Opus API | ~$5-10 |
| Resend (100 emails/day free) | $0 |
| GitHub Actions | $0 |
| **Total** | **~$5-10/month** |

## Email Report Sections

1. Performance Scorecard
2. Macro Regime Assessment
3. Current Holdings Review
4. Sells This Month
5. New Recommendations (by time horizon)
6. Metals & Commodities Outlook
7. Portfolio Allocation Charts
8. Politician Trade Alerts
9. Risks to Portfolio
10. Watchlist
11. Action Summary

## Disclaimer

⚠️ **This is not financial advice.** This project is for educational and informational purposes only. 

- Past performance does not guarantee future results
- Always do your own research before investing
- Consult a licensed financial advisor for personalized advice
- The authors are not responsible for any investment decisions made based on this tool's output

## License

MIT License - feel free to use, modify, and distribute.
