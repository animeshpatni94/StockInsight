"""
Data fetching module for market data and prices.
Uses yfinance for stock data retrieval.
Dynamically fetches stock universe using Yahoo Finance Screener API.
Fetches popular ETFs from web sources for dynamic ETF coverage.
"""

import yfinance as yf
from yfinance import EquityQuery
import pandas as pd
import numpy as np
import time
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import (
    INDEXES, SECTORS, TECHNICAL_PARAMS
)

# Configure logging for detailed stock tracking
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Flag to control verbose logging (set to True for debugging)
VERBOSE_LOGGING = True

def log_stocks(category: str, tickers: List[str], max_display: int = 20):
    """Log stock tickers with truncation for readability."""
    if not VERBOSE_LOGGING:
        return
    if len(tickers) <= max_display:
        logger.info(f"  📋 {category}: {', '.join(tickers)}")
    else:
        displayed = tickers[:max_display]
        logger.info(f"  📋 {category} ({len(tickers)} total): {', '.join(displayed)}... +{len(tickers)-max_display} more")


def get_dynamic_stock_universe() -> Dict[str, List[str]]:
    """
    Dynamically fetch stock universe using Yahoo Finance Screener API.
    100% dynamic - no hardcoded stock lists.
    Uses sector and market cap filters to get comprehensive coverage.
    
    Returns:
        Dictionary with categorized stock lists from live screener data
    """
    print("  Fetching dynamic stock universe using Yahoo Finance Screener...")
    
    universe = {
        "mega_cap": [],            # > $500B market cap (AAPL, MSFT, NVDA, etc.)
        "large_cap": [],           # $50B - $500B market cap
        "mid_cap": [],             # $10B - $50B market cap  
        "small_cap": [],           # $2B - $10B market cap
        "micro_cap": [],           # $500M - $2B market cap
        "nano_cap": [],            # $100M - $500M market cap (emerging companies)
        "sector_tech": [],         # Technology sector
        "sector_healthcare": [],   # Healthcare sector (includes biotech)
        "sector_financials": [],   # Financial Services sector
        "sector_energy": [],       # Energy sector
        "sector_consumer_disc": [],# Consumer Cyclical sector
        "sector_consumer_staples": [], # Consumer Defensive sector
        "sector_industrials": [],  # Industrials sector (includes aerospace/space)
        "sector_materials": [],    # Basic Materials sector (includes mining)
        "sector_utilities": [],    # Utilities sector
        "sector_realestate": [],   # Real Estate sector
        "sector_communication": [],# Communication Services sector (includes satellites)
    }
    
    all_tickers: Set[str] = set()
    
    # Market cap based screening (US exchanges only)
    # Expanded to get ~1500+ stocks with lower floor for emerging companies
    cap_screens = [
        # Mega cap > $500B (includes AAPL, MSFT, NVDA, GOOGL, AMZN, META, etc.)
        ("mega_cap", 500_000_000_000, 20_000_000_000_000, 60),
        # Large cap $50B - $500B
        ("large_cap", 50_000_000_000, 500_000_000_000, 200),
        # Mid cap $10B - $50B  
        ("mid_cap", 10_000_000_000, 50_000_000_000, 250),
        # Small cap $2B - $10B
        ("small_cap", 2_000_000_000, 10_000_000_000, 250),
        # Micro cap $500M - $2B (space, biotech, mining emerging companies)
        ("micro_cap", 500_000_000, 2_000_000_000, 200),
        # Nano cap $100M - $500M (early stage, high growth potential)
        ("nano_cap", 100_000_000, 500_000_000, 100),
    ]
    
    for category, min_cap, max_cap, count in cap_screens:
        tickers = _screen_by_market_cap(min_cap, max_cap, count)
        if tickers:
            universe[category].extend(tickers)
            all_tickers.update(tickers)
            print(f"    {category}: {len(tickers)} stocks")
            log_stocks(f"{category} tickers", tickers)
    
    # Sector based screening - lower market cap floor ($500M) to catch emerging companies
    # This covers: Mining (Materials), Space (Industrials), Biotech (Healthcare), etc.
    sector_screens = [
        # (category, sector_name, count, min_market_cap)
        ("sector_tech", "Technology", 120, 500_000_000),
        ("sector_healthcare", "Healthcare", 100, 300_000_000),  # Lower for biotech
        ("sector_financials", "Financial Services", 100, 500_000_000),
        ("sector_energy", "Energy", 80, 300_000_000),
        ("sector_consumer_disc", "Consumer Cyclical", 90, 500_000_000),
        ("sector_consumer_staples", "Consumer Defensive", 70, 500_000_000),
        ("sector_industrials", "Industrials", 100, 300_000_000),  # Lower for aerospace/space
        ("sector_materials", "Basic Materials", 80, 200_000_000),  # Lower for mining
        ("sector_utilities", "Utilities", 60, 500_000_000),
        ("sector_realestate", "Real Estate", 70, 500_000_000),
        ("sector_communication", "Communication Services", 80, 300_000_000),  # Lower for satellites
    ]
    
    for category, sector, count, min_cap in sector_screens:
        tickers = _screen_by_sector(sector, count, min_cap)
        if tickers:
            universe[category].extend(tickers)
            all_tickers.update(tickers)
            print(f"    {category}: {len(tickers)} stocks")
            log_stocks(f"{category} tickers", tickers)
    
    # Remove duplicates within each category
    for category in universe:
        universe[category] = list(dict.fromkeys(universe[category]))
    
    total = len(all_tickers)
    print(f"  Total unique tickers in universe: {total}")
    
    # Log a sample of the full universe
    all_list = list(all_tickers)
    logger.info(f"  🌐 FULL STOCK UNIVERSE ({total} stocks):")
    log_stocks("Sample of all stocks", all_list[:50], max_display=50)
    
    if total < 50:
        print("  WARNING: Low ticker count, falling back to ETF holdings...")
        etf_tickers = _fallback_etf_holdings()
        all_tickers.update(etf_tickers)
        universe["large_cap"].extend(etf_tickers)
        print(f"  Added {len(etf_tickers)} from ETF fallback, total: {len(all_tickers)}")
    
    return universe


def _screen_by_market_cap(min_cap: int, max_cap: int, count: int = 50) -> List[str]:
    """
    Screen stocks by market cap range on US exchanges.
    Uses pagination to get more than 25 results.
    """
    try:
        query = EquityQuery('AND', [
            EquityQuery('IS-IN', ['exchange', 'NMS', 'NYQ']),  # NASDAQ, NYSE
            EquityQuery('GT', ['intradaymarketcap', min_cap]),
            EquityQuery('LT', ['intradaymarketcap', max_cap])
        ])
        
        all_symbols = []
        offset = 0
        page_size = 25  # Yahoo limits to 25 per page
        
        while len(all_symbols) < count:
            result = yf.screen(query, count=page_size, offset=offset)
            quotes = result.get('quotes', [])
            if not quotes:
                break
            
            for q in quotes:
                ticker = _clean_ticker(q.get('symbol'))
                if ticker and ticker not in all_symbols:
                    all_symbols.append(ticker)
            
            offset += page_size
            if offset >= result.get('total', 0):
                break
        
        return all_symbols[:count]
    except Exception as e:
        print(f"    Screen by market cap failed: {e}")
        return []


def _screen_by_sector(sector: str, count: int = 30, min_market_cap: int = 500_000_000) -> List[str]:
    """
    Screen stocks by sector on US exchanges.
    Uses pagination to get more than 25 results.
    
    Args:
        sector: Yahoo Finance sector name
        count: Maximum number of stocks to return
        min_market_cap: Minimum market cap filter (default $500M for broader coverage)
    """
    try:
        query = EquityQuery('AND', [
            EquityQuery('EQ', ['sector', sector]),
            EquityQuery('IS-IN', ['exchange', 'NMS', 'NYQ']),  # NASDAQ, NYSE
            EquityQuery('GT', ['intradaymarketcap', min_market_cap])
        ])
        
        all_symbols = []
        offset = 0
        page_size = 25
        
        while len(all_symbols) < count:
            result = yf.screen(query, count=page_size, offset=offset)
            quotes = result.get('quotes', [])
            if not quotes:
                break
            
            for q in quotes:
                ticker = _clean_ticker(q.get('symbol'))
                if ticker and ticker not in all_symbols:
                    all_symbols.append(ticker)
            
            offset += page_size
            if offset >= result.get('total', 0):
                break
        
        return all_symbols[:count]
    except Exception as e:
        print(f"    Screen by sector {sector} failed: {e}")
        return []


