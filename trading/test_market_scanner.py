import unittest

from market_scanner import analyse_candles, discover_eur_spot_markets, ema, rank_opportunity, rsi, select_shortlist


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


    def test_discovers_active_eur_spot_pairs_only(self):
        markets = {
            "BTC/EUR": {"active": True, "spot": True, "quote": "EUR", "base": "BTC", "type": "spot"},
            "DOGE/EUR": {"active": True, "spot": True, "quote": "EUR", "base": "DOGE", "type": "spot"},
            "BTC/USD": {"active": True, "spot": True, "quote": "USD", "base": "BTC", "type": "spot"},
            "ETH/EUR:EUR": {"active": True, "swap": True, "quote": "EUR", "base": "ETH", "type": "swap"},
            "USDT/EUR": {"active": True, "spot": True, "quote": "EUR", "base": "USDT", "type": "spot"},
            "OLD/EUR": {"active": False, "spot": True, "quote": "EUR", "base": "OLD", "type": "spot"},
        }
        self.assertEqual(discover_eur_spot_markets(markets), ["BTC/EUR", "DOGE/EUR"])

    def test_open_position_is_reserved_in_shortlist_for_monitoring(self):
        liquid = [
            (1_000_000 - index, f"COIN{index}/EUR", {"last": 1.0}, 0.1)
            for index in range(30)
        ]
        markets = {"HELD/EUR": {"active": True, "spot": True}}
        tickers = {"HELD/EUR": {"last": 2.0, "bid": 1.99, "ask": 2.01, "quoteVolume": 1000}}
        shortlist, monitor_only = select_shortlist(
            liquid, ["HELD/EUR"], markets, tickers
        )
        self.assertEqual(len(shortlist), 30)
        self.assertIn("HELD/EUR", {row[1] for row in shortlist})
        self.assertEqual(monitor_only, {"HELD/EUR"})

    def test_ranking_prefers_stronger_bullish_setup(self):
        weak = {"trend": "neutral", "rsi14": 42, "volume_ratio": 0.8, "change_24h_pct": -1, "spread_pct": 0.5}
        strong = {"trend": "bullish", "rsi14": 58, "volume_ratio": 2.0, "change_24h_pct": 4, "spread_pct": 0.1}
        self.assertGreater(rank_opportunity(strong), rank_opportunity(weak))

if __name__ == "__main__":
    unittest.main()
