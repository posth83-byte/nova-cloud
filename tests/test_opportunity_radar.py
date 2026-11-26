import unittest
from unittest.mock import patch
import asyncio

from trading.opportunity_radar import rank_opportunities


class OpportunityRadarTests(unittest.TestCase):
    def setUp(self):
        self.markets = [
            {
                "symbol": "XBT/EUR", "ask": 60000, "bid": 59940,
                "spread_pct": 0.1, "volume_24h_quote_est": 500000,
                "change_24h_pct": 4.2, "high_24h": 62000, "low_24h": 58000,
                "last": 60000, "min_order_qty": 0.0001, "min_cost_quote": 0.5,
            },
            {
                "symbol": "BAD/EUR", "ask": 1.01, "bid": 0.99,
                "spread_pct": 2.0, "volume_24h_quote_est": 100000,
                "change_24h_pct": 50, "high_24h": 2, "low_24h": 0.5,
                "last": 1, "min_order_qty": 1, "min_cost_quote": 0,
            },
        ]

    def test_ranks_candidate_but_never_creates_buy_signal(self):
        result = rank_opportunities(self.markets, equity_sek=200, eur_sek=11.2)
        self.assertEqual(result["eligible_count"], 1)
        self.assertEqual(result["candidates"][0]["symbol"], "XBT/EUR")
        self.assertFalse(result["buy_signal"])
        self.assertFalse(result["candidates"][0]["buy_signal"])
        self.assertEqual(result["candidates"][0]["action"], "monitor_closely")
        self.assertFalse(result["orders_enabled"])

    def test_rejects_spread_and_exchange_minimum_over_budget(self):
        market = dict(self.markets[0])
        market["min_order_qty"] = 1
        result = rank_opportunities([market], equity_sek=200, eur_sek=11.2)
        self.assertEqual(result["eligible_count"], 0)
        self.assertEqual(result["rejected_sample"][0]["reason"], "minimum_order_exceeds_200_sek")

    def test_rejects_invalid_input(self):
        with self.assertRaises(ValueError):
            rank_opportunities([], equity_sek=200, eur_sek=0)


class OpportunityRadarApiTests(unittest.TestCase):
    def test_opportunities_endpoint_is_read_only(self):
        from trading import api
        state = {"starting_cash": "200.00", "cash": "200.00", "worker": {}}
        market_data = {"markets": [{
            "symbol": "XBT/EUR", "ask": 60000, "bid": 59940,
            "spread_pct": 0.1, "volume_24h_quote_est": 500000,
            "change_24h_pct": 4.2, "high_24h": 62000, "low_24h": 58000,
            "last": 60000, "min_order_qty": 0.0001, "min_cost_quote": 0.5,
        }]}
        fx = {"rate": 11.2, "age_days": 1, "date": "2026-11-25", "source": "test"}
        with (
            patch.object(api, "_load", return_value=(state, 1)),
            patch.object(api, "fetch_eur_sek_rate", return_value=fx),
            patch.object(api, "scan_markets", return_value=market_data),
        ):
            result = asyncio.run(api.trading_opportunities(limit=5))
        self.assertEqual(result["mode"], "opportunity_radar")
        self.assertFalse(result["execution_enabled"])
        self.assertFalse(result["orders_enabled"])
        self.assertEqual(result["paper_balance_sek"], 200.0)
        self.assertEqual(result["eligible_count"], 1)


if __name__ == "__main__":
    unittest.main()
