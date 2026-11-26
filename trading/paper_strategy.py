"""Deterministic, ranked strategy for paper-only evaluation."""
from __future__ import annotations

from typing import Any

from paper_engine import PaperBroker, TradeRejected

STRATEGY_NAME = "ranked_eur_spot_trend_rsi_volume_v2"
STOP_DISTANCE_PCT = 2.0
ENTRY_RSI_MIN = 50.0
ENTRY_RSI_MAX = 68.0
MIN_VOLUME_RATIO = 1.2
EXIT_RSI = 75.0


def run_cycle(broker: PaperBroker, market_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if broker.state.get("mode") != "paper":
        raise ValueError("This strategy is restricted to paper mode")
    by_symbol = {item["symbol"]: item for item in market_results if item.get("symbol")}
    processed = broker.state.setdefault("processed_candles", {})
    fresh = [
        item for item in market_results
        if item.get("symbol")
        and item.get("last_candle_timestamp") is not None
        and int(item["last_candle_timestamp"]) > int(processed.get(item["symbol"], -1))
    ]
    fresh_by_symbol = {item["symbol"]: item for item in fresh}
    prices = {
        symbol: float(item.get("mark_price_eur") or item["last_price_eur"])
        for symbol, item in by_symbol.items()
        if item.get("mark_price_eur") is not None or item.get("last_price_eur") is not None
    }
    if not fresh:
        return broker.check_stops(prices)

    actions = []
    actions.extend(broker.check_stops(prices))
    for symbol in list(broker.state["positions"]):
        item = fresh_by_symbol.get(symbol)
        if not item or symbol not in prices:
            continue
        rv = item.get("rsi14")
        if item.get("trend") == "bearish" or (rv is not None and float(rv) >= EXIT_RSI):
            actions.append(broker.sell(symbol, prices[symbol], reason="strategy_exit"))

    if not broker.state["positions"]:
        candidates = sorted(
            (
                item for item in fresh
                if item.get("symbol") in broker.allowed_symbols and not item.get("monitor_only", False)
            ),
            key=lambda item: (
                float(item.get("opportunity_score") or 0),
                float(item.get("quote_volume_24h_eur") or 0),
            ),
            reverse=True,
        )
        for item in candidates:
            symbol = item["symbol"]
            rv, vr = item.get("rsi14"), item.get("volume_ratio")
            if (
                item.get("trend") == "bullish"
                and rv is not None
                and ENTRY_RSI_MIN <= float(rv) <= ENTRY_RSI_MAX
                and vr is not None
                and float(vr) >= MIN_VOLUME_RATIO
            ):
                price = prices.get(symbol)
                if price is None:
                    continue
                try:
                    fill = broker.buy(
                        symbol,
                        price,
                        price * (1.0 - STOP_DISTANCE_PCT / 100.0),
                        prices=prices,
                        minimum_amount=item.get("minimum_order_amount"),
                        minimum_notional=item.get("minimum_order_cost_eur"),
                    )
                    actions.append({
                        "strategy": STRATEGY_NAME,
                        "opportunity_score": item.get("opportunity_score"),
                        **fill,
                    })
                    break
                except TradeRejected as exc:
                    actions.append({
                        "event": "entry_skipped",
                        "symbol": symbol,
                        "reason": str(exc),
                        "opportunity_score": item.get("opportunity_score"),
                    })
                    continue

    for symbol, item in by_symbol.items():
        if item.get("last_candle_timestamp") is not None:
            processed[symbol] = int(item["last_candle_timestamp"])
    broker._save()
    return actions
