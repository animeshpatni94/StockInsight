"""
Portfolio history management module.
Handles loading, saving, and updating portfolio state across months.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from collections import defaultdict

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
            
            # Validate and fix any data integrity issues
            history = _validate_and_fix_history(history)
            
            return history
    except FileNotFoundError:
        print(f"Portfolio history not found at {file_path}, creating new one...")
        return _create_empty_history()
    except json.JSONDecodeError as e:
        print(f"Error parsing portfolio history: {e}")
        return _create_empty_history()


def _validate_and_fix_history(history: Dict) -> Dict:
    """
    Validate history data and fix any issues.
    Called automatically when loading history.
    """
    needs_recalc = False
    
    # Fix duplicate months in history
    monthly = history.get('monthly_history', [])
    if monthly:
        seen_months = {}
        unique_monthly = []
        for m in monthly:
            month = m.get('month')
            if month not in seen_months:
                seen_months[month] = True
                unique_monthly.append(m)
            else:
                print(f"  Removed duplicate month entry: {month}")
                needs_recalc = True
        history['monthly_history'] = unique_monthly
    
    # Fix closed positions with missing sell prices
    closed = history.get('closed_positions', [])
    needs_fix = [p for p in closed if p.get('sell_price') is None]
    if needs_fix:
        tickers = [p.get('ticker') for p in needs_fix if p.get('ticker')]
        if tickers:
            print(f"  Fixing {len(needs_fix)} closed positions with missing sell prices...")
            current_prices = get_current_prices(tickers)
            for pos in needs_fix:
                ticker = pos.get('ticker')
                buy_price = pos.get('buy_price', 0)
                if ticker in current_prices and buy_price > 0:
                    sell_price = current_prices[ticker]
                    pos['sell_price'] = round(sell_price, 2)
                    pos['return_pct'] = round(((sell_price / buy_price) - 1) * 100, 2)
                    needs_recalc = True
    
    # IMMEDIATELY recalculate performance summary if any fixes were applied
    if needs_recalc:
        print("  Recalculating performance summary after data fixes...")
        history['performance_summary'] = _update_performance_summary(history)
    
    return history


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



# NOTE: fix_closed_positions() was removed - functionality now handled by _validate_and_fix_history()


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
                          market_data: Dict) -> Tuple[List[Dict], List[Dict]]:
    """
    Calculate current performance for all holdings and detect triggered alerts.
    
    Args:
        current_portfolio: List of current holdings
        market_data: Current market data
    
    Returns:
        Tuple of (updated_portfolio, triggered_alerts)
        - updated_portfolio: Portfolio with updated performance metrics
        - triggered_alerts: List of positions that hit stop-loss or target
    """
    if not current_portfolio:
        return [], []
    
    # Get current prices for all holdings
    tickers = [h['ticker'] for h in current_portfolio if h.get('ticker')]
    current_prices = get_current_prices(tickers)
    
    # Log warning if many prices are missing
    missing_prices = [t for t in tickers if t not in current_prices]
    if missing_prices:
        print(f"  Warning: Could not fetch prices for {len(missing_prices)} tickers: {missing_prices[:5]}...")
    
    updated_portfolio = []
    triggered_alerts = []
    
    for holding in current_portfolio:
        ticker = holding.get('ticker')
        if not ticker:
            continue
            
        entry_price = holding.get('recommended_price', 0)
        current_price = current_prices.get(ticker)
        
        # If we couldn't get current price, don't just use entry price (that gives fake 0% P&L)
        # Instead, try to indicate the data is stale
        if current_price is None or current_price <= 0:
            print(f"  Warning: No current price for {ticker}, using entry price ${entry_price}")
            current_price = entry_price
            price_stale = True
        else:
            price_stale = False
        
        # Calculate gain/loss
        if entry_price > 0 and current_price > 0:
            gain_loss_pct = ((current_price / entry_price) - 1) * 100
        else:
            gain_loss_pct = 0
        
        # Check stop-loss and target
        stop_loss = holding.get('stop_loss') or 0
        price_target = holding.get('price_target') or 0
        
        status = holding.get('status', 'HOLD')
        alert_type = None
        
        if not price_stale:  # Only update status if we have real prices
            if stop_loss and current_price <= stop_loss:
                status = 'STOP_LOSS_HIT'
                alert_type = 'stop_loss'
            elif price_target and current_price >= price_target:
                status = 'TARGET_REACHED'
                alert_type = 'target'
        
        updated_holding = {
            **holding,
            'current_price': round(current_price, 2),
            'gain_loss_pct': round(gain_loss_pct, 2),
            'status': status,
            'price_stale': price_stale,
            'last_reviewed': datetime.now().strftime('%Y-%m-%d')
        }
        updated_portfolio.append(updated_holding)
        
        # Track triggered alerts
        if alert_type:
            triggered_alerts.append({
                'ticker': ticker,
                'alert_type': alert_type,
                'entry_price': entry_price,
                'current_price': round(current_price, 2),
                'trigger_price': stop_loss if alert_type == 'stop_loss' else price_target,
                'gain_loss_pct': round(gain_loss_pct, 2),
                'allocation_pct': holding.get('allocation_pct', 0)
            })
    
    # Log summary
    prices_fetched = len(tickers) - len(missing_prices)
    print(f"  Performance calculated: {prices_fetched}/{len(tickers)} prices fetched successfully")
    
    if triggered_alerts:
        print(f"  ⚠️  {len(triggered_alerts)} ALERTS TRIGGERED:")
        for alert in triggered_alerts:
            if alert['alert_type'] == 'stop_loss':
                print(f"    🔴 {alert['ticker']}: STOP-LOSS HIT @ ${alert['current_price']:.2f} (loss: {alert['gain_loss_pct']:.1f}%)")
            else:
                print(f"    🟢 {alert['ticker']}: TARGET REACHED @ ${alert['current_price']:.2f} (gain: {alert['gain_loss_pct']:.1f}%)")
    
    return updated_portfolio, triggered_alerts


# NOTE: calculate_portfolio_value() was removed - use get_actual_portfolio_value() instead
# NOTE: validate_allocations() was removed - use validate_allocation_rules() instead


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
    
    # Process sells - fetch current prices for sold stocks to calculate actual returns
    sells = analysis_result.get('sells', [])
    closed_this_month = []
    
    # Get current prices for all sold tickers
    sold_tickers = [s.get('ticker') for s in sells if s.get('ticker')]
    sold_prices = get_current_prices(sold_tickers) if sold_tickers else {}
    
    for sell in sells:
        ticker = sell.get('ticker')
        # Find the original position
        original = next((h for h in old_portfolio if h['ticker'] == ticker), None)
        if original:
            buy_price = original.get('recommended_price', 0)
            # Use current market price as sell price (the actual price we'd get today)
            sell_price = sold_prices.get(ticker) or sell.get('sell_price') or original.get('current_price') or buy_price
            
            # Calculate actual return from buy to sell price
            if buy_price > 0 and sell_price > 0:
                actual_return_pct = ((sell_price / buy_price) - 1) * 100
            else:
                actual_return_pct = 0
            
            closed_this_month.append({
                'ticker': ticker,
                'company_name': original.get('company_name', ''),
                'buy_date': original.get('recommended_date'),
                'buy_price': round(buy_price, 2),
                'sell_date': datetime.now().strftime('%Y-%m-%d'),
                'sell_price': round(sell_price, 2),
                'return_pct': round(actual_return_pct, 2),
                'hold_period_days': _calculate_hold_days(original.get('recommended_date')),
                'reason': sell.get('reason', ''),
                'lesson_learned': sell.get('lesson_learned', ''),
                'action_type': 'FULL_SELL'
            })
    
    # Build new portfolio from review + new recommendations
    new_portfolio = []
    sold_tickers = [s.get('ticker') for s in sells]
    reviewed_tickers = set()
    
    # Process portfolio review (holds, trims, adds)
    portfolio_review = analysis_result.get('portfolio_review', [])
    for review in portfolio_review:
        action = review.get('action', 'HOLD').upper()
        if action in ['HOLD', 'TRIM', 'ADD']:
            ticker = review.get('ticker')
            reviewed_tickers.add(ticker)
            original = next((h for h in old_portfolio if h['ticker'] == ticker), None)
            if original:
                old_alloc = original.get('allocation_pct', 0)
                new_alloc = review.get('new_allocation_pct', old_alloc)
                
                # Handle TRIM - record partial sale P&L
                if action == 'TRIM' and new_alloc < old_alloc:
                    trimmed_pct = old_alloc - new_alloc
                    buy_price = original.get('recommended_price', 0)
                    current_price = sold_prices.get(ticker) or original.get('current_price') or buy_price
                    trim_return_pct = ((current_price / buy_price) - 1) * 100 if buy_price > 0 else 0
                    
                    # Record the trimmed portion as a partial sale
                    closed_this_month.append({
                        'ticker': ticker,
                        'company_name': original.get('company_name', ''),
                        'buy_date': original.get('recommended_date'),
                        'buy_price': round(buy_price, 2),
                        'sell_date': datetime.now().strftime('%Y-%m-%d'),
                        'sell_price': round(current_price, 2),
                        'return_pct': round(trim_return_pct, 2),
                        'hold_period_days': _calculate_hold_days(original.get('recommended_date')),
                        'reason': f"TRIM: Reduced from {old_alloc:.1f}% to {new_alloc:.1f}%",
                        'allocation_trimmed_pct': round(trimmed_pct, 2),
                        'action_type': 'TRIM'
                    })
                
                # Handle ADD - update cost basis with weighted average
                # Support both dollar-based (add_amount) and percentage-based (new_allocation_pct)
                if action == 'ADD':
                    add_amount = review.get('add_amount', 0)  # Dollar amount to add
                    old_investment = original.get('investment_amount', 0)
                    old_price = original.get('recommended_price', 0)
                    current_price = sold_prices.get(ticker) or original.get('current_price') or old_price
                    
                    if add_amount > 0 and current_price > 0:
                        # Dollar-based ADD
                        new_investment = old_investment + add_amount
                        
                        # Calculate new weighted average cost basis
                        if old_investment > 0 and old_price > 0:
                            new_cost_basis = ((old_investment * old_price / old_price) + (add_amount)) / (old_investment / old_price + add_amount / current_price) if current_price > 0 else old_price
                            # Simpler: weighted average based on shares
                            old_shares = old_investment / old_price if old_price > 0 else 0
                            new_shares = add_amount / current_price if current_price > 0 else 0
                            total_shares = old_shares + new_shares
                            if total_shares > 0:
                                new_cost_basis = (old_investment + add_amount) / total_shares
                            else:
                                new_cost_basis = current_price
                        else:
                            new_cost_basis = current_price
                        
                        original['recommended_price'] = round(new_cost_basis, 2)
                        original['investment_amount'] = round(new_investment, 2)
                        original['add_history'] = original.get('add_history', []) + [{
                            'date': datetime.now().strftime('%Y-%m-%d'),
                            'added_amount': add_amount,
                            'price': round(current_price, 2)
                        }]
                    elif new_alloc > old_alloc:
                        # Percentage-based ADD (legacy support)
                        added_pct = new_alloc - old_alloc
                        
                        # Calculate new weighted average cost basis
                        if old_alloc > 0 and old_price > 0:
                            new_cost_basis = ((old_alloc * old_price) + (added_pct * current_price)) / new_alloc
                            original['recommended_price'] = round(new_cost_basis, 2)
                            original['add_history'] = original.get('add_history', []) + [{
                                'date': datetime.now().strftime('%Y-%m-%d'),
                                'added_pct': added_pct,
                                'price': round(current_price, 2)
                            }]
                
                updated = {**original}
                updated['allocation_pct'] = new_alloc
                updated['status'] = action
                updated['last_reviewed'] = datetime.now().strftime('%Y-%m-%d')
                new_portfolio.append(updated)
    
    # Update closed positions AFTER TRIM processing so partial sales are included
    history['closed_positions'].extend(closed_this_month)
    
    # Keep existing holdings that weren't explicitly reviewed or sold (default to HOLD)
    for holding in old_portfolio:
        ticker = holding.get('ticker')
        if ticker not in reviewed_tickers and ticker not in sold_tickers:
            updated = {**holding}
            updated['status'] = 'HOLD'  # Default to HOLD if not reviewed
            updated['last_reviewed'] = datetime.now().strftime('%Y-%m-%d')
            new_portfolio.append(updated)
    
    # Add new recommendations
    new_recs = analysis_result.get('new_recommendations', [])
    
    # Get total portfolio value for percentage calculations
    monthly_history = history.get('monthly_history', [])
    starting_capital = history['metadata'].get('starting_capital', 100000)
    if monthly_history:
        current_portfolio_value = monthly_history[-1].get('ending_value', starting_capital)
    else:
        current_portfolio_value = starting_capital
    
    for rec in new_recs:
        # Use the actual recommended_price if set, otherwise use current_market_price,
        # otherwise fall back to entry_zone midpoint (not the low!)
        entry_zone = rec.get('entry_zone', {})
        entry_mid = (entry_zone.get('low', 0) + entry_zone.get('high', 0)) / 2 if entry_zone else 0
        rec_price = rec.get('recommended_price') or rec.get('current_market_price') or entry_mid
        
        # Handle both dollar-based (investment_amount) and percentage-based (allocation_pct)
        investment_amount = rec.get('investment_amount', 0)
        allocation_pct = rec.get('allocation_pct', 0)
        
        # If investment_amount is provided, calculate allocation_pct from it
        if investment_amount > 0 and current_portfolio_value > 0:
            allocation_pct = (investment_amount / current_portfolio_value) * 100
        # If only allocation_pct is provided, calculate investment_amount
        elif allocation_pct > 0 and current_portfolio_value > 0:
            investment_amount = current_portfolio_value * (allocation_pct / 100)
        
        # Calculate shares based on investment amount and price
        shares = int(investment_amount / rec_price) if rec_price > 0 else 0
        
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
            'allocation_pct': round(allocation_pct, 2),
            'investment_amount': round(investment_amount, 2),
            'shares': shares,
            'recommended_date': datetime.now().strftime('%Y-%m-%d'),
            'recommended_price': round(rec_price, 2),  # Use actual current price, not entry zone low
            'entry_zone': entry_zone,
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
    
    # Add month to history - calculate return from OLD portfolio (what we held this month)
    sp500_return = market_data.get('indexes', {}).get('S&P 500', {}).get('returns', {}).get('1mo', 0)
    
    # Get cash info for proper return calculation
    cash_alloc = history.get('cash', {}).get('allocation_pct', 0)
    cash_yield = history.get('cash', {}).get('yield_pct', 5.0)  # Default 5% annual yield
    portfolio_return = _calculate_portfolio_return(old_portfolio, cash_alloc, cash_yield)
    
    # FIXED: Calculate ending value by compounding from previous month's ending value
    # Not from starting capital (which would ignore previous gains/losses)
    monthly_history = history.get('monthly_history', [])
    starting_capital = history['metadata'].get('starting_capital', 100000)
    
    if monthly_history:
        # Get the previous month's ending value as this month's starting value
        previous_ending = monthly_history[-1].get('ending_value', starting_capital)
    else:
        # First month - start from initial capital
        previous_ending = starting_capital
    
    # This month's ending value compounds from previous month
    current_ending = previous_ending * (1 + portfolio_return / 100)
    
    month_record = {
        'month': current_month,
        'starting_value': round(previous_ending, 2),
        'ending_value': round(current_ending, 2),
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


def _calculate_portfolio_return(portfolio: List[Dict], cash_allocation_pct: float = 0.0, cash_yield_pct: float = 0.0) -> float:
    """
    Calculate portfolio return based on recommended prices vs current prices.
    Properly accounts for cash position to avoid overstating returns.
    
    Args:
        portfolio: List of holdings with recommended_price and allocation_pct
        cash_allocation_pct: Percentage of portfolio in cash (0-100)
        cash_yield_pct: Annual yield on cash (e.g., 5.0 for 5%)
    
    Returns:
        Weighted portfolio return percentage (properly weighted against 100%)
    """
    if not portfolio:
        # If all cash, return cash yield (prorated for the period)
        # Assuming monthly reporting, divide annual yield by 12
        return (cash_yield_pct / 12) if cash_yield_pct > 0 else 0.0
    
    # Get current prices for all holdings
    tickers = [h['ticker'] for h in portfolio if h.get('ticker')]
    if not tickers:
        return 0.0
    
    current_prices = get_current_prices(tickers)
    
    total_weighted_return = 0.0
    total_stock_allocation = 0.0
    
    for holding in portfolio:
        ticker = holding.get('ticker')
        weight = holding.get('allocation_pct', 0)
        rec_price = holding.get('recommended_price', 0)
        
        if not ticker or weight <= 0 or rec_price <= 0:
            continue
        
        current_price = current_prices.get(ticker, rec_price)
        
        # Calculate return for this position
        position_return = ((current_price / rec_price) - 1) * 100
        
        # Add weighted contribution (weight is percentage of total portfolio)
        total_weighted_return += weight * position_return
        total_stock_allocation += weight
    
    # Calculate cash contribution (cash earns money market yield, prorated monthly)
    # Use provided cash_allocation_pct, or calculate from remaining allocation
    actual_cash_pct = cash_allocation_pct if cash_allocation_pct > 0 else (100 - total_stock_allocation)
    if actual_cash_pct > 0:
        monthly_cash_return = (cash_yield_pct / 12) if cash_yield_pct > 0 else 0.0
        total_weighted_return += actual_cash_pct * monthly_cash_return
    
    # Divide by 100 (total portfolio) not by total_stock_allocation
    # This properly accounts for cash drag on returns
    return total_weighted_return / 100.0


def _update_performance_summary(history: Dict) -> Dict:
    """Update cumulative performance summary using proper compound returns."""
    closed = history.get('closed_positions', [])
    monthly = history.get('monthly_history', [])
    
    # Use a small threshold for breakeven - trades within +/- 0.5% are considered breakeven
    # Only count as win if > 0.5%, only count as loss if < -0.5%
    breakeven_threshold = 0.5
    wins = [c for c in closed if c.get('return_pct', 0) > breakeven_threshold]
    losses = [c for c in closed if c.get('return_pct', 0) < -breakeven_threshold]
    # Note: trades between -0.5% and +0.5% are breakeven and don't count toward win/loss
    
    # FIXED: Use compound returns instead of simple sum
    # Compound formula: (1 + r1) * (1 + r2) * ... * (1 + rn) - 1
    portfolio_compound = 1.0
    sp500_compound = 1.0
    
    for m in monthly:
        portfolio_return = m.get('portfolio_return_pct', 0) / 100  # Convert to decimal
        sp500_return_month = m.get('sp500_return_pct', 0) / 100
        
        portfolio_compound *= (1 + portfolio_return)
        sp500_compound *= (1 + sp500_return_month)
    
    # Convert back to percentage
    total_return = (portfolio_compound - 1) * 100
    sp500_return = (sp500_compound - 1) * 100
    
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


def validate_allocation_rules(recommendations: Dict, history: Dict) -> Dict:
    """
    Validate that Claude's recommendations follow allocation rules.
    Auto-corrects issues and returns validation report.
    
    Args:
        recommendations: Claude's parsed recommendations
        history: Current portfolio history
        
    Returns:
        Dictionary with validation results and corrected recommendations
    """
    issues = []
    warnings = []
    corrections = []
    
    buys = recommendations.get('buys', [])
    sells = recommendations.get('sells', [])
    trims = recommendations.get('trims', [])
    adds = recommendations.get('adds', [])
    
    current_portfolio = history.get('current_portfolio', [])
    current_cash = history.get('cash', {}).get('allocation_pct', 0)
    
    # Rule 1: Total allocation must equal 100%
    total_alloc = sum(b.get('allocation_pct', 0) for b in buys)
    total_alloc += sum(h.get('allocation_pct', 0) for h in current_portfolio 
                       if h['ticker'] not in [s['ticker'] for s in sells])
    # Account for trims (reduce allocation)
    for trim in trims:
        ticker = trim['ticker']
        new_alloc = trim.get('new_allocation_pct', 0)
        for h in current_portfolio:
            if h['ticker'] == ticker:
                total_alloc -= h.get('allocation_pct', 0)
                total_alloc += new_alloc
    # Account for adds (increase allocation)
    for add in adds:
        ticker = add['ticker']
        add_amount = add.get('add_pct', 0)
        total_alloc += add_amount
    
    # Calculate cash after transactions
    cash_freed = sum(s.get('allocation_pct', 0) for s in sells)
    for trim in trims:
        ticker = trim['ticker']
        new_alloc = trim.get('new_allocation_pct', 0)
        for h in current_portfolio:
            if h['ticker'] == ticker:
                cash_freed += h.get('allocation_pct', 0) - new_alloc
    
    cash_used = sum(b.get('allocation_pct', 0) for b in buys)
    cash_used += sum(a.get('add_pct', 0) for a in adds)
    
    projected_cash = current_cash + cash_freed - cash_used
    
    if projected_cash < 0:
        issues.append(f"Insufficient cash: would need {abs(projected_cash):.1f}% more")
    
    # ONE RULE: No single position exceeds 15%
    max_position_pct = ALLOCATION_RULES.get('single_stock_max', 0.15) * 100
    for buy in buys:
        if buy.get('allocation_pct', 0) > max_position_pct:
            issues.append(f"Position {buy['ticker']} exceeds {max_position_pct:.0f}% max ({buy['allocation_pct']}%)")
            # Auto-correct
            old_alloc = buy['allocation_pct']
            buy['allocation_pct'] = max_position_pct
            corrections.append(f"Reduced {buy['ticker']} from {old_alloc}% to {max_position_pct:.0f}%")
    
    # Helpful warnings (not enforced, just informational)
    existing_tickers = {h['ticker'] for h in current_portfolio}
    for buy in buys:
        if buy['ticker'] in existing_tickers and buy['ticker'] not in [a['ticker'] for a in adds]:
            warnings.append(f"BUY {buy['ticker']} already in portfolio - should this be ADD?")
    
    for sell in sells:
        if sell['ticker'] not in existing_tickers:
            issues.append(f"SELL {sell['ticker']} not in current portfolio")
    
    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'warnings': warnings,
        'corrections': corrections,
        'corrected_recommendations': recommendations,
        'projected_cash': round(projected_cash, 2)
    }


def auto_generate_sells_from_alerts(triggered_alerts: List[Dict], 
                                    current_portfolio: List[Dict]) -> List[Dict]:
    """
    Auto-generate SELL recommendations for positions that hit stop-loss.
    
    Args:
        triggered_alerts: List of triggered stop-loss/target alerts
        current_portfolio: Current portfolio holdings
        
    Returns:
        List of sell recommendations
    """
    auto_sells = []
    
    for alert in triggered_alerts:
        if alert['alert_type'] == 'stop_loss':
            # Find the holding
            holding = next((h for h in current_portfolio if h['ticker'] == alert['ticker']), None)
            if holding:
                auto_sells.append({
                    'ticker': alert['ticker'],
                    'allocation_pct': holding.get('allocation_pct', 0),
                    'reason': f"STOP-LOSS TRIGGERED at ${alert['current_price']:.2f} (loss: {alert['gain_loss_pct']:.1f}%)",
                    'auto_generated': True
                })
                print(f"  🔴 Auto-generated SELL for {alert['ticker']} (stop-loss hit)")
    
    return auto_sells


def get_actual_portfolio_value(history: Dict, starting_capital: float = 100000) -> Dict:
    """
    Calculate the actual portfolio value based on current prices.
    Accounts for compounded returns over time.
    
    Args:
        history: Portfolio history dictionary
        starting_capital: Initial capital
        
    Returns:
        Dictionary with actual value metrics
    """
    # Calculate compounded return from closed positions
    closed_positions = history.get('closed_positions', [])
    
    # Track capital through time
    running_capital = starting_capital
    
    # Group closed positions by month to properly compound
    monthly_returns = defaultdict(list)
    for pos in closed_positions:
        sell_date = pos.get('sell_date', pos.get('closed_date', ''))
        if sell_date:
            month = sell_date[:7]  # YYYY-MM
            return_pct = pos.get('return_pct', 0)
            allocation = pos.get('allocation_pct', 0)
            # Weighted return contribution
            contribution = (return_pct * allocation) / 100
            monthly_returns[month].append(contribution)
    
    # Apply compounded returns
    for month in sorted(monthly_returns.keys()):
        month_return = sum(monthly_returns[month])
        running_capital *= (1 + month_return / 100)
    
    # Calculate current unrealized value
    current_portfolio = history.get('current_portfolio', [])
    unrealized_value = 0
    
    for holding in current_portfolio:
        allocation = holding.get('allocation_pct', 0)
        gain_loss = holding.get('gain_loss_pct', 0)
        
        # Value of this position based on current capital
        position_value = (running_capital * allocation / 100) * (1 + gain_loss / 100)
        unrealized_value += position_value
    
    # Cash portion
    cash_allocation = history.get('cash', {}).get('allocation_pct', 0)
    cash_value = running_capital * cash_allocation / 100
    
    total_value = unrealized_value + cash_value
    total_return_pct = ((total_value / starting_capital) - 1) * 100
    
    return {
        'starting_capital': starting_capital,
        'current_value': round(total_value, 2),
        'realized_gains': round(running_capital - starting_capital, 2),
        'unrealized_value': round(unrealized_value, 2),
        'cash_value': round(cash_value, 2),
        'total_return_pct': round(total_return_pct, 2)
    }

