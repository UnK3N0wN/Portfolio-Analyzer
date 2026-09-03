from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch
 
import pandas as pd
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
 
from portfolio.models import Holding, Portfolio, PortfolioSnapshot, PriceAlert, WatchlistItem
from portfolio.tasks import (
    _safe_close, check_all_price_alerts, create_daily_snapshots,
    update_all_holding_prices, update_all_watchlist_prices,
)
 
 
def fake_history(close_price):
    """Build a minimal DataFrame shaped like yfinance's .history() output."""
    return pd.DataFrame({'Close': [close_price]})
 
 
def empty_history():
    return pd.DataFrame({'Close': []})
 
 
class SafeCloseHelperTests(TestCase):
    """_safe_close is the shared NaN/Inf guard used by all three price tasks."""
 
    def test_normal_price_is_returned_rounded(self):
        self.assertEqual(_safe_close(fake_history(123.456789123)), round(123.456789123, 8))
 
    def test_empty_dataframe_returns_none(self):
        self.assertIsNone(_safe_close(empty_history()))
 
    def test_nan_close_returns_none(self):
        self.assertIsNone(_safe_close(fake_history(float('nan'))))
 
    def test_inf_close_returns_none(self):
        self.assertIsNone(_safe_close(fake_history(float('inf'))))
 
 
class UpdateAllHoldingPricesTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pw12345')
        self.portfolio = Portfolio.objects.create(user=self.user)
        self.holding = Holding.objects.create(
            portfolio=self.portfolio, symbol='AAPL', name='Apple Inc.',
            quantity=Decimal('10'), avg_price=Decimal('100'), current_price=Decimal('0'),
        )
 
    @patch('portfolio.tasks.yf.Ticker')
    def test_updates_price_on_success(self, mock_ticker):
        mock_ticker.return_value.history.return_value = fake_history(155.25)
        result = update_all_holding_prices()
        self.holding.refresh_from_db()
        self.assertEqual(float(self.holding.current_price), 155.25)
        self.assertEqual(result['updated'], 1)
        self.assertEqual(result['failed'], 0)
 
    @patch('portfolio.tasks.yf.Ticker')
    def test_nan_price_is_skipped_not_saved(self, mock_ticker):
        mock_ticker.return_value.history.return_value = fake_history(float('nan'))
        update_all_holding_prices()
        self.holding.refresh_from_db()
        # current_price must remain untouched, not become NaN
        self.assertEqual(float(self.holding.current_price), 0.0)
 
    @patch('portfolio.tasks.yf.Ticker')
    def test_exception_for_one_symbol_does_not_abort_the_rest(self, mock_ticker):
        second = Holding.objects.create(
            portfolio=self.portfolio, symbol='TSLA', name='Tesla Inc.',
            quantity=Decimal('2'), avg_price=Decimal('200'),
        )
 
        def side_effect(symbol):
            m = MagicMock()
            if symbol == 'AAPL':
                m.history.side_effect = Exception('network blip')
            else:
                m.history.return_value = fake_history(250.0)
            return m
        mock_ticker.side_effect = side_effect
 
        result = update_all_holding_prices()
        second.refresh_from_db()
        self.assertEqual(float(second.current_price), 250.0)
        self.assertEqual(result['failed'], 1)
        self.assertEqual(result['updated'], 1)
 
    @patch('portfolio.tasks.yf.Ticker')
    def test_empty_history_is_skipped(self, mock_ticker):
        mock_ticker.return_value.history.return_value = empty_history()
        result = update_all_holding_prices()
        self.assertEqual(result['updated'], 0)
 
 
class CheckAllPriceAlertsTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='bob', password='pw12345')
 
    @patch('portfolio.tasks.yf.Ticker')
    def test_alert_triggers_when_price_crosses_target(self, mock_ticker):
        alert = PriceAlert.objects.create(
            user=self.user, symbol='AAPL', name='Apple Inc.',
            alert_type='above', target_price=Decimal('200'), current_price=Decimal('190'),
        )
        mock_ticker.return_value.history.return_value = fake_history(205.0)
        result = check_all_price_alerts()
        alert.refresh_from_db()
        self.assertTrue(alert.is_triggered)
        self.assertIsNotNone(alert.triggered_at)
        self.assertEqual(result['triggered'], 1)
 
    @patch('portfolio.tasks.yf.Ticker')
    def test_alert_not_triggered_stays_untriggered(self, mock_ticker):
        alert = PriceAlert.objects.create(
            user=self.user, symbol='AAPL', name='Apple Inc.',
            alert_type='above', target_price=Decimal('200'), current_price=Decimal('190'),
        )
        mock_ticker.return_value.history.return_value = fake_history(195.0)
        result = check_all_price_alerts()
        alert.refresh_from_db()
        self.assertFalse(alert.is_triggered)
        self.assertEqual(result['triggered'], 0)
 
    @patch('portfolio.tasks.yf.Ticker')
    def test_already_triggered_alerts_are_excluded_from_query(self, mock_ticker):
        PriceAlert.objects.create(
            user=self.user, symbol='AAPL', name='Apple Inc.',
            alert_type='above', target_price=Decimal('200'), current_price=Decimal('999'),
            is_triggered=True,
        )
        mock_ticker.return_value.history.return_value = fake_history(999.0)
        check_all_price_alerts()
        # Ticker should never even be called for an already-triggered alert
        mock_ticker.assert_not_called()
 
    @patch('portfolio.tasks.yf.Ticker')
    def test_inactive_alerts_are_excluded_from_query(self, mock_ticker):
        PriceAlert.objects.create(
            user=self.user, symbol='AAPL', name='Apple Inc.',
            alert_type='above', target_price=Decimal('200'), current_price=Decimal('999'),
            is_active=False,
        )
        check_all_price_alerts()
        mock_ticker.assert_not_called()
 
    @patch('portfolio.tasks.yf.Ticker')
    def test_nan_price_does_not_falsely_trigger_alert(self, mock_ticker):
        alert = PriceAlert.objects.create(
            user=self.user, symbol='AAPL', name='Apple Inc.',
            alert_type='above', target_price=Decimal('200'), current_price=Decimal('190'),
        )
        mock_ticker.return_value.history.return_value = fake_history(float('nan'))
        check_all_price_alerts()
        alert.refresh_from_db()
        self.assertFalse(alert.is_triggered)
 
 
class UpdateAllWatchlistPricesTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='carol', password='pw12345')
 
    @patch('portfolio.tasks.yf.Ticker')
    def test_updates_watchlist_price(self, mock_ticker):
        item = WatchlistItem.objects.create(user=self.user, symbol='TSLA', name='Tesla Inc.')
        mock_ticker.return_value.history.return_value = fake_history(310.5)
        result = update_all_watchlist_prices()
        item.refresh_from_db()
        self.assertEqual(float(item.current_price), 310.5)
        self.assertEqual(result['updated'], 1)
 
 
class CreateDailySnapshotsTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='dave', password='pw12345')
        self.portfolio = Portfolio.objects.create(user=self.user)
        Holding.objects.create(
            portfolio=self.portfolio, symbol='AAPL', name='Apple Inc.',
            quantity=Decimal('10'), avg_price=Decimal('100'), current_price=Decimal('120'),
        )
 
    def test_creates_one_snapshot_per_portfolio(self):
        result = create_daily_snapshots()
        self.assertEqual(result['snapshotted'], 1)
        snap = PortfolioSnapshot.objects.get(portfolio=self.portfolio)
        self.assertEqual(float(snap.total_value), 1200.0)
        self.assertEqual(float(snap.total_invested), 1000.0)
        self.assertEqual(float(snap.profit_loss), 200.0)
 
    def test_running_twice_same_day_upserts_not_duplicates(self):
        create_daily_snapshots()
        create_daily_snapshots()
        self.assertEqual(PortfolioSnapshot.objects.filter(portfolio=self.portfolio).count(), 1)
 
    def test_covers_every_portfolio_independently(self):
        other_user = User.objects.create_user(username='erin', password='pw12345')
        Portfolio.objects.create(user=other_user)
        result = create_daily_snapshots()
        self.assertEqual(result['snapshotted'], 2)
        self.assertEqual(PortfolioSnapshot.objects.count(), 2)