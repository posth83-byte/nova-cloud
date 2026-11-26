import unittest
from unittest.mock import patch

from trading.paper_engine import create_initial_state
from trading import worker


class PaperWorkerTests(unittest.TestCase):
    def setUp(self):
        self.state = create_initial_state("200.00")
        self.state["paper_enabled"] = True
        self.market = {
            "symbol": "XBT/EUR",
            "ask": 20.1,
            "bid": 19.9,
            "last": 20.0,
            "spread_pct": 0.1,
            "volume_24h_quote_est": 500_000,
            "min_order_qty": 0.01,
            "min_cost_quote": 1.0,
        }
        closes = [10.0] * 36 + [20.0]
        self.history = {
            "candles": [
                {"timestamp": 1_800_000_000 + i * 3600, "close": value}
                for i, value in enumerate(closes)
            ],
            "min_order_qty": 0.01,
            "min_cost_eur": 1.0,
        }
        self.fx = {"rate": 10.0, "date": "2026-11-26", "age_days": 0}

    def test_worker_simulates_buy_on_new_closed_candle(self):
        saved = []
        with (
            patch.object(worker, "load_or_create", return_value=(self.state, 4)),
            patch.object(worker, "fetch_eur_sek_rate", return_value=self.fx),
            patch.object(worker, "scan_markets", return_value={"markets": [self.market]}),
            patch.object(worker, "fetch_ohlc_candles", return_value=self.history),
            patch.object(worker, "save_state", side_effect=lambda state, revision: saved.append(state) or 5),
        ):
            result = worker.run_paper_tick()

        self.assertTrue(result["ok"])
        self.assertTrue(result["paper_enabled"])
        self.assertFalse(result["orders_enabled"])
        self.assertEqual(result["actions"][0]["side"], "paper_buy")
        self.assertIn("XBT/EUR", saved[0]["positions"])
        self.assertLess(float(saved[0]["cash"]), 200.0)

    def test_worker_is_idempotent_for_already_processed_candle(self):
        timestamp = self.history["candles"][-1]["timestamp"]
        self.state["worker"] = {"processed_candles": {"XBT/EUR": timestamp}}
        saved = []
        with (
            patch.object(worker, "load_or_create", return_value=(self.state, 4)),
            patch.object(worker, "fetch_eur_sek_rate", return_value=self.fx),
            patch.object(worker, "scan_markets", return_value={"markets": [self.market]}),
            patch.object(worker, "fetch_ohlc_candles", return_value=self.history),
            patch.object(worker, "save_state", side_effect=lambda state, revision: saved.append(state) or 5),
        ):
            result = worker.run_paper_tick()

        self.assertTrue(result["ok"])
        self.assertEqual(result["candles_evaluated"], 0)
        self.assertEqual(result["actions"], [])
        self.assertEqual(saved[0]["positions"], {})

    def test_disabled_paper_worker_does_not_fetch_markets(self):
        self.state["paper_enabled"] = False
        with (
            patch.object(worker, "load_or_create", return_value=(self.state, 4)),
            patch.object(worker, "scan_markets") as scan,
            patch.object(worker, "save_state", return_value=5),
        ):
            result = worker.run_paper_tick()
        self.assertEqual(result["status"], "waiting_for_paper_activation")
        scan.assert_not_called()


if __name__ == "__main__":
    unittest.main()
