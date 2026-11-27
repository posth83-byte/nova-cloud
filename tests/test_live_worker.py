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

    def test_confirmed_buy_reconciliation_uses_actual_exchange_cash_not_stale_ledger(self):
        state = dict(self.state)
        state["cash_sek"] = "212.85"
        intent = {
            "client_order_id": "f" * 32,
            "pair_symbol": "ALGO/EUR",
            "base_asset": "ALGO",
            "side": "buy",
            "exchange_result": {
                "vol_exec": "254.25583355",
                "cost": "18.896294",
                "fee": "0.151170",
            },
        }
        updated = live_worker._apply_intent_fill(
            state, intent, Decimal("11.2025"),
            exchange_cash_sek=Decimal("1.00"),
        )
        self.assertEqual(updated["cash_sek"], "1.00")
        self.assertEqual(
            updated["positions"]["ALGO/EUR"]["quantity"], "254.25583355"
        )
        self.assertEqual(len(updated["trades"]), 1)

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

    def test_active_lease_prevents_second_worker_from_running(self):
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        self.state["worker"] = {
            "lease_id": "already-running",
            "lease_until": (now + timedelta(minutes=2)).isoformat(),
        }
        with patch.object(live_worker, "save_live_state") as save:
            state, revision, lease_id = live_worker._acquire_lease(self.state, 4, now)
        self.assertIsNone(lease_id)
        self.assertEqual(revision, 4)
        save.assert_not_called()

    def test_lease_acquisition_uses_revision_guarded_save(self):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        with patch.object(live_worker, "save_live_state", return_value=8) as save:
            state, revision, lease_id = live_worker._acquire_lease(self.state, 7, now)
        self.assertTrue(lease_id)
        self.assertEqual(revision, 8)
        self.assertEqual(state["worker"]["lease_id"], lease_id)
        save.assert_called_once()

    def test_live_tick_journals_one_approved_momentum_buy_and_books_fill(self):
        state = dict(self.state)
        market = {
            "symbol": "LINK/EUR", "api_pair": "LINKEUR",
            "base_asset": "LINK", "last": 10.0, "ask": 10.0, "bid": 9.99,
            "spread_pct": 0.10, "volume_24h_quote_est": 25000.0,
            "min_order_qty": 0.1, "min_cost_quote": 1.0,
            "price_decimals": 2, "lot_decimals": 4,
        }
        candles = [{"timestamp": 1000 + i * 3600, "close": 10.0} for i in range(40)]
        intent = {
            "client_order_id": "e" * 32,
            "pair_symbol": "LINK/EUR", "base_asset": "LINK", "side": "buy",
            "exchange_result": {"vol_exec": "1", "cost": "10", "fee": "0.04"},
        }
        saved = []
        def save(updated, revision):
            saved.append(dict(updated))
            return revision + 1
        with (
            patch.dict("os.environ", {"TRADE_LIVE_ENABLED": "true"}),
            patch.object(live_worker, "load_or_create_live_state", return_value=(state, 1)),
            patch.object(live_worker, "_acquire_lease", side_effect=lambda s, r, n: (s, r + 1, "lease")),
            patch.object(live_worker, "fetch_eur_sek_rate", return_value={
                "rate": 11.0, "age_days": 0, "date": "2026-11-26",
            }),
            patch.object(live_worker, "run_read_only_preflight", return_value={
                "connected": True, "open_orders_clear": True,
            }),
            patch.object(live_worker, "get_account_balances", side_effect=[
                {"ZEUR": "36.36"}, {"ZEUR": "26.32"},
            ]),
            patch.object(live_worker, "scan_markets", return_value={"markets": [market]}),
            patch.object(live_worker, "fetch_ohlc_candles", return_value={"candles": candles}),
            patch.object(live_worker, "_cross_signal", return_value=(False, False)) as cross_signal,
            patch.object(live_worker, "_momentum_entry_signal", return_value=True) as momentum_signal,
            patch.object(live_worker, "_select_watchlist", return_value=({"LINK/EUR"}, 0)),
            patch.object(live_worker, "list_unapplied_order_intents", return_value=[]),
            patch.object(live_worker, "get_open_orders", return_value={}) as open_orders,
            patch.object(live_worker, "validate_limit_order", return_value={"validated": True}) as validate,
            patch.object(live_worker, "execute_journaled_limit_order", side_effect=lambda **kwargs: (
                self.assertEqual(
                    state["worker"]["processed_candles"]["LINK/EUR"],
                    candles[-1]["timestamp"],
                ) or {
                    "status": "closed", "client_order_id": "e" * 32, "vol_exec": "1",
                }
            )) as execute,
            patch.object(live_worker, "get_order_intent", return_value=intent),
            patch.object(live_worker, "mark_order_ledger_applied") as mark,
            patch.object(live_worker, "save_live_state", side_effect=save),
        ):
            result = live_worker.run_live_tick()
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["status"], "running")
        execute.assert_called_once()
        cross_signal.assert_called_once_with(candles, after_timestamp=0)
        momentum_signal.assert_called_once_with(candles, after_timestamp=0)
        validate.assert_called_once()
        open_orders.assert_called_once()
        kwargs = execute.call_args.kwargs
        self.assertEqual(kwargs["pair"], "LINKEUR")
        self.assertEqual(kwargs["side"], "buy")
        self.assertLessEqual(kwargs["volume"] * kwargs["price"] * Decimal("11"), Decimal("400"))
        mark.assert_called_once_with("e" * 32)
        self.assertEqual(state["positions"]["LINK/EUR"]["quantity"], "1")
        self.assertEqual(state["cash_sek"], "289.52")
        self.assertEqual(result["budget_available_eur"], "36.36")
        self.assertFalse(result["withdrawals_enabled"])

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
