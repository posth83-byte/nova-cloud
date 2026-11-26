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
from trading.opportunity_radar import rank_opportunities


MAX_WATCHLIST = 24
MAX_OPEN_POSITIONS = 3
MAX_TOTAL_EXPOSURE_PCT = 1.00
MIN_TURNOVER_EUR = 10_000.0
MAX_SPREAD_PCT = 0.35


def _cross_signal(
    candles: list[dict[str, Any]],
    *,
    after_timestamp: int = 0,
    max_signal_age_candles: int = 3,
) -> tuple[bool, bool]:
    """Return the newest recent SMA cross since the last scan of this market.

    The market watchlist rotates across several scheduler runs. Looking only at
    the newest candle can miss a cross that happened between scans. We therefore
    inspect every newly closed candle, retain the newest cross, and ignore
    signals older than a small bounded number of candles.
    """
    clean = []
    for row in candles:
        try:
            timestamp = int(row["timestamp"])
            close = float(row["close"])
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        if timestamp > 0 and close > 0:
            clean.append({"timestamp": timestamp, "close": close})
    clean.sort(key=lambda row: row["timestamp"])
    # Deduplicate timestamps deterministically, retaining the last observation.
    by_timestamp = {row["timestamp"]: row for row in clean}
    clean = [by_timestamp[key] for key in sorted(by_timestamp)]
    closes = [row["close"] for row in clean]
    if len(closes) < 37 or max_signal_age_candles < 0:
        return False, False

    def average(end: int, window: int) -> float:
        return sum(closes[end - window + 1:end + 1]) / window

    latest_signal = (False, False)
    latest_signal_index = None
    for end in range(36, len(closes)):
        if clean[end]["timestamp"] <= int(after_timestamp or 0):
            continue
        fast_previous, slow_previous = average(end - 1, 12), average(end - 1, 36)
        fast_current, slow_current = average(end, 12), average(end, 36)
        cross_up = fast_previous <= slow_previous and fast_current > slow_current
        cross_down = fast_previous >= slow_previous and fast_current < slow_current
        if cross_up or cross_down:
            latest_signal = (cross_up, cross_down)
            latest_signal_index = end

    if latest_signal_index is None:
        return False, False
    signal_age = len(clean) - 1 - latest_signal_index
    if signal_age > max_signal_age_candles:
        return False, False
    return latest_signal



def _momentum_entry_signal(
    candles: list[dict[str, Any]],
    *,
    after_timestamp: int = 0,
) -> bool:
    """Confirm a fresh, orderly uptrend without chasing sharp/overbought moves.

    This supplements (never replaces) the SMA crossover. It uses closed candles,
    an EMA12/EMA36 trend filter, a bounded 14-period RSI, and a modest 3-candle
    return. It is intentionally conservative and does not bypass execution risk
    checks.
    """
    clean = []
    for row in candles:
        try:
            timestamp = int(row["timestamp"])
            close = float(row["close"])
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        if timestamp > 0 and close > 0:
            clean.append((timestamp, close))
    clean.sort(key=lambda item: item[0])
    dedup = {timestamp: close for timestamp, close in clean}
    clean = [(timestamp, dedup[timestamp]) for timestamp in sorted(dedup)]
    if len(clean) < 37 or clean[-1][0] <= int(after_timestamp or 0):
        return False

    closes = [close for _, close in clean]

    def ema(values: list[float], period: int) -> float:
        alpha = 2.0 / (period + 1.0)
        value = sum(values[:period]) / period
        for price in values[period:]:
            value = alpha * price + (1.0 - alpha) * value
        return value

    changes = [closes[index] - closes[index - 1] for index in range(len(closes) - 14, len(closes))]
    gains = sum(max(change, 0.0) for change in changes) / 14.0
    losses = sum(max(-change, 0.0) for change in changes) / 14.0
    if losses <= 0:
        return False
    rsi = 100.0 - (100.0 / (1.0 + gains / losses))
    fast = ema(closes, 12)
    slow = ema(closes, 36)
    last = closes[-1]
    momentum_3 = ((last / closes[-4]) - 1.0) * 100.0
    distance_from_fast = ((last / fast) - 1.0) * 100.0 if fast > 0 else 999.0

    return (
        fast > slow * 1.0005
        and last > fast
        and 48.0 <= rsi <= 72.0
        and 0.15 <= momentum_3 <= 4.5
        and 0.0 <= distance_from_fast <= 2.5
    )


