"""Safety and accounting tests for autonomous live worker."""
import unittest
from decimal import Decimal
from unittest.mock import patch

from trading import live_worker


class LiveWorkerTests(unittest.TestCase):
    def setUp(self):
        self.state = {
            "enabled": True,
            "emergency_stop": False,
            "cash_sek": "200.00",
            "positions": {},
            "trades": [],
            "realized_pnl_sek": "0.00",
            "applied_order_ids": [],
            "risk": {
                "max_budget_sek": "200.00",
                "daily_loss_limit_pct": "0.02",
                "max_drawdown_pct": "0.10",
                "max_open_positions": 3,
                "fee_rate": "0.0040",
                "slippage_rate": "0.0015",
            },
            "peak_equity_sek": "200.00",
            "day_key": None,
            "day_start_equity_sek": "200.00",
            "worker": {},
        }

    def test_confirmed_buy_fill_updates_live_cash_and_cost_basis(self):
        intent = {
            "client_order_id": "a" * 32,
            "pair_symbol": "LINK/EUR",
            "base_asset": "LINK",
            "side": "buy",
            "exchange_result": {
                "vol_exec": "2", "cost": "10", "fee": "0.04",
            },
        }
        updated = live_worker._apply_intent_fill(
            self.state, intent, Decimal("11")
        )
        self.assertEqual(updated["cash_sek"], "89.56")
        self.assertEqual(updated["positions"]["LINK/EUR"]["quantity"], "2")
        self.assertEqual(updated["positions"]["LINK/EUR"]["cost_basis_sek"], "55.22")
        self.assertIn("a" * 32, updated["applied_order_ids"])

    def test_confirmed_sell_fill_updates_realized_profit(self):
        self.state["cash_sek"] = "100.00"
        self.state["positions"] = {
            "LINK/EUR": {
                "quantity": "2", "cost_basis_sek": "55.22", "base_asset": "LINK"
            }
        }
        intent = {
            "client_order_id": "b" * 32,
            "pair_symbol": "LINK/EUR",
            "side": "sell",
            "exchange_result": {
                "vol_exec": "2", "cost": "12", "fee": "0.05",
            },
        }
        updated = live_worker._apply_intent_fill(
            self.state, intent, Decimal("11")
        )
        self.assertEqual(updated["cash_sek"], "231.45")
        self.assertEqual(updated["positions"], {})
        self.assertEqual(updated["realized_pnl_sek"], "21.01")

    def test_fill_replay_is_idempotent(self):
        intent = {
            "client_order_id": "c" * 32,
            "pair_symbol": "LINK/EUR",
            "side": "buy",
            "exchange_result": {"vol_exec": "1", "cost": "5", "fee": "0.02"},
        }
        once = live_worker._apply_intent_fill(self.state, intent, Decimal("11"))
        twice = live_worker._apply_intent_fill(once, intent, Decimal("11"))
        self.assertEqual(twice["cash_sek"], once["cash_sek"])
        self.assertEqual(twice["positions"], once["positions"])
        self.assertEqual(len(twice["trades"]), 1)

    def test_unresolved_order_stops_worker_recovery_without_resubmission(self):
        row = {
            "client_order_id": "d" * 32,
            "status": "unknown",
        }
        with (
            patch.object(live_worker, "list_unapplied_order_intents", return_value=[row]),
            patch.object(live_worker, "reconcile_order_intent", return_value={
                "status": "unknown", "resubmit": False
            }) as reconcile,
        ):
            with self.assertRaisesRegex(live_worker.LiveWorkerError, "okänt eller öppet"):
                live_worker._recover_unapplied(self.state, 1, Decimal("11"))
        reconcile.assert_called_once()

    def test_disabled_live_state_does_not_contact_kraken(self):
        state = dict(self.state)
        state["enabled"] = False
        with (
            patch.object(live_worker, "load_or_create_live_state", return_value=(state, 2)),
            patch.object(live_worker, "run_read_only_preflight") as preflight,
            patch.object(live_worker, "scan_markets") as markets,
        ):
            result = live_worker.run_live_tick()
        self.assertEqual(result["status"], "disabled")
        preflight.assert_not_called()
        markets.assert_not_called()


if __name__ == "__main__":
    unittest.main()
