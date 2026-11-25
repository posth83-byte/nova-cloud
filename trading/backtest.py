"""Historical OHLCV backtest for the JARVIS paper strategy.

Signals are computed only from candles that have closed. Entries execute at the
next candle open, avoiding same-candle look-ahead. Stops are checked against
intrabar lows and use the worse of stop/open on a gap down. No live orders.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from market_scanner import ema, rsi


def _indicators(candles: list[list[float]], end: int) -> dict[str, Any]:
    window = candles[: end + 1]
    closes = [float(c[4]) for c in window]
    volumes = [float(c[5]) for c in window]
    if len(closes) < 51:
        return {}
    e20, e50, current_rsi = ema(closes, 20), ema(closes, 50), rsi(closes, 14)
    average_volume = sum(volumes[-21:-1]) / 20
    volume_ratio = volumes[-1] / average_volume if average_volume > 0 else None
    trend = "neutral"
    if e20 is not None and e50 is not None and closes[-1] > e20 > e50:
        trend = "bullish"
    elif e20 is not None and e50 is not None and closes[-1] < e20 < e50:
        trend = "bearish"
    return {"trend": trend, "rsi14": current_rsi, "volume_ratio": volume_ratio}


def run_backtest(
    candles: list[list[float]],
    starting_cash: float,
    fee_rate: float = 0.0026,
    slippage_rate: float = 0.0005,
    risk_pct: float = 1.0,
    daily_drawdown_pct: float = 2.0,
    stop_distance_pct: float = 2.0,
) -> dict[str, Any]:
    if len(candles) < 60:
        raise ValueError("At least 60 candles are required")
    if starting_cash <= 0 or not 0 <= fee_rate < 0.1 or not 0 <= slippage_rate < 0.1:
        raise ValueError("Invalid cash, fee or slippage configuration")
    if not 0 < risk_pct <= 1 or not 0 < daily_drawdown_pct <= 2:
        raise ValueError("Risk settings exceed the initial paper policy")

    cash = float(starting_cash)
    position = None
    fills: list[dict[str, Any]] = []
    equity_curve: list[dict[str, float]] = []
    day_start_equity = cash
    active_day = None
    peak_equity = cash
    max_drawdown_pct = 0.0
    blocked_days: set[str] = set()

    for i in range(50, len(candles) - 1):
        candle = candles[i]
        next_candle = candles[i + 1]
        timestamp = int(candle[0])
        day = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc).date().isoformat()
        if day != active_day:
            active_day = day
            day_start_equity = cash + (position["quantity"] * float(candle[4]) if position else 0.0)

        open_price, low_price, close_price = float(candle[1]), float(candle[3]), float(candle[4])
        # Stop first; if a candle gaps below the stop, assume fill at its open.
        if position:
            stop = position["stop_price"]
            if low_price <= stop:
                raw_exit = min(stop, open_price)
                exit_fill = raw_exit * (1.0 - slippage_rate)
                gross = position["quantity"] * exit_fill
                exit_fee = gross * fee_rate
                proceeds = gross - exit_fee
                pnl = proceeds - position["entry_cost"]
                cash += proceeds
                fills.append({
                    "side": "sell", "reason": "stop_loss", "timestamp": timestamp,
                    "price": exit_fill, "fee": exit_fee, "net_pnl": pnl,
                })
                position = None

        # Use the completed current candle to decide; execute only at next candle open.
        if position:
            indicators = _indicators(candles, i)
            if indicators.get("trend") == "bearish" or (
                indicators.get("rsi14") is not None and indicators["rsi14"] >= 75
            ):
                exit_raw = float(next_candle[1])
                exit_fill = exit_raw * (1.0 - slippage_rate)
                gross = position["quantity"] * exit_fill
                exit_fee = gross * fee_rate
                proceeds = gross - exit_fee
                pnl = proceeds - position["entry_cost"]
                cash += proceeds
                fills.append({
                    "side": "sell", "reason": "strategy_exit",
                    "timestamp": int(next_candle[0]), "price": exit_fill,
                    "fee": exit_fee, "net_pnl": pnl,
                })
                position = None

        marked_equity = cash + (position["quantity"] * close_price if position else 0.0)
        peak_equity = max(peak_equity, marked_equity)
        drawdown = (peak_equity - marked_equity) / peak_equity * 100 if peak_equity else 0.0
        max_drawdown_pct = max(max_drawdown_pct, drawdown)
        daily_floor = day_start_equity * (1.0 - daily_drawdown_pct / 100.0)
        if marked_equity <= daily_floor:
            blocked_days.add(day)

        if position is None and day not in blocked_days:
            indicators = _indicators(candles, i)
            if (
                indicators.get("trend") == "bullish"
                and indicators.get("rsi14") is not None
                and 50 <= indicators["rsi14"] <= 68
                and indicators.get("volume_ratio") is not None
                and indicators["volume_ratio"] >= 1.2
            ):
                entry_raw = float(next_candle[1])
                entry_fill = entry_raw * (1.0 + slippage_rate)
                stop = entry_fill * (1.0 - stop_distance_pct / 100.0)
                stop_fill = stop * (1.0 - slippage_rate)
                risk_per_unit = (
                    entry_fill - stop_fill
                    + entry_fill * fee_rate
                    + stop_fill * fee_rate
                )
                equity = cash
                quantity = min(
                    equity * (risk_pct / 100.0) / risk_per_unit,
                    cash / (entry_fill * (1.0 + fee_rate)),
                )
                notional = quantity * entry_fill
                entry_fee = notional * fee_rate
                total_cost = notional + entry_fee
                if quantity > 0 and total_cost <= cash:
                    cash -= total_cost
                    position = {
                        "quantity": quantity,
                        "entry_price": entry_fill,
                        "stop_price": stop,
                        "entry_cost": total_cost,
                    }
                    fills.append({
                        "side": "buy", "reason": "baseline_entry",
                        "timestamp": int(next_candle[0]), "price": entry_fill,
                        "fee": entry_fee, "quantity": quantity,
                    })

        mark = float(next_candle[4])
        equity = cash + (position["quantity"] * mark if position else 0.0)
        equity_curve.append({"timestamp": int(next_candle[0]), "equity": equity})

    if position:
        last = candles[-1]
        exit_fill = float(last[4]) * (1.0 - slippage_rate)
        gross = position["quantity"] * exit_fill
        exit_fee = gross * fee_rate
        proceeds = gross - exit_fee
        pnl = proceeds - position["entry_cost"]
        cash += proceeds
        fills.append({
            "side": "sell", "reason": "end_of_test",
            "timestamp": int(last[0]), "price": exit_fill,
            "fee": exit_fee, "net_pnl": pnl,
        })
        position = None

    sells = [fill for fill in fills if fill["side"] == "sell"]
    trade_pnls = [float(fill.get("net_pnl", 0.0)) for fill in sells]
    wins = [pnl for pnl in trade_pnls if pnl > 0]
    losses = [pnl for pnl in trade_pnls if pnl < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    net_profit = cash - starting_cash

    # Fee- and slippage-adjusted buy-and-hold benchmark over the same test window.
    benchmark_entry = float(candles[50][1]) * (1.0 + slippage_rate)
    benchmark_exit = float(candles[-1][4]) * (1.0 - slippage_rate)
    benchmark_quantity = starting_cash / (benchmark_entry * (1.0 + fee_rate))
    benchmark_ending = (
        benchmark_quantity * benchmark_exit * (1.0 - fee_rate)
    )
    benchmark_profit = benchmark_ending - starting_cash
    benchmark_return = benchmark_profit / starting_cash * 100.0

    return {
        "mode": "historical_backtest",
        "starting_cash": round(starting_cash, 8),
        "ending_cash": round(cash, 8),
        "net_profit": round(net_profit, 8),
        "net_return_pct": round(net_profit / starting_cash * 100, 4),
        "closed_trades": len(sells),
        "winning_trades": len(wins),
        "win_rate_pct": round(len(wins) / len(sells) * 100, 2) if sells else 0.0,
        "expectancy_per_trade": round(sum(trade_pnls) / len(trade_pnls), 8) if trade_pnls else None,
        "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss > 0 else (None if gross_profit == 0 else "infinite"),
        "gross_profit": round(gross_profit, 8),
        "gross_loss": round(gross_loss, 8),
        "buy_and_hold_ending_cash": round(benchmark_ending, 8),
        "buy_and_hold_net_profit": round(benchmark_profit, 8),
        "buy_and_hold_return_pct": round(benchmark_return, 4),
        "strategy_vs_buy_and_hold_pct_points": round(net_profit / starting_cash * 100.0 - benchmark_return, 4),
        "max_drawdown_pct": round(max_drawdown_pct, 4),
        "fees_and_slippage_included": True,
        "benchmark_costs_included": True,
        "lookahead_protection": "closed-candle signal; next-candle-open entry",
        "fills": fills,
        "equity_curve": equity_curve,
        "warning": "Historical simulation only. Does not predict or guarantee future returns.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Backtest JARVIS strategy on OHLCV JSON")
    parser.add_argument("--input", required=True, help="JSON file containing a list of OHLCV rows")
    parser.add_argument("--starting-cash", required=True, type=float, help="Starting balance in EUR")
    parser.add_argument("--output", default="trading/backtest-result.json")
    args = parser.parse_args()
    candles = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = run_backtest(candles, args.starting_cash)
    Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("fills", "equity_curve")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
