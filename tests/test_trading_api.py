"""Endpoint-level tests for the safe Trade AI API."""
import asyncio
import importlib.util
import unittest
from unittest.mock import patch

if importlib.util.find_spec("fastapi") is None:
    raise unittest.SkipTest("FastAPI is installed in the app validation environment, not lightweight unit jobs")

from fastapi import HTTPException

from trading import api
from trading.paper_engine import create_initial_state


class TradingApiTests(unittest.TestCase):
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
        self.assertEqual(result["max_trade_budget_sek"], 20.0)
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


if __name__ == "__main__":
    unittest.main()
