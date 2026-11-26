import unittest
from unittest.mock import patch

from trading.kraken_monitor import fetch_ohlc_candles


class KrakenOHLCFetchTests(unittest.TestCase):
    @patch("trading.kraken_monitor._public_get")
    def test_fetches_closed_candles_and_pair_minimums(self, public_get):
        public_get.side_effect = [
            {"XXBTZEUR": {
                "wsname": "XBT/EUR", "altname": "XBTEUR",
                "ordermin": "0.0001", "costmin": "0.5",
            }},
            {"XXBTZEUR": [
                [1700000000, "1", "1", "1", "10", "1", "1", 1],
                [1700003600, "1", "1", "1", "11", "1", "1", 1],
                [1700007200, "1", "1", "1", "12", "1", "1", 1],
            ], "last": 1700010000},
        ]
        result = fetch_ohlc_candles("XBT/EUR")
        self.assertEqual(len(result["candles"]), 2)
        self.assertEqual(result["candles"][-1]["close"], 11.0)
        self.assertEqual(result["min_order_qty"], 0.0001)
        self.assertEqual(result["min_cost_eur"], 0.5)
        self.assertIn("interval=60", public_get.call_args_list[1].args[0])


if __name__ == "__main__":
    unittest.main()