# NOTE: _screen_by_industry() was removed - not used in current implementation


def _clean_ticker(symbol: str) -> Optional[str]:
    """Clean and validate a ticker symbol."""
    if not symbol or not isinstance(symbol, str):
        return None
    symbol = symbol.upper().strip()
    # Valid US ticker: 1-5 chars, letters only (or with hyphen/period like BRK-B, BF.B)
    if 1 <= len(symbol) <= 6 and symbol.replace('-', '').replace('.', '').isalpha():
        return symbol
    return None


def _fallback_etf_holdings() -> List[str]:
    """
    Fallback method: fetch holdings from major ETFs if screener fails.
    """
    print("    Using ETF holdings fallback...")
    all_holdings = []
    
    for etf_symbol in ['SPY', 'QQQ', 'IWM', 'XLK', 'XLV', 'XLF']:
        try:
            etf = yf.Ticker(etf_symbol)
            funds_data = etf.funds_data
            if funds_data and hasattr(funds_data, 'top_holdings'):
                holdings = funds_data.top_holdings
                if holdings is not None and not holdings.empty:
                    for t in holdings.index.tolist()[:15]:
                        clean = _clean_ticker(t)
                        if clean:
                            all_holdings.append(clean)
        except:
            pass
    
    return list(dict.fromkeys(all_holdings))  # Remove duplicates


# NOTE: _fetch_etf_holdings() was removed - use _fallback_etf_holdings() instead


def fetch_ticker_data(ticker: str, period: str = "1y") -> Optional[pd.DataFrame]:
    """
    Fetch historical data for a single ticker.
    
    Args:
        ticker: Stock symbol
        period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
    
    Returns:
        DataFrame with OHLCV data or None if fetch fails
    """
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        if df.empty:
            return None
        df['Ticker'] = ticker
        return df
    except Exception as e:
        print(f"Error fetching {ticker}: {str(e)}")
        return None


