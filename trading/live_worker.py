"""Autonomous, fail-closed Kraken Spot live worker.

Uses the same closed-candle SMA cross as the paper worker, but keeps a
separate SEK ledger, journals every order before submission, and never
retries an ambiguous exchange outcome.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_DOWN, ROUND_UP, ROUND_HALF_UP
import uuid
from typing import Any

from trading.kraken_monitor import KrakenPublicAPIError, fetch_ohlc_candles, scan_markets
from trading.strategy import StrategyDataError, fetch_eur_sek_rate
from trading.opportunity_radar import rank_opportunities
from trading.worker import (
    _cross_signal, _momentum_entry_signal, _momentum_exit_signal,
    _select_watchlist, MAX_WATCHLIST,
)
from trading.kraken_private import (
    KrakenPrivateAPIError,
    get_account_balances,
    get_open_orders,
    run_read_only_preflight,
    validate_limit_order,
)
from trading.live_engine import (
    LiveExecutionError,
    execute_journaled_limit_order,
    reconcile_order_intent,
)
from trading.live_store import (
    LiveStoreError,
    get_order_intent,
    list_unapplied_order_intents,
    load_or_create_live_state,
    mark_order_ledger_applied,
    save_live_state,
)

MAX_OPEN_POSITIONS = 3
MAX_SPREAD_PCT = 0.35
MIN_TURNOVER_EUR = 10_000.0
ZERO = Decimal("0")
CENT = Decimal("0.01")


class LiveWorkerError(RuntimeError):
    """A safe, fail-closed live worker error."""


def _d(value: Any) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite():
        raise LiveWorkerError("Ogiltigt numeriskt värde i livehandeln.")
    return result


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _acquire_lease(
    state: dict[str, Any], revision: int, now: datetime
) -> tuple[dict[str, Any], int, str | None]:
    """Acquire a short database-CAS lease so manual and scheduled ticks cannot overlap."""
    worker = dict(state.get("worker") or {})
    lease_until_raw = worker.get("lease_until")
    if lease_until_raw:
        try:
            lease_until = datetime.fromisoformat(str(lease_until_raw))
            if lease_until.tzinfo is None:
                lease_until = lease_until.replace(tzinfo=timezone.utc)
            if lease_until > now:
                return state, revision, None
        except ValueError:
            # Malformed lease is treated as expired, then replaced atomically.
            pass
    lease_id = uuid.uuid4().hex
    worker["lease_id"] = lease_id
    worker["lease_until"] = (now + timedelta(minutes=6)).isoformat()
    state["worker"] = worker
    return state, save_live_state(state, revision), lease_id


def _clear_lease(state: dict[str, Any]) -> dict[str, Any]:
    worker = dict(state.get("worker") or {})
    worker.pop("lease_id", None)
    worker.pop("lease_until", None)
    state["worker"] = worker
    return state


def _halt(state: dict[str, Any], reason: str) -> dict[str, Any]:
    state["enabled"] = False
    state["emergency_stop"] = True
    state["stop_reason"] = str(reason)[:240]
    state["worker"] = {
        **{key: value for key, value in dict(state.get("worker") or {}).items()
           if key not in {"lease_id", "lease_until"}},
        "status": "emergency_stopped",
        "last_error": str(reason)[:240],
        "last_tick_at": datetime.now(timezone.utc).isoformat(),
    }
    return state


def _apply_intent_fill(
    state: dict[str, Any], intent: dict[str, Any], fx_rate: Decimal
) -> dict[str, Any]:
    """Apply one confirmed exchange fill exactly once to the live-only ledger."""
    client_id = str(intent["client_order_id"])
    applied = set(state.get("applied_order_ids") or [])
    if client_id in applied:
        return state
    exchange = intent.get("exchange_result") or {}
    quantity = _d(exchange.get("vol_exec") or "0")
    cost_eur = _d(exchange.get("cost") or "0")
    fee_eur = _d(exchange.get("fee") or "0")
    if min(quantity, cost_eur, fee_eur) < ZERO:
        raise LiveWorkerError("Kraken rapporterade negativa avslutsvärden.")
    if quantity > ZERO:
        gross_sek = cost_eur * fx_rate
        fee_sek = fee_eur * fx_rate
        positions = dict(state.get("positions") or {})
        symbol = str(intent["pair_symbol"])
        current_cash = _d(state["cash_sek"])
        if intent["side"] == "buy":
            total_cost = gross_sek + fee_sek
            if total_cost > current_cash:
                raise LiveWorkerError("Bekräftat köp överstiger livebokens disponibla saldo.")
            old = positions.get(symbol, {})
            old_qty = _d(old.get("quantity") or "0")
            old_basis = _d(old.get("cost_basis_sek") or "0")
            new_qty = old_qty + quantity
            total_basis = old_qty * old_basis + total_cost
            positions[symbol] = {
                "quantity": format(new_qty, "f"),
                "cost_basis_sek": format(total_basis / new_qty, "f"),
                "base_asset": str(intent.get("base_asset") or ""),
            }
            state["cash_sek"] = format(_round_money(current_cash - total_cost), "f")
            realized = ZERO
        elif intent["side"] == "sell":
            old = positions.get(symbol)
            if not old:
                raise LiveWorkerError("Kraken sålde en tillgång som saknas i livebokens innehav.")
            old_qty = _d(old["quantity"])
            if quantity > old_qty:
                raise LiveWorkerError("Bekräftat sälj överstiger livebokens registrerade innehav.")
            net_proceeds = gross_sek - fee_sek
            basis = _d(old["cost_basis_sek"])
            realized = net_proceeds - basis * quantity
            remaining = old_qty - quantity
            if remaining == ZERO:
                positions.pop(symbol, None)
            else:
                positions[symbol] = {**old, "quantity": format(remaining, "f")}
            state["cash_sek"] = format(_round_money(current_cash + net_proceeds), "f")
            state["realized_pnl_sek"] = format(
                _round_money(_d(state.get("realized_pnl_sek") or "0") + realized), "f"
            )
        else:
            raise LiveWorkerError("Orderjournalen innehåller en okänd orderriktning.")
        state["positions"] = positions
        trades = list(state.get("trades") or [])
        trades.append({
            "timestamp": str(intent.get("updated_at") or datetime.now(timezone.utc).isoformat()),
            "client_order_id": client_id,
            "pair": symbol,
            "side": str(intent["side"]),
            "quantity": format(quantity, "f"),
            "cost_sek": format(_round_money(gross_sek), "f"),
            "fee_sek": format(_round_money(fee_sek), "f"),
            "realized_pnl_sek": format(_round_money(realized), "f"),
            "mode": "live_spot",
        })
        state["trades"] = trades[-500:]
    state["applied_order_ids"] = list(applied | {client_id})[-500:]
    return state


def _recover_unapplied(
    state: dict[str, Any], revision: int, fx_rate: Decimal
) -> tuple[dict[str, Any], int, bool]:
    """Reconcile prior orders and apply their fills before considering new signals."""
    rows = list_unapplied_order_intents()
    if not rows:
        return state, revision, False
    changed = False
    for row in rows:
        client_id = str(row["client_order_id"])
        if row.get("status") == "prepared":
            from trading.live_store import update_order_intent
            update_order_intent(client_id, status="rejected", exchange_result={
                "reason": "prepared_intent_never_submitted"
            })
            row = get_order_intent(client_id) or row
        elif row.get("status") not in {"closed", "rejected"}:
            result = reconcile_order_intent(client_id)
            if result.get("status") not in {"closed", "rejected"}:
                raise LiveWorkerError(
                    "En tidigare order har okänt eller öppet utfall. Livehandeln stoppas för avstämning."
                )
            row = get_order_intent(client_id) or row
        if client_id not in set(state.get("applied_order_ids") or []):
            state = _apply_intent_fill(state, row, fx_rate)
            changed = True
        # Persist the ledger first. applied_order_ids makes recovery idempotent.
        if changed:
            revision = save_live_state(state, revision)
            changed = False
        mark_order_ledger_applied(client_id)
    return state, revision, True


def run_live_tick() -> dict[str, Any]:
    """Evaluate closed Kraken candles and execute at most one guarded Spot order."""
    state, revision = load_or_create_live_state()
    now = datetime.now(timezone.utc)
    worker = dict(state.get("worker") or {})
    worker["last_tick_at"] = now.isoformat()
    state["worker"] = worker

    if state.get("emergency_stop") or not state.get("enabled"):
        worker["status"] = "emergency_stopped" if state.get("emergency_stop") else "disabled"
        state["worker"] = worker
        return {
            "ok": True, "status": worker["status"], "live_enabled": False,
            "orders_enabled": False, "withdrawals_enabled": False,
        }

    try:
        state, revision, lease_id = _acquire_lease(state, revision, now)
        if lease_id is None:
            return {
                "ok": True, "status": "already_running",
                "live_enabled": True, "orders_enabled": False,
                "withdrawals_enabled": False,
            }
        worker = dict(state.get("worker") or {})
        fx = fetch_eur_sek_rate()
        rate = _d(fx["rate"])
        preflight = run_read_only_preflight(rate)
        if not preflight.get("connected") or not preflight.get("open_orders_clear"):
            raise LiveWorkerError("Kraken-kontot eller öppna order klarade inte säkerhetskontrollen.")
        balances = get_account_balances()
        eur_balance = _d(balances.get("ZEUR", balances.get("EUR", "0")))
        # Kraken is the source of truth for spendable EUR cash. This lets
        # new deposits increase the trading budget automatically; the old
        # local 200 SEK seed is not a permanent cap.
        available_sek = _round_money(eur_balance * rate)
        state["cash_sek"] = format(available_sek, "f")

        markets_result = scan_markets(
            quote="EUR", limit=100,
            include_symbols=list((state.get("positions") or {}).keys()),
        )
        markets = markets_result.get("markets") or []
        by_symbol = {str(row.get("symbol", "")).upper(): row for row in markets}
        positions = dict(state.get("positions") or {})
        missing = [symbol for symbol in positions if symbol.upper() not in by_symbol]
        if missing:
            raise LiveWorkerError("Saknar färsk marknadsdata för innehav: " + ", ".join(missing))
        marks = {
            symbol: _d(row["last"]) * rate
            for symbol, row in by_symbol.items()
            if _d(row.get("last") or 0) > ZERO
        }
        equity = available_sek + sum(
            _d(item["quantity"]) * marks[symbol]
            for symbol, item in positions.items()
        )
        if equity <= ZERO:
            raise LiveWorkerError("Liveportföljens värde är ogiltigt.")
        day_key = now.date().isoformat()
        if state.get("day_key") != day_key:
            state["day_key"] = day_key
            state["day_start_equity_sek"] = format(_round_money(equity), "f")
        peak = max(_d(state.get("peak_equity_sek") or "200"), equity)
        state["peak_equity_sek"] = format(_round_money(peak), "f")
        day_start = _d(state.get("day_start_equity_sek") or equity)
        if equity <= day_start * Decimal("0.98"):
            raise LiveWorkerError("Dagens förlustgräns på 2 procent är nådd.")
        if equity <= peak * Decimal("0.90"):
            raise LiveWorkerError("Maximal portföljnedgång på 10 procent är nådd.")

        state, revision, recovered = _recover_unapplied(state, revision, rate)
        if recovered:
            state = _clear_lease(state)
            worker = dict(state.get("worker") or {})
            worker.update({
                "status": "reconciled_previous_order",
                "last_success_at": now.isoformat(),
                "last_error": None,
                "last_fx": fx,
            })
            state["worker"] = worker
            revision = save_live_state(state, revision)
            return {
                "ok": True, "status": "reconciled_previous_order",
                "live_enabled": bool(state.get("enabled")),
                "actions": [], "revision": revision,
                "orders_enabled": False, "withdrawals_enabled": False,
            }
        positions = dict(state.get("positions") or {})
        risk = state["risk"]
        # Dynamic ceiling: all current EUR cash plus live positions, bounded
        # by the actual marked live portfolio equity rather than a fixed seed.
        exposure = sum(
            _d(item["quantity"]) * marks[symbol]
            for symbol, item in positions.items()
        )
        eligible = []
        for row in markets:
            try:
                ask, bid = _d(row["ask"]), _d(row["bid"])
                spread = _d(row["spread_pct"])
                turnover = _d(row["volume_24h_quote_est"])
                min_qty = _d(row.get("min_order_qty") or 0)
                min_cost = _d(row.get("min_cost_quote") or 0)
            except (KeyError, ValueError, TypeError):
                continue
            if ask <= ZERO or bid <= ZERO or ask < bid:
                continue
            if spread > Decimal(str(MAX_SPREAD_PCT)) or turnover < Decimal(str(MIN_TURNOVER_EUR)):
                continue
            if max(min_cost, min_qty * ask) * rate > available_sek:
                continue
            eligible.append(row)
        radar = rank_opportunities(
            eligible, equity_sek=max(float(available_sek), 0.01),
            eur_sek=float(rate), limit=max(1, len(eligible)),
        ) if eligible else {"candidates": []}
        radar_scores = {row["symbol"]: float(row["score"]) for row in radar["candidates"]}
        eligible.sort(key=lambda row: (
            -radar_scores.get(str(row.get("symbol", "")).upper(), 0.0),
            float(row.get("spread_pct") or 99),
            -float(row.get("volume_24h_quote_est") or 0),
        ))
        watch, next_cursor = _select_watchlist(
            eligible, positions, int(worker.get("watchlist_cursor") or 0)
        )
        processed = dict(worker.get("processed_candles") or {})
        evaluated = 0
        actions: list[dict[str, Any]] = []
        order_sent = False

        for symbol in sorted(watch):
            if order_sent:
                break
            market = by_symbol.get(symbol)
            if not market:
                continue
            history = fetch_ohlc_candles(
                symbol, interval=60, api_pair=market.get("api_pair"),
                min_order_qty=market.get("min_order_qty"),
                min_cost_eur=market.get("min_cost_quote"),
            )
            candles = history.get("candles") or []
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
            position = positions.get(symbol)
            side = (
                "sell" if position and (cross_down or _momentum_exit_signal(candles, after_timestamp=last_processed))
                else "buy" if not position and (
                    cross_up or _momentum_entry_signal(candles, after_timestamp=last_processed)
                )
                else None
            )
            if side is None:
                continue

            pair = str(market.get("api_pair") or "").upper()
            if not pair or not pair.isalnum():
                raise LiveWorkerError("Kraken saknar giltig API-paridentifierare.")
            base_asset = str(market.get("base_asset") or "")
            if side == "buy":
                if len(positions) >= MAX_OPEN_POSITIONS:
                    actions.append({"symbol": symbol, "result": "max_positions"})
                    continue
                remaining_cap = max(ZERO, equity - exposure)
                spend_budget = min(available_sek, remaining_cap)
                fee_rate = _d(risk["fee_rate"])
                slippage = _d(risk["slippage_rate"])
                ask = _d(market["ask"])
                price_decimals = int(market.get("price_decimals") or 8)
                limit_price = ask.quantize(
                    Decimal(1).scaleb(-price_decimals), rounding=ROUND_UP
                )
                raw_qty = spend_budget / (
                    limit_price * rate * (Decimal("1") + fee_rate + slippage)
                )
                lot_decimals = int(market.get("lot_decimals") or 8)
                qty = raw_qty.quantize(Decimal(1).scaleb(-lot_decimals), rounding=ROUND_DOWN)
                min_qty = _d(market.get("min_order_qty") or 0)
                min_cost = _d(market.get("min_cost_quote") or 0)
                if qty <= ZERO or qty < min_qty or qty * limit_price < min_cost:
                    actions.append({"symbol": symbol, "result": "below_exchange_minimum"})
                    continue
            else:
                qty = _d(position["quantity"])
                actual_asset_balance = _d(balances.get(base_asset, "0"))
                if not base_asset or actual_asset_balance < qty:
                    raise LiveWorkerError("Kraken-saldo för innehavet understiger livebokens registrerade mängd.")
                bid = _d(market["bid"])
                price_decimals = int(market.get("price_decimals") or 8)
                limit_price = bid.quantize(
                    Decimal(1).scaleb(-price_decimals), rounding=ROUND_DOWN
                )
                lot_decimals = int(market.get("lot_decimals") or 8)
                qty = qty.quantize(Decimal(1).scaleb(-lot_decimals), rounding=ROUND_DOWN)

            # Persist the candle cursor before placing any order. If the
            # process crashes after a fill, this signal cannot fire twice.
            worker["processed_candles"] = dict(list(processed.items())[-100:])
            worker["watchlist_cursor"] = next_cursor
            state["worker"] = worker
            revision = save_live_state(state, revision)
            if get_open_orders():
                raise LiveWorkerError(
                    "En öppen Kraken-order upptäcktes precis före orderläggning. Livehandeln stoppas."
                )
            validation = validate_limit_order(
                pair=pair, side=side, volume=qty, price=limit_price
            )
            if not validation.get("validated"):
                raise LiveWorkerError("Kraken godkände inte ordervalideringen.")
            result = execute_journaled_limit_order(
                pair=pair, side=side, volume=qty, price=limit_price,
                pair_symbol=symbol, base_asset=base_asset,
            )
            if result.get("status") != "closed":
                raise LiveWorkerError("Orderns slutstatus är inte bekräftad; ingen ny order skickas.")
            client_id = str(result["client_order_id"])
            intent = get_order_intent(client_id)
            if not intent:
                raise LiveWorkerError("Ordern saknas i livejournalen efter Kraken-svar.")
            # Market metadata was journaled before Kraken received the order.
            state = _apply_intent_fill(state, intent, rate)
            revision = save_live_state(state, revision)
            mark_order_ledger_applied(client_id)
            actions.append({
                "symbol": symbol, "side": "live_" + side,
                "filled_quantity": result.get("vol_exec", "0"),
                "order_id": client_id,
            })
            order_sent = True

        state = _clear_lease(state)
        worker = dict(state.get("worker") or {})
        worker.update({
            "status": "running",
            "last_success_at": now.isoformat(),
            "last_error": None,
            "last_fx": fx,
            "last_markets_found": len(markets),
            "last_markets_eligible": len(eligible),
            "last_markets_scanned": len(watch),
            "last_candles_evaluated": evaluated,
            "watchlist_cursor": next_cursor,
            "processed_candles": dict(list(processed.items())[-100:]),
            "last_actions": actions[-MAX_WATCHLIST:],
            "last_equity_sek": format(_round_money(equity), "f"),
        })
        state["worker"] = worker
        revision = save_live_state(state, revision)
        return {
            "ok": True, "status": "running", "live_enabled": True,
            "markets_found": len(markets), "markets_eligible": len(eligible),
            "candles_evaluated": evaluated, "actions": actions,
            "revision": revision, "orders_enabled": True,
            "withdrawals_enabled": False,
        }
    except (
        StrategyDataError, KrakenPublicAPIError, KrakenPrivateAPIError,
        LiveExecutionError, LiveStoreError, LiveWorkerError, ValueError, KeyError, TypeError
    ) as exc:
        reason = str(exc)[:240]
        try:
            state = _halt(state, reason)
            revision = save_live_state(state, revision)
            return {
                "ok": False, "status": "emergency_stopped", "reason": reason,
                "revision": revision, "live_enabled": False,
                "orders_enabled": False, "withdrawals_enabled": False,
            }
        except LiveStoreError:
            return {
                "ok": False, "status": "journal_unavailable",
                "reason": "Livejournalen kunde inte uppdateras; ingen ny order får skickas.",
                "live_enabled": False, "orders_enabled": False,
                "withdrawals_enabled": False,
            }
