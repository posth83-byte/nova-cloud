"""Endpoint-level tests for the safe Trade AI API."""
import asyncio
import importlib.util
import unittest
from decimal import Decimal
from unittest.mock import patch

if importlib.util.find_spec("fastapi") is None:
    raise unittest.SkipTest("FastAPI is installed in the app validation environment, not lightweight unit jobs")

from fastapi import HTTPException
from starlette.requests import Request

from trading import api
from trading.paper_engine import create_initial_state


class TradingApiTests(unittest.TestCase):
    def test_live_dashboard_requires_separate_read_key(self):
        with patch.dict("os.environ", {"TRADE_DASHBOARD_TOKEN": "read-only-secret"}):
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(api.live_dashboard(request=Request({"type": "http", "headers": []}), x_trade_dashboard_token="wrong"))
        self.assertEqual(raised.exception.status_code, 401)

    def test_live_dashboard_returns_private_account_and_live_filled_positions(self):
        state = {
            "enabled": True, "emergency_stop": False, "cash_sek": "100.00",
            "positions": {"XBT/EUR": {"quantity": "0.001", "cost_basis_sek": "500000", "base_asset": "XXBT"}},
            "realized_pnl_sek": "2.50", "day_start_equity_sek": "110.00",
            "trades": [], "worker": {"last_success_at": "2026-11-26T12:00:00+00:00"},
            "risk": {"max_open_positions": 3, "daily_loss_limit_pct": "0.02"},
        }
        fx = {"rate": 11.2, "date": "2026-11-26", "source": "test"}
        account = {"connected": True, "eur_balance": "10", "open_orders_count": 0}
        valuation = {
            "total_eur": 70.0, "total_sek": 784.0, "valuation_complete": True,
            "unpriced_assets": [],
            "assets": [
                {"asset": "ZEUR", "symbol": "EUR", "balance": 10.0, "price_eur": 1.0, "value_eur": 10.0, "value_sek": 112.0},
                {"asset": "XXBT", "symbol": "XBT/EUR", "balance": 0.001, "price_eur": 60000.0, "value_eur": 60.0, "value_sek": 672.0},
            ],
        }
        radar = {"candidates": [{"symbol": "XBT/EUR", "change_24h_pct": 1.0, "spread_pct": 0.1}]}
        with (
            patch.dict("os.environ", {"TRADE_DASHBOARD_TOKEN": "read-only-secret"}),
            patch.object(api, "load_or_create_live_state", return_value=(state, 5)),
            patch.object(api, "fetch_eur_sek_rate", return_value=fx),
            patch.object(api, "run_read_only_preflight", return_value=account),
            patch.object(api, "get_account_balances", return_value={"ZEUR": "10", "XXBT": "0.001"}),
            patch.object(api, "value_account_balances", return_value=valuation),
            patch.object(api, "scan_markets", return_value={"markets": []}),
            patch.object(api, "rank_opportunities", return_value=radar),
            patch.object(api, "list_recent_order_intents", return_value=[]),
            patch.object(api, "get_recent_closed_orders", return_value=[]),
        ):
            result = asyncio.run(api.live_dashboard(request=Request({"type": "http", "headers": []}), x_trade_dashboard_token="read-only-secret"))
        self.assertEqual(result["account"]["total_value_sek"], 784.0)
        self.assertEqual(result["account"]["available_eur"], "10")
        self.assertTrue(result["trade_ai"]["live_enabled"])
        self.assertEqual(result["trade_ai"]["positions"][0]["market_value_sek"], "672.00")
        self.assertEqual(result["opportunities"][0]["symbol"], "XBT/EUR")
        self.assertFalse(result["orders_enabled"])
        self.assertFalse(result["withdrawals_enabled"])

    def test_status_is_read_only_paper_mode(self):
        result = asyncio.run(api.trading_status())
        self.assertEqual(result["status"], "online")
        self.assertEqual(result["mode"], "paper_only")
        self.assertFalse(result["orders_enabled"])
        self.assertFalse(result["withdrawals_enabled"])

    def test_markets_endpoint_returns_public_scanner_result(self):
        expected = {"quote": "EUR", "markets": [{"symbol": "XBTEUR"}]}
        with patch.object(api, "scan_markets", return_value=expected):
            result = asyncio.run(api.trading_markets(quote="EUR", limit=1))
        self.assertEqual(result, expected)

    def test_paper_status_reports_safe_sek_ledger(self):
        state = create_initial_state("200.00")
        with patch.object(api, "_load", return_value=(state, 1)):
            result = asyncio.run(api.paper_status())
        self.assertEqual(result["cash"], "200.00")
        self.assertEqual(result["starting_cash"], "200.00")
        self.assertEqual(result["currency"], "SEK")
        self.assertFalse(result["paper_enabled"])
        self.assertFalse(result["orders_enabled"])
        self.assertFalse(result["withdrawals_enabled"])
        self.assertEqual(result["storage"], "supabase")
        self.assertEqual(result["revision"], 1)

    def test_paper_status_values_positions_from_recent_worker_marks(self):
        from datetime import datetime, timezone
        state = create_initial_state("200.00")
        state["positions"] = {"XBT/EUR": {"quantity": "0.001", "cost_basis": "50000"}}
        state["cash"] = "150.00"
        state["worker"] = {
            "last_marked_at": datetime.now(timezone.utc).isoformat(),
            "last_marks_sek": {"XBT/EUR": 60000.0},
        }
        with patch.object(api, "_load", return_value=(state, 3)):
            result = asyncio.run(api.paper_status())
        self.assertEqual(result["equity"], "210.00")
        self.assertEqual(result["valuation_status"], "complete")

    def test_paper_status_handles_positions_without_fresh_sek_marks(self):
        state = create_initial_state("200.00")
        state["positions"] = {"XBT/EUR": {"quantity": "0.001", "cost_basis": "500000"}}
        with patch.object(api, "_load", return_value=(state, 2)):
            result = asyncio.run(api.paper_status())
        self.assertIsNone(result["equity"])
        self.assertEqual(result["valuation_status"], "awaiting_fresh_sek_market_marks")
        self.assertFalse(result["orders_enabled"])

    def test_strategy_preview_is_read_only_and_uses_sek_fx(self):
        state = create_initial_state("200.00")
        market = {"markets": [{
            "symbol": "XBT/EUR", "ask": 60000, "bid": 59900,
            "spread_pct": 0.1668, "volume_24h_quote_est": 500000,
            "min_cost_quote": 0.5, "min_order_qty": 0.0001,
        }]}
        fx = {"rate": 11.2, "age_days": 1, "date": "2026-11-25", "source": "test"}
        with (
            patch.object(api, "_load", return_value=(state, 1)),
            patch.object(api, "fetch_eur_sek_rate", return_value=fx),
            patch.object(api, "scan_markets", return_value=market),
        ):
            result = asyncio.run(api.paper_strategy_preview())
        self.assertEqual(result["mode"], "paper_preview_only")
        self.assertFalse(result["execution_enabled"])
        self.assertEqual(result["max_trade_budget_sek"], 200.0)
        self.assertEqual(result["candidate_count"], 1)

    def test_opportunities_endpoint_is_read_only(self):
        state = {
            "starting_cash": "200.00", "cash": "200.00",
            "worker": {},
        }
        market_data = {"markets": [{
            "symbol": "XBT/EUR", "ask": 60000, "bid": 59940,
            "spread_pct": 0.1, "volume_24h_quote_est": 500000,
            "change_24h_pct": 4.2, "high_24h": 62000, "low_24h": 58000,
            "last": 60000, "min_order_qty": 0.0001, "min_cost_quote": 0.5,
        }]}
        fx = {"rate": 11.2, "age_days": 1, "date": "2026-11-25", "source": "test"}
        with (
            patch.object(api, "_load", return_value=(state, 1)),
            patch.object(api, "fetch_eur_sek_rate", return_value=fx),
            patch.object(api, "scan_markets", return_value=market_data),
        ):
            result = asyncio.run(api.trading_opportunities(limit=5))
        self.assertEqual(result["mode"], "opportunity_radar")
        self.assertFalse(result["execution_enabled"])
        self.assertFalse(result["orders_enabled"])
        self.assertFalse(result["withdrawals_enabled"])
        self.assertEqual(result["paper_balance_sek"], 200.0)
        self.assertEqual(result["eligible_count"], 1)

    def test_historical_backtest_endpoint_is_read_only(self):
        state = create_initial_state("200.00")
        history = {
            "candles": [
                {"timestamp": 1_700_000_000 + i * 3600, "close": 100 + i * 0.1}
                for i in range(120)
            ],
            "min_order_qty": 1000,
            "min_cost_eur": 0.5,
        }
        market = {"markets": [{"symbol": "XBT/EUR", "spread_pct": 0.2}]}
        fx = {"rate": 11.2, "date": "2026-11-25", "source": "test"}
        with (
            patch.object(api, "_load", return_value=(state, 1)),
            patch.object(api, "fetch_ohlc_candles", return_value=history),
            patch.object(api, "scan_markets", return_value=market),
            patch.object(api, "fetch_eur_sek_rate", return_value=fx),
        ):
            result = asyncio.run(api.paper_backtest(pair="XBT/EUR"))
        self.assertEqual(result["mode"], "historical_backtest_only")
        self.assertFalse(result["orders_enabled"])
        self.assertFalse(result["withdrawals_enabled"])
        self.assertEqual(result["market"], "XBT/EUR")
        self.assertEqual(result["results"]["closed_trades"], 0)

    def test_paper_worker_tick_requires_control_token_and_runs_simulation(self):
        with (
            patch.dict("os.environ", {"TRADE_CONTROL_TOKEN": "worker-secret"}),
            patch.object(api, "run_paper_tick", return_value={"ok": True, "orders_enabled": False}) as run,
        ):
            result = asyncio.run(api.paper_worker_tick(x_trade_control_token="worker-secret"))
        self.assertTrue(result["ok"])
        run.assert_called_once_with()

    def test_paper_worker_tick_accepts_verified_github_oidc(self):
        with (
            patch.object(api, "_github_actions_guard") as guard,
            patch.object(api, "run_paper_tick", return_value={"ok": True}) as run,
        ):
            result = asyncio.run(api.paper_worker_tick(
                x_trade_control_token=None, authorization="Bearer short-lived-oidc"
            ))
        self.assertTrue(result["ok"])
        guard.assert_called_once_with("Bearer short-lived-oidc")
        run.assert_called_once_with()

    def test_paper_start_requires_manual_github_dispatch_when_using_oidc(self):
        state = create_initial_state("200.00")
        with (
            patch.object(api, "_github_actions_guard") as guard,
            patch.object(api, "_load", return_value=(state, 2)),
            patch.object(api, "_save", return_value=3),
        ):
            result = asyncio.run(api.paper_start(
                x_trade_control_token=None, authorization="Bearer short-lived-oidc"
            ))
        self.assertTrue(result["paper_enabled"])
        guard.assert_called_once_with("Bearer short-lived-oidc", manual_start=True)

    def test_paper_pause_accepts_verified_github_dispatch(self):
        state = create_initial_state("200.00")
        state["paper_enabled"] = True
        with (
            patch.object(api, "_github_actions_guard") as guard,
            patch.object(api, "_load", return_value=(state, 3)),
            patch.object(api, "_save", return_value=4),
        ):
            result = asyncio.run(api.paper_pause(
                x_trade_control_token=None, authorization="Bearer short-lived-oidc"
            ))
        self.assertFalse(result["paper_enabled"])
        guard.assert_called_once_with("Bearer short-lived-oidc", manual_start=True)

    def test_emergency_stop_accepts_verified_github_dispatch(self):
        state = create_initial_state("200.00")
        state["paper_enabled"] = True
        with (
            patch.object(api, "_github_actions_guard") as guard,
            patch.object(api, "_load", return_value=(state, 3)),
            patch.object(api, "_save", return_value=4),
        ):
            result = asyncio.run(api.paper_emergency_stop(
                reason="manual test", x_trade_control_token=None,
                authorization="Bearer short-lived-oidc"
            ))
        self.assertTrue(result["emergency_stop"])
        guard.assert_called_once_with("Bearer short-lived-oidc", manual_start=True)

    def test_control_guard_fails_closed_when_token_missing(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(HTTPException) as exc:
                api._control_guard("anything")
        self.assertEqual(exc.exception.status_code, 503)

    def test_control_guard_rejects_wrong_token(self):
        with patch.dict("os.environ", {"TRADE_CONTROL_TOKEN": "expected-secret"}):
            with self.assertRaises(HTTPException) as exc:
                api._control_guard("wrong-secret")
        self.assertEqual(exc.exception.status_code, 401)

    def test_paper_start_requires_guard_and_persists_state(self):
        state = create_initial_state("200.00")
        saved = []
        with (
            patch.dict("os.environ", {"TRADE_CONTROL_TOKEN": "expected-secret"}),
            patch.object(api, "_load", return_value=(state, 4)),
            patch.object(api, "_save", side_effect=lambda updated, revision: saved.append((updated, revision)) or 5),
        ):
            result = asyncio.run(api.paper_start(x_trade_control_token="expected-secret"))
        self.assertTrue(result["paper_enabled"])
        self.assertFalse(result["orders_enabled"])
        self.assertTrue(saved[0][0]["paper_enabled"])
        self.assertEqual(saved[0][1], 4)

    def test_pause_persists_disabled_state(self):
        state = create_initial_state("200.00")
        state["paper_enabled"] = True
        saved = []
        with (
            patch.dict("os.environ", {"TRADE_CONTROL_TOKEN": "expected-secret"}),
            patch.object(api, "_load", return_value=(state, 5)),
            patch.object(api, "_save", side_effect=lambda updated, revision: saved.append(updated) or 6),
        ):
            result = asyncio.run(api.paper_pause(x_trade_control_token="expected-secret"))
        self.assertFalse(result["paper_enabled"])
        self.assertFalse(saved[0]["paper_enabled"])

    def test_emergency_stop_disables_paper_and_persists_reason(self):
        state = create_initial_state("200.00")
        state["paper_enabled"] = True
        saved = []
        with (
            patch.dict("os.environ", {"TRADE_CONTROL_TOKEN": "expected-secret"}),
            patch.object(api, "_load", return_value=(state, 6)),
            patch.object(api, "_save", side_effect=lambda updated, revision: saved.append(updated) or 7),
        ):
            result = asyncio.run(api.paper_emergency_stop(
                reason="test stop", x_trade_control_token="expected-secret"
            ))
        self.assertTrue(result["emergency_stop"])
        self.assertFalse(result["paper_enabled"])
        self.assertTrue(saved[0]["emergency_stop"])
        self.assertEqual(saved[0]["stop_reason"], "test stop")



    def test_live_worker_tick_requires_scheduler_identity_and_runs_worker(self):
        with (
            patch.object(api, "_github_actions_guard") as guard,
            patch.object(api, "run_live_tick", return_value={
                "ok": True, "status": "disabled", "live_enabled": False,
                "orders_enabled": False, "withdrawals_enabled": False,
            }) as worker,
        ):
            result = asyncio.run(api.live_worker_tick(
                x_trade_control_token=None, authorization="Bearer oidc"
            ))
        guard.assert_called_once()
        self.assertIn(
            "posth83-byte/nova-cloud/.github/workflows/trade-live-scheduler-v2.yml@refs/heads/main",
            guard.call_args.kwargs["allowed_workflows"],
        )
        worker.assert_called_once()
        self.assertFalse(result["live_enabled"])
        self.assertFalse(result["orders_enabled"])

    def test_live_worker_tick_rejects_bad_manual_control_token(self):
        with patch.object(api, "_control_guard", side_effect=HTTPException(status_code=401)):
            with self.assertRaises(HTTPException):
                asyncio.run(api.live_worker_tick(x_trade_control_token="wrong"))

    def test_live_status_reads_separate_default_off_ledger(self):
        state = {
            "enabled": False, "emergency_stop": False, "cash_sek": "200.00",
            "positions": {}, "realized_pnl_sek": "0.00", "risk": {},
            "worker": {"status": "disabled"},
        }
        with (
            patch.dict("os.environ", {"TRADE_LIVE_ENABLED": "false"}),
            patch.object(api, "credentials_configured", return_value=True),
            patch.object(api, "load_or_create_live_state", return_value=(state, 1)),
        ):
            result = asyncio.run(api.live_status())
        self.assertTrue(result["credentials_configured"])
        self.assertEqual(result["live_order_engine"], "guarded_autonomous_spot_worker")
        self.assertFalse(result["live_enabled"])
        self.assertFalse(result["orders_enabled"])
        self.assertFalse(result["withdrawals_enabled"])
        self.assertEqual(result["budget_policy"], "all_available_kraken_eur_balance")

    def test_live_status_reports_orders_enabled_only_when_all_gates_are_ready(self):
        state = {
            "enabled": True, "emergency_stop": False, "cash_sek": "200.00",
            "positions": {}, "realized_pnl_sek": "0.00", "risk": {},
            "worker": {"status": "running"},
        }
        with (
            patch.dict("os.environ", {"TRADE_LIVE_ENABLED": "true"}),
            patch.object(api, "credentials_configured", return_value=True),
            patch.object(api, "load_or_create_live_state", return_value=(state, 2)),
        ):
            result = asyncio.run(api.live_status())
        self.assertEqual(result["mode"], "live_spot")
        self.assertTrue(result["server_gate_enabled"])
        self.assertTrue(result["orders_enabled"])

    def test_live_start_refuses_when_server_gate_is_off(self):
        with (
            patch.object(api, "_manual_control_guard"),
            patch.dict("os.environ", {"TRADE_LIVE_ENABLED": "false"}),
            patch.object(api, "run_read_only_preflight") as preflight,
        ):
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(api.live_start(x_trade_control_token="secret"))
        self.assertEqual(raised.exception.status_code, 409)
        preflight.assert_not_called()

    def test_live_start_arms_only_after_server_gate_and_clean_preflight(self):
        state = {"enabled": False, "emergency_stop": False, "worker": {}}
        with (
            patch.object(api, "_github_actions_guard") as guard,
            patch.dict("os.environ", {"TRADE_LIVE_ENABLED": "true"}),
            patch.object(api, "load_or_create_live_state", return_value=(state, 7)),
            patch.object(api, "fetch_eur_sek_rate", return_value={"rate": 11.2}),
            patch.object(api, "run_read_only_preflight", return_value={
                "connected": True, "open_orders_clear": True,
            }),
            patch.object(api, "save_live_state", return_value=8) as save,
        ):
            result = asyncio.run(api.live_start(
                x_trade_control_token=None, authorization="Bearer oidc"
            ))
        self.assertTrue(result["live_enabled"])
        self.assertEqual(result["budget_policy"], "all_available_kraken_eur_balance")
        self.assertFalse(result["withdrawals_enabled"])
        self.assertTrue(state["enabled"])
        self.assertEqual(state["worker"]["status"], "armed")
        save.assert_called_once_with(state, 7)
        guard.assert_called_once()
        self.assertTrue(guard.call_args.kwargs["manual_start"])
        self.assertIn(
            "posth83-byte/nova-cloud/.github/workflows/trade-live-scheduler.yml@refs/heads/main",
            guard.call_args.kwargs["allowed_workflows"],
        )
        self.assertIn(
            "posth83-byte/nova-cloud/.github/workflows/trade-live-scheduler-v2.yml@refs/heads/main",
            guard.call_args.kwargs["allowed_workflows"],
        )

    def test_live_start_requires_clean_kraken_preflight(self):
        state = {"enabled": False, "emergency_stop": False, "worker": {}}
        with (
            patch.object(api, "_manual_control_guard"),
            patch.dict("os.environ", {"TRADE_LIVE_ENABLED": "true"}),
            patch.object(api, "load_or_create_live_state", return_value=(state, 7)),
            patch.object(api, "fetch_eur_sek_rate", return_value={"rate": 11.0}),
            patch.object(api, "run_read_only_preflight", return_value={
                "connected": True, "open_orders_clear": False,
            }),
            patch.object(api, "save_live_state") as save,
        ):
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(api.live_start(x_trade_control_token="secret"))
        self.assertEqual(raised.exception.status_code, 409)
        save.assert_not_called()

    def test_live_pause_persists_disabled_state(self):
        state = {"enabled": True, "worker": {"status": "running"}}
        saved = []
        with (
            patch.object(api, "_control_guard"),
            patch.object(api, "load_or_create_live_state", return_value=(state, 3)),
            patch.object(api, "save_live_state", side_effect=lambda updated, revision: saved.append(updated) or 4),
        ):
            result = asyncio.run(api.live_pause(x_trade_control_token="secret"))
        self.assertFalse(result["live_enabled"])
        self.assertFalse(saved[0]["enabled"])
        self.assertEqual(saved[0]["worker"]["status"], "paused")
        self.assertFalse(result["open_exchange_orders_cancelled"])

    def test_live_emergency_stop_is_durable_and_disables_worker(self):
        state = {"enabled": True, "emergency_stop": False, "worker": {"status": "running"}}
        saved = []
        with (
            patch.object(api, "_control_guard"),
            patch.object(api, "load_or_create_live_state", return_value=(state, 5)),
            patch.object(api, "save_live_state", side_effect=lambda updated, revision: saved.append(updated) or 6),
        ):
            result = asyncio.run(api.live_emergency_stop(
                reason="test stop", x_trade_control_token="secret"
            ))
        self.assertTrue(result["emergency_stop"])
        self.assertFalse(saved[0]["enabled"])
        self.assertTrue(saved[0]["emergency_stop"])
        self.assertEqual(saved[0]["stop_reason"], "test stop")

    def test_live_preflight_requires_control_token(self):
        with (
            patch.dict("os.environ", {"TRADE_CONTROL_TOKEN": "expected-secret"}),
            self.assertRaises(HTTPException) as exc,
        ):
            asyncio.run(api.live_preflight(x_trade_control_token="wrong"))
        self.assertEqual(exc.exception.status_code, 401)

    def test_live_preflight_is_read_only_and_returns_no_order_capability(self):
        result_data = {
            "connected": True,
            "eur_balance": "10.0",
            "eur_balance_sek_estimate": "112.00",
            "open_orders_count": 0,
            "open_orders_clear": True,
            "orders_enabled": False,
            "withdrawals_enabled": False,
        }
        fx = {"rate": 11.2, "date": "2026-11-26", "source": "test", "age_days": 0}
        with (
            patch.dict("os.environ", {"TRADE_CONTROL_TOKEN": "expected-secret"}),
            patch.object(api, "fetch_eur_sek_rate", return_value=fx),
            patch.object(api, "run_read_only_preflight", return_value=result_data) as preflight,
        ):
            result = asyncio.run(api.live_preflight(x_trade_control_token="expected-secret"))
        preflight.assert_called_once()
        self.assertTrue(result["connected"])
        self.assertFalse(result["orders_enabled"])
        self.assertFalse(result["withdrawals_enabled"])
        self.assertEqual(result["fx_reference"]["date"], "2026-11-26")



    def test_live_validate_order_uses_full_kraken_eur_balance_and_never_submits(self):
        fx = {"rate": 11.2, "date": "2026-11-26", "source": "test", "age_days": 0}
        account = {"eur_balance": "36.0", "open_orders_clear": True}
        markets = {"markets": [{
            "symbol": "XBT/EUR", "api_pair": "XBTEUR", "ask": 60000.0,
            "bid": 59940.0, "spread_pct": 0.1, "volume_24h_quote_est": 500000.0,
            "change_24h_pct": 4.2, "high_24h": 62000.0, "low_24h": 58000.0,
            "last": 60000.0, "min_order_qty": 0.0001, "min_cost_quote": 0.5,
            "price_decimals": 1, "lot_decimals": 8,
        }]}
        radar = {"candidates": [{"symbol": "XBT/EUR", "score": 82.0, "buy_signal": False}]}
        validated = {"validated": True, "orders_enabled": False, "withdrawals_enabled": False}
        with (
            patch.object(api, "_control_guard"),
            patch.object(api, "fetch_eur_sek_rate", return_value=fx),
            patch.object(api, "run_read_only_preflight", return_value=account),
            patch.object(api, "scan_markets", return_value=markets),
            patch.object(api, "rank_opportunities", return_value=radar) as rank,
            patch.object(api, "validate_limit_order", return_value=validated) as validate,
        ):
            result = asyncio.run(api.live_validate_order(x_trade_control_token="expected-secret"))
        validate.assert_called_once()
        rank.assert_called_once()
        self.assertAlmostEqual(rank.call_args.kwargs["equity_sek"], 403.2)
        kwargs = validate.call_args.kwargs
        self.assertEqual(kwargs["pair"], "XBTEUR")
        self.assertEqual(kwargs["side"], "buy")
        self.assertLessEqual(
            Decimal(kwargs["volume"]) * Decimal(kwargs["price"]) * Decimal("1.005506") * Decimal("11.2"),
            Decimal("403.21"),
        )
        self.assertGreater(Decimal(kwargs["volume"]) * Decimal(kwargs["price"]) * Decimal("1.005506") * Decimal("11.2"), Decimal("200.00"))
        self.assertTrue(result["validated"])
        self.assertFalse(result["orders_enabled"])
        self.assertFalse(result["withdrawals_enabled"])

    def test_live_validate_order_refuses_existing_open_orders(self):
        with (
            patch.object(api, "_control_guard"),
            patch.object(api, "fetch_eur_sek_rate", return_value={"rate": 11.2}),
            patch.object(api, "run_read_only_preflight", return_value={
                "eur_balance": "19.0", "open_orders_clear": False,
            }),
            self.assertRaises(HTTPException) as exc,
        ):
            asyncio.run(api.live_validate_order(x_trade_control_token="expected-secret"))
        self.assertEqual(exc.exception.status_code, 409)

if __name__ == "__main__":
    unittest.main()
