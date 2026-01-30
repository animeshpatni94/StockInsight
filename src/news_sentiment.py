"""
News sentiment module using Alpha Vantage API.
Fetches bullish/bearish sentiment scores for stocks.

Alpha Vantage Free Tier: 25 API requests per day
"""

import os
import requests
from typing import Dict, List, Optional
from datetime import datetime
import time


# Alpha Vantage API endpoint
ALPHAVANTAGE_BASE_URL = "https://www.alphavantage.co/query"


def get_alphavantage_api_key() -> Optional[str]:
    """Get Alpha Vantage API key from environment."""
    return os.getenv('ALPHAVANTAGE_API_KEY')


def fetch_sentiment(ticker: str) -> Optional[Dict]:
    """
    Fetch news sentiment for a single ticker from Alpha Vantage.
    
    Args:
        ticker: Stock symbol
    
    Returns:
        Dictionary with sentiment data or None if unavailable
    """
    api_key = get_alphavantage_api_key()
    if not api_key:
        return None
    
    try:
        params = {
            'function': 'NEWS_SENTIMENT',
            'tickers': ticker,
            'apikey': api_key,
            'limit': 50  # Get up to 50 articles for analysis
        }
        
        response = requests.get(ALPHAVANTAGE_BASE_URL, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        
        # Check for API errors or rate limits
        if 'Note' in data or 'Information' in data:
            # Rate limit hit
            return None
        
        if 'feed' not in data or not data['feed']:
            return None
        
        feed = data['feed']
        
        # Calculate aggregate sentiment from articles
        ticker_sentiments = []
        articles_count = 0
        
        for article in feed:
            ticker_sentiment = article.get('ticker_sentiment', [])
            for ts in ticker_sentiment:
                if ts.get('ticker', '').upper() == ticker.upper():
                    try:
                        # Score ranges from -1 (bearish) to 1 (bullish)
                        score = float(ts.get('ticker_sentiment_score', 0))
                        relevance = float(ts.get('relevance_score', 0))
                        # Weight by relevance
                        if relevance > 0.1:  # Only consider relevant articles
                            ticker_sentiments.append(score * relevance)
                            articles_count += 1
                    except (ValueError, TypeError):
                        pass
        
        if not ticker_sentiments:
            return None
        
        # Calculate weighted average sentiment
        avg_sentiment = sum(ticker_sentiments) / len(ticker_sentiments)
        
        # Convert -1 to 1 scale to bullish percentage (0-100)
        # -1 = 0% bullish, 0 = 50% bullish, 1 = 100% bullish
        bullish_pct = (avg_sentiment + 1) * 50
        bearish_pct = 100 - bullish_pct
        
        # Determine sentiment label and emoji
        if bullish_pct >= 65:
            label = "BULLISH"
            emoji = "🟢"
        elif bullish_pct >= 55:
            label = "SLIGHTLY_BULLISH"
            emoji = "🟢"
        elif bearish_pct >= 65:
            label = "BEARISH"
            emoji = "🔴"
        elif bearish_pct >= 55:
            label = "SLIGHTLY_BEARISH"
            emoji = "🔴"
        else:
            label = "NEUTRAL"
            emoji = "⚪"
        
        return {
            'ticker': ticker,
            'bullish_pct': round(bullish_pct, 1),
            'bearish_pct': round(bearish_pct, 1),
            'label': label,
            'emoji': emoji,
            'articles_analyzed': articles_count,
            'avg_sentiment_score': round(avg_sentiment, 3),
            'display_text': f"{emoji} {bullish_pct:.0f}% Bullish"
        }
        
    except requests.exceptions.RequestException as e:
        return None
    except Exception as e:
        return None


def fetch_multiple_sentiments(tickers: List[str], max_tickers: int = 20) -> Dict[str, Dict]:
    """
    Fetch sentiment for multiple tickers using Alpha Vantage.
    
    Alpha Vantage allows querying multiple tickers in one request,
    which is more efficient than single-ticker approaches.
    
    Free tier: 25 requests/day, so we batch tickers to conserve calls.
    
    Args:
        tickers: List of stock symbols
        max_tickers: Maximum number of tickers to analyze (default 20)
    
    Returns:
        Dictionary mapping ticker to sentiment data
    """
    api_key = get_alphavantage_api_key()
    if not api_key:
        print("  Alpha Vantage API key not configured, skipping sentiment analysis")
        return {}
    
    tickers_to_fetch = list(set(tickers))[:max_tickers]  # Dedupe and limit
    print(f"  Fetching news sentiment for up to {len(tickers_to_fetch)} stocks via Alpha Vantage...")
    
    results = {}
    
    # Alpha Vantage NEWS_SENTIMENT can take comma-separated tickers
    # But to get better results, we'll query in small batches
    batch_size = 5  # Query 5 tickers at a time
    max_api_calls = 20  # Hard cap to stay well under 25/day free tier limit
    batches = [tickers_to_fetch[i:i + batch_size] for i in range(0, len(tickers_to_fetch), batch_size)]
    batches = batches[:max_api_calls]  # Never exceed max API calls
    
    for batch in batches:
        try:
            batch_str = ','.join(batch)
            params = {
                'function': 'NEWS_SENTIMENT',
                'tickers': batch_str,
                'apikey': api_key,
                'limit': 100  # More articles for batch
            }
            
            response = requests.get(ALPHAVANTAGE_BASE_URL, params=params, timeout=20)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for rate limit
            if 'Note' in data or 'Information' in data:
                print(f"    ⚠️ API rate limit reached, got sentiment for {len(results)} stocks")
                break
            
            if 'feed' not in data:
                continue
            
            feed = data['feed']
            
            # Aggregate sentiments per ticker
            ticker_scores = {t.upper(): [] for t in batch}
            
            for article in feed:
                ticker_sentiment = article.get('ticker_sentiment', [])
                for ts in ticker_sentiment:
                    t = ts.get('ticker', '').upper()
                    if t in ticker_scores:
                        try:
                            score = float(ts.get('ticker_sentiment_score', 0))
                            relevance = float(ts.get('relevance_score', 0))
                            if relevance > 0.1:
                                ticker_scores[t].append(score * relevance)
                        except (ValueError, TypeError):
                            pass
            
            # Build results for this batch
            for t, scores in ticker_scores.items():
                if scores:
                    avg_sentiment = sum(scores) / len(scores)
                    bullish_pct = (avg_sentiment + 1) * 50
                    bearish_pct = 100 - bullish_pct
                    
                    if bullish_pct >= 65:
                        label = "BULLISH"
                        emoji = "🟢"
                    elif bullish_pct >= 55:
                        label = "SLIGHTLY_BULLISH"
                        emoji = "🟢"
                    elif bearish_pct >= 65:
                        label = "BEARISH"
                        emoji = "🔴"
                    elif bearish_pct >= 55:
                        label = "SLIGHTLY_BEARISH"
                        emoji = "🔴"
                    else:
                        label = "NEUTRAL"
                        emoji = "⚪"
                    
                    results[t] = {
                        'ticker': t,
                        'bullish_pct': round(bullish_pct, 1),
                        'bearish_pct': round(bearish_pct, 1),
                        'label': label,
                        'emoji': emoji,
                        'articles_analyzed': len(scores),
                        'avg_sentiment_score': round(avg_sentiment, 3),
                        'display_text': f"{emoji} {bullish_pct:.0f}% Bullish"
                    }
            
            # Small delay between batches to be respectful of rate limits
            time.sleep(0.5)
            
        except requests.exceptions.RequestException:
            continue
        except Exception:
            continue
    
    if results:
        bullish_count = sum(1 for s in results.values() if s['label'] in ['BULLISH', 'SLIGHTLY_BULLISH'])
        bearish_count = sum(1 for s in results.values() if s['label'] in ['BEARISH', 'SLIGHTLY_BEARISH'])
        print(f"    Got sentiment for {len(results)} stocks: {bullish_count} bullish, {bearish_count} bearish")
    
    return results


def get_market_sentiment_summary(sentiments: Dict[str, Dict]) -> Dict:
    """
    Generate overall market sentiment summary from individual stock sentiments.
    
    Args:
        sentiments: Dictionary of ticker -> sentiment data
    
    Returns:
        Summary dictionary with aggregate metrics
    """
    if not sentiments:
        return {
            'overall': 'unknown',
            'avg_bullish_pct': 50,
            'stocks_bullish': 0,
            'stocks_bearish': 0,
            'stocks_neutral': 0
        }
    
    bullish_pcts = [s['bullish_pct'] for s in sentiments.values()]
    avg_bullish = sum(bullish_pcts) / len(bullish_pcts)
    
    stocks_bullish = sum(1 for s in sentiments.values() if s['label'] in ['BULLISH', 'SLIGHTLY_BULLISH'])
    stocks_bearish = sum(1 for s in sentiments.values() if s['label'] in ['BEARISH', 'SLIGHTLY_BEARISH'])
    stocks_neutral = sum(1 for s in sentiments.values() if s['label'] == 'NEUTRAL')
    
    if avg_bullish >= 60:
        overall = 'bullish'
        overall_emoji = '🟢'
    elif avg_bullish <= 40:
        overall = 'bearish'
        overall_emoji = '🔴'
    else:
        overall = 'neutral'
        overall_emoji = '⚪'
    
    return {
        'overall': overall,
        'overall_emoji': overall_emoji,
        'avg_bullish_pct': round(avg_bullish, 1),
        'stocks_bullish': stocks_bullish,
        'stocks_bearish': stocks_bearish,
        'stocks_neutral': stocks_neutral,
        'total_analyzed': len(sentiments)
    }


def is_alphavantage_configured() -> bool:
    """Check if Alpha Vantage API is configured."""
    return bool(get_alphavantage_api_key())


# Backward compatibility alias
is_sentiment_configured = is_alphavantage_configured
