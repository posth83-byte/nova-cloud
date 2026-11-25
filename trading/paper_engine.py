"""Deterministic paper broker for JARVIS Trading.

This module is deliberately offline: it has no exchange client, API keys, or live
order path. It models spot buys/sells in one quote currency and persists a paper
ledger. Profits stay in cash/equity and are therefore available for reinvestment.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class TradeRejected(ValueError):
    """Raised when a proposed paper trade violates a configured rule."""


def _number(value: Any, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise TradeRejected(f"{name} must be a number") from None
    if result <= 0 or result != result or result == float("inf"):
        raise TradeRejected(f"{name} must be a finite positive number")
    return result


class PaperBroker:
    """Small, persistent, long-only spot paper broker."""

    def __init__(
        self,
        state_path: str | Path,
        starting_cash: float,
        quote_currency: str = "EUR",
        allowed_symbols: tuple[str, ...] = ("BTC/EUR", "ETH/EUR"),
        max_risk_per_trade_pct: float = 1.0,
        max_daily_drawdown_pct: float = 2.0,
        fee_rate: float = 0.0026,
        slippage_rate: float = 0.0005,
        minimum_notional: float = 0.0,
    ) -> None:
        self.path = Path(state_path)
        self.quote_currency = quote_currency.upper()
        self.allowed_symbols = tuple(allowed_symbols)
        self.max_risk_per_trade_pct = _number(max_risk_per_trade_pct, "max_risk_per_trade_pct")
        self.max_daily_drawdown_pct = _number(max_daily_drawdown_pct, "max_daily_drawdown_pct")
        self.fee_rate = float(fee_rate)
        self.slippage_rate = float(slippage_rate)
        self.minimum_notional = float(minimum_notional)
        if not 0 <= self.fee_rate < 0.1:
            raise ValueError("fee_rate must be between 0 and 10%")
        if not 0 <= self.slippage_rate < 0.1:
            raise ValueError("slippage_rate must be between 0 and 10%")
        if self.max_risk_per_trade_pct > 1:
            raise ValueError("Risk per trade cannot exceed 1% in the initial policy")
        if self.max_daily_drawdown_pct > 2:
            raise ValueError("Daily drawdown cannot exceed 2% in the initial policy")
        if self.minimum_notional < 0:
            raise ValueError("minimum_notional cannot be negative")

        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            self.state = json.loads(self.path.read_text(encoding="utf-8"))
            if self.state.get("mode") != "paper":
                raise ValueError("Refusing to load a non-paper state")
            if self.state.get("quote_currency") != self.quote_currency:
                raise ValueError("State quote currency does not match configuration")
        else:
            cash = _number(starting_cash, "starting_cash")
            now = datetime.now(timezone.utc).date().isoformat()
            self.state = {
                "mode": "paper",
                "quote_currency": self.quote_currency,
                "initial_cash": cash,
                "cash": cash,
                "external_funding": cash,
                "positions": {},
                "fills": [],
                "realized_pnl": 0.0,
                "fees_paid": 0.0,
                "day": now,
                "day_start_equity": cash,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self._save()

    def _save(self) -> None:
        payload = json.dumps(self.state, indent=2, sort_keys=True)
        fd, temp_name = tempfile.mkstemp(prefix=self.path.name, dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self.path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def _roll_day(self, prices: dict[str, float] | None = None) -> None:
        today = datetime.now(timezone.utc).date().isoformat()
        if self.state["day"] != today:
            marks = prices or {}
            equity = self.equity(marks, update_day=False)
            self.state["day"] = today
            self.state["day_start_equity"] = equity

    def equity(self, prices: dict[str, float], update_day: bool = True) -> float:
        if update_day:
            self._roll_day(prices)
        total = float(self.state["cash"])
        for symbol, position in self.state["positions"].items():
            if symbol not in prices:
                raise TradeRejected(f"Missing mark price for open position {symbol}")
            total += float(position["quantity"]) * _number(prices[symbol], "mark price")
        return round(total, 8)

    def snapshot(self, prices: dict[str, float] | None = None) -> dict[str, Any]:
        marks = prices or {}
        equity = self.equity(marks) if marks or not self.state["positions"] else None
        return {
            "mode": "paper",
            "quote_currency": self.quote_currency,
            "cash": round(float(self.state["cash"]), 8),
            "equity": equity,
            "external_funding": self.state["external_funding"],
            "realized_pnl": round(float(self.state["realized_pnl"]), 8),
            "fees_paid": round(float(self.state["fees_paid"]), 8),
            "open_positions": self.state["positions"],
            "fills": self.state["fills"][-20:],
            "automatic_profit_reinvestment": True,
            "live_orders_enabled": False,
        }

    def _check_daily_stop(self, prices: dict[str, float]) -> float:
        self._roll_day(prices)
        equity = self.equity(prices, update_day=False)
        start = float(self.state["day_start_equity"])
        floor = start * (1.0 - self.max_daily_drawdown_pct / 100.0)
        if equity <= floor:
            raise TradeRejected("Daily drawdown limit reached; new entries are blocked")
        return equity

    def buy(
        self,
        symbol: str,
        market_price: float,
        stop_price: float,
        prices: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        if symbol not in self.allowed_symbols:
            raise TradeRejected(f"Market is not allowlisted: {symbol}")
        if symbol in self.state["positions"]:
            raise TradeRejected("Only one open position per market is allowed")
        if self.state["positions"]:
            raise TradeRejected("Maximum one open position across the portfolio")
        price = _number(market_price, "market_price")
        stop = _number(stop_price, "stop_price")
        if stop >= price:
            raise TradeRejected("A long spot entry requires stop_price below market_price")

        marks = dict(prices or {})
        marks[symbol] = price
        equity = self._check_daily_stop(marks)
        entry_fill = price * (1.0 + self.slippage_rate)
        # Budget includes estimated entry and stop-exit fees/slippage.
        stop_fill = stop * (1.0 - self.slippage_rate)
        risk_per_unit = (entry_fill - stop_fill) + (entry_fill * self.fee_rate) + (stop_fill * self.fee_rate)
        risk_budget = equity * (self.max_risk_per_trade_pct / 100.0)
        quantity_by_risk = risk_budget / risk_per_unit
        cash = float(self.state["cash"])
        quantity_by_cash = cash / (entry_fill * (1.0 + self.fee_rate))
        quantity = min(quantity_by_risk, quantity_by_cash)
        notional = quantity * entry_fill
        if quantity <= 0 or notional < self.minimum_notional:
            raise TradeRejected("Order is below minimum notional or available risk/cash")
        fee = notional * self.fee_rate
        total_cost = notional + fee
        if total_cost > cash + 1e-9:
            raise TradeRejected("Insufficient quote balance")

        position = {
            "symbol": symbol,
            "quantity": round(quantity, 12),
            "entry_price": round(entry_fill, 12),
            "stop_price": stop,
            "entry_fee": round(fee, 8),
            "entry_cost": round(total_cost, 8),
            "opened_at": datetime.now(timezone.utc).isoformat(),
        }
        self.state["cash"] = round(cash - total_cost, 8)
        self.state["fees_paid"] = round(float(self.state["fees_paid"]) + fee, 8)
        self.state["positions"][symbol] = position
        fill = {"side": "buy", **position, "fee": round(fee, 8)}
        self.state["fills"].append(fill)
        self._save()
        return fill

    def sell(self, symbol: str, market_price: float, reason: str = "strategy_exit") -> dict[str, Any]:
        if symbol not in self.state["positions"]:
            raise TradeRejected(f"No open position for {symbol}")
        price = _number(market_price, "market_price")
        position = self.state["positions"][symbol]
        exit_fill = price * (1.0 - self.slippage_rate)
        quantity = float(position["quantity"])
        proceeds = quantity * exit_fill
        fee = proceeds * self.fee_rate
        net_proceeds = proceeds - fee
        pnl = net_proceeds - float(position["entry_cost"])
        self.state["cash"] = round(float(self.state["cash"]) + net_proceeds, 8)
        self.state["realized_pnl"] = round(float(self.state["realized_pnl"]) + pnl, 8)
        self.state["fees_paid"] = round(float(self.state["fees_paid"]) + fee, 8)
        fill = {
            "side": "sell",
            "symbol": symbol,
            "quantity": round(quantity, 12),
            "price": round(exit_fill, 12),
            "fee": round(fee, 8),
            "realized_pnl": round(pnl, 8),
            "reason": reason,
            "closed_at": datetime.now(timezone.utc).isoformat(),
        }
        del self.state["positions"][symbol]
        self.state["fills"].append(fill)
        self._save()
        return fill