def fetch_ticker_info(ticker: str) -> Optional[Dict]:
    """
    Fetch comprehensive fundamental info for a single ticker.
    Includes valuation, growth, profitability, financial health, analyst ratings, and more.
    
    Args:
        ticker: Stock symbol
    
    Returns:
        Dictionary with ticker info or None if fetch fails
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        return {
            # === BASIC INFO ===
            'ticker': ticker,
            'name': info.get('longName', info.get('shortName', ticker)),
            'sector': info.get('sector', 'Unknown'),
            'industry': info.get('industry', 'Unknown'),
            
            # === PRICE DATA ===
            'current_price': info.get('currentPrice', info.get('regularMarketPrice')),
            'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
            'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
            'fifty_day_avg': info.get('fiftyDayAverage'),
            'two_hundred_day_avg': info.get('twoHundredDayAverage'),
            'fifty_two_week_change': info.get('52WeekChange'),  # NEW
            'sp500_52_week_change': info.get('SandP52WeekChange'),  # NEW - compare vs market
            
            # === VALUATION MULTIPLES ===
            'market_cap': info.get('marketCap', 0),
            'enterprise_value': info.get('enterpriseValue'),  # NEW
            'pe_ratio': info.get('trailingPE'),
            'forward_pe': info.get('forwardPE'),
            'peg_ratio': info.get('pegRatio'),
            'price_to_book': info.get('priceToBook'),
            'price_to_sales': info.get('priceToSalesTrailing12Months'),  # NEW
            'ev_to_revenue': info.get('enterpriseToRevenue'),  # NEW
            'ev_to_ebitda': info.get('enterpriseToEbitda'),  # NEW
            
            # === GROWTH METRICS ===
            'revenue_growth': info.get('revenueGrowth'),  # YoY
            'earnings_growth': info.get('earningsGrowth'),  # YoY
            'earnings_quarterly_growth': info.get('earningsQuarterlyGrowth'),  # NEW - latest quarter
            'revenue_quarterly_growth': info.get('revenueQuarterlyGrowth'),  # NEW - latest quarter
            
            # === PROFITABILITY & MARGINS ===
            'profit_margin': info.get('profitMargins'),
            'gross_margins': info.get('grossMargins'),  # NEW
            'ebitda_margins': info.get('ebitdaMargins'),  # NEW
            'operating_margins': info.get('operatingMargins'),  # NEW
            'roe': info.get('returnOnEquity'),
            'roa': info.get('returnOnAssets'),  # NEW
            
            # === FINANCIAL HEALTH ===
            'total_cash': info.get('totalCash'),  # NEW
            'total_debt': info.get('totalDebt'),  # NEW
            'free_cashflow': info.get('freeCashflow'),  # NEW
            'operating_cashflow': info.get('operatingCashflow'),  # NEW
            'debt_to_equity': info.get('debtToEquity'),
            'current_ratio': info.get('currentRatio'),  # NEW
            'quick_ratio': info.get('quickRatio'),  # NEW
            
            # === DIVIDENDS ===
            'dividend_yield': info.get('dividendYield', 0),
            'dividend_rate': info.get('dividendRate'),  # NEW - annual dividend $
            'payout_ratio': info.get('payoutRatio'),
            'ex_dividend_date': info.get('exDividendDate'),  # NEW
            
            # === TRADING & LIQUIDITY ===
            'avg_volume': info.get('averageVolume'),
            'avg_volume_10day': info.get('averageVolume10days'),  # NEW
            'beta': info.get('beta'),
            'float_shares': info.get('floatShares'),  # NEW
            'shares_outstanding': info.get('sharesOutstanding'),  # NEW
            
            # === SHORT INTEREST ===
            'short_ratio': info.get('shortRatio'),  # days to cover
            'shares_short': info.get('sharesShort'),  # NEW
            'short_percent_of_float': info.get('shortPercentOfFloat'),  # NEW
            'shares_short_prior_month': info.get('sharesShortPriorMonth'),  # NEW
            
            # === OWNERSHIP ===
            'insider_ownership': info.get('heldPercentInsiders'),
            'institutional_ownership': info.get('heldPercentInstitutions'),
            
            # === ANALYST RATINGS === (NEW SECTION)
            'analyst_recommendation': info.get('recommendationKey'),  # strong_buy, buy, hold, sell
            'analyst_rating_score': info.get('recommendationMean'),  # 1-5 scale (1=Strong Buy)
            'num_analyst_opinions': info.get('numberOfAnalystOpinions'),
            'target_mean_price': info.get('targetMeanPrice'),
            'target_high_price': info.get('targetHighPrice'),
            'target_low_price': info.get('targetLowPrice'),
            
            # === EARNINGS INFO === (NEW)
            'trailing_eps': info.get('trailingEps'),
            'forward_eps': info.get('forwardEps'),
            'book_value': info.get('bookValue'),
            'revenue_per_share': info.get('revenuePerShare'),
        }
    except Exception as e:
        print(f"Error fetching info for {ticker}: {str(e)}")
        return None


def fetch_historical_financials(ticker: str) -> Optional[Dict]:
    """
    Fetch historical financial data for a ticker (4 years of annual data).
    Includes revenue, net income, EPS, and cash flow trends.
    
    Args:
        ticker: Stock symbol
    
    Returns:
        Dictionary with historical financial trends or None if fetch fails
    """
    try:
        stock = yf.Ticker(ticker)
        
        result = {
            'ticker': ticker,
            'revenue_history': [],      # Last 4 years of revenue
            'net_income_history': [],   # Last 4 years of net income
            'eps_history': [],          # Last 4 years of EPS
            'fcf_history': [],          # Last 4 years of free cash flow
            'gross_profit_history': [], # Last 4 years of gross profit
            'ebitda_history': [],       # Last 4 years of EBITDA
            'revenue_growth_trend': [], # YoY growth rates
            'periods': [],              # Year labels
        }
        
        # Get annual income statement
        income = stock.income_stmt
        if income is not None and not income.empty:
            # Get years (columns are timestamps)
            years = [col.year if hasattr(col, 'year') else str(col)[:4] for col in income.columns[:4]]
            result['periods'] = years
            
            # Revenue
            if 'Total Revenue' in income.index:
                revenues = income.loc['Total Revenue'].values[:4]
                result['revenue_history'] = [round(float(r)/1e9, 2) if pd.notna(r) else None for r in revenues]
                # Calculate growth rates
                for i in range(len(revenues)-1):
                    if pd.notna(revenues[i]) and pd.notna(revenues[i+1]) and revenues[i+1] != 0:
                        growth = ((revenues[i] / revenues[i+1]) - 1) * 100
                        result['revenue_growth_trend'].append(round(growth, 1))
            
            # Net Income
            if 'Net Income' in income.index:
                net_incomes = income.loc['Net Income'].values[:4]
                result['net_income_history'] = [round(float(n)/1e9, 2) if pd.notna(n) else None for n in net_incomes]
            
            # Gross Profit
            if 'Gross Profit' in income.index:
                gross = income.loc['Gross Profit'].values[:4]
                result['gross_profit_history'] = [round(float(g)/1e9, 2) if pd.notna(g) else None for g in gross]
            
            # EBITDA
            if 'EBITDA' in income.index:
                ebitda = income.loc['EBITDA'].values[:4]
                result['ebitda_history'] = [round(float(e)/1e9, 2) if pd.notna(e) else None for e in ebitda]
            
            # Basic EPS
            if 'Basic EPS' in income.index:
                eps = income.loc['Basic EPS'].values[:4]
                result['eps_history'] = [round(float(e), 2) if pd.notna(e) else None for e in eps]
        
        # Get cash flow statement for FCF
        cashflow = stock.cashflow
        if cashflow is not None and not cashflow.empty:
            if 'Free Cash Flow' in cashflow.index:
                fcf = cashflow.loc['Free Cash Flow'].values[:4]
                result['fcf_history'] = [round(float(f)/1e9, 2) if pd.notna(f) else None for f in fcf]
        
        return result
        
    except Exception as e:
        print(f"Error fetching historical financials for {ticker}: {str(e)}")
        return None


def fetch_historical_financials_batch(tickers: List[str], max_workers: int = 3) -> Dict[str, Dict]:
    """
    Fetch historical financials for multiple tickers with rate limiting.
    
    Args:
        tickers: List of stock symbols
        max_workers: Maximum parallel threads (keep low to avoid rate limits)
    
    Returns:
        Dictionary mapping ticker to historical financial data
    """
    results = {}
    print(f"    Fetching historical financials for {len(tickers)} tickers...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(fetch_historical_financials, ticker): ticker 
            for ticker in tickers
        }
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                data = future.result()
                if data is not None:
                    results[ticker] = data
            except Exception as e:
                print(f"Error processing historical data for {ticker}: {str(e)}")
    
    print(f"    Fetched historical financials for {len(results)}/{len(tickers)} tickers")
    
    # Log sample of historical data
    if results:
        sample_ticker = list(results.keys())[0]
        sample = results[sample_ticker]
        if sample.get('revenue_history'):
            periods = sample.get('periods', [])
            rev = sample.get('revenue_history', [])
            ni = sample.get('net_income_history', [])
            print(f"    📊 Sample ({sample_ticker}): Periods {periods}")
            print(f"       Revenue: {['$' + str(round(r, 1)) + 'B' if r else 'N/A' for r in rev]}")
            print(f"       Net Inc: {['$' + str(round(n, 2)) + 'B' if n else 'N/A' for n in ni]}")
    
    return results


def fetch_multiple_tickers(tickers: List[str], period: str = "1y", 
                          max_workers: int = 10) -> Dict[str, pd.DataFrame]:
    """
    Fetch data for multiple tickers in parallel.
    
    Args:
        tickers: List of stock symbols
        period: Time period
        max_workers: Maximum parallel threads
    
    Returns:
        Dictionary mapping ticker to DataFrame
    """
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(fetch_ticker_data, ticker, period): ticker 
            for ticker in tickers
        }
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                data = future.result()
                if data is not None:
                    results[ticker] = data
            except Exception as e:
                print(f"Error processing {ticker}: {str(e)}")
    return results


def fetch_multiple_ticker_info(tickers: List[str], 
                               max_workers: int = 2,
                               batch_size: int = 20,
                               delay_between_batches: float = 3.0) -> List[Dict]:
    """
    Fetch info for multiple tickers with rate limiting to avoid Yahoo Finance blocks.
    
    Args:
        tickers: List of stock symbols
        max_workers: Maximum parallel threads (2 for safety with 1000+ stocks)
        batch_size: Number of tickers to process per batch (20 = very safe)
        delay_between_batches: Seconds to wait between batches (3s for 1000+ stocks)
    
    Returns:
        List of ticker info dictionaries
    """
    results = []
    total_batches = (len(tickers) + batch_size - 1) // batch_size
    failed_count = 0
    successful_tickers = []
    
    logger.info(f"  🔄 BATCH PROCESSING: {len(tickers)} tickers in {total_batches} batches (batch_size={batch_size})")
    
    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len(tickers))
        batch_tickers = tickers[start_idx:end_idx]
        
        # Log each batch being processed
        if VERBOSE_LOGGING and (batch_num % 5 == 0 or batch_num == total_batches - 1):
            logger.info(f"  📦 Batch {batch_num+1}/{total_batches}: Processing {', '.join(batch_tickers[:10])}{'...' if len(batch_tickers) > 10 else ''}")
        
        # Process batch with limited parallelism
        batch_success = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ticker = {
                executor.submit(fetch_ticker_info, ticker): ticker 
                for ticker in batch_tickers
            }
            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                try:
                    info = future.result()
                    if info is not None:
                        results.append(info)
                        successful_tickers.append(ticker)
                        batch_success.append(ticker)
                    else:
                        failed_count += 1
                except Exception as e:
                    failed_count += 1
                    # Only print first few errors to avoid spam
                    if failed_count <= 5:
                        print(f"      Error fetching {ticker}: {str(e)[:50]}")
        
        # Rate limiting: pause between batches (except after last batch)
        if batch_num < total_batches - 1:
            time.sleep(delay_between_batches)
            # Progress indicator every 3 batches
            if (batch_num + 1) % 3 == 0:
                print(f"      Processed {end_idx}/{len(tickers)} stocks ({len(results)} success, {failed_count} failed)...")
    
    print(f"      Final: {len(results)} loaded, {failed_count} failed")
    
    # Log sample of new comprehensive fields (first successful stock)
    if results and VERBOSE_LOGGING:
        sample = results[0]
        ticker = sample.get('ticker', 'N/A')
        new_fields = []
        if sample.get('analyst_recommendation'):
            new_fields.append(f"Analyst: {sample['analyst_recommendation']}")
        if sample.get('target_mean_price'):
            new_fields.append(f"Target: ${sample['target_mean_price']:.0f}")
        if sample.get('ev_to_ebitda'):
            new_fields.append(f"EV/EBITDA: {sample['ev_to_ebitda']:.1f}")
        if sample.get('free_cashflow'):
            fcf_b = sample['free_cashflow'] / 1e9
            new_fields.append(f"FCF: ${fcf_b:.1f}B")
        if sample.get('short_percent_of_float'):
            new_fields.append(f"Short%: {sample['short_percent_of_float']*100:.1f}%")
        if new_fields:
            logger.info(f"  📊 Sample new fields ({ticker}): {' | '.join(new_fields)}")
    
    return results


def get_current_prices(tickers: List[str]) -> Dict[str, float]:
    """
    Get current prices for a list of tickers.
    
    Args:
        tickers: List of stock symbols
    
    Returns:
        Dictionary mapping ticker to current price
    """
    if not tickers:
        return {}
    
    prices = {}
    
    # Remove duplicates and None values
    tickers = list(set(t for t in tickers if t))
    
    try:
        data = yf.download(tickers, period="5d", progress=False)
        
        if data.empty:
            raise ValueError("Empty data returned from yfinance")
        
        # Handle different data structures from yfinance
        if len(tickers) == 1:
            # Single ticker - data has simple columns
            if 'Close' in data.columns:
                close_data = data['Close'].dropna()
                if not close_data.empty:
                    prices[tickers[0]] = float(close_data.iloc[-1])
        else:
            # Multiple tickers - data has MultiIndex columns
            if 'Close' in data.columns:
                close_data = data['Close']
                for ticker in tickers:
                    try:
                        if ticker in close_data.columns:
                            ticker_close = close_data[ticker].dropna()
                            if not ticker_close.empty:
                                prices[ticker] = float(ticker_close.iloc[-1])
                    except Exception:
                        pass
            elif isinstance(data.columns, pd.MultiIndex):
                # Alternative MultiIndex structure
                for ticker in tickers:
                    try:
                        if ('Close', ticker) in data.columns:
                            ticker_close = data[('Close', ticker)].dropna()
                            if not ticker_close.empty:
                                prices[ticker] = float(ticker_close.iloc[-1])
                    except Exception:
                        pass
    except Exception as e:
        print(f"Bulk download failed: {str(e)}, trying individual fetches...")
    
    # Fallback: fetch missing tickers individually
    missing_tickers = [t for t in tickers if t not in prices]
    for ticker in missing_tickers:
        try:
            stock = yf.Ticker(ticker)
            # Try fast_info first (faster)
            try:
                price = stock.fast_info.get('lastPrice') or stock.fast_info.get('regularMarketPrice')
                if price and price > 0:
                    prices[ticker] = float(price)
                    continue
            except:
                pass
            
            # Fallback to info
            info = stock.info
            price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
            if price and price > 0:
                prices[ticker] = float(price)
            else:
                # Last resort: use history
                hist = stock.history(period="5d")
                if not hist.empty and 'Close' in hist.columns:
                    close_data = hist['Close'].dropna()
                    if not close_data.empty:
                        prices[ticker] = float(close_data.iloc[-1])
        except Exception as e:
            print(f"  Warning: Could not fetch price for {ticker}: {e}")
    
    return prices


def fetch_index_data() -> Dict[str, Dict]:
    """
    Fetch performance data for major market indexes.
    
    Returns:
        Dictionary with index performance metrics
    """
    index_data = {}
    for name, symbol in INDEXES.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1y")
            
            if hist.empty:
                continue
            
            current = hist['Close'].iloc[-1]
            
            # Calculate returns for various periods
            returns = {}
            for period_name, days in [('1d', 1), ('1w', 5), ('1mo', 21), 
                                       ('3mo', 63), ('6mo', 126), ('ytd', None), ('1y', 252)]:
                try:
                    if period_name == 'ytd':
                        # YTD calculation - use timezone-aware comparison
                        year_start = pd.Timestamp(datetime(datetime.now().year, 1, 1)).tz_localize(hist.index.tz)
                        ytd_data = hist[hist.index >= year_start]
                        if len(ytd_data) > 1:
                            returns['ytd'] = (current / ytd_data['Close'].iloc[0] - 1) * 100
                    elif days and len(hist) > days:
                        past_price = hist['Close'].iloc[-days-1]
                        returns[period_name] = (current / past_price - 1) * 100
                except Exception:
                    pass  # Skip this period if calculation fails
            
            index_data[name] = {
                'symbol': symbol,
                'current': round(current, 2),
                'returns': {k: round(v, 2) for k, v in returns.items()}
            }
        except Exception as e:
            print(f"Error fetching index {name}: {str(e)}")
    
    return index_data


def fetch_sector_performance() -> Dict[str, Dict]:
    """
    Fetch performance data for all sectors using ETF proxies.
    Uses bulk download for efficiency.
    
    Returns:
        Dictionary with sector performance metrics
    """
    # Collect all sector ETFs + SPY for relative strength
    sector_etfs = [config['etf'] for sector, config in SECTORS.items()]
    all_tickers = sector_etfs + ['SPY']
    
    # Bulk download
    try:
        hist_data = yf.download(all_tickers, period="1y", progress=False, threads=True, group_by='ticker')
        if hist_data.empty:
            return {}
    except Exception as e:
        print(f"Error bulk downloading sector data: {e}")
        return {}
    
    # Get SPY data for relative strength calculation
    spy_close = None
    spy_return_3mo = 0
    try:
        if 'SPY' in hist_data.columns.get_level_values(0):
            spy_close = hist_data['SPY']['Close'].dropna()
            if len(spy_close) >= 63:
                spy_return_3mo = (spy_close.iloc[-1] / spy_close.iloc[-63]) - 1
    except Exception:
        pass
    
    sector_data = {}
    for sector, config in SECTORS.items():
        etf = config['etf']
        try:
            if etf not in hist_data.columns.get_level_values(0):
                continue
            
            close_data = hist_data[etf]['Close'].dropna()
            if len(close_data) < 2:
                continue
            
            current = close_data.iloc[-1]
            
            # Calculate returns
            returns = {}
            for period_name, days in [('1mo', 21), ('3mo', 63), ('6mo', 126), ('1y', 252)]:
                if len(close_data) > days:
                    past_price = close_data.iloc[-days-1]
                    returns[period_name] = (current / past_price - 1) * 100
            
            # Calculate relative strength vs SPY
            relative_strength = 0
            if spy_close is not None and len(close_data) >= 63:
                sector_return = (current / close_data.iloc[-63]) - 1
                relative_strength = (sector_return - spy_return_3mo) * 100
            
            sector_data[sector] = {
                'etf': etf,
                'current': round(float(current), 2),
                'returns': {k: round(v, 2) for k, v in returns.items()},
                'relative_strength_3mo': round(relative_strength, 2)
            }
        except Exception as e:
            print(f"Error processing sector {sector}: {str(e)}")
    
    return sector_data


# =============================================================================
# ETF DATA FETCHING - DYNAMIC FROM WEB + FALLBACK
# =============================================================================
# Primary: Fetch popular ETFs from etfdb.com (largest ETF database)
# Fallback: Use well-known benchmark ETFs if web fetch fails
# All PRICES are fetched LIVE from Yahoo Finance


def fetch_popular_etfs_from_web() -> Dict[str, List[str]]:
    """
    Fetch popular ETFs dynamically from etfdb.com.
    Falls back to curated list if web fetch fails.
    
    Returns:
        Dictionary with ETF categories and tickers
    """
    print("    Fetching popular ETFs from web...")
    
    etf_categories = {
        "total_market": [],
        "growth": [],
        "value": [],
        "dividend": [],
        "sector_tech": [],
        "sector_healthcare": [],
        "sector_financials": [],
        "sector_energy": [],
        "commodities": [],
        "bonds": [],
        "international": [],
        "thematic": [],
    }
    
    try:
        # Try to fetch from etfdb.com's most popular ETFs
        # Using their public pages which list top ETFs by AUM
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Fetch top ETFs by AUM from etfdb
        response = requests.get(
            'https://etfdb.com/compare/market-cap/',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            # Parse the page for ETF tickers
            # Look for ticker symbols in the HTML
            import re
            # Find patterns like "/etf/VOO/" or ticker symbols
            tickers = re.findall(r'/etf/([A-Z]{2,5})/', response.text)
            unique_tickers = list(dict.fromkeys(tickers))[:100]  # Top 100 unique
            
            if len(unique_tickers) >= 20:
                print(f"    Found {len(unique_tickers)} ETFs from web")
                # Categorize them using yfinance info
                for ticker in unique_tickers[:50]:  # Check top 50
                    try:
                        info = yf.Ticker(ticker).info
                        category = info.get('category', '').lower()
                        
                        if 'total' in category or 'broad' in category:
                            etf_categories["total_market"].append(ticker)
                        elif 'growth' in category:
                            etf_categories["growth"].append(ticker)
                        elif 'value' in category:
                            etf_categories["value"].append(ticker)
                        elif 'dividend' in category:
                            etf_categories["dividend"].append(ticker)
                        elif 'tech' in category or 'semiconductor' in category:
                            etf_categories["sector_tech"].append(ticker)
                        elif 'health' in category or 'biotech' in category:
                            etf_categories["sector_healthcare"].append(ticker)
                        elif 'financ' in category or 'bank' in category:
                            etf_categories["sector_financials"].append(ticker)
                        elif 'energy' in category or 'oil' in category:
                            etf_categories["sector_energy"].append(ticker)
                        elif 'commodity' in category or 'gold' in category or 'metal' in category:
                            etf_categories["commodities"].append(ticker)
                        elif 'bond' in category or 'treasury' in category or 'fixed' in category:
                            etf_categories["bonds"].append(ticker)
                        elif 'international' in category or 'emerging' in category or 'foreign' in category:
                            etf_categories["international"].append(ticker)
                        else:
                            etf_categories["thematic"].append(ticker)
                    except:
                        continue
                
                # If we got good data, return it
                total = sum(len(v) for v in etf_categories.values())
                if total >= 20:
                    return etf_categories
                    
    except Exception as e:
        print(f"    Web fetch failed: {e}, using fallback ETFs")
    
    # Fallback: Curated list of most popular ETFs (rarely changes)
    print("    Using curated popular ETF list...")
    fallback_etfs = {
        "total_market": ["VOO", "VTI", "SPY", "IVV", "SPLG"],
        "growth": ["VUG", "SCHG", "IWF", "VOOG", "MGK"],
        "value": ["VTV", "SCHV", "IWD", "VOOV", "RPV"],
        "dividend": ["SCHD", "VIG", "VYM", "DVY", "DGRO"],
        "sector_tech": ["VGT", "XLK", "QQQ", "SMH", "SOXX"],
        "sector_healthcare": ["VHT", "XLV", "XBI", "IBB", "ARKG"],
        "sector_financials": ["VFH", "XLF", "KBE", "KRE", "IAI"],
        "sector_energy": ["VDE", "XLE", "XOP", "OIH", "AMLP"],
        "commodities": ["GLD", "SLV", "USO", "UNG", "DBA", "DBC", "PDBC"],
        "bonds": ["BND", "AGG", "TLT", "SHY", "LQD", "HYG", "TIP"],
        "international": ["VEA", "VWO", "VXUS", "EFA", "EEM", "VGK", "VPL", "FXI", "EWJ"],
        "thematic": ["ARKK", "ARKW", "ARKG", "ICLN", "TAN", "CIBR", "BOTZ", "SKYY", "CLOU"],
    }
    
    # Log all ETFs being used
    all_etfs = []
    for cat, etfs in fallback_etfs.items():
        all_etfs.extend(etfs)
        log_stocks(f"ETF {cat}", etfs)
    logger.info(f"  📊 TOTAL ETFs: {len(all_etfs)} across {len(fallback_etfs)} categories")
    
    return fallback_etfs


def fetch_commodity_data() -> Dict[str, Dict]:
    """
    Fetch live price data for commodity ETFs.
    Uses hardcoded ETF tickers (GLD, SLV, USO, etc.) - Yahoo doesn't support ETF screening.
    
    Returns:
        Dictionary with commodity/metal data
    """
    print("    Fetching commodity ETFs (using standard benchmark tickers)...")
    commodity_data = {}
    
    # Industry-standard commodity ETFs (hardcoded because Yahoo doesn't support ETF screening)
    # These are the most liquid, widely-used benchmarks for each commodity category
    commodity_tickers = {
        "Gold": "GLD",              # SPDR Gold Shares - largest gold ETF
        "Silver": "SLV",            # iShares Silver Trust
        "Oil": "USO",               # United States Oil Fund
        "Natural Gas": "UNG",       # United States Natural Gas Fund
        "Agriculture": "DBA",       # Invesco DB Agriculture Fund
        "Metals": "DBB",            # Invesco DB Base Metals Fund
        "Commodities Broad": "DJP"  # iPath Bloomberg Commodity Index
    }
    
    for category, ticker in commodity_tickers.items():
        if not ticker:
            continue
            
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1y")
            
            if hist.empty:
                continue
            
            current = hist['Close'].iloc[-1]
            
            # Calculate returns
            returns = {}
            for period_name, days in [('1mo', 21), ('3mo', 63), ('6mo', 126), ('1y', 252)]:
                if len(hist) > days:
                    past_price = hist['Close'].iloc[-days-1]
                    returns[period_name] = (current / past_price - 1) * 100
            
            commodity_data[category] = {
                'ticker': ticker,
                'current': round(current, 2),
                'returns': {k: round(v, 2) for k, v in returns.items()}
            }
        except Exception as e:
            print(f"Error fetching commodity {category}: {str(e)}")
    
    return commodity_data


def fetch_fixed_income_data() -> Dict[str, Dict]:
    """
    Fetch live price data for fixed income ETFs.
    Uses hardcoded ETF tickers (TLT, SHY, LQD, etc.) - Yahoo doesn't support ETF screening.
    
    Returns:
        Dictionary with fixed income data
    """
    print("    Fetching fixed income ETFs (using standard benchmark tickers)...")
    fi_data = {}
    
    # Industry-standard bond ETFs (hardcoded because Yahoo doesn't support ETF screening)
    # These are the most liquid, widely-used benchmarks for each fixed income category
    fi_tickers = {
        "Treasury Short": "SHY",    # iShares 1-3 Year Treasury Bond ETF
        "Treasury Long": "TLT",     # iShares 20+ Year Treasury Bond ETF
        "Corporate Bond": "LQD",    # iShares iBoxx $ Investment Grade Corp Bond ETF
        "High Yield": "HYG",        # iShares iBoxx $ High Yield Corp Bond ETF
        "TIPS": "TIP"               # iShares TIPS Bond ETF
    }
    
    for category, ticker in fi_tickers.items():
        if not ticker:
            continue
            
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1y")
            info = stock.info
            
            if hist.empty:
                continue
            
            current = hist['Close'].iloc[-1]
            
            # Calculate returns
            returns = {}
            for period_name, days in [('1mo', 21), ('3mo', 63), ('6mo', 126), ('1y', 252)]:
                if len(hist) > days:
                    past_price = hist['Close'].iloc[-days-1]
                    returns[period_name] = (current / past_price - 1) * 100
            
            fi_data[category] = {
                'ticker': ticker,
                'current': round(current, 2),
                'yield': info.get('yield', info.get('dividendYield', 0)),
                'returns': {k: round(v, 2) for k, v in returns.items()}
            }
        except Exception as e:
            print(f"Error fetching fixed income {category}: {str(e)}")
    
    return fi_data


def fetch_international_data() -> Dict[str, Dict]:
    """
    Fetch live price data for international market ETFs.
    Uses hardcoded ETF tickers (VEA, VWO, VGK, etc.) - Yahoo doesn't support ETF screening.
    
    Returns:
        Dictionary with international market data
    """
    print("    Fetching international ETFs (using standard benchmark tickers)...")
    intl_data = {}
    
    # Industry-standard international ETFs (hardcoded because Yahoo doesn't support ETF screening)
    # These are the most liquid, widely-used benchmarks for each region
    intl_tickers = {
        "Developed Markets": "VEA",   # Vanguard FTSE Developed Markets ETF
        "Emerging Markets": "VWO",    # Vanguard FTSE Emerging Markets ETF
        "Europe": "VGK",              # Vanguard FTSE Europe ETF
        "Asia Pacific": "VPL",        # Vanguard FTSE Pacific ETF
        "China": "FXI",               # iShares China Large-Cap ETF
        "Japan": "EWJ"                # iShares MSCI Japan ETF
    }
    
    for region, ticker in intl_tickers.items():
        if not ticker:
            continue
            
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1y")
            
            if hist.empty:
                continue
            
            current = hist['Close'].iloc[-1]
            
            # Calculate returns
            returns = {}
            for period_name, days in [('1mo', 21), ('3mo', 63), ('6mo', 126), ('1y', 252)]:
                if len(hist) > days:
                    past_price = hist['Close'].iloc[-days-1]
                    returns[period_name] = (current / past_price - 1) * 100
            
            intl_data[region] = {
                'ticker': ticker,
                'current': round(current, 2),
                'returns': {k: round(v, 2) for k, v in returns.items()}
            }
        except Exception as e:
            print(f"Error fetching international {region}: {str(e)}")
    
    return intl_data


def fetch_growth_etf_data() -> Dict[str, Dict]:
    """
    Fetch live price data for growth and thematic ETFs.
    Attempts to fetch popular ETFs from web, falls back to curated list.
    
    Returns:
        Dictionary with growth/thematic ETF data organized by theme
    """
    print("    Fetching thematic/growth ETFs...")
    growth_data = {}
    
    # Get ETFs from web (or fallback)
    popular_etfs = fetch_popular_etfs_from_web()
    
    # Build theme_tickers from the dynamic data
    theme_tickers = {
        "Total Market": popular_etfs.get("total_market", ["VOO", "VTI"])[:3],
        "Growth": popular_etfs.get("growth", ["VUG", "SCHG"])[:3],
        "Value": popular_etfs.get("value", ["VTV", "SCHV"])[:3],
        "Dividend": popular_etfs.get("dividend", ["SCHD", "VIG", "VYM"])[:3],
        "Technology": popular_etfs.get("sector_tech", ["QQQ", "VGT", "SMH"])[:3],
        "Healthcare": popular_etfs.get("sector_healthcare", ["XLV", "XBI"])[:2],
        "Financials": popular_etfs.get("sector_financials", ["XLF", "VFH"])[:2],
        "Energy": popular_etfs.get("sector_energy", ["XLE", "VDE"])[:2],
        "International": popular_etfs.get("international", ["VEA", "VWO", "EFA"])[:3],
        "Thematic/Innovation": popular_etfs.get("thematic", ["ARKK", "ICLN", "CIBR"])[:3],
    }
    
    for theme, etfs in theme_tickers.items():
        theme_data = {}
        for ticker in etfs:
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="1y")
                info = stock.info
                
                if hist.empty:
                    continue
                
                current = hist['Close'].iloc[-1]
                
                # Calculate returns
                returns = {}
                for period_name, days in [('1mo', 21), ('3mo', 63), ('6mo', 126), ('1y', 252)]:
                    if len(hist) > days:
                        past_price = hist['Close'].iloc[-days-1]
                        returns[period_name] = (current / past_price - 1) * 100
                
                theme_data[ticker] = {
                    'name': info.get('longName', info.get('shortName', ticker)),
                    'current': round(current, 2),
                    'returns': {k: round(v, 2) for k, v in returns.items()},
                    'expense_ratio': info.get('annualReportExpenseRatio', 0),
                    'aum': info.get('totalAssets', 0)
                }
            except Exception as e:
                continue
        
        if theme_data:
            growth_data[theme] = theme_data
    
    return growth_data


def fetch_dollar_index() -> Dict:
    """
    Fetch US Dollar Index (DXY) data.
    
    Returns:
        Dictionary with DXY data
    """
    try:
        # UUP is a USD ETF proxy
        ticker = yf.Ticker('UUP')
        hist = ticker.history(period="1y")
        
        if hist.empty:
            return {}
        
        current = hist['Close'].iloc[-1]
        
        returns = {}
        for period_name, days in [('1mo', 21), ('3mo', 63), ('6mo', 126)]:
            if len(hist) > days:
                past_price = hist['Close'].iloc[-days-1]
                returns[period_name] = (current / past_price - 1) * 100
        
        return {
            'ticker': 'UUP',
            'current': round(current, 2),
            'returns': {k: round(v, 2) for k, v in returns.items()},
            'trend': 'strengthening' if returns.get('1mo', 0) > 0 else 'weakening'
        }
    except Exception as e:
        print(f"Error fetching dollar index: {str(e)}")
        return {}


def fetch_vix() -> Dict:
    """
    Fetch VIX (volatility index) data with historical context.
    
    Returns:
        Dictionary with VIX data including historical perspective
    """
    try:
        ticker = yf.Ticker('^VIX')
        hist = ticker.history(period="1y")  # Get 1 year for historical context
        
        if hist.empty:
            return {}
        
        current = hist['Close'].iloc[-1]
        avg_30d = hist['Close'].tail(21).mean()
        avg_1y = hist['Close'].mean()  # Historical average
        high_1y = hist['Close'].max()
        low_1y = hist['Close'].min()
        
        # Determine alert level
        if current >= 30:
            alert_level = "HIGH_FEAR"
            alert_emoji = "🔴"
            recommendation = "Defensive mode - increase cash, avoid new aggressive positions"
        elif current >= 25:
            alert_level = "ELEVATED"
            alert_emoji = "🟡"
            recommendation = "Caution - reduce position sizes, tighten stop-losses"
        elif current >= 20:
            alert_level = "NORMAL"
            alert_emoji = "🟢"
            recommendation = "Normal conditions - proceed with standard risk management"
        else:
            alert_level = "LOW"
            alert_emoji = "🟢"
            recommendation = "Low fear - favorable for risk-on positions, but complacency risk"
        
        return {
            'current': round(current, 2),
            'level': round(current, 2),  # Numeric value for email display
            'avg_30d': round(avg_30d, 2),
            'avg_1y': round(avg_1y, 2),
            'historical_avg': round(avg_1y, 2),  # Alias for clarity
            'high_1y': round(high_1y, 2),
            'low_1y': round(low_1y, 2),
            'warning_level': 'extreme' if current >= 30 else 'elevated' if current >= 25 else 'normal',
            'status': 'low' if current < 15 else 'elevated' if current < 25 else 'high',
            'vs_average': 'above' if current > avg_30d else 'below',
            'alert_level': alert_level,
            'alert_emoji': alert_emoji,
            'recommendation': recommendation,
            'percentile': round((current - low_1y) / (high_1y - low_1y) * 100, 1) if high_1y != low_1y else 50,
            'change_pct': round((current - avg_30d) / avg_30d * 100, 1) if avg_30d > 0 else 0
        }
    except Exception as e:
        print(f"Error fetching VIX: {str(e)}")
        return {}


def fetch_treasury_yields() -> Dict:
    """
    Fetch treasury yield data using ETF proxies.
    
    Returns:
        Dictionary with yield curve data
    """
    yields = {}
    proxies = {
        '2yr': 'SHY',   # 1-3 year treasury
        '10yr': 'IEF',  # 7-10 year treasury
        '30yr': 'TLT'   # 20+ year treasury
    }
    
    for maturity, ticker in proxies.items():
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            yields[maturity] = {
                'proxy_etf': ticker,
                'yield': info.get('yield', 0)
            }
        except Exception as e:
            print(f"Error fetching yield {maturity}: {str(e)}")
    
    return yields


def fetch_market_news(max_news: int = 15) -> List[Dict]:
    """
    Fetch recent market and geopolitical news from Yahoo Finance.
    Uses major market tickers to get broad market news coverage.
    
    Args:
        max_news: Maximum number of news items to return
    
    Returns:
        List of news items with title, publisher, summary, and date
    """
    print("  Fetching market news from Yahoo Finance...")
    all_news = []
    seen_titles = set()
    
    # Tickers that give broad market/geopolitical news coverage
    # Using popular stocks + ETFs that attract diverse news
    news_tickers = ['AAPL', 'MSFT', 'NVDA', 'SPY', 'QQQ', 'GLD', 'XLE', 'TLT', 'EEM']
    
    for ticker_symbol in news_tickers:
        try:
            ticker = yf.Ticker(ticker_symbol)
            news = ticker.news
            
            if news:
                for item in news[:5]:  # Get top 5 from each ticker
                    # Handle new nested structure: news item has 'content' key
                    content = item.get('content', item)  # Fall back to item if no content key
                    
                    title = content.get('title', '')
                    if not title:
                        continue
                    
                    # Skip duplicates
                    if title in seen_titles:
                        continue
                    seen_titles.add(title)
                    
                    # Extract publisher from nested structure
                    provider = content.get('provider', {})
                    publisher = provider.get('displayName', 'Unknown') if isinstance(provider, dict) else 'Unknown'
                    
                    # Extract URL from nested structure
                    canonical = content.get('canonicalUrl', {})
                    link = canonical.get('url', '') if isinstance(canonical, dict) else ''
                    
                    # Extract publish date
                    pub_date = content.get('pubDate', '')
                    
                    # Extract summary if available
                    summary = content.get('summary', '')[:200] if content.get('summary') else ''
                    
                    # Extract relevant fields
                    news_item = {
                        'title': title,
                        'publisher': publisher,
                        'link': link,
                        'published': pub_date,
                        'summary': summary,
                        'type': content.get('contentType', 'STORY')
                    }
                    
                    # Look for geopolitical keywords in title AND summary
                    text_to_search = (title + ' ' + summary).lower()
                    geopolitical_keywords = [
                        'tariff', 'trade war', 'sanction', 'china', 'russia', 'ukraine',
                        'fed', 'federal reserve', 'interest rate', 'inflation', 'recession',
                        'election', 'policy', 'regulation', 'antitrust', 'oil', 'opec',
                        'supply chain', 'semiconductor', 'chip', 'war', 'conflict',
                        'currency', 'dollar', 'yuan', 'euro', 'central bank', 'treasury',
                        'trump', 'biden', 'congress', 'senate', 'nato', 'middle east',
                        'iran', 'israel', 'taiwan', 'korea', 'import', 'export'
                    ]
                    news_item['is_geopolitical'] = any(kw in text_to_search for kw in geopolitical_keywords)
                    
                    all_news.append(news_item)
                    
                    if len(all_news) >= max_news * 2:  # Get extra for filtering
                        break
        except Exception as e:
            print(f"    Error fetching news for {ticker_symbol}: {e}")
            continue
    
    # Sort by geopolitical priority first
    all_news.sort(key=lambda x: not x.get('is_geopolitical', False))
    
    # Return limited results
    result = all_news[:max_news]
    print(f"    Found {len(result)} relevant news items ({sum(1 for n in result if n.get('is_geopolitical'))} geopolitical)")
    
    return result


def fetch_all_market_data() -> Dict[str, Any]:
    """
    Fetch all market data needed for analysis.
    
    Returns:
        Comprehensive dictionary with all market data
    """
    print("  Fetching index data...")
    index_data = fetch_index_data()
    
    print("  Fetching sector data...")
    sector_data = fetch_sector_performance()
    
    print("  Fetching commodity data...")
    commodity_data = fetch_commodity_data()
    
    print("  Fetching fixed income data...")
    fixed_income_data = fetch_fixed_income_data()
    
    print("  Fetching international data...")
    international_data = fetch_international_data()
    
    print("  Fetching growth/thematic ETF data...")
    growth_etf_data = fetch_growth_etf_data()
    
    print("  Fetching macro indicators...")
    dollar_data = fetch_dollar_index()
    vix_data = fetch_vix()
    yield_data = fetch_treasury_yields()
    
    # Fetch market news for geopolitical context
    market_news = fetch_market_news(max_news=15)
    
    return {
        'timestamp': datetime.now().isoformat(),
        'indexes': index_data,
        'sectors': sector_data,
        'commodities': commodity_data,
        'fixed_income': fixed_income_data,
        'international': international_data,
        'growth_etfs': growth_etf_data,
        'macro': {
            'dollar': dollar_data,
            'vix': vix_data,
            'yields': yield_data
        },
        'market_news': market_news
    }


def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate technical indicators for a price DataFrame.
    
    Args:
        df: DataFrame with OHLCV data
    
    Returns:
        DataFrame with added technical indicator columns
    """
    if df is None or df.empty:
        return df
    
    # Simple Moving Averages
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=TECHNICAL_PARAMS['rsi_period']).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=TECHNICAL_PARAMS['rsi_period']).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # Average True Range (ATR)
    high_low = df['High'] - df['Low']
    high_close = abs(df['High'] - df['Close'].shift())
    low_close = abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(window=TECHNICAL_PARAMS['atr_period']).mean()
    
    # Volume SMA
    df['Volume_SMA'] = df['Volume'].rolling(window=20).mean()
    df['Volume_Ratio'] = df['Volume'] / df['Volume_SMA']
    
    # Golden/Death Cross signals
    df['Golden_Cross'] = (df['SMA_50'] > df['SMA_200']) & (df['SMA_50'].shift() <= df['SMA_200'].shift())
    df['Death_Cross'] = (df['SMA_50'] < df['SMA_200']) & (df['SMA_50'].shift() >= df['SMA_200'].shift())
    
    return df