def _momentum_exit_signal(
    candles: list[dict[str, Any]],
    *,
    after_timestamp: int = 0,
) -> bool:
    """Exit a held position on confirmed trend deterioration, using closed candles only."""
    clean = []
    for row in candles:
        try:
            timestamp, close = int(row["timestamp"]), float(row["close"])
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        if timestamp > 0 and close > 0:
            clean.append((timestamp, close))
    clean.sort(key=lambda item: item[0])
    dedup = {timestamp: close for timestamp, close in clean}
    clean = [(timestamp, dedup[timestamp]) for timestamp in sorted(dedup)]
    if len(clean) < 37 or clean[-1][0] <= int(after_timestamp or 0):
        return False

    closes = [close for _, close in clean]
    def ema(values: list[float], period: int) -> float:
        alpha = 2.0 / (period + 1.0)
        value = sum(values[:period]) / period
        for price in values[period:]:
            value = alpha * price + (1.0 - alpha) * value
        return value

    changes = [closes[index] - closes[index - 1] for index in range(len(closes) - 14, len(closes))]
    gains = sum(max(change, 0.0) for change in changes) / 14.0
    losses = sum(max(-change, 0.0) for change in changes) / 14.0
    rsi = 0.0 if losses <= 0 else 100.0 - (100.0 / (1.0 + gains / losses))
    fast, slow, last = ema(closes, 12), ema(closes, 36), closes[-1]
    momentum_3 = ((last / closes[-4]) - 1.0) * 100.0
    return (last < fast and fast < slow and momentum_3 <= -0.5) or (rsi <= 42.0 and momentum_3 <= -0.75)


