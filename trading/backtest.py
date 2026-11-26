"""Deterministic, out-of-sample SMA backtest. Simulation only; no order execution."""
from __future__ import annotations

from math import isfinite
from typing import Any


def run_sma_backtest(
    candles: list[dict[str, Any]],
    *,
    fx_sek_per_eur: float,
    starting_cash_sek: float = 200.0,
    min_order_qty: float = 0.0,
    min_cost_eur: float = 0.0,
    fast_window: int = 12,
    slow_window: int = 36,
    spread_pct: float = 0.20,
    fee_rate: float = 0.004,
    slippage_rate: float = 0.0015,
) -> dict[str, Any]:
    """Evaluate a fixed SMA crossover only on the final 30% of chronological candles.

    EUR quote prices are converted to SEK using one current reference FX rate.
    This is explicitly an approximation, not historical FX accounting.
    """
    if not (isfinite(fx_sek_per_eur) and fx_sek_per_eur > 0):
        raise ValueError("Ogiltig EUR/SEK-kurs.")
    if not (isfinite(starting_cash_sek) and starting_cash_sek > 0):
        raise ValueError("Ogiltigt startkapital.")
    if fast_window < 2 or slow_window <= fast_window:
        raise ValueError("Ogiltiga SMA-perioder.")
    if not 0 <= spread_pct <= 5 or not 0 <= fee_rate <= 0.05 or not 0 <= slippage_rate <= 0.05:
        raise ValueError("Ogiltiga kostnadsantaganden.")

    clean = []
    for candle in candles:
        try:
            timestamp = int(candle["timestamp"])
            close = float(candle["close"])
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        if timestamp > 0 and isfinite(close) and close > 0:
            clean.append({"timestamp": timestamp, "close": close})
    clean.sort(key=lambda row: row["timestamp"])
    # Remove duplicate timestamps deterministically, retaining the last value.
    unique = {row["timestamp"]: row for row in clean}
    clean = [unique[key] for key in sorted(unique)]
    if len(clean) < slow_window + 20:
        raise ValueError("För få giltiga historiska ljusstakar för ett meningsfullt test.")

    closes = [row["close"] for row in clean]
    split = max(slow_window + 1, int(len(clean) * 0.70))
    if len(clean) - split < 10:
        raise ValueError("För kort out-of-sample-period.")

    cash = (starting_cash_sek / fx_sek_per_eur)
    starting_cash_eur = cash
    quantity = 0.0
    entry_cost = 0.0
    trades = []
    rejected_minimums = 0
    equity_curve = []
    peak = starting_cash_eur
    max_drawdown = 0.0
    spread = spread_pct / 100.0
    max_trade_eur = (starting_cash_sek * 0.10 / fx_sek_per_eur) / (1 + fee_rate + slippage_rate)
    max_position_eur = starting_cash_sek * 0.25 / fx_sek_per_eur

    def sma(end_index: int, window: int) -> float:
        return sum(closes[end_index - window + 1:end_index + 1]) / window

    for index in range(split, len(clean)):
        price = closes[index]
        fast_now = sma(index, fast_window)
        slow_now = sma(index, slow_window)
        fast_prev = sma(index - 1, fast_window)
        slow_prev = sma(index - 1, slow_window)
        cross_up = fast_prev <= slow_prev and fast_now > slow_now
        cross_down = fast_prev >= slow_prev and fast_now < slow_now

        if quantity == 0 and cross_up:
            ask = price * (1 + spread / 2)
            fill = ask * (1 + slippage_rate)
            spend = min(cash, max_trade_eur, max_position_eur)
            qty = spend / (fill * (1 + fee_rate))
            required_qty = max(0.0, min_order_qty)
            required_cost = max(0.0, min_cost_eur)
            if qty + 1e-12 < required_qty or qty * ask < required_cost:
                rejected_minimums += 1
            else:
                gross = qty * fill
                fee = gross * fee_rate
                total = gross + fee
                if total <= cash and total <= max_position_eur:
                    cash -= total
                    quantity = qty
                    entry_cost = total
                    trades.append({
                        "timestamp": clean[index]["timestamp"],
                        "side": "buy",
                        "price_eur": round(fill, 8),
                        "quantity": round(qty, 12),
                        "fee_eur": round(fee, 8),
                    })
        elif quantity > 0 and cross_down:
            bid = price * (1 - spread / 2)
            fill = bid * (1 - slippage_rate)
            gross = quantity * fill
            fee = gross * fee_rate
            proceeds = gross - fee
            pnl = proceeds - entry_cost
            cash += proceeds
            trades.append({
                "timestamp": clean[index]["timestamp"],
                "side": "sell",
                "price_eur": round(fill, 8),
                "quantity": round(quantity, 12),
                "fee_eur": round(fee, 8),
                "net_trade_pnl_eur": round(pnl, 8),
            })
            quantity = 0.0
            entry_cost = 0.0

        equity = cash + quantity * price
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - equity) / peak)
        equity_curve.append(equity)

    # Close any remaining simulated position at the final available close.
    if quantity > 0:
        price = closes[-1] * (1 - spread / 2) * (1 - slippage_rate)
        gross = quantity * price
        fee = gross * fee_rate
        proceeds = gross - fee
        pnl = proceeds - entry_cost
        cash += proceeds
        trades.append({
            "timestamp": clean[-1]["timestamp"],
            "side": "sell_end_of_test",
            "price_eur": round(price, 8),
            "quantity": round(quantity, 12),
            "fee_eur": round(fee, 8),
            "net_trade_pnl_eur": round(pnl, 8),
        })
        quantity = 0.0

    net_eur = cash - starting_cash_eur
    sell_trades = [trade for trade in trades if trade["side"].startswith("sell")]
    trade_pnls = [trade.get("net_trade_pnl_eur", 0.0) for trade in sell_trades]
    winners = sum(1 for pnl in trade_pnls if pnl > 0)

    # Same-sized buy-and-hold benchmark with identical costs and exchange minimums.
    benchmark_cash = starting_cash_eur
    benchmark_executed = False
    benchmark_entry = closes[split] * (1 + spread / 2) * (1 + slippage_rate)
    benchmark_spend = min(benchmark_cash, max_trade_eur, max_position_eur)
    benchmark_qty = benchmark_spend / (benchmark_entry * (1 + fee_rate))
    if (benchmark_qty + 1e-12 >= max(0.0, min_order_qty)
            and benchmark_qty * closes[split] * (1 + spread / 2) >= max(0.0, min_cost_eur)):
        benchmark_cost = benchmark_qty * benchmark_entry * (1 + fee_rate)
        if benchmark_cost <= benchmark_cash and benchmark_cost <= max_position_eur:
            benchmark_cash -= benchmark_cost
            benchmark_executed = True
            benchmark_exit = closes[-1] * (1 - spread / 2) * (1 - slippage_rate)
            benchmark_cash += benchmark_qty * benchmark_exit * (1 - fee_rate)
    benchmark_net_eur = benchmark_cash - starting_cash_eur
    return {
        "mode": "historical_backtest_only",
        "execution_enabled": False,
        "orders_enabled": False,
        "withdrawals_enabled": False,
        "strategy": "SMA crossover (12/36)",
        "sample": {
            "candles": len(clean),
            "in_sample_candles": split,
            "out_of_sample_candles": len(clean) - split,
            "out_of_sample_start": clean[split]["timestamp"],
            "out_of_sample_end": clean[-1]["timestamp"],
        },
        "assumptions": {
            "starting_cash_sek": round(starting_cash_sek, 2),
            "fx_sek_per_eur": fx_sek_per_eur,
            "fx_method": "current reference rate applied uniformly; historical FX unavailable",
            "spread_pct": spread_pct,
            "fee_rate": fee_rate,
            "slippage_rate": slippage_rate,
            "max_trade_pct": 0.10,
            "max_position_pct": 0.25,
        },
        "results": {
            "net_profit_sek_est": round(net_eur * fx_sek_per_eur, 2),
            "return_pct": round((net_eur / starting_cash_eur) * 100, 3),
            "max_drawdown_pct": round(max_drawdown * 100, 3),
            "closed_trades": len(sell_trades),
            "win_rate_pct": round((winners / len(sell_trades)) * 100, 2) if sell_trades else None,
            "average_net_trade_pnl_sek_est": round((sum(trade_pnls) / len(trade_pnls)) * fx_sek_per_eur, 2) if trade_pnls else None,
            "expectancy_sek_est": round((sum(trade_pnls) / len(trade_pnls)) * fx_sek_per_eur, 2) if trade_pnls else None,
            "buy_and_hold_net_profit_sek_est": round(benchmark_net_eur * fx_sek_per_eur, 2),
            "buy_and_hold_return_pct": round((benchmark_net_eur / starting_cash_eur) * 100, 3),
            "buy_and_hold_executed": benchmark_executed,
            "rejected_for_exchange_minimum": rejected_minimums,
            "ending_cash_sek_est": round(cash * fx_sek_per_eur, 2),
        },
        "trades": trades[-50:],
        "note": "Historiskt test på sista 30 % av datan. Resultat är inte en prognos eller köp-/säljsignal.",
    }
