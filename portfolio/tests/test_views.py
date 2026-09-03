from decimal import Decimal
from unittest.mock import patch
 
import pandas as pd
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
 
from portfolio.models import Holding, Portfolio, PriceAlert, WatchlistItem
 
 
def fake_history(close_price):
    return pd.DataFrame({'Close': [close_price]})
 
 
class AuthRequiredTests(TestCase):
    """Every portfolio view should redirect anonymous users to login."""
 
    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('portfolio:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
 
    def test_portfolio_view_requires_login(self):
        response = self.client.get(reverse('portfolio:portfolio'))
        self.assertEqual(response.status_code, 302)
 
    def test_watchlist_requires_login(self):
        response = self.client.get(reverse('portfolio:watchlist'))
        self.assertEqual(response.status_code, 302)
 
    def test_ai_chat_requires_login(self):
        response = self.client.get(reverse('portfolio:ai_chat'))
        self.assertEqual(response.status_code, 302)
 
 
class DashboardViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pw12345')
        self.client.login(username='alice', password='pw12345')
        self.portfolio = Portfolio.objects.create(user=self.user)
 
    def test_dashboard_loads_for_logged_in_user(self):
        response = self.client.get(reverse('portfolio:dashboard'))
        self.assertEqual(response.status_code, 200)
 
    def test_dashboard_creates_a_portfolio_if_none_exists(self):
        # get_or_create_portfolio should silently create one, not 500
        new_user = User.objects.create_user(username='newbie', password='pw12345')
        self.client.login(username='newbie', password='pw12345')
        response = self.client.get(reverse('portfolio:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Portfolio.objects.filter(user=new_user).exists())
 
    def test_dashboard_shows_correct_totals(self):
        Holding.objects.create(
            portfolio=self.portfolio, symbol='AAPL', name='Apple Inc.',
            quantity=Decimal('10'), avg_price=Decimal('100'), current_price=Decimal('120'),
        )
        response = self.client.get(reverse('portfolio:dashboard'))
        self.assertEqual(response.context['total_value'], 1200.0)
        self.assertEqual(response.context['total_invested'], 1000.0)
 
    def test_dashboard_upserts_todays_snapshot(self):
        from portfolio.models import PortfolioSnapshot
        self.assertEqual(PortfolioSnapshot.objects.count(), 0)
        self.client.get(reverse('portfolio:dashboard'))
        self.assertEqual(PortfolioSnapshot.objects.filter(portfolio=self.portfolio).count(), 1)
 
    def test_recently_triggered_alert_shows_a_message(self):
        from django.utils import timezone
        PriceAlert.objects.create(
            user=self.user, symbol='AAPL', name='Apple Inc.', alert_type='above',
            target_price=Decimal('100'), is_triggered=True, triggered_at=timezone.now(),
        )
        response = self.client.get(reverse('portfolio:dashboard'))
        messages_list = list(response.context['messages'])
        self.assertTrue(any('AAPL' in str(m) for m in messages_list))
 
 
class AddStockViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='bob', password='pw12345')
        self.client.login(username='bob', password='pw12345')
        self.portfolio = Portfolio.objects.create(user=self.user)
 
    @patch('portfolio.views.yf.Ticker')
    def test_add_new_holding_success(self, mock_ticker):
        mock_ticker.return_value.history.return_value = fake_history(150.0)
        response = self.client.post(reverse('portfolio:add_stock'), {
            'symbol': 'AAPL', 'name': 'Apple Inc.', 'asset_type': 'stock',
            'quantity': '10', 'price': '145.00', 'notes': '',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Holding.objects.filter(portfolio=self.portfolio, symbol='AAPL').exists())
 
    @patch('portfolio.views.yf.Ticker')
    def test_duplicate_symbol_is_rejected(self, mock_ticker):
        Holding.objects.create(
            portfolio=self.portfolio, symbol='AAPL', name='Apple Inc.',
            quantity=Decimal('1'), avg_price=Decimal('100'),
        )
        mock_ticker.return_value.history.return_value = fake_history(150.0)
        self.client.post(reverse('portfolio:add_stock'), {
            'symbol': 'AAPL', 'name': 'Apple Inc.', 'asset_type': 'stock',
            'quantity': '5', 'price': '150.00', 'notes': '',
        })
        # Should NOT create a second AAPL holding for this portfolio
        self.assertEqual(Holding.objects.filter(portfolio=self.portfolio, symbol='AAPL').count(), 1)
 
    def test_symbol_is_uppercased_and_stripped(self):
        with patch('portfolio.views.yf.Ticker') as mock_ticker:
            mock_ticker.return_value.history.return_value = fake_history(50.0)
            self.client.post(reverse('portfolio:add_stock'), {
                'symbol': '  aapl  ', 'name': 'Apple Inc.', 'asset_type': 'stock',
                'quantity': '1', 'price': '50.00', 'notes': '',
            })
        self.assertTrue(Holding.objects.filter(portfolio=self.portfolio, symbol='AAPL').exists())
 
    def test_tenth_holding_allowed_eleventh_blocked(self):
        for i in range(10):
            Holding.objects.create(
                portfolio=self.portfolio, symbol=f'SYM{i}', name=f'Symbol {i}',
                quantity=Decimal('1'), avg_price=Decimal('10'),
            )
        response = self.client.get(reverse('portfolio:add_stock'))
        # Redirected away instead of showing the add form, since limit is reached
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Holding.objects.filter(portfolio=self.portfolio).count(), 10)
 
 
class BuyMoreViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='carol', password='pw12345')
        self.client.login(username='carol', password='pw12345')
        self.portfolio = Portfolio.objects.create(user=self.user)
        self.holding = Holding.objects.create(
            portfolio=self.portfolio, symbol='AAPL', name='Apple Inc.',
            quantity=Decimal('10'), avg_price=Decimal('100'), current_price=Decimal('100'),
        )
 
    @patch('portfolio.views.yf.Ticker')
    def test_buying_more_recalculates_weighted_average_price(self, mock_ticker):
        mock_ticker.return_value.history.return_value = fake_history(100.0)
        self.client.post(reverse('portfolio:buy_more', args=[self.holding.id]), {
            'quantity': '10', 'price': '200.00', 'notes': '',
        })
        self.holding.refresh_from_db()
        # (10*100 + 10*200) / 20 = 150
        self.assertAlmostEqual(float(self.holding.avg_price), 150.0)
        self.assertAlmostEqual(float(self.holding.quantity), 20.0)
 
    def test_cannot_buy_more_on_another_users_holding(self):
        other = User.objects.create_user(username='mallory', password='pw12345')
        self.client.login(username='mallory', password='pw12345')
        response = self.client.get(reverse('portfolio:buy_more', args=[self.holding.id]))
        self.assertEqual(response.status_code, 404)
 
 
class SellHoldingViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='dave', password='pw12345')
        self.client.login(username='dave', password='pw12345')
        self.portfolio = Portfolio.objects.create(user=self.user)
        self.holding = Holding.objects.create(
            portfolio=self.portfolio, symbol='AAPL', name='Apple Inc.',
            quantity=Decimal('10'), avg_price=Decimal('100'), current_price=Decimal('120'),
        )
 
    def test_selling_more_than_owned_is_rejected(self):
        response = self.client.post(reverse('portfolio:sell_holding', args=[self.holding.id]), {
            'quantity': '999', 'price': '120.00', 'notes': '',
        })
        self.holding.refresh_from_db()
        self.assertEqual(float(self.holding.quantity), 10.0)  # unchanged
        self.assertEqual(response.status_code, 200)  # re-rendered with error, not redirected
 
    def test_selling_partial_quantity_reduces_holding(self):
        response = self.client.post(reverse('portfolio:sell_holding', args=[self.holding.id]), {
            'quantity': '4', 'price': '120.00', 'notes': '',
        })
        self.holding.refresh_from_db()
        self.assertEqual(float(self.holding.quantity), 6.0)
        self.assertEqual(response.status_code, 302)
 
    def test_selling_entire_position_deletes_the_holding(self):
        self.client.post(reverse('portfolio:sell_holding', args=[self.holding.id]), {
            'quantity': '10', 'price': '120.00', 'notes': '',
        })
        self.assertFalse(Holding.objects.filter(id=self.holding.id).exists())
 
    def test_sell_creates_a_transaction_record(self):
        from portfolio.models import Transaction
        self.client.post(reverse('portfolio:sell_holding', args=[self.holding.id]), {
            'quantity': '4', 'price': '120.00', 'notes': '',
        })
        self.assertTrue(Transaction.objects.filter(
            portfolio=self.portfolio, symbol='AAPL', transaction_type='sell'
        ).exists())
 
 
class PriceAlertViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='erin', password='pw12345')
        self.client.login(username='erin', password='pw12345')
 
    def test_create_alert(self):
        response = self.client.post(reverse('portfolio:price_alerts'), {
            'symbol': 'AAPL', 'name': 'Apple Inc.', 'alert_type': 'above', 'target_price': '200.00',
        })
        self.assertTrue(PriceAlert.objects.filter(user=self.user, symbol='AAPL').exists())
 
    def test_delete_alert_removes_it(self):
        alert = PriceAlert.objects.create(
            user=self.user, symbol='AAPL', name='Apple Inc.', alert_type='above', target_price=Decimal('200'),
        )
        self.client.post(reverse('portfolio:delete_alert', args=[alert.id]))
        self.assertFalse(PriceAlert.objects.filter(id=alert.id).exists())
 
    def test_cannot_delete_another_users_alert(self):
        other = User.objects.create_user(username='mallory', password='pw12345')
        alert = PriceAlert.objects.create(
            user=other, symbol='AAPL', name='Apple Inc.', alert_type='above', target_price=Decimal('200'),
        )
        self.client.post(reverse('portfolio:delete_alert', args=[alert.id]))
        # Should still exist — the view scopes lookups to request.user
        self.assertTrue(PriceAlert.objects.filter(id=alert.id).exists())
 
    def test_toggle_alert_flips_is_active(self):
        alert = PriceAlert.objects.create(
            user=self.user, symbol='AAPL', name='Apple Inc.', alert_type='above',
            target_price=Decimal('200'), is_active=True,
        )
        self.client.post(reverse('portfolio:toggle_alert', args=[alert.id]))
        alert.refresh_from_db()
        self.assertFalse(alert.is_active)
 
 
class WatchlistViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='frank', password='pw12345')
        self.client.login(username='frank', password='pw12345')
 
    def test_add_to_watchlist(self):
        self.client.post(reverse('portfolio:watchlist'), {
            'symbol': 'TSLA', 'name': 'Tesla Inc.', 'asset_type': 'stock',
        })
        self.assertTrue(WatchlistItem.objects.filter(user=self.user, symbol='TSLA').exists())
 
    def test_delete_from_watchlist(self):
        item = WatchlistItem.objects.create(user=self.user, symbol='TSLA', name='Tesla Inc.')
        self.client.post(reverse('portfolio:delete_watchlist', args=[item.id]))
        self.assertFalse(WatchlistItem.objects.filter(id=item.id).exists())
 
 
class HoldingDetailViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='grace', password='pw12345')
        self.client.login(username='grace', password='pw12345')
        self.portfolio = Portfolio.objects.create(user=self.user)
        self.holding = Holding.objects.create(
            portfolio=self.portfolio, symbol='AAPL', name='Apple Inc.',
            quantity=Decimal('10'), avg_price=Decimal('100'),
        )
 
    @patch('portfolio.views.yf.Ticker')
    def test_page_renders_with_valid_price_history(self, mock_ticker):
        hist = pd.DataFrame(
            {'Close': [100 + i * 0.5 for i in range(40)]},
            index=pd.date_range('2026-01-01', periods=40, freq='D'),
        )
        mock_instance = mock_ticker.return_value
        mock_instance.history.return_value = hist
        mock_instance.info = {'fiftyTwoWeekHigh': 150, 'fiftyTwoWeekLow': 90}
 
        response = self.client.get(reverse('portfolio:holding_detail', args=[self.holding.id]))
        self.assertEqual(response.status_code, 200)
        # The response must be valid JSON-embeddable — no bare Python 'nan' token
        self.assertNotIn(b' nan,', response.content)
        self.assertNotIn(b'[nan', response.content)
 
    @patch('portfolio.views.yf.Ticker')
    def test_page_does_not_crash_when_yfinance_fails(self, mock_ticker):
        mock_ticker.side_effect = Exception('API down')
        response = self.client.get(reverse('portfolio:holding_detail', args=[self.holding.id]))
        self.assertEqual(response.status_code, 200)
 
    def test_cannot_view_another_users_holding(self):
        other = User.objects.create_user(username='mallory', password='pw12345')
        self.client.login(username='mallory', password='pw12345')
        response = self.client.get(reverse('portfolio:holding_detail', args=[self.holding.id]))
        self.assertEqual(response.status_code, 404)