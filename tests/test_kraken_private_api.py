"""Tests for authenticated read-only Kraken Spot API preflight."""
import base64
import hashlib
import hmac
import json
import os
import unittest
from decimal import Decimal
from unittest.mock import patch

from trading import kraken_private as private


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class KrakenPrivateTests(unittest.TestCase):
    def setUp(self):
        self.secret = base64.b64encode(b"test-private-key").decode("ascii")
        self.env = patch.dict(os.environ, {
            "KRAKEN_API_KEY": "test-public-key",
            "KRAKEN_API_SECRET": self.secret,
        })
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_signature_matches_kraken_hmac_sha512_scheme(self):
        nonce = "12345"
        encoded = b"nonce=12345&pair=XBTEUR"
        digest = hashlib.sha256(nonce.encode() + encoded).digest()
        expected = base64.b64encode(
            hmac.new(b"test-private-key", b"/0/private/AddOrder" + digest, hashlib.sha512).digest()
        ).decode("ascii")
        self.assertEqual(
            private._signature("/0/private/AddOrder", encoded, nonce, self.secret),
            expected,
        )

    def test_private_post_sends_signed_form_and_never_logs_credentials(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["body"] = request.data
            captured["timeout"] = timeout
            return FakeResponse({"error": [], "result": {"ok": True}})

        with patch.object(private.urllib.request, "urlopen", side_effect=fake_urlopen):
            result = private._private_post("Balance")
        self.assertEqual(result, {"ok": True})
        self.assertEqual(captured["url"], "https://api.kraken.com/0/private/Balance")
        self.assertIn(b"nonce=", captured["body"])
        self.assertEqual(captured["headers"]["Api-key"], "test-public-key")
        self.assertNotIn(self.secret.encode(), captured["body"])

    def test_rejects_missing_credentials(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(private.KrakenPrivateAPIError):
                private._private_post("Balance")

    def test_rejects_invalid_endpoint(self):
        with self.assertRaises(private.KrakenPrivateAPIError):
            private._private_post("../AddOrder")

    def test_preflight_requires_all_trading_permissions_and_no_withdrawal(self):
        responses = [
            {"permissions": sorted(private.REQUIRED_PERMISSIONS), "apiKeyName": "NOVA"},
            {"ZEUR": "12.5"},
            {"open": {}},
        ]
        with patch.object(private, "_private_post", side_effect=responses):
            result = private.run_read_only_preflight(Decimal("11.2"))
        self.assertTrue(result["connected"])
        self.assertEqual(result["eur_balance_sek_estimate"], "140.00")
        self.assertTrue(result["open_orders_clear"])
        self.assertFalse(result["withdrawals_permission"])
        self.assertFalse(result["orders_enabled"])
        self.assertFalse(result["withdrawals_enabled"])

    def test_preflight_rejects_withdrawal_permission(self):
        responses = [
            {"permissions": sorted(private.REQUIRED_PERMISSIONS | {"withdraw-funds"})}
        ]
        with patch.object(private, "_private_post", side_effect=responses):
            with self.assertRaisesRegex(private.KrakenPrivateAPIError, "uttagsbehörigheter"):
                private.run_read_only_preflight(Decimal("11.2"))

    def test_preflight_rejects_missing_permissions(self):
        with patch.object(private, "_private_post", return_value={"permissions": ["query-funds"]}):
            with self.assertRaisesRegex(private.KrakenPrivateAPIError, "saknar"):
                private.run_read_only_preflight(Decimal("11.2"))

    def test_preflight_flags_existing_open_orders(self):
        responses = [
            {"permissions": sorted(private.REQUIRED_PERMISSIONS)},
            {"ZEUR": "12.5"},
            {"open": {"ORDER-1": {"status": "open"}}},
        ]
        with patch.object(private, "_private_post", side_effect=responses):
            result = private.run_read_only_preflight(Decimal("11.2"))
        self.assertEqual(result["open_orders_count"], 1)
        self.assertFalse(result["open_orders_clear"])



    def test_limit_order_validation_sets_validate_true_and_never_enables_orders(self):
        captured = {}

        def fake_post(endpoint, params=None):
            captured["endpoint"] = endpoint
            captured["params"] = params
            return {"descr": {"order": "buy 0.001 XBT/EUR @ limit"}}

        with patch.object(private, "_private_post", side_effect=fake_post):
            result = private.validate_limit_order(
                pair="XBTEUR", side="buy",
                volume=Decimal("0.001"), price=Decimal("60000"),
            )
        self.assertEqual(captured["endpoint"], "AddOrder")
        self.assertEqual(captured["params"]["validate"], "true")
        self.assertEqual(captured["params"]["ordertype"], "limit")
        self.assertEqual(captured["params"]["timeinforce"], "IOC")
        self.assertNotIn("leverage", captured["params"])
        self.assertTrue(result["validated"])
        self.assertFalse(result["orders_enabled"])
        self.assertFalse(result["withdrawals_enabled"])

    def test_limit_order_validation_rejects_margin_like_pair_and_invalid_values(self):
        with self.assertRaises(private.KrakenPrivateAPIError):
            private.validate_limit_order(
                pair="XBT/EUR", side="buy",
                volume=Decimal("0.001"), price=Decimal("60000"),
            )
        with self.assertRaises(private.KrakenPrivateAPIError):
            private.validate_limit_order(
                pair="XBTEUR", side="buy",
                volume=Decimal("0"), price=Decimal("60000"),
            )


    def test_live_submit_requires_explicit_server_gate(self):
        with (
            patch.dict(os.environ, {"TRADE_LIVE_ENABLED": "false"}),
            patch.object(private, "_private_post") as post,
            self.assertRaises(private.KrakenPrivateAPIError),
        ):
            private.submit_limit_order(
                pair="LINKEUR", side="buy", volume=Decimal("1"),
                price=Decimal("8.4"), client_order_id="a" * 32,
            )
        post.assert_not_called()

    def test_live_submit_sends_spot_limit_ioc_without_leverage(self):
        with (
            patch.dict(os.environ, {"TRADE_LIVE_ENABLED": "true"}),
            patch.object(private, "_private_post", return_value={"txid": ["ORDER-1"]}) as post,
        ):
            result = private.submit_limit_order(
                pair="LINKEUR", side="buy", volume=Decimal("1.2"),
                price=Decimal("8.4"), client_order_id="a" * 32,
            )
        params = post.call_args.args[1]
        self.assertEqual(post.call_args.args[0], "AddOrder")
        self.assertEqual(params["ordertype"], "limit")
        self.assertEqual(params["timeinforce"], "IOC")
        self.assertEqual(params["oflags"], "fciq")
        self.assertEqual(params["validate"] if "validate" in params else None, None)
        self.assertNotIn("leverage", params)
        self.assertEqual(result["txid"], "ORDER-1")
        self.assertEqual(result["mode"], "live_spot")

    def test_order_lookup_checks_open_then_closed_by_client_id(self):
        responses = [
            {"open": {}},
            {"closed": {"ORDER-2": {
                "status": "closed", "vol_exec": "1.2", "cost": "10.08", "fee": "0.04",
            }}},
        ]
        with patch.object(private, "_private_post", side_effect=responses) as post:
            order = private.lookup_order_by_client_id("b" * 32)
        self.assertEqual([call.args[0] for call in post.call_args_list], ["OpenOrders", "ClosedOrders"])
        self.assertEqual(order["txid"], "ORDER-2")
        self.assertEqual(order["order_collection"], "closed")
        self.assertEqual(order["vol_exec"], "1.2")

    def test_query_order_by_txid_returns_authoritative_fill_totals(self):
        with patch.object(private, "_private_post", return_value={
            "ORDER123": {
                "status": "closed", "vol": "2", "vol_exec": "1.5",
                "cost": "12.3", "fee": "0.05", "price": "8.2",
                "trades": ["TRADE1"],
            }
        }) as post:
            order = private.query_order_by_txid("ORDER123")
        post.assert_called_once_with("QueryOrders", {"txid": "ORDER123", "trades": "true"})
        self.assertEqual(order["vol_exec"], "1.5")
        self.assertEqual(order["cost"], "12.3")
        self.assertEqual(order["fee"], "0.05")
        self.assertEqual(order["status"], "closed")

    def test_query_order_by_txid_rejects_bad_reference(self):
        with patch.object(private, "_private_post") as post:
            with self.assertRaises(private.KrakenPrivateAPIError):
                private.query_order_by_txid("bad-order-id!")
        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
