"""Endpoint-level tests for the safe Trade AI API."""
import asyncio

import pytest
from fastapi import HTTPException

from trading import api
from trading.paper_engine import create_initial_state


def test_status_is_read_only_paper_mode():
    result = asyncio.run(api.trading_status())
    assert result["status"] == "online"
    assert result["mode"] == "paper_only"
    assert result["orders_enabled"] is False
    assert result["withdrawals_enabled"] is False


def test_markets_endpoint_returns_public_scanner_result(monkeypatch):
    expected = {"quote": "EUR", "markets": [{"symbol": "XBTEUR"}]}
    monkeypatch.setattr(api, "scan_markets", lambda quote, limit: expected)
    result = asyncio.run(api.trading_markets(quote="EUR", limit=1))
    assert result == expected


def test_paper_status_initializes_safe_sek_ledger(monkeypatch):
    state = create_initial_state("200.00")
    monkeypatch.setattr(api, "_load", lambda: (state, 1))
    result = asyncio.run(api.paper_status())
    assert result["cash"] == "200.00"
    assert result["starting_cash"] == "200.00"
    assert result["currency"] == "SEK"
    assert result["paper_enabled"] is False
    assert result["orders_enabled"] is False
    assert result["withdrawals_enabled"] is False
    assert result["storage"] == "supabase"
    assert result["revision"] == 1


def test_paper_status_handles_positions_without_fresh_sek_marks(monkeypatch):
    state = create_initial_state("200.00")
    state["positions"] = {"XBT/EUR": {"quantity": "0.001", "cost_basis": "500000"}}
    monkeypatch.setattr(api, "_load", lambda: (state, 2))
    result = asyncio.run(api.paper_status())
    assert result["equity"] is None
    assert result["valuation_status"] == "awaiting_fresh_sek_market_marks"
    assert result["orders_enabled"] is False


def test_control_guard_fails_closed_when_token_missing(monkeypatch):
    monkeypatch.delenv("TRADE_CONTROL_TOKEN", raising=False)
    with pytest.raises(HTTPException) as exc:
        api._control_guard("anything")
    assert exc.value.status_code == 503


def test_control_guard_rejects_wrong_token(monkeypatch):
    monkeypatch.setenv("TRADE_CONTROL_TOKEN", "expected-secret")
    with pytest.raises(HTTPException) as exc:
        api._control_guard("wrong-secret")
    assert exc.value.status_code == 401


def test_paper_start_requires_guard_and_persists_state(monkeypatch):
    monkeypatch.setenv("TRADE_CONTROL_TOKEN", "expected-secret")
    state = create_initial_state("200.00")
    saved = []
    monkeypatch.setattr(api, "_load", lambda: (state, 4))
    monkeypatch.setattr(api, "_save", lambda updated, revision: saved.append((updated, revision)) or 5)
    result = asyncio.run(api.paper_start(x_trade_control_token="expected-secret"))
    assert result == {"ok": True, "paper_enabled": True, "revision": 5, "orders_enabled": False}
    assert saved[0][0]["paper_enabled"] is True
    assert saved[0][1] == 4


def test_pause_persists_disabled_state(monkeypatch):
    monkeypatch.setenv("TRADE_CONTROL_TOKEN", "expected-secret")
    state = create_initial_state("200.00")
    state["paper_enabled"] = True
    saved = []
    monkeypatch.setattr(api, "_load", lambda: (state, 5))
    monkeypatch.setattr(api, "_save", lambda updated, revision: saved.append(updated) or 6)
    result = asyncio.run(api.paper_pause(x_trade_control_token="expected-secret"))
    assert result["paper_enabled"] is False
    assert saved[0]["paper_enabled"] is False


def test_emergency_stop_disables_paper_and_persists_reason(monkeypatch):
    monkeypatch.setenv("TRADE_CONTROL_TOKEN", "expected-secret")
    state = create_initial_state("200.00")
    state["paper_enabled"] = True
    saved = []
    monkeypatch.setattr(api, "_load", lambda: (state, 6))
    monkeypatch.setattr(api, "_save", lambda updated, revision: saved.append(updated) or 7)
    result = asyncio.run(api.paper_emergency_stop(
        reason="test stop", x_trade_control_token="expected-secret"
    ))
    assert result["emergency_stop"] is True
    assert result["paper_enabled"] is False
    assert saved[0]["emergency_stop"] is True
    assert saved[0]["stop_reason"] == "test stop"
