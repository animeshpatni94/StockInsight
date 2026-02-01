"""
Market screening module for identifying investment opportunities.
Implements momentum, fundamental, and technical screens across all sectors.
"""

import yfinance as yf
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import (
    SECTORS, TECHNICAL_PARAMS, FUNDAMENTAL_PARAMS
)
from data_fetcher import (
    fetch_ticker_data, fetch_ticker_info, fetch_multiple_ticker_info,
    calculate_technical_indicators, get_current_prices, get_dynamic_stock_universe
)


class MarketScanner:
    """Comprehensive market screening class."""
    
    def __init__(self):
        self.stock_data = {}
        self.stock_info = []
        self.stock_universe = None
        self._price_cache = {}  # Cache for historical prices
        
    def load_universe(self, max_stocks: int = 1500):
        """Load stock universe data for screening."""
        # Dynamically fetch stock universe from ETF holdings
        self.stock_universe = get_dynamic_stock_universe()
        
        all_tickers = []
        for cap_category, tickers in self.stock_universe.items():
            all_tickers.extend(tickers)
        all_tickers = list(set(all_tickers))[:max_stocks]
        
        print(f"    Loading {len(all_tickers)} stocks...")
        # Use rate-limited fetching with very conservative settings to fetch all 1500 stocks
        self.stock_info = fetch_multiple_ticker_info(all_tickers, max_workers=2, batch_size=20, delay_between_batches=3.0)
        print(f"    Loaded info for {len(self.stock_info)} stocks")
        
    def _bulk_download_prices(self, tickers: List[str], period: str = "3mo") -> pd.DataFrame:
        """
        Download historical prices for multiple tickers in bulk.
        Uses yf.download() which is much more efficient than individual calls.
        Rate limited with batches to avoid Yahoo Finance blocks.
        
        Args:
            tickers: List of stock symbols
            period: Time period for historical data
            
        Returns:
            DataFrame with price data (multi-level columns if multiple tickers)
        """
        if not tickers:
            return pd.DataFrame()
        
        # Cache key
        cache_key = f"{','.join(sorted(tickers[:10]))}_{period}"
        if cache_key in self._price_cache:
            return self._price_cache[cache_key]
        
        # Batch download to avoid rate limits (50 tickers per batch for safety)
        batch_size = 50
        all_data = []
        
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(tickers) + batch_size - 1) // batch_size
            print(f"        Downloading batch {batch_num}/{total_batches} ({len(batch)} tickers)...")
            try:
                data = yf.download(
                    batch, 
                    period=period, 
                    progress=False, 
                    threads=True,
                    group_by='ticker'
                )
                if not data.empty:
                    all_data.append(data)
            except Exception as e:
                print(f"        Batch {batch_num} error: {e}")
            
            # Rate limit: 2 second delay between batches
            if i + batch_size < len(tickers):
                time.sleep(2.0)
        
        if all_data:
            result = pd.concat(all_data, axis=1) if len(all_data) > 1 else all_data[0]
            self._price_cache[cache_key] = result
            return result
        
        return pd.DataFrame()
        
    # ==================== MOMENTUM SCREENS ====================
    
    def get_top_gainers(self, sector: Optional[str] = None, n: int = 20, 
                        period: str = "1mo") -> List[Dict]:
        """
        Get top performing stocks in the past period.
        Uses bulk download for efficiency and rate limit compliance.
        
        Args:
            sector: Filter by sector (None for all)
            n: Number of results to return
            period: Time period for return calculation
        
        Returns:
            List of top gainers with performance data
        """
        stocks = self.stock_info
        if sector:
            stocks = [s for s in stocks if s.get('sector') == sector]
        
        # Get tickers list
        tickers = [s['ticker'] for s in stocks if s.get('ticker')]
        if not tickers:
            return []
        
        # Build ticker info lookup
        ticker_info = {s['ticker']: s for s in stocks if s.get('ticker')}
        
        days_map = {'1w': 5, '1mo': 21, '3mo': 63, '6mo': 126}
        days = days_map.get(period, 21)
        
        # Bulk download prices (much more efficient!)
        print(f"      Downloading prices for {len(tickers)} tickers...")
        price_data = self._bulk_download_prices(tickers, period="3mo")
        
        if price_data.empty:
            return []
        
        results = []
        for ticker in tickers:
            try:
                # Handle both single and multi-ticker DataFrame structures
                if len(tickers) == 1:
                    close_prices = price_data['Close']
                else:
                    if ticker in price_data.columns.get_level_values(0):
                        close_prices = price_data[ticker]['Close']
                    else:
                        continue
                
                # Drop NaN values
                close_prices = close_prices.dropna()
                
                if len(close_prices) > days:
                    current = close_prices.iloc[-1]
                    past = close_prices.iloc[-days-1] if len(close_prices) > days else close_prices.iloc[0]
                    return_pct = ((current / past) - 1) * 100
                    
                    info = ticker_info.get(ticker, {})
                    results.append({
                        'ticker': ticker,
                        'name': info.get('name', ticker),
                        'sector': info.get('sector', 'Unknown'),
                        'return_pct': round(return_pct, 2),
                        'current_price': round(float(current), 2),
                        'market_cap': info.get('market_cap', 0)
                    })
            except Exception:
                continue
        
        # Sort by return descending
        results.sort(key=lambda x: x['return_pct'], reverse=True)
        return results[:n]
    
    def get_top_losers(self, sector: Optional[str] = None, n: int = 20,
                       period: str = "1mo") -> List[Dict]:
        """
        Get worst performing stocks (potential value opportunities).
        
        Args:
            sector: Filter by sector (None for all)
            n: Number of results to return
            period: Time period for return calculation
        
        Returns:
            List of top losers with performance data
        """
        gainers = self.get_top_gainers(sector=sector, n=200, period=period)
        # Sort by return ascending (worst first)
        gainers.sort(key=lambda x: x['return_pct'])
        return gainers[:n]
    
    def get_52week_high_breakouts(self, threshold: float = 0.98) -> List[Dict]:
        """
        Find stocks trading within threshold of 52-week high.
        
        Args:
            threshold: Percentage of 52-week high (0.98 = within 2%)
        
        Returns:
            List of stocks near 52-week highs
        """
        results = []
        for stock in self.stock_info:
            current = stock.get('current_price', 0)
            high_52w = stock.get('fifty_two_week_high', 0)
            
            if current and high_52w and high_52w > 0:
                ratio = current / high_52w
                if ratio >= threshold:
                    results.append({
                        'ticker': stock.get('ticker'),
                        'name': stock.get('name'),
                        'sector': stock.get('sector'),
                        'current_price': round(current, 2),
                        '52w_high': round(high_52w, 2),
                        'pct_from_high': round((1 - ratio) * 100, 2)
                    })
        
        results.sort(key=lambda x: x['pct_from_high'])
        return results
    
    def get_52week_low_bounces(self, threshold: float = 1.10) -> List[Dict]:
        """
        Find stocks bouncing off 52-week lows.
        
        Args:
            threshold: Maximum ratio above 52-week low (1.10 = within 10%)
        
        Returns:
            List of stocks near 52-week lows
        """
        results = []
        for stock in self.stock_info:
            current = stock.get('current_price', 0)
            low_52w = stock.get('fifty_two_week_low', 0)
            
            if current and low_52w and low_52w > 0:
                ratio = current / low_52w
                if ratio <= threshold:
                    results.append({
                        'ticker': stock.get('ticker'),
                        'name': stock.get('name'),
                        'sector': stock.get('sector'),
                        'current_price': round(current, 2),
                        '52w_low': round(low_52w, 2),
                        'pct_from_low': round((ratio - 1) * 100, 2)
                    })
        
        results.sort(key=lambda x: x['pct_from_low'])
        return results
    
    def get_unusual_volume(self, threshold: float = 3.0) -> List[Dict]:
        """
        Find stocks with unusual volume spikes.
        Uses bulk download for efficiency.
        
        Args:
            threshold: Multiple of average volume (3.0 = 3x average)
        
        Returns:
            List of stocks with volume spikes
        """
        tickers = [s['ticker'] for s in self.stock_info if s.get('ticker')]
        if not tickers:
            return []
        
        # Build ticker info lookup
        ticker_info = {s['ticker']: s for s in self.stock_info if s.get('ticker')}
        
        # Bulk download prices with volume
        print(f"      Checking volume for {len(tickers)} tickers...")
        price_data = self._bulk_download_prices(tickers, period="1mo")
        
        if price_data.empty:
            return []
        
        results = []
        for ticker in tickers:
            try:
                # Handle both single and multi-ticker DataFrame structures
                if len(tickers) == 1:
                    volume_data = price_data['Volume']
                    close_data = price_data['Close']
                else:
                    if ticker not in price_data.columns.get_level_values(0):
                        continue
                    volume_data = price_data[ticker]['Volume']
                    close_data = price_data[ticker]['Close']
                
                volume_data = volume_data.dropna()
                close_data = close_data.dropna()
                
                if len(volume_data) < 5:
                    continue
                
                current_volume = volume_data.iloc[-1]
                avg_volume = volume_data.iloc[:-1].mean()
                
                if avg_volume > 0:
                    volume_ratio = current_volume / avg_volume
                    if volume_ratio >= threshold:
                        info = ticker_info.get(ticker, {})
                        price_change_pct = 0
                        if len(close_data) >= 2:
                            price_change_pct = ((close_data.iloc[-1] / close_data.iloc[-2]) - 1) * 100
                        
                        results.append({
                            'ticker': ticker,
                            'name': info.get('name'),
                            'sector': info.get('sector'),
                            'current_volume': int(current_volume),
                            'avg_volume': int(avg_volume),
                            'volume_ratio': round(volume_ratio, 2),
                            'price_change_pct': round(price_change_pct, 2)
                        })
            except Exception:
                continue
        
        results.sort(key=lambda x: x['volume_ratio'], reverse=True)
        return results
    
    # ==================== FUNDAMENTAL SCREENS ====================
    
    def get_value_stocks(self) -> List[Dict]:
        """
        Find value stocks: P/E < 15 with earnings growth > 10%.
        
        Returns:
            List of value stock candidates
        """
        results = []
        
        for stock in self.stock_info:
            pe = stock.get('pe_ratio')
            earnings_growth = stock.get('earnings_growth')
            
            if (pe and earnings_growth and 
                pe < FUNDAMENTAL_PARAMS['value_pe_max'] and 
                earnings_growth > FUNDAMENTAL_PARAMS['value_earnings_growth_min']):
                
                results.append({
                    'ticker': stock.get('ticker'),
                    'name': stock.get('name'),
                    'sector': stock.get('sector'),
                    'pe_ratio': round(pe, 2),
                    'earnings_growth': round(earnings_growth * 100, 2),
                    'current_price': stock.get('current_price'),
                    'market_cap': stock.get('market_cap'),
                    'dividend_yield': round((stock.get('dividend_yield') or 0) * 100, 2)
                })
        
        results.sort(key=lambda x: x['pe_ratio'])
        return results
    
    def get_growth_stocks(self) -> List[Dict]:
        """
        Find growth stocks with comprehensive criteria:
        - Revenue growth > 20% YoY OR
        - Earnings growth > 25% OR
        - Strong forward PE with high growth (PEG < 2)
        
        Includes growth scores for ranking quality.
        
        Returns:
            List of growth stock candidates with growth scores
        """
        results = []
        
        for stock in self.stock_info:
            revenue_growth = stock.get('revenue_growth') or 0
            earnings_growth = stock.get('earnings_growth') or 0
            peg_ratio = stock.get('peg_ratio')
            forward_pe = stock.get('forward_pe')
            market_cap = stock.get('market_cap') or 0
            roe = stock.get('roe') or 0
            
            # Growth score calculation (0-100)
            growth_score = 0
            growth_flags = []
            
            # Revenue growth component (max 40 points)
            if revenue_growth > 0.50:  # 50%+
                growth_score += 40
                growth_flags.append("Hyper revenue growth (50%+)")
            elif revenue_growth > 0.30:  # 30-50%
                growth_score += 30
                growth_flags.append("Strong revenue growth (30%+)")
            elif revenue_growth > 0.20:  # 20-30%
                growth_score += 20
                growth_flags.append("Solid revenue growth (20%+)")
            elif revenue_growth > 0.10:  # 10-20%
                growth_score += 10
            
            # Earnings growth component (max 30 points)
            if earnings_growth > 0.50:  # 50%+
                growth_score += 30
                growth_flags.append("Explosive EPS growth (50%+)")
            elif earnings_growth > 0.30:  # 30-50%
                growth_score += 20
                growth_flags.append("Strong EPS growth (30%+)")
            elif earnings_growth > 0.15:  # 15-30%
                growth_score += 10
            
            # PEG ratio bonus (max 15 points) - growth at reasonable price
            if peg_ratio and 0 < peg_ratio < 1:
                growth_score += 15
                growth_flags.append("Undervalued growth (PEG < 1)")
            elif peg_ratio and peg_ratio < 1.5:
                growth_score += 10
                growth_flags.append("Reasonable PEG (< 1.5)")
            elif peg_ratio and peg_ratio < 2:
                growth_score += 5
            
            # ROE bonus (max 15 points) - quality of growth
            if roe > 0.25:  # 25%+
                growth_score += 15
                growth_flags.append("High ROE (25%+)")
            elif roe > 0.15:  # 15-25%
                growth_score += 10
            elif roe > 0.10:  # 10-15%
                growth_score += 5
            
            # Only include stocks with meaningful growth score (at least one strong signal)
            if growth_score >= 20:
                # Determine growth category
                if market_cap > 200_000_000_000:
                    cap_category = "Mega Cap"
                elif market_cap > 10_000_000_000:
                    cap_category = "Large Cap"
                elif market_cap > 2_000_000_000:
                    cap_category = "Mid Cap"
                elif market_cap > 300_000_000:
                    cap_category = "Small Cap"
                else:
                    cap_category = "Micro Cap"
                
                results.append({
                    'ticker': stock.get('ticker'),
                    'name': stock.get('name'),
                    'sector': stock.get('sector'),
                    'industry': stock.get('industry'),
                    'revenue_growth': round(revenue_growth * 100, 2),
                    'earnings_growth': round(earnings_growth * 100, 2),
                    'peg_ratio': round(peg_ratio, 2) if peg_ratio else None,
                    'roe': round(roe * 100, 2) if roe else None,
                    'current_price': stock.get('current_price'),
                    'forward_pe': round(forward_pe, 2) if forward_pe else None,
                    'market_cap': market_cap,
                    'cap_category': cap_category,
                    'growth_score': growth_score,
                    'growth_flags': growth_flags
                })
        
        # Sort by growth score descending
        results.sort(key=lambda x: x['growth_score'], reverse=True)
        return results
    
    def get_garp_stocks(self) -> List[Dict]:
        """
        Find GARP (Growth at Reasonable Price) stocks:
        - PEG ratio < 1.5 with positive growth
        - Earnings growth > 15%
        - Reasonable P/E for the sector
        
        Returns:
            List of GARP candidates
        """
        results = []
        
        for stock in self.stock_info:
            peg_ratio = stock.get('peg_ratio')
            earnings_growth = stock.get('earnings_growth') or 0
            pe_ratio = stock.get('pe_ratio')
            forward_pe = stock.get('forward_pe')
            
            # GARP criteria: PEG < 1.5 with real growth
            if (peg_ratio and 0 < peg_ratio < 1.5 and 
                earnings_growth > 0.15 and
                pe_ratio and pe_ratio < 35):
                
                results.append({
                    'ticker': stock.get('ticker'),
                    'name': stock.get('name'),
                    'sector': stock.get('sector'),
                    'peg_ratio': round(peg_ratio, 2),
                    'pe_ratio': round(pe_ratio, 2),
                    'forward_pe': round(forward_pe, 2) if forward_pe else None,
                    'earnings_growth': round(earnings_growth * 100, 2),
                    'revenue_growth': round((stock.get('revenue_growth') or 0) * 100, 2),
                    'current_price': stock.get('current_price'),
                    'market_cap': stock.get('market_cap')
                })
        
        results.sort(key=lambda x: x['peg_ratio'])
        return results
    
    def get_dividend_stocks(self) -> List[Dict]:
        """
        Find dividend stocks: Yield > 3%, payout ratio < 60%.
        
        Returns:
            List of dividend stock candidates
        """
        results = []
        
        for stock in self.stock_info:
            div_yield = stock.get('dividend_yield')
            payout_ratio = stock.get('payout_ratio')
            
            if div_yield and div_yield > FUNDAMENTAL_PARAMS['dividend_yield_min']:
                # Payout ratio check (if available)
                if payout_ratio is None or payout_ratio < FUNDAMENTAL_PARAMS['dividend_payout_max']:
                    results.append({
                        'ticker': stock.get('ticker'),
                        'name': stock.get('name'),
                        'sector': stock.get('sector'),
                        'dividend_yield': round(div_yield * 100, 2),
                        'payout_ratio': round((payout_ratio or 0) * 100, 2),
                        'pe_ratio': stock.get('pe_ratio'),
                        'current_price': stock.get('current_price')
                    })
        
        results.sort(key=lambda x: x['dividend_yield'], reverse=True)
        return results
    
    def get_insider_buying_clusters(self) -> List[Dict]:
        """
        Find stocks with significant insider buying activity.
        Note: Requires additional data source or API for insider trades.
        
        Returns:
            List of stocks with insider buying
        """
        # This is a placeholder - insider data typically requires a paid API
        # like Quiver Quantitative, SEC EDGAR parsing, or similar
        results = []
        
        # Filter by insider ownership as a proxy
        for stock in self.stock_info:
            insider_pct = stock.get('insider_ownership')
            if insider_pct and insider_pct > 0.10:  # > 10% insider ownership
                results.append({
                    'ticker': stock.get('ticker'),
                    'name': stock.get('name'),
                    'sector': stock.get('sector'),
                    'insider_ownership_pct': round(insider_pct * 100, 2),
                    'current_price': stock.get('current_price')
                })
        
        results.sort(key=lambda x: x['insider_ownership_pct'], reverse=True)
        return results[:20]
    
    def get_earnings_surprises(self, positive: bool = True, 
                               threshold: float = 0.10) -> List[Dict]:
        """
        Find stocks with recent earnings surprises.
        Note: Requires earnings data which is limited in free yfinance.
        
        Args:
            positive: True for beats, False for misses
            threshold: Minimum surprise percentage (0.10 = 10%)
        
        Returns:
            List of stocks with earnings surprises
        """
        # Placeholder - would need earnings calendar API
        # Return stocks with strong/weak earnings growth as proxy
        if positive:
            stocks = self.get_growth_stocks()
        else:
            stocks = [s for s in self.stock_info 
                     if s.get('earnings_growth') and s.get('earnings_growth') < -0.10]
            stocks.sort(key=lambda x: x.get('earnings_growth', 0))
        
        return stocks[:15]
    
    # ==================== TECHNICAL SCREENS ====================
    
    def get_golden_crosses(self) -> List[Dict]:
        """
        Find stocks where 50 DMA crossed above 200 DMA recently.
        
        Returns:
            List of stocks with recent golden crosses
        """
        results = []
        
        for stock in self.stock_info:
            ticker = stock.get('ticker')
            if not ticker:
                continue
            
            sma_50 = stock.get('fifty_day_avg')
            sma_200 = stock.get('two_hundred_day_avg')
            
            if sma_50 and sma_200:
                # Current state: 50 > 200 (bullish)
                if sma_50 > sma_200:
                    # Check if it was recent (within 5% of each other suggests recent cross)
                    ratio = sma_50 / sma_200
                    if 1.0 < ratio < 1.05:
                        results.append({
                            'ticker': ticker,
                            'name': stock.get('name'),
                            'sector': stock.get('sector'),
                            'current_price': stock.get('current_price'),
                            'sma_50': round(sma_50, 2),
                            'sma_200': round(sma_200, 2),
                            'signal': 'Golden Cross (Bullish)'
                        })
        
        return results
    
    def get_death_crosses(self) -> List[Dict]:
        """
        Find stocks where 50 DMA crossed below 200 DMA recently.
        
        Returns:
            List of stocks with recent death crosses
        """
        results = []
        
        for stock in self.stock_info:
            ticker = stock.get('ticker')
            if not ticker:
                continue
            
            sma_50 = stock.get('fifty_day_avg')
            sma_200 = stock.get('two_hundred_day_avg')
            
            if sma_50 and sma_200:
                # Current state: 50 < 200 (bearish)
                if sma_50 < sma_200:
                    ratio = sma_50 / sma_200
                    if 0.95 < ratio < 1.0:
                        results.append({
                            'ticker': ticker,
                            'name': stock.get('name'),
                            'sector': stock.get('sector'),
                            'current_price': stock.get('current_price'),
                            'sma_50': round(sma_50, 2),
                            'sma_200': round(sma_200, 2),
                            'signal': 'Death Cross (Bearish)'
                        })
        
        return results
    
    def _calculate_rsi_bulk(self, price_data: pd.DataFrame, tickers: List[str], window: int = 14) -> Dict[str, float]:
        """
        Calculate RSI for multiple tickers from bulk price data.
        
        Args:
            price_data: DataFrame with price data from bulk download
            tickers: List of tickers
            window: RSI window period
            
        Returns:
            Dictionary mapping ticker to RSI value
        """
        rsi_values = {}
        
        for ticker in tickers:
            try:
                # Handle both single and multi-ticker DataFrame structures
                if len(tickers) == 1:
                    close_data = price_data['Close']
                else:
                    if ticker not in price_data.columns.get_level_values(0):
                        continue
                    close_data = price_data[ticker]['Close']
                
                close_data = close_data.dropna()
                
                if len(close_data) < window:
                    continue
                
                # Calculate RSI
                delta = close_data.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
                
                if loss.iloc[-1] != 0:
                    rs = gain.iloc[-1] / loss.iloc[-1]
                    rsi = 100 - (100 / (1 + rs))
                    rsi_values[ticker] = rsi
            except Exception:
                continue
        
        return rsi_values
    
    def get_oversold_stocks(self, rsi_threshold: int = 30) -> List[Dict]:
        """
        Find stocks with RSI below threshold (oversold).
        Uses bulk download for efficiency.
        
        Args:
            rsi_threshold: RSI level below which stock is considered oversold
        
        Returns:
            List of oversold stocks
        """
        tickers = [s['ticker'] for s in self.stock_info if s.get('ticker')]
        if not tickers:
            return []
        
        # Build ticker info lookup
        ticker_info = {s['ticker']: s for s in self.stock_info if s.get('ticker')}
        
        # Bulk download prices
        print(f"      Calculating RSI for {len(tickers)} tickers...")
        price_data = self._bulk_download_prices(tickers, period="1mo")
        
        if price_data.empty:
            return []
        
        # Calculate RSI for all tickers
        rsi_values = self._calculate_rsi_bulk(price_data, tickers)
        
        # Log RSI calculation results
        rsi_success_count = len(rsi_values)
        rsi_failed_count = len(tickers) - rsi_success_count
        print(f"      ✓ RSI calculated for {rsi_success_count}/{len(tickers)} stocks ({rsi_failed_count} failed/skipped)")
        
        results = []
        for ticker, rsi in rsi_values.items():
            if rsi < rsi_threshold:
                info = ticker_info.get(ticker, {})
                results.append({
                    'ticker': ticker,
                    'name': info.get('name'),
                    'sector': info.get('sector'),
                    'current_price': info.get('current_price'),
                    'rsi': round(rsi, 2),
                    'signal': 'Oversold'
                })
        
        print(f"      ✓ Found {len(results)} oversold stocks (RSI < {rsi_threshold})")
        if results:
            top_oversold = [f"{r['ticker']}({r['rsi']})" for r in results[:5]]
            print(f"        Top oversold: {', '.join(top_oversold)}")
        
        results.sort(key=lambda x: x['rsi'])
        return results
    
    def get_overbought_stocks(self, rsi_threshold: int = 70) -> List[Dict]:
        """
        Find stocks with RSI above threshold (overbought).
        Uses bulk download for efficiency.
        
        Args:
            rsi_threshold: RSI level above which stock is considered overbought
        
        Returns:
            List of overbought stocks
        """
        tickers = [s['ticker'] for s in self.stock_info if s.get('ticker')]
        if not tickers:
            return []
        
        # Build ticker info lookup
        ticker_info = {s['ticker']: s for s in self.stock_info if s.get('ticker')}
        
        # Bulk download prices (reuses cache from oversold if already run)
        price_data = self._bulk_download_prices(tickers, period="1mo")
        
        if price_data.empty:
            return []
        
        # Calculate RSI for all tickers
        rsi_values = self._calculate_rsi_bulk(price_data, tickers)
        
        # Log RSI calculation results (only if not already logged by oversold)
        rsi_success_count = len(rsi_values)
        
        results = []
        for ticker, rsi in rsi_values.items():
            if rsi > rsi_threshold:
                info = ticker_info.get(ticker, {})
                results.append({
                    'ticker': ticker,
                    'name': info.get('name'),
                    'sector': info.get('sector'),
                    'current_price': info.get('current_price'),
                    'rsi': round(rsi, 2),
                    'signal': 'Overbought'
                })
        
        print(f"      ✓ Found {len(results)} overbought stocks (RSI > {rsi_threshold})")
        if results:
            top_overbought = [f"{r['ticker']}({r['rsi']})" for r in results[:5]]
            print(f"        Top overbought: {', '.join(top_overbought)}")
        
        results.sort(key=lambda x: x['rsi'], reverse=True)
        return results
    
    # ==================== SECTOR ANALYSIS ====================
    
    def get_sector_performance(self, periods: List[str] = None) -> Dict[str, Dict]:
        """
        Get sector performance across multiple time periods.
        Uses bulk download for efficiency.
        
        Args:
            periods: List of periods to analyze
        
        Returns:
            Dictionary with sector performance by period
        """
        if periods is None:
            periods = ['1mo', '3mo', '6mo']
        
        # Collect all sector ETFs
        etfs = [config['etf'] for sector, config in SECTORS.items()]
        
        # Bulk download all ETF data at once
        try:
            etf_data = yf.download(etfs, period="1y", progress=False, threads=True, group_by='ticker')
            if etf_data.empty:
                return {}
        except Exception:
            return {}
        
        sector_perf = {}
        days_map = {'1mo': 21, '3mo': 63, '6mo': 126, '1y': 252}
        
        for sector, config in SECTORS.items():
            etf = config['etf']
            try:
                if etf not in etf_data.columns.get_level_values(0):
                    continue
                
                close_data = etf_data[etf]['Close'].dropna()
                if len(close_data) < 2:
                    continue
                
                current = close_data.iloc[-1]
                perf = {'etf': etf, 'current_price': round(float(current), 2)}
                
                for period in periods:
                    days = days_map.get(period, 21)
                    if len(close_data) > days:
                        past = close_data.iloc[-days-1]
                        perf[f'{period}_return'] = round(((current / past) - 1) * 100, 2)
                
                sector_perf[sector] = perf
            except Exception:
                continue
        
        return sector_perf
    
    def get_sector_rotation_signals(self) -> List[Dict]:
        """
        Identify sector rotation based on relative performance changes.
        
        Returns:
            List of sectors with rotation signals
        """
        sector_perf = self.get_sector_performance(['1mo', '3mo'])
        
        signals = []
        for sector, perf in sector_perf.items():
            ret_1mo = perf.get('1mo_return', 0)
            ret_3mo = perf.get('3mo_return', 0)
            
            # Acceleration = recent outperformance
            if ret_1mo > 0 and ret_3mo > 0:
                if ret_1mo > (ret_3mo / 3):  # 1mo return > monthly avg of 3mo
                    signals.append({
                        'sector': sector,
                        'etf': perf['etf'],
                        'signal': 'Accelerating',
                        '1mo_return': ret_1mo,
                        '3mo_return': ret_3mo
                    })
            # Deceleration = slowing momentum
            elif ret_1mo < (ret_3mo / 3):
                signals.append({
                    'sector': sector,
                    'etf': perf['etf'],
                    'signal': 'Decelerating',
                    '1mo_return': ret_1mo,
                    '3mo_return': ret_3mo
                })
        
        return signals
    
    def get_sector_vs_spy(self) -> List[Dict]:
        """
        Calculate sector relative strength vs S&P 500.
        Uses bulk download for efficiency.
        
        Returns:
            List of sectors with relative strength metrics
        """
        # Collect all ETFs including SPY
        etfs = ['SPY'] + [config['etf'] for sector, config in SECTORS.items()]
        
        # Bulk download all ETF data at once
        try:
            etf_data = yf.download(etfs, period="3mo", progress=False, threads=True, group_by='ticker')
            if etf_data.empty:
                return []
        except Exception:
            return []
        
        # Get SPY return
        try:
            spy_close = etf_data['SPY']['Close'].dropna()
            if len(spy_close) < 2:
                return []
            spy_return = ((spy_close.iloc[-1] / spy_close.iloc[0]) - 1) * 100
        except Exception:
            return []
        
        results = []
        for sector, config in SECTORS.items():
            etf = config['etf']
            try:
                if etf not in etf_data.columns.get_level_values(0):
                    continue
                
                close_data = etf_data[etf]['Close'].dropna()
                if len(close_data) < 2:
                    continue
                
                sector_return = ((close_data.iloc[-1] / close_data.iloc[0]) - 1) * 100
                relative_strength = sector_return - spy_return
                
                results.append({
                    'sector': sector,
                    'etf': etf,
                    'sector_return_3mo': round(sector_return, 2),
                    'spy_return_3mo': round(spy_return, 2),
                    'relative_strength': round(relative_strength, 2),
                    'rating': 'Outperforming' if relative_strength > 2 else 
                             'Underperforming' if relative_strength < -2 else 'In-line'
                })
            except Exception:
                continue
        
        results.sort(key=lambda x: x['relative_strength'], reverse=True)
        return results


