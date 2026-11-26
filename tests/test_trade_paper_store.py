import unittest
from unittest.mock import patch

from trading import paper_store


class PaperStoreConcurrencyTests(unittest.TestCase):
    def test_save_uses_revision_guard_for_existing_state(self):
        with patch.object(paper_store, "_request", return_value=[{"revision": 8}]) as request:
            revision = paper_store.save_state({"cash": "200.00"}, 7)
        self.assertEqual(revision, 8)
        args, kwargs = request.call_args
        self.assertEqual(args[0], "PATCH")
        self.assertIn("revision=eq.7", args[1])
        self.assertEqual(kwargs["payload"]["revision"], 8)

    def test_save_rejects_stale_revision_instead_of_overwriting(self):
        with patch.object(paper_store, "_request", return_value=[]):
            with self.assertRaises(paper_store.PaperStoreError):
                paper_store.save_state({"cash": "190.00"}, 7)

    def test_initial_state_insert_is_not_an_upsert(self):
        with patch.object(paper_store, "_request", return_value=[{"revision": 1}]) as request:
            revision = paper_store.save_state({"cash": "200.00"}, 0)
        self.assertEqual(revision, 1)
        args, kwargs = request.call_args
        self.assertEqual(args[0], "POST")
        self.assertNotIn("resolution=merge-duplicates", kwargs.get("prefer", ""))


if __name__ == "__main__":
    unittest.main()
