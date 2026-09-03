from django.test import TestCase
 
from portfolio.forms import AddHoldingForm, BuyForm, PriceAlertForm, SellForm, WatchlistForm
 
 
class AddHoldingFormTests(TestCase):
    def valid_data(self, **overrides):
        data = {
            'symbol': 'AAPL', 'name': 'Apple Inc.', 'asset_type': 'stock',
            'quantity': '10', 'price': '150.50', 'notes': '',
        }
        data.update(overrides)
        return data
 
    def test_valid_data_passes(self):
        form = AddHoldingForm(data=self.valid_data())
        self.assertTrue(form.is_valid())
 
    def test_missing_symbol_is_invalid(self):
        form = AddHoldingForm(data=self.valid_data(symbol=''))
        self.assertFalse(form.is_valid())
        self.assertIn('symbol', form.errors)
 
    def test_missing_quantity_is_invalid(self):
        form = AddHoldingForm(data=self.valid_data(quantity=''))
        self.assertFalse(form.is_valid())
        self.assertIn('quantity', form.errors)
 
    def test_non_numeric_quantity_is_invalid(self):
        form = AddHoldingForm(data=self.valid_data(quantity='not-a-number'))
        self.assertFalse(form.is_valid())
        self.assertIn('quantity', form.errors)
 
    def test_invalid_asset_type_choice_is_rejected(self):
        form = AddHoldingForm(data=self.valid_data(asset_type='nonsense'))
        self.assertFalse(form.is_valid())
        self.assertIn('asset_type', form.errors)
 
    def test_notes_is_optional(self):
        form = AddHoldingForm(data=self.valid_data(notes=''))
        self.assertTrue(form.is_valid())
 
    def test_crypto_asset_type_accepted(self):
        form = AddHoldingForm(data=self.valid_data(symbol='BTC-USD', asset_type='crypto'))
        self.assertTrue(form.is_valid())
 
 
class BuyFormTests(TestCase):
    def test_valid_data_passes(self):
        form = BuyForm(data={'quantity': '5', 'price': '100.00', 'notes': ''})
        self.assertTrue(form.is_valid())
 
    def test_missing_price_is_invalid(self):
        form = BuyForm(data={'quantity': '5', 'price': '', 'notes': ''})
        self.assertFalse(form.is_valid())
        self.assertIn('price', form.errors)
 
    def test_negative_quantity_is_currently_accepted_by_the_field(self):
        # DecimalField has no min_value set on this form, so negative values
        # pass form validation today. Documented here so a future min_value
        # constraint change is a deliberate decision, not a silent regression.
        form = BuyForm(data={'quantity': '-5', 'price': '100.00', 'notes': ''})
        self.assertTrue(form.is_valid())
 
 
class SellFormTests(TestCase):
    def test_valid_data_passes(self):
        form = SellForm(data={'quantity': '2', 'price': '120.00', 'notes': ''})
        self.assertTrue(form.is_valid())
 
    def test_missing_quantity_is_invalid(self):
        form = SellForm(data={'quantity': '', 'price': '120.00', 'notes': ''})
        self.assertFalse(form.is_valid())
 
 
class PriceAlertFormTests(TestCase):
    def test_valid_data_passes(self):
        form = PriceAlertForm(data={
            'symbol': 'AAPL', 'name': 'Apple Inc.',
            'alert_type': 'above', 'target_price': '200.00',
        })
        self.assertTrue(form.is_valid())
 
    def test_invalid_alert_type_rejected(self):
        form = PriceAlertForm(data={
            'symbol': 'AAPL', 'name': 'Apple Inc.',
            'alert_type': 'sideways', 'target_price': '200.00',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('alert_type', form.errors)
 
    def test_missing_target_price_is_invalid(self):
        form = PriceAlertForm(data={
            'symbol': 'AAPL', 'name': 'Apple Inc.', 'alert_type': 'above', 'target_price': '',
        })
        self.assertFalse(form.is_valid())
 
 
class WatchlistFormTests(TestCase):
    def test_valid_data_passes(self):
        form = WatchlistForm(data={'symbol': 'TSLA', 'name': 'Tesla Inc.', 'asset_type': 'stock'})
        self.assertTrue(form.is_valid())
 
    def test_missing_name_is_invalid(self):
        form = WatchlistForm(data={'symbol': 'TSLA', 'name': '', 'asset_type': 'stock'})
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)