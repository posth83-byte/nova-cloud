"""Durable, isolated persistence for real Kraken order intents and live state."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any
from uuid import UUID


class LiveStoreError(RuntimeError):
    """A safe error from the live-trading journal."""


def _config() -> tuple[str, str]:
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = (
        os.getenv("SUPABASE_SECRET_KEY", "").strip()
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    )
    if not url or not key:
        raise LiveStoreError("Supabase är inte konfigurerat för livejournalen.")
    return url, key


def _request(table: str, method: str, query: str = "", payload: Any = None,
             prefer: str = "return=representation") -> list[dict[str, Any]]:
    if table not in {"jarvis_live_trading_state", "jarvis_live_order_intents"}:
        raise LiveStoreError("Ogiltig livejournal.")
    base, key = _config()
    url = f"{base}/rest/v1/{table}"
    if query:
        url += "?" + query
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {
        "apikey": key,
        "Authorization": "Bearer " + key,
        "Accept": "application/json",
        "Prefer": prefer,
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read().decode("utf-8")
            value = json.loads(raw) if raw else []
    except urllib.error.HTTPError as exc:
        # Never return the database response body; it may contain account data.
        raise LiveStoreError(f"Livejournalen svarade med HTTP {exc.code}.") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise LiveStoreError("Livejournalen kunde inte nås säkert.") from exc
    if not isinstance(value, list):
        raise LiveStoreError("Livejournalen returnerade ett ogiltigt svar.")
    return value


def load_live_state() -> tuple[dict[str, Any] | None, int]:
    query = urllib.parse.urlencode({"id": "eq.primary", "select": "state,revision", "limit": "1"})
    rows = _request("jarvis_live_trading_state", "GET", query, prefer="")
    if not rows:
        return None, 0
    return rows[0]["state"], int(rows[0]["revision"])


def save_live_state(state: dict[str, Any], revision: int) -> int:
    next_revision = revision + 1
    if revision == 0:
        rows = _request(
            "jarvis_live_trading_state", "POST",
            payload={"id": "primary", "state": state, "revision": next_revision},
        )
    else:
        query = urllib.parse.urlencode({
            "id": "eq.primary", "revision": "eq." + str(revision), "select": "revision"
        })
        rows = _request(
            "jarvis_live_trading_state", "PATCH", query,
            payload={"state": state, "revision": next_revision},
        )
    if not rows:
        raise LiveStoreError("Livejournalens revision ändrades; körningen stoppades.")
    return next_revision


def create_initial_live_state() -> dict[str, Any]:
    """A separate real-money ledger, disabled by default and capped at 200 SEK."""
    return {
        "schema_version": 1,
        "mode": "live_spot",
        "enabled": False,
        "emergency_stop": False,
        "stop_reason": None,
        "currency": "SEK",
        "starting_cash_sek": "200.00",
        "cash_sek": "200.00",
        "positions": {},
        "trades": [],
        "realized_pnl_sek": "0.00",
        "peak_equity_sek": "200.00",
        "day_key": None,
        "day_start_equity_sek": "200.00",
        "worker": {"status": "disabled", "last_error": None},
        "risk": {
            "max_budget_sek": "200.00",
            "daily_loss_limit_pct": "0.02",
            "max_drawdown_pct": "0.10",
            "max_open_positions": 3,
            "fee_rate": "0.0040",
            "slippage_rate": "0.0015",
        },
    }


def load_or_create_live_state() -> tuple[dict[str, Any], int]:
    state, revision = load_live_state()
    if state is not None:
        return state, revision
    initial = create_initial_live_state()
    try:
        return initial, save_live_state(initial, 0)
    except LiveStoreError:
        # Another process may have initialized the row concurrently.
        current, current_revision = load_live_state()
        if current is not None:
            return current, current_revision
        raise


def create_order_intent(*, intent_id: str, client_order_id: str, pair: str,
                        side: str, volume: str, limit_price: str) -> dict[str, Any]:
    try:
        UUID(intent_id)
    except (ValueError, TypeError, AttributeError) as exc:
        raise LiveStoreError("Ogiltigt order-intent-ID.") from exc
    if side not in {"buy", "sell"} or not pair or not pair.isalnum():
        raise LiveStoreError("Ogiltig orderavsikt.")
    rows = _request(
        "jarvis_live_order_intents", "POST",
        payload={
            "id": intent_id, "client_order_id": client_order_id, "pair": pair,
            "side": side, "volume": volume, "limit_price": limit_price,
            "status": "prepared",
            "request_payload": {"pair": pair, "side": side, "volume": volume, "price": limit_price},
        },
    )
    if not rows:
        raise LiveStoreError("Orderavsikten kunde inte journalföras före orderläggning.")
    return rows[0]


def list_unapplied_order_intents(limit: int = 20) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode({
        "ledger_applied": "eq.false",
        "status": "in.(submitting,unknown,accepted,closed)",
        "select": "*", "order": "created_at.asc", "limit": str(max(1, min(limit, 100))),
    })
    return _request("jarvis_live_order_intents", "GET", query, prefer="")


def mark_order_ledger_applied(client_order_id: str) -> None:
    query = urllib.parse.urlencode({
        "client_order_id": "eq." + client_order_id,
        "status": "in.(closed,rejected)", "select": "client_order_id",
    })
    rows = _request(
        "jarvis_live_order_intents", "PATCH", query,
        payload={"ledger_applied": True},
    )
    if not rows:
        raise LiveStoreError("Ordern kunde inte markeras bokförd i livejournalen.")


def attach_order_metadata(client_order_id: str, *, pair_symbol: str, base_asset: str) -> None:
    if not pair_symbol or "/" not in pair_symbol or not base_asset:
        raise LiveStoreError("Ogiltig tillgångsmetadata för orderjournalen.")
    query = urllib.parse.urlencode({
        "client_order_id": "eq." + client_order_id, "select": "client_order_id"
    })
    rows = _request(
        "jarvis_live_order_intents", "PATCH", query,
        payload={"pair_symbol": pair_symbol, "base_asset": base_asset},
    )
    if not rows:
        raise LiveStoreError("Orderns tillgångsmetadata kunde inte sparas.")


def get_order_intent(client_order_id: str) -> dict[str, Any] | None:
    query = urllib.parse.urlencode({
        "client_order_id": "eq." + client_order_id, "select": "*", "limit": "1"
    })
    rows = _request("jarvis_live_order_intents", "GET", query, prefer="")
    return rows[0] if rows else None


def update_order_intent(client_order_id: str, *, status: str,
                        txid: str | None = None,
                        exchange_result: dict[str, Any] | None = None) -> dict[str, Any]:
    allowed = {"prepared", "submitting", "unknown", "accepted", "closed", "rejected", "reconciled"}
    if status not in allowed:
        raise LiveStoreError("Ogiltig orderstatus.")
    query = urllib.parse.urlencode({"client_order_id": "eq." + client_order_id, "select": "*"})
    payload: dict[str, Any] = {"status": status}
    if txid is not None:
        payload["txid"] = txid
    if exchange_result is not None:
        payload["exchange_result"] = exchange_result
    rows = _request("jarvis_live_order_intents", "PATCH", query, payload=payload)
    if not rows:
        raise LiveStoreError("Orderjournalen kunde inte uppdatera orderstatus.")
    return rows[0]
