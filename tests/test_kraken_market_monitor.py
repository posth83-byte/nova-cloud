import unittest

from trading.kraken_monitor import build_market_rows


class KrakenMarketMonitorTests(unittest.TestCase):
    def test_builds_and_ranks_eur_markets_by_quote_turnover(self):
        pairs = {
            "XXBTZEUR": {"altname": "XBTEUR", "wsname": "XBT/EUR", "status": "online"},
            "XETCZEUR": {"altname": "ETCEUR", "wsname": "ETC/EUR", "status": "online"},
            "USDCZEUR": {"altname": "USDCEUR", "wsname": "USDC/EUR", "status": "online"},
            "XETHZUSD": {"altname": "ETHUSD", "wsname": "ETH/USD", "status": "online"},
        }
        tickers = {
            "XBTEUR": {"c": ["60000"], "o": "59000", "v": ["1", "2"], "p": ["59500", "59500"], "h": ["61000", "60500"], "l": ["58000", "58500"]},
            "ETCEUR": {"c": ["20"], "o": "21", "v": ["10", "100"], "p": ["20", "20"], "h": ["22", "22"], "l": ["19", "19"]},
            "USDCEUR": {"c": ["0.9"], "o": "0.9", "v": ["1000", "1000"], "p": ["0.9", "0.9"], "h": ["0.91", "0.91"], "l": ["0.89", "0.89"]},
            "ETHUSD": {"c": ["3000"], "o": "2900", "v": ["10", "10"], "p": ["2950", "2950"], "h": ["3100", "3100"], "l": ["2800", "2800"]},
        }
        rows = build_market_rows(pairs, tickers, quote="EUR")
        self.assertEqual([row["symbol"] for row in rows], ["ETC/EUR", "XBT/EUR"])
        self.assertAlmostEqual(rows[1]["change_24h_pct"], 1.695, places=2)
        self.assertEqual(rows[0]["volume_24h_quote_est"], 2000.0)

    def test_ignores_offline_and_incomplete_pairs(self):
        pairs = {
            "A": {"altname": "AAAEUR", "wsname": "AAA/EUR", "status": "cancel_only"},
            "B": {"altname": "BBBEUR", "wsname": "BBB/EUR", "status": "online"},
        }
        rows = build_market_rows(pairs, {}, quote="EUR")
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
