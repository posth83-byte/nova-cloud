"""Authenticated, read-only Kraken Spot REST preflight.

This module deliberately exposes no order-placement or withdrawal method.
Credentials are read only from server environment variables and are never
returned, logged, or persisted.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from decimal import Decimal, InvalidOperation
from typing import Any

KRAKEN_PRIVATE_URL = "https://api.kraken.com/0/private"
REQUIRED_PERMISSIONS = {
    "query-funds",
    "query-open-trades",
    "modify-trades",
    "query-closed-trades",
}
FORBIDDEN_PERMISSIONS = {
    "withdraw-funds",
    "add-withdraw-address",
    "update-withdraw-address",
}
_nonce_lock = threading.Lock()
_last_nonce = 0


class KrakenPrivateAPIError(RuntimeError):
    """A safe, non-secret Kraken private API error."""


def _credentials() -> tuple[str, str]:
    api_key = os.getenv("KRAKEN_API_KEY", "").strip()
    api_secret = (
        os.getenv("KRAKEN_API_SECRET", "").strip()
        or os.getenv("KRAKEN_SECRET_KEY", "").strip()
    )
    if not api_key or not api_secret:
        raise KrakenPrivateAPIError(
            "Kraken API-nycklar saknas i serverns hemliga miljövariabler."
        )
    try:
        base64.b64decode(api_secret, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise KrakenPrivateAPIError(
            "Kraken API-hemligheten har ogiltigt Base64-format."
        ) from exc
    return api_key, api_secret


def _next_nonce() -> str:
    global _last_nonce
    with _nonce_lock:
        _last_nonce = max(time.time_ns() // 1_000_000, _last_nonce + 1)
        return str(_last_nonce)


def _signature(path: str, encoded_data: bytes, nonce: str, secret: str) -> str:
    try:
        secret_bytes = base64.b64decode(secret, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise KrakenPrivateAPIError("Kraken API-hemligheten är ogiltig.") from exc
    digest = hashlib.sha256(nonce.encode("utf-8") + encoded_data).digest()
    mac = hmac.new(secret_bytes, path.encode("utf-8") + digest, hashlib.sha512)
    return base64.b64encode(mac.digest()).decode("ascii")


def _private_post(endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    if not endpoint or "/" in endpoint or not endpoint.isalnum():
        raise KrakenPrivateAPIError("Ogiltig privat Kraken-metod.")
    api_key, api_secret = _credentials()
    nonce = _next_nonce()
    payload = dict(params or {})
    payload["nonce"] = nonce
    encoded = urllib.parse.urlencode(payload).encode("utf-8")
    path = f"/0/private/{endpoint}"
    request = urllib.request.Request(
        KRAKEN_PRIVATE_URL + "/" + endpoint,
        data=encoded,
        headers={
            "API-Key": api_key,
            "API-Sign": _signature(path, encoded, nonce, api_secret),
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "NOVA-Cloud-Trade-Preflight/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Do not echo provider response bodies; they can contain account data.
        raise KrakenPrivateAPIError(
            f"Kraken privat API svarade med HTTP {exc.code}."
        ) from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise KrakenPrivateAPIError(
            f"Kraken privat API kunde inte verifieras ({type(exc).__name__})."
        ) from exc
    if not isinstance(payload, dict):
        raise KrakenPrivateAPIError("Kraken returnerade ett ogiltigt svar.")
    errors = payload.get("error") or []
    if errors:
        # Return only a small, sanitized list of exchange error codes.
        safe_errors = [str(item)[:100] for item in errors[:3]]
        raise KrakenPrivateAPIError("Kraken API: " + "; ".join(safe_errors))
    result = payload.get("result")
    if not isinstance(result, dict):
        raise KrakenPrivateAPIError("Kraken returnerade ingen giltig result-data.")
    return result


def credentials_configured() -> bool:
    key = bool(os.getenv("KRAKEN_API_KEY", "").strip())
    secret = bool(
        os.getenv("KRAKEN_API_SECRET", "").strip()
        or os.getenv("KRAKEN_SECRET_KEY", "").strip()
    )
    return key and secret


def run_read_only_preflight(eur_sek: Decimal) -> dict[str, Any]:
    """Verify key permissions, account access, EUR balance and open orders."""
    if not eur_sek.is_finite() or eur_sek <= 0:
        raise KrakenPrivateAPIError("EUR/SEK-kursen är ogiltig.")
    key_info = _private_post("GetApiKeyInfo")
    permissions = set(key_info.get("permissions") or [])
    missing = sorted(REQUIRED_PERMISSIONS - permissions)
    forbidden = sorted(FORBIDDEN_PERMISSIONS & permissions)
    if missing:
        raise KrakenPrivateAPIError(
            "Kraken-nyckeln saknar nödvändiga behörigheter: " + ", ".join(missing)
        )
    if forbidden:
        raise KrakenPrivateAPIError(
            "Kraken-nyckeln har förbjudna uttagsbehörigheter. Ta bort dem innan livehandel."
        )

    balances = _private_post("Balance")
    try:
        eur_balance = Decimal(str(balances.get("ZEUR", balances.get("EUR", "0"))))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise KrakenPrivateAPIError("EUR-saldot från Kraken är ogiltigt.") from exc
    if not eur_balance.is_finite() or eur_balance < 0:
        raise KrakenPrivateAPIError("EUR-saldot från Kraken är ogiltigt.")

    open_orders_result = _private_post("OpenOrders")
    open_orders = open_orders_result.get("open") or {}
    if not isinstance(open_orders, dict):
        raise KrakenPrivateAPIError("Krakens öppna order kunde inte verifieras.")

    return {
        "connected": True,
        "api_key_label": str(key_info.get("apiKeyName") or "Kraken API key")[:80],
        "permissions": sorted(permissions),
        "withdrawals_permission": False,
        "eur_balance": str(eur_balance.quantize(Decimal("0.00000001"))),
        "eur_balance_sek_estimate": str(
            (eur_balance * eur_sek).quantize(Decimal("0.01"))
        ),
        "eur_sek_rate": str(eur_sek),
        "open_orders_count": len(open_orders),
        "open_orders_clear": len(open_orders) == 0,
        "budget_policy": "all_available_kraken_eur_balance",
        "orders_enabled": False,
        "withdrawals_enabled": False,
        "mode": "private_read_only_preflight",
    }


def validate_limit_order(
    *,
    pair: str,
    side: str,
    volume: Decimal,
    price: Decimal,
) -> dict[str, Any]:
    """Ask Kraken to validate a spot limit order without submitting it."""
    pair = str(pair or "").strip().upper()
    side = str(side or "").strip().lower()
    if not pair or not pair.isalnum() or len(pair) > 24:
        raise KrakenPrivateAPIError("Ogiltigt Kraken-marknadspar.")
    if side not in {"buy", "sell"}:
        raise KrakenPrivateAPIError("Ogiltig orderriktning.")
    if not volume.is_finite() or not price.is_finite() or volume <= 0 or price <= 0:
        raise KrakenPrivateAPIError("Ordervolym och limitpris måste vara positiva.")
    client_order_id = uuid.uuid4().hex
    result = _private_post("AddOrder", {
        "ordertype": "limit",
        "type": side,
        "volume": format(volume, "f"),
        "pair": pair,
        "price": format(price, "f"),
        "timeinforce": "IOC",
        "cl_ord_id": client_order_id,
        "validate": "true",
    })
    description = result.get("descr") or {}
    return {
        "validated": True,
        "mode": "exchange_validation_only",
        "order_type": "limit",
        "side": side,
        "pair": pair,
        "volume": format(volume, "f"),
        "price": format(price, "f"),
        "description": str(description.get("order") or "")[:240],
        "client_order_id": client_order_id,
        "orders_enabled": False,
        "withdrawals_enabled": False,
    }


def get_open_orders() -> dict[str, Any]:
    """Return open spot orders to internal safety checks only."""
    result = _private_post("OpenOrders")
    orders = result.get("open") or {}
    if not isinstance(orders, dict):
        raise KrakenPrivateAPIError("Krakens öppna order kunde inte verifieras.")
    return orders


def get_account_balances() -> dict[str, Any]:
    """Return private balance data to server-side trading logic only."""
    return _private_post("Balance")


def lookup_order_by_client_id(client_order_id: str) -> dict[str, Any] | None:
    """Reconcile a possibly submitted IOC order without ever resubmitting it."""
    client_order_id = str(client_order_id or "").strip()
    if not client_order_id:
        raise KrakenPrivateAPIError("Orderreferensen saknas.")
    for endpoint, collection in (("OpenOrders", "open"), ("ClosedOrders", "closed")):
        result = _private_post(endpoint, {"cl_ord_id": client_order_id})
        orders = result.get(collection) or {}
        if isinstance(orders, dict) and orders:
            txid, order = next(iter(orders.items()))
            if isinstance(order, dict):
                return {
                    **order,
                    "txid": str(txid),
                    "order_collection": collection,
                    "client_order_id": client_order_id,
                }
    return None


def query_order_by_txid(txid: str) -> dict[str, Any] | None:
    """Fetch authoritative execution quantities and fees for one known order."""
    txid = str(txid or "").strip()
    if (
        not txid or len(txid) > 40
        or any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-" for character in txid.upper())
    ):
        raise KrakenPrivateAPIError("Ogiltig Kraken-orderreferens.")
    result = _private_post("QueryOrders", {"txid": txid, "trades": "true"})
    order = result.get(txid)
    if not isinstance(order, dict):
        return None
    return {
        "txid": txid,
        "status": str(order.get("status") or "").lower(),
        "vol": str(order.get("vol") or "0"),
        "vol_exec": str(order.get("vol_exec") or "0"),
        "cost": str(order.get("cost") or "0"),
        "fee": str(order.get("fee") or "0"),
        "price": str(order.get("price") or "0"),
        "avg_price": str(order.get("price") or "0"),
        "trades": list(order.get("trades") or []),
        "oflags": str(order.get("oflags") or ""),
    }


def submit_limit_order(
    *,
    pair: str,
    side: str,
    volume: Decimal,
    price: Decimal,
    client_order_id: str,
) -> dict[str, Any]:
    """Submit a real, non-margin, EUR spot limit IOC order behind a hard env gate."""
    if os.getenv("TRADE_LIVE_ENABLED", "").strip().lower() != "true":
        raise KrakenPrivateAPIError("Livehandel är avstängd på servernivå.")
    pair = str(pair or "").strip().upper()
    side = str(side or "").strip().lower()
    client_order_id = str(client_order_id or "").strip()
    if not pair or not pair.isalnum() or len(pair) > 24:
        raise KrakenPrivateAPIError("Ogiltigt Kraken-marknadspar.")
    if side not in {"buy", "sell"}:
        raise KrakenPrivateAPIError("Ogiltig orderriktning.")
    if not client_order_id or len(client_order_id) > 36 or not client_order_id.isalnum():
        raise KrakenPrivateAPIError("Ogiltig klientorderreferens.")
    if not volume.is_finite() or not price.is_finite() or volume <= 0 or price <= 0:
        raise KrakenPrivateAPIError("Ordervolym och limitpris måste vara positiva.")
    result = _private_post("AddOrder", {
        "ordertype": "limit",
        "type": side,
        "volume": format(volume, "f"),
        "pair": pair,
        "price": format(price, "f"),
        "timeinforce": "IOC",
        "oflags": "fciq",
        "cl_ord_id": client_order_id,
        # No leverage parameter is sent; this is spot-only.
    })
    txids = result.get("txid") or []
    if not isinstance(txids, list) or not txids:
        raise KrakenPrivateAPIError(
            "Kraken bekräftade inte orderreferensen; ordern måste stämmas av manuellt."
        )
    return {
        "accepted": True,
        "txid": str(txids[0]),
        "client_order_id": client_order_id,
        "pair": pair,
        "side": side,
        "volume": format(volume, "f"),
        "price": format(price, "f"),
        "order_type": "limit",
        "timeinforce": "IOC",
        "mode": "live_spot",
    }
