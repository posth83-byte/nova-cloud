"""Small server-side Supabase JSON state store for paper trading.

Only the service-role secret may access the backing table. This module is
paper-only and refuses to persist any state whose mode is not exactly "paper".
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class SupabaseStateStore:
    TABLE = "jarvis_trading_state"

    def __init__(self, url: str, secret_key: str, timeout: int = 15) -> None:
        self.url = url.strip().rstrip("/")
        self.secret_key = secret_key.strip()
        self.timeout = timeout
        self.revision = 0
        if not self.url or not self.secret_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SECRET_KEY are required")

    @classmethod
    def from_env(cls) -> "SupabaseStateStore":
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_SECRET_KEY", "") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        return cls(url, key)

    def _request(self, method: str, payload: dict[str, Any] | None = None) -> Any:
        query = urllib.parse.urlencode({"id": "eq.primary", "select": "state,revision"})
        url = f"{self.url}/rest/v1/{self.TABLE}?{query}"
        headers = {
            "apikey": self.secret_key,
            "Authorization": "Bearer " + self.secret_key,
            "Accept": "application/json",
        }
        data = None
        if payload is not None:
            url += "&on_conflict=id"
            data = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
            headers["Prefer"] = "resolution=merge-duplicates,return=representation"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:400]
            raise RuntimeError(f"Supabase paper-state request failed ({exc.code}): {detail}") from None
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Supabase paper-state connection failed: {exc.reason}") from None
        if not raw:
            return []
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise RuntimeError("Supabase paper-state returned invalid JSON") from None

    def load(self) -> dict[str, Any] | None:
        rows = self._request("GET")
        if not isinstance(rows, list) or len(rows) > 1:
            raise RuntimeError("Supabase paper-state returned an unexpected row set")
        if not rows:
            return None
        row = rows[0]
        state = row.get("state")
        if not isinstance(state, dict) or state.get("mode") != "paper":
            raise RuntimeError("Refusing to load a missing, invalid, or non-paper state")
        self.revision = int(row.get("revision") or 0)
        return state

    def save(self, state: dict[str, Any]) -> int:
        if not isinstance(state, dict) or state.get("mode") != "paper":
            raise ValueError("SupabaseStateStore accepts paper-mode state only")
        next_revision = self.revision + 1
        rows = self._request("POST", {
            "id": "primary",
            "state": state,
            "revision": next_revision,
        })
        if not isinstance(rows, list) or len(rows) != 1:
            raise RuntimeError("Supabase did not confirm the saved paper state")
        saved_revision = int(rows[0].get("revision") or 0)
        if saved_revision != next_revision:
            raise RuntimeError("Supabase paper-state revision did not match the saved revision")
        self.revision = saved_revision
        return saved_revision
