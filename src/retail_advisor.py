"""
Retail Investor Advisory Module.
Provides specialized analysis and alerts for individual investors.
Focuses on practical, actionable insights that help everyday investors make smarter decisions.

Key Features:
- Tax-Loss Harvesting Detection
- Portfolio Correlation Analysis
- Liquidity/Spread Warnings
- Trailing Stop-Loss Management
- Dollar-Cost Averaging Strategies
- Short Interest/Squeeze Detection
- Institutional Ownership Trends
- Sector Rotation Timing
- Fee Impact Analysis
- Ex-Dividend Capture Optimization
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import warnings

warnings.filterwarnings('ignore')


# ==================== TAX-LOSS HARVESTING ====================

def detect_tax_loss_harvesting_opportunities(
    portfolio: List[Dict],
    current_prices: Dict[str, float],
    year_end_threshold_days: int = 60
) -> List[Dict]:
    """
    Identify positions that could be sold for tax-loss harvesting.
    
    Tax-loss harvesting rules:
    - Sell losing positions to offset capital gains
    - Wash sale rule: Can't buy substantially identical security within 30 days
    - More valuable near year-end (Oct-Dec)
    - Short-term losses offset short-term gains first (more valuable at 32%+ vs 15%)
    
    Args:
        portfolio: Current portfolio holdings
        current_prices: Dictionary of current prices
        year_end_threshold_days: Days until year-end to flag as high priority
    
    Returns:
        List of tax-loss harvesting opportunities with recommendations
    """
    opportunities = []
    today = datetime.now()
    year_end = datetime(today.year, 12, 31)
    days_to_year_end = (year_end - today).days
    
    # Determine if we're in tax-loss harvesting season (Oct-Dec)
    is_harvest_season = today.month >= 10
    
    for holding in portfolio:
        ticker = holding.get('ticker')
        buy_price = holding.get('recommended_price', 0)
        buy_date_str = holding.get('recommended_date', '')
        allocation = holding.get('allocation_pct', 0)
        
        if not ticker or buy_price <= 0:
            continue
        
        current_price = current_prices.get(ticker, buy_price)
        loss_pct = ((current_price / buy_price) - 1) * 100
        
        # Only consider positions with meaningful losses (> 5%)
        if loss_pct >= -5:
            continue
        
        # Calculate hold period for short-term vs long-term classification
        try:
            buy_date = datetime.strptime(buy_date_str, '%Y-%m-%d')
            hold_days = (today - buy_date).days
            is_short_term = hold_days < 365
        except (ValueError, TypeError):
            hold_days = 0
            is_short_term = True
        
        # Calculate tax benefit (estimated)
        # Short-term losses are more valuable (32% tax rate vs 15% long-term)
        tax_rate = 0.32 if is_short_term else 0.15
        estimated_tax_savings = abs(loss_pct / 100) * allocation * tax_rate * 1000  # Per $100k portfolio
        
        # Priority scoring
        priority_score = 0
        priority_reasons = []
        
        # Bigger losses = higher priority
        if loss_pct <= -20:
            priority_score += 3
            priority_reasons.append("Significant loss (>20%)")
        elif loss_pct <= -10:
            priority_score += 2
            priority_reasons.append("Moderate loss (>10%)")
        else:
            priority_score += 1
        
        # Short-term losses are more valuable
        if is_short_term:
            priority_score += 2
            priority_reasons.append("Short-term loss (higher tax benefit)")
        
        # Near year-end = urgent
        if is_harvest_season:
            priority_score += 2
            priority_reasons.append(f"Tax season ({days_to_year_end} days to year-end)")
        
        # Determine similar securities for reinvestment (avoid wash sale)
        similar_securities = _get_similar_securities(holding)
        
        opportunities.append({
            'ticker': ticker,
            'company_name': holding.get('company_name', ticker),
            'loss_pct': round(loss_pct, 2),
            'current_price': round(current_price, 2),
            'buy_price': round(buy_price, 2),
            'allocation_pct': allocation,
            'hold_days': hold_days,
            'is_short_term': is_short_term,
            'tax_rate': tax_rate,
            'estimated_tax_savings': round(estimated_tax_savings, 2),
            'priority': 'HIGH' if priority_score >= 5 else 'MEDIUM' if priority_score >= 3 else 'LOW',
            'priority_score': priority_score,
            'priority_reasons': priority_reasons,
            'similar_securities': similar_securities,
            'wash_sale_warning': "Wait 31+ days before repurchasing same security",
            'recommendation': _get_tlh_recommendation(loss_pct, is_short_term, is_harvest_season)
        })
    
    # Sort by priority score descending
    opportunities.sort(key=lambda x: x['priority_score'], reverse=True)
    return opportunities


def _get_similar_securities(holding: Dict) -> List[str]:
    """Get similar securities for wash-sale compliant reinvestment."""
    sector = holding.get('sector', '')
    asset_class = holding.get('asset_class', '')
    
    # Sector ETF alternatives (won't trigger wash sale)
    sector_etfs = {
        'Technology': ['XLK', 'VGT', 'FTEC'],
        'Healthcare': ['XLV', 'VHT', 'IYH'],
        'Financials': ['XLF', 'VFH', 'IYF'],
        'Energy': ['XLE', 'VDE', 'IYE'],
        'Consumer Discretionary': ['XLY', 'VCR'],
        'Consumer Staples': ['XLP', 'VDC'],
        'Industrials': ['XLI', 'VIS'],
        'Materials': ['XLB', 'VAW'],
        'Utilities': ['XLU', 'VPU'],
        'Real Estate': ['XLRE', 'VNQ'],
        'Communication Services': ['XLC', 'VOX']
    }
    
    return sector_etfs.get(sector, ['SPY', 'VTI', 'IVV'])


def _get_tlh_recommendation(loss_pct: float, is_short_term: bool, is_harvest_season: bool) -> str:
    """Generate actionable tax-loss harvesting recommendation."""
    if loss_pct <= -20 and is_harvest_season:
        return "🔴 STRONG SELL for tax harvesting. Large loss + year-end = maximize tax benefit."
    elif loss_pct <= -15 and is_short_term:
        return "🟠 Consider selling. Short-term loss has higher tax benefit (32% vs 15%)."
    elif loss_pct <= -10 and is_harvest_season:
        return "🟡 Review for harvest. Year-end approaching - lock in losses if thesis broken."
    else:
        return "🟢 Monitor. Only harvest if investment thesis has deteriorated."


# ==================== PORTFOLIO CORRELATION ANALYSIS ====================

def analyze_portfolio_correlation(
    portfolio: List[Dict],
    lookback_days: int = 90
) -> Dict:
    """
    Analyze correlation between portfolio holdings.
    High correlation means less diversification than it appears.
    
    Args:
        portfolio: Current portfolio holdings
        lookback_days: Days of price history for correlation
    
    Returns:
        Correlation analysis with warnings and recommendations
    """
    if len(portfolio) < 2:
        return {
            'status': 'INSUFFICIENT_DATA',
            'message': 'Need at least 2 positions for correlation analysis'
        }
    
    tickers = [h.get('ticker') for h in portfolio if h.get('ticker')]
    if len(tickers) < 2:
        return {'status': 'INSUFFICIENT_DATA', 'message': 'Need at least 2 valid tickers'}
    
    # Download price data
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days + 30)  # Extra buffer
        
        data = yf.download(tickers, start=start_date, end=end_date, progress=False)
        
        if data.empty:
            return {'status': 'DATA_ERROR', 'message': 'Could not fetch price data'}
        
        # Get adjusted close prices
        if len(tickers) == 1:
            return {'status': 'INSUFFICIENT_DATA', 'message': 'Need multiple tickers'}
        
        # Handle multi-ticker format
        if 'Adj Close' in data.columns.get_level_values(0) if hasattr(data.columns, 'get_level_values') else False:
            prices = data['Adj Close']
        else:
            prices = data['Close'] if 'Close' in data else data
        
        # Calculate daily returns
        returns = prices.pct_change().dropna()
        
        if len(returns) < 20:
            return {'status': 'INSUFFICIENT_DATA', 'message': 'Not enough price history'}
        
        # Calculate correlation matrix
        corr_matrix = returns.corr()
        
    except Exception as e:
        return {'status': 'ERROR', 'message': str(e)}
    
    # Analyze correlations
    high_correlations = []
    moderate_correlations = []
    
    for i, ticker1 in enumerate(tickers):
        for j, ticker2 in enumerate(tickers):
            if i >= j:  # Skip diagonal and duplicates
                continue
            
            try:
                corr = corr_matrix.loc[ticker1, ticker2]
                if pd.isna(corr):
                    continue
                
                if corr >= 0.8:
                    high_correlations.append({
                        'pair': (ticker1, ticker2),
                        'correlation': round(corr, 3),
                        'risk': 'HIGH',
                        'warning': f"⚠️ {ticker1} and {ticker2} move together 80%+ of the time. Consider reducing one."
                    })
                elif corr >= 0.6:
                    moderate_correlations.append({
                        'pair': (ticker1, ticker2),
                        'correlation': round(corr, 3),
                        'risk': 'MODERATE'
                    })
            except (KeyError, TypeError):
                continue
    
    # Calculate portfolio-level diversification score
    # Lower average correlation = better diversification
    upper_triangle = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    avg_correlation = upper_triangle.stack().mean()
    
    if pd.isna(avg_correlation):
        avg_correlation = 0
    
    diversification_score = max(0, min(100, (1 - avg_correlation) * 100))
    
    # Generate sector concentration analysis
    sector_exposure = defaultdict(float)
    for holding in portfolio:
        sector = holding.get('sector', 'Unknown')
        alloc = holding.get('allocation_pct', 0)
        sector_exposure[sector] += alloc
    
    sector_warnings = []
    for sector, exposure in sector_exposure.items():
        if exposure > 35:
            sector_warnings.append({
                'sector': sector,
                'exposure': round(exposure, 1),
                'warning': f"⚠️ {sector} exposure ({exposure:.1f}%) exceeds 35% limit"
            })
    
    return {
        'status': 'SUCCESS',
        'diversification_score': round(diversification_score, 1),
        'diversification_grade': _get_diversification_grade(diversification_score),
        'average_correlation': round(avg_correlation, 3),
        'high_correlation_pairs': high_correlations,
        'moderate_correlation_pairs': moderate_correlations,
        'sector_exposure': dict(sector_exposure),
        'sector_warnings': sector_warnings,
        'recommendations': _get_correlation_recommendations(
            diversification_score, high_correlations, sector_warnings
        )
    }


def _get_diversification_grade(score: float) -> str:
    """Convert diversification score to letter grade."""
    if score >= 80:
        return 'A - Excellent diversification'
    elif score >= 65:
        return 'B - Good diversification'
    elif score >= 50:
        return 'C - Moderate diversification'
    elif score >= 35:
        return 'D - Poor diversification'
    else:
        return 'F - Concentrated portfolio (high risk)'


def _get_correlation_recommendations(
    score: float, 
    high_corr: List[Dict], 
    sector_warnings: List[Dict]
) -> List[str]:
    """Generate actionable diversification recommendations."""
    recs = []
    
    if score < 50:
        recs.append("🔴 Portfolio is highly concentrated. Add uncorrelated assets (bonds, gold, international).")
    
    if high_corr:
        pairs = [f"{p['pair'][0]}/{p['pair'][1]}" for p in high_corr[:3]]
        recs.append(f"🟠 Consider reducing one of these correlated pairs: {', '.join(pairs)}")
    
    if sector_warnings:
        sectors = [w['sector'] for w in sector_warnings]
        recs.append(f"🟡 Reduce exposure to overweight sectors: {', '.join(sectors)}")
    
    if not recs:
        recs.append("🟢 Portfolio diversification looks healthy.")
    
    return recs


# ==================== LIQUIDITY & SPREAD ANALYSIS ====================

def analyze_liquidity_risks(
    portfolio: List[Dict],
    watchlist: List[str] = None
) -> Dict:
    """
    Analyze liquidity risks for portfolio holdings and watchlist.
    Retail investors often get poor fills on illiquid stocks.
    
    Liquidity metrics:
    - Average daily volume
    - Dollar volume (price * volume)
    - Market cap
    - Bid-ask spread estimate
    
    Args:
        portfolio: Current portfolio holdings
        watchlist: Additional tickers to analyze
    
    Returns:
        Liquidity analysis with warnings
    """
    tickers = [h.get('ticker') for h in portfolio if h.get('ticker')]
    if watchlist:
        tickers.extend(watchlist)
    tickers = list(set(tickers))
    
    if not tickers:
        return {'status': 'NO_TICKERS', 'warnings': []}
    
    liquidity_data = []
    warnings = []
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            avg_volume = info.get('averageVolume', 0) or info.get('averageDailyVolume10Day', 0) or 0
            current_price = info.get('currentPrice') or info.get('regularMarketPrice') or 0
            market_cap = info.get('marketCap', 0) or 0
            bid = info.get('bid', 0) or 0
            ask = info.get('ask', 0) or 0
            
            # Calculate dollar volume
            dollar_volume = avg_volume * current_price if avg_volume and current_price else 0
            
            # Estimate spread
            if bid > 0 and ask > 0:
                spread_pct = ((ask - bid) / ((ask + bid) / 2)) * 100
            else:
                # Estimate spread based on volume and market cap
                if dollar_volume > 100_000_000:  # $100M+ daily volume
                    spread_pct = 0.02
                elif dollar_volume > 10_000_000:  # $10M-$100M
                    spread_pct = 0.08
                elif dollar_volume > 1_000_000:   # $1M-$10M
                    spread_pct = 0.25
                else:
                    spread_pct = 0.75  # Illiquid
            
            # Determine liquidity tier
            if dollar_volume >= 50_000_000:
                liquidity_tier = 'HIGH'
                risk_level = 'LOW'
            elif dollar_volume >= 5_000_000:
                liquidity_tier = 'MEDIUM'
                risk_level = 'LOW'
            elif dollar_volume >= 500_000:
                liquidity_tier = 'LOW'
                risk_level = 'MEDIUM'
            else:
                liquidity_tier = 'VERY_LOW'
                risk_level = 'HIGH'
            
            data = {
                'ticker': ticker,
                'avg_volume': avg_volume,
                'dollar_volume': round(dollar_volume, 0),
                'market_cap': market_cap,
                'estimated_spread_pct': round(spread_pct, 3),
                'liquidity_tier': liquidity_tier,
                'risk_level': risk_level
            }
            liquidity_data.append(data)
            
            # Generate warnings for illiquid stocks
            if risk_level == 'HIGH':
                warnings.append({
                    'ticker': ticker,
                    'severity': 'HIGH',
                    'issue': 'Very low liquidity',
                    'dollar_volume': dollar_volume,
                    'spread_pct': spread_pct,
                    'warning': f"⚠️ {ticker}: Low liquidity (${dollar_volume/1000:.0f}K daily). "
                              f"Expected ~{spread_pct:.2f}% spread cost per trade. Use LIMIT orders only!",
                    'recommendation': "Use limit orders, consider position size carefully, avoid during market stress"
                })
            elif risk_level == 'MEDIUM':
                warnings.append({
                    'ticker': ticker,
                    'severity': 'MEDIUM',
                    'issue': 'Moderate liquidity',
                    'dollar_volume': dollar_volume,
                    'spread_pct': spread_pct,
                    'warning': f"🟡 {ticker}: Moderate liquidity. Use limit orders for better fills.",
                    'recommendation': "Use limit orders, avoid large market orders"
                })
                
        except Exception as e:
            continue
    
    # Sort warnings by severity
    warnings.sort(key=lambda x: {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}.get(x['severity'], 3))
    
    return {
        'status': 'SUCCESS',
        'liquidity_data': liquidity_data,
        'warnings': warnings,
        'summary': {
            'high_risk_count': len([w for w in warnings if w['severity'] == 'HIGH']),
            'medium_risk_count': len([w for w in warnings if w['severity'] == 'MEDIUM']),
            'total_analyzed': len(liquidity_data)
        }
    }


# ==================== TRAILING STOP-LOSS MANAGEMENT ====================

def calculate_trailing_stops(
    portfolio: List[Dict],
    current_prices: Dict[str, float],
    method: str = 'atr'  # 'atr', 'percent', or 'support'
) -> List[Dict]:
    """
    Calculate recommended trailing stop-loss levels for portfolio.
    Trailing stops lock in profits while giving winners room to run.
    
    Methods:
    - ATR: Based on Average True Range (volatility-adjusted)
    - Percent: Fixed percentage below peak (typically 15-20%)
    - Support: Based on technical support levels
    
    Args:
        portfolio: Current portfolio holdings
        current_prices: Dictionary of current prices
        method: Stop-loss calculation method
    
    Returns:
        List of trailing stop recommendations
    """
    results = []
    
    for holding in portfolio:
        ticker = holding.get('ticker')
        buy_price = holding.get('recommended_price', 0)
        fixed_stop = holding.get('stop_loss', 0)
        
        if not ticker or buy_price <= 0:
            continue
        
        current_price = current_prices.get(ticker, buy_price)
        gain_pct = ((current_price / buy_price) - 1) * 100
        
        # Fetch historical data for calculations
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="3mo")
            
            if hist.empty or len(hist) < 20:
                # Use default percentage method
                trailing_stop = current_price * 0.85  # 15% trailing
                method_used = 'DEFAULT_PCT'
            else:
                # Calculate ATR for volatility-based stop
                high = hist['High']
                low = hist['Low']
                close = hist['Close']
                
                tr1 = high - low
                tr2 = abs(high - close.shift())
                tr3 = abs(low - close.shift())
                tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                atr = tr.rolling(14).mean().iloc[-1]
                
                # Find highest close since purchase (simulated peak tracking)
                peak_price = hist['Close'].max()
                
                if method == 'atr':
                    # ATR-based: 2.5x ATR below peak
                    atr_multiplier = 2.5
                    trailing_stop = peak_price - (atr * atr_multiplier)
                    method_used = f'ATR_{atr_multiplier}x'
                elif method == 'percent':
                    # Percentage-based: 15% below peak
                    trailing_stop = peak_price * 0.85
                    method_used = 'PCT_15'
                else:
                    # Support-based: recent swing low
                    recent_lows = low.rolling(5).min()
                    trailing_stop = recent_lows.iloc[-1]
                    method_used = 'SUPPORT'
                
        except Exception:
            trailing_stop = current_price * 0.85
            peak_price = current_price
            method_used = 'DEFAULT_PCT'
        
        # Ensure trailing stop is never below original stop-loss
        if fixed_stop > 0:
            trailing_stop = max(trailing_stop, fixed_stop)
        
        # Ensure trailing stop is never above current price
        trailing_stop = min(trailing_stop, current_price * 0.95)
        
        # Calculate risk metrics
        risk_from_current = ((trailing_stop / current_price) - 1) * 100
        locked_in_gain = ((trailing_stop / buy_price) - 1) * 100 if buy_price > 0 else 0
        
        results.append({
            'ticker': ticker,
            'current_price': round(current_price, 2),
            'buy_price': round(buy_price, 2),
            'gain_pct': round(gain_pct, 2),
            'original_stop': round(fixed_stop, 2) if fixed_stop > 0 else None,
            'trailing_stop': round(trailing_stop, 2),
            'method': method_used,
            'risk_from_current_pct': round(risk_from_current, 2),
            'locked_in_gain_pct': round(locked_in_gain, 2),
            'status': _get_trailing_stop_status(gain_pct, locked_in_gain),
            'action': _get_trailing_stop_action(gain_pct, risk_from_current, locked_in_gain)
        })
    
    return results


def _get_trailing_stop_status(gain_pct: float, locked_in_gain: float) -> str:
    """Determine trailing stop status."""
    if locked_in_gain >= 20:
        return '🟢 LOCKED_PROFIT'
    elif locked_in_gain > 0:
        return '🟢 BREAKEVEN_PROTECTED'
    elif gain_pct > 0:
        return '🟡 PROFITABLE_UNPROTECTED'
    else:
        return '🔴 LOSING'


def _get_trailing_stop_action(gain_pct: float, risk_pct: float, locked_gain: float) -> str:
    """Generate trailing stop action recommendation."""
    if gain_pct >= 25 and locked_gain < 15:
        return "🟠 TIGHTEN STOP: Large gain, raise stop to lock in more profit"
    elif gain_pct >= 15 and locked_gain < 0:
        return "🟡 RAISE STOP: Move stop to breakeven to protect gains"
    elif risk_pct < -20:
        return "🔴 STOP TOO LOOSE: Consider tightening to limit downside"
    else:
        return "🟢 APPROPRIATE: Current stop level is reasonable"


# ==================== DOLLAR-COST AVERAGING STRATEGY ====================

def generate_dca_plan(
    ticker: str,
    total_allocation: float,
    num_tranches: int = 3,
    current_price: float = None
) -> Dict:
    """
    Generate a dollar-cost averaging plan for entering a position.
    Reduces timing risk by spreading purchases across multiple points.
    
    Args:
        ticker: Stock symbol
        total_allocation: Target allocation percentage
        num_tranches: Number of purchase tranches (2-5)
        current_price: Current market price
    
    Returns:
        DCA plan with entry points and allocation
    """
    num_tranches = max(2, min(5, num_tranches))
    
    # Fetch current price and technical levels
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="6mo")
        info = stock.info
        
        if current_price is None:
            current_price = info.get('currentPrice') or info.get('regularMarketPrice') or 0
        
        if hist.empty or current_price <= 0:
            return {'status': 'ERROR', 'message': 'Could not fetch price data'}
        
        # Calculate technical levels for entry points
        sma_50 = hist['Close'].rolling(50).mean().iloc[-1] if len(hist) >= 50 else current_price * 0.95
        sma_200 = hist['Close'].rolling(200).mean().iloc[-1] if len(hist) >= 200 else current_price * 0.90
        recent_low = hist['Close'].rolling(20).min().iloc[-1]
        
        # ATR for volatility
        high = hist['High']
        low = hist['Low']
        close = hist['Close']
        tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]
        
    except Exception as e:
        return {'status': 'ERROR', 'message': str(e)}
    
    # Generate tranches
    tranches = []
    allocation_per_tranche = total_allocation / num_tranches
    
    # Tranche 1: Current price (immediate entry)
    tranches.append({
        'tranche': 1,
        'trigger': 'IMMEDIATE',
        'price_level': round(current_price, 2),
        'allocation_pct': round(allocation_per_tranche, 2),
        'description': 'Initial position - establish exposure now'
    })
    
    # Tranche 2: 5% pullback or support level
    entry_2 = min(current_price * 0.95, recent_low * 1.02)
    tranches.append({
        'tranche': 2,
        'trigger': 'LIMIT_ORDER',
        'price_level': round(entry_2, 2),
        'allocation_pct': round(allocation_per_tranche, 2),
        'description': f'Add on 5% pullback (near support ${entry_2:.2f})'
    })
    
    if num_tranches >= 3:
        # Tranche 3: 50 SMA or 10% pullback
        entry_3 = min(sma_50, current_price * 0.90)
        tranches.append({
            'tranche': 3,
            'trigger': 'LIMIT_ORDER',
            'price_level': round(entry_3, 2),
            'allocation_pct': round(allocation_per_tranche, 2),
            'description': f'Add at 50-SMA support (${entry_3:.2f})'
        })
    
    if num_tranches >= 4:
        # Tranche 4: 200 SMA or 15% pullback
        entry_4 = min(sma_200, current_price * 0.85)
        tranches.append({
            'tranche': 4,
            'trigger': 'LIMIT_ORDER',
            'price_level': round(entry_4, 2),
            'allocation_pct': round(allocation_per_tranche, 2),
            'description': f'Add at 200-SMA support (${entry_4:.2f})'
        })
    
    if num_tranches >= 5:
        # Tranche 5: Major support or 20% pullback
        entry_5 = current_price * 0.80
        tranches.append({
            'tranche': 5,
            'trigger': 'LIMIT_ORDER',
            'price_level': round(entry_5, 2),
            'allocation_pct': round(allocation_per_tranche, 2),
            'description': f'Major pullback opportunity (${entry_5:.2f})'
        })
    
    # Calculate average entry if all tranches filled
    total_weight = sum(t['allocation_pct'] for t in tranches)
    weighted_avg = sum(t['price_level'] * t['allocation_pct'] for t in tranches) / total_weight
    
    return {
        'status': 'SUCCESS',
        'ticker': ticker,
        'current_price': round(current_price, 2),
        'total_allocation': total_allocation,
        'num_tranches': num_tranches,
        'tranches': tranches,
        'average_entry_if_all_filled': round(weighted_avg, 2),
        'discount_vs_current': round(((weighted_avg / current_price) - 1) * 100, 2),
        'volatility_atr': round(atr, 2),
        'recommendation': f"Set limit orders for tranches 2-{num_tranches}. Reduces average cost if stock pulls back."
    }


# ==================== SHORT INTEREST & SQUEEZE DETECTION ====================

def analyze_short_interest(tickers: List[str]) -> List[Dict]:
    """
    Analyze short interest for potential squeeze candidates or red flags.
    
    High short interest can indicate:
    - Potential squeeze (if > 20% and stock starts rising)
    - Fundamental problems (bears betting against company)
    
    Args:
        tickers: List of stock symbols
    
    Returns:
        Short interest analysis with risk assessment
    """
    results = []
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            short_ratio = info.get('shortRatio')  # Days to cover
            short_pct = info.get('shortPercentOfFloat')  # % of float shorted
            
            # Handle missing or zero values
            if short_pct is None and short_ratio:
                short_pct = short_ratio * 0.05  # Rough estimate
            
            if short_pct is None:
                short_pct = 0
            
            short_pct = short_pct * 100 if short_pct < 1 else short_pct  # Convert to percentage
            
            # Get price momentum for squeeze detection
            hist = stock.history(period="1mo")
            if not hist.empty:
                price_change_1mo = ((hist['Close'].iloc[-1] / hist['Close'].iloc[0]) - 1) * 100
            else:
                price_change_1mo = 0
            
            # Determine short interest classification
            if short_pct >= 30:
                si_level = 'EXTREME'
                risk_opportunity = 'HIGH_RISK' if price_change_1mo < 0 else 'SQUEEZE_CANDIDATE'
            elif short_pct >= 20:
                si_level = 'HIGH'
                risk_opportunity = 'ELEVATED_RISK' if price_change_1mo < 0 else 'MODERATE_SQUEEZE'
            elif short_pct >= 10:
                si_level = 'MODERATE'
                risk_opportunity = 'NORMAL'
            else:
                si_level = 'LOW'
                risk_opportunity = 'BULLISH_SIGNAL'
            
            # Squeeze detection
            is_squeezing = short_pct >= 15 and price_change_1mo > 10
            
            results.append({
                'ticker': ticker,
                'short_pct_of_float': round(short_pct, 2),
                'days_to_cover': short_ratio,
                'short_interest_level': si_level,
                'risk_opportunity': risk_opportunity,
                'price_change_1mo': round(price_change_1mo, 2),
                'potential_squeeze': is_squeezing,
                'analysis': _get_short_interest_analysis(short_pct, price_change_1mo, is_squeezing)
            })
            
        except Exception:
            continue
    
    # Sort by short interest descending
    results.sort(key=lambda x: x['short_pct_of_float'], reverse=True)
    return results


def _get_short_interest_analysis(short_pct: float, price_change: float, squeezing: bool) -> str:
    """Generate short interest analysis."""
    if squeezing:
        return f"🚀 SQUEEZE IN PROGRESS: {short_pct:.1f}% short + {price_change:.1f}% gain = shorts covering!"
    elif short_pct >= 30:
        if price_change < -10:
            return f"⚠️ DANGER: Extreme short interest ({short_pct:.1f}%) + falling price. Bears are winning."
        else:
            return f"👀 WATCH: Extreme short ({short_pct:.1f}%). Could squeeze or crash. High risk/reward."
    elif short_pct >= 20:
        return f"🟡 ELEVATED: {short_pct:.1f}% short. Monitor for squeeze or fundamental issues."
    elif short_pct < 5:
        return f"🟢 LOW SHORT: Only {short_pct:.1f}% short. Bulls in control."
    else:
        return f"Normal short interest ({short_pct:.1f}%). No special signal."


# ==================== INSTITUTIONAL OWNERSHIP TRACKING ====================

def analyze_institutional_ownership(tickers: List[str]) -> List[Dict]:
    """
    Analyze institutional ownership levels and potential concerns.
    
    Institutional ownership insights:
    - Very high (>90%): Crowded trade risk
    - High (70-90%): Strong smart money support
    - Moderate (40-70%): Healthy mix
    - Low (<40%): Either early opportunity or red flag
    
    Args:
        tickers: List of stock symbols
    
    Returns:
        Institutional ownership analysis
    """
    results = []
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            inst_pct = info.get('heldPercentInstitutions', 0) or 0
            insider_pct = info.get('heldPercentInsiders', 0) or 0
            
            inst_pct = inst_pct * 100 if inst_pct < 1 else inst_pct
            insider_pct = insider_pct * 100 if insider_pct < 1 else insider_pct
            
            # Classify ownership level
            if inst_pct >= 90:
                level = 'VERY_HIGH'
                signal = 'CAUTION'
                analysis = "Crowded trade. If institutions sell, who will buy?"
            elif inst_pct >= 70:
                level = 'HIGH'
                signal = 'BULLISH'
                analysis = "Strong institutional support. Smart money is invested."
            elif inst_pct >= 40:
                level = 'MODERATE'
                signal = 'NEUTRAL'
                analysis = "Healthy mix of institutional and retail ownership."
            elif inst_pct >= 20:
                level = 'LOW'
                signal = 'MIXED'
                analysis = "Low institutional interest. Could be opportunity or red flag."
            else:
                level = 'VERY_LOW'
                signal = 'RESEARCH_NEEDED'
                analysis = "Minimal institutional ownership. High risk, do extra due diligence."
            
            results.append({
                'ticker': ticker,
                'institutional_pct': round(inst_pct, 2),
                'insider_pct': round(insider_pct, 2),
                'ownership_level': level,
                'signal': signal,
                'analysis': analysis,
                'insider_note': _get_insider_note(insider_pct)
            })
            
        except Exception:
            continue
    
    return results


def _get_insider_note(insider_pct: float) -> str:
    """Generate insider ownership note."""
    if insider_pct >= 20:
        return f"🟢 High insider ownership ({insider_pct:.1f}%). Management has skin in the game."
    elif insider_pct >= 5:
        return f"Moderate insider ownership ({insider_pct:.1f}%)."
    else:
        return f"Low insider ownership ({insider_pct:.1f}%). Management may not be aligned."


# ==================== SECTOR ROTATION ANALYSIS ====================

def analyze_sector_rotation() -> Dict:
    """
    Analyze current sector rotation phase based on economic cycle.
    
    Economic Cycle Phases:
    - Early Cycle: Financials, Consumer Discretionary, Industrials
    - Mid Cycle: Technology, Communication Services, Materials
    - Late Cycle: Energy, Healthcare, Consumer Staples
    - Recession: Utilities, Healthcare, Consumer Staples, Gold
    
    Returns:
        Sector rotation analysis with phase detection and recommendations
    """
    # Sector ETFs to analyze
    sector_etfs = {
        'Technology': 'XLK',
        'Healthcare': 'XLV',
        'Financials': 'XLF',
        'Energy': 'XLE',
        'Consumer Discretionary': 'XLY',
        'Consumer Staples': 'XLP',
        'Industrials': 'XLI',
        'Materials': 'XLB',
        'Utilities': 'XLU',
        'Communication Services': 'XLC',
        'Real Estate': 'XLRE'
    }
    
    # Cycle-sensitive ETFs
    cycle_indicators = {
        'early_cycle': ['XLF', 'XLY', 'XLI'],  # Financials, Discretionary, Industrials
        'mid_cycle': ['XLK', 'XLC', 'XLB'],     # Tech, Comm Services, Materials
        'late_cycle': ['XLE', 'XLV', 'XLP'],    # Energy, Healthcare, Staples
        'recession': ['XLU', 'GLD', 'TLT']       # Utilities, Gold, Treasuries
    }
    
    try:
        # Download sector performance data
        all_etfs = list(sector_etfs.values()) + ['SPY', 'GLD', 'TLT']
        data = yf.download(all_etfs, period="6mo", progress=False, group_by='ticker')
        
        if data.empty:
            return {'status': 'ERROR', 'message': 'Could not fetch sector data'}
        
        sector_performance = {}
        
        for sector, etf in sector_etfs.items():
            try:
                if etf in data.columns.get_level_values(0):
                    close = data[etf]['Close'].dropna()
                    if len(close) >= 21:
                        ret_1mo = ((close.iloc[-1] / close.iloc[-21]) - 1) * 100
                        ret_3mo = ((close.iloc[-1] / close.iloc[-63]) - 1) * 100 if len(close) >= 63 else ret_1mo
                        sector_performance[sector] = {
                            'etf': etf,
                            '1mo_return': round(ret_1mo, 2),
                            '3mo_return': round(ret_3mo, 2),
                            'momentum': 'ACCELERATING' if ret_1mo > ret_3mo/3 else 'DECELERATING'
                        }
            except Exception:
                continue
        
        # Calculate cycle phase scores
        phase_scores = {phase: 0 for phase in cycle_indicators}
        
        for phase, etfs in cycle_indicators.items():
            for etf in etfs:
                try:
                    if etf in data.columns.get_level_values(0):
                        close = data[etf]['Close'].dropna()
                        if len(close) >= 21:
                            ret = ((close.iloc[-1] / close.iloc[-21]) - 1) * 100
                            phase_scores[phase] += ret
                except Exception:
                    continue
            phase_scores[phase] = round(phase_scores[phase] / len(etfs), 2)
        
        # Determine current phase
        current_phase = max(phase_scores, key=phase_scores.get)
        
        # Get phase-appropriate sector recommendations
        phase_recommendations = {
            'early_cycle': ['Financials', 'Consumer Discretionary', 'Industrials'],
            'mid_cycle': ['Technology', 'Communication Services', 'Materials'],
            'late_cycle': ['Energy', 'Healthcare', 'Consumer Staples'],
            'recession': ['Utilities', 'Consumer Staples', 'Healthcare']
        }
        
    except Exception as e:
        return {'status': 'ERROR', 'message': str(e)}
    
    return {
        'status': 'SUCCESS',
        'current_phase': current_phase.upper().replace('_', ' '),
        'phase_scores': phase_scores,
        'sector_performance': sector_performance,
        'recommended_sectors': phase_recommendations.get(current_phase, []),
        'sectors_to_avoid': _get_sectors_to_avoid(current_phase),
        'phase_description': _get_phase_description(current_phase),
        'rotation_advice': _get_rotation_advice(current_phase, sector_performance)
    }


def _get_sectors_to_avoid(phase: str) -> List[str]:
    """Get sectors that typically underperform in current phase."""
    avoid_map = {
        'early_cycle': ['Utilities', 'Consumer Staples'],
        'mid_cycle': ['Utilities', 'Real Estate'],
        'late_cycle': ['Consumer Discretionary', 'Technology'],
        'recession': ['Consumer Discretionary', 'Financials', 'Technology']
    }
    return avoid_map.get(phase, [])


def _get_phase_description(phase: str) -> str:
    """Get description of current economic cycle phase."""
    descriptions = {
        'early_cycle': "Economy recovering. Interest rates low. Credit expanding. Favor cyclicals.",
        'mid_cycle': "Economy growing steadily. Corporate profits strong. Favor growth.",
        'late_cycle': "Growth slowing. Inflation rising. Fed tightening. Favor defensives.",
        'recession': "Economic contraction. Risk-off. Favor safety: utilities, gold, treasuries."
    }
    return descriptions.get(phase, "Unknown phase")


def _get_rotation_advice(phase: str, performance: Dict) -> List[str]:
    """Generate rotation advice based on phase and momentum."""
    advice = []
    
    if phase == 'early_cycle':
        advice.append("📈 EARLY CYCLE: Overweight banks, consumer discretionary, industrials")
        advice.append("Banks benefit from steepening yield curve and loan growth")
    elif phase == 'mid_cycle':
        advice.append("📊 MID CYCLE: Favor technology and growth stocks")
        advice.append("Corporate earnings typically peak - ride the momentum")
    elif phase == 'late_cycle':
        advice.append("⚠️ LATE CYCLE: Rotate to defensives and commodities")
        advice.append("Reduce growth exposure, add energy and healthcare")
    elif phase == 'recession':
        advice.append("🛡️ RECESSION: Maximum defense - utilities, gold, treasuries")
        advice.append("Preserve capital. Cash is a position. Prepare for recovery entry.")
    
    # Add momentum-based advice
    accelerating = [s for s, d in performance.items() if d.get('momentum') == 'ACCELERATING']
    if accelerating:
        advice.append(f"Momentum accelerating in: {', '.join(accelerating[:3])}")
    
    return advice


# ==================== FEE IMPACT ANALYSIS ====================

def analyze_fee_impact(
    portfolio: List[Dict],
    holding_years: int = 5
) -> Dict:
    """
    Analyze impact of expense ratios and fees on long-term returns.
    
    Args:
        portfolio: Current portfolio holdings
        holding_years: Years to project fee impact
    
    Returns:
        Fee impact analysis with recommendations
    """
    fee_data = []
    total_weighted_expense = 0
    total_allocation = 0
    
    for holding in portfolio:
        ticker = holding.get('ticker')
        allocation = holding.get('allocation_pct', 0)
        
        if not ticker:
            continue
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Get expense ratio (for ETFs) or estimate transaction costs
            expense_ratio = info.get('annualReportExpenseRatio') or info.get('expenseRatio', 0) or 0
            
            # Detect if it's a leveraged/inverse ETF (higher costs)
            name = info.get('longName', '').upper()
            is_leveraged = any(x in name for x in ['2X', '3X', 'ULTRA', 'LEVERAGED', 'INVERSE', 'SHORT'])
            
            # Estimated implicit costs for leveraged products
            if is_leveraged:
                implicit_cost = 0.005  # Additional 0.5% drag from daily rebalancing
            else:
                implicit_cost = 0
            
            total_annual_cost = (expense_ratio or 0) + implicit_cost
            
            # Project fee drag over time
            if total_annual_cost > 0:
                # Compound impact: (1 - fee)^years shows remaining value
                fee_drag_5yr = (1 - (1 - total_annual_cost) ** holding_years) * 100
            else:
                fee_drag_5yr = 0
            
            fee_data.append({
                'ticker': ticker,
                'allocation_pct': allocation,
                'expense_ratio': round(total_annual_cost * 100, 3),
                'is_leveraged': is_leveraged,
                'annual_cost_dollars': round(total_annual_cost * allocation * 1000, 2),  # Per $100k
                f'{holding_years}yr_fee_drag_pct': round(fee_drag_5yr, 2),
                'warning': _get_fee_warning(total_annual_cost, is_leveraged)
            })
            
            total_weighted_expense += total_annual_cost * allocation
            total_allocation += allocation
            
        except Exception:
            fee_data.append({
                'ticker': ticker,
                'allocation_pct': allocation,
                'expense_ratio': 0,
                'warning': None
            })
    
    # Calculate portfolio-level fee impact
    avg_expense = (total_weighted_expense / total_allocation * 100) if total_allocation > 0 else 0
    
    # Estimate total cost over holding period (per $100k)
    total_fee_drag = (1 - (1 - total_weighted_expense/total_allocation) ** holding_years) * 100 if total_allocation > 0 else 0
    
    return {
        'status': 'SUCCESS',
        'holdings': fee_data,
        'portfolio_weighted_expense_pct': round(avg_expense, 3),
        f'{holding_years}yr_total_fee_drag_pct': round(total_fee_drag, 2),
        'annual_cost_per_100k': round(total_weighted_expense * 1000, 2),
        f'{holding_years}yr_cost_per_100k': round(total_fee_drag * 1000, 2),
        'high_fee_holdings': [h for h in fee_data if (h.get('expense_ratio', 0) > 0.5) or h.get('is_leveraged')],
        'recommendations': _get_fee_recommendations(avg_expense, fee_data)
    }


def _get_fee_warning(expense: float, is_leveraged: bool) -> Optional[str]:
    """Generate fee warning if applicable."""
    if is_leveraged:
        return "⚠️ Leveraged/Inverse ETF - hidden decay costs from daily rebalancing"
    elif expense > 0.01:
        return f"🟡 High expense ratio ({expense*100:.2f}%). Consider lower-cost alternative."
    elif expense > 0.005:
        return "Moderate expense ratio. Acceptable for active management."
    return None


def _get_fee_recommendations(avg_expense: float, holdings: List[Dict]) -> List[str]:
    """Generate fee-related recommendations."""
    recs = []
    
    if avg_expense > 0.5:
        recs.append("🔴 Portfolio expense ratio is high. Consider switching to low-cost index ETFs.")
    
    leveraged = [h['ticker'] for h in holdings if h.get('is_leveraged')]
    if leveraged:
        recs.append(f"⚠️ Leveraged ETFs ({', '.join(leveraged)}) have hidden decay. Use for short-term only.")
    
    high_fee = [h['ticker'] for h in holdings if h.get('expense_ratio', 0) > 0.75]
    if high_fee:
        recs.append(f"Consider lower-cost alternatives for: {', '.join(high_fee)}")
    
    if not recs:
        recs.append("🟢 Portfolio fee structure is reasonable.")
    
    return recs


# ==================== EX-DIVIDEND CAPTURE OPTIMIZATION ====================

def optimize_dividend_timing(
    portfolio: List[Dict],
    watchlist: List[str] = None,
    days_ahead: int = 30
) -> Dict:
    """
    Analyze dividend timing opportunities and risks.
    
    Key dates:
    - Declaration date: Dividend announced
    - Ex-dividend date: Must own BEFORE this date to receive dividend
    - Record date: Company checks ownership
    - Payment date: Dividend paid
    
    Args:
        portfolio: Current portfolio holdings
        watchlist: Additional tickers to analyze
        days_ahead: Days to look ahead for ex-dividend dates
    
    Returns:
        Dividend timing analysis with recommendations
    """
    tickers = [h.get('ticker') for h in portfolio if h.get('ticker')]
    if watchlist:
        tickers.extend(watchlist)
    tickers = list(set(tickers))
    
    upcoming_dividends = []
    hold_recommendations = []
    buy_opportunities = []
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            
            # Get dividend info
            calendar = stock.calendar
            info = stock.info
            
            div_rate = info.get('dividendRate', 0) or 0
            div_yield = info.get('dividendYield', 0) or 0
            current_price = info.get('currentPrice') or info.get('regularMarketPrice') or 0
            
            if div_rate <= 0:
                continue
            
            # Try to get ex-dividend date
            ex_div_date = None
            if hasattr(calendar, 'get'):
                ex_div_date = calendar.get('Ex-Dividend Date')
            elif isinstance(calendar, pd.DataFrame) and 'Ex-Dividend Date' in calendar.index:
                ex_div_date = calendar.loc['Ex-Dividend Date'].iloc[0]
            
            # If no upcoming ex-div date, estimate based on quarterly pattern
            if ex_div_date is None or (isinstance(ex_div_date, datetime) and ex_div_date < datetime.now()):
                # Estimate next quarterly dividend
                quarterly_div = div_rate / 4
                div_yield_single = (quarterly_div / current_price) * 100 if current_price > 0 else 0
                
                upcoming_dividends.append({
                    'ticker': ticker,
                    'quarterly_dividend': round(quarterly_div, 3),
                    'annual_yield_pct': round(div_yield * 100, 2),
                    'single_div_yield_pct': round(div_yield_single, 2),
                    'ex_div_date': 'Check investor relations',
                    'current_price': round(current_price, 2)
                })
            else:
                # We have an ex-dividend date
                if isinstance(ex_div_date, str):
                    ex_div_date = datetime.strptime(ex_div_date, '%Y-%m-%d')
                
                days_until_ex = (ex_div_date - datetime.now()).days
                
                quarterly_div = div_rate / 4
                div_yield_single = (quarterly_div / current_price) * 100 if current_price > 0 else 0
                
                dividend_info = {
                    'ticker': ticker,
                    'ex_div_date': ex_div_date.strftime('%Y-%m-%d'),
                    'days_until_ex': days_until_ex,
                    'quarterly_dividend': round(quarterly_div, 3),
                    'annual_yield_pct': round(div_yield * 100, 2),
                    'single_div_yield_pct': round(div_yield_single, 2),
                    'current_price': round(current_price, 2)
                }
                
                if 0 < days_until_ex <= days_ahead:
                    upcoming_dividends.append(dividend_info)
                    
                    # Check if in portfolio
                    in_portfolio = ticker in [h.get('ticker') for h in portfolio]
                    
                    if in_portfolio:
                        # Recommend holding through ex-div if yield is material
                        if div_yield_single >= 0.5:
                            hold_recommendations.append({
                                **dividend_info,
                                'action': 'HOLD',
                                'reason': f"Hold through ex-div to capture ${quarterly_div:.2f}/share ({div_yield_single:.2f}%)"
                            })
                    else:
                        # Potential buy opportunity
                        if div_yield_single >= 0.75 and days_until_ex >= 3:
                            buy_opportunities.append({
                                **dividend_info,
                                'action': 'CONSIDER_BUY',
                                'reason': f"Buy before {ex_div_date.strftime('%m/%d')} for ${quarterly_div:.2f} dividend"
                            })
                            
        except Exception:
            continue
    
    # Sort by ex-div date
    upcoming_dividends.sort(key=lambda x: x.get('days_until_ex', 999))
    
    return {
        'status': 'SUCCESS',
        'upcoming_dividends': upcoming_dividends,
        'hold_recommendations': hold_recommendations,
        'buy_opportunities': buy_opportunities,
        'warnings': _get_dividend_warnings(),
        'total_upcoming_in_portfolio': len(hold_recommendations)
    }


def _get_dividend_warnings() -> List[str]:
    """Generate dividend-related warnings for retail investors."""
    return [
        "⚠️ Stock price typically drops by dividend amount on ex-date",
        "📅 You must own BEFORE ex-dividend date to receive dividend",
        "💰 Qualified dividends (held 60+ days) taxed at lower rate",
        "🚫 Don't buy solely for dividend - ensure thesis is sound"
    ]


# ==================== COMPREHENSIVE RETAIL ANALYSIS ====================

def run_retail_investor_analysis(
    portfolio: List[Dict],
    current_prices: Dict[str, float],
    watchlist: List[str] = None
) -> Dict:
    """
    Run comprehensive analysis specifically for retail investors.
    Combines all retail-focused insights into one actionable report.
    
    Args:
        portfolio: Current portfolio holdings
        current_prices: Dictionary of current prices
        watchlist: Additional tickers to analyze
    
    Returns:
        Complete retail investor analysis
    """
    print("  Running retail investor analysis...")
    
    # Get all tickers
    portfolio_tickers = [h.get('ticker') for h in portfolio if h.get('ticker')]
    all_tickers = list(set(portfolio_tickers + (watchlist or [])))
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'status': 'SUCCESS'
    }
    
    # 1. Tax-Loss Harvesting
    print("    Analyzing tax-loss harvesting opportunities...")
    results['tax_loss_harvesting'] = detect_tax_loss_harvesting_opportunities(
        portfolio, current_prices
    )
    
    # 2. Portfolio Correlation
    print("    Analyzing portfolio correlation...")
    results['correlation_analysis'] = analyze_portfolio_correlation(portfolio)
    
    # 3. Liquidity Risks
    print("    Analyzing liquidity risks...")
    results['liquidity_analysis'] = analyze_liquidity_risks(portfolio, watchlist)
    
    # 4. Trailing Stops
    print("    Calculating trailing stops...")
    results['trailing_stops'] = calculate_trailing_stops(portfolio, current_prices)
    
    # 5. Short Interest
    print("    Analyzing short interest...")
    results['short_interest'] = analyze_short_interest(all_tickers[:20])  # Limit for speed
    
    # 6. Institutional Ownership
    print("    Analyzing institutional ownership...")
    results['institutional_ownership'] = analyze_institutional_ownership(all_tickers[:20])
    
    # 7. Sector Rotation
    print("    Analyzing sector rotation...")
    results['sector_rotation'] = analyze_sector_rotation()
    
    # 8. Fee Impact
    print("    Analyzing fee impact...")
    results['fee_analysis'] = analyze_fee_impact(portfolio)
    
    # 9. Dividend Timing
    print("    Analyzing dividend timing...")
    results['dividend_timing'] = optimize_dividend_timing(portfolio, watchlist)
    
    # Generate priority alerts
    results['priority_alerts'] = _generate_priority_alerts(results)
    
    print("  ✓ Retail investor analysis complete")
    return results


def _generate_priority_alerts(analysis: Dict) -> List[Dict]:
    """Generate prioritized alerts from all analyses."""
    alerts = []
    
    # Tax-loss harvesting alerts (high priority near year-end)
    tlh = analysis.get('tax_loss_harvesting', [])
    high_priority_tlh = [t for t in tlh if t.get('priority') == 'HIGH']
    if high_priority_tlh:
        alerts.append({
            'priority': 'HIGH',
            'category': 'TAX_OPTIMIZATION',
            'title': f"🏦 {len(high_priority_tlh)} Tax-Loss Harvesting Opportunities",
            'details': [f"{t['ticker']}: {t['loss_pct']:.1f}% loss" for t in high_priority_tlh[:3]],
            'action': "Review for potential tax savings before year-end"
        })
    
    # High correlation warnings
    corr = analysis.get('correlation_analysis', {})
    high_corr = corr.get('high_correlation_pairs', [])
    if high_corr:
        alerts.append({
            'priority': 'MEDIUM',
            'category': 'DIVERSIFICATION',
            'title': f"📊 {len(high_corr)} Highly Correlated Position Pairs",
            'details': [f"{p['pair'][0]}/{p['pair'][1]}: {p['correlation']:.0%} correlated" for p in high_corr[:3]],
            'action': "Consider reducing one position in each pair"
        })
    
    # Liquidity warnings
    liq = analysis.get('liquidity_analysis', {})
    high_risk_liq = [w for w in liq.get('warnings', []) if w.get('severity') == 'HIGH']
    if high_risk_liq:
        alerts.append({
            'priority': 'HIGH',
            'category': 'LIQUIDITY',
            'title': f"💧 {len(high_risk_liq)} Illiquid Positions",
            'details': [f"{w['ticker']}: Low volume, ~{w['spread_pct']:.2f}% spread" for w in high_risk_liq[:3]],
            'action': "Use LIMIT orders only. Consider position size."
        })
    
    # Squeeze candidates
    short = analysis.get('short_interest', [])
    squeezes = [s for s in short if s.get('potential_squeeze')]
    if squeezes:
        alerts.append({
            'priority': 'HIGH',
            'category': 'OPPORTUNITY',
            'title': f"🚀 {len(squeezes)} Potential Short Squeeze(s)",
            'details': [f"{s['ticker']}: {s['short_pct_of_float']:.1f}% short, +{s['price_change_1mo']:.1f}% this month" for s in squeezes[:3]],
            'action': "High risk/reward. Consider momentum play with tight stop."
        })
    
    # Upcoming dividends
    div = analysis.get('dividend_timing', {})
    hold_recs = div.get('hold_recommendations', [])
    if hold_recs:
        alerts.append({
            'priority': 'MEDIUM',
            'category': 'INCOME',
            'title': f"💰 {len(hold_recs)} Positions with Upcoming Dividends",
            'details': [f"{d['ticker']}: Ex-div {d['ex_div_date']} (${d['quarterly_dividend']:.2f})" for d in hold_recs[:3]],
            'action': "Hold through ex-dividend date to capture income"
        })
    
    # High fee warnings
    fees = analysis.get('fee_analysis', {})
    high_fee = fees.get('high_fee_holdings', [])
    if high_fee:
        alerts.append({
            'priority': 'LOW',
            'category': 'COSTS',
            'title': f"💸 {len(high_fee)} High-Fee Holdings",
            'details': [f"{h['ticker']}: {h['expense_ratio']:.2f}% annual expense" for h in high_fee[:3]],
            'action': "Consider lower-cost alternatives for long-term holdings"
        })
    
    # Sort by priority
    priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    alerts.sort(key=lambda x: priority_order.get(x['priority'], 3))
    
    return alerts