def _select_watchlist(
    candidates: list[dict[str, Any]],
    positions: dict[str, Any],
    cursor: int,
) -> tuple[set[str], int]:
    """Rotate through eligible markets so the fixed-size batch covers the full list."""
    symbols = list(dict.fromkeys(
        str(row.get("symbol", "")).strip().upper()
        for row in candidates
        if str(row.get("symbol", "")).strip()
    ))
    if not symbols:
        return {str(symbol).upper() for symbol in positions}, 0

    start = int(cursor) % len(symbols)
    end = min(start + MAX_WATCHLIST, len(symbols))
    selected = set(symbols[start:end])
    next_cursor = 0 if end >= len(symbols) else end
    selected.update(str(symbol).upper() for symbol in positions)
    return selected, next_cursor


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
        market_data = scan_markets(
            quote="EUR", limit=100, include_symbols=list(state.get("positions", {}).keys())
        )
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
        # User-approved paper policy: a qualifying setup may use all available
        # paper equity; legacy 10%/25% caps are upgraded in the persisted state.
        risk["max_trade_pct"] = "1.00"
        risk["max_position_pct"] = "1.00"
        state["risk"] = risk
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
                "last_marked_at": now.isoformat(), "last_marks_sek": marks,
            }
            next_revision = save_state(state, revision)
            return {
                "ok": True, "status": "emergency_stopped", "reason": stop_reason,
                "revision": next_revision, "orders_enabled": False,
                "withdrawals_enabled": False,
            }

        trade_budget = min(equity * float(risk["max_trade_pct"]), float(state["cash"]))
        all_in_cost_factor = (1 + float(risk["fee_rate"])) * (1 + float(risk["slippage_rate"]))
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
            if minimum_eur * rate > trade_budget / all_in_cost_factor:
                continue
            candidates.append(row)

        radar = rank_opportunities(
            candidates, equity_sek=max(trade_budget, 0.01), eur_sek=rate,
            limit=max(1, len(candidates)),
        ) if candidates else {"candidates": []}
        radar_scores = {row["symbol"]: float(row["score"]) for row in radar["candidates"]}
        candidates.sort(key=lambda row: (
            -radar_scores.get(str(row.get("symbol", "")).upper(), 0.0),
            float(row.get("spread_pct") or 99),
            -float(row.get("volume_24h_quote_est") or 0),
        ))
        watch_symbols, next_watchlist_cursor = _select_watchlist(
            candidates, positions, int(worker_state.get("watchlist_cursor") or 0)
        )
        processed = dict(worker_state.get("processed_candles") or {})
        actions = []
        evaluated = 0
        markets_scanned = 0
        entry_taken = False

        for symbol in sorted(watch_symbols):
            market = market_by_symbol.get(symbol)
            if market is None:
                continue
            markets_scanned += 1
            history = fetch_ohlc_candles(
                symbol, interval=60, api_pair=market.get("api_pair"),
                min_order_qty=market.get("min_order_qty"),
                min_cost_eur=market.get("min_cost_quote"),
            )
            candles = history.get("candles", [])
            if len(candles) < 37:
                continue
            candle_time = int(candles[-1]["timestamp"])
            last_processed = int(processed.get(symbol) or 0)
            if last_processed >= candle_time:
                continue
            processed[symbol] = candle_time
            evaluated += 1
            cross_up, cross_down = _cross_signal(
                candles, after_timestamp=last_processed
            )
            position = state.get("positions", {}).get(symbol)

            if position and (cross_down or _momentum_exit_signal(candles, after_timestamp=last_processed)):
                quantity = str(position["quantity"])
                state = apply_paper_trade(
                    state, symbol=symbol, side="sell", quantity=quantity,
                    price_sek=Decimal(str(market["bid"])) * Decimal(str(rate)),
                    timestamp=now, marks_sek=marks,
                )
                actions.append({"symbol": symbol, "side": "paper_sell", "candle": candle_time})
            elif not position and (
                cross_up or _momentum_entry_signal(candles, after_timestamp=last_processed)
            ):
                current_positions = state.get("positions", {})
                current_equity = float(portfolio_snapshot(state, marks)["equity"])
                current_exposure = sum(
                    float(item["quantity"]) * float(marks[position_symbol])
                    for position_symbol, item in current_positions.items()
                )
                available_allocation = min(
                    current_equity * float(risk["max_trade_pct"]),
                    float(state["cash"]),
                )
                if entry_taken or len(current_positions) >= MAX_OPEN_POSITIONS or (
                    current_exposure + available_allocation
                    > current_equity * MAX_TOTAL_EXPOSURE_PCT
                ):
                    actions.append({"symbol": symbol, "side": "rejected_portfolio_exposure"})
                    continue
                ask_eur = float(market["ask"])
                ask_sek = Decimal(str(ask_eur)) * Decimal(str(rate))
                fee = Decimal(str(risk["fee_rate"]))
                slippage = Decimal(str(risk["slippage_rate"]))
                current_trade_budget = min(
                    current_equity * float(risk["max_trade_pct"]),
                    float(state["cash"]),
                )
                budget = min(
                    Decimal(str(current_trade_budget)),
                    Decimal(str(state["cash"])),
                )
                quantity = budget / (ask_sek * (Decimal("1") + slippage) * (Decimal("1") + fee))
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
                entry_taken = True

        worker_state.update({
            "status": "running",
            "last_marked_at": now.isoformat(),
            "last_marks_sek": marks,
            "last_error": None,
            "last_success_at": now.isoformat(),
            "last_fx": fx,
            "last_markets_found": len(markets),
            "last_markets_eligible": len(candidates),
            "last_markets_scanned": markets_scanned,
            "last_candles_evaluated": evaluated,
            "watchlist_cursor": next_watchlist_cursor,
            "processed_candles": dict(list(processed.items())[-100:]),
            "last_actions": actions[-MAX_WATCHLIST:],
        })
        state["worker"] = worker_state
        next_revision = save_state(state, revision)
        return {
            "ok": True, "status": "running", "paper_enabled": True,
            "markets_found": len(markets), "markets_eligible": len(candidates),
            "markets_scanned": markets_scanned,
            "candles_evaluated": evaluated, "actions": actions,
            "revision": next_revision, "orders_enabled": False,
            "withdrawals_enabled": False,
        }
    except (StrategyDataError, KrakenPublicAPIError, PaperTradingError, ValueError, KeyError, TypeError) as exc:
        error_text = str(exc)[:300]
        if isinstance(exc, PaperTradingError) and (
            "Dagens förlustgräns" in error_text or "Maximal portföljnedgång" in error_text
        ):
            state = activate_emergency_stop(state, error_text)
            worker_state["status"] = "emergency_stopped"
        else:
            worker_state["status"] = "waiting_for_valid_market_data"
        worker_state.update({
            "last_error": error_text,
            "last_success_at": worker_state.get("last_success_at"),
        })
        state["worker"] = worker_state
        next_revision = save_state(state, revision)
        return {
            "ok": False, "status": worker_state["status"],
            "error": worker_state["last_error"], "revision": next_revision,
            "orders_enabled": False, "withdrawals_enabled": False,
        }
