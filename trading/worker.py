"""Scheduled, simulation-only Trade AI worker.

This worker consumes closed 60-minute Kraken candles and updates the durable
paper ledger. It has no private exchange client and cannot place live orders.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from trading.kraken_monitor import KrakenPublicAPIError, fetch_ohlc_candles, scan_markets
from trading.paper_engine import (
    PaperTradingError,
    activate_emergency_stop,
    apply_paper_trade,
    portfolio_snapshot,
)
from trading.paper_store import load_or_create, save_state
from trading.paper_engine import create_initial_state
from trading.strategy import StrategyDataError, fetch_eur_sek_rate


MAX_WATCHLIST = 8
MIN_TURNOVER_EUR = 10_000.0
MAX_SPREAD_PCT = 0.35


def _cross_signal(candles: list[dict[str, Any]]) -> tuple[bool, bool]:
    closes = [float(row["close"]) for row in candles if float(row["close"]) > 0]
    if len(closes) < 37:
        return False, False

    def average(end: int, window: int) -> float:
        return sum(closes[end - window + 1:end + 1]) / window

    end = len(closes) - 1
    fast_previous, slow_previous = average(end - 1, 12), average(end - 1, 36)
    fast_current, slow_current = average(end, 12), average(end, 36)
    return (
        fast_previous <= slow_previous and fast_current > slow_current,
        fast_previous >= slow_previous and fast_current < slow_current,
    )


def run_paper_tick() -> dict[str, Any]:
    """Run one idempotent market scan and paper-only strategy evaluation."""
    state, revision = load_or_create(create_initial_state)
    now = datetime.now(timezone.utc)
    worker_state = dict(state.get("worker") or {})
    worker_state["last_tick_at"] = now.isoformat()

    if state.get("emergency_stop"):
        return {
            "ok": True, "status": "emergency_stopped", "paper_enabled": False,
            "orders_enabled": False, "withdrawals_enabled": False,
        }
    if not state.get("paper_enabled"):
        worker_state["status"] = "waiting_for_paper_activation"
        state["worker"] = worker_state
        next_revision = save_state(state, revision)
        return {
            "ok": True, "status": worker_state["status"], "paper_enabled": False,
            "revision": next_revision, "orders_enabled": False,
            "withdrawals_enabled": False,
        }

    try:
        fx = fetch_eur_sek_rate()
        rate = float(fx["rate"])
        market_data = scan_markets(quote="EUR", limit=50)
        markets = market_data.get("markets", [])
        market_by_symbol = {str(row.get("symbol", "")).upper(): row for row in markets}
        positions = state.get("positions", {})

        # A position must have a fresh SEK mark before any risk decision or trade.
        missing_positions = [symbol for symbol in positions if symbol.upper() not in market_by_symbol]
        if missing_positions:
            raise StrategyDataError(
                "Saknar färsk marknadsdata för öppna positioner: " + ", ".join(missing_positions)
            )
        marks = {
            symbol: float(row["last"]) * rate
            for symbol, row in market_by_symbol.items()
            if float(row.get("last") or 0) > 0
        }

        equity = float(portfolio_snapshot(state, marks)["equity"])
        risk = state["risk"]
        day_key = now.date().isoformat()
        if state.get("day_key") != day_key:
            state["day_key"] = day_key
            state["day_start_equity"] = f"{equity:.2f}"
        day_start = float(state.get("day_start_equity") or equity)
        peak = max(float(state.get("peak_equity") or equity), equity)
        state["peak_equity"] = f"{peak:.2f}"

        stop_reason = None
        if equity <= day_start * (1 - float(risk["daily_loss_limit_pct"])):
            stop_reason = "Dagens förlustgräns nådd"
        elif equity <= peak * (1 - float(risk["max_drawdown_pct"])):
            stop_reason = "Maximal portföljnedgång nådd"
        if stop_reason:
            state = activate_emergency_stop(state, stop_reason)
            state["worker"] = {
                **worker_state, "status": "emergency_stopped",
                "last_error": stop_reason, "last_tick_at": now.isoformat(),
            }
            next_revision = save_state(state, revision)
            return {
                "ok": True, "status": "emergency_stopped", "reason": stop_reason,
                "revision": next_revision, "orders_enabled": False,
                "withdrawals_enabled": False,
            }

        trade_budget = equity * float(risk["max_trade_pct"])
        candidates = []
        for row in markets:
            symbol = str(row.get("symbol", "")).upper()
            if not symbol:
                continue
            try:
                ask = float(row["ask"])
                bid = float(row["bid"])
                spread = float(row["spread_pct"])
                turnover = float(row["volume_24h_quote_est"])
                min_qty = float(row.get("min_order_qty") or 0)
                min_cost = float(row.get("min_cost_quote") or 0)
            except (KeyError, TypeError, ValueError):
                continue
            if ask <= 0 or bid <= 0 or ask < bid:
                continue
            if spread > MAX_SPREAD_PCT or turnover < MIN_TURNOVER_EUR:
                continue
            minimum_eur = max(min_cost, min_qty * ask)
            if minimum_eur * rate > trade_budget / 1.0055:
                continue
            candidates.append(row)

        candidates.sort(key=lambda row: (
            float(row.get("spread_pct") or 99),
            -float(row.get("volume_24h_quote_est") or 0),
        ))
        watch_symbols = {str(row["symbol"]).upper() for row in candidates[:MAX_WATCHLIST]}
        watch_symbols.update(symbol.upper() for symbol in positions)
        processed = dict(worker_state.get("processed_candles") or {})
        actions = []
        evaluated = 0

        for symbol in sorted(watch_symbols):
            market = market_by_symbol.get(symbol)
            if market is None:
                continue
            history = fetch_ohlc_candles(symbol, interval=60)
            candles = history.get("candles", [])
            if len(candles) < 37:
                continue
            candle_time = int(candles[-1]["timestamp"])
            if int(processed.get(symbol) or 0) >= candle_time:
                continue
            processed[symbol] = candle_time
            evaluated += 1
            cross_up, cross_down = _cross_signal(candles)
            position = state.get("positions", {}).get(symbol)

            if position and cross_down:
                quantity = str(position["quantity"])
                state = apply_paper_trade(
                    state, symbol=symbol, side="sell", quantity=quantity,
                    price_sek=Decimal(str(market["bid"])) * Decimal(str(rate)),
                    timestamp=now, marks_sek=marks,
                )
                actions.append({"symbol": symbol, "side": "paper_sell", "candle": candle_time})
            elif not position and cross_up:
                ask_eur = float(market["ask"])
                ask_sek = Decimal(str(ask_eur)) * Decimal(str(rate))
                fee = Decimal(str(risk["fee_rate"]))
                slippage = Decimal(str(risk["slippage_rate"]))
                budget = min(
                    Decimal(str(trade_budget)),
                    Decimal(str(state["cash"])),
                )
                quantity = budget / (ask_sek * (Decimal("1") + fee + slippage))
                minimum_qty = Decimal(str(history.get("min_order_qty") or 0))
                minimum_cost = Decimal(str(history.get("min_cost_eur") or 0))
                if quantity < minimum_qty or quantity * Decimal(str(ask_eur)) < minimum_cost:
                    actions.append({"symbol": symbol, "side": "rejected_exchange_minimum"})
                    continue
                state = apply_paper_trade(
                    state, symbol=symbol, side="buy", quantity=quantity,
                    price_sek=ask_sek, timestamp=now, marks_sek=marks,
                )
                actions.append({"symbol": symbol, "side": "paper_buy", "candle": candle_time})

        worker_state.update({
            "status": "running",
            "last_error": None,
            "last_success_at": now.isoformat(),
            "last_fx": fx,
            "last_markets_found": len(markets),
            "last_markets_eligible": len(candidates),
            "last_candles_evaluated": evaluated,
            "processed_candles": processed,
            "last_actions": actions[-MAX_WATCHLIST:],
        })
        state["worker"] = worker_state
        next_revision = save_state(state, revision)
        return {
            "ok": True, "status": "running", "paper_enabled": True,
            "markets_found": len(markets), "markets_eligible": len(candidates),
            "candles_evaluated": evaluated, "actions": actions,
            "revision": next_revision, "orders_enabled": False,
            "withdrawals_enabled": False,
        }
    except (StrategyDataError, KrakenPublicAPIError, PaperTradingError, ValueError, KeyError, TypeError) as exc:
        worker_state.update({
            "status": "waiting_for_valid_market_data",
            "last_error": str(exc)[:300],
            "last_success_at": worker_state.get("last_success_at"),
        })
        state["worker"] = worker_state
        next_revision = save_state(state, revision)
        return {
            "ok": False, "status": worker_state["status"],
            "error": worker_state["last_error"], "revision": next_revision,
            "orders_enabled": False, "withdrawals_enabled": False,
        }
