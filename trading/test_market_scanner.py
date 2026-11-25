import unittest

from market_scanner import analyse_candles, ema, rsi


class IndicatorTests(unittest.TestCase):
    def test_ema_requires_enough_values(self):
        self.assertIsNone(ema([1, 2, 3], 5))

    def test_ema_is_calculated(self):
        self.assertAlmostEqual(ema([1, 2, 3, 4, 5], 3), 4.0)

    def test_rsi_all_gains_is_100(self):
        self.assertEqual(rsi(list(range(1, 20)), 14), 100.0)

    def test_rsi_flat_is_50(self):
        self.assertEqual(rsi([10.0] * 20, 14), 50.0)

    def test_analyser_needs_51_candles(self):
        with self.assertRaises(ValueError):
            analyse_candles("BTC/EUR", [])

    def test_analyser_exposes_closed_candle_timestamp(self):
        candles = []
        for i in range(60):
            price = 100 + i
            candles.append([i * 3_600_000, price, price + 1, price - 1, price, 10])
        result = analyse_candles("BTC/EUR", candles)
        self.assertEqual(result["last_candle_timestamp"], candles[-1][0])

    def test_analyser_never_emits_trade_order(self):
        candles = []
        for i in range(60):
            price = 100 + i
            candles.append([i, price, price + 1, price - 1, price, 10])
        result = analyse_candles("BTC/EUR", candles)
        self.assertEqual(result["signal"], "watch_only")
        self.assertIn("warning", result)


if __name__ == "__main__":
    unittest.main()
