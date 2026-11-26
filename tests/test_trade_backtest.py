import math
import unittest

from trading.backtest import run_sma_backtest


class TradeBacktestTests(unittest.TestCase):
    def make_candles(self, count=240):
        rows = []
        for index in range(count):
            # Deterministic oscillating trend produces repeatable crossovers.
            close = 100 + (index * 0.04) + 5 * math.sin(index / 8)
            rows.append({"timestamp": 1_700_000_000 + index * 3600, "close": close})
        return rows

    def test_runs_out_of_sample_with_costs_and_simulation_flags(self):
        result = run_sma_backtest(
            self.make_candles(),
            fx_sek_per_eur=11.2,
            min_order_qty=0.00001,
            spread_pct=0.2,
        )
        self.assertEqual(result["mode"], "historical_backtest_only")
        self.assertFalse(result["execution_enabled"])
        self.assertFalse(result["orders_enabled"])\n        self.assertIn("buy_and_hold_return_pct", result["results"])\n        self.assertIn("expectancy_sek_est", result["results"])
        self.assertEqual(result["sample"]["candles"], 240)
        self.assertEqual(result["sample"]["in_sample_candles"] +
                         result["sample"]["out_of_sample_candles"], 240)
        self.assertGreaterEqual(result["results"]["max_drawdown_pct"], 0)
        self.assertLessEqual(result["results"]["max_drawdown_pct"], 100)

    def test_rejects_exchange_minimum_above_trade_budget(self):
        result = run_sma_backtest(
            self.make_candles(),
            fx_sek_per_eur=11.2,
            min_order_qty=1000,
        )
        self.assertEqual(result["results"]["closed_trades"], 0)
        self.assertGreaterEqual(result["results"]["rejected_for_exchange_minimum"], 0)

    def test_rejects_insufficient_or_invalid_data(self):
        with self.assertRaises(ValueError):
            run_sma_backtest(self.make_candles(30), fx_sek_per_eur=11.2)
        with self.assertRaises(ValueError):
            run_sma_backtest(self.make_candles(), fx_sek_per_eur=0)


if __name__ == "__main__":
    unittest.main()
