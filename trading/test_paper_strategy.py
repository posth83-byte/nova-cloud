import tempfile
import unittest
from pathlib import Path

from paper_engine import PaperBroker
from paper_strategy import run_cycle


class PaperStrategyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.broker = PaperBroker(Path(self.temp.name) / "state.json", 500.0)

    def tearDown(self):
        self.temp.cleanup()

    def test_bullish_confirmed_setup_creates_paper_buy(self):
        actions = run_cycle(self.broker, [{
            "symbol": "BTC/EUR",
            "last_price_eur": 100.0,
            "trend": "bullish",
            "rsi14": 60.0,
            "volume_ratio": 1.5,
            "last_candle_timestamp": 1000,
        }])
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["side"], "buy")
        self.assertIn("BTC/EUR", self.broker.state["positions"])

    def test_monitor_only_position_cannot_be_opened_as_new_trade(self):
        actions = run_cycle(self.broker, [{
            "symbol": "BTC/EUR",
            "last_price_eur": 100.0,
            "trend": "bullish",
            "rsi14": 60.0,
            "volume_ratio": 1.5,
            "last_candle_timestamp": 1000,
            "monitor_only": True,
        }])
        self.assertEqual(actions, [])
        self.assertEqual(self.broker.state["positions"], {})

    def test_monitor_only_position_still_triggers_stop(self):
        self.broker.buy("BTC/EUR", 100.0, 98.0)
        self.broker.state["processed_candles"]["BTC/EUR"] = 1000
        self.broker._save()
        actions = run_cycle(self.broker, [{
            "symbol": "BTC/EUR",
            "last_price_eur": 97.0,
            "trend": "neutral",
            "rsi14": 45.0,
            "volume_ratio": 1.0,
            "last_candle_timestamp": 1000,
            "monitor_only": True,
        }])
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["reason"], "stop_loss")
        self.assertEqual(self.broker.state["positions"], {})

    def test_weak_volume_does_not_open_trade(self):
        actions = run_cycle(self.broker, [{
            "symbol": "BTC/EUR",
            "last_price_eur": 100.0,
            "trend": "bullish",
            "rsi14": 60.0,
            "volume_ratio": 0.8,
            "last_candle_timestamp": 1000,
        }])
        self.assertEqual(actions, [])
        self.assertEqual(self.broker.state["positions"], {})

    def test_same_closed_candle_is_processed_only_once(self):
        neutral = {
            "symbol": "BTC/EUR", "last_price_eur": 100.0,
            "trend": "neutral", "rsi14": 45.0, "volume_ratio": 1.0,
            "last_candle_timestamp": 1000,
        }
        self.assertEqual(run_cycle(self.broker, [neutral]), [])
        changed_same_candle = dict(neutral, trend="bullish", rsi14=60.0, volume_ratio=1.5)
        self.assertEqual(run_cycle(self.broker, [changed_same_candle]), [])
        next_candle = dict(changed_same_candle, last_candle_timestamp=2000)
        self.assertEqual(run_cycle(self.broker, [next_candle])[0]["side"], "buy")

    def test_stale_symbol_signal_cannot_open_position(self):
        neutral_eth = {
            "symbol": "ETH/EUR", "last_price_eur": 100.0,
            "trend": "neutral", "rsi14": 45.0, "volume_ratio": 1.0,
            "last_candle_timestamp": 1000,
        }
        self.assertEqual(run_cycle(self.broker, [neutral_eth]), [])
        stale_bullish_eth = dict(neutral_eth, trend="bullish", rsi14=60.0, volume_ratio=1.5)
        fresh_neutral_btc = {
            "symbol": "BTC/EUR", "last_price_eur": 100.0,
            "trend": "neutral", "rsi14": 45.0, "volume_ratio": 1.0,
            "last_candle_timestamp": 2000,
        }
        self.assertEqual(run_cycle(self.broker, [stale_bullish_eth, fresh_neutral_btc]), [])
        fresh_bullish_eth = dict(stale_bullish_eth, last_candle_timestamp=2000)
        self.assertEqual(run_cycle(self.broker, [fresh_bullish_eth, fresh_neutral_btc])[0]["side"], "buy")

    def test_stop_monitoring_runs_without_a_new_candle(self):
        self.broker.buy("BTC/EUR", 100.0, 98.0)
        self.broker.state["processed_candles"]["BTC/EUR"] = 1000
        self.broker._save()
        same_candle_lower_mark = {
            "symbol": "BTC/EUR", "last_price_eur": 97.0,
            "trend": "neutral", "rsi14": 45.0, "volume_ratio": 1.0,
            "last_candle_timestamp": 1000,
        }
        actions = run_cycle(self.broker, [same_candle_lower_mark])
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["reason"], "stop_loss")
        self.assertEqual(self.broker.state["positions"], {})

    def test_live_mark_price_triggers_stop_before_hourly_close(self):
        self.broker.buy("BTC/EUR", 100.0, 98.0)
        self.broker.state["processed_candles"]["BTC/EUR"] = 1000
        self.broker._save()
        market = {
            "symbol": "BTC/EUR",
            "last_price_eur": 101.0,
            "mark_price_eur": 97.0,
            "trend": "neutral",
            "rsi14": 45.0,
            "volume_ratio": 1.0,
            "last_candle_timestamp": 1000,
        }
        actions = run_cycle(self.broker, [market])
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["reason"], "stop_loss")
        self.assertEqual(self.broker.state["positions"], {})

    def test_bearish_trend_exits_existing_position(self):
        self.broker.buy("BTC/EUR", 100.0, 98.0)
        actions = run_cycle(self.broker, [{
            "symbol": "BTC/EUR",
            "last_price_eur": 99.0,
            "trend": "bearish",
            "rsi14": 45.0,
            "volume_ratio": 1.0,
            "last_candle_timestamp": 1000,
        }])
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["reason"], "strategy_exit")
        self.assertEqual(self.broker.state["positions"], {})


if __name__ == "__main__":
    unittest.main()
