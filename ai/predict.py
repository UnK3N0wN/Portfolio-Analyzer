"""
ai/predict.py
Simple stock price prediction using scikit-learn linear regression.
Used to predict short-term price trends from historical data.
"""

import numpy as np

try:
    from sklearn.linear_model import LinearRegression
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


def predict_price_trend(price_history, days_ahead=7):
    """
    Predict price trend using linear regression.

    Args:
        price_history: list of closing prices (oldest to newest)
        days_ahead:    how many days to predict ahead

    Returns:
        dict with prediction results
    """
    if not SKLEARN_AVAILABLE:
        return {'error': 'scikit-learn not installed. Run: pip install scikit-learn'}

    if len(price_history) < 5:
        return {'error': 'Not enough price history for prediction (need at least 5 data points)'}

    prices = np.array(price_history).reshape(-1, 1)
    days   = np.arange(len(prices)).reshape(-1, 1)

    model = LinearRegression()
    model.fit(days, prices)

    # Predict future days
    future_days  = np.arange(len(prices), len(prices) + days_ahead).reshape(-1, 1)
    future_prices = model.predict(future_days).flatten()

    current_price   = float(price_history[-1])
    predicted_price = float(future_prices[-1])
    change          = predicted_price - current_price
    change_pct      = (change / current_price) * 100 if current_price else 0

    return {
        'current_price':   round(current_price, 2),
        'predicted_price': round(predicted_price, 2),
        'change':          round(change, 2),
        'change_percent':  round(change_pct, 2),
        'trend':           'upward' if change > 0 else 'downward',
        'future_prices':   [round(float(p), 2) for p in future_prices],
        'confidence':      'low',   # Linear regression is simple — always flag low confidence
    }


def get_portfolio_trend(holdings):
    """
    Get overall portfolio trend based on holdings performance.

    Args:
        holdings: queryset of Holding objects

    Returns:
        dict with portfolio trend summary
    """
    if not holdings:
        return {'error': 'No holdings to analyze'}

    gainers = [h for h in holdings if h.profit_loss_percent() > 0]
    losers  = [h for h in holdings if h.profit_loss_percent() < 0]

    total_invested = sum(h.total_invested() for h in holdings)
    total_value    = sum(h.current_value() for h in holdings)
    total_pl       = total_value - total_invested
    total_pl_pct   = (total_pl / total_invested * 100) if total_invested else 0

    return {
        'total_invested':  round(total_invested, 2),
        'total_value':     round(total_value, 2),
        'total_pl':        round(total_pl, 2),
        'total_pl_pct':    round(total_pl_pct, 2),
        'gainers_count':   len(gainers),
        'losers_count':    len(losers),
        'overall_trend':   'positive' if total_pl > 0 else 'negative',
        'best_performer':  max(holdings, key=lambda h: h.profit_loss_percent()).symbol if holdings else None,
        'worst_performer': min(holdings, key=lambda h: h.profit_loss_percent()).symbol if holdings else None,
    }