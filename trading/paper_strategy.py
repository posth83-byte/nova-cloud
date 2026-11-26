"""Deterministic baseline strategy for paper-only evaluation.

This is a deliberately simple research baseline, not a profit promise. It only
creates paper trades through PaperBroker; it has no exchange/order API.
"""
from __future__ import annotations

from typing import Any

from paper_engine import PaperBroker


STRATEGY_NAME = "ema_trend_rsi_volume_v1"
STOP_DISTANCE_PCT = 2.0
ENTRY_RSI_MIN = 50.0
ENTRY_RSI_MAX = 68.0
MIN_VOLUME_RATIO = 1.2
EXIT_RSI = 75.0


def run_cycle(broker: PaperBroker, market_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if broker.state.get("mode") != "paper":
        raise ValueError("This strategy is restricted to paper mode")

    new_results = []
    processed = broker.state.setdefault("processed_candles", {})
    by_symbol = {item["symbol"]: item for item in market_results if item.get("symbol")}
    for item in market_results:
        symbol = item.get("symbol")
        candle_ts = item.get("last_candle_timestamp")
        if symbol and candle_ts is not None and int(candle_ts) > int(processed.get(symbol, -1)):
            new_results.append(item)
    fresh_by_symbol = {item["symbol"]: item for item in new_results if item.get("symbol")}
    prices = {
        symbol: float(item.get("mark_price_eur") or item["last_price_eur"])
        for symbol, item in by_symbol.items()
        if item.get("mark_price_eur") is not None or item.get("last_price_eur") is not None
    }
    if not new_results:
        # Even without a new closed candle, refresh stop monitoring with available marks.
        return broker.check_stops(prices)
    actions: list[dict[str, Any]] = []

    # Stops are evaluated before any other decision.
    actions.extend(broker.check_stops(prices))

    # Exit an existing position when the trend breaks or momentum becomes extreme.
    for symbol in list(broker.state["positions"]):
        item = fresh_by_symbol.get(symbol)
        if not item or symbol not in prices:
            continue
        rsi = item.get("rsi14")
        if item.get("trend") == "bearish" or (rsi is not None and float(rsi) >= EXIT_RSI):
            actions.append(broker.sell(symbol, prices[symbol], reason="strategy_exit"))

    # One position maximum. Rank is deterministic: first allowlisted qualifying pair.
    if not broker.state["positions"]:
        for symbol in broker.allowed_symbols:
            item = fresh_by_symbol.get(symbol)
            if not item or symbol not in prices:
                continue
            rsi = item.get("rsi14")
            volume_ratio = item.get("volume_ratio")
            if (
                item.get("trend") == "bullish"
                and rsi is not None
                and ENTRY_RSI_MIN <= float(rsi) <= ENTRY_RSI_MAX
                and volume_ratio is not None
                and float(volume_ratio) >= MIN_VOLUME_RATIO
            ):
                price = prices[symbol]
                stop = price * (1.0 - STOP_DISTANCE_PCT / 100.0)
                fill = broker.buy(
                    symbol,
                    price,
                    stop,
                    prices=prices,
                    minimum_amount=item.get("minimum_order_amount"),
                )
                actions.append({"strategy": STRATEGY_NAME, **fill})
                break

    for symbol, item in by_symbol.items():
        if item.get("last_candle_timestamp") is not None:
            processed[symbol] = int(item["last_candle_timestamp"])
    broker._save()
    return actions
