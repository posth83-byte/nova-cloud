"""Download public Kraken OHLCV history for offline backtesting."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import ccxt


def download(symbol: str, timeframe: str, days: int) -> list[list[float]]:
    exchange = ccxt.kraken({"enableRateLimit": True, "timeout": 20000})
    timeframe_ms = int(exchange.parse_timeframe(timeframe) * 1000)
    since = exchange.milliseconds() - days * 86_400_000
    rows: dict[int, list[float]] = {}
    for _ in range(20):
        batch = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=720)
        if not batch:
            break
        for candle in batch:
            rows[int(candle[0])] = candle
        newest = max(int(c[0]) for c in batch)
        next_since = newest + timeframe_ms
        if next_since <= since or newest >= exchange.milliseconds() - timeframe_ms:
            break
        since = next_since
        if len(batch) < 2:
            break
    return [rows[key] for key in sorted(rows)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Download public Kraken candles")
    parser.add_argument("--symbol", default="BTC/EUR", choices=("BTC/EUR", "ETH/EUR"))
    parser.add_argument("--timeframe", default="1h", choices=("1h", "4h", "1d"))
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--output", default="trading/history.json")
    args = parser.parse_args()
    if not 1 <= args.days <= 365:
        parser.error("--days must be between 1 and 365")
    candles = download(args.symbol, args.timeframe, args.days)
    Path(args.output).write_text(json.dumps(candles), encoding="utf-8")
    print(json.dumps({
        "symbol": args.symbol,
        "timeframe": args.timeframe,
        "candles": len(candles),
        "output": args.output,
        "note": "Public market data only; no exchange credentials or orders.",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
