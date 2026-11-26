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
        with patch.dict("os.environ", {"TRADE_CONTROL_TOKEN": "expected-secret"}), \
             patch.object(api, "_load", return_value=(state, 4)), \
             patch.object(api, "_save", side_effect=lambda updated, revision: saved.append((updated, revision)) or 5):
            result = asyncio.run(api.paper_start(x_trade_control_token="expected-secret"))
        self.assertTrue(result["paper_enabled"])
        self.assertFalse(result["orders_enabled"])
        self.assertTrue(saved[0][0]["paper_enabled"])
        self.assertEqual(saved[0][1], 4)

    def test_pause_persists_disabled_state(self):
        state = create_initial_state("200.00")
        state["paper_enabled"] = True
        saved = []
        with patch.dict("os.environ", {"TRADE_CONTROL_TOKEN": "expected-secret"}), \
             patch.object(api, "_load", return_value=(state, 5)), \
             patch.object(api, "_save", side_effect=lambda updated, revision: saved.append(updated) or 6):
            result = asyncio.run(api.paper_pause(x_trade_control_token="expected-secret"))
        self.assertFalse(result["paper_enabled"])
        self.assertFalse(saved[0]["paper_enabled"])

    def test_emergency_stop_disables_paper_and_persists_reason(self):
        state = create_initial_state("200.00")
        state["paper_enabled"] = True
        saved = []
        with patch.dict("os.environ", {"TRADE_CONTROL_TOKEN": "expected-secret"}), \
             patch.object(api, "_load", return_value=(state, 6)), \
             patch.object(api, "_save", side_effect=lambda updated, revision: saved.append(updated) or 7):
            result = asyncio.run(api.paper_emergency_stop(
                reason="test stop", x_trade_control_token="expected-secret"
            ))
        self.assertTrue(result["emergency_stop"])
        self.assertFalse(result["paper_enabled"])
        self.assertTrue(saved[0]["emergency_stop"])
        self.assertEqual(saved[0]["stop_reason"], "test stop")


if __name__ == "__main__":
    unittest.main()