def fetch_historical_context() -> Dict:
    """
    Fetch 5-year historical context to reduce recency bias.
    Includes sector performance, P/E ranges, and market cycle indicators.
    Uses bulk download for efficiency.
    
    Returns:
        Dictionary with historical perspective data
    """
    print("  Fetching 5-year historical context...")
    context = {
        'sector_5yr_performance': {},
        'sp500_pe_context': {},
        'market_cycle_indicators': {},
        'historical_vix': {}
    }
    
    try:
        # Collect all tickers needed
        sector_etfs = [config['etf'] for sector, config in SECTORS.items()]
        all_tickers = sector_etfs + ['SPY', 'SHY', 'IEF', '^VIX']
        
        # Bulk download 5 years of data
        print("    Downloading 5-year historical data...")
        hist_data = yf.download(all_tickers, period="5y", progress=False, threads=True, group_by='ticker')
        
        if hist_data.empty:
            return context
        
        # 5-year sector performance
        for sector, config in SECTORS.items():
            etf = config['etf']
            try:
                if etf not in hist_data.columns.get_level_values(0):
                    continue
                
                close_data = hist_data[etf]['Close'].dropna()
                if len(close_data) > 252:  # Need at least 1 year
                    current = close_data.iloc[-1]
                    year_1_ago = close_data.iloc[-252] if len(close_data) > 252 else close_data.iloc[0]
                    year_3_ago = close_data.iloc[-756] if len(close_data) > 756 else close_data.iloc[0]
                    year_5_ago = close_data.iloc[0]
                    
                    context['sector_5yr_performance'][sector] = {
                        'return_1y': round((current / year_1_ago - 1) * 100, 2),
                        'return_3y': round((current / year_3_ago - 1) * 100, 2),
                        'return_5y': round((current / year_5_ago - 1) * 100, 2),
                        'avg_annual_5y': round(((current / year_5_ago) ** (1/5) - 1) * 100, 2)
                    }
            except Exception:
                pass
        
        # S&P 500 P/E context (need individual call for info)
        try:
            spy = yf.Ticker('SPY')
            spy_info = spy.info
            current_pe = spy_info.get('trailingPE', 0)
            
            # Historical P/E ranges (approximate market averages)
            context['sp500_pe_context'] = {
                'current_pe': round(current_pe, 2) if current_pe else 0,
                'historical_avg': 17.0,  # Long-term S&P 500 average
                'historical_low': 10.0,   # Crisis lows
                'historical_high': 30.0,  # Bubble highs
                'assessment': 'expensive' if current_pe and current_pe > 22 else 'fair' if current_pe and current_pe > 15 else 'cheap' if current_pe else 'unknown',
                'deviation_from_avg': round(((current_pe / 17.0) - 1) * 100, 1) if current_pe else 0
            }
        except Exception:
            context['sp500_pe_context'] = {'current_pe': 0, 'assessment': 'unknown'}
        
        # Market cycle indicators from bulk data
        try:
            if 'SHY' in hist_data.columns.get_level_values(0) and 'IEF' in hist_data.columns.get_level_values(0):
                shy_close = hist_data['SHY']['Close'].dropna()
                ief_close = hist_data['IEF']['Close'].dropna()
                
                # Use last year of data
                if len(shy_close) > 252 and len(ief_close) > 252:
                    shy_return = (shy_close.iloc[-1] / shy_close.iloc[-252] - 1) * 100
                    ief_return = (ief_close.iloc[-1] / ief_close.iloc[-252] - 1) * 100
                    
                    context['market_cycle_indicators'] = {
                        'yield_curve_signal': 'steepening' if ief_return > shy_return else 'flattening',
                        'bond_market_sentiment': 'risk-off' if ief_return > shy_return + 2 else 'risk-on' if shy_return > ief_return + 2 else 'neutral'
                    }
        except Exception:
            context['market_cycle_indicators'] = {'yield_curve_signal': 'unknown'}
        
        # Historical VIX context from bulk data
        try:
            if '^VIX' in hist_data.columns.get_level_values(0):
                vix_close = hist_data['^VIX']['Close'].dropna()
                if len(vix_close) > 0:
                    context['historical_vix'] = {
                        'avg_5y': round(vix_close.mean(), 2),
                        'max_5y': round(vix_close.max(), 2),
                        'min_5y': round(vix_close.min(), 2),
                        'current_vs_5y_avg': round((vix_close.iloc[-1] / vix_close.mean() - 1) * 100, 1)
                    }
        except Exception:
            pass
        
    except Exception as e:
        print(f"Error fetching historical context: {str(e)}")
    
    return context