def run_all_screens() -> Dict:
    """
    Run all market screens and return compiled results.
    Covers all industries, sectors, and asset classes.
    
    Returns:
        Dictionary with all screening results
    """
    print("  Initializing market scanner...")
    scanner = MarketScanner()
    scanner.load_universe(max_stocks=1500)  # Analyze full 1500 stock universe
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'momentum': {},
        'fundamental': {},
        'technical': {},
        'sector': {}
    }
    
    print("  Running momentum screens...")
    results['momentum'] = {
        'top_gainers': scanner.get_top_gainers(n=75),
        'top_losers': scanner.get_top_losers(n=75),
        '52w_high_breakouts': scanner.get_52week_high_breakouts()[:60],
        '52w_low_bounces': scanner.get_52week_low_bounces()[:60],
        'unusual_volume': scanner.get_unusual_volume()[:60]
    }
    
    print("  Running fundamental screens (growth, value, GARP, dividend)...")
    results['fundamental'] = {
        'value_stocks': scanner.get_value_stocks()[:75],
        'growth_stocks': scanner.get_growth_stocks()[:100],  # More growth stocks
        'garp_stocks': scanner.get_garp_stocks()[:50],       # NEW: Growth at Reasonable Price
        'dividend_stocks': scanner.get_dividend_stocks()[:60],
        'insider_buying': scanner.get_insider_buying_clusters()[:40]
    }
    
    print("  Running technical screens...")
    results['technical'] = {
        'golden_crosses': scanner.get_golden_crosses()[:50],
        'death_crosses': scanner.get_death_crosses()[:50],
        'oversold': scanner.get_oversold_stocks()[:60],
        'overbought': scanner.get_overbought_stocks()[:60]
    }
    
    print("  Running sector analysis...")
    results['sector'] = {
        'performance': scanner.get_sector_performance(),
        'rotation_signals': scanner.get_sector_rotation_signals(),
        'vs_spy': scanner.get_sector_vs_spy()
    }
    
    return results
