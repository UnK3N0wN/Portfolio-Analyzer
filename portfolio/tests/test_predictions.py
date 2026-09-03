"""
Tests for the technical indicator and prediction functions in
portfolio/views.py: calculate_macd, calculate_rsi, calculate_bollinger_bands,
and predict_prices (the Random Forest + Holt's smoothing ensemble).

These are pure functions (no DB, no network), so plain TestCase (or even
unittest) is enough — no fixtures needed.
"""
import math

from django.test import SimpleTestCase

from portfolio.views import (
    calculate_bollinger_bands, calculate_macd, calculate_rsi, predict_prices,
)


class MACDTests(SimpleTestCase):
    def test_flat_price_series_gives_zero_macd(self):
        prices = [100.0] * 40
        macd_line, signal_line, histogram = calculate_macd(prices)
        self.assertTrue(all(abs(v) < 1e-9 for v in macd_line))
        self.assertTrue(all(abs(v) < 1e-9 for v in histogram))

    def test_output_lengths_match_input_length(self):
        prices = [100 + i for i in range(50)]
        macd_line, signal_line, histogram = calculate_macd(prices)
        self.assertEqual(len(macd_line), 50)
        self.assertEqual(len(signal_line), 50)
        self.assertEqual(len(histogram), 50)

    def test_histogram_equals_macd_minus_signal(self):
        prices = [100 + (i % 7) * 2 for i in range(40)]
        macd_line, signal_line, histogram = calculate_macd(prices)
        for m, s, h in zip(macd_line, signal_line, histogram):
            self.assertAlmostEqual(h, round(m - s, 4), places=3)

    def test_rising_trend_produces_positive_macd_by_the_end(self):
        prices = [100 + i * 2 for i in range(40)]  # steady uptrend
        macd_line, _, _ = calculate_macd(prices)
        self.assertGreater(macd_line[-1], 0)

    def test_short_series_does_not_crash(self):
        macd_line, signal_line, histogram = calculate_macd([100.0])
        self.assertEqual(macd_line, [])
        self.assertEqual(signal_line, [])
        self.assertEqual(histogram, [])

    def test_empty_series_does_not_crash(self):
        macd_line, signal_line, histogram = calculate_macd([])
        self.assertEqual(macd_line, [])


class RSITests(SimpleTestCase):
    def test_all_gains_pushes_rsi_toward_100(self):
        prices = [100 + i for i in range(30)]  # strictly increasing
        rsi = calculate_rsi(prices)
        self.assertGreater(rsi[-1], 90)

    def test_all_losses_pushes_rsi_toward_0(self):
        prices = [130 - i for i in range(30)]  # strictly decreasing
        rsi = calculate_rsi(prices)
        self.assertLess(rsi[-1], 10)

    def test_rsi_stays_within_valid_range(self):
        prices = [100 + (i % 5) * 3 - (i % 3) * 2 for i in range(40)]
        rsi = calculate_rsi(prices)
        for v in rsi:
            self.assertGreaterEqual(v, 0)
            self.assertLessEqual(v, 100)

    def test_output_length_matches_input(self):
        prices = list(range(100, 130))
        rsi = calculate_rsi(prices)
        self.assertEqual(len(rsi), len(prices))

    def test_single_price_does_not_crash(self):
        rsi = calculate_rsi([100.0])
        self.assertEqual(rsi, [50.0])


class BollingerBandsTests(SimpleTestCase):
    def test_upper_band_always_at_or_above_middle(self):
        prices = [100 + (i % 5) for i in range(30)]
        mid, upper, lower = calculate_bollinger_bands(prices)
        for m, u in zip(mid, upper):
            self.assertGreaterEqual(u, m)

    def test_lower_band_always_at_or_below_middle(self):
        prices = [100 + (i % 5) for i in range(30)]
        mid, upper, lower = calculate_bollinger_bands(prices)
        for m, l in zip(mid, lower):
            self.assertLessEqual(l, m)

    def test_flat_price_series_gives_zero_width_bands(self):
        prices = [50.0] * 25
        mid, upper, lower = calculate_bollinger_bands(prices)
        for m, u, l in zip(mid, upper, lower):
            self.assertAlmostEqual(m, 50.0)
            self.assertAlmostEqual(u, 50.0)
            self.assertAlmostEqual(l, 50.0)

    def test_output_lengths_match_input(self):
        prices = [100 + i for i in range(45)]
        mid, upper, lower = calculate_bollinger_bands(prices)
        self.assertEqual(len(mid), 45)
        self.assertEqual(len(upper), 45)
        self.assertEqual(len(lower), 45)


class PredictPricesTests(SimpleTestCase):
    def test_insufficient_data_returns_empty_prediction(self):
        result = predict_prices([100, 101, 102], days=7)
        self.assertEqual(result['predicted'], [])
        self.assertEqual(result['model'], 'insufficient_data')

    def test_returns_requested_number_of_days(self):
        prices = [100 + i * 0.5 for i in range(40)]
        result = predict_prices(prices, days=7)
        self.assertEqual(len(result['predicted']), 7)
        self.assertEqual(len(result['upper']), 7)
        self.assertEqual(len(result['lower']), 7)

    def test_upper_band_never_below_predicted_value(self):
        prices = [100 + i * 0.5 for i in range(40)]
        result = predict_prices(prices, days=7)
        for p, u in zip(result['predicted'], result['upper']):
            self.assertGreaterEqual(u, p)

    def test_lower_band_never_above_predicted_value(self):
        prices = [100 + i * 0.5 for i in range(40)]
        result = predict_prices(prices, days=7)
        for p, l in zip(result['predicted'], result['lower']):
            self.assertLessEqual(l, p)

    def test_lower_band_never_goes_negative(self):
        # even a sharply falling series should floor the lower band at 0
        prices = [50 - i * 1.1 for i in range(30)]
        result = predict_prices(prices, days=7)
        for l in result['lower']:
            self.assertGreaterEqual(l, 0)

    def test_model_name_is_one_of_the_known_values(self):
        prices = [100 + i * 0.3 for i in range(40)]
        result = predict_prices(prices, days=7)
        self.assertIn(result['model'], ('ensemble_rf_holt', 'holt_linear'))

    def test_no_nan_or_inf_in_output(self):
        prices = [100 + i * 0.7 for i in range(40)]
        result = predict_prices(prices, days=7)
        for series in (result['predicted'], result['upper'], result['lower']):
            for v in series:
                self.assertFalse(math.isnan(v), f'NaN found in prediction output: {series}')
                self.assertFalse(math.isinf(v), f'Inf found in prediction output: {series}')

    def test_uptrend_produces_higher_final_prediction_than_first_predicted_day(self):
        prices = [100 + i * 1.5 for i in range(40)]  # strong, clean uptrend
        result = predict_prices(prices, days=7)
        self.assertGreater(result['predicted'][-1], result['predicted'][0])