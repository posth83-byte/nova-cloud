"""Deterministic, simulation-only trading ledger and risk controls.

This module never connects to an exchange and never places real orders.
Prices passed to it must already be converted into SEK by a separately
verified FX source; no implicit currency conversion is performed.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

CENT = Decimal("0.01")
ZERO = Decimal("0")


class PaperTradingError(ValueError):
    """A proposed simulated trade violates the paper-trading rules."""


def money(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise PaperTradingError("Beloppet är ogiltigt.") from exc
    if not result.is_finite():
        raise PaperTradingError("Beloppet måste vara ändligt.")
    return result


def q2(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def create_initial_state(starting_cash_sek: Any = "200.00") -> dict[str, Any]:
    cash = q2(money(starting_cash_sek))
    if cash <= ZERO:
        raise PaperTradingError("Startkapitalet måste vara större än noll.")
    return {
        "schema_version": 1,
        "mode": "paper_only",
        "currency": "SEK",
        "starting_cash": str(cash),
        "cash": str(cash),
        "paper_enabled": False,
        "emergency_stop": False,
        "positions": {},
        "trades": [],
        "realized_pnl": "0.00",
        "peak_equity": str(cash),
        "day_key": None,
        "day_start_equity": str(cash),
        "risk": {
            "max_trade_pct": "0.10",
            "max_position_pct": "0.25",
            "daily_loss_limit_pct": "0.02",
            "max_drawdown_pct": "0.10",
            "fee_rate": "0.0040",
            "slippage_rate": "0.0015",
        },
    }


def _equity(state: dict[str, Any], marks: dict[str, Any]) -> Decimal:
    total = money(state["cash"])
    for symbol, position in state["positions"].items():
        if symbol not in marks:
            raise PaperTradingError(f"Saknar SEK-marknadspris för {symbol}.")
        mark = money(marks[symbol])
        if mark <= ZERO:
            raise PaperTradingError("Marknadspriset måste vara större än noll.")
        total += money(position["quantity"]) * mark
    return q2(total)


def portfolio_snapshot(state: dict[str, Any], marks: dict[str, Any] | None = None) -> dict[str, Any]:
    marks = marks or {}
    equity = _equity(state, marks) if state["positions"] else q2(money(state["cash"]))
    starting = money(state["starting_cash"])
    peak = max(money(state["peak_equity"]), equity)
    return {
        "mode": "paper_only",
        "currency": "SEK",
        "paper_enabled": bool(state["paper_enabled"]),
        "emergency_stop": bool(state["emergency_stop"]),
        "cash": str(q2(money(state["cash"]))),
        "equity": str(equity),
        "starting_cash": str(q2(starting)),
        "total_pnl": str(q2(equity - starting)),
        "realized_pnl": str(q2(money(state["realized_pnl"]))),
        "peak_equity": str(q2(peak)),
        "positions": deepcopy(state["positions"]),
        "trade_count": len(state["trades"]),
        "orders_enabled": False,
        "withdrawals_enabled": False,
    }


def set_paper_enabled(state: dict[str, Any], enabled: bool) -> dict[str, Any]:
    updated = deepcopy(state)
    if enabled and updated["emergency_stop"]:
        raise PaperTradingError("Nödstoppet är aktiverat och måste granskas separat.")
    updated["paper_enabled"] = bool(enabled)
    return updated


def activate_emergency_stop(state: dict[str, Any], reason: str) -> dict[str, Any]:
    updated = deepcopy(state)
    updated["emergency_stop"] = True
    updated["paper_enabled"] = False
    updated["stop_reason"] = str(reason or "Riskgräns nådd")[:240]
    return updated


def apply_paper_trade(
    state: dict[str, Any],
    *,
    symbol: str,
    side: str,
    quantity: Any,
    price_sek: Any,
    timestamp: datetime | None = None,
    marks_sek: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply one simulated spot fill, including conservative fee/slippage."""
    if not state.get("paper_enabled") or state.get("emergency_stop"):
        raise PaperTradingError("Pappershandel är inte aktiv eller nödstoppet är på.")
    symbol = str(symbol or "").strip().upper()
    if not symbol or len(symbol) > 24 or "/" not in symbol:
        raise PaperTradingError("Ange en giltig marknad, exempelvis XBT/EUR.")
    side = str(side or "").strip().lower()
    if side not in {"buy", "sell"}:
        raise PaperTradingError("Sidan måste vara buy eller sell.")

    qty = money(quantity)
    price = money(price_sek)
    if qty <= ZERO or price <= ZERO:
        raise PaperTradingError("Antal och pris måste vara större än noll.")

    risk = state["risk"]
    fee_rate = money(risk["fee_rate"])
    slippage_rate = money(risk["slippage_rate"])
    if not ZERO <= fee_rate <= Decimal("0.05") or not ZERO <= slippage_rate <= Decimal("0.05"):
        raise PaperTradingError("Ogiltiga avgifts- eller slippageantaganden.")

    now = timestamp or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise PaperTradingError("Tidsstämpeln måste innehålla tidszon.")
    day_key = now.astimezone(timezone.utc).date().isoformat()
    updated = deepcopy(state)
    marks = dict(marks_sek or {})
    marks[symbol] = price

    current_equity = _equity(updated, marks) if updated["positions"] else q2(money(updated["cash"]))
    if updated.get("day_key") != day_key:
        updated["day_key"] = day_key
        updated["day_start_equity"] = str(current_equity)

    day_start = money(updated["day_start_equity"])
    if current_equity <= day_start * (Decimal("1") - money(risk["daily_loss_limit_pct"])):
        raise PaperTradingError("Dagens förlustgräns är nådd.")

    peak = max(money(updated["peak_equity"]), current_equity)
    if current_equity <= peak * (Decimal("1") - money(risk["max_drawdown_pct"])):
        raise PaperTradingError("Maximal portföljnedgång är nådd.")

    fill_price = price * (Decimal("1") + slippage_rate if side == "buy" else Decimal("1") - slippage_rate)
    gross = qty * fill_price
    fee = gross * fee_rate
    cash = money(updated["cash"])
    positions = updated["positions"]
    realized = ZERO

    if side == "buy":
        total_cost = gross + fee
        equity_before = current_equity
        if total_cost > cash:
            raise PaperTradingError("Otillräckligt simulerat saldo.")
        if total_cost > equity_before * money(risk["max_trade_pct"]):
            raise PaperTradingError("Köpet överskrider maxgränsen per affär.")
        existing = positions.get(symbol, {"quantity": "0", "cost_basis": "0"})
        old_qty = money(existing["quantity"])
        old_cost = money(existing["cost_basis"]) * old_qty
        new_qty = old_qty + qty
        if total_cost + old_cost > equity_before * money(risk["max_position_pct"]):
            raise PaperTradingError("Köpet skulle överskrida maxexponeringen i marknaden.")
        avg_cost = (old_cost + total_cost) / new_qty
        positions[symbol] = {"quantity": str(new_qty), "cost_basis": str(avg_cost)}
        cash -= total_cost
    else:
        existing = positions.get(symbol)
        if not existing or qty > money(existing["quantity"]):
            raise PaperTradingError("Det finns inte tillräckligt med simulerat innehav att sälja.")
        net_proceeds = gross - fee
        avg_cost = money(existing["cost_basis"])
        realized = net_proceeds - (avg_cost * qty)
        remaining = money(existing["quantity"]) - qty
        if remaining == ZERO:
            del positions[symbol]
        else:
            positions[symbol] = {"quantity": str(remaining), "cost_basis": str(avg_cost)}
        cash += net_proceeds

    updated["cash"] = str(q2(cash))
    updated["realized_pnl"] = str(q2(money(updated["realized_pnl"]) + realized))
    updated["peak_equity"] = str(q2(max(peak, current_equity)))
    updated["trades"].append({
        "timestamp": now.astimezone(timezone.utc).isoformat(),
        "symbol": symbol,
        "side": side,
        "quantity": str(qty),
        "reference_price_sek": str(price),
        "fill_price_sek": str(q2(fill_price)),
        "fee_sek": str(q2(fee)),
        "slippage_rate": str(slippage_rate),
        "realized_pnl_sek": str(q2(realized)),
        "mode": "paper_only",
    })
    return updated
