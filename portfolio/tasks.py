import logging
import math

import yfinance as yf
from celery import shared_task
from django.utils import timezone

from .models import Holding, Portfolio, PortfolioSnapshot, PriceAlert, WatchlistItem

logger = logging.getLogger(__name__)

def _safe_close(data):
    if data.empty:
        return None
    price = float(data['Close'].iloc[-1])
    if math.isnan(price) or math.isinf(price):
        return None
    return round(price, 8)

@shared_task
def update_all_holding_prices():
    """Refresh Holding.current_price for every holding, across all users."""
    updated, failed = 0, 0
    for holding in Holding.objects.select_related('portfolio').all():
        try:
            data = yf.Ticker(holding.symbol).history(period='1d')
            if not data.empty:
                holding.current_price = round(float(data['Close'].iloc[-1]), 8)
                holding.save(update_fields=['current_price', 'last_updated'])
                updated += 1
        except Exception:
            failed += 1
            logger.warning('Price update failed for %s', holding.symbol, exc_info=True)
    logger.info('update_all_holding_prices: %s updated, %s failed', updated, failed)
    return {'updated': updated, 'failed': failed}


@shared_task
def check_all_price_alerts():
    """Refresh alert prices and flip is_triggered for any that hit target."""
    triggered, failed = 0, 0
    alerts = PriceAlert.objects.filter(is_active=True, is_triggered=False)
    for alert in alerts:
        try:
            data = yf.Ticker(alert.symbol).history(period='1d')
            if data.empty:
                continue
            alert.current_price = round(float(data['Close'].iloc[-1]), 8)
            if alert.check_trigger():
                alert.is_triggered = True
                alert.triggered_at = timezone.now()
                alert.save(update_fields=['current_price', 'is_triggered', 'triggered_at'])
                triggered += 1
                # TODO: hook up email/push notification here — this is the
                # natural place for it now that it's decoupled from a request.
            else:
                alert.save(update_fields=['current_price'])
        except Exception:
            failed += 1
            logger.warning('Alert check failed for %s', alert.symbol, exc_info=True)
    logger.info('check_all_price_alerts: %s triggered, %s failed', triggered, failed)
    return {'triggered': triggered, 'failed': failed}


@shared_task
def update_all_watchlist_prices():
    """Refresh WatchlistItem.current_price for every user's watchlist."""
    updated, failed = 0, 0
    for item in WatchlistItem.objects.all():
        try:
            data = yf.Ticker(item.symbol).history(period='1d')
            if not data.empty:
                item.current_price = round(float(data['Close'].iloc[-1]), 8)
                item.save(update_fields=['current_price'])
                updated += 1
        except Exception:
            failed += 1
            logger.warning('Watchlist price update failed for %s', item.symbol, exc_info=True)
    logger.info('update_all_watchlist_prices: %s updated, %s failed', updated, failed)
    return {'updated': updated, 'failed': failed}


@shared_task
def create_daily_snapshots():
    """One PortfolioSnapshot per portfolio per day, using already-fresh prices."""
    today = timezone.localdate()
    count = 0
    for portfolio in Portfolio.objects.all():
        PortfolioSnapshot.objects.update_or_create(
            portfolio=portfolio, date=today,
            defaults={
                'total_value':    round(portfolio.total_value(), 2),
                'total_invested': round(portfolio.total_invested(), 2),
                'profit_loss':    round(portfolio.total_profit_loss(), 2),
            }
        )
        count += 1
    logger.info('create_daily_snapshots: %s portfolios snapshotted', count)
    return {'snapshotted': count}