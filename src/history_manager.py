"""
Portfolio history management module.
Handles loading, saving, and updating portfolio state across months.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from config import PATHS, ALLOCATION_RULES
from data_fetcher import get_current_prices


def load_history(file_path: Optional[str] = None) -> Dict:
    """
    Load portfolio history from JSON file.
    
    Args:
        file_path: Path to history file (uses default if None)
    
    Returns:
        Portfolio history dictionary
    """
    if file_path is None:
        file_path = PATHS['portfolio_history']
    
    # Handle relative path from project root
    if not os.path.isabs(file_path):
        # Try to find the file relative to the script location
        script_dir = Path(__file__).parent.parent
        file_path = script_dir / file_path
    
    try:
        with open(file_path, 'r') as f:
            history = json.load(f)
            return history
    except FileNotFoundError:
        print(f"Portfolio history not found at {file_path}, creating new one...")
        return _create_empty_history()
    except json.JSONDecodeError as e:
        print(f"Error parsing portfolio history: {e}")
        return _create_empty_history()


def save_history(history: Dict, file_path: Optional[str] = None) -> bool:
    """
    Save portfolio history to JSON file.
    
    Args:
        history: Portfolio history dictionary
        file_path: Path to save file (uses default if None)
    
    Returns:
        True if successful, False otherwise
    """
    if file_path is None:
        file_path = PATHS['portfolio_history']
    
    # Handle relative path
    if not os.path.isabs(file_path):
        script_dir = Path(__file__).parent.parent
        file_path = script_dir / file_path
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Update metadata
    history['metadata']['last_updated'] = datetime.now().strftime('%Y-%m-%d')
    
    try:
        with open(file_path, 'w') as f:
            json.dump(history, f, indent=2, default=str)
        print(f"Portfolio history saved to {file_path}")
        return True
    except Exception as e:
        print(f"Error saving portfolio history: {e}")
        return False


def _create_empty_history() -> Dict:
    """
    Create a new empty portfolio history structure.
    
    Returns:
        Empty portfolio history dictionary
    """
    return {
        "metadata": {
            "created": datetime.now().strftime('%Y-%m-%d'),
            "last_updated": datetime.now().strftime('%Y-%m-%d'),
            "total_months": 0,
            "starting_capital": 100000
        },
        "current_portfolio": [],
        "cash": {
            "allocation_pct": 100.0,
            "vehicle": "SGOV",
            "yield_pct": 5.1
        },
        "monthly_history": [],
        "closed_positions": [],
        "performance_summary": {
            "total_return_pct": 0.0,
            "sp500_total_return_pct": 0.0,
            "total_alpha_pct": 0.0,
            "win_count": 0,
            "loss_count": 0,
            "win_rate_pct": 0.0,
            "average_win_pct": 0.0,
            "average_loss_pct": 0.0,
            "best_trade": None,
            "worst_trade": None
        }
    }


def calculate_performance(current_portfolio: List[Dict], 
                          market_data: Dict) -> List[Dict]:
    """
    Calculate current performance for all holdings.
    
    Args:
        current_portfolio: List of current holdings
        market_data: Current market data
    
    Returns:
        Portfolio with updated performance metrics
    """
    if not current_portfolio:
        return []
    
    # Get current prices for all holdings
    tickers = [h['ticker'] for h in current_portfolio]
    current_prices = get_current_prices(tickers)
    
    updated_portfolio = []
    for holding in current_portfolio:
        ticker = holding['ticker']
        entry_price = holding.get('recommended_price', 0)
        current_price = current_prices.get(ticker, entry_price)
        
        # Calculate gain/loss
        if entry_price > 0:
            gain_loss_pct = ((current_price / entry_price) - 1) * 100
        else:
            gain_loss_pct = 0
        
        # Check stop-loss and target
        stop_loss = holding.get('stop_loss') or 0
        price_target = holding.get('price_target') or 0
        
        status = holding.get('status', 'HOLD')
        if stop_loss and current_price <= stop_loss:
            status = 'STOP_LOSS_HIT'
        elif price_target and current_price >= price_target:
            status = 'TARGET_REACHED'
        
        updated_holding = {
            **holding,
            'current_price': round(current_price, 2),
            'gain_loss_pct': round(gain_loss_pct, 2),
            'status': status,
            'last_reviewed': datetime.now().strftime('%Y-%m-%d')
        }
        updated_portfolio.append(updated_holding)
    
    return updated_portfolio


def calculate_portfolio_value(portfolio: List[Dict], cash: Dict, 
                              starting_capital: float = 100000) -> Dict:
    """
    Calculate total portfolio value and allocation percentages.
    
    Args:
        portfolio: Current holdings
        cash: Cash position info
        starting_capital: Initial capital
    
    Returns:
        Dictionary with portfolio value metrics
    """
    total_allocation = sum(h.get('allocation_pct', 0) for h in portfolio)
    cash_allocation = cash.get('allocation_pct', 0)
    
    # Calculate implied value based on allocations
    invested_value = (total_allocation / 100) * starting_capital
    cash_value = (cash_allocation / 100) * starting_capital
    
    # If we have current prices and shares, calculate actual value
    actual_value = 0
    for holding in portfolio:
        shares = holding.get('shares', 0)
        current_price = holding.get('current_price', holding.get('recommended_price', 0))
        actual_value += shares * current_price
    
    return {
        'total_allocation_pct': total_allocation + cash_allocation,
        'invested_allocation_pct': total_allocation,
        'cash_allocation_pct': cash_allocation,
        'implied_portfolio_value': invested_value + cash_value,
        'actual_portfolio_value': actual_value + cash_value if actual_value > 0 else None,
        'position_count': len(portfolio)
    }


def validate_allocations(portfolio: List[Dict], cash: Dict) -> Dict:
    """
    Validate portfolio allocations against diversification rules.
    
    Args:
        portfolio: Current holdings
        cash: Cash position info
    
    Returns:
        Dictionary with validation results
    """
    violations = []
    warnings = []
    
    # Check total allocation
    total_alloc = sum(h.get('allocation_pct', 0) for h in portfolio)
    total_alloc += cash.get('allocation_pct', 0)
    
    if abs(total_alloc - 100) > 0.5:
        warnings.append(f"Total allocation is {total_alloc:.1f}% (should be ~100%)")
    
    # Check single stock max
    for holding in portfolio:
        alloc = holding.get('allocation_pct', 0)
        if alloc > ALLOCATION_RULES['single_stock_max'] * 100:
            violations.append(
                f"{holding['ticker']} allocation {alloc:.1f}% exceeds "
                f"{ALLOCATION_RULES['single_stock_max']*100:.0f}% maximum"
            )
    
    # Check sector concentration
    sector_allocs = {}
    for holding in portfolio:
        sector = holding.get('sector', 'Unknown')
        sector_allocs[sector] = sector_allocs.get(sector, 0) + holding.get('allocation_pct', 0)
    
    for sector, alloc in sector_allocs.items():
        if alloc > ALLOCATION_RULES['single_sector_max'] * 100:
            violations.append(
                f"{sector} sector allocation {alloc:.1f}% exceeds "
                f"{ALLOCATION_RULES['single_sector_max']*100:.0f}% maximum"
            )
    
    # Check position count
    pos_count = len(portfolio)
    if pos_count < ALLOCATION_RULES['min_positions'] and pos_count > 0:
        warnings.append(
            f"Position count ({pos_count}) below minimum "
            f"({ALLOCATION_RULES['min_positions']})"
        )
    if pos_count > ALLOCATION_RULES['max_positions']:
        violations.append(
            f"Position count ({pos_count}) exceeds maximum "
            f"({ALLOCATION_RULES['max_positions']})"
        )
    
    # Check asset class allocations
    asset_class_allocs = {}
    for holding in portfolio:
        asset_class = holding.get('asset_class', 'us_stock')
        asset_class_allocs[asset_class] = (
            asset_class_allocs.get(asset_class, 0) + 
            holding.get('allocation_pct', 0)
        )
    
    # Map to rule categories
    us_stocks = asset_class_allocs.get('us_stock', 0)
    rules = ALLOCATION_RULES['us_stocks']
    if us_stocks < rules['min'] * 100 or us_stocks > rules['max'] * 100:
        warnings.append(
            f"US stocks allocation {us_stocks:.1f}% outside target range "
            f"({rules['min']*100:.0f}%-{rules['max']*100:.0f}%)"
        )
    
    # Check bonds/cash
    bonds_cash = cash.get('allocation_pct', 0) + asset_class_allocs.get('bond_etf', 0)
    rules = ALLOCATION_RULES['bonds_cash']
    if bonds_cash < rules['min'] * 100 or bonds_cash > rules['max'] * 100:
        warnings.append(
            f"Bonds/Cash allocation {bonds_cash:.1f}% outside target range "
            f"({rules['min']*100:.0f}%-{rules['max']*100:.0f}%)"
        )
    
    return {
        'is_valid': len(violations) == 0,
        'violations': violations,
        'warnings': warnings,
        'sector_allocations': sector_allocs,
        'asset_class_allocations': asset_class_allocs
    }


def update_history_with_month(history: Dict, analysis_result: Dict, 
                              market_data: Dict) -> Dict:
    """
    Update portfolio history with current month's analysis results.
    
    Args:
        history: Current portfolio history
        analysis_result: Claude's analysis output
        market_data: Current market data
    
    Returns:
        Updated portfolio history
    """
    current_month = datetime.now().strftime('%Y-%m')
    
    # Calculate this month's performance
    old_portfolio = history.get('current_portfolio', [])
    
    # Process sells
    sells = analysis_result.get('sells', [])
    closed_this_month = []
    for sell in sells:
        ticker = sell.get('ticker')
        # Find the original position
        original = next((h for h in old_portfolio if h['ticker'] == ticker), None)
        if original:
            closed_this_month.append({
                'ticker': ticker,
                'company_name': original.get('company_name', ''),
                'buy_date': original.get('recommended_date'),
                'buy_price': original.get('recommended_price'),
                'sell_date': datetime.now().strftime('%Y-%m-%d'),
                'sell_price': sell.get('sell_price', original.get('current_price')),
                'return_pct': sell.get('loss_pct', 0),
                'hold_period_days': _calculate_hold_days(original.get('recommended_date')),
                'reason': sell.get('reason', ''),
                'lesson_learned': sell.get('lesson_learned', '')
            })
    
    # Update closed positions
    history['closed_positions'].extend(closed_this_month)
    
    # Build new portfolio from review + new recommendations
    new_portfolio = []
    
    # Process portfolio review (holds and trims)
    portfolio_review = analysis_result.get('portfolio_review', [])
    for review in portfolio_review:
        if review.get('action') in ['HOLD', 'TRIM']:
            ticker = review.get('ticker')
            original = next((h for h in old_portfolio if h['ticker'] == ticker), None)
            if original:
                updated = {**original}
                updated['allocation_pct'] = review.get('new_allocation_pct', original['allocation_pct'])
                updated['status'] = review.get('action')
                updated['last_reviewed'] = datetime.now().strftime('%Y-%m-%d')
                new_portfolio.append(updated)
    
    # Add new recommendations
    new_recs = analysis_result.get('new_recommendations', [])
    for rec in new_recs:
        new_portfolio.append({
            'ticker': rec.get('ticker'),
            'company_name': rec.get('company_name', ''),
            'asset_class': rec.get('asset_class', 'us_stock'),
            'sector': rec.get('sector', 'Unknown'),
            'sub_industry': rec.get('sub_industry', ''),
            'market_cap': rec.get('market_cap', ''),
            'geography': rec.get('geography', 'US'),
            'investment_style': rec.get('investment_style', 'value'),
            'risk_level': rec.get('risk_level', 'moderate'),
            'time_horizon': rec.get('time_horizon', 'medium_term'),
            'allocation_pct': rec.get('allocation_pct', 0),
            'shares': 0,  # Would need to calculate based on price and allocation
            'recommended_date': datetime.now().strftime('%Y-%m-%d'),
            'recommended_price': rec.get('entry_zone', {}).get('low', 0),
            'entry_zone': rec.get('entry_zone', {}),
            'price_target': rec.get('price_target', 0),
            'stop_loss': rec.get('stop_loss', 0),
            'thesis': rec.get('thesis', ''),
            'status': 'BUY',
            'last_reviewed': datetime.now().strftime('%Y-%m-%d')
        })
    
    # Update current portfolio
    history['current_portfolio'] = new_portfolio
    
    # Update cash
    allocation_summary = analysis_result.get('allocation_summary', {})
    cash_alloc = 100 - sum(h.get('allocation_pct', 0) for h in new_portfolio)
    history['cash']['allocation_pct'] = max(0, cash_alloc)
    
    # Add month to history
    sp500_return = market_data.get('indexes', {}).get('S&P 500', {}).get('returns', {}).get('1mo', 0)
    portfolio_return = _calculate_portfolio_return(old_portfolio, new_portfolio)
    
    month_record = {
        'month': current_month,
        'starting_value': history['metadata'].get('starting_capital', 100000),
        'ending_value': history['metadata'].get('starting_capital', 100000) * (1 + portfolio_return/100),
        'portfolio_return_pct': round(portfolio_return, 2),
        'sp500_return_pct': round(sp500_return, 2),
        'alpha_pct': round(portfolio_return - sp500_return, 2),
        'recommendations_made': [
            {'ticker': r.get('ticker'), 'action': 'BUY', 'allocation': r.get('allocation_pct')}
            for r in new_recs
        ],
        'sells_executed': [{'ticker': s.get('ticker'), 'return_pct': s.get('loss_pct', 0)} for s in sells],
        'notable_politician_trades': analysis_result.get('politician_trade_analysis', {}).get('notable_trades', [])
    }
    history['monthly_history'].append(month_record)
    
    # Update performance summary
    history['performance_summary'] = _update_performance_summary(history)
    
    # Update metadata
    history['metadata']['total_months'] = len(history['monthly_history'])
    history['metadata']['last_updated'] = datetime.now().strftime('%Y-%m-%d')
    
    return history


def _calculate_hold_days(buy_date_str: str) -> int:
    """Calculate days held from buy date to today."""
    if not buy_date_str:
        return 0
    try:
        buy_date = datetime.strptime(buy_date_str, '%Y-%m-%d')
        return (datetime.now() - buy_date).days
    except ValueError:
        return 0


def _calculate_portfolio_return(old_portfolio: List[Dict], 
                                new_portfolio: List[Dict]) -> float:
    """Calculate approximate portfolio return for the month."""
    if not old_portfolio:
        return 0.0
    
    total_weighted_return = 0
    total_weight = 0
    
    for holding in old_portfolio:
        weight = holding.get('allocation_pct', 0)
        gain = holding.get('gain_loss_pct', 0)
        total_weighted_return += weight * gain
        total_weight += weight
    
    if total_weight > 0:
        return total_weighted_return / total_weight
    return 0.0


def _update_performance_summary(history: Dict) -> Dict:
    """Update cumulative performance summary."""
    closed = history.get('closed_positions', [])
    monthly = history.get('monthly_history', [])
    
    wins = [c for c in closed if c.get('return_pct', 0) > 0]
    losses = [c for c in closed if c.get('return_pct', 0) <= 0]
    
    total_return = sum(m.get('portfolio_return_pct', 0) for m in monthly)
    sp500_return = sum(m.get('sp500_return_pct', 0) for m in monthly)
    
    avg_win = sum(w.get('return_pct', 0) for w in wins) / len(wins) if wins else 0
    avg_loss = sum(l.get('return_pct', 0) for l in losses) / len(losses) if losses else 0
    
    best = max(closed, key=lambda x: x.get('return_pct', 0)) if closed else None
    worst = min(closed, key=lambda x: x.get('return_pct', 0)) if closed else None
    
    return {
        'total_return_pct': round(total_return, 2),
        'sp500_total_return_pct': round(sp500_return, 2),
        'total_alpha_pct': round(total_return - sp500_return, 2),
        'win_count': len(wins),
        'loss_count': len(losses),
        'win_rate_pct': round(len(wins) / (len(wins) + len(losses)) * 100, 1) if (wins or losses) else 0,
        'average_win_pct': round(avg_win, 2),
        'average_loss_pct': round(avg_loss, 2),
        'best_trade': {'ticker': best['ticker'], 'return_pct': best['return_pct']} if best else None,
        'worst_trade': {'ticker': worst['ticker'], 'return_pct': worst['return_pct']} if worst else None
    }


def calculate_risk_metrics(history: Dict) -> Dict:
    """
    Calculate risk management metrics including drawdown and risk status.
    
    Industry-standard thresholds:
    - Max Drawdown Warning: -10%
    - Max Drawdown Defensive: -15%
    - Win Rate Warning: <40% after 5+ trades
    - Consecutive Losses Warning: 3+
    - Losing Streak Defensive: 4+ consecutive losses
    
    Args:
        history: Portfolio history dictionary
    
    Returns:
        Dictionary with risk metrics and recommended mode
    """
    perf = history.get('performance_summary', {})
    monthly = history.get('monthly_history', [])
    closed = history.get('closed_positions', [])
    
    # Calculate drawdown from peak
    peak_value = 100000  # Starting capital
    current_value = 100000
    
    if monthly:
        # Track running portfolio value and peak
        running_value = 100000
        for month in monthly:
            month_return = month.get('portfolio_return_pct', 0)
            running_value *= (1 + month_return / 100)
            peak_value = max(peak_value, running_value)
        current_value = running_value
    
    drawdown_pct = ((current_value - peak_value) / peak_value) * 100 if peak_value > 0 else 0
    
    # Count consecutive losses (most recent trades)
    consecutive_losses = 0
    if monthly:
        for month in reversed(monthly):
            if month.get('portfolio_return_pct', 0) < 0:
                consecutive_losses += 1
            else:
                break
    
    # Also check recent closed positions for streak
    recent_closed_losses = 0
    for pos in reversed(closed[-5:]):  # Last 5 closed positions
        if pos.get('return_pct', 0) < 0:
            recent_closed_losses += 1
        else:
            break
    
    consecutive_losses = max(consecutive_losses, recent_closed_losses)
    
    # Get performance metrics
    total_return = perf.get('total_return_pct', 0)
    win_rate = perf.get('win_rate_pct', 0)
    total_trades = perf.get('win_count', 0) + perf.get('loss_count', 0)
    alpha = perf.get('total_alpha_pct', 0)
    
    # Determine risk status based on industry-standard thresholds
    risk_status = "NORMAL"
    risk_reasons = []
    
    # Drawdown checks (industry standard: -10% caution, -15% defensive, -20% critical)
    if drawdown_pct <= -20:
        risk_status = "CRITICAL"
        risk_reasons.append(f"Severe drawdown: {drawdown_pct:.1f}% from peak")
    elif drawdown_pct <= -15:
        risk_status = "DEFENSIVE"
        risk_reasons.append(f"Significant drawdown: {drawdown_pct:.1f}% from peak")
    elif drawdown_pct <= -10:
        risk_status = "CAUTION"
        risk_reasons.append(f"Elevated drawdown: {drawdown_pct:.1f}% from peak")
    
    # Win rate checks (only after sufficient trades)
    if total_trades >= 5:
        if win_rate < 30:
            risk_status = max(risk_status, "DEFENSIVE", key=lambda x: ["NORMAL", "CAUTION", "DEFENSIVE", "CRITICAL"].index(x))
            risk_reasons.append(f"Poor win rate: {win_rate:.1f}% ({total_trades} trades)")
        elif win_rate < 40:
            if risk_status == "NORMAL":
                risk_status = "CAUTION"
            risk_reasons.append(f"Below-average win rate: {win_rate:.1f}%")
    
    # Consecutive loss checks
    if consecutive_losses >= 4:
        risk_status = max(risk_status, "DEFENSIVE", key=lambda x: ["NORMAL", "CAUTION", "DEFENSIVE", "CRITICAL"].index(x))
        risk_reasons.append(f"Losing streak: {consecutive_losses} consecutive losses")
    elif consecutive_losses >= 3:
        if risk_status == "NORMAL":
            risk_status = "CAUTION"
        risk_reasons.append(f"Loss streak building: {consecutive_losses} consecutive losses")
    
    # Significant underperformance vs benchmark
    if total_trades >= 3 and alpha < -10:
        risk_status = max(risk_status, "CAUTION", key=lambda x: ["NORMAL", "CAUTION", "DEFENSIVE", "CRITICAL"].index(x))
        risk_reasons.append(f"Significant underperformance vs S&P 500: {alpha:.1f}%")
    
    # Define mode-specific rules
    mode_rules = {
        "NORMAL": {
            "max_position_size": 15,
            "min_cash": 5,
            "aggressive_allowed": True,
            "speculative_allowed": True,
            "max_new_positions": 5
        },
        "CAUTION": {
            "max_position_size": 10,
            "min_cash": 15,
            "aggressive_allowed": True,
            "speculative_allowed": False,
            "max_new_positions": 3
        },
        "DEFENSIVE": {
            "max_position_size": 7,
            "min_cash": 25,
            "aggressive_allowed": False,
            "speculative_allowed": False,
            "max_new_positions": 2
        },
        "CRITICAL": {
            "max_position_size": 5,
            "min_cash": 40,
            "aggressive_allowed": False,
            "speculative_allowed": False,
            "max_new_positions": 1
        }
    }
    
    return {
        "risk_status": risk_status,
        "risk_reasons": risk_reasons,
        "metrics": {
            "current_value": round(current_value, 2),
            "peak_value": round(peak_value, 2),
            "drawdown_pct": round(drawdown_pct, 2),
            "consecutive_losses": consecutive_losses,
            "win_rate_pct": win_rate,
            "total_trades": total_trades,
            "alpha_vs_sp500": round(alpha, 2)
        },
        "rules": mode_rules[risk_status],
        "recommendations": _get_risk_recommendations(risk_status, risk_reasons)
    }


def _get_risk_recommendations(status: str, reasons: List[str]) -> List[str]:
    """Generate specific recommendations based on risk status."""
    recommendations = []
    
    if status == "NORMAL":
        recommendations.append("Continue with standard investment approach")
        recommendations.append("Maintain diversification across sectors and styles")
    
    elif status == "CAUTION":
        recommendations.append("Reduce position sizes on new investments")
        recommendations.append("Avoid speculative plays until performance improves")
        recommendations.append("Consider trimming underperforming positions")
        recommendations.append("Increase cash buffer to 15%+")
    
    elif status == "DEFENSIVE":
        recommendations.append("HALT new aggressive/speculative positions")
        recommendations.append("Reduce all position sizes to max 7%")
        recommendations.append("Increase cash to 25%+ (safety cushion)")
        recommendations.append("Focus only on high-conviction, conservative ideas")
        recommendations.append("Review and potentially exit all losing positions")
        recommendations.append("Consider defensive sectors: utilities, healthcare, staples")
    
    elif status == "CRITICAL":
        recommendations.append("⚠️ EMERGENCY: Consider moving to 40%+ cash")
        recommendations.append("Exit all speculative and high-beta positions")
        recommendations.append("Max 5% position sizes only")
        recommendations.append("Only ultra-conservative investments (treasuries, dividend aristocrats)")
        recommendations.append("Review entire strategy before committing new capital")
    
    return recommendations


def get_portfolio_summary(history: Dict) -> str:
    """
    Generate a text summary of current portfolio state.
    
    Args:
        history: Portfolio history dictionary
    
    Returns:
        Formatted summary string
    """
    portfolio = history.get('current_portfolio', [])
    cash = history.get('cash', {})
    perf = history.get('performance_summary', {})
    
    lines = [
        "=" * 50,
        "PORTFOLIO SUMMARY",
        "=" * 50,
        f"Positions: {len(portfolio)}",
        f"Cash: {cash.get('allocation_pct', 0):.1f}%",
        "",
        "Current Holdings:"
    ]
    
    for h in portfolio:
        gain = h.get('gain_loss_pct', 0)
        emoji = "🟢" if gain > 0 else "🔴" if gain < 0 else "⚪"
        lines.append(
            f"  {emoji} {h['ticker']}: {h.get('allocation_pct', 0):.1f}% "
            f"({gain:+.1f}%)"
        )
    
    lines.extend([
        "",
        "Performance:",
        f"  Total Return: {perf.get('total_return_pct', 0):.2f}%",
        f"  vs S&P 500: {perf.get('total_alpha_pct', 0):+.2f}%",
        f"  Win Rate: {perf.get('win_rate_pct', 0):.1f}%",
        "=" * 50
    ])
    
    return "\n".join(lines)
