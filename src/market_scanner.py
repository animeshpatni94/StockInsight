"""
Market screening module for identifying investment opportunities.
Implements momentum, fundamental, and technical screens across all sectors.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import (
    SECTORS, STOCK_UNIVERSE, TECHNICAL_PARAMS, FUNDAMENTAL_PARAMS
)
from data_fetcher import (
    fetch_ticker_data, fetch_ticker_info, fetch_multiple_ticker_info,
    calculate_technical_indicators, get_current_prices
)


class MarketScanner:
    """Comprehensive market screening class."""
    
    def __init__(self):
        self.stock_data = {}
        self.stock_info = []
        
    def load_universe(self, max_stocks: int = 200):
        """Load stock universe data for screening."""
        all_tickers = []
        for cap_category, tickers in STOCK_UNIVERSE.items():
            all_tickers.extend(tickers)
        all_tickers = list(set(all_tickers))[:max_stocks]
        
        print(f"    Loading {len(all_tickers)} stocks...")
        self.stock_info = fetch_multiple_ticker_info(all_tickers, max_workers=15)
        print(f"    Loaded info for {len(self.stock_info)} stocks")
        
    # ==================== MOMENTUM SCREENS ====================
    
    def get_top_gainers(self, sector: Optional[str] = None, n: int = 20, 
                        period: str = "1mo") -> List[Dict]:
        """
        Get top performing stocks in the past period.
        
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
        
        # Calculate returns
        tickers = [s['ticker'] for s in stocks if s.get('ticker')]
        
        results = []
        days_map = {'1w': 5, '1mo': 21, '3mo': 63, '6mo': 126}
        days = days_map.get(period, 21)
        
        for stock in stocks:
            ticker = stock.get('ticker')
            if not ticker:
                continue
            try:
                data = yf.Ticker(ticker).history(period="3mo")
                if len(data) > days:
                    current = data['Close'].iloc[-1]
                    past = data['Close'].iloc[-days-1]
                    return_pct = ((current / past) - 1) * 100
                    
                    results.append({
                        'ticker': ticker,
                        'name': stock.get('name', ticker),
                        'sector': stock.get('sector', 'Unknown'),
                        'return_pct': round(return_pct, 2),
                        'current_price': round(current, 2),
                        'market_cap': stock.get('market_cap', 0)
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
        
        Args:
            threshold: Multiple of average volume (3.0 = 3x average)
        
        Returns:
            List of stocks with volume spikes
        """
        results = []
        
        for stock in self.stock_info:
            ticker = stock.get('ticker')
            if not ticker:
                continue
            
            try:
                data = yf.Ticker(ticker).history(period="1mo")
                if len(data) < 5:
                    continue
                
                current_volume = data['Volume'].iloc[-1]
                avg_volume = data['Volume'].iloc[:-1].mean()
                
                if avg_volume > 0:
                    volume_ratio = current_volume / avg_volume
                    if volume_ratio >= threshold:
                        results.append({
                            'ticker': ticker,
                            'name': stock.get('name'),
                            'sector': stock.get('sector'),
                            'current_volume': int(current_volume),
                            'avg_volume': int(avg_volume),
                            'volume_ratio': round(volume_ratio, 2),
                            'price_change_pct': round(
                                ((data['Close'].iloc[-1] / data['Close'].iloc[-2]) - 1) * 100, 2
                            )
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
        Find growth stocks: Revenue growth > 20% YoY.
        
        Returns:
            List of growth stock candidates
        """
        results = []
        
        for stock in self.stock_info:
            revenue_growth = stock.get('revenue_growth')
            
            if (revenue_growth and 
                revenue_growth > FUNDAMENTAL_PARAMS['growth_revenue_growth_min']):
                
                results.append({
                    'ticker': stock.get('ticker'),
                    'name': stock.get('name'),
                    'sector': stock.get('sector'),
                    'revenue_growth': round(revenue_growth * 100, 2),
                    'earnings_growth': round((stock.get('earnings_growth') or 0) * 100, 2),
                    'current_price': stock.get('current_price'),
                    'forward_pe': stock.get('forward_pe'),
                    'peg_ratio': stock.get('peg_ratio')
                })
        
        results.sort(key=lambda x: x['revenue_growth'], reverse=True)
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
    
    def get_oversold_stocks(self, rsi_threshold: int = 30) -> List[Dict]:
        """
        Find stocks with RSI below threshold (oversold).
        
        Args:
            rsi_threshold: RSI level below which stock is considered oversold
        
        Returns:
            List of oversold stocks
        """
        results = []
        
        for stock in self.stock_info:
            ticker = stock.get('ticker')
            if not ticker:
                continue
            
            try:
                data = yf.Ticker(ticker).history(period="1mo")
                if len(data) < 14:
                    continue
                
                # Calculate RSI
                delta = data['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                
                if loss.iloc[-1] != 0:
                    rs = gain.iloc[-1] / loss.iloc[-1]
                    rsi = 100 - (100 / (1 + rs))
                    
                    if rsi < rsi_threshold:
                        results.append({
                            'ticker': ticker,
                            'name': stock.get('name'),
                            'sector': stock.get('sector'),
                            'current_price': stock.get('current_price'),
                            'rsi': round(rsi, 2),
                            'signal': 'Oversold'
                        })
            except Exception:
                continue
        
        results.sort(key=lambda x: x['rsi'])
        return results
    
    def get_overbought_stocks(self, rsi_threshold: int = 70) -> List[Dict]:
        """
        Find stocks with RSI above threshold (overbought).
        
        Args:
            rsi_threshold: RSI level above which stock is considered overbought
        
        Returns:
            List of overbought stocks
        """
        results = []
        
        for stock in self.stock_info:
            ticker = stock.get('ticker')
            if not ticker:
                continue
            
            try:
                data = yf.Ticker(ticker).history(period="1mo")
                if len(data) < 14:
                    continue
                
                # Calculate RSI
                delta = data['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                
                if loss.iloc[-1] != 0:
                    rs = gain.iloc[-1] / loss.iloc[-1]
                    rsi = 100 - (100 / (1 + rs))
                    
                    if rsi > rsi_threshold:
                        results.append({
                            'ticker': ticker,
                            'name': stock.get('name'),
                            'sector': stock.get('sector'),
                            'current_price': stock.get('current_price'),
                            'rsi': round(rsi, 2),
                            'signal': 'Overbought'
                        })
            except Exception:
                continue
        
        results.sort(key=lambda x: x['rsi'], reverse=True)
        return results
    
    # ==================== SECTOR ANALYSIS ====================
    
    def get_sector_performance(self, periods: List[str] = None) -> Dict[str, Dict]:
        """
        Get sector performance across multiple time periods.
        
        Args:
            periods: List of periods to analyze
        
        Returns:
            Dictionary with sector performance by period
        """
        if periods is None:
            periods = ['1mo', '3mo', '6mo']
        
        sector_perf = {}
        
        for sector, config in SECTORS.items():
            etf = config['etf']
            try:
                data = yf.Ticker(etf).history(period="1y")
                if data.empty:
                    continue
                
                current = data['Close'].iloc[-1]
                perf = {'etf': etf, 'current_price': round(current, 2)}
                
                days_map = {'1mo': 21, '3mo': 63, '6mo': 126, '1y': 252}
                for period in periods:
                    days = days_map.get(period, 21)
                    if len(data) > days:
                        past = data['Close'].iloc[-days-1]
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
        
        Returns:
            List of sectors with relative strength metrics
        """
        # Get SPY performance
        try:
            spy_data = yf.Ticker('SPY').history(period="3mo")
            if spy_data.empty:
                return []
            spy_return = ((spy_data['Close'].iloc[-1] / spy_data['Close'].iloc[0]) - 1) * 100
        except Exception:
            return []
        
        results = []
        for sector, config in SECTORS.items():
            etf = config['etf']
            try:
                data = yf.Ticker(etf).history(period="3mo")
                if data.empty:
                    continue
                
                sector_return = ((data['Close'].iloc[-1] / data['Close'].iloc[0]) - 1) * 100
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
    
    Returns:
        Dictionary with all screening results
    """
    print("  Initializing market scanner...")
    scanner = MarketScanner()
    scanner.load_universe(max_stocks=150)
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'momentum': {},
        'fundamental': {},
        'technical': {},
        'sector': {}
    }
    
    print("  Running momentum screens...")
    results['momentum'] = {
        'top_gainers': scanner.get_top_gainers(n=15),
        'top_losers': scanner.get_top_losers(n=15),
        '52w_high_breakouts': scanner.get_52week_high_breakouts()[:15],
        '52w_low_bounces': scanner.get_52week_low_bounces()[:15],
        'unusual_volume': scanner.get_unusual_volume()[:15]
    }
    
    print("  Running fundamental screens...")
    results['fundamental'] = {
        'value_stocks': scanner.get_value_stocks()[:15],
        'growth_stocks': scanner.get_growth_stocks()[:15],
        'dividend_stocks': scanner.get_dividend_stocks()[:15],
        'insider_buying': scanner.get_insider_buying_clusters()[:10]
    }
    
    print("  Running technical screens...")
    results['technical'] = {
        'golden_crosses': scanner.get_golden_crosses()[:10],
        'death_crosses': scanner.get_death_crosses()[:10],
        'oversold': scanner.get_oversold_stocks()[:15],
        'overbought': scanner.get_overbought_stocks()[:15]
    }
    
    print("  Running sector analysis...")
    results['sector'] = {
        'performance': scanner.get_sector_performance(),
        'rotation_signals': scanner.get_sector_rotation_signals(),
        'vs_spy': scanner.get_sector_vs_spy()
    }
    
    return results
