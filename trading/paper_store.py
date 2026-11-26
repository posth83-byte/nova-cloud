"""Server-side persistence for the simulation-only Trade AI ledger."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = (
    os.getenv("SUPABASE_SECRET_KEY", "").strip()
    or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
)


class PaperStoreError(RuntimeError):
    pass


def _request(method: str, query: str = "", payload: Any = None, prefer: str = ""):
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise PaperStoreError("Supabase är inte konfigurerat för Trade AI.")
    url = SUPABASE_URL + "/rest/v1/jarvis_trading_state"
    if query:
        url += "?" + query
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": "Bearer " + SUPABASE_KEY,
        "Accept": "application/json",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    if prefer:
        headers["Prefer"] = prefer
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else []
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:500]
        raise PaperStoreError(f"Trade AI-lagring HTTP {error.code}: {detail}") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise PaperStoreError("Trade AI kan inte nå den permanenta lagringen.") from error


def load_state() -> tuple[dict[str, Any] | None, int]:
    query = urllib.parse.urlencode({
        "id": "eq.primary", "select": "state,revision", "limit": "1"
    })
    rows = _request("GET", query)
    if not rows:
        return None, 0
    return rows[0]["state"], int(rows[0].get("revision") or 0)


def save_state(state: dict[str, Any], revision: int) -> int:
    next_revision = revision + 1
    _request(
        "POST",
        payload={"id": "primary", "state": state, "revision": next_revision},
        prefer="resolution=merge-duplicates,return=minimal",
    )
    return next_revision


def load_or_create(initializer) -> tuple[dict[str, Any], int]:
    state, revision = load_state()
    if state is not None:
        return state, revision
    state = initializer("200.00")
    revision = save_state(state, 0)
    return state, revision
