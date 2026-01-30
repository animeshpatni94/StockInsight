"""
Politician trade tracking and analysis module.
Fetches and analyzes congressional stock trades from public sources.
"""

import os
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from config import COMMITTEE_SECTOR_MAP


# API Configuration
QUIVER_BASE_URL = "https://api.quiverquant.com/beta"


def fetch_recent_trades(days: int = 45) -> List[Dict]:
    """
    Fetch all congressional trades from the past N days.
    
    Args:
        days: Number of days to look back
    
    Returns:
        List of trade dictionaries
    """
    api_key = os.getenv('QUIVER_API_KEY')
    
    if not api_key:
        print("  Warning: QUIVER_API_KEY not set, using mock data")
        return _get_mock_trades()
    
    try:
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Accept': 'application/json'
        }
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Quiver Quantitative endpoint for congressional trading
        url = f"{QUIVER_BASE_URL}/historical/congresstrading"
        params = {
            'from': start_date.strftime('%Y-%m-%d'),
            'to': end_date.strftime('%Y-%m-%d')
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        trades = response.json()
        
        # Normalize the data
        normalized_trades = []
        for trade in trades:
            normalized_trades.append({
                'politician': trade.get('Representative', 'Unknown'),
                'party': trade.get('Party', 'Unknown'),
                'chamber': trade.get('House', 'Unknown'),
                'ticker': trade.get('Ticker', ''),
                'company': trade.get('Company', ''),
                'transaction_type': trade.get('Transaction', ''),
                'amount': trade.get('Amount', ''),
                'trade_date': trade.get('TransactionDate', ''),
                'disclosure_date': trade.get('DisclosureDate', ''),
                'sector': trade.get('Sector', 'Unknown'),
                'committees': trade.get('Committees', [])
            })
        
        return normalized_trades
        
    except requests.exceptions.RequestException as e:
        print(f"  Error fetching politician trades: {str(e)}")
        return _get_mock_trades()
    except Exception as e:
        print(f"  Unexpected error: {str(e)}")
        return _get_mock_trades()


def _get_mock_trades() -> List[Dict]:
    """
    Return mock data for testing when API is unavailable.
    
    Returns:
        List of mock trade dictionaries
    """
    return [
        {
            'politician': 'Nancy Pelosi',
            'party': 'Democrat',
            'chamber': 'House',
            'ticker': 'NVDA',
            'company': 'NVIDIA Corporation',
            'transaction_type': 'Purchase',
            'amount': '$1,000,001 - $5,000,000',
            'trade_date': '2026-01-15',
            'disclosure_date': '2026-01-20',
            'sector': 'Technology',
            'committees': ['Finance', 'Intelligence']
        },
        {
            'politician': 'Dan Crenshaw',
            'party': 'Republican',
            'chamber': 'House',
            'ticker': 'LMT',
            'company': 'Lockheed Martin',
            'transaction_type': 'Purchase',
            'amount': '$100,001 - $250,000',
            'trade_date': '2026-01-10',
            'disclosure_date': '2026-01-18',
            'sector': 'Industrials',
            'committees': ['Armed Services', 'Energy']
        },
        {
            'politician': 'Tommy Tuberville',
            'party': 'Republican',
            'chamber': 'Senate',
            'ticker': 'RTX',
            'company': 'RTX Corporation',
            'transaction_type': 'Purchase',
            'amount': '$250,001 - $500,000',
            'trade_date': '2026-01-08',
            'disclosure_date': '2026-01-16',
            'sector': 'Industrials',
            'committees': ['Armed Services']
        },
        {
            'politician': 'Mark Green',
            'party': 'Republican',
            'chamber': 'House',
            'ticker': 'UNH',
            'company': 'UnitedHealth Group',
            'transaction_type': 'Purchase',
            'amount': '$50,001 - $100,000',
            'trade_date': '2026-01-12',
            'disclosure_date': '2026-01-22',
            'sector': 'Healthcare',
            'committees': ['Health']
        },
        {
            'politician': 'Josh Gottheimer',
            'party': 'Democrat',
            'chamber': 'House',
            'ticker': 'GOOGL',
            'company': 'Alphabet Inc.',
            'transaction_type': 'Sale',
            'amount': '$100,001 - $250,000',
            'trade_date': '2026-01-05',
            'disclosure_date': '2026-01-15',
            'sector': 'Technology',
            'committees': ['Judiciary']
        }
    ]


def analyze_committee_correlation(trades: List[Dict]) -> List[Dict]:
    """
    Flag trades where politician sits on committee overseeing that sector.
    
    Args:
        trades: List of trade dictionaries
    
    Returns:
        Trades with 'suspicious_flag' and 'correlation_reason' fields added
    """
    flagged_trades = []
    
    for trade in trades:
        politician_committees = trade.get('committees', [])
        trade_sector = trade.get('sector', '')
        
        trade['suspicious_flag'] = False
        trade['correlation_reason'] = None
        
        for committee in politician_committees:
            if committee in COMMITTEE_SECTOR_MAP:
                related_sectors = COMMITTEE_SECTOR_MAP[committee]
                
                # Check if trade sector matches committee oversight
                for related in related_sectors:
                    if (related.lower() in trade_sector.lower() or 
                        trade_sector.lower() in related.lower()):
                        trade['suspicious_flag'] = True
                        trade['correlation_reason'] = (
                            f"{committee} committee has oversight of {trade_sector} sector"
                        )
                        flagged_trades.append(trade)
                        break
                
                if trade['suspicious_flag']:
                    break
    
    return flagged_trades


def find_trade_clusters(trades: List[Dict], min_politicians: int = 3, 
                        days: int = 30) -> List[Dict]:
    """
    Find stocks that multiple politicians bought within a time window.
    Bipartisan buying is a stronger signal.
    
    Args:
        trades: List of trade dictionaries
        min_politicians: Minimum number of politicians trading same stock
        days: Time window in days
    
    Returns:
        List of clustered trades by ticker
    """
    from collections import defaultdict
    
    # Group trades by ticker
    ticker_trades = defaultdict(list)
    
    cutoff_date = datetime.now() - timedelta(days=days)
    
    for trade in trades:
        if trade.get('transaction_type', '').lower() in ['purchase', 'buy']:
            try:
                trade_date = datetime.strptime(trade.get('trade_date', ''), '%Y-%m-%d')
                if trade_date >= cutoff_date:
                    ticker_trades[trade.get('ticker')].append(trade)
            except ValueError:
                # Skip trades with invalid dates
                continue
    
    # Find clusters
    clusters = []
    for ticker, ticker_trade_list in ticker_trades.items():
        if len(ticker_trade_list) >= min_politicians:
            # Check for bipartisan buying
            parties = set(t.get('party', 'Unknown') for t in ticker_trade_list)
            is_bipartisan = len(parties) > 1
            
            clusters.append({
                'ticker': ticker,
                'company': ticker_trade_list[0].get('company', ''),
                'num_politicians': len(ticker_trade_list),
                'politicians': [t.get('politician') for t in ticker_trade_list],
                'parties': list(parties),
                'is_bipartisan': is_bipartisan,
                'signal_strength': 'Strong' if is_bipartisan else 'Moderate',
                'trades': ticker_trade_list
            })
    
    # Sort by number of politicians (strongest signal first)
    clusters.sort(key=lambda x: (x['is_bipartisan'], x['num_politicians']), reverse=True)
    
    return clusters


def get_politician_performance(politician_name: str, months: int = 12) -> Dict:
    """
    Track how a specific politician's trades have performed.
    
    Args:
        politician_name: Name of the politician
        months: Number of months to analyze
    
    Returns:
        Performance metrics dictionary
    """
    # This would require historical trade data and price data
    # Placeholder implementation
    return {
        'politician': politician_name,
        'period_months': months,
        'total_trades': 0,
        'win_rate': 0.0,
        'average_return': 0.0,
        'vs_sp500': 0.0,
        'note': 'Requires historical data API access'
    }


def check_overlap_with_portfolio(trades: List[Dict], 
                                  current_holdings: List[str]) -> List[Dict]:
    """
    Check if any politician trades overlap with our current holdings.
    
    Args:
        trades: List of recent politician trades
        current_holdings: List of tickers in our portfolio
    
    Returns:
        List of overlapping trades with implications
    """
    overlaps = []
    holdings_set = set(h.upper() for h in current_holdings)
    
    for trade in trades:
        ticker = trade.get('ticker', '').upper()
        if ticker in holdings_set:
            transaction = trade.get('transaction_type', '').lower()
            
            if transaction in ['purchase', 'buy']:
                implication = 'CONFIRMATION: Politician buying what we hold'
                sentiment = 'positive'
            elif transaction in ['sale', 'sell']:
                implication = 'WARNING: Politician selling what we hold'
                sentiment = 'negative'
            else:
                implication = 'Unknown transaction type'
                sentiment = 'neutral'
            
            overlaps.append({
                **trade,
                'implication': implication,
                'sentiment': sentiment
            })
    
    return overlaps


def get_top_traded_stocks(trades: List[Dict], n: int = 10) -> List[Dict]:
    """
    Get the most actively traded stocks by Congress.
    
    Args:
        trades: List of trade dictionaries
        n: Number of top stocks to return
    
    Returns:
        List of most traded stocks with counts
    """
    from collections import Counter
    
    # Count trades by ticker
    buy_counts = Counter()
    sell_counts = Counter()
    
    for trade in trades:
        ticker = trade.get('ticker', '')
        transaction = trade.get('transaction_type', '').lower()
        
        if transaction in ['purchase', 'buy']:
            buy_counts[ticker] += 1
        elif transaction in ['sale', 'sell']:
            sell_counts[ticker] += 1
    
    # Combine and calculate net sentiment
    all_tickers = set(buy_counts.keys()) | set(sell_counts.keys())
    
    results = []
    for ticker in all_tickers:
        buys = buy_counts.get(ticker, 0)
        sells = sell_counts.get(ticker, 0)
        total = buys + sells
        net = buys - sells
        
        results.append({
            'ticker': ticker,
            'total_trades': total,
            'buys': buys,
            'sells': sells,
            'net_sentiment': 'Bullish' if net > 0 else 'Bearish' if net < 0 else 'Neutral',
            'net_score': net
        })
    
    # Sort by total activity
    results.sort(key=lambda x: x['total_trades'], reverse=True)
    
    return results[:n]


def format_politician_report(trades: List[Dict], 
                             flagged_trades: List[Dict]) -> str:
    """
    Format politician trades into a readable report section.
    
    Args:
        trades: All recent trades
        flagged_trades: Trades flagged as suspicious
    
    Returns:
        Formatted string report
    """
    lines = []
    lines.append("=" * 60)
    lines.append("CONGRESSIONAL TRADING ACTIVITY REPORT")
    lines.append("=" * 60)
    lines.append("")
    
    # Summary statistics
    total_trades = len(trades)
    buys = sum(1 for t in trades if t.get('transaction_type', '').lower() in ['purchase', 'buy'])
    sells = total_trades - buys
    flagged_count = len(flagged_trades)
    
    lines.append(f"Total Trades: {total_trades}")
    lines.append(f"Purchases: {buys} | Sales: {sells}")
    lines.append(f"Flagged for Committee Correlation: {flagged_count}")
    lines.append("")
    
    # Flagged trades section
    if flagged_trades:
        lines.append("-" * 40)
        lines.append("⚠️  SUSPICIOUS TRADES (Committee Overlap)")
        lines.append("-" * 40)
        
        for trade in flagged_trades:
            lines.append(f"\n{trade.get('politician')} ({trade.get('party')})")
            lines.append(f"  Ticker: {trade.get('ticker')} - {trade.get('company')}")
            lines.append(f"  Action: {trade.get('transaction_type')}")
            lines.append(f"  Amount: {trade.get('amount')}")
            lines.append(f"  Date: {trade.get('trade_date')}")
            lines.append(f"  🚨 {trade.get('correlation_reason')}")
    
    # Top traded stocks
    top_stocks = get_top_traded_stocks(trades, n=5)
    if top_stocks:
        lines.append("")
        lines.append("-" * 40)
        lines.append("📊 MOST TRADED BY CONGRESS")
        lines.append("-" * 40)
        
        for stock in top_stocks:
            sentiment_emoji = "🟢" if stock['net_sentiment'] == 'Bullish' else "🔴" if stock['net_sentiment'] == 'Bearish' else "⚪"
            lines.append(f"{sentiment_emoji} {stock['ticker']}: {stock['buys']} buys, {stock['sells']} sells ({stock['net_sentiment']})")
    
    lines.append("")
    lines.append("=" * 60)
    
    return "\n".join(lines)


def get_politician_trades_summary(days: int = 45) -> Dict:
    """
    Get a comprehensive summary of politician trading activity.
    
    Args:
        days: Number of days to analyze
    
    Returns:
        Dictionary with complete trading analysis
    """
    # Fetch trades
    trades = fetch_recent_trades(days=days)
    
    # Analyze
    flagged = analyze_committee_correlation(trades)
    clusters = find_trade_clusters(trades)
    top_traded = get_top_traded_stocks(trades, n=10)
    
    return {
        'all_trades': trades,
        'flagged_trades': flagged,
        'trade_clusters': clusters,
        'top_traded': top_traded,
        'summary': {
            'total_trades': len(trades),
            'flagged_count': len(flagged),
            'cluster_count': len(clusters),
            'period_days': days
        }
    }
