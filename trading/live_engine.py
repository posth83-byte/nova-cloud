"""Fail-closed coordinator for journal-first Kraken Spot order submission.

This module deliberately does not choose trades. Strategy code must first
produce a risk-approved intent; this coordinator guarantees that the intent
is durable before a single exchange submission and is never blindly retried.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from trading.kraken_private import (
    KrakenPrivateAPIError,
    lookup_order_by_client_id,
    submit_limit_order,
)
from trading.live_store import (
    LiveStoreError,
    create_order_intent,
    get_order_intent,
    update_order_intent,
)


class LiveExecutionError(RuntimeError):
    """A fail-closed live execution or reconciliation error."""


def execute_journaled_limit_order(
    *, pair: str, side: str, volume: Decimal, price: Decimal
) -> dict[str, Any]:
    """Persist unique intent, then submit exactly once; ambiguous outcomes stop."""
    intent_id = str(uuid.uuid4())
    client_order_id = uuid.uuid4().hex
    # This durable insert must succeed before Kraken can receive an order.
    create_order_intent(
        intent_id=intent_id,
        client_order_id=client_order_id,
        pair=pair,
        side=side,
        volume=format(volume, "f"),
        limit_price=format(price, "f"),
    )
    update_order_intent(client_order_id, status="submitting")
    try:
        result = submit_limit_order(
            pair=pair, side=side, volume=volume, price=price,
            client_order_id=client_order_id,
        )
    except KrakenPrivateAPIError as exc:
        # A timeout may happen after Kraken accepted the order. Never retry here.
        try:
            update_order_intent(
                client_order_id, status="unknown",
                exchange_result={"error_type": type(exc).__name__},
            )
        except LiveStoreError as journal_exc:
            raise LiveExecutionError(
                "Orderutfallet är osäkert och journalen kunde inte uppdateras; stoppa all handel."
            ) from journal_exc
        raise LiveExecutionError(
            "Orderutfallet är osäkert. Ordern får endast stämmas av, aldrig skickas om."
        ) from exc
    update_order_intent(
        client_order_id, status="accepted", txid=result["txid"],
        exchange_result={"accepted": True, "mode": "live_spot"},
    )
    return {
        "accepted": True,
        "client_order_id": client_order_id,
        "txid": result["txid"],
        "pair": pair,
        "side": side,
        "mode": "live_spot",
    }


def reconcile_order_intent(client_order_id: str) -> dict[str, Any]:
    """Look up an existing intent at Kraken; this function can never submit."""
    intent = get_order_intent(client_order_id)
    if not intent:
        raise LiveExecutionError("Orderavsikten saknas i den permanenta journalen.")
    if intent.get("status") in {"closed", "reconciled", "rejected"}:
        return {"status": intent["status"], "client_order_id": client_order_id}
    try:
        order = lookup_order_by_client_id(client_order_id)
    except KrakenPrivateAPIError as exc:
        raise LiveExecutionError(
            "Kraken kunde inte stämma av ordern. Ingen ny order skickas."
        ) from exc
    if order is None:
        # Absence is not proof of non-submission after a network timeout.
        update_order_intent(client_order_id, status="unknown")
        return {"status": "unknown", "client_order_id": client_order_id, "resubmit": False}
    status = str(order.get("status") or "").lower()
    journal_status = "closed" if status in {"closed", "canceled", "expired"} else "accepted"
    update_order_intent(
        client_order_id, status=journal_status, txid=str(order.get("txid") or ""),
        exchange_result={
            "status": status,
            "vol_exec": str(order.get("vol_exec") or "0"),
            "cost": str(order.get("cost") or "0"),
            "fee": str(order.get("fee") or "0"),
        },
    )
    return {
        "status": journal_status,
        "client_order_id": client_order_id,
        "txid": str(order.get("txid") or ""),
        "vol_exec": str(order.get("vol_exec") or "0"),
        "cost": str(order.get("cost") or "0"),
        "fee": str(order.get("fee") or "0"),
        "resubmit": False,
    }
