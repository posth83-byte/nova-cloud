"""Safety tests for journal-first Kraken order execution."""
import unittest
from decimal import Decimal
from unittest.mock import patch

from trading import live_engine
from trading.kraken_private import KrakenPrivateAPIError
from trading.live_store import LiveStoreError


class LiveEngineTests(unittest.TestCase):
    def test_journal_insert_precedes_single_exchange_submission(self):
        order = []
        def journal(**kwargs):
            order.append("journal")
        def update(*args, **kwargs):
            order.append("state:" + kwargs["status"])
        def submit(**kwargs):
            order.append("exchange")
            return {"txid": "ORDER-1"}
        with (
            patch.object(live_engine, "create_order_intent", side_effect=journal),
            patch.object(live_engine, "update_order_intent", side_effect=update),
            patch.object(live_engine, "submit_limit_order", side_effect=submit),
            patch.object(live_engine, "query_order_by_txid", return_value={
                "status": "closed", "vol_exec": "1", "cost": "8.4", "fee": "0.03"
            }),
        ):
            result = live_engine.execute_journaled_limit_order(
                pair="LINKEUR", side="buy", volume=Decimal("1"),
                price=Decimal("8.4"),
            )
        self.assertEqual(order, ["journal", "state:submitting", "exchange", "state:accepted"])
        self.assertEqual(result["txid"], "ORDER-1")

    def test_exchange_timeout_is_marked_unknown_and_never_retried(self):
        order = []
        def update(*args, **kwargs):
            order.append(kwargs["status"])
        with (
            patch.object(live_engine, "create_order_intent"),
            patch.object(live_engine, "update_order_intent", side_effect=update),
            patch.object(
                live_engine, "submit_limit_order",
                side_effect=KrakenPrivateAPIError("timeout"),
            ) as submit,
            self.assertRaisesRegex(live_engine.LiveExecutionError, "aldrig skickas om"),
        ):
            live_engine.execute_journaled_limit_order(
                pair="LINKEUR", side="buy", volume=Decimal("1"),
                price=Decimal("8.4"),
            )
        self.assertEqual(order, ["submitting", "unknown"])
        submit.assert_called_once()

    def test_failure_to_journal_prevents_exchange_submission(self):
        with (
            patch.object(live_engine, "create_order_intent", side_effect=LiveStoreError("db")),
            patch.object(live_engine, "submit_limit_order") as submit,
            self.assertRaises(LiveStoreError),
        ):
            live_engine.execute_journaled_limit_order(
                pair="LINKEUR", side="buy", volume=Decimal("1"),
                price=Decimal("8.4"),
            )
        submit.assert_not_called()

    def test_unknown_order_not_found_is_never_resubmitted(self):
        with (
            patch.object(live_engine, "get_order_intent", return_value={"status": "unknown"}),
            patch.object(live_engine, "lookup_order_by_client_id", return_value=None),
            patch.object(live_engine, "update_order_intent") as update,
        ):
            result = live_engine.reconcile_order_intent("a" * 32)
        self.assertEqual(result["status"], "unknown")
        self.assertFalse(result["resubmit"])
        update.assert_called_once_with("a" * 32, status="unknown")


if __name__ == "__main__":
    unittest.main()
