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

    def test_stop_monitor_closes_position_automatically(self):
        self.broker.buy("BTC/EUR", 100.0, 95.0)
        fills = self.broker.check_stops({"BTC/EUR": 94.0})
        self.assertEqual(len(fills), 1)
        self.assertEqual(fills[0]["reason"], "stop_loss")
        self.assertEqual(self.broker.state["positions"], {})

    def test_daily_drawdown_blocks_new_entry(self):
        self.broker.buy("BTC/EUR", 100.0, 95.0)
        self.broker.sell("BTC/EUR", 50.0, reason="test_drawdown")
        with self.assertRaises(TradeRejected):
            self.broker.buy("ETH/EUR", 50.0, 47.0)

    def test_kraken_pair_specific_minimums(self):
        minimums = {"BTC/EUR": 0.00006, "ETH/EUR": 0.002}
        btc = PaperBroker(
            self.path.parent / "small-btc.json", 17.81,
            fee_rate=0.008, slippage_rate=0.0005,
            minimum_notional=0.45, minimum_order_sizes=minimums,
        )
        btc_fill = btc.buy("BTC/EUR", 80000.0, 78400.0)
        self.assertGreaterEqual(btc_fill["quantity"], 0.00006)

        eth = PaperBroker(
            self.path.parent / "small-eth.json", 17.81,
            fee_rate=0.008, slippage_rate=0.0005,
            minimum_notional=0.45, minimum_order_sizes=minimums,
        )
        with self.assertRaises(TradeRejected):
            eth.buy("ETH/EUR", 2700.0, 2646.0)

    def test_exchange_minimum_amount_is_not_bypassed(self):
        small = PaperBroker(self.path.parent / "amount-min.json", 500.0, minimum_notional=1.0)
        with self.assertRaises(TradeRejected):
            small.buy("BTC/EUR", 100.0, 95.0, minimum_amount=1.0)

    def test_minimum_notional_is_not_bypassed(self):
        strict = PaperBroker(self.path.parent / "strict.json", 500.0, minimum_notional=1000.0)
        with self.assertRaises(TradeRejected):
            strict.buy("BTC/EUR", 100.0, 95.0)

    def test_live_state_is_refused(self):
        state = json.loads(self.path.read_text())
        state["mode"] = "live"
        self.path.write_text(json.dumps(state))
        with self.assertRaises(ValueError):
            PaperBroker(self.path, 500.0)


if __name__ == "__main__":
    unittest.main()
