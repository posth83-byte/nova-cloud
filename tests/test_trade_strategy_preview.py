import unittest
from trading.strategy import StrategyDataError, build_strategy_preview


class TradeStrategyPreviewTests(unittest.TestCase):
    def setUp(self):
        self.fx = {"rate": 11.2, "age_days": 1, "date": "2026-11-25", "source": "test"}

    def test_converts_prices_to_sek_and_allows_full_equity_allocation(self):
        markets = [{
            "symbol": "XBT/EUR", "ask": 60000, "bid": 59900,
            "spread_pct": 0.1668, "volume_24h_quote_est": 500000,
            "min_cost_quote": 0.5, "min_order_qty": 0.00001,
        }]
        result = build_strategy_preview(markets, self.fx)
        self.assertEqual(result["mode"], "paper_preview_only")
        self.assertFalse(result["execution_enabled"])
        self.assertEqual(result["max_trade_budget_sek"], 200.0)
        self.assertEqual(result["candidates"][0]["reference_ask_sek"], 672000.0)
        self.assertEqual(result["candidates"][0]["max_simulated_trade_budget_sek"], 200.0)

    def test_rejects_spread_and_exchange_minimum_over_budget(self):
        markets = [
            {"symbol": "A/EUR", "ask": 2, "bid": 1.9, "spread_pct": 5,
             "volume_24h_quote_est": 50000, "min_cost_quote": 1},
            {"symbol": "B/EUR", "ask": 2, "bid": 1.99, "spread_pct": 0.5,
             "volume_24h_quote_est": 50000, "min_cost_quote": 5},
        ]
        result = build_strategy_preview(markets, self.fx)
        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(result["rejected_count"], 2)

    def test_rejects_minimum_quantity_notional_when_costmin_missing(self):
        markets = [{
            "symbol": "XBT/EUR", "ask": 60000, "bid": 59900,
            "spread_pct": 0.1668, "volume_24h_quote_est": 500000,
            "min_order_qty": 0.0001,
        }]
        result = build_strategy_preview(markets, self.fx)
        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(result["rejected"][0]["reason"],
                         "exchange_minimum_exceeds_trade_budget_after_costs")

    def test_rejects_stale_fx(self):
        with self.assertRaises(StrategyDataError):
            build_strategy_preview([], {**self.fx, "age_days": 5})


if __name__ == "__main__":
    unittest.main()
