import json
import tempfile
import unittest
from pathlib import Path

from paper_engine import PaperBroker, TradeRejected


class PaperBrokerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "paper-state.json"
        self.broker = PaperBroker(self.path, 500.0, minimum_notional=1.0)

    def tearDown(self):
        self.temp.cleanup()

    def test_buy_and_sell_records_net_profit_after_costs(self):
        self.broker.buy("BTC/EUR", 100.0, 95.0)
        result = self.broker.sell("BTC/EUR", 110.0)
        self.assertGreater(result["realized_pnl"], 0)
        self.assertEqual(self.broker.state["positions"], {})
        self.assertGreater(self.broker.state["fees_paid"], 0)

    def test_loss_is_recorded_after_fees(self):
        self.broker.buy("BTC/EUR", 100.0, 95.0)
        result = self.broker.sell("BTC/EUR", 90.0)
        self.assertLess(result["realized_pnl"], 0)

    def test_only_allowlisted_spot_pairs(self):
        with self.assertRaises(TradeRejected):
            self.broker.buy("DOGE/EUR", 0.1, 0.09)

    def test_requires_stop_below_entry(self):
        with self.assertRaises(TradeRejected):
            self.broker.buy("BTC/EUR", 100.0, 100.0)

    def test_one_open_position_maximum(self):
        self.broker.buy("BTC/EUR", 100.0, 95.0)
        with self.assertRaises(TradeRejected):
            self.broker.buy("ETH/EUR", 50.0, 47.0)

    def test_reloads_persistent_paper_state(self):
        self.broker.buy("BTC/EUR", 100.0, 95.0)
        restored = PaperBroker(self.path, 500.0, minimum_notional=1.0)
        self.assertIn("BTC/EUR", restored.state["positions"])
        self.assertEqual(restored.state["mode"], "paper")

    def test_profit_remains_in_cash_for_reinvestment(self):
        self.broker.buy("BTC/EUR", 100.0, 95.0)
        self.broker.sell("BTC/EUR", 110.0)
        self.assertGreater(self.broker.state["cash"], 500.0)
        self.assertEqual(self.broker.state["external_funding"], 500.0)

    def test_live_state_is_refused(self):
        state = json.loads(self.path.read_text())
        state["mode"] = "live"
        self.path.write_text(json.dumps(state))
        with self.assertRaises(ValueError):
            PaperBroker(self.path, 500.0)


if __name__ == "__main__":
    unittest.main()
