import unittest
from unittest.mock import patch

from trading.kraken_monitor import build_market_rows, value_account_balances


class KrakenMarketMonitorTests(unittest.TestCase):
    def test_builds_and_ranks_eur_markets_by_quote_turnover(self):
        pairs = {
            "XXBTZEUR": {"altname": "XBTEUR", "wsname": "XBT/EUR", "status": "online", "pair_decimals": 1, "lot_decimals": 8, "base": "XXBT", "quote": "ZEUR"},
            "XETCZEUR": {"altname": "ETCEUR", "wsname": "ETC/EUR", "status": "online"},
            "USDCZEUR": {"altname": "USDCEUR", "wsname": "USDC/EUR", "status": "online"},
            "XETHZUSD": {"altname": "ETHUSD", "wsname": "ETH/USD", "status": "online"},
        }
        tickers = {
            "XBTEUR": {"c": ["60000"], "o": "59000", "v": ["1", "2"], "p": ["59500", "59500"], "a": ["60030", "1", "1"], "b": ["59970", "1", "1"], "h": ["61000", "60500"], "l": ["58000", "58500"]},
            "ETCEUR": {"c": ["20"], "o": "21", "v": ["10", "100"], "p": ["20", "20"], "a": ["20.02", "1", "1"], "b": ["19.98", "1", "1"], "h": ["22", "22"], "l": ["19", "19"]},
            "USDCEUR": {"c": ["0.9"], "o": "0.9", "v": ["1000", "1000"], "p": ["0.9", "0.9"], "h": ["0.91", "0.91"], "l": ["0.89", "0.89"]},
            "ETHUSD": {"c": ["3000"], "o": "2900", "v": ["10", "10"], "p": ["2950", "2950"], "h": ["3100", "3100"], "l": ["2800", "2800"]},
        }
        rows = build_market_rows(pairs, tickers, quote="EUR")
        self.assertEqual([row["symbol"] for row in rows], ["XBT/EUR", "ETC/EUR"])
        self.assertAlmostEqual(rows[0]["change_24h_pct"], 1.695, places=2)
        self.assertEqual(rows[1]["volume_24h_quote_est"], 2000.0)
        self.assertAlmostEqual(rows[0]["spread_pct"], 0.1, places=2)
        self.assertAlmostEqual(rows[0]["ask"], 60030.0)
        self.assertAlmostEqual(rows[0]["bid"], 59970.0)
        self.assertEqual(rows[0]["price_decimals"], 1)
        self.assertEqual(rows[0]["lot_decimals"], 8)
        self.assertEqual(rows[0]["base_asset"], "XXBT")
        self.assertEqual(rows[0]["quote_asset"], "ZEUR")


    def test_values_all_priced_balances_and_marks_unknown_assets(self):
        pairs = {
            "XXBTZEUR": {"altname": "XBTEUR", "wsname": "XBT/EUR", "status": "online", "base": "XXBT"},
            "ZUSDZEUR": {"altname": "USDEUR", "wsname": "USD/EUR", "status": "online", "base": "ZUSD"},
            "XETHZUSD": {"altname": "ETHUSD", "wsname": "ETH/USD", "status": "online", "base": "XETH"},
        }
        tickers = {
            "XBTEUR": {"c": ["60000"]},
            "USDEUR": {"c": ["0.9"]},
            "ETHUSD": {"c": ["3000"]},
        }
        with patch("trading.kraken_monitor._public_get", side_effect=[pairs, tickers]):
            result = value_account_balances(
                {"ZEUR": "10", "XXBT": "0.001", "XETH": "0.1", "ZUSD": "5", "UNKNOWN": "3"},
                11.2,
            )
        self.assertAlmostEqual(result["total_eur"], 344.5)
        self.assertAlmostEqual(result["total_sek"], 3858.4)
        self.assertFalse(result["valuation_complete"])
        self.assertEqual(result["unpriced_assets"][0]["asset"], "UNKNOWN")
        self.assertEqual({row["asset"] for row in result["assets"]}, {"ZEUR", "XXBT", "XETH", "ZUSD"})

    def test_preserves_zero_precision_metadata(self):
        pairs = {
            "AAA": {
                "altname": "AAAEUR", "wsname": "AAA/EUR", "status": "online",
                "pair_decimals": 0, "lot_decimals": 0,
            }
        }
        tickers = {
            "AAAEUR": {
                "c": ["2"], "o": "2", "v": ["1", "10"], "p": ["2", "2"],
                "a": ["2", "1", "1"], "b": ["1", "1", "1"],
                "h": ["2", "2"], "l": ["1", "1"],
            }
        }
        rows = build_market_rows(pairs, tickers, quote="EUR")
        self.assertEqual(rows[0]["price_decimals"], 0)
        self.assertEqual(rows[0]["lot_decimals"], 0)

    def test_ignores_offline_and_incomplete_pairs(self):
        pairs = {
            "A": {"altname": "AAAEUR", "wsname": "AAA/EUR", "status": "cancel_only"},
            "B": {"altname": "BBBEUR", "wsname": "BBB/EUR", "status": "online"},
        }
        rows = build_market_rows(pairs, {}, quote="EUR")
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
