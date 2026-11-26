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


if __name__ == "__main__":
    unittest.main()