def get_dividend_calendar(tickers: List[str], days_ahead: int = 14) -> Dict[str, Dict]:
    """
    Get upcoming ex-dividend dates and dividend info for portfolio holdings.
    
    Args:
        tickers: List of stock symbols to check
        days_ahead: Number of days to look ahead for ex-dividend dates
    
    Returns:
        Dictionary mapping ticker to dividend info
    """
    print(f"  Checking dividend calendar ({days_ahead} days ahead)...")
    dividend_data = {}
    today = datetime.now()
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            ex_div_timestamp = info.get('exDividendDate')
            dividend_rate = info.get('dividendRate', 0)  # Annual dividend per share
            dividend_yield = info.get('dividendYield', 0)  # Yield as decimal
            
            if ex_div_timestamp and dividend_rate and dividend_rate > 0:
                # Convert Unix timestamp to datetime
                ex_div_date = datetime.fromtimestamp(ex_div_timestamp)
                days_until = (ex_div_date - today).days
                
                # Only include if ex-div is upcoming within window
                if 0 <= days_until <= days_ahead:
                    # Quarterly dividend (most common) = annual / 4
                    quarterly_dividend = dividend_rate / 4
                    
                    dividend_data[ticker] = {
                        'ex_dividend_date': ex_div_date.strftime('%Y-%m-%d'),
                        'ex_dividend_display': ex_div_date.strftime('%b %d'),
                        'days_until': days_until,
                        'dividend_per_share': round(quarterly_dividend, 4),
                        'annual_dividend': round(dividend_rate, 4),
                        'dividend_yield_pct': round((dividend_yield or 0) * 100, 2),
                        'company_name': info.get('longName', info.get('shortName', ticker))
                    }
        except Exception:
            pass
    
    if dividend_data:
        print(f"    Found {len(dividend_data)} stocks with upcoming ex-dividend dates")
    
    return dividend_data


