"""
Data fetching module for market data and prices.
Uses yfinance for stock data retrieval.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import (
    INDEXES, SECTORS, COMMODITIES, FIXED_INCOME, 
    INTERNATIONAL, STOCK_UNIVERSE, TECHNICAL_PARAMS
)


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
    Fetch fundamental info for a single ticker.
    
    Args:
        ticker: Stock symbol
    
    Returns:
        Dictionary with ticker info or None if fetch fails
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            'ticker': ticker,
            'name': info.get('longName', info.get('shortName', ticker)),
            'sector': info.get('sector', 'Unknown'),
            'industry': info.get('industry', 'Unknown'),
            'market_cap': info.get('marketCap', 0),
            'pe_ratio': info.get('trailingPE'),
            'forward_pe': info.get('forwardPE'),
            'peg_ratio': info.get('pegRatio'),
            'price_to_book': info.get('priceToBook'),
            'dividend_yield': info.get('dividendYield', 0),
            'payout_ratio': info.get('payoutRatio'),
            'revenue_growth': info.get('revenueGrowth'),
            'earnings_growth': info.get('earningsGrowth'),
            'profit_margin': info.get('profitMargins'),
            'roe': info.get('returnOnEquity'),
            'debt_to_equity': info.get('debtToEquity'),
            'current_price': info.get('currentPrice', info.get('regularMarketPrice')),
            'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
            'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
            'fifty_day_avg': info.get('fiftyDayAverage'),
            'two_hundred_day_avg': info.get('twoHundredDayAverage'),
            'avg_volume': info.get('averageVolume'),
            'beta': info.get('beta'),
            'short_ratio': info.get('shortRatio'),
            'insider_ownership': info.get('heldPercentInsiders'),
            'institutional_ownership': info.get('heldPercentInstitutions')
        }
    except Exception as e:
        print(f"Error fetching info for {ticker}: {str(e)}")
        return None


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
                               max_workers: int = 10) -> List[Dict]:
    """
    Fetch info for multiple tickers in parallel.
    
    Args:
        tickers: List of stock symbols
        max_workers: Maximum parallel threads
    
    Returns:
        List of ticker info dictionaries
    """
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(fetch_ticker_info, ticker): ticker 
            for ticker in tickers
        }
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                info = future.result()
                if info is not None:
                    results.append(info)
            except Exception as e:
                print(f"Error processing info for {ticker}: {str(e)}")
    return results


def get_current_prices(tickers: List[str]) -> Dict[str, float]:
    """
    Get current prices for a list of tickers.
    
    Args:
        tickers: List of stock symbols
    
    Returns:
        Dictionary mapping ticker to current price
    """
    prices = {}
    try:
        data = yf.download(tickers, period="1d", progress=False)
        if 'Close' in data.columns:
            # Multiple tickers
            for ticker in tickers:
                if ticker in data['Close'].columns:
                    price = data['Close'][ticker].iloc[-1]
                    if not pd.isna(price):
                        prices[ticker] = float(price)
        else:
            # Single ticker
            if len(tickers) == 1 and not data.empty:
                prices[tickers[0]] = float(data['Close'].iloc[-1])
    except Exception as e:
        print(f"Error fetching current prices: {str(e)}")
        # Fallback to individual fetches
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                price = info.get('currentPrice', info.get('regularMarketPrice'))
                if price:
                    prices[ticker] = float(price)
            except:
                pass
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
                if period_name == 'ytd':
                    # YTD calculation
                    year_start = datetime(datetime.now().year, 1, 1)
                    ytd_data = hist[hist.index >= pd.Timestamp(year_start)]
                    if len(ytd_data) > 1:
                        returns['ytd'] = (current / ytd_data['Close'].iloc[0] - 1) * 100
                elif days and len(hist) > days:
                    past_price = hist['Close'].iloc[-days-1]
                    returns[period_name] = (current / past_price - 1) * 100
            
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
    
    Returns:
        Dictionary with sector performance metrics
    """
    sector_data = {}
    for sector, config in SECTORS.items():
        etf = config['etf']
        try:
            ticker = yf.Ticker(etf)
            hist = ticker.history(period="1y")
            
            if hist.empty:
                continue
            
            current = hist['Close'].iloc[-1]
            
            # Calculate returns
            returns = {}
            for period_name, days in [('1mo', 21), ('3mo', 63), ('6mo', 126), ('1y', 252)]:
                if len(hist) > days:
                    past_price = hist['Close'].iloc[-days-1]
                    returns[period_name] = (current / past_price - 1) * 100
            
            # Calculate relative strength vs SPY
            spy = yf.Ticker('SPY')
            spy_hist = spy.history(period="3mo")
            if not spy_hist.empty and len(hist) >= 63:
                sector_return = (current / hist['Close'].iloc[-63]) - 1
                spy_return = (spy_hist['Close'].iloc[-1] / spy_hist['Close'].iloc[0]) - 1
                relative_strength = (sector_return - spy_return) * 100
            else:
                relative_strength = 0
            
            sector_data[sector] = {
                'etf': etf,
                'current': round(current, 2),
                'returns': {k: round(v, 2) for k, v in returns.items()},
                'relative_strength_3mo': round(relative_strength, 2)
            }
        except Exception as e:
            print(f"Error fetching sector {sector}: {str(e)}")
    
    return sector_data


