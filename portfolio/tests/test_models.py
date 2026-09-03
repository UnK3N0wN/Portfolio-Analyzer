from datetime import date, timedelta
from decimal import Decimal
 
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase
 
from portfolio.models import (
    Holding, Portfolio, PortfolioSnapshot, PriceAlert, Transaction, WatchlistItem,
)
 
 
class PortfolioModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pw12345')
        self.portfolio = Portfolio.objects.create(user=self.user)
 
    def test_str_representation(self):
        self.assertEqual(str(self.portfolio), 'alice - My Portfolio')
 
    def test_totals_are_zero_with_no_holdings(self):
        self.assertEqual(self.portfolio.total_value(), 0)
        self.assertEqual(self.portfolio.total_invested(), 0)
        self.assertEqual(self.portfolio.total_profit_loss(), 0)
        self.assertEqual(self.portfolio.profit_loss_percent(), 0)
 
    def test_profit_loss_percent_does_not_divide_by_zero(self):
        # invested == 0 must short-circuit rather than raise ZeroDivisionError
        self.assertEqual(self.portfolio.profit_loss_percent(), 0)
 
    def test_totals_aggregate_across_multiple_holdings(self):
        Holding.objects.create(
            portfolio=self.portfolio, symbol='AAPL', name='Apple Inc.',
            quantity=Decimal('10'), avg_price=Decimal('100'), current_price=Decimal('120'),
        )
        Holding.objects.create(
            portfolio=self.portfolio, symbol='TSLA', name='Tesla Inc.',
            quantity=Decimal('2'), avg_price=Decimal('300'), current_price=Decimal('250'),
        )
        # AAPL: invested 1000, value 1200 | TSLA: invested 600, value 500
        self.assertAlmostEqual(self.portfolio.total_invested(), 1600)
        self.assertAlmostEqual(self.portfolio.total_value(), 1700)
        self.assertAlmostEqual(self.portfolio.total_profit_loss(), 100)
        self.assertAlmostEqual(self.portfolio.profit_loss_percent(), 6.25)
 
    def test_one_portfolio_per_user(self):
        # OneToOneField(user) must reject a second Portfolio for the same user
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Portfolio.objects.create(user=self.user)
 
 
class HoldingModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='bob', password='pw12345')
        self.portfolio = Portfolio.objects.create(user=self.user)
 
    def test_str_representation(self):
        h = Holding.objects.create(
            portfolio=self.portfolio, symbol='AAPL', name='Apple Inc.',
            quantity=Decimal('5'), avg_price=Decimal('100'),
        )
        self.assertEqual(str(h), 'AAPL - 5')
 
    def test_total_invested(self):
        h = Holding.objects.create(
            portfolio=self.portfolio, symbol='AAPL', name='Apple Inc.',
            quantity=Decimal('10'), avg_price=Decimal('150.50'),
        )
        self.assertAlmostEqual(h.total_invested(), 1505.0)
 
    def test_current_value(self):
        h = Holding.objects.create(
            portfolio=self.portfolio, symbol='AAPL', name='Apple Inc.',
            quantity=Decimal('10'), avg_price=Decimal('100'), current_price=Decimal('130'),
        )
        self.assertAlmostEqual(h.current_value(), 1300.0)
 
    def test_profit_loss_positive(self):
        h = Holding.objects.create(
            portfolio=self.portfolio, symbol='AAPL', name='Apple Inc.',
            quantity=Decimal('10'), avg_price=Decimal('100'), current_price=Decimal('130'),
        )
        self.assertAlmostEqual(h.profit_loss(), 300.0)
        self.assertAlmostEqual(h.profit_loss_percent(), 30.0)
 
    def test_profit_loss_negative(self):
        h = Holding.objects.create(
            portfolio=self.portfolio, symbol='TSLA', name='Tesla Inc.',
            quantity=Decimal('4'), avg_price=Decimal('300'), current_price=Decimal('250'),
        )
        self.assertAlmostEqual(h.profit_loss(), -200.0)
        self.assertAlmostEqual(h.profit_loss_percent(), -16.6666666, places=3)
 
    def test_profit_loss_percent_zero_avg_price_does_not_crash(self):
        h = Holding.objects.create(
            portfolio=self.portfolio, symbol='FREE', name='Free Asset',
            quantity=Decimal('1'), avg_price=Decimal('0'), current_price=Decimal('10'),
        )
        self.assertEqual(h.profit_loss_percent(), 0)
 
    def test_symbol_unique_per_portfolio(self):
        Holding.objects.create(
            portfolio=self.portfolio, symbol='AAPL', name='Apple Inc.',
            quantity=Decimal('1'), avg_price=Decimal('100'),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Holding.objects.create(
                    portfolio=self.portfolio, symbol='AAPL', name='Apple Inc. duplicate',
                    quantity=Decimal('1'), avg_price=Decimal('100'),
                )
 
    def test_same_symbol_allowed_across_different_portfolios(self):
        other_user = User.objects.create_user(username='carol', password='pw12345')
        other_portfolio = Portfolio.objects.create(user=other_user)
        Holding.objects.create(
            portfolio=self.portfolio, symbol='AAPL', name='Apple Inc.',
            quantity=Decimal('1'), avg_price=Decimal('100'),
        )
        # Should NOT raise — unique_together is scoped to (portfolio, symbol)
        Holding.objects.create(
            portfolio=other_portfolio, symbol='AAPL', name='Apple Inc.',
            quantity=Decimal('1'), avg_price=Decimal('100'),
        )
        self.assertEqual(Holding.objects.filter(symbol='AAPL').count(), 2)
 
 
class TransactionModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='dave', password='pw12345')
        self.portfolio = Portfolio.objects.create(user=self.user)
 
    def test_str_representation(self):
        t = Transaction.objects.create(
            portfolio=self.portfolio, symbol='AAPL', name='Apple Inc.',
            transaction_type='buy', quantity=Decimal('5'), price=Decimal('150'),
            total_amount=Decimal('750'),
        )
        self.assertEqual(str(t), 'BUY 5 AAPL @ 150')
 
    def test_default_ordering_is_most_recent_first(self):
        t1 = Transaction.objects.create(
            portfolio=self.portfolio, symbol='AAPL', name='Apple Inc.',
            transaction_type='buy', quantity=Decimal('1'), price=Decimal('100'), total_amount=Decimal('100'),
        )
        t2 = Transaction.objects.create(
            portfolio=self.portfolio, symbol='TSLA', name='Tesla Inc.',
            transaction_type='buy', quantity=Decimal('1'), price=Decimal('200'), total_amount=Decimal('200'),
        )
        ordered = list(self.portfolio.transactions.all())
        self.assertEqual(ordered, [t2, t1])
 
 
class PriceAlertModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='erin', password='pw12345')
 
    def test_str_representation(self):
        a = PriceAlert.objects.create(
            user=self.user, symbol='AAPL', name='Apple Inc.',
            alert_type='above', target_price=Decimal('200'),
        )
        self.assertEqual(str(a), 'AAPL above $200')
 
    def test_trigger_fires_when_price_crosses_above_target(self):
        a = PriceAlert.objects.create(
            user=self.user, symbol='AAPL', name='Apple Inc.',
            alert_type='above', target_price=Decimal('200'), current_price=Decimal('205'),
        )
        self.assertTrue(a.check_trigger())
 
    def test_trigger_does_not_fire_below_target_for_above_type(self):
        a = PriceAlert.objects.create(
            user=self.user, symbol='AAPL', name='Apple Inc.',
            alert_type='above', target_price=Decimal('200'), current_price=Decimal('195'),
        )
        self.assertFalse(a.check_trigger())
 
    def test_trigger_fires_when_price_crosses_below_target(self):
        a = PriceAlert.objects.create(
            user=self.user, symbol='TSLA', name='Tesla Inc.',
            alert_type='below', target_price=Decimal('200'), current_price=Decimal('195'),
        )
        self.assertTrue(a.check_trigger())
 
    def test_trigger_fires_exactly_at_target_boundary(self):
        # check_trigger uses >= / <=, so hitting the target exactly should fire
        a = PriceAlert.objects.create(
            user=self.user, symbol='TSLA', name='Tesla Inc.',
            alert_type='below', target_price=Decimal('200'), current_price=Decimal('200'),
        )
        self.assertTrue(a.check_trigger())
 
    def test_inactive_alert_never_triggers(self):
        a = PriceAlert.objects.create(
            user=self.user, symbol='AAPL', name='Apple Inc.',
            alert_type='above', target_price=Decimal('200'), current_price=Decimal('999'),
            is_active=False,
        )
        self.assertFalse(a.check_trigger())
 
    def test_already_triggered_alert_does_not_retrigger(self):
        a = PriceAlert.objects.create(
            user=self.user, symbol='AAPL', name='Apple Inc.',
            alert_type='above', target_price=Decimal('200'), current_price=Decimal('999'),
            is_triggered=True,
        )
        self.assertFalse(a.check_trigger())
 
    def test_default_ordering_is_most_recent_first(self):
        a1 = PriceAlert.objects.create(user=self.user, symbol='AAPL', name='Apple', alert_type='above', target_price=Decimal('1'))
        a2 = PriceAlert.objects.create(user=self.user, symbol='TSLA', name='Tesla', alert_type='above', target_price=Decimal('1'))
        self.assertEqual(list(self.user.price_alerts.all()), [a2, a1])
 
 
class WatchlistItemModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='frank', password='pw12345')
 
    def test_str_representation(self):
        item = WatchlistItem.objects.create(user=self.user, symbol='AAPL', name='Apple Inc.')
        self.assertEqual(str(item), 'frank watching AAPL')
 
    def test_symbol_unique_per_user(self):
        WatchlistItem.objects.create(user=self.user, symbol='AAPL', name='Apple Inc.')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                WatchlistItem.objects.create(user=self.user, symbol='AAPL', name='Apple Inc. dup')
 
    def test_same_symbol_allowed_for_different_users(self):
        other = User.objects.create_user(username='grace', password='pw12345')
        WatchlistItem.objects.create(user=self.user, symbol='AAPL', name='Apple Inc.')
        # Should NOT raise
        WatchlistItem.objects.create(user=other, symbol='AAPL', name='Apple Inc.')
        self.assertEqual(WatchlistItem.objects.filter(symbol='AAPL').count(), 2)
 
 
class PortfolioSnapshotModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='henry', password='pw12345')
        self.portfolio = Portfolio.objects.create(user=self.user)
 
    def test_one_snapshot_per_portfolio_per_day(self):
        today = date.today()
        PortfolioSnapshot.objects.create(portfolio=self.portfolio, date=today, total_value=Decimal('100'))
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PortfolioSnapshot.objects.create(portfolio=self.portfolio, date=today, total_value=Decimal('200'))
 
    def test_different_days_allowed(self):
        today = date.today()
        yesterday = today - timedelta(days=1)
        PortfolioSnapshot.objects.create(portfolio=self.portfolio, date=yesterday, total_value=Decimal('100'))
        PortfolioSnapshot.objects.create(portfolio=self.portfolio, date=today, total_value=Decimal('150'))
        self.assertEqual(self.portfolio.snapshots.count(), 2)
 
    def test_ordering_is_chronological(self):
        today = date.today()
        yesterday = today - timedelta(days=1)
        s_today = PortfolioSnapshot.objects.create(portfolio=self.portfolio, date=today, total_value=Decimal('150'))
        s_yesterday = PortfolioSnapshot.objects.create(portfolio=self.portfolio, date=yesterday, total_value=Decimal('100'))
        self.assertEqual(list(self.portfolio.snapshots.all()), [s_yesterday, s_today])