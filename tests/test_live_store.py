"""Tests for the isolated persistent live order journal."""
import json
import unittest
from unittest.mock import patch

from trading import live_store


class FakeResponse:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.value).encode()


class LiveStoreTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict("os.environ", {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "not-a-real-key",
        })
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_initial_live_ledger_is_separate_and_disabled_by_default(self):
        state = live_store.create_initial_live_state()
        self.assertEqual(state["mode"], "live_spot")
        self.assertFalse(state["enabled"])
        self.assertFalse(state["emergency_stop"])
        self.assertEqual(state["cash_sek"], "200.00")
        self.assertEqual(state["risk"]["max_budget_sek"], "200.00")
        self.assertNotIn("paper_enabled", state)

    def test_live_state_initialization_persists_revision_one(self):
        with patch.object(live_store, "load_live_state", return_value=(None, 0)), \
             patch.object(live_store, "save_live_state", return_value=1) as save:
            state, revision = live_store.load_or_create_live_state()
        self.assertFalse(state["enabled"])
        self.assertEqual(revision, 1)
        save.assert_called_once_with(state, 0)

    def test_order_intent_is_persisted_before_submission_payload(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data)
            captured["method"] = request.method
            return FakeResponse([captured["body"]])

        with patch.object(live_store.urllib.request, "urlopen", side_effect=fake_urlopen):
            row = live_store.create_order_intent(
                intent_id="12345678-1234-5678-1234-567812345678",
                client_order_id="a" * 32, pair="LINKEUR", side="buy",
                volume="1.25", limit_price="8.4",
                pair_symbol="LINK/EUR", base_asset="LINK",
            )
        self.assertEqual(captured["method"], "POST")
        self.assertIn("jarvis_live_order_intents", captured["url"])
        self.assertEqual(captured["body"]["status"], "prepared")
        self.assertEqual(captured["body"]["pair_symbol"], "LINK/EUR")
        self.assertEqual(captured["body"]["base_asset"], "LINK")
        self.assertEqual(row["client_order_id"], "a" * 32)

    def test_rejects_invalid_order_intent_before_database_call(self):
        with patch.object(live_store.urllib.request, "urlopen") as post:
            with self.assertRaises(live_store.LiveStoreError):
                live_store.create_order_intent(
                    intent_id="not-a-uuid", client_order_id="b" * 32,
                    pair="LINKEUR", side="buy", volume="1", limit_price="8",
                )
        post.assert_not_called()

    def test_revision_conflict_stops_live_state_overwrite(self):
        with patch.object(live_store, "_request", return_value=[]):
            with self.assertRaisesRegex(live_store.LiveStoreError, "revision"):
                live_store.save_live_state({"mode": "live"}, 4)

    def test_unknown_status_is_rejected(self):
        with patch.object(live_store, "_request") as request:
            with self.assertRaises(live_store.LiveStoreError):
                live_store.update_order_intent("a" * 32, status="retry")
        request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