def get_earnings_calendar(tickers: List[str], days_ahead: int = 14) -> Dict[str, Dict]:
    """
    Get upcoming earnings dates for a list of tickers.
    Flags stocks with earnings within the specified window.
    Dynamically skips ETFs (detected via yfinance quoteType) which don't have earnings.
    
    Args:
        tickers: List of stock symbols to check
        days_ahead: Number of days to look ahead for earnings (default 14)
    
    Returns:
        Dictionary mapping ticker to earnings info
    """
    print(f"  Checking earnings calendar ({days_ahead} days ahead)...")
    earnings_data = {}
    today = datetime.now()
    cutoff_date = today + timedelta(days=days_ahead)
    etf_count = 0
    
    print(f"    Checking {len(tickers)} tickers...")
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            
            # Dynamically detect ETFs via quoteType - skip them (no earnings)
            info = stock.info
            quote_type = info.get('quoteType', 'EQUITY')
            if quote_type == 'ETF':
                etf_count += 1
                continue
            
            calendar = stock.calendar
            
            if calendar is None:
                continue
                
            # Handle different calendar formats (dict or DataFrame)
            earnings_date = None
            
            # yfinance now returns calendar as a dict
            if isinstance(calendar, dict) and 'Earnings Date' in calendar:
                dates = calendar['Earnings Date']
                if isinstance(dates, list) and len(dates) > 0:
                    earnings_date = dates[0]
                elif dates is not None:
                    earnings_date = dates
            # Legacy DataFrame format (older yfinance versions)
            elif hasattr(calendar, 'empty') and not calendar.empty:
                if 'Earnings Date' in calendar.index:
                    dates = calendar.loc['Earnings Date']
                    if isinstance(dates, pd.Series):
                        earnings_date = dates.iloc[0]
                    else:
                        earnings_date = dates
            
            if earnings_date is not None:
                # Convert to datetime if needed
                if isinstance(earnings_date, pd.Timestamp):
                    earnings_dt = earnings_date.to_pydatetime()
                elif isinstance(earnings_date, datetime):
                    earnings_dt = earnings_date
                elif hasattr(earnings_date, 'year'):  # datetime.date object
                    # Convert date to datetime
                    earnings_dt = datetime(earnings_date.year, earnings_date.month, earnings_date.day)
                else:
                    continue
                
                # Remove timezone info for comparison
                if earnings_dt.tzinfo is not None:
                    earnings_dt = earnings_dt.replace(tzinfo=None)
                
                days_until = (earnings_dt - today).days
                
                if 0 <= days_until <= days_ahead:
                    earnings_data[ticker] = {
                        'earnings_date': earnings_dt.strftime('%Y-%m-%d'),
                        'days_until': days_until,
                        'warning': True,
                        'warning_text': f"⚠️ Earnings in {days_until} days ({earnings_dt.strftime('%b %d')})"
                    }
        except Exception as e:
            # Silently skip stocks where we can't get earnings data
            pass
    
    if etf_count > 0:
        print(f"    Skipped {etf_count} ETFs (no earnings)")
    if earnings_data:
        print(f"    Found {len(earnings_data)} stocks with upcoming earnings")
    else:
        print(f"    No upcoming earnings in the next {days_ahead} days")
    
    return earnings_data


def get_stock_universe_data(max_stocks: int = 1000) -> List[Dict]:
    """
    Fetch fundamental data for the stock universe.
    Uses dynamic ETF holdings for current, valid tickers.
    
    Args:
        max_stocks: Maximum number of stocks to fetch (default 1000)
    
    Returns:
        List of stock info dictionaries
    """
    # Get dynamic stock universe from ETF holdings
    stock_universe = get_dynamic_stock_universe()
    
    all_tickers = []
    for cap_category, tickers in stock_universe.items():
        all_tickers.extend(tickers)
    
    # Limit to max_stocks
    all_tickers = list(set(all_tickers))[:max_stocks]
    
    print(f"  Fetching data for {len(all_tickers)} stocks...")
    return fetch_multiple_ticker_info(all_tickers, max_workers=15)
