"""Unit tests for the Supabase paper-state store."""
from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from supabase_state import SupabaseStateStore


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


class SupabaseStateStoreTests(unittest.TestCase):
    def test_load_returns_paper_state_and_revision(self):
        state = {"mode": "paper", "cash": 17.81, "positions": {}}
        with patch("urllib.request.urlopen", return_value=FakeResponse([{"state": state, "revision": 4}])):
            store = SupabaseStateStore("https://example.supabase.co", "server-secret")
            self.assertEqual(store.load(), state)
            self.assertEqual(store.revision, 4)

    def test_save_uses_service_credentials_and_increments_revision(self):
        response = FakeResponse([{"revision": 1}])
        with patch("urllib.request.urlopen", return_value=response) as mocked:
            store = SupabaseStateStore("https://example.supabase.co", "server-secret")
            saved = store.save({"mode": "paper", "cash": 17.81})
        self.assertEqual(saved, 1)
        request = mocked.call_args.args[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Apikey"), "server-secret")
        self.assertIsNone(request.get_header("Authorization"))
        self.assertIn("resolution=merge-duplicates", request.get_header("Prefer"))
        self.assertEqual(json.loads(request.data)["id"], "primary")

    def test_legacy_service_role_jwt_is_sent_as_bearer(self):
        token = "eyJhbGciOiJIUzI1NiJ9.test.signature"
        with patch("urllib.request.urlopen", return_value=FakeResponse([{"revision": 1}])) as mocked:
            store = SupabaseStateStore("https://example.supabase.co", token)
            store.save({"mode": "paper", "cash": 17.81})
        request = mocked.call_args.args[0]
        self.assertEqual(request.get_header("Apikey"), token)
        self.assertEqual(request.get_header("Authorization"), "Bearer " + token)

    def test_non_paper_state_is_rejected(self):
        store = SupabaseStateStore("https://example.supabase.co", "server-secret")
        with self.assertRaises(ValueError):
            store.save({"mode": "live"})

    def test_missing_credentials_are_rejected(self):
        with patch.dict(os.environ, {"SUPABASE_URL": "", "SUPABASE_SECRET_KEY": "", "SUPABASE_SERVICE_ROLE_KEY": ""}):
            with self.assertRaises(ValueError):
                SupabaseStateStore.from_env()


if __name__ == "__main__":
    unittest.main()
