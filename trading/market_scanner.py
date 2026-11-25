"""Read-only public-market scanner for JARVIS Trading.

This module never authenticates and never places orders.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Iterable

import ccxt


SYMBOLS = ("BTC/EUR", "ETH/EUR")
TIMEFRAME = "1h"
CANDLE_LIMIT = 100


def ema(values: Iterable[float], period: int) -> float | None:
    data = [float(v) for v in values]
    if period <= 0 or len(data) < period:
        return None
    alpha = 2.0 / (period + 1.0)
    current = sum(data[:period]) / period
    for value in data[period:]:
        current = alpha * value + (1.0 - alpha) * current
    return current


def rsi(values: Iterable[float], period: int = 14) -> float | None:
    data = [float(v) for v in values]
    if period <= 0 or len(data) <= period:
        return None
    changes = [data[i] - data[i - 1] for i in range(1, len(data))]
    gains = [max(change, 0.0) for change in changes]
    losses = [max(-change, 0.0) for change in changes]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for gain, loss in zip(gains[period:], losses[period:]):
        avg_gain = ((avg_gain * (period - 1)) + gain) / period
        avg_loss = ((avg_loss * (period - 1)) + loss) / period
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    relative_strength = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + relative_strength))


def analyse_candles(symbol: str, candles: list[list[float]]) -> dict:
    if len(candles) < 51:
        raise ValueError(f"Not enough candles for {symbol}: received {len(candles)}")
    closes = [float(candle[4]) for candle in candles]
    volumes = [float(candle[5]) for candle in candles]
    last_price = closes[-1]
    average_volume = sum(volumes[-21:-1]) / 20
    volume_ratio = (volumes[-1] / average_volume) if average_volume > 0 else None
    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50)
    current_rsi = rsi(closes, 14)

    if ema20 is not None and ema50 is not None and last_price > ema20 > ema50:
        trend = "bullish"
    elif ema20 is not None and ema50 is not None and last_price < ema20 < ema50:
        trend = "bearish"
    else:
        trend = "neutral"

    return {
        "symbol": symbol,
        "timeframe": TIMEFRAME,
        "last_candle_timestamp": int(candles[-1][0]),
        "last_price_eur": round(last_price, 2),
        "ema20": round(ema20, 2) if ema20 is not None else None,
        "ema50": round(ema50, 2) if ema50 is not None else None,
        "rsi14": round(current_rsi, 2) if current_rsi is not None else None,
        "volume_ratio": round(volume_ratio, 2) if volume_ratio is not None else None,
        "trend": trend,
        "signal": "watch_only",
        "warning": "Research signal only. No buy/sell recommendation or order.",
    }


def scan() -> dict:
    exchange = ccxt.kraken({"enableRateLimit": True, "timeout": 15000})
    results = []
    errors = []
    for symbol in SYMBOLS:
        try:
            candles = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=CANDLE_LIMIT)
            timeframe_ms = int(exchange.parse_timeframe(TIMEFRAME) * 1000)
            now_ms = exchange.milliseconds()
            closed_candles = [candle for candle in candles if int(candle[0]) + timeframe_ms <= now_ms]
            analysis = analyse_candles(symbol, closed_candles)
            try:
                ticker = exchange.fetch_ticker(symbol)
                mark = ticker.get("last")
                if mark is not None and float(mark) > 0:
                    analysis["mark_price_eur"] = round(float(mark), 2)
                    analysis["mark_price_source"] = "live_ticker"
                else:
                    analysis["mark_price_eur"] = analysis["last_price_eur"]
                    analysis["mark_price_source"] = "last_closed_candle_fallback"
            except Exception:
                analysis["mark_price_eur"] = analysis["last_price_eur"]
                analysis["mark_price_source"] = "last_closed_candle_fallback"
            results.append(analysis)
        except Exception as exc:  # Public-data failures must not stop the other pair.
            errors.append({"symbol": symbol, "error": str(exc)[:240]})
    return {
        "mode": "paper",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "exchange": "kraken",
        "results": results,
        "errors": errors,
        "orders_enabled": False,
    }


if __name__ == "__main__":
    print(json.dumps(scan(), indent=2))
