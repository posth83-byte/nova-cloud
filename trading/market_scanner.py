"""Read-only Kraken EUR spot-universe scanner for JARVIS Trading."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Iterable

import ccxt

TIMEFRAME = "1h"
CANDLE_LIMIT = 100
MAX_ANALYSIS_MARKETS = 30
MIN_QUOTE_VOLUME_EUR = 100_000.0
MAX_SPREAD_PCT = 0.60
EXCLUDED_BASES = {
    "EUR", "USD", "USDT", "USDC", "DAI", "EURC", "TUSD", "PYUSD",
    "USDE", "FDUSD", "UST", "USTC", "USDD",
}


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
    gains = [max(c, 0.0) for c in changes]
    losses = [max(-c, 0.0) for c in changes]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for gain, loss in zip(gains[period:], losses[period:]):
        avg_gain = ((avg_gain * (period - 1)) + gain) / period
        avg_loss = ((avg_loss * (period - 1)) + loss) / period
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    return 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))


def analyse_candles(symbol: str, candles: list[list[float]]) -> dict:
    if len(candles) < 51:
        raise ValueError(f"Not enough candles for {symbol}: received {len(candles)}")
    closes = [float(c[4]) for c in candles]
    volumes = [float(c[5]) for c in candles]
    last_price = closes[-1]
    avg_volume = sum(volumes[-21:-1]) / 20
    volume_ratio = volumes[-1] / avg_volume if avg_volume > 0 else None
    ema20, ema50 = ema(closes, 20), ema(closes, 50)
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
        "last_price_eur": round(last_price, 8),
        "ema20": round(ema20, 8) if ema20 is not None else None,
        "ema50": round(ema50, 8) if ema50 is not None else None,
        "rsi14": round(current_rsi, 2) if current_rsi is not None else None,
        "volume_ratio": round(volume_ratio, 2) if volume_ratio is not None else None,
        "trend": trend,
        "signal": "watch_only",
        "warning": "Research signal only. No buy/sell recommendation or order.",
    }


def discover_eur_spot_markets(markets: dict) -> list[str]:
    symbols = []
    for symbol, market in markets.items():
        if not market.get("active", True):
            continue
        if market.get("spot") is False or market.get("swap") or market.get("future") or market.get("option"):
            continue
        if market.get("quote") != "EUR" or market.get("base") in EXCLUDED_BASES:
            continue
        if market.get("type") not in (None, "spot"):
            continue
        symbols.append(symbol)
    return sorted(set(symbols))


def rank_opportunity(item: dict) -> float:
    score = 40.0 if item.get("trend") == "bullish" else 0.0
    rv = item.get("rsi14")
    if rv is not None and 50 <= float(rv) <= 68:
        score += 20.0
    vr = item.get("volume_ratio")
    if vr is not None:
        score += min(max(float(vr) - 1.0, 0.0), 3.0) * 8.0
    change = item.get("change_24h_pct")
    if change is not None and float(change) > 0:
        score += min(float(change), 10.0)
    spread = item.get("spread_pct")
    if spread is not None:
        score += max(0.0, 10.0 - float(spread) * 10.0)
    return round(score, 2)


def select_shortlist(
    liquid: list[tuple[float, str, dict, float]],
    required_symbols: Iterable[str],
    markets: dict,
    tickers: dict,
) -> tuple[list[tuple[float, str, dict, float]], set[str]]:
    """Keep the normal top-30 scan while reserving a slot for each open position.

    A required position that fails discovery liquidity filters is included only
    for monitoring and must never become a new-entry candidate.
    """
    shortlist = list(liquid[:MAX_ANALYSIS_MARKETS])
    selected = {row[1] for row in shortlist}
    monitor_only: set[str] = set()
    for symbol in sorted(set(required_symbols)):
        if symbol in selected or symbol not in markets:
            continue
        ticker = tickers.get(symbol) or {}
        last = ticker.get("last")
        if last is None or float(last) <= 0:
            continue
        bid, ask = ticker.get("bid"), ticker.get("ask")
        spread = None
        if bid and ask and float(bid) > 0 and float(ask) >= float(bid):
            mid = (float(bid) + float(ask)) / 2.0
            spread = ((float(ask) - float(bid)) / mid) * 100.0 if mid else None
        quote_volume = float(ticker.get("quoteVolume") or 0.0)
        row = (quote_volume, symbol, ticker, spread if spread is not None else 100.0)
        if len(shortlist) >= MAX_ANALYSIS_MARKETS:
            shortlist[-1] = row
        else:
            shortlist.append(row)
        monitor_only.add(symbol)
        selected.add(symbol)
    return shortlist, monitor_only


def scan(required_symbols: Iterable[str] = ()) -> dict:
    exchange = ccxt.kraken({"enableRateLimit": True, "timeout": 20000})
    results = []
    errors = []
    markets = exchange.load_markets()
    symbols = discover_eur_spot_markets(markets)
    try:
        tickers = exchange.fetch_tickers(symbols)
    except Exception as exc:
        return {
            "mode": "paper",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "exchange": "kraken",
            "universe_size": len(symbols),
            "scanned_count": 0,
            "results": [],
            "errors": [{"stage": "tickers", "error": str(exc)[:240]}],
            "orders_enabled": False,
        }
    liquid = []
    for symbol in symbols:
        ticker = tickers.get(symbol) or {}
        quote_volume = ticker.get("quoteVolume")
        bid, ask = ticker.get("bid"), ticker.get("ask")
        if quote_volume is None or float(quote_volume or 0) < MIN_QUOTE_VOLUME_EUR:
            continue
        if not bid or not ask or float(bid) <= 0 or float(ask) <= float(bid):
            continue
        mid = (float(bid) + float(ask)) / 2.0
        spread = ((float(ask) - float(bid)) / mid) * 100.0
        if spread > MAX_SPREAD_PCT:
            continue
        liquid.append((float(quote_volume), symbol, ticker, spread))
    liquid.sort(reverse=True)
    shortlist, monitor_only = select_shortlist(liquid, required_symbols, markets, tickers)
    timeframe_ms = int(exchange.parse_timeframe(TIMEFRAME) * 1000)
    now_ms = exchange.milliseconds()
    for quote_volume, symbol, ticker, spread in shortlist:
        try:
            candles = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=CANDLE_LIMIT)
            closed = [c for c in candles if int(c[0]) + timeframe_ms <= now_ms]
            item = analyse_candles(symbol, closed)
            market = markets.get(symbol, {})
            limits = market.get("limits", {})
            item["minimum_order_amount"] = (limits.get("amount") or {}).get("min")
            item["minimum_order_cost_eur"] = (limits.get("cost") or {}).get("min")
            item["quote_volume_24h_eur"] = round(quote_volume, 2)
            item["spread_pct"] = round(spread, 4) if spread is not None else None
            item["change_24h_pct"] = ticker.get("percentage")
            item["mark_price_eur"] = float(ticker.get("last") or item["last_price_eur"])
            item["opportunity_score"] = rank_opportunity(item)
            item["monitor_only"] = symbol in monitor_only
            if item["monitor_only"]:
                item["warning"] = "Open-position monitoring only; excluded from new entries."
            else:
                item["warning"] = "Research rank only; fees, risk and strategy gates still apply."
            results.append(item)
        except Exception as exc:
            errors.append({"symbol": symbol, "error": str(exc)[:240]})
    results.sort(key=lambda row: (row["opportunity_score"], row["quote_volume_24h_eur"]), reverse=True)
    return {
        "mode": "paper",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "exchange": "kraken",
        "universe_size": len(symbols),
        "liquid_candidates": len(liquid),
        "scanned_count": len(results),
        "results": results,
        "errors": errors,
        "orders_enabled": False,
    }


if __name__ == "__main__":
    print(json.dumps(scan(), indent=2))