def fetch_commodity_data() -> Dict[str, Dict]:
    """
    Fetch data for commodities and metals.
    
    Returns:
        Dictionary with commodity/metal data
    """
    commodity_data = {}
    
    # Combine all commodity tickers
    all_commodities = {}
    for category, tickers in {**COMMODITIES}.items():
        all_commodities[category] = tickers[0]  # Use primary ETF
    
    for category, ticker in all_commodities.items():
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
    Fetch data for fixed income ETFs.
    
    Returns:
        Dictionary with fixed income data
    """
    fi_data = {}
    
    for category, tickers in FIXED_INCOME.items():
        ticker = tickers[0]  # Use primary ETF
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
    Fetch data for international market ETFs.
    
    Returns:
        Dictionary with international market data
    """
    intl_data = {}
    
    for region, tickers in INTERNATIONAL.items():
        ticker = tickers[0]  # Use primary ETF
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
    Fetch VIX (volatility index) data.
    
    Returns:
        Dictionary with VIX data
    """
    try:
        ticker = yf.Ticker('^VIX')
        hist = ticker.history(period="3mo")
        
        if hist.empty:
            return {}
        
        current = hist['Close'].iloc[-1]
        avg_30d = hist['Close'].tail(21).mean()
        
        return {
            'current': round(current, 2),
            'avg_30d': round(avg_30d, 2),
            'level': 'low' if current < 15 else 'elevated' if current < 25 else 'high',
            'vs_average': 'above' if current > avg_30d else 'below'
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
    
    print("  Fetching macro indicators...")
    dollar_data = fetch_dollar_index()
    vix_data = fetch_vix()
    yield_data = fetch_treasury_yields()
    
    return {
        'timestamp': datetime.now().isoformat(),
        'indexes': index_data,
        'sectors': sector_data,
        'commodities': commodity_data,
        'fixed_income': fixed_income_data,
        'international': international_data,
        'macro': {
            'dollar': dollar_data,
            'vix': vix_data,
            'yields': yield_data
        }
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


def get_stock_universe_data(max_stocks: int = 200) -> List[Dict]:
    """
    Fetch fundamental data for the stock universe.
    
    Args:
        max_stocks: Maximum number of stocks to fetch
    
    Returns:
        List of stock info dictionaries
    """
    all_tickers = []
    for cap_category, tickers in STOCK_UNIVERSE.items():
        all_tickers.extend(tickers)
    
    # Limit to max_stocks
    all_tickers = list(set(all_tickers))[:max_stocks]
    
    print(f"  Fetching data for {len(all_tickers)} stocks...")
    return fetch_multiple_ticker_info(all_tickers, max_workers=15)
