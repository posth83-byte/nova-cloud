import unittest

from backtest import run_backtest, run_walk_forward


def make_candles(count=180):
    rows = []
    price = 100.0
    for i in range(count):
        # Smooth upward drift with small deterministic oscillations.
        price *= 1.001 + (0.0002 if i % 3 == 0 else -0.00005)
        volume = 100.0 if i % 5 else 160.0
        rows.append([i * 3_600_000, price, price * 1.003, price * 0.997, price, volume])
    return rows


class BacktestTests(unittest.TestCase):
    def test_requires_enough_history(self):
        with self.assertRaises(ValueError):
            run_backtest(make_candles(30), 500)

    def test_result_includes_costs_and_metrics(self):
        result = run_backtest(make_candles(), 500)
        self.assertTrue(result["fees_and_slippage_included"])
        self.assertIn("net_return_pct", result)
        self.assertIn("max_drawdown_pct", result)
        self.assertIn("expectancy_per_trade", result)
        self.assertIn("profit_factor", result)
        self.assertIn("buy_and_hold_return_pct", result)
        self.assertIn("strategy_vs_buy_and_hold_pct_points", result)
        self.assertTrue(result["benchmark_costs_included"])
        self.assertEqual(result["mode"], "historical_backtest")

    def test_next_candle_entry_avoids_same_candle_lookahead(self):
        candles = make_candles()
        result = run_backtest(candles, 500)
        buys = [fill for fill in result["fills"] if fill["side"] == "buy"]
        if buys:
            self.assertGreaterEqual(buys[0]["timestamp"], candles[51][0])

    def test_risk_policy_rejects_excessive_risk(self):
        with self.assertRaises(ValueError):
            run_backtest(make_candles(), 500, risk_pct=2.0)


    def test_walk_forward_uses_multiple_non_overlapping_oos_folds(self):
        candles = make_candles(450)
        result = run_walk_forward(candles, 500, test_window=100)
        self.assertEqual(result["mode"], "walk_forward_out_of_sample")
        self.assertGreaterEqual(result["fold_count"], 3)
        self.assertTrue(result["non_overlapping_oos_windows"])
        self.assertTrue(result["fees_and_slippage_included"])
        self.assertIn("buy_and_hold_return_pct", result)
        self.assertIn("profit_factor", result)
        folds = result["folds"]
        for previous, current in zip(folds, folds[1:]):
            self.assertGreater(current["oos_start_timestamp"], previous["oos_end_timestamp"])

    def test_walk_forward_rejects_too_little_history(self):
        with self.assertRaises(ValueError):
            run_walk_forward(make_candles(180), 500, test_window=100)


if __name__ == "__main__":
    unittest.main()
